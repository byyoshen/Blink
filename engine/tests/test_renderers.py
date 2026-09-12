"""Unit coverage for the semantic split and the per-client view renderers.

``validate_views.py`` checks the committed repository, but it only byte-compares
the Surge payload and then trusts each client's header count.  The actual
per-client view serialization -- Surge's leading dot, mihomo's ``+.`` prefix, the
classical fallback, the QX filter form -- had no direct test, so a wrong prefix
would ship as a silently ineffective rule set.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build  # noqa: E402
import parity_check  # noqa: E402
import renderers  # noqa: E402

LOCATION = build.SourceLocation("fixture", 1, ("App",))


def rule(kind: str, value: str, *options: str) -> build.Rule:
    return build.Rule(kind, value, options, LOCATION)


def body(text: str) -> list[str]:
    """The payload lines of a generated file, without the two header lines."""
    lines = text.splitlines()
    assert lines[0].startswith("# 规则名称:"), lines[0]
    assert lines[1].startswith("# 规则统计:"), lines[1]
    assert lines[2] == ""
    return lines[3:]


def header_count(text: str) -> int:
    return int(text.splitlines()[1].split(":", 1)[1].strip())


class SemanticViewTests(unittest.TestCase):
    def test_pure_domain_app_produces_only_a_domainset_view(self) -> None:
        views = build.semantic_views(
            [rule("DOMAIN", "api.example.com"), rule("DOMAIN-SUFFIX", "example.com")]
        )
        self.assertEqual([name for name, _rules in views], ["domainset"])

    def test_keyword_or_process_downgrades_the_domain_view_to_nonip(self) -> None:
        for extra in (rule("DOMAIN-KEYWORD", "example"), rule("PROCESS-NAME", "app")):
            views = build.semantic_views([rule("DOMAIN-SUFFIX", "example.com"), extra])
            self.assertEqual([name for name, _rules in views], ["nonip"], extra.kind)

    def test_ip_rules_always_form_the_last_view(self) -> None:
        views = build.semantic_views(
            [
                rule("DOMAIN-SUFFIX", "example.com"),
                rule("IP-CIDR", "192.0.2.0/24", "no-resolve"),
            ]
        )
        self.assertEqual([name for name, _rules in views], ["domainset", "ip"])

    def test_ip_only_app_produces_no_empty_domain_view(self) -> None:
        views = build.semantic_views([rule("IP-CIDR6", "2001:db8::/64", "no-resolve")])
        self.assertEqual([name for name, _rules in views], ["ip"])

    def test_view_rules_partition_the_canonical_set_exactly(self) -> None:
        rules = [
            rule("DOMAIN", "api.example.com"),
            rule("DOMAIN-KEYWORD", "example"),
            rule("USER-AGENT", "Example*"),
            rule("IP-CIDR", "192.0.2.0/24", "no-resolve"),
        ]
        split = [item for _name, view in build.semantic_views(rules) for item in view]
        self.assertEqual(split, rules)


class DomainsetPayloadTests(unittest.TestCase):
    def test_surge_domainset_marks_a_suffix_with_a_leading_dot(self) -> None:
        text = renderers.render_surge_domainset(
            [rule("DOMAIN", "api.example.com"), rule("DOMAIN-SUFFIX", "example.com")], "App"
        )
        self.assertEqual(body(text), ["api.example.com", ".example.com"])

    def test_mihomo_domainset_marks_a_suffix_with_a_plus_dot(self) -> None:
        text = renderers.render_mihomo_domainset(
            [rule("DOMAIN", "api.example.com"), rule("DOMAIN-SUFFIX", "example.com")], "App"
        )
        self.assertEqual(body(text), ["api.example.com", "+.example.com"])

    def test_domainset_renderers_refuse_every_non_domain_kind(self) -> None:
        for kind, value in (
            ("DOMAIN-KEYWORD", "example"),
            ("USER-AGENT", "Example*"),
            ("PROCESS-NAME", "app"),
            ("IP-CIDR", "192.0.2.0/24"),
        ):
            for render in (renderers.render_surge_domainset, renderers.render_mihomo_domainset):
                with self.assertRaises(renderers.RendererError):
                    render([rule(kind, value)], "App")

    def test_domainset_renderers_never_emit_an_empty_payload(self) -> None:
        for render in (renderers.render_surge_domainset, renderers.render_mihomo_domainset):
            with self.assertRaises(renderers.RendererError):
                render([], "App")


class EgernSchemaTests(unittest.TestCase):
    def test_emitted_buckets_are_exactly_the_ones_parity_check_accepts(self) -> None:
        # parity_check rejects any key it does not know, so a bucket the renderer
        # can emit but the verifier cannot read would fail the build with a
        # misleading "unknown Egern keys" error instead of a renderer error.
        self.assertEqual(
            set(renderers.EGERN_KEY_ORDER),
            {"no_resolve"} | set(parity_check.EGERN_TYPES),
        )

    def test_ip_rules_without_no_resolve_omit_the_set_level_flag(self) -> None:
        # Egern's no_resolve is set-level: all-on emits it, all-off omits it, and
        # only a genuine mix is unexpressible.  The all-off case must not be
        # mistaken for a mix, or an upstream publishing bare IP-CIDR lines would
        # fail the whole build with a message describing the wrong cause.
        text, dropped = renderers.render_egern_yaml(
            [rule("DOMAIN-SUFFIX", "example.com"), rule("IP-CIDR", "192.0.2.0/24")], "App"
        )
        self.assertEqual(dropped, [])
        self.assertNotIn("no_resolve", text)
        self.assertIn("192.0.2.0/24", text)

    def test_ip_rules_all_carrying_no_resolve_emit_the_set_level_flag(self) -> None:
        text, _dropped = renderers.render_egern_yaml(
            [rule("IP-CIDR", "192.0.2.0/24", "no-resolve")], "App"
        )
        self.assertIn("no_resolve: true", text)

    def test_mixed_no_resolve_still_fails_explicitly(self) -> None:
        with self.assertRaisesRegex(renderers.RendererError, "set-level"):
            renderers.render_egern_yaml(
                [
                    rule("IP-CIDR", "192.0.2.0/24", "no-resolve"),
                    rule("IP-CIDR", "198.51.100.0/24"),
                ],
                "App",
            )

    def test_every_canonical_kind_is_either_bucketed_or_explicitly_dropped(self) -> None:
        sample = {
            "DOMAIN": "api.example.com",
            "DOMAIN-SUFFIX": "example.com",
            "DOMAIN-KEYWORD": "example",
            "USER-AGENT": "Example*",
            "PROCESS-NAME": "com.example.app",
            "IP-CIDR": "192.0.2.0/24",
            "IP-CIDR6": "2001:db8::/64",
        }
        self.assertEqual(set(sample), set(build.ALLOWED_RULE_TYPES))
        for kind, value in sample.items():
            rules = [rule(kind, value), rule("DOMAIN-SUFFIX", "anchor.example")]
            text, dropped = renderers.render_egern_yaml(rules, "App")
            if kind == "PROCESS-NAME":
                self.assertEqual(dropped, [f"{kind},{value}"])
            else:
                self.assertEqual(dropped, [], kind)
                self.assertIn(value, text, kind)


class RenderViewTests(unittest.TestCase):
    DOMAINS = [rule("DOMAIN", "api.example.com"), rule("DOMAIN-SUFFIX", "example.com")]
    NONIP = [
        rule("DOMAIN-SUFFIX", "example.com"),
        rule("DOMAIN-KEYWORD", "example"),
        rule("USER-AGENT", "Example*"),
        rule("PROCESS-NAME", "com.example.app"),
    ]
    IP = [
        rule("IP-CIDR", "192.0.2.0/24", "no-resolve"),
        rule("IP-CIDR6", "2001:db8::/64", "no-resolve"),
    ]

    def test_domainset_uses_each_clients_own_domain_list_format(self) -> None:
        expected = {
            # Surge DOMAIN-SET payload.
            "surge": ["api.example.com", ".example.com"],
            "shadowrocket": ["api.example.com", ".example.com"],
            # mihomo behavior: domain payload.
            "stash": ["api.example.com", "+.example.com"],
            "clash": ["api.example.com", "+.example.com"],
            # Clients that consume the classical form instead.
            "loon": ["DOMAIN,api.example.com", "DOMAIN-SUFFIX,example.com"],
            "egern": ["DOMAIN,api.example.com", "DOMAIN-SUFFIX,example.com"],
            "quantumultx": ["HOST,api.example.com,policy", "HOST-SUFFIX,example.com,policy"],
        }
        self.assertEqual(set(expected), set(renderers.CLIENTS))
        for client, lines in expected.items():
            text = renderers.render_view(client, "domainset", self.DOMAINS, "App")
            self.assertEqual(body(text), lines, client)

    def test_nonip_view_applies_each_clients_documented_drop(self) -> None:
        for client in ("surge", "shadowrocket", "loon", "stash"):
            lines = body(renderers.render_view(client, "nonip", self.NONIP, "App"))
            self.assertIn("PROCESS-NAME,com.example.app", lines)
            self.assertIn("USER-AGENT,Example*", lines)
        # Clash kernels have no USER-AGENT type.
        clash = body(renderers.render_view("clash", "nonip", self.NONIP, "App"))
        self.assertIn("PROCESS-NAME,com.example.app", clash)
        self.assertNotIn("USER-AGENT,Example*", clash)
        # Egern and QX cannot express PROCESS-NAME.
        egern = body(renderers.render_view("egern", "nonip", self.NONIP, "App"))
        self.assertNotIn("PROCESS-NAME,com.example.app", egern)
        self.assertIn("USER-AGENT,Example*", egern)
        qx = body(renderers.render_view("quantumultx", "nonip", self.NONIP, "App"))
        self.assertEqual(
            qx,
            [
                "HOST-SUFFIX,example.com,policy",
                "HOST-KEYWORD,example,policy",
                "USER-AGENT,Example*,policy",
            ],
        )

    def test_ip_view_keeps_no_resolve_wherever_the_format_carries_it(self) -> None:
        for client in ("surge", "shadowrocket", "loon", "stash", "clash", "egern"):
            lines = body(renderers.render_view(client, "ip", self.IP, "App"))
            self.assertEqual(
                lines,
                ["IP-CIDR,192.0.2.0/24,no-resolve", "IP-CIDR6,2001:db8::/64,no-resolve"],
                client,
            )
        # QX filter lines have no production-proven no-resolve slot.
        self.assertEqual(
            body(renderers.render_view("quantumultx", "ip", self.IP, "App")),
            ["IP-CIDR,192.0.2.0/24,policy", "IP6-CIDR,2001:db8::/64,policy"],
        )

    def test_header_count_matches_the_emitted_body_for_every_client_and_view(self) -> None:
        # validate_views.py compares this header against the expected phase size
        # after each client's drops, so the two must never disagree.
        for view_name, rules in (
            ("domainset", self.DOMAINS),
            ("nonip", self.NONIP),
            ("ip", self.IP),
        ):
            for client in renderers.CLIENTS:
                text = renderers.render_view(client, view_name, rules, "App")
                self.assertEqual(header_count(text), len(body(text)), f"{client}/{view_name}")

    def test_every_registered_client_can_render_every_view(self) -> None:
        for client in renderers.CLIENTS:
            for view_name in sorted(build.VIEW_TYPES):
                rules = {
                    "domainset": self.DOMAINS,
                    "nonip": self.NONIP,
                    "ip": self.IP,
                }[view_name]
                self.assertTrue(renderers.render_view(client, view_name, rules, "App"))

    def test_unknown_view_or_client_fails_loudly(self) -> None:
        with self.assertRaises(renderers.RendererError):
            renderers.render_view("surge", "everything", self.DOMAINS, "App")
        with self.assertRaises(renderers.RendererError):
            renderers.render_view("nonsuch", "domainset", self.DOMAINS, "App")


if __name__ == "__main__":
    unittest.main()
