#!/usr/bin/env python3
"""Verify Profiles/ are reproducible from intent/templates and local Blink references exist."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import build_profile

BLINK_RAW = re.compile(
    r"https://raw\.githubusercontent\.com/byyoshen/Blink/main/"
    r"(Surge|Loon|Shadowrocket|Stash|Clash|Egern|QuantumultX)/"
    r"([A-Za-z0-9._-]+\.(?:list|yaml|conf))"
)
PLACEHOLDER = "https://YOUR-SUBSCRIPTION-URL"
APP_MANAGED_SUBSCRIPTION_CLIENTS = {"shadowrocket", "loon", "quantumultx"}


class ProfileVerificationError(RuntimeError):
    """A generated Profile drifted from intent or references an invalid local rule path."""


def check(root: Path) -> dict:
    intent_path = root / "engine" / "sources" / "profile" / "intent.yaml"
    template_dir = root / "engine" / "sources" / "profile" / "templates"
    output_dir = root / "Profiles"

    original = (
        build_profile.INTENT_PATH,
        build_profile.TEMPLATE_DIR,
        build_profile.OUTPUT_DIR,
    )
    build_profile.INTENT_PATH = intent_path
    build_profile.TEMPLATE_DIR = template_dir
    build_profile.OUTPUT_DIR = output_dir
    try:
        intent = build_profile.load_intent(intent_path)
        build_profile.validate_intent(intent)
        if intent.get("subscription", {}).get("url") != PLACEHOLDER:
            raise ProfileVerificationError(
                "intent subscription URL must remain the public placeholder"
            )
        expected = {
            client: build_profile.render_client(client, intent) for client in build_profile.CLIENTS
        }
    finally:
        (
            build_profile.INTENT_PATH,
            build_profile.TEMPLATE_DIR,
            build_profile.OUTPUT_DIR,
        ) = original

    expected_names = {output_name for _template, output_name in build_profile.CLIENTS.values()}
    actual_names = {path.name for path in output_dir.iterdir() if path.is_file()}
    if actual_names != expected_names:
        raise ProfileVerificationError(
            f"Profiles file set mismatch; missing={sorted(expected_names - actual_names)}, "
            f"extra={sorted(actual_names - expected_names)}"
        )

    references = set()
    for client, text in expected.items():
        _template, output_name = build_profile.CLIENTS[client]
        path = output_dir / output_name
        actual = path.read_text(encoding="utf-8")
        if actual != text:
            raise ProfileVerificationError(
                f"{path}: drifted from intent/templates; regenerate with build_profile.py --write"
            )
        if PLACEHOLDER not in actual:
            raise ProfileVerificationError(
                f"{path}: generated profile must expose the public subscription placeholder"
            )
        if client in APP_MANAGED_SUBSCRIPTION_CLIENTS and "ADAPTED" not in actual:
            raise ProfileVerificationError(
                f"{path}: App-managed subscription mapping must be marked ADAPTED"
            )
        for directory, filename in BLINK_RAW.findall(text):
            relative = f"{directory}/{filename}"
            target = root / relative
            if not target.is_file() or target.stat().st_size == 0:
                raise ProfileVerificationError(
                    f"{path}: missing or empty Blink reference {relative}"
                )
            references.add(relative)

    return {
        "profiles": len(expected),
        "blink_rule_references": len(references),
        "subscription_placeholder": intent["subscription"]["url"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    arguments = parser.parse_args(argv)
    try:
        print(json.dumps(check(arguments.root.resolve()), ensure_ascii=False, indent=2))
        return 0
    except (ProfileVerificationError, build_profile.ProfileError, OSError) as error:
        print(f"profile verification failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
