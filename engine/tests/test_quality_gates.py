from __future__ import annotations

import json
import os
import sys
import tempfile as _tempfile
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import build  # noqa: E402
import health_check  # noqa: E402
import parity_check  # noqa: E402
import secret_scan  # noqa: E402
import verify_manifest  # noqa: E402

_WORKSPACE_TMP = Path(__file__).resolve().parents[2] / ".tmp-tests"
_temp_sequence = iter(range(1 << 30))


def _mkdtemp(*_args, **_kwargs):
    _WORKSPACE_TMP.mkdir(exist_ok=True)
    path = _WORKSPACE_TMP / f"q{os.getpid()}_{next(_temp_sequence)}"
    os.mkdir(path)
    return str(path)


_tempfile.mkdtemp = _mkdtemp


def app_config() -> dict:
    return {
        "enabled": True,
        "output": "Surge/Demo.list",
        "sources": [
            {
                "name": "fixture",
                "author": "Blink tests",
                "role": "primary",
                "format": "v2fly-domain-list",
                "url": "https://example.invalid/data/demo",
            }
        ],
        "include_policy": {"mode": "explicit", "allow": [], "deny": []},
        "attributes": {"mode": "explicit", "include": []},
        "supplement": "engine/sources/supplement/Demo.list",
        "exclude": [],
        "note": "test fixture",
    }


def rule(value: str = "example.com") -> build.Rule:
    return build.Rule(
        "DOMAIN-SUFFIX",
        value,
        (),
        build.SourceLocation("fixture", 1, ("Demo",)),
    )


def prepare_repository(root: Path) -> tuple[dict, build.Compilation, dict]:
    builder_dir = root / "engine" / "scripts"
    builder_dir.mkdir(parents=True)
    for name in ("build.py", "renderers.py"):
        (builder_dir / name).write_bytes((SCRIPTS / name).read_bytes())
    source_manifest = {"version": 1, "apps": {"Demo": app_config()}}
    manifest_path = root / "engine" / "sources" / "apps.yaml"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(
        yaml.safe_dump(source_manifest, sort_keys=False), encoding="utf-8", newline="\n"
    )
    rules = [rule()]
    compilation = build.Compilation(
        "Demo",
        rules,
        [],
        [],
        {},
        source_inputs={"https://example.invalid/data/demo": "example.com\n"},
        input_rules=1,
        # compile_app always derives the semantic split; a fixture that skipped it
        # would not describe any real build.
        views=build.semantic_views(rules),
    )
    rendered = build.rendered_outputs(compilation, source_manifest, root)
    build.write_outputs([compilation], source_manifest, root, [rendered])
    provenance = build.build_provenance_manifest(
        [compilation], source_manifest, [rendered], root, preserve_unselected=False
    )
    build.write_provenance(provenance, root)
    return source_manifest, compilation, rendered


