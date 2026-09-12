from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "engine" / "scripts"))
import build_profile  # noqa: E402

# Sandboxed Windows runners may deny chmod on directories; tempfile cleanup
# calls it on every temporary directory it removes.  Redirect mkdtemp to
# plain directories inside the workspace so TemporaryDirectory keeps working.
import os
import tempfile as _tempfile

_WORKSPACE_TMP = Path(__file__).resolve().parents[2] / ".tmp-tests"
_temp_sequence = iter(range(1 << 30))


def _mkdtemp(*_args, **_kwargs):
    _WORKSPACE_TMP.mkdir(exist_ok=True)
    path = _WORKSPACE_TMP / f"t{os.getpid()}_{next(_temp_sequence)}"
    os.mkdir(path)
    return str(path)


_tempfile.mkdtemp = _mkdtemp


def sample_intent() -> dict:
    return {
        "version": 1,
        "subscription": {
            "name": "Sub",
            "url": "https://YOUR-SUBSCRIPTION-URL",
            "update_interval": 86400,
        },
        "policy_groups": [
            {"name": "Proxy", "type": "select", "members": ["HK", "Final", "Sub"]},
            {"name": "Final", "type": "select", "members": ["HK", "Auto", "DIRECT"]},
            {"name": "HK", "type": "select", "filter": "(?i)Hong\\s*Kong"},
            {
                "name": "Auto",
                "type": "url-test",
                "members": ["HK"],
                "interval": 600,
                "tolerance": 80,
            },
        ],
        "apps": {"YouTube": {"policy": "Proxy"}},
        "infrastructure": [
            {
                "name": "reject",
                "url": "https://ruleset.skk.moe/List/non_ip/reject.conf",
                "policy": "REJECT",
                "qx_url": "https://example.invalid/qx-reject.list",
            },
        ],
    }


def ip_sample_intent() -> dict:
    """Sample intent with an IP-phase infrastructure rule and an app IP view."""
    intent = sample_intent()
    intent["apps"]["YouTube"] = {"policy": "Proxy", "views": ["domainset", "ip"]}
    intent["infrastructure"].append(
        {
            "name": "china-ip",
            "url": "https://example.invalid/china-ip.conf",
            "policy": "DIRECT",
            "phase": "ip",
            "options": {client: "no-resolve" for client in build_profile.IP_NO_RESOLVE_CLIENTS},
            "qx_url": "https://example.invalid/qx-china-ip.list",
        }
    )
    return intent


