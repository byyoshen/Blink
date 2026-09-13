#!/usr/bin/env python3
"""Generate engine/portal/public/data/stats.json for the portal.

Reads the generated client outputs plus the source manifest and writes a
small JSON document consumed by the Vite + React portal.  The output contains
only data derived from those inputs — no timestamps — so it changes exactly
when the generated outputs or the manifest change, and the daily workflow
commits it together with the generated rules.

Surge/*.list stays the canonical count and type source; the classical
clients (Surge / Loon / Shadowrocket / Stash) share byte-identical files,
while mihomo/*.list is the same body minus USER-AGENT (Clash kernels have
no such rule type) and Egern/*.yaml is rendered from the same canonical
rules and may explicitly drop PROCESS-NAME lines (recorded as ``dropped``).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

import yaml

import repo_identity

REPO = repo_identity.REPO_URL
RAW_BASE = repo_identity.RAW_BASE

# Display-only portal metadata.  Source logic lives in the manifest; this
# mapping only groups apps for the portal and suggests a policy label for the
# copyable reference line.  The last field is always the user's own choice.
# ``icon`` points at the official App Store artwork stored under
# engine/portal/public/app-icons/ (AI uses the ChatGPT logo by request).
PORTAL_META = {
    "OKX": {"category": "Finance", "emoji": "💠", "policy": "Finance", "icon": "app-icons/OKX.jpg"},
    "PayPal": {
        "category": "Finance",
        "emoji": "💸",
        "policy": "Finance",
        "icon": "app-icons/PayPal.jpg",
    },
    "SafePal": {
        "category": "Finance",
        "emoji": "🔐",
        "policy": "Finance",
        "icon": "app-icons/SafePal.jpg",
    },
    "ZABank": {
        "category": "Finance",
        "emoji": "🏦",
        "policy": "Finance",
        "icon": "app-icons/ZABank.jpg",
    },
    "WhatsApp": {
        "category": "Communication",
        "emoji": "💬",
        "policy": "Proxy",
        "icon": "app-icons/WhatsApp.jpg",
    },
    "LINE": {
        "category": "Communication",
        "emoji": "💬",
        "policy": "Proxy",
        "icon": "app-icons/LINE.jpg",
    },
    "Telegram": {
        "category": "Communication",
        "emoji": "✈️",
        "policy": "Proxy",
        "icon": "app-icons/Telegram.jpg",
    },
    "GitHub": {
        "category": "Development",
        "emoji": "🐙",
        "policy": "GitHub",
        "icon": "app-icons/GitHub.jpg",
    },
    "AWSConsole": {
        "category": "Development",
        "emoji": "☁️",
        "policy": "Development",
        "icon": "app-icons/AWSConsole.jpg",
    },
    "Steam": {
        "category": "Gaming",
        "emoji": "🎮",
        "policy": "Proxy",
        "icon": "app-icons/Steam.jpg",
    },
    "X": {"category": "Social", "emoji": "𝕏", "policy": "Proxy", "icon": "app-icons/X.jpg"},
    "Instagram": {
        "category": "Social",
        "emoji": "📷",
        "policy": "Proxy",
        "icon": "app-icons/Instagram.jpg",
    },
    "Threads": {
        "category": "Social",
        "emoji": "🧵",
        "policy": "Proxy",
        "icon": "app-icons/Threads.jpg",
    },
    "Facebook": {
        "category": "Social",
        "emoji": "📘",
        "policy": "Proxy",
        "icon": "app-icons/Facebook.jpg",
    },
    "YouTube": {
        "category": "Media",
        "emoji": "▶️",
        "policy": "Media",
        "icon": "app-icons/YouTube.jpg",
    },
    "Netflix": {
        "category": "Media",
        "emoji": "🎬",
        "policy": "Media",
        "icon": "app-icons/Netflix.jpg",
    },
    "TikTok": {
        "category": "Media",
        "emoji": "🎵",
        "policy": "Proxy",
        "icon": "app-icons/TikTok.jpg",
    },
    "Spotify": {
        "category": "Media",
        "emoji": "🎧",
        "policy": "Proxy",
        "icon": "app-icons/Spotify.jpg",
    },
    "APTV": {
        "category": "Media",
        "emoji": "📺",
        "policy": "Media",
        "icon": "app-icons/APTV.jpg",
        "self_use": True,
    },
    "Disney": {
        "category": "Media",
        "emoji": "🏰",
        "policy": "Media",
        "icon": "app-icons/Disney.jpg",
    },
    "ParamountPlus": {
        "category": "Media",
        "emoji": "🎞️",
        "policy": "Media",
        "icon": "app-icons/ParamountPlus.jpg",
    },
    "PrimeVideo": {
        "category": "Media",
        "emoji": "📦",
        "policy": "Media",
        "icon": "app-icons/PrimeVideo.jpg",
    },
    "Hulu": {"category": "Media", "emoji": "💚", "policy": "Media", "icon": "app-icons/Hulu.jpg"},
    "HBO": {"category": "Media", "emoji": "🍿", "policy": "Media", "icon": "app-icons/HBO.jpg"},
    "Twitch": {
        "category": "Media",
        "emoji": "🔴",
        "policy": "Media",
        "icon": "app-icons/Twitch.jpg",
    },
    "NBA": {"category": "Media", "emoji": "🏀", "policy": "Media", "icon": "app-icons/NBA.jpg"},
    "AI": {"category": "AI", "emoji": "🤖", "policy": "Proxy", "icon": "app-icons/AI.jpg"},
    "Suno": {"category": "AI", "emoji": "🎶", "policy": "AI", "icon": "app-icons/Suno.jpg"},
    "Google": {"category": "Web", "emoji": "🔍", "policy": "Proxy", "icon": "app-icons/Google.jpg"},
    "Starryblu": {
        "category": "Finance",
        "emoji": "💳",
        "policy": "Finance",
        "icon": "app-icons/Starryblu.jpg",
    },
}

CLIENTS = (
    ("surge", "Surge", ".list"),
    ("loon", "Loon", ".list"),
    ("shadowrocket", "Shadowrocket", ".list"),
    ("stash", "Stash", ".list"),
    ("mihomo", "mihomo", ".list"),
    ("egern", "Egern", ".yaml"),
    ("quantumultx", "QuantumultX", ".list"),
)

HEADER_NAME = re.compile(r"^# 规则名称:\s*(.+?)\s*$")
HEADER_COUNT = re.compile(r"^# 规则统计:\s*(\d+)\s*$")
VIEW_TYPES = ("domainset", "nonip", "ip")


class PortalError(RuntimeError):
    """A deterministic input error that must stop stats generation."""


def parse_list(path: Path) -> tuple[str | None, int | None, dict[str, int]]:
    name = None
    count = None
    types: Counter[str] = Counter()
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise PortalError(f"cannot read {path}: {error}") from error
    for line in lines:
        match = HEADER_NAME.match(line)
        if match:
            name = match.group(1)
            continue
        match = HEADER_COUNT.match(line)
        if match:
            count = int(match.group(1))
            continue
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        types[stripped.split(",")[0]] += 1
    return name, count, dict(types)


def parse_header_count(path: Path) -> int:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise PortalError(f"cannot read {path}: {error}") from error
    for line in lines:
        match = HEADER_COUNT.match(line)
        if match:
            return int(match.group(1))
    raise PortalError(f"{path}: missing 规则统计 header")


def build(root: Path) -> dict:
    manifest_path = root / "engine" / "sources" / "apps.yaml"
    try:
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise PortalError(f"cannot read manifest {manifest_path}: {error}") from error
    if not isinstance(manifest, dict) or not isinstance(manifest.get("apps"), dict):
        raise PortalError("manifest must be a mapping with an apps mapping")
    apps_out = []
    for app_name, app in manifest["apps"].items():
        if not app.get("enabled"):
            continue
        meta = PORTAL_META.get(app_name)
        if meta is None:
            raise PortalError(f"{app_name}: missing portal metadata (add it to PORTAL_META)")
        output = root / app["output"]
        list_name, header_count, type_counts = parse_list(output)
        if list_name != app_name:
            raise PortalError(
                f"{output}: header name {list_name!r} does not match app {app_name!r}"
            )
        if header_count is None:
            raise PortalError(f"{output}: missing 规则统计 header")
        if header_count != sum(type_counts.values()):
            raise PortalError(
                f"{output}: header count {header_count} does not match body rules {sum(type_counts.values())}"
            )
        stem = output.stem
        clients = {}
        for key, directory, suffix in CLIENTS:
            entry = {"file": f"{directory}/{stem}{suffix}", "rules": header_count}
            if key in {"egern", "quantumultx", "mihomo"}:
                client_count = parse_header_count(root / entry["file"])
                if client_count > header_count:
                    raise PortalError(
                        f"{app_name}: {key} count {client_count} exceeds canonical {header_count}"
                    )
                entry["rules"] = client_count
                entry["dropped"] = header_count - client_count
            clients[key] = entry
        views = {}
        for key, directory, _suffix in CLIENTS:
            view_map = {}
            for view_name in VIEW_TYPES:
                vpath = root / directory / f"{stem}-{view_name}.conf"
                if vpath.is_file():
                    view_map[view_name] = {
                        "file": f"{directory}/{stem}-{view_name}.conf",
                        "rules": parse_header_count(vpath),
                    }
            if view_map:
                views[key] = view_map
        sources = app.get("sources") or []
        primary = next(
            (item for item in sources if item.get("role") == "primary"),
            sources[0] if sources else {},
        )
        apps_out.append(
            {
                "name": app_name,
                "category": meta["category"],
                "emoji": meta["emoji"],
                "icon": meta.get("icon"),
                "self_use": bool(meta.get("self_use")),
                "policy": meta["policy"],
                "file": app["output"],
                "rules": header_count,
                "types": type_counts,
                "clients": clients,
                "views": views,
                "source": {
                    "author": primary.get("author", ""),
                    "name": primary.get("name", ""),
                    "format": primary.get("format", ""),
                },
                "note": (app.get("note") or "").strip(),
            }
        )
    return {"repo": REPO, "raw_base": RAW_BASE, "apps": apps_out}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("engine/sources/apps.yaml"))
    parser.add_argument("--output", type=Path, default=Path("engine/portal/public/data/stats.json"))
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--stdout", action="store_true", help="print the JSON instead of writing it")
    mode.add_argument(
        "--check",
        action="store_true",
        help="fail if the committed portal data differs from the generated outputs",
    )
    arguments = parser.parse_args(argv)
    root = arguments.manifest.resolve().parent.parent.parent
    # The document carries emoji and Chinese notes; a non-UTF-8 console (GBK on a
    # Chinese Windows shell) would otherwise raise UnicodeEncodeError on --stdout.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, OSError):  # pragma: no cover - unusual stream
            pass
    try:
        document = build(root)
        text = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
        if arguments.stdout:
            print(text, end="")
        elif arguments.check:
            output = arguments.output
            if not output.is_file():
                raise PortalError(f"missing portal data {output}")
            if output.read_text(encoding="utf-8") != text:
                raise PortalError(
                    f"{output} is stale: regenerate it with "
                    "`python engine/scripts/gen_portal_stats.py` and commit the result"
                )
            print(json.dumps({"checked": str(output), "apps": len(document["apps"])}, indent=2))
        else:
            output = arguments.output
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(text, encoding="utf-8", newline="\n")
        return 0
    except PortalError as error:
        print(f"portal stats failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
