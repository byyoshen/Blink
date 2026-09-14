from __future__ import annotations

import os
import sys
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "engine" / "scripts"))
import build  # noqa: E402

# Some sandboxed runners ship a tempfile whose mkdtemp creates directories
# with restrictive DACLs: subdirectory creation inside them then fails with
# PermissionError.  Redirect mkdtemp to plain directories inside the
# workspace so TemporaryDirectory keeps working everywhere.  Cleanup still
# runs through the standard path.
import tempfile as _tempfile

_WORKSPACE_TMP = Path(__file__).resolve().parents[2] / ".tmp-tests"
_temp_sequence = iter(range(1 << 30))


def _mkdtemp(*_args, **_kwargs):
    _WORKSPACE_TMP.mkdir(exist_ok=True)
    path = _WORKSPACE_TMP / f"t{os.getpid()}_{next(_temp_sequence)}"
    os.mkdir(path)
    return str(path)


_tempfile.mkdtemp = _mkdtemp

# Fallback for runners that also deny chmod on directories (tempfile cleanup
# calls it before deleting).  Neutralize directory chmod only when unusable.
if os.name == "nt":
    try:
        os.chmod(_WORKSPACE_TMP, 0o700)
    except (PermissionError, FileNotFoundError):
        _real_chmod = os.chmod

        def _chmod_skip_directories(path, mode):
            if not os.path.isdir(path):
                return _real_chmod(path, mode)
            return None

        os.chmod = _chmod_skip_directories


ROOT_URL = "https://example.invalid/data/root"


def app_config(
    *, allow=None, deny=None, attributes=None, source_format="v2fly-domain-list", url=ROOT_URL
) -> dict:
    return {
        "enabled": True,
        "output": "Surge/Test.list",
        "sources": [
            {"name": "test-source", "role": "primary", "format": source_format, "url": url}
        ],
        "include_policy": {"mode": "explicit", "allow": allow or [], "deny": deny or []},
        "attributes": {"mode": "explicit", "include": attributes or []},
        "supplement": "engine/sources/supplement/Test.list",
        "exclude": [],
    }


