"""Checks on the shipped ``agents-md-improver`` skill itself."""

from __future__ import annotations

import json
import re
from pathlib import Path

import check_guidance as cg
import lint_skill as ls
import pytest

REPO = Path(__file__).resolve().parents[2]
SKILL_DIR = REPO / "claude/skills/agents-md-improver"
REFERENCES = SKILL_DIR / "references"
GUIDANCE = REPO / "tools/guidance/agents-md-improver"
LINE_BUDGETS = {
    "SKILL.md": 199,
    "references/official-instructions.md": 90,
    "references/official-skills.md": 90,
    "references/method-instructions.md": 80,
    "references/method-skills.md": 50,
}
TAG_RE = re.compile(r"\[([a-z0-9-]+(?:, [a-z0-9-]+)*)\]$")


def manifest() -> cg.Manifest:
    """:return: The skill's guidance manifest."""
    return cg.parse_manifest(json.loads((GUIDANCE / "manifest.json").read_text()))


def test_skill_lints_clean_for_portable_target() -> None:
    """The skill passes its own linter with no errors."""
    report = ls.lint(SKILL_DIR, "portable")
    assert [f for f in report.findings if f.severity == "error"] == []


@pytest.mark.parametrize("rel", LINE_BUDGETS)
def test_line_budgets(rel: str) -> None:
    """SKILL.md and each reference file stay within their line budgets."""
    lines = (SKILL_DIR / rel).read_text().count("\n")
    assert lines <= LINE_BUDGETS[rel]


@pytest.mark.parametrize("name", ["official-instructions.md", "official-skills.md"])
def test_official_rules_carry_valid_section_tags(name: str) -> None:
    """Every rule in an official file is tagged with sections that target that file."""
    owned = {s.id for s in manifest().sections if s.target == name}
    body_rules: list[str] = []
    heading = ""
    for line in (REFERENCES / name).read_text().splitlines():
        if line.startswith("#"):
            heading = line.lstrip("# ")
        elif line.startswith("- ") and heading != "Contents":
            body_rules.append(line)
    assert body_rules
    for rule in body_rules:
        match = TAG_RE.search(rule)
        assert match, f"untagged rule: {rule}"
        assert set(match.group(1).split(", ")) <= owned, rule


def test_every_section_is_condensed_somewhere() -> None:
    """Each tracked section is cited by at least one rule in its target file."""
    text = {
        name: (REFERENCES / name).read_text()
        for name in ("official-instructions.md", "official-skills.md")
    }
    uncited = [s.id for s in manifest().sections if s.id not in text[s.target]]
    assert uncited == []


def test_manifest_accepted_with_snapshots() -> None:
    """Every section and watch entry has a hash; every section has a snapshot."""
    data = manifest()
    assert all(s.sha256 for s in data.sections)
    assert all(w.sha256 for w in data.watch)
    for section in data.sections:
        snapshot = (GUIDANCE / "snapshots" / f"{section.id}.md").read_text()
        assert cg.digest(snapshot) == section.sha256


def test_manifest_points_at_this_skill() -> None:
    """``references_dir`` resolves to the skill's references."""
    assert (REPO / manifest().references_dir).resolve() == REFERENCES


@pytest.mark.parametrize("name", ["official-instructions.md", "official-skills.md"])
def test_official_files_carry_the_checked_date(name: str) -> None:
    """Each official file's ``as_of`` equals the manifest's ``last_checked``."""
    raw, _ = ls.split_frontmatter((REFERENCES / name).read_text())
    assert raw is not None
    assert f"as_of: {manifest().last_checked.isoformat()}" in raw.splitlines()


def test_skill_ships_no_update_machinery() -> None:
    """The checker, manifest and snapshots live in ``tools/``, not the skill."""
    assert {p.name for p in SKILL_DIR.iterdir()} == {"SKILL.md", "references"}


def test_reference_files_do_not_link_each_other() -> None:
    """Reference files are one level deep: no links between them."""
    for path in REFERENCES.glob("*.md"):
        assert not re.search(r"\]\([^)]*\.md\)", path.read_text()), path.name


def test_only_portable_frontmatter() -> None:
    """SKILL.md uses only ``name`` and ``description``."""
    raw, _ = ls.split_frontmatter((SKILL_DIR / "SKILL.md").read_text())
    assert raw is not None
    assert {line.split(":")[0] for line in raw.splitlines()} == {"name", "description"}