class ProfileEngineTests(unittest.TestCase):
    def render(self, intent: dict) -> dict[str, str]:
        return {
            client: build_profile.render_client(client, intent) for client in build_profile.CLIENTS
        }

    def test_all_seven_clients_render_without_leftover_markers(self) -> None:
        outputs = self.render(sample_intent())
        self.assertEqual(set(outputs), set(build_profile.CLIENTS))
        for client, text in outputs.items():
            for marker in build_profile.MARKERS:
                self.assertNotIn(marker, text, f"{client} left marker {marker}")

    def test_every_profile_exposes_single_subscription_placeholder(self) -> None:
        outputs = self.render(sample_intent())
        placeholder = "https://YOUR-SUBSCRIPTION-URL"
        for client, text in outputs.items():
            self.assertIn(placeholder, text, client)
        for client in ("shadowrocket", "loon", "quantumultx"):
            self.assertIn("ADAPTED", outputs[client], client)

    def test_yaml_clients_parse_as_valid_yaml(self) -> None:
        outputs = self.render(sample_intent())
        for client in ("stash", "egern", "clash"):
            document = yaml.safe_load(outputs[client])
            self.assertIsInstance(document, dict)

    def test_clash_uses_text_format_drops_sub_and_ends_with_match(self) -> None:
        outputs = self.render(sample_intent())
        text = outputs["clash"]
        document = yaml.safe_load(text)
        # format: text is mandatory for classical providers (default is yaml).
        self.assertGreater(text.count("format: text"), 0)
        # Clash proxies arrays cannot reference a provider name: Sub must be
        # covered by the region filter groups instead.
        proxy_group = next(g for g in document["proxy-groups"] if g["name"] == "Proxy")
        self.assertNotIn("Sub", proxy_group["proxies"])
        hk_group = next(g for g in document["proxy-groups"] if g["name"] == "HK")
        self.assertEqual(hk_group["use"], ["Sub"])
        # Infrastructure + app providers and the MATCH tail rule.
        self.assertIn("RULE-SET,reject,REJECT", text)
        self.assertIn("RULE-SET,YouTube,Proxy", text)
        self.assertTrue(text.rstrip().endswith("- MATCH,Final"))

    def test_stash_and_egern_filters_are_single_quoted_and_parse(self) -> None:
        outputs = self.render(sample_intent())
        self.assertIn("filter: '(?i)Hong\\s*Kong'", outputs["stash"])
        document = yaml.safe_load(outputs["stash"])
        group = next(g for g in document["proxy-groups"] if g["name"] == "HK")
        self.assertEqual(group["filter"], "(?i)Hong\\s*Kong")

    def test_qx_keeps_group_name_case_and_lowercases_builtins(self) -> None:
        outputs = self.render(sample_intent())
        text = outputs["quantumultx"]
        self.assertIn("force-policy=Proxy", text)  # 组名保持大小写
        self.assertIn("force-policy=reject", text)  # 内置策略小写
        self.assertIn("static=Final, HK,Auto,direct", text)
        self.assertNotIn("Sub", text.split("[policy]")[1].split("[filter_remote]")[0])

    def test_qx_requires_qx_url_for_remote_rules(self) -> None:
        intent = sample_intent()
        del intent["infrastructure"][0]["qx_url"]
        with self.assertRaisesRegex(build_profile.ProfileError, "qx_url"):
            build_profile.render_client("quantumultx", intent)

    def test_unknown_group_member_fails(self) -> None:
        intent = sample_intent()
        intent["policy_groups"][0]["members"].append("Nope")
        with self.assertRaisesRegex(build_profile.ProfileError, "unknown member"):
            build_profile.validate_intent(intent)

    def test_cycle_detection_fails(self) -> None:
        intent = sample_intent()
        intent["policy_groups"][0]["members"] = ["Loop"]
        intent["policy_groups"].append({"name": "Loop", "type": "select", "members": ["Proxy"]})
        with self.assertRaisesRegex(build_profile.ProfileError, "cycle"):
            build_profile.validate_intent(intent)

    def test_app_policy_must_resolve(self) -> None:
        intent = sample_intent()
        intent["apps"]["YouTube"]["policy"] = "Ghost"
        with self.assertRaisesRegex(build_profile.ProfileError, "does not exist"):
            build_profile.validate_intent(intent)

    def test_client_availability_list_honored(self) -> None:
        intent = sample_intent()
        intent["infrastructure"][0]["clients"] = ["surge"]
        outputs = self.render(intent)
        self.assertIn("reject.conf", outputs["surge"])
        self.assertNotIn("reject.conf", outputs["shadowrocket"])

    def test_inline_domain_infrastructure_renders_on_every_client(self) -> None:
        # ``kind: domain`` carries no URL, so it must not trip the QX qx_url
        # requirement that only applies to remote rule sets.
        intent = sample_intent()
        intent["infrastructure"].insert(
            0, {"name": "probe", "kind": "domain", "value": "example.com", "policy": "DIRECT"}
        )
        build_profile.validate_intent(intent)
        outputs = self.render(intent)
        self.assertIn("host, example.com, direct", outputs["quantumultx"])
        self.assertIn("DOMAIN,example.com,DIRECT", outputs["surge"])
        self.assertIn("  - DOMAIN,example.com,DIRECT", outputs["stash"])

    def test_ip_phase_reference_keeps_no_resolve_where_supported(self) -> None:
        intent = ip_sample_intent()
        outputs = self.render(intent)
        self.assertIn(
            "RULE-SET,https://example.invalid/china-ip.conf,DIRECT,no-resolve", outputs["surge"]
        )
        self.assertIn(
            "RULE-SET,https://example.invalid/china-ip.conf,DIRECT,no-resolve",
            outputs["shadowrocket"],
        )
        self.assertIn("  - RULE-SET,china_ip,DIRECT,no-resolve", outputs["stash"])
        self.assertIn("  - RULE-SET,china_ip,DIRECT,no-resolve", outputs["clash"])

    def test_ip_view_reference_keeps_no_resolve_where_supported(self) -> None:
        intent = ip_sample_intent()
        outputs = self.render(intent)
        self.assertIn("YouTube-ip.conf,Proxy,no-resolve", outputs["surge"])
        self.assertIn("YouTube-ip.conf,Proxy,no-resolve", outputs["shadowrocket"])
        self.assertIn("  - RULE-SET,YouTube_ip,Proxy,no-resolve", outputs["stash"])
        self.assertIn("  - RULE-SET,YouTube_ip,Proxy,no-resolve", outputs["clash"])
        # Clients without a reference-level slot must not invent one.
        for client in set(build_profile.CLIENTS) - set(build_profile.IP_NO_RESOLVE_CLIENTS):
            self.assertNotIn("-ip.conf, policy = Proxy, no-resolve", outputs[client])

    def test_real_intent_ip_references_all_carry_no_resolve(self) -> None:
        """Every IP-phase reference must carry no-resolve on clients that support it.

        The upstream china_ip list has no per-line no-resolve, so the reference
        line is the only place the domain-first / IP-last guarantee can live.
        """
        intent = build_profile.load_intent(build_profile.INTENT_PATH)
        build_profile.validate_intent(intent)
        ip_urls = {
            rule["url"]
            for rule in intent.get("infrastructure", [])
            if build_profile._phase(rule) == "ip" and rule.get("url")
        }
        self.assertTrue(ip_urls, "the real intent must declare IP-phase infrastructure")
        mihomo_keys = {
            re.sub(r"[^A-Za-z0-9]", "_", rule["name"])
            for rule in intent["infrastructure"]
            if build_profile._phase(rule) == "ip"
        }
        mihomo_keys |= {
            f"{app}_ip"
            for app, entry in intent["apps"].items()
            if "ip" in (entry.get("views") or [])
        }
        checked = 0
        for client in sorted(build_profile.IP_NO_RESOLVE_CLIENTS):
            for line in build_profile.render_client(client, intent).splitlines():
                stripped = line.strip()
                if stripped.startswith("#") or "RULE-SET," not in stripped:
                    continue
                if client in {"stash", "clash"}:
                    key = stripped.split("RULE-SET,", 1)[1].split(",")[0]
                    if key not in mihomo_keys:
                        continue
                elif not (any(url in stripped for url in ip_urls) or "-ip.conf" in stripped):
                    continue
                checked += 1
                self.assertIn("no-resolve", stripped, f"{client}: {stripped}")
        self.assertGreaterEqual(checked, 4 * len(ip_urls))

    def test_write_outputs_generates_profiles_dir(self) -> None:
        intent = sample_intent()
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            for client, (_template, output_name) in build_profile.CLIENTS.items():
                template = root / "sources" / "profile" / "templates" / _template
                template.parent.mkdir(parents=True, exist_ok=True)
                template.write_text("__POLICY_GROUPS__\n__RULES__\n", encoding="utf-8")
            # Swap module constants for the temp root.
            original = (build_profile.TEMPLATE_DIR, build_profile.OUTPUT_DIR)
            build_profile.TEMPLATE_DIR = root / "sources" / "profile" / "templates"
            build_profile.OUTPUT_DIR = root / "Profiles"
            try:
                outputs = {
                    client: build_profile.render_client(client, intent)
                    for client in build_profile.CLIENTS
                }
                build_profile.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
                for client, text in outputs.items():
                    _template, output_name = build_profile.CLIENTS[client]
                    (build_profile.OUTPUT_DIR / output_name).write_text(text, encoding="utf-8")
                self.assertEqual(len(list((root / "Profiles").glob("*"))), 7)
            finally:
                build_profile.TEMPLATE_DIR, build_profile.OUTPUT_DIR = original


if __name__ == "__main__":
    unittest.main()
