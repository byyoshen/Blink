#!/usr/bin/env python3
"""Verify deterministic provenance and SHA256 coverage for generated artifacts."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import build

SHA256 = re.compile(r"^[0-9a-f]{64}$")


class ManifestError(RuntimeError):
    """The provenance manifest is incomplete, stale, or malformed."""


def require_sha256(value: object, context: str) -> str:
    if not isinstance(value, str) or not SHA256.fullmatch(value):
        raise ManifestError(f"{context}: expected lowercase SHA256")
    return value


def safe_path(root: Path, value: object, context: str) -> Path:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ManifestError(f"{context}: expected a repository-relative POSIX path")
    path = (root / value).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as error:
        raise ManifestError(f"{context}: path escapes repository root") from error
    return path


def verify_file(root: Path, record: object, context: str) -> Path:
    if not isinstance(record, dict):
        raise ManifestError(f"{context}: expected a mapping")
    path = safe_path(root, record.get("path"), f"{context}.path")
    expected = require_sha256(record.get("sha256"), f"{context}.sha256")
    if not path.is_file():
        raise ManifestError(f"{context}: missing file {path}")
    actual = build.sha256_bytes(path.read_bytes())
    if actual != expected:
        raise ManifestError(f"{context}: checksum mismatch for {path}")
    return path


def check(root: Path) -> dict:
    provenance_path = root / build.PROVENANCE_FILENAME
    try:
        document = json.loads(provenance_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ManifestError(f"cannot read {provenance_path}: {error}") from error
    if not isinstance(document, dict) or document.get("schema_version") != 1:
        raise ManifestError("manifest.json must use schema_version 1")

    source_manifest = build.load_manifest(root / "engine" / "sources" / "apps.yaml")
    enabled = {
        name: app for name, app in source_manifest["apps"].items() if app.get("enabled") is True
    }
    records = document.get("apps")
    if not isinstance(records, dict) or set(records) != set(enabled):
        raise ManifestError("manifest app set does not equal enabled apps.yaml entries")

    source_definition = document.get("source_definition")
    source_path = verify_file(root, source_definition, "source_definition")
    expected_source_path = (root / "engine" / "sources" / "apps.yaml").resolve()
    if source_path != expected_source_path:
        raise ManifestError("source_definition must point to engine/sources/apps.yaml")

    builder = document.get("builder")
    if not isinstance(builder, dict) or builder.get("version") != build.BUILDER_VERSION:
        raise ManifestError("builder version does not match the current build.py")
    builder_files = builder.get("files")
    if not isinstance(builder_files, dict):
        raise ManifestError("builder.files must be a mapping")
    expected_builder_paths = {"engine/scripts/build.py", "engine/scripts/renderers.py"}
    if set(builder_files) != expected_builder_paths:
        raise ManifestError("builder.files must cover build.py and renderers.py exactly")
    for relative, expected in builder_files.items():
        expected = require_sha256(expected, f"builder.files.{relative}")
        path = safe_path(root, relative, f"builder.files.{relative}")
        if not path.is_file() or build.sha256_bytes(path.read_bytes()) != expected:
            raise ManifestError(f"builder checksum mismatch for {relative}")

    verified_outputs = 0
    verified_sources = 0
    for app_name, app in enabled.items():
        record = records[app_name]
        if not isinstance(record, dict):
            raise ManifestError(f"{app_name}: record must be a mapping")

        sources = record.get("sources")
        if not isinstance(sources, list):
            raise ManifestError(f"{app_name}: sources must be a list")
        declared_urls = {source["url"] for source in app["sources"]}
        recorded_urls = set()
        for index, source in enumerate(sources):
            context = f"{app_name}.sources[{index}]"
            if not isinstance(source, dict) or not isinstance(source.get("url"), str):
                raise ManifestError(f"{context}: invalid source record")
            url = source["url"]
            if not url.startswith("https://") or url in recorded_urls:
                raise ManifestError(f"{context}: source URL must be unique HTTPS")
            recorded_urls.add(url)
            require_sha256(source.get("text_sha256"), f"{context}.text_sha256")
            if not isinstance(source.get("bytes"), int) or source["bytes"] < 0:
                raise ManifestError(f"{context}.bytes: expected a non-negative integer")
            if not isinstance(source.get("lines"), int) or source["lines"] < 0:
                raise ManifestError(f"{context}.lines: expected a non-negative integer")
            verified_sources += 1
        if not declared_urls.issubset(recorded_urls):
            raise ManifestError(f"{app_name}: not every declared upstream was fingerprinted")

        supplement = record.get("supplement")
        supplement_path = root / app["supplement"]
        if supplement_path.exists():
            verified = verify_file(root, supplement, f"{app_name}.supplement")
            if verified != supplement_path.resolve():
                raise ManifestError(f"{app_name}: supplement path differs from apps.yaml")
        elif supplement is not None:
            raise ManifestError(f"{app_name}: records a supplement that does not exist")

        canonical = record.get("canonical")
        if not isinstance(canonical, dict):
            raise ManifestError(f"{app_name}: canonical must be a mapping")
        canonical_sha256 = require_sha256(canonical.get("sha256"), f"{app_name}.canonical.sha256")
        canonical_count = canonical.get("rules")
        if not isinstance(canonical_count, int) or canonical_count <= 0:
            raise ManifestError(f"{app_name}: canonical rules must be positive")

        # Optional: hits per declared domain exclude.  Absent on records written
        # before the accounting existed, and on apps that declare no domain
        # exclude; present records must cover exactly the declared specs.
        excluded_domains = canonical.get("excluded_domains")
        if excluded_domains is not None:
            if not isinstance(excluded_domains, dict) or not all(
                isinstance(hits, int) and hits >= 0 for hits in excluded_domains.values()
            ):
                raise ManifestError(
                    f"{app_name}.canonical.excluded_domains: expected spec -> non-negative count"
                )
            declared_domain_excludes = {
                item for item in app["exclude"] if isinstance(item, str) and not item.endswith(":*")
            }
            if set(excluded_domains) != declared_domain_excludes:
                raise ManifestError(f"{app_name}: recorded domain excludes do not match apps.yaml")

        surge_path = root / app["output"]
        if not surge_path.is_file():
            raise ManifestError(f"{app_name}: missing canonical Surge output {surge_path}")
        surge_rules = build.parse_surge_rule_set_text(
            surge_path.read_text(encoding="utf-8"),
            surge_path.relative_to(root).as_posix(),
            (app_name, "manifest-verification"),
        )
        if len(surge_rules) != canonical_count:
            raise ManifestError(
                f"{app_name}: canonical rule count does not match verified Surge output"
            )
        if build.canonical_rules_sha256(surge_rules) != canonical_sha256:
            raise ManifestError(
                f"{app_name}: canonical checksum does not match verified Surge output"
            )

        outputs = record.get("outputs")
        if not isinstance(outputs, dict) or set(outputs) != set(build.CLIENTS):
            raise ManifestError(f"{app_name}: outputs must cover all seven clients")
        for client, output in outputs.items():
            path = verify_file(root, output, f"{app_name}.outputs.{client}")
            target = build.CLIENTS[client]
            surge = root / app["output"]
            expected = (
                surge
                if client == "surge"
                else root / target.directory / f"{surge.stem}{target.suffix}"
            )
            if path != expected.resolve():
                raise ManifestError(f"{app_name}/{client}: output path differs from apps.yaml")
            rules = output.get("rules")
            dropped = output.get("dropped")
            if not isinstance(rules, int) or rules <= 0 or not isinstance(dropped, list):
                raise ManifestError(f"{app_name}/{client}: invalid rules/dropped metadata")
            if rules + len(dropped) != canonical_count:
                raise ManifestError(f"{app_name}/{client}: rules + dropped != canonical count")
            verified_outputs += 1

        views = record.get("views")
        if views is not None:
            if not isinstance(views, dict):
                raise ManifestError(f"{app_name}: views must be a mapping")
            for client_key, client_views in views.items():
                if client_key not in build.CLIENTS:
                    raise ManifestError(f"{app_name}: unknown client in views {client_key!r}")
                if not isinstance(client_views, dict):
                    raise ManifestError(f"{app_name}.views.{client_key}: must be a mapping")
                for view_name, view in client_views.items():
                    context = f"{app_name}.views.{client_key}.{view_name}"
                    if view_name not in build.VIEW_TYPES:
                        raise ManifestError(f"{app_name}: unknown view {view_name!r}")
                    view_path = verify_file(root, view, context)
                    directory = build.CLIENTS[client_key].directory
                    expected_view = (root / directory / f"{app_name}-{view_name}.conf").resolve()
                    if view_path != expected_view:
                        raise ManifestError(
                            f"{app_name}/{client_key}/{view_name}: view path differs from convention"
                        )
                    if not isinstance(view.get("rules"), int) or view["rules"] <= 0:
                        raise ManifestError(f"{context}: invalid rules metadata")

    return {
        "apps": len(enabled),
        "sources": verified_sources,
        "outputs": verified_outputs,
        "manifest": build.PROVENANCE_FILENAME,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    arguments = parser.parse_args(argv)
    try:
        print(json.dumps(check(arguments.root.resolve()), ensure_ascii=False, indent=2))
        return 0
    except (ManifestError, build.BuildError) as error:
        print(f"manifest verification failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