class QualityGateTests(unittest.TestCase):
    def test_provenance_and_all_client_parity_pass(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_repository(root)
            self.assertEqual(verify_manifest.check(root)["outputs"], 7)
            report = parity_check.check(root)
            self.assertEqual(report["apps"]["Demo"]["quantumultx"], 1)
            self.assertEqual(health_check.check(root)["apps"]["Demo"]["rules"], 1)

    def test_one_client_injection_breaks_parity_and_checksum(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_repository(root)
            qx = root / "QuantumultX" / "Demo.list"
            qx.write_text(
                qx.read_text(encoding="utf-8") + "HOST-SUFFIX,extra.example,policy\n",
                encoding="utf-8",
            )
            with self.assertRaises(parity_check.ParityError):
                parity_check.check(root)
            with self.assertRaises(verify_manifest.ManifestError):
                verify_manifest.check(root)

    def test_manifest_canonical_checksum_is_recomputed_from_surge(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_repository(root)
            manifest_path = root / build.PROVENANCE_FILENAME
            document = json.loads(manifest_path.read_text(encoding="utf-8"))
            document["apps"]["Demo"]["canonical"]["sha256"] = "0" * 64
            manifest_path.write_text(
                json.dumps(document, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(verify_manifest.ManifestError, "canonical checksum"):
                verify_manifest.check(root)

    def test_duplicate_and_byte_drift_are_detected(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source_manifest, _compilation, rendered = prepare_repository(root)
            surge = root / "Surge" / "Demo.list"
            surge.write_text(
                surge.read_text(encoding="utf-8") + "DOMAIN-SUFFIX,example.com\n",
                encoding="utf-8",
            )
            with self.assertRaises(health_check.HealthError):
                health_check.check(root)
            expected = build.build_provenance_manifest(
                [_compilation], source_manifest, [rendered], root, preserve_unselected=False
            )
            errors = build.verify_rendered_outputs([rendered], expected, root)
            self.assertTrue(any("Surge/Demo.list" in error for error in errors))

    def test_large_semantic_change_is_blocked_before_write(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source_manifest, _compilation, _rendered = prepare_repository(root)
            expanded = build.Compilation(
                "Demo",
                [rule(f"d{index}.example") for index in range(30)],
                [],
                [],
                {},
                input_rules=30,
            )
            report, violations = build.assess_changes(
                [expanded],
                source_manifest,
                root,
                threshold_lines=20,
                threshold_ratio=0.2,
            )
            self.assertEqual(report[0]["added"], 30)
            self.assertTrue(violations)

    def test_refresh_provenance_only_changes_builder_fingerprints(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source_manifest, _compilation, _rendered = prepare_repository(root)
            manifest_path = root / build.PROVENANCE_FILENAME
            before = json.loads(manifest_path.read_text(encoding="utf-8"))

            # An edit that does not change any output still invalidates the
            # recorded builder checksum, which is what fails verify_manifest.
            builder = root / "engine" / "scripts" / "build.py"
            builder.write_bytes(builder.read_bytes() + b"\n# provenance-only edit\n")
            with self.assertRaisesRegex(verify_manifest.ManifestError, "builder checksum"):
                verify_manifest.check(root)

            document = build.refresh_provenance(source_manifest, root)
            build.write_provenance(document, root)
            after = json.loads(manifest_path.read_text(encoding="utf-8"))

            # Everything derived from upstream or from the committed artifacts is
            # reproduced offline; only the builder fingerprint moves.
            self.assertNotEqual(
                before["builder"]["files"]["engine/scripts/build.py"],
                after["builder"]["files"]["engine/scripts/build.py"],
            )
            before["builder"]["files"]["engine/scripts/build.py"] = after["builder"]["files"][
                "engine/scripts/build.py"
            ]
            self.assertEqual(before, after)
            self.assertEqual(verify_manifest.check(root)["outputs"], 7)

    def test_refresh_provenance_refuses_when_an_output_drifted(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source_manifest, _compilation, _rendered = prepare_repository(root)
            qx = root / "QuantumultX" / "Demo.list"
            qx.write_text(
                qx.read_text(encoding="utf-8") + "HOST-SUFFIX,extra.example,policy\n",
                encoding="utf-8",
            )
            # A refresh must never paper over a real rendering change: the
            # committed output no longer matches what the renderers produce.
            with self.assertRaisesRegex(build.BuildError, "run a full --write"):
                build.refresh_provenance(source_manifest, root)

    def test_refresh_provenance_refuses_an_undeclared_upstream(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source_manifest, _compilation, _rendered = prepare_repository(root)
            # A new upstream means the content changed, so its fingerprint cannot
            # be carried over from the previous manifest.
            source_manifest["apps"]["Demo"]["sources"][0]["url"] = (
                "https://example.invalid/data/new"
            )
            with self.assertRaisesRegex(build.BuildError, "no recorded fingerprint"):
                build.refresh_provenance(source_manifest, root)

    def test_refresh_provenance_carries_upstream_only_counters(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source_manifest, _compilation, _rendered = prepare_repository(root)
            manifest_path = root / build.PROVENANCE_FILENAME
            document = json.loads(manifest_path.read_text(encoding="utf-8"))
            canonical = document["apps"]["Demo"]["canonical"]
            canonical["input_rules"] = 9
            canonical["skipped_excluded"] = ["IP-ASN,64500"]
            canonical["denied_includes"] = ["npmjs"]
            canonical["excluded_domains"] = {"domain-suffix:cdn.example": 3}
            # The recorded exclude set has to match apps.yaml, otherwise the
            # dedicated guard (tested separately) rejects the refresh.
            source_manifest["apps"]["Demo"]["exclude"] = ["domain-suffix:cdn.example"]
            manifest_path.write_text(
                json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
                newline="\n",
            )
            refreshed = build.refresh_provenance(source_manifest, root)["apps"]["Demo"]["canonical"]
            # Counters only a live fetch can establish must survive the refresh
            # rather than being silently reset to zero.
            self.assertEqual(refreshed["input_rules"], 9)
            self.assertEqual(refreshed["skipped_excluded"], ["IP-ASN,64500"])
            self.assertEqual(refreshed["denied_includes"], ["npmjs"])
            self.assertEqual(refreshed["excluded_domains"], {"domain-suffix:cdn.example": 3})

    def test_refresh_provenance_refuses_a_changed_exclude_declaration(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source_manifest, _compilation, _rendered = prepare_repository(root)
            manifest_path = root / build.PROVENANCE_FILENAME
            document = json.loads(manifest_path.read_text(encoding="utf-8"))
            document["apps"]["Demo"]["canonical"]["excluded_domains"] = {
                "domain-suffix:cdn.example": 1
            }
            manifest_path.write_text(
                json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
                newline="\n",
            )
            source_manifest["apps"]["Demo"]["exclude"] = ["domain-suffix:other.example"]
            with self.assertRaisesRegex(build.BuildError, "different domain excludes"):
                build.refresh_provenance(source_manifest, root)

    def test_secret_scan_reports_location_without_echoing_secret(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            token = "ghp_" + "A" * 40
            (root / "unsafe.txt").write_text(token, encoding="utf-8")
            with self.assertRaises(secret_scan.SecretScanError) as raised:
                secret_scan.scan(root)
            self.assertIn("unsafe.txt:1", str(raised.exception))
            self.assertNotIn(token, str(raised.exception))

    def test_secret_scan_covers_extensionless_key_and_pem_files(self) -> None:
        fixtures = {
            ".env": "AKIA" + "A" * 16,
            "certificate.pem": "-----BEGIN " + "PRIVATE KEY-----",
            "service.key": "ghp_" + "A" * 40,
        }
        for filename, value in fixtures.items():
            with self.subTest(filename=filename), TemporaryDirectory() as directory:
                root = Path(directory)
                (root / filename).write_text(value, encoding="utf-8")
                with self.assertRaises(secret_scan.SecretScanError):
                    secret_scan.scan(root)

    def test_secret_scan_covers_local_paths_and_opaque_subscriptions(self) -> None:
        fixtures = {
            "forward-path.txt": "C:" + "/Users/Alice/private/config.txt",
            "backward-path.txt": "D:" + "\\Private\\profile.txt",
            "subscription.txt": "https://example.invalid/sub/" + "abcdefghijklmnop",
        }
        for filename, value in fixtures.items():
            with self.subTest(filename=filename), TemporaryDirectory() as directory:
                root = Path(directory)
                (root / filename).write_text(value, encoding="utf-8")
                with self.assertRaises(secret_scan.SecretScanError):
                    secret_scan.scan(root)

    def test_secret_scan_allows_documented_local_path_placeholder(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "safe.md").write_text(r"C:\Users\<username>\file", encoding="utf-8")
            self.assertEqual(secret_scan.scan(root)["hits"], 0)

    def test_placeholder_does_not_hide_a_second_real_local_path(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            text = r"placeholder C:\Users\<username>\file; actual " + "D:" + r"\Private\file"
            (root / "unsafe.md").write_text(text, encoding="utf-8")
            with self.assertRaises(secret_scan.SecretScanError):
                secret_scan.scan(root)


if __name__ == "__main__":
    unittest.main()
