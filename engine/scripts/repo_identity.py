#!/usr/bin/env python3
"""The repository's own published identity, in one place.

The owner/repo slug used to be spelled out in seven literals across
``build_profile.py``, ``gen_portal_stats.py`` and ``verify_profiles.py``, plus the
portal source and the README.  Renaming the GitHub account therefore meant a
find-and-replace across unrelated files, where one miss produces URLs that still
look right but 404 (or, worse, keep resolving through GitHub's redirect until it
stops).  Every generated reference now derives from the constants below.

This module is deliberately data-only: it must stay importable by the scripts
without pulling in the builder.
"""

from __future__ import annotations

OWNER = "byyoshen"
REPOSITORY = "Blink"
BRANCH = "main"

REPO_URL = f"https://github.com/{OWNER}/{REPOSITORY}"
PAGES_URL = f"https://{OWNER}.github.io/{REPOSITORY}/"
# Base for every raw rule/profile reference emitted into generated artifacts.
RAW_BASE = f"https://raw.githubusercontent.com/{OWNER}/{REPOSITORY}/{BRANCH}"


def raw_url(*parts: str) -> str:
    """Join a repository-relative path onto the raw base."""
    return "/".join((RAW_BASE, *parts))
