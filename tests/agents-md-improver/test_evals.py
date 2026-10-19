"""Consistency checks for the skill-creator evals and their fixtures."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

EVALS_DIR = Path(__file__).resolve().parent / "evals"
FIXTURES = EVALS_DIR / "fixtures"
MAX_FIXTURE_BYTES = 50_000


def evals() -> dict[str, Any]:
    """:return: The parsed ``evals.json``."""
    return json.loads((EVALS_DIR / "evals.json").read_text())


def test_evals_schema() -> None:
    """Ten evals with unique ids, prompts, expectations and existing files."""
    data = evals()
    assert data["skill_name"] == "agents-md-improver"
    items: list[dict[str, Any]] = data["evals"]
    assert [e["id"] for e in items] == list(range(1, 11))
    for item in items:
        assert item["prompt"] and item["expected_output"] and item["expectations"]
        for rel in item["files"]:
            assert (EVALS_DIR / rel).exists(), rel


def test_discriminating_expectations_present() -> None:
    """E1, E2 and E4 carry discriminating ([D]) expectations."""
    for item in evals()["evals"]:
        if item["id"] in (1, 2, 4):
            assert any("[D]" in e for e in item["expectations"]), item["id"]


def test_fixture_shapes() -> None:
    """Fixtures match what the evals describe and stay small."""
    assert (FIXTURES / "e1/AGENTS.md").read_text().count("\n") == 78
    link = FIXTURES / "e5/CLAUDE.md"
    assert link.is_symlink() and link.readlink() == Path("AGENTS.md")
    size = sum(p.stat().st_size for p in FIXTURES.rglob("*") if p.is_file())
    assert size <= MAX_FIXTURE_BYTES