class BuildTests(unittest.TestCase):
    def compile(self, config: dict, texts: dict[str, str]) -> build.Compilation:
        with TemporaryDirectory() as directory:
            return build.compile_app("Test", config, Path(directory), texts.__getitem__)

    def test_maps_core_v2fly_directives_and_normalizes(self) -> None:
        result = self.compile(
            app_config(),
            {ROOT_URL: "Example.COM.\nfull:Api.Example.com\nkeyword:GitHub\n"},
        )
        self.assertEqual(
            build.render_classical_body(result.rules),
            ["DOMAIN,api.example.com", "DOMAIN-SUFFIX,example.com", "DOMAIN-KEYWORD,github"],
        )

    def test_loads_and_validates_project_manifest(self) -> None:
        root = Path(__file__).resolve().parents[2]
        manifest = build.load_manifest(root / "engine" / "sources" / "apps.yaml")
        self.assertEqual(
            set(manifest["apps"]),
            {
                "OKX",
                "WhatsApp",
                "LINE",
                "GitHub",
                "SafePal",
                "PayPal",
                "Netflix",
                "YouTube",
                "X",
                "Instagram",
                "Telegram",
                "Threads",
                "TikTok",
                "Spotify",
                "AI",
                "ZABank",
                "APTV",
                "Steam",
                "Disney",
                "ParamountPlus",
                "Hulu",
                "PrimeVideo",
                "HBO",
                "Twitch",
                "Facebook",
                "Google",
                "NBA",
                "Suno",
                "Starryblu",
                "AWSConsole",
            },
        )
        for app_name, app in manifest["apps"].items():
            build.validate_app_config(app_name, app)

    def test_write_outputs_adds_name_and_rule_count_header(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            config = app_config()
            rule = build.Rule(
                "DOMAIN-SUFFIX",
                "example.com",
                (),
                build.SourceLocation("test", 1, ("Test",)),
            )
            compilation = build.Compilation("Test", [rule], [], [], {})
            build.write_outputs([compilation], {"apps": {"Test": config}}, root)
            surge = (root / "Surge" / "Test.list").read_text(encoding="utf-8")
            self.assertEqual(
                surge, "# 规则名称: Test\n# 规则统计: 1\n\nDOMAIN-SUFFIX,example.com\n"
            )
            # The three classical clients consume the exact same bytes.
            for directory in ("Loon", "Shadowrocket", "Stash"):
                self.assertEqual(
                    (root / directory / "Test.list").read_text(encoding="utf-8"), surge
                )
            # Clash consumes the same classical bytes when no USER-AGENT is
            # present (its own directory, UA-dropped variant of the same body).
            self.assertEqual((root / "mihomo" / "Test.list").read_text(encoding="utf-8"), surge)
            # Egern gets its own YAML rule-set schema.
            self.assertEqual(
                (root / "Egern" / "Test.yaml").read_text(encoding="utf-8"),
                "# 规则名称: Test\n# 规则统计: 1\n\ndomain_suffix_set:\n- example.com\n",
            )
            # Quantumult X gets its own filter lines with a placeholder policy.
            self.assertEqual(
                (root / "QuantumultX" / "Test.list").read_text(encoding="utf-8"),
                "# 规则名称: Test\n# 规则统计: 1\n\nHOST-SUFFIX,example.com,policy\n",
            )

    def test_quantumultx_maps_kinds_and_drops_unexpressible(self) -> None:
        location = build.SourceLocation("test", 1, ("Test",))
        rules = [
            build.Rule("DOMAIN", "api.example.com", (), location),
            build.Rule("DOMAIN-SUFFIX", "example.com", (), location),
            build.Rule("DOMAIN-KEYWORD", "example", (), location),
            build.Rule("IP-CIDR", "192.0.2.0/24", ("no-resolve",), location),
            build.Rule("IP-CIDR6", "2001:db8::/64", ("no-resolve",), location),
            build.Rule("USER-AGENT", "Example App*", (), location),
            build.Rule("PROCESS-NAME", "com.example.app", (), location),
        ]
        text, dropped = build.render_quantumultx(rules, "Test")
        self.assertEqual(dropped, ["PROCESS-NAME,com.example.app"])
        self.assertEqual(
            text.splitlines()[3:],
            [
                "HOST,api.example.com,policy",
                "HOST-SUFFIX,example.com,policy",
                "HOST-KEYWORD,example,policy",
                "IP-CIDR,192.0.2.0/24,policy",
                "IP6-CIDR,2001:db8::/64,policy",
                "USER-AGENT,Example App*,policy",
            ],
        )
        self.assertEqual(text.splitlines()[1], "# 规则统计: 6")

    def test_clash_drops_user_agent_explicitly(self) -> None:
        location = build.SourceLocation("test", 1, ("Test",))
        rules = [
            build.Rule("DOMAIN", "api.example.com", (), location),
            build.Rule("DOMAIN-SUFFIX", "example.com", (), location),
            build.Rule("DOMAIN-KEYWORD", "example", (), location),
            build.Rule("IP-CIDR", "192.0.2.0/24", ("no-resolve",), location),
            build.Rule("IP-CIDR6", "2001:db8::/64", ("no-resolve",), location),
            build.Rule("USER-AGENT", "Example App*", (), location),
            build.Rule("PROCESS-NAME", "com.example.app", (), location),
        ]
        text, dropped = build.render_classical_mihomo(rules, "Test")
        # USER-AGENT is the only kind Clash cannot express: dropped and
        # reported, never silently skipped by the kernel.
        self.assertEqual(dropped, ["USER-AGENT,Example App*"])
        self.assertEqual(
            text.splitlines()[3:],
            [
                "DOMAIN,api.example.com",
                "DOMAIN-SUFFIX,example.com",
                "DOMAIN-KEYWORD,example",
                "IP-CIDR,192.0.2.0/24,no-resolve",
                "IP-CIDR6,2001:db8::/64,no-resolve",
                "PROCESS-NAME,com.example.app",
            ],
        )
        self.assertEqual(text.splitlines()[1], "# 规则统计: 6")

    def test_clash_output_never_silently_empty(self) -> None:
        location = build.SourceLocation("test", 1, ("Test",))
        with self.assertRaisesRegex(build.RendererError, "empty"):
            build.render_classical_mihomo(
                [build.Rule("USER-AGENT", "Example App*", (), location)], "Test"
            )

    def test_quantumultx_output_never_silently_empty(self) -> None:
        location = build.SourceLocation("test", 1, ("Test",))
        with self.assertRaisesRegex(build.RendererError, "empty"):
            build.render_quantumultx(
                [build.Rule("PROCESS-NAME", "com.example.app", (), location)], "Test"
            )

    def test_egern_yaml_covers_all_expressible_kinds(self) -> None:
        with TemporaryDirectory():
            location = build.SourceLocation("test", 1, ("Test",))
            rules = [
                build.Rule("DOMAIN", "api.example.com", (), location),
                build.Rule("DOMAIN-SUFFIX", "example.com", (), location),
                build.Rule("DOMAIN-KEYWORD", "example", (), location),
                build.Rule("IP-CIDR", "192.0.2.0/24", ("no-resolve",), location),
                build.Rule("IP-CIDR6", "2001:db8::/64", ("no-resolve",), location),
                build.Rule("USER-AGENT", "Example App*", (), location),
            ]
            text, dropped = build.render_egern_yaml(rules, "Test")
            self.assertEqual(dropped, [])
            document = yaml.safe_load(text.split("\n\n", 1)[1])
            self.assertEqual(document["no_resolve"], True)
            self.assertEqual(document["domain_set"], ["api.example.com"])
            self.assertEqual(document["domain_suffix_set"], ["example.com"])
            self.assertEqual(document["domain_keyword_set"], ["example"])
            self.assertEqual(document["ip_cidr_set"], ["192.0.2.0/24"])
            self.assertEqual(document["ip_cidr6_set"], ["2001:db8::/64"])
            self.assertEqual(document["user_agent_set"], ["Example App*"])

    def test_egern_drops_process_name_and_reports_it(self) -> None:
        location = build.SourceLocation("test", 1, ("Test",))
        rules = [
            build.Rule("PROCESS-NAME", "com.example.app", (), location),
            build.Rule("DOMAIN-SUFFIX", "example.com", (), location),
        ]
        text, dropped = build.render_egern_yaml(rules, "Test")
        self.assertEqual(dropped, ["PROCESS-NAME,com.example.app"])
        self.assertNotIn("process", text)
        self.assertEqual(text.splitlines()[1], "# 规则统计: 1")

    def test_egern_omits_no_resolve_without_ip_rules(self) -> None:
        location = build.SourceLocation("test", 1, ("Test",))
        text, _dropped = build.render_egern_yaml(
            [build.Rule("DOMAIN-SUFFIX", "example.com", (), location)], "Test"
        )
        self.assertNotIn("no_resolve", text)

    def test_egern_mixed_no_resolve_fails_explicitly(self) -> None:
        location = build.SourceLocation("test", 1, ("Test",))
        rules = [
            build.Rule("IP-CIDR", "192.0.2.0/24", ("no-resolve",), location),
            build.Rule("IP-CIDR", "198.51.100.0/24", (), location),
        ]
        with self.assertRaisesRegex(build.RendererError, "no_resolve"):
            build.render_egern_yaml(rules, "Test")

    def test_egern_output_never_silently_empty(self) -> None:
        location = build.SourceLocation("test", 1, ("Test",))
        with self.assertRaisesRegex(build.RendererError, "empty"):
            build.render_egern_yaml(
                [build.Rule("PROCESS-NAME", "com.example.app", (), location)], "Test"
            )

    def test_existing_surge_outputs_roundtrip_byte_identical(self) -> None:
        # Backward-compatibility gate: every committed Surge/*.list must be
        # reproduced byte-for-byte by parse -> dedup/sort -> classical render.
        root = Path(__file__).resolve().parents[2]
        for path in sorted((root / "Surge").glob("*.list")):
            with self.subTest(app=path.stem):
                text = path.read_text(encoding="utf-8")
                rules = build.parse_surge_rule_set_text(text, str(path), ("golden",))
                unique = {rule.key: rule for rule in rules}
                ordered = sorted(
                    unique.values(), key=lambda rule: (build.SORT_ORDER[rule.kind], rule.value)
                )
                self.assertEqual(build.render_classical(ordered, path.stem), text)

    def test_explicit_include_allows_and_denies(self) -> None:
        result = self.compile(
            app_config(allow=["child"], deny=["other"]),
            {
                ROOT_URL: "include:child\ninclude:other\nroot.example\n",
                "https://example.invalid/data/child": "child.example\n",
            },
        )
        self.assertEqual(
            build.render_classical_body(result.rules),
            ["DOMAIN-SUFFIX,child.example", "DOMAIN-SUFFIX,root.example"],
        )
        self.assertEqual([name for name, _ in result.denied_includes], ["other"])

    def test_unclassified_include_fails(self) -> None:
        with self.assertRaisesRegex(build.BuildError, "not declared"):
            self.compile(app_config(), {ROOT_URL: "include:child\n"})

    def test_attribute_selection_keeps_untagged_entries(self) -> None:
        texts = {ROOT_URL: "plain.example\ncn.example @cn\nads.example @ads\n"}
        without_attributes = self.compile(app_config(), texts)
        self.assertEqual(
            build.render_classical_body(without_attributes.rules), ["DOMAIN-SUFFIX,plain.example"]
        )
        with_cn = self.compile(app_config(attributes=["cn"]), texts)
        self.assertEqual(
            build.render_classical_body(with_cn.rules),
            ["DOMAIN-SUFFIX,cn.example", "DOMAIN-SUFFIX,plain.example"],
        )

    def test_negative_attributes_and_regexp_fail(self) -> None:
        with self.assertRaisesRegex(build.BuildError, "negative attributes"):
            self.compile(app_config(), {ROOT_URL: "not-cn.example @!cn\n"})
        with self.assertRaisesRegex(build.BuildError, "unsupported v2fly regexp"):
            self.compile(app_config(), {ROOT_URL: "regexp:^example\\.com$\n"})

    def test_parses_native_surge_rules_conservatively(self) -> None:
        source_url = "https://example.invalid/Surge/Test.list"
        result = self.compile(
            app_config(source_format="surge-rule-set", url=source_url),
            {
                source_url: (
                    "# generated source\n"
                    "DOMAIN,Api.Example.COM.\n"
                    "DOMAIN-SUFFIX,Example.com\n"
                    "DOMAIN-KEYWORD,GitHub\n"
                    "USER-AGENT,Example App*\n"
                    "PROCESS-NAME,Example App\n"
                    "IP-CIDR,192.0.2.7/24,no-resolve\n"
                    "IP-CIDR6,2001:db8::7/64\n"
                )
            },
        )
        self.assertEqual(
            build.render_classical_body(result.rules),
            [
                "DOMAIN,api.example.com",
                "DOMAIN-SUFFIX,example.com",
                "DOMAIN-KEYWORD,github",
                "USER-AGENT,Example App*",
                "PROCESS-NAME,Example App",
                "IP-CIDR,192.0.2.0/24,no-resolve",
                "IP-CIDR6,2001:db8::/64",
            ],
        )

    def test_native_surge_unknown_types_and_policies_fail(self) -> None:
        source_url = "https://example.invalid/Surge/Test.list"
        with self.assertRaisesRegex(build.BuildError, "unsupported Surge rule type"):
            self.compile(
                app_config(source_format="surge-rule-set", url=source_url),
                {source_url: "URL-REGEX,^https://example\\.com\n"},
            )
        with self.assertRaisesRegex(build.BuildError, "unexpected option"):
            self.compile(
                app_config(source_format="surge-rule-set", url=source_url),
                {source_url: "DOMAIN,example.com,Proxy\n"},
            )

    def test_rejects_invalid_supplement_keyword(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            supplement = Path(temporary_directory) / "Demo.list"
            supplement.write_text("DOMAIN-KEYWORD,\n", encoding="utf-8")
            with self.assertRaisesRegex(build.BuildError, "invalid supplement rule"):
                build.parse_supplement(supplement, "Demo")

    def test_type_level_exclude_skips_ip_asn_and_url_regex(self) -> None:
        source_url = "https://example.invalid/Surge/Test.list"
        config = app_config(source_format="surge-rule-set", url=source_url)
        config["exclude"] = ["ip-asn:*", "url-regex:*"]
        result = self.compile(
            config,
            {
                source_url: (
                    "DOMAIN-SUFFIX,example.com\n"
                    "IP-ASN,11983,no-resolve\n"
                    "URL-REGEX,^https://example\\.com\n"
                )
            },
        )
        self.assertEqual(build.render_classical_body(result.rules), ["DOMAIN-SUFFIX,example.com"])
        self.assertEqual(
            result.skipped_excluded, ["IP-ASN,11983", "URL-REGEX,^https://example\\.com"]
        )

    def test_v2fly_regexp_type_level_exclude(self) -> None:
        source_url = "https://example.invalid/data/aws"
        config = app_config(source_format="v2fly-domain-list", url=source_url, deny=["aws-cn"])
        config["exclude"] = ["regexp:*"]
        result = self.compile(
            config,
            {
                source_url: (
                    "include:aws-cn\n"
                    "aws.amazon.com\n"
                    "regexp:.+\\.awsdns-[0-9][0-9]\\.(co\\.uk|com|net|org)$\n"
                ),
            },
        )
        self.assertEqual(
            build.render_classical_body(result.rules), ["DOMAIN-SUFFIX,aws.amazon.com"]
        )
        self.assertEqual(
            result.skipped_excluded, [".+\\.awsdns-[0-9][0-9]\\.(co\\.uk|com|net|org)$"]
        )
        self.assertEqual(result.denied_includes, [("aws-cn", result.denied_includes[0][1])])

    def test_v2fly_regexp_without_exclude_fails(self) -> None:
        source_url = "https://example.invalid/data/aws"
        config = app_config(source_format="v2fly-domain-list", url=source_url, deny=["aws-cn"])
        with self.assertRaisesRegex(build.BuildError, "unsupported v2fly regexp"):
            self.compile(
                config,
                {source_url: "aws.amazon.com\nregexp:.+\\.awsdns-[0-9][0-9]\\.com$\n"},
            )

    def test_type_level_exclude_requires_wildcard_value(self) -> None:
        config = app_config(
            source_format="surge-rule-set", url="https://example.invalid/Surge/Test.list"
        )
        config["exclude"] = ["ip-asn:11983"]
        with self.assertRaisesRegex(build.BuildError, "must use '\\*'"):
            self.compile(
                config, {"https://example.invalid/Surge/Test.list": "DOMAIN-SUFFIX,example.com\n"}
            )

    def test_supplement_only_app_builds_from_supplement(self) -> None:
        config = app_config()
        config["sources"] = []
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            supplement_dir = root / "engine" / "sources" / "supplement"
            supplement_dir.mkdir(parents=True)
            (supplement_dir / "Test.list").write_text(
                "DOMAIN-SUFFIX,example.com\n", encoding="utf-8"
            )
            result = build.compile_app("Test", config, root, lambda url: "")
            self.assertEqual(
                build.render_classical_body(result.rules), ["DOMAIN-SUFFIX,example.com"]
            )

    def test_supplement_only_app_without_rules_fails(self) -> None:
        config = app_config()
        config["sources"] = []
        with TemporaryDirectory() as temporary_directory:
            with self.assertRaisesRegex(build.BuildError, "empty"):
                build.compile_app("Test", config, Path(temporary_directory), lambda url: "")

    def test_include_cycle_fails(self) -> None:
        with self.assertRaisesRegex(build.BuildError, "cycle"):
            self.compile(
                app_config(allow=["child", "test-source"]),
                {
                    ROOT_URL: "include:child\nroot.example\n",
                    "https://example.invalid/data/child": "include:test-source\n",
                },
            )

    def test_mixed_domain_and_type_level_excludes(self) -> None:
        source_url = "https://example.invalid/Surge/Test.list"
        config = app_config(source_format="surge-rule-set", url=source_url)
        config["exclude"] = ["domain-suffix:blocked.com", "ip-asn:*"]
        result = self.compile(
            config,
            {
                source_url: "DOMAIN-SUFFIX,example.com\nDOMAIN-SUFFIX,blocked.com\nIP-ASN,11983,no-resolve\n"
            },
        )
        self.assertEqual(build.render_classical_body(result.rules), ["DOMAIN-SUFFIX,example.com"])
        self.assertEqual(result.skipped_excluded, ["IP-ASN,11983"])

    def test_domain_excludes_are_counted_per_declared_spec(self) -> None:
        source_url = "https://example.invalid/Surge/Test.list"
        config = app_config(source_format="surge-rule-set", url=source_url)
        config["exclude"] = [
            "domain-suffix:cdn.example",
            "domain-keyword:tracker",
            "domain-suffix:never.example",
        ]
        result = self.compile(
            config,
            {
                source_url: (
                    "DOMAIN-SUFFIX,keep.example\n"
                    "DOMAIN-SUFFIX,cdn.example\n"
                    "DOMAIN,asset.cdn.example\n"
                    "DOMAIN-KEYWORD,tracker\n"
                )
            },
        )
        self.assertEqual(build.render_classical_body(result.rules), ["DOMAIN-SUFFIX,keep.example"])
        # A declared exclude that matches nothing stays in the record as a zero,
        # so an upstream that stopped carrying the rule becomes a visible diff.
        self.assertEqual(
            result.excluded_domains,
            {
                "domain-suffix:cdn.example": 2,
                "domain-keyword:tracker": 1,
                "domain-suffix:never.example": 0,
            },
        )

    def test_excluded_domains_recorded_in_provenance_only_when_declared(self) -> None:
        source_url = "https://example.invalid/Surge/Test.list"
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            config = app_config(source_format="surge-rule-set", url=source_url)
            config["exclude"] = ["domain-suffix:cdn.example"]
            manifest = {"version": 1, "apps": {"Test": config}}
            texts = {source_url: "DOMAIN-SUFFIX,keep.example\nDOMAIN-SUFFIX,cdn.example\n"}
            compilation = build.compile_app("Test", config, root, texts.__getitem__)
            rendered = build.rendered_outputs(compilation, manifest, root)
            record = build.app_provenance_record(compilation, config, rendered, root)
            self.assertEqual(
                record["canonical"]["excluded_domains"], {"domain-suffix:cdn.example": 1}
            )

            plain = app_config(source_format="surge-rule-set", url=source_url)
            compilation = build.compile_app("Test", plain, root, texts.__getitem__)
            rendered = build.rendered_outputs(compilation, {"apps": {"Test": plain}}, root)
            record = build.app_provenance_record(compilation, plain, rendered, root)
            self.assertNotIn("excluded_domains", record["canonical"])

    def test_prune_stale_views_removes_a_view_the_split_no_longer_produces(self) -> None:
        source_url = "https://example.invalid/Surge/Test.list"
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            config = app_config(source_format="surge-rule-set", url=source_url)
            config["views"] = True
            manifest = {"version": 1, "apps": {"Test": config}}

            # First build carries an IP rule, so every client gets an ip view.
            compilation = build.compile_app(
                "Test",
                config,
                root,
                {source_url: "DOMAIN-SUFFIX,example.com\nIP-CIDR,198.51.100.0/24,no-resolve\n"}.get,
            )
            build.write_outputs([compilation], manifest, root)
            build.write_client_views([compilation], manifest, root)
            ip_views = [
                root / client.directory / "Test-ip.conf" for client in build.CLIENTS.values()
            ]
            self.assertTrue(all(path.is_file() for path in ip_views))

            # Upstream drops the IP rule: semantic_views stops producing the ip
            # view, and the orphan file would fail validate_views as spurious.
            compilation = build.compile_app(
                "Test", config, root, {source_url: "DOMAIN-SUFFIX,example.com\n"}.get
            )
            build.write_outputs([compilation], manifest, root)
            build.write_client_views([compilation], manifest, root)
            removed = build.prune_stale_views([compilation], manifest, root)
            self.assertEqual(len(removed), len(build.CLIENTS))
            self.assertFalse(any(path.is_file() for path in ip_views))
            # The surviving domainset view is untouched.
            self.assertTrue(
                all(
                    (root / client.directory / "Test-domainset.conf").is_file()
                    for client in build.CLIENTS.values()
                )
            )
            self.assertEqual(build.prune_stale_views([compilation], manifest, root), [])

    def test_prune_stale_views_removes_every_view_when_views_disabled(self) -> None:
        source_url = "https://example.invalid/Surge/Test.list"
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            config = app_config(source_format="surge-rule-set", url=source_url)
            config["views"] = True
            manifest = {"version": 1, "apps": {"Test": config}}
            compilation = build.compile_app(
                "Test", config, root, {source_url: "DOMAIN-SUFFIX,example.com\n"}.get
            )
            build.write_client_views([compilation], manifest, root)
            config["views"] = False
            removed = build.prune_stale_views([compilation], manifest, root)
            self.assertEqual(len(removed), len(build.CLIENTS))

    def test_semantic_views_name_the_non_ip_portion_by_its_content(self) -> None:
        # The non-IP portion is emitted once, under one of two names: a pure
        # domain portion becomes `domainset`, anything carrying keyword / UA /
        # PROCESS becomes `nonip`. Never both -- the two need different
        # reference types (DOMAIN-SET vs RULE-SET), so an app publishing both
        # would invite referencing the wrong one, which Surge does not report.
        location = build.SourceLocation("test", 1, ("Test",))
        domain_only = [
            build.Rule("DOMAIN", "api.example.com", (), location),
            build.Rule("DOMAIN-SUFFIX", "example.com", (), location),
        ]
        self.assertEqual([name for name, _ in build.semantic_views(domain_only)], ["domainset"])

        for extra_kind, value in (
            ("DOMAIN-KEYWORD", "example"),
            ("USER-AGENT", "Example App*"),
            ("PROCESS-NAME", "com.example.app"),
        ):
            with self.subTest(extra=extra_kind):
                names = [
                    name
                    for name, _ in build.semantic_views(
                        [*domain_only, build.Rule(extra_kind, value, (), location)]
                    )
                ]
                self.assertEqual(names, ["nonip"])

        # IP always comes last, and a domain-only app gets no empty ip view.
        with_ip = [
            *domain_only,
            build.Rule("IP-CIDR", "192.0.2.0/24", ("no-resolve",), location),
        ]
        self.assertEqual([name for name, _ in build.semantic_views(with_ip)], ["domainset", "ip"])
        self.assertEqual(build.semantic_views([]), [])

    def test_canonicalized_ip_rules_are_reported_not_silent(self) -> None:
        source_url = "https://example.invalid/Surge/Test.list"
        config = app_config(source_format="surge-rule-set", url=source_url)
        result = self.compile(
            config,
            {
                source_url: (
                    # Host bits set: the canonical form widens what upstream wrote.
                    "IP-CIDR,198.51.100.7/24,no-resolve\n"
                    # Bare address and upper-case IPv6: same range, different text.
                    "IP-CIDR,203.0.113.9\n"
                    "IP-CIDR6,2001:DB8::/64,no-resolve\n"
                    # Already canonical: must not be reported.
                    "IP-CIDR,192.0.2.0/24,no-resolve\n"
                )
            },
        )
        self.assertEqual(
            result.rewritten_ip_rules,
            [
                "IP-CIDR,198.51.100.7/24 -> 198.51.100.0/24",
                "IP-CIDR,203.0.113.9 -> 203.0.113.9/32",
                "IP-CIDR6,2001:DB8::/64 -> 2001:db8::/64",
            ],
        )

    def test_canonical_ip_rules_report_nothing(self) -> None:
        source_url = "https://example.invalid/Surge/Test.list"
        config = app_config(source_format="surge-rule-set", url=source_url)
        result = self.compile(
            config,
            {source_url: "IP-CIDR,192.0.2.0/24,no-resolve\nDOMAIN-SUFFIX,example.com\n"},
        )
        self.assertEqual(result.rewritten_ip_rules, [])

    def test_supplement_ip_rewrites_are_reported_too(self) -> None:
        source_url = "https://example.invalid/Surge/Test.list"
        config = app_config(source_format="surge-rule-set", url=source_url)
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            supplement_dir = root / "engine" / "sources" / "supplement"
            supplement_dir.mkdir(parents=True)
            (supplement_dir / "Test.list").write_text(
                "IP-CIDR,198.51.100.7/24,no-resolve\n", encoding="utf-8"
            )
            result = build.compile_app(
                "Test", config, root, {source_url: "DOMAIN-SUFFIX,example.com\n"}.__getitem__
            )
        self.assertEqual(result.rewritten_ip_rules, ["IP-CIDR,198.51.100.7/24 -> 198.51.100.0/24"])

    def test_supplement_stays_strict_despite_type_excludes(self) -> None:
        source_url = "https://example.invalid/Surge/Test.list"
        config = app_config(source_format="surge-rule-set", url=source_url)
        config["exclude"] = ["ip-asn:*"]
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            supplement_dir = root / "engine" / "sources" / "supplement"
            supplement_dir.mkdir(parents=True)
            (supplement_dir / "Test.list").write_text("IP-ASN,11983,no-resolve\n", encoding="utf-8")
            with self.assertRaisesRegex(build.BuildError, "invalid supplement rule"):
                build.compile_app(
                    "Test", config, root, {source_url: "DOMAIN-SUFFIX,example.com\n"}.__getitem__
                )

    def test_fetch_retries_transient_failures(self) -> None:
        class FakeHeaders:
            def get_content_type(self):
                return "text/plain"

        class FakeResponse:
            def __init__(self, body):
                self.headers = FakeHeaders()
                self._body = body

            def read(self):
                return self._body

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

        real_urlopen = build.urllib.request.urlopen
        real_sleep = time.sleep
        calls = []

        def fake_urlopen(request, timeout):
            calls.append(timeout)
            if len(calls) < 3:
                raise TimeoutError("transient network failure")
            return FakeResponse(b"example.com\n")

        build.urllib.request.urlopen = fake_urlopen
        time.sleep = lambda seconds: None
        try:
            text = build.default_fetch_text("https://example.invalid/test.list")
        finally:
            build.urllib.request.urlopen = real_urlopen
            time.sleep = real_sleep
        self.assertEqual(text, "example.com\n")
        self.assertEqual(len(calls), 3)

    def test_cli_supplement_only_app_end_to_end(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            # The provenance manifest fingerprints the builder of the repository
            # being built (what verify_manifest.py resolves), so a fixture repo
            # has to carry it like a real checkout does.
            scripts = Path(__file__).resolve().parents[1] / "scripts"
            builder_dir = root / "engine" / "scripts"
            builder_dir.mkdir(parents=True)
            for name in ("build.py", "renderers.py"):
                (builder_dir / name).write_bytes((scripts / name).read_bytes())
            supplement_dir = root / "engine" / "sources" / "supplement"
            supplement_dir.mkdir(parents=True)
            (supplement_dir / "Demo.list").write_text(
                "DOMAIN-SUFFIX,example.com\n", encoding="utf-8"
            )
            sources_dir = root / "engine" / "sources"
            manifest = sources_dir / "apps.yaml"
            manifest.write_text(
                "version: 1\n"
                "apps:\n"
                "  Demo:\n"
                "    enabled: true\n"
                "    output: Surge/Demo.list\n"
                "    sources: []\n"
                "    include_policy: {mode: explicit, allow: [], deny: []}\n"
                "    attributes: {mode: explicit, include: []}\n"
                "    supplement: engine/sources/supplement/Demo.list\n"
                "    exclude: []\n",
                encoding="utf-8",
            )
            exit_code = build.main(["--manifest", str(manifest), "--app", "Demo", "--write"])
            self.assertEqual(exit_code, 0)
            self.assertEqual(
                (root / "Surge" / "Demo.list").read_text(encoding="utf-8"),
                "# 规则名称: Demo\n# 规则统计: 1\n\nDOMAIN-SUFFIX,example.com\n",
            )


if __name__ == "__main__":
    unittest.main()
