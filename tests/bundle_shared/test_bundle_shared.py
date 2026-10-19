"""Tests for ``tools/bundle_shared.py``."""

from __future__ import annotations

from pathlib import Path

import bundle_shared as bs
import pytest

SHARED_FILES = {"__init__.py": '"""Shared."""\n', "mdparse.py": "X = 1\n"}


def make_src(root: Path) -> Path:
    """:param root: Parent directory. :return: A fake ``shared`` source package."""
    src = root / "src" / "shared"
    src.mkdir(parents=True)
    for name, content in SHARED_FILES.items():
        (src / name).write_text(content)
    return src


def make_skill(root: Path, script: str) -> Path:
    """Write a skill with one script.

    :param root: Parent directory.
    :param script: Content of ``scripts/run.py``.
    :return: The skill directory.
    """
    skill = root / "demo"
    (skill / "scripts").mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: demo\n---\n")
    (skill / "scripts" / "run.py").write_text(script)
    return skill


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("from shared.mdparse import fence_mask\n", {"mdparse"}),
        ("from shared import mdparse\n", {"mdparse"}),
        ("import shared.mdparse\n", {"mdparse"}),
        ("from sharedx import y\nimport json\n", set[str]()),
        ("from .shared import y\n", set[str]()),
    ],
)
def test_imported_modules(source: str, expected: set[str]) -> None:
    """Only absolute imports of ``shared`` submodules count."""
    assert bs.imported_modules(source) == expected


def test_planned_files(tmp_path: Path) -> None:
    """A skill importing ``shared.mdparse`` gets it plus ``__init__.py``."""
    skill = make_skill(tmp_path, "from shared.mdparse import X\n")
    assert bs.planned_files(skill, make_src(tmp_path)) == SHARED_FILES


def test_planned_files_no_imports(tmp_path: Path) -> None:
    """A skill that doesn't import ``shared`` needs nothing."""
    skill = make_skill(tmp_path, "print('hi')\n")
    assert bs.planned_files(skill, make_src(tmp_path)) == {}


def test_planned_files_missing_module(tmp_path: Path) -> None:
    """Importing a module ``tools/shared/`` lacks fails fast."""
    skill = make_skill(tmp_path, "from shared.nope import X\n")
    with pytest.raises(FileNotFoundError, match="nope"):
        bs.planned_files(skill, make_src(tmp_path))


def test_write_then_check_clean(tmp_path: Path) -> None:
    """After writing, nothing is stale; bundled copies don't count as importers."""
    skill = make_skill(tmp_path, "from shared.mdparse import X\n")
    files = bs.planned_files(skill, make_src(tmp_path))
    assert bs.stale(skill, files) == ["__init__.py", "mdparse.py"]
    bs.write_bundle(skill, files)
    assert bs.stale(skill, files) == []
    assert bs.planned_files(skill, make_src(tmp_path / "again")) == files


def test_stale_copies_detected_and_removed(tmp_path: Path) -> None:
    """Outdated and no-longer-needed copies are stale; writing fixes both."""
    skill = make_skill(tmp_path, "from shared.mdparse import X\n")
    files = bs.planned_files(skill, make_src(tmp_path))
    bs.write_bundle(skill, files)
    bundle = skill / "scripts" / "shared"
    (bundle / "mdparse.py").write_text("X = 0\n")
    (bundle / "old.py").write_text("")
    assert bs.stale(skill, files) == ["old.py", "mdparse.py"]
    bs.write_bundle(skill, files)
    assert bs.stale(skill, files) == []


def test_unused_bundle_removed(tmp_path: Path) -> None:
    """When no script imports ``shared`` any more, the bundle goes away."""
    skill = make_skill(tmp_path, "from shared.mdparse import X\n")
    bs.write_bundle(skill, bs.planned_files(skill, make_src(tmp_path)))
    (skill / "scripts" / "run.py").write_text("print('hi')\n")
    bs.write_bundle(skill, {})
    assert not (skill / "scripts" / "shared").exists()


def test_cli(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """``--check`` fails on a stale bundle; a plain run fixes it; bad input exits 1."""
    skill = make_skill(tmp_path, "from shared.mdparse import fence_mask\n")
    assert bs.main([str(skill), "--check"]) == 1
    assert bs.main([str(skill)]) == 0
    assert (skill / "scripts" / "shared" / "mdparse.py").read_text() == (
        bs.SHARED_SRC / "mdparse.py"
    ).read_text()
    assert bs.main([str(skill), "--check"]) == 0
    assert bs.main([str(tmp_path / "nope")]) == 1
    assert "not a skill directory" in capsys.readouterr().err
