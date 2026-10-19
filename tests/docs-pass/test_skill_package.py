"""Checks on the shipped ``docs-pass`` skill itself."""

from __future__ import annotations

from pathlib import Path

import lint_skill as ls
import yaml

REPO = Path(__file__).resolve().parents[2]
SKILL_DIR = REPO / "claude/skills/docs-pass"


def test_skill_lints_clean_for_claude_code_target() -> None:
    """The skill passes the linter with no errors."""
    report = ls.lint(SKILL_DIR, "claude-code")
    assert [f for f in report.findings if f.severity == "error"] == []


def test_only_invoked_by_the_user() -> None:
    """The skill edits files, so only ``/docs-pass`` loads it."""
    raw, _ = ls.split_frontmatter((SKILL_DIR / "SKILL.md").read_text())
    assert raw is not None
    assert yaml.safe_load(raw)["disable-model-invocation"] is True
