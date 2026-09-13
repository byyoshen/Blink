#!/usr/bin/env python3
"""Validate the semantic multi-view outputs against the canonical rules.

Each view (`domainset` / `nonip` / `ip`) must be semantically consistent with
the canonical rule set:

- ``domainset`` only ever carries ``DOMAIN`` / ``DOMAIN-SUFFIX`` (a pure-domain
  view); it must never contain DOMAIN-KEYWORD, USER-AGENT, PROCESS-NAME or any
  IP rule.
- ``nonip`` never carries an IP rule (IP lives in the later ``ip`` phase).
- ``ip`` only ever carries ``IP-CIDR`` / ``IP-CIDR6`` (with their no-resolve
  option); domain rules must never leak into it.
- A domain-only app must not produce a spurious empty ``ip`` view, and an app
  that has IP rules must carry the ``ip`` view on every client.
- The Surge view payload must be byte-semantically identical to the canonical
  split (no dropped or duplicated rules), and every client view file must be
  present, non-empty, and report a header count that matches its phase.

Run offline: only the committed repo is inspected.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

import build

HEADER_COUNT = re.compile(r"^# 规则统计:\s*(\d+)\s*$")

# Allowed canonical kinds per view phase.
VIEW_KINDS = {
    "domainset": frozenset({"DOMAIN", "DOMAIN-SUFFIX"}),
    "nonip": frozenset({"DOMAIN", "DOMAIN-SUFFIX", "DOMAIN-KEYWORD", "USER-AGENT", "PROCESS-NAME"}),
    "ip": frozenset({"IP-CIDR", "IP-CIDR6"}),
}


class ViewsError(RuntimeError):
    """A semantic view output violates the domain-first / IP-last invariants."""


def _header_count(path: Path) -> int:
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            match = HEADER_COUNT.match(line)
            if match:
                return int(match.group(1))
    except OSError as error:
        raise ViewsError(f"cannot read {path}: {error}") from error
    raise ViewsError(f"{path}: missing 规则统计 header")


def _parse_surge_domainset(path: Path, context: str) -> list[tuple[str, str, tuple[str, ...]]]:
    """Parse a Surge DOMAIN-SET payload (bare domain / ``.+suffix``)."""
    rules: list[tuple[str, str, tuple[str, ...]]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise ViewsError(f"cannot read {path}: {error}") from error
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("."):
            rules.append(("DOMAIN-SUFFIX", stripped[1:], ()))
        else:
            rules.append(("DOMAIN", stripped, ()))
    if not rules:
        raise ViewsError(f"{context}: domainset payload is empty")
    return rules


def _dropped_for_client(client_key: str, rules: list[object]) -> int:
    """Rules the client cannot express (mirrors the renderer's explicit drops)."""
    if client_key == "mihomo":
        return sum(1 for rule in rules if rule.kind == "USER-AGENT")
    if client_key in {"egern", "quantumultx"}:
        return sum(1 for rule in rules if rule.kind == "PROCESS-NAME")
    return 0


def check_views(root: Path) -> dict:
    manifest = build.load_manifest(root / "engine" / "sources" / "apps.yaml")
    report = {"apps": {}}
    for app_name, app in manifest["apps"].items():
        if not app.get("enabled"):
            continue
        if not app.get("views"):
            continue
        surge_path = root / app["output"]
        canonical = build.parse_surge_rule_set_text(
            surge_path.read_text(encoding="utf-8"), str(surge_path), (app_name, "views-check")
        )
        if not canonical:
            raise ViewsError(f"{app_name}: canonical output is empty")
        expected = build.semantic_views(canonical)
        expected_map = {name: list(rules) for name, rules in expected}
        present_names = set(expected_map)

        for view_name, view_rules in expected:
            kinds = {rule.kind for rule in view_rules}
            disallowed = kinds - VIEW_KINDS[view_name]
            if disallowed:
                raise ViewsError(
                    f"{app_name}/{view_name}: disallowed rule kinds {sorted(disallowed)}"
                )

            # Surge (reference client): byte-semantic equality with the canonical split.
            surge_view = root / "Surge" / f"{app_name}-{view_name}.conf"
            if not surge_view.is_file():
                raise ViewsError(f"{app_name}/{view_name}: missing Surge view file")
            if view_name == "domainset":
                actual = _parse_surge_domainset(surge_view, f"{app_name}/{view_name}")
                expected_keys = [(rule.kind, rule.value, ()) for rule in view_rules]
            else:
                actual = [
                    rule.key
                    for rule in build.parse_surge_rule_set_text(
                        surge_view.read_text(encoding="utf-8"),
                        str(surge_view),
                        (app_name, "views-check"),
                    )
                ]
                expected_keys = [rule.key for rule in view_rules]
            if Counter(actual) != Counter(expected_keys):
                raise ViewsError(
                    f"{app_name}/{view_name}: Surge view payload differs from canonical split"
                )

            # Every client must carry a non-empty view whose header count matches
            # the phase after the client's explicit drops.
            for client_key, client in build.CLIENTS.items():
                vpath = root / client.directory / f"{app_name}-{view_name}.conf"
                if not vpath.is_file() or vpath.stat().st_size == 0:
                    raise ViewsError(f"{app_name}/{view_name}: missing/empty in {client.directory}")
                expected_count = len(view_rules) - _dropped_for_client(client_key, view_rules)
                if _header_count(vpath) != expected_count:
                    raise ViewsError(
                        f"{app_name}/{view_name}: header count mismatch in {client.directory} "
                        f"({_header_count(vpath)} != {expected_count})"
                    )

        # No spurious view files (e.g. an ip view on a domain-only app).
        for _client_key, client in build.CLIENTS.items():
            for view_name in ("domainset", "nonip", "ip"):
                vpath = root / client.directory / f"{app_name}-{view_name}.conf"
                exists = vpath.is_file()
                if view_name in present_names and not exists:
                    raise ViewsError(f"{app_name}/{view_name}: missing in {client.directory}")
                if view_name not in present_names and exists:
                    raise ViewsError(f"{app_name}/{view_name}: spurious in {client.directory}")

        report["apps"][app_name] = {name: len(rules) for name, rules in expected_map.items()}
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    arguments = parser.parse_args(argv)
    try:
        print(json.dumps(check_views(arguments.root.resolve()), ensure_ascii=False, indent=2))
        return 0
    except (ViewsError, build.BuildError) as error:
        print(f"views check failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
