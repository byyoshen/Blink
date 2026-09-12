#!/usr/bin/env python3
"""Fail on credential, proxy-subscription, private-key, or local-user-path patterns."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Local tooling directories: never part of the repository, so scanning them
# only produces false positives against the maintainer's own machine.
SKIP_PARTS = {
    ".claude",
    ".git",
    ".npm-cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tmp-tests",
    ".venv",
    "__pycache__",
    "dist",
    "node_modules",
}
BINARY_SUFFIXES = {
    ".7z",
    ".avi",
    ".bin",
    ".bmp",
    ".class",
    ".dll",
    ".doc",
    ".docx",
    ".eot",
    ".exe",
    ".gif",
    ".gz",
    ".ico",
    ".jar",
    ".jpeg",
    ".jpg",
    ".mov",
    ".mp3",
    ".mp4",
    ".o",
    ".obj",
    ".otf",
    ".pdf",
    ".png",
    ".pyc",
    ".so",
    ".tar",
    ".ttf",
    ".webm",
    ".webp",
    ".woff",
    ".woff2",
    ".xls",
    ".xlsx",
    ".zip",
}
PATTERNS = {
    "github-token": re.compile(r"(?:ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})"),
    "aws-access-key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "private-key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "proxy-uri": re.compile(r"(?:vmess|vless|ss|trojan)://[A-Za-z0-9+/=_?&.%:@-]{8,}"),
    "url-token": re.compile(
        r"https?://[^\s<>\"']+[?&](?:token|access_token|auth|key)=[A-Za-z0-9._~-]{8,}",
        re.IGNORECASE,
    ),
    "url-credentials": re.compile(r"https?://[^\s/:@]+:[^\s/@]+@[^\s<>\"']+"),
    "opaque-subscription-url": re.compile(
        r"https?://[^\s<>\"']+/(?:sub|subscribe|subscription)/[A-Za-z0-9_-]{16,}(?:[/?#]|$)",
        re.IGNORECASE,
    ),
    "local-absolute-path": re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:[\\/](?![\\/])[^\s<>\"'`|]+"),
}


class SecretScanError(RuntimeError):
    """One or more repository text files contain a forbidden sensitive pattern."""


def is_documented_path_placeholder(line: str, end: int) -> bool:
    """Allow only an angle-bracket placeholder immediately following a path prefix."""
    remainder = line[end:]
    return remainder.startswith("<") and ">" in remainder


def iter_text_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() in BINARY_SUFFIXES:
            continue
        relative = path.relative_to(root)
        if any(part in SKIP_PARTS for part in relative.parts):
            continue
        yield path


def scan(root: Path) -> dict:
    hits = []
    files = 0
    for path in iter_text_files(root):
        try:
            content = path.read_bytes()
        except OSError as error:
            raise SecretScanError(f"cannot scan {path}: {error}") from error
        if b"\x00" in content:
            continue
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            # Unknown binary formats are skipped after the NUL-byte/suffix
            # checks. Repository text is required to be UTF-8.
            continue
        files += 1
        for line_number, line in enumerate(text.splitlines(), start=1):
            for rule, pattern in PATTERNS.items():
                matches = list(pattern.finditer(line))
                if rule == "local-absolute-path":
                    matches = [
                        match
                        for match in matches
                        if not is_documented_path_placeholder(line, match.end())
                    ]
                if matches:
                    hits.append(
                        {
                            "rule": rule,
                            "path": path.relative_to(root).as_posix(),
                            "line": line_number,
                        }
                    )
    if hits:
        summary = ", ".join(f"{hit['rule']}@{hit['path']}:{hit['line']}" for hit in hits[:20])
        raise SecretScanError(f"found {len(hits)} sensitive-pattern hit(s): {summary}")
    return {"files_scanned": files, "patterns": sorted(PATTERNS), "hits": 0}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    arguments = parser.parse_args(argv)
    try:
        print(json.dumps(scan(arguments.root.resolve()), ensure_ascii=False, indent=2))
        return 0
    except SecretScanError as error:
        print(f"secret scan failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
