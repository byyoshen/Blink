"""The published repository identity must be spelled out in exactly one place.

engine/scripts/repo_identity.py is the single source for the owner/repo slug, and
every generated reference derives from it.  Hand-maintained prose cannot, so the
README, the portal shell and the design docs still carry the slug literally -- 18
occurrences at the time of writing.  The 2026-09 account rename had to touch all
of them, and a missed one yields a URL that still looks correct but 404s (or keeps
resolving through GitHub's redirect until it stops).  These tests fail on any
self-reference that disagrees with the constants.
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_profile  # noqa: E402
import repo_identity  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]

# Every shape in which this repository refers to itself.  Each pattern captures
# (owner, repo); a match is only asserted on when the repo is ours, so upstream
# references (Repcz/Tool, SukkaW/Surge, v2fly/domain-list-community, ...) are
# ignored without needing an allow-list.
SELF_REFERENCE_PATTERNS = (
    re.compile(r"raw\.githubusercontent\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)"),
    re.compile(r"github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)"),
    re.compile(r"([A-Za-z0-9_-]+)\.github\.io/([A-Za-z0-9_.-]+)"),
    re.compile(r"cdn\.jsdelivr\.net/gh/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)[@/]"),
    # Badge endpoints embed the slug too, e.g. img.shields.io/github/stars/<o>/<r>
    re.compile(r"img\.shields\.io/github/[a-z-]+/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)"),
)

# Files that may legitimately spell the slug out.  Generated artifacts are
# included on purpose: they must agree with the constants that produced them.
SCANNED_GLOBS = (
    "*.md",
    "engine/*.md",
    "engine/docs/*.md",
    "engine/portal/index.html",
    "engine/portal/src/*.ts",
    "engine/portal/src/*.tsx",
    "engine/portal/src/components/*.tsx",
    "engine/scripts/*.py",
    "Profiles/*",
    ".github/workflows/*.yml",
    ".github/ISSUE_TEMPLATE/*.md",
)

# A floor so the scan cannot silently pass by matching nothing -- the same
# failure mode that made verify_profiles' raw-URL regex worth deriving.
MINIMUM_SELF_REFERENCES = 15


def scanned_files() -> list[Path]:
    paths: set[Path] = set()
    for pattern in SCANNED_GLOBS:
        paths.update(path for path in ROOT.glob(pattern) if path.is_file())
    return sorted(paths)


def self_references(text: str) -> list[tuple[str, str]]:
    found = []
    for pattern in SELF_REFERENCE_PATTERNS:
        found.extend(pattern.findall(text))
    return found


class RepoIdentityTests(unittest.TestCase):
    """The owner/repo slug must live in exactly one module."""

    def test_only_repo_identity_spells_out_the_slug_in_code(self) -> None:
        scripts = ROOT / "engine" / "scripts"
        slug = f"{repo_identity.OWNER}/{repo_identity.REPOSITORY}"
        offenders = [
            path.name
            for path in sorted(scripts.glob("*.py"))
            if path.name != "repo_identity.py" and slug in path.read_text(encoding="utf-8")
        ]
        self.assertEqual(offenders, [], f"hardcoded {slug!r}; derive it from repo_identity instead")

    def test_generated_references_derive_from_the_constants(self) -> None:
        self.assertTrue(build_profile.BLINK_RAW.startswith(repo_identity.RAW_BASE))
        self.assertTrue(build_profile.BLINK_RAW_CLASH.startswith(repo_identity.RAW_BASE))
        self.assertTrue(build_profile.BLINK_RAW_QX.startswith(repo_identity.RAW_BASE))
        self.assertEqual(build_profile.BLINK_RAW_VIEW, repo_identity.RAW_BASE)
        self.assertEqual(
            repo_identity.raw_url("Surge", "AI.list"),
            f"{repo_identity.RAW_BASE}/Surge/AI.list",
        )

    def test_constants_agree_with_each_other(self) -> None:
        slug = f"{repo_identity.OWNER}/{repo_identity.REPOSITORY}"
        self.assertEqual(repo_identity.REPO_URL, f"https://github.com/{slug}")
        self.assertEqual(
            repo_identity.PAGES_URL,
            f"https://{repo_identity.OWNER}.github.io/{repo_identity.REPOSITORY}/",
        )
        self.assertEqual(
            repo_identity.RAW_BASE,
            f"https://raw.githubusercontent.com/{slug}/{repo_identity.BRANCH}",
        )


class SelfReferenceTests(unittest.TestCase):
    """Hand-written docs and the portal shell must use the current slug."""

    def test_every_self_reference_uses_the_current_owner(self) -> None:
        stale: list[str] = []
        total = 0
        for path in scanned_files():
            text = path.read_text(encoding="utf-8", errors="replace")
            for owner, repository in self_references(text):
                if repository != repo_identity.REPOSITORY:
                    continue  # an upstream repository, not this one
                total += 1
                if owner != repo_identity.OWNER:
                    stale.append(f"{path.relative_to(ROOT).as_posix()}: {owner}/{repository}")
        self.assertEqual(
            sorted(set(stale)),
            [],
            "self-reference uses a stale owner; update it or repo_identity",
        )
        self.assertGreaterEqual(
            total,
            MINIMUM_SELF_REFERENCES,
            "the self-reference scan matched almost nothing, so it is no longer "
            "guarding anything; check SELF_REFERENCE_PATTERNS and SCANNED_GLOBS",
        )

    def test_the_scan_would_catch_a_stale_owner(self) -> None:
        # Guards the guard: the patterns must actually recognise each URL shape.
        samples = (
            f"https://raw.githubusercontent.com/old/{repo_identity.REPOSITORY}/main/Surge/AI.list",
            f"https://github.com/old/{repo_identity.REPOSITORY}",
            f"https://old.github.io/{repo_identity.REPOSITORY}/",
            f"https://cdn.jsdelivr.net/gh/old/{repo_identity.REPOSITORY}@main/Surge/AI.list",
            f"https://img.shields.io/github/stars/old/{repo_identity.REPOSITORY}?style=flat",
        )
        for sample in samples:
            owners = [
                owner
                for owner, repository in self_references(sample)
                if repository == repo_identity.REPOSITORY
            ]
            self.assertIn("old", owners, sample)

    def test_readme_and_portal_are_actually_covered(self) -> None:
        # The two files a rename is most likely to leave behind.
        covered = {path.relative_to(ROOT).as_posix() for path in scanned_files()}
        self.assertIn("README.md", covered)
        self.assertIn("engine/portal/index.html", covered)


class RepoDocLinkTests(unittest.TestCase):
    """Every in-repo document the portal and docs link to must actually exist."""

    # The portal's footer shipped `blob/main/SOURCE_AUDITS.md` for months while
    # the file lived at `engine/SOURCE_AUDITS.md`.  Nothing caught it: the slug
    # was correct, the URL was well-formed, and only GitHub knew it was a 404.
    # A path that moves under `engine/` is the likely repeat of this.
    LINK_PATTERN = re.compile(r"(?:blob|tree)/(?:main|\$\{[^}]*\})/([A-Za-z0-9_./-]+)")

    LINK_GLOBS = SCANNED_GLOBS

    # A floor for the same reason as MINIMUM_SELF_REFERENCES: a pattern that
    # stops matching would otherwise pass silently forever.
    MINIMUM_LINKS = 5

    # Known limitation, deliberately not worked around: this scans text, so a
    # document that *quotes* a broken link as evidence fails the same as one
    # that publishes it.  The engineering register tripped exactly this while
    # recording the bug above.  The rule is that prose describes a broken path
    # rather than reproducing it; an allow-list would also excuse real ones.

    def _links(self) -> list[tuple[Path, str]]:
        found: list[tuple[Path, str]] = []
        for pattern in self.LINK_GLOBS:
            for path in sorted(ROOT.glob(pattern)):
                if not path.is_file():
                    continue
                text = path.read_text(encoding="utf-8", errors="replace")
                found.extend((path, target) for target in self.LINK_PATTERN.findall(text))
        return found

    def test_linked_repository_paths_exist(self) -> None:
        links = self._links()
        broken = sorted(
            {
                f"{path.relative_to(ROOT).as_posix()} -> {target}"
                for path, target in links
                if not (ROOT / target).exists()
            }
        )
        self.assertEqual(broken, [], "link points at a path that is not in the repository")
        self.assertGreaterEqual(
            len(links),
            self.MINIMUM_LINKS,
            "the repository-link scan matched almost nothing, so it is no longer "
            "guarding anything; check LINK_PATTERN and LINK_GLOBS",
        )

    def test_the_scan_would_catch_a_moved_file(self) -> None:
        # Guards the guard, in both spellings the repo actually uses.
        samples = (
            "https://github.com/o/r/blob/main/NOT_HERE.md",
            "`${repo}/blob/main/NOT_HERE.md`",
            "https://github.com/o/r/tree/main/NOT_HERE.md",
        )
        for sample in samples:
            self.assertIn("NOT_HERE.md", self.LINK_PATTERN.findall(sample), sample)


if __name__ == "__main__":
    unittest.main()
