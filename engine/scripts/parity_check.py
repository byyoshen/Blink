#!/usr/bin/env python3
"""Verify the documented semantic relationship among all generated clients."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

import yaml

import build
import renderers

HEADER_NAME = re.compile(r"^# 规则名称:\s*(.+?)\s*$")
HEADER_COUNT = re.compile(r"^# 规则统计:\s*(\d+)\s*$")
EGERN_TYPES = {
    "domain_set": "DOMAIN",
    "domain_suffix_set": "DOMAIN-SUFFIX",
    "domain_keyword_set": "DOMAIN-KEYWORD",
    "ip_cidr_set": "IP-CIDR",
    "ip_cidr6_set": "IP-CIDR6",
    "user_agent_set": "USER-AGENT",
}
QX_TYPES = {value: key for key, value in renderers.QUANTUMULTX_TYPES.items()}


class ParityError(RuntimeError):
    """A generated client output violates the declared compatibility matrix."""


def read_header(path: Path) -> tuple[str, int]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise ParityError(f"cannot read {path}: {error}") from error
    name = None
    count = None
    for line in lines[:5]:
        if match := HEADER_NAME.match(line):
            name = match.group(1)
        if match := HEADER_COUNT.match(line):
            count = int(match.group(1))
    if name is None or count is None:
        raise ParityError(f"{path}: missing generated name/count header")
    return name, count


def parse_classical(path: Path, app_name: str) -> list[tuple[str, str, tuple[str, ...]]]:
    try:
        text = path.read_text(encoding="utf-8-sig")
        rules = build.parse_surge_rule_set_text(text, str(path), (app_name, path.parent.name))
    except (OSError, build.BuildError) as error:
        raise ParityError(f"{path}: invalid classical output: {error}") from error
    return [rule.key for rule in rules]


def parse_egern(path: Path) -> list[tuple[str, str, tuple[str, ...]]]:
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise ParityError(f"{path}: invalid YAML: {error}") from error
    if not isinstance(document, dict):
        raise ParityError(f"{path}: Egern output must be a mapping")
    unknown = set(document) - ({"no_resolve"} | set(EGERN_TYPES))
    if unknown:
        raise ParityError(f"{path}: unknown Egern keys: {sorted(unknown)}")
    no_resolve = document.get("no_resolve", False)
    if not isinstance(no_resolve, bool):
        raise ParityError(f"{path}: no_resolve must be boolean")
    rules = []
    for key, kind in EGERN_TYPES.items():
        values = document.get(key, [])
        if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
            raise ParityError(f"{path}: {key} must be a string list")
        options = ("no-resolve",) if no_resolve and kind in {"IP-CIDR", "IP-CIDR6"} else ()
        rules.extend((kind, value, options) for value in values)
    return rules


def parse_quantumultx(path: Path) -> list[tuple[str, str, tuple[str, ...]]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise ParityError(f"cannot read {path}: {error}") from error
    rules = []
    for number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = [part.strip() for part in stripped.split(",")]
        if len(parts) != 3 or parts[0] not in QX_TYPES:
            raise ParityError(f"{path}:{number}: invalid Quantumult X filter line")
        if parts[2] != renderers.QUANTUMULTX_POLICY_PLACEHOLDER:
            raise ParityError(f"{path}:{number}: policy placeholder must be literal 'policy'")
        rules.append((QX_TYPES[parts[0]], parts[1], ()))
    return rules


def assert_multiset(
    app_name: str,
    client: str,
    actual: list[tuple[str, str, tuple[str, ...]]],
    expected: list[tuple[str, str, tuple[str, ...]]],
) -> None:
    actual_counter = Counter(actual)
    expected_counter = Counter(expected)
    if actual_counter == expected_counter:
        return
    missing = list((expected_counter - actual_counter).elements())[:5]
    extra = list((actual_counter - expected_counter).elements())[:5]
    raise ParityError(f"{app_name}/{client}: semantic mismatch; missing={missing}, extra={extra}")


def expected_paths(root: Path, apps: dict) -> dict[str, set[Path]]:
    paths = {key: set() for key in build.CLIENTS}
    for app in apps.values():
        surge = root / app["output"]
        for key, client in build.CLIENTS.items():
            path = (
                surge
                if key == "surge"
                else root / client.directory / f"{surge.stem}{client.suffix}"
            )
            paths[key].add(path.resolve())
    return paths


def check(root: Path) -> dict:
    manifest = build.load_manifest(root / "engine" / "sources" / "apps.yaml")
    apps = {name: app for name, app in manifest["apps"].items() if app["enabled"]}
    paths_by_client = expected_paths(root, apps)
    for key, client in build.CLIENTS.items():
        directory = root / client.directory
        actual = {path.resolve() for path in directory.glob(f"*{client.suffix}")}
        missing = sorted(str(path) for path in paths_by_client[key] - actual)
        extra = sorted(str(path) for path in actual - paths_by_client[key])
        if missing or extra:
            raise ParityError(
                f"{client.directory}: file set mismatch; missing={missing}, extra={extra}"
            )

    report = {"apps": {}}
    for app_name, app in apps.items():
        surge_path = root / app["output"]
        classical_paths = [
            surge_path,
            root / "Loon" / surge_path.name,
            root / "Shadowrocket" / surge_path.name,
            root / "Stash" / surge_path.name,
        ]
        surge_bytes = surge_path.read_bytes()
        for path in classical_paths[1:]:
            if path.read_bytes() != surge_bytes:
                raise ParityError(f"{app_name}: {path.parent.name} is not byte-identical to Surge")

        surge = parse_classical(surge_path, app_name)
        if not surge:
            raise ParityError(f"{app_name}: canonical output is empty")
        client_counts = {}
        for path in classical_paths:
            name, count = read_header(path)
            if name != app_name or count != len(surge):
                raise ParityError(f"{path}: header metadata does not match its body")
            client_counts[path.parent.name.lower()] = count

        mihomo_path = root / "mihomo" / surge_path.name
        mihomo = parse_classical(mihomo_path, app_name)
        mihomo_expected = [rule for rule in surge if rule[0] != "USER-AGENT"]
        assert_multiset(app_name, "mihomo", mihomo, mihomo_expected)

        egern_path = root / "Egern" / f"{surge_path.stem}.yaml"
        egern = parse_egern(egern_path)
        egern_expected = [rule for rule in surge if rule[0] != "PROCESS-NAME"]
        assert_multiset(app_name, "egern", egern, egern_expected)

        qx_path = root / "QuantumultX" / surge_path.name
        qx = parse_quantumultx(qx_path)
        qx_expected = [
            (kind, value, ()) for kind, value, _options in surge if kind != "PROCESS-NAME"
        ]
        assert_multiset(app_name, "quantumultx", qx, qx_expected)

        for key, path, rules in (
            ("mihomo", mihomo_path, mihomo),
            ("egern", egern_path, egern),
            ("quantumultx", qx_path, qx),
        ):
            name, count = read_header(path)
            if name != app_name or count != len(rules):
                raise ParityError(f"{path}: header metadata does not match its body")
            client_counts[key] = count
        report["apps"][app_name] = client_counts
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument(
        "--strict", action="store_true", help="compatibility alias; checks are strict"
    )
    arguments = parser.parse_args(argv)
    try:
        print(json.dumps(check(arguments.root.resolve()), ensure_ascii=False, indent=2))
        return 0
    except (ParityError, build.BuildError, OSError) as error:
        print(f"parity check failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
