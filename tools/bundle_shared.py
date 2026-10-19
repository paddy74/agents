#!/usr/bin/env python3
"""Copy the ``tools/shared/`` modules a skill's scripts import into the skill.

Skill scripts import shared code as ``shared.<module>``. A skill ships only its own
folder, so before installing or packaging, this copies each imported module (plus
``__init__.py``) into ``<skill>/scripts/shared/`` and removes stale copies. The copies
are generated and gitignored; edit ``tools/shared/`` instead.

Exit 0 on success; with ``--check``, exit 1 when a copy is missing or out of date.
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path
from typing import cast

BUNDLE_DIR = "shared"
SHARED_SRC = Path(__file__).resolve().parent / BUNDLE_DIR
INIT = "__init__.py"


def imported_modules(source: str) -> set[str]:
    """List the ``shared`` submodules a Python source imports.

    :param source: Python source text.
    :return: Submodule names, e.g. ``{"mdparse"}``.
    :raises SyntaxError: If the source doesn't parse.
    """
    found: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            parts = node.module.split(".")
            if parts[0] != BUNDLE_DIR:
                continue
            if len(parts) > 1:
                found.add(parts[1])
            else:
                found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                parts = alias.name.split(".")
                if parts[0] == BUNDLE_DIR and len(parts) > 1:
                    found.add(parts[1])
    return found


def planned_files(skill_dir: Path, src: Path = SHARED_SRC) -> dict[str, str]:
    """Work out what ``scripts/shared/`` must contain.

    :param skill_dir: Skill directory.
    :param src: Shared source package.
    :return: File name to content; empty when no script imports ``shared``.
    :raises FileNotFoundError: If a script imports a module ``src`` lacks.
    """
    scripts = skill_dir / "scripts"
    modules: set[str] = set()
    if scripts.is_dir():
        for path in sorted(scripts.rglob("*.py")):
            if BUNDLE_DIR not in path.relative_to(scripts).parts:
                modules |= imported_modules(path.read_text(encoding="utf-8"))
    if not modules:
        return {}
    files = {INIT: (src / INIT).read_text(encoding="utf-8")}
    for module in sorted(modules):
        path = src / f"{module}.py"
        if not path.is_file():
            raise FileNotFoundError(f"{skill_dir.name}: no shared module {path}")
        files[path.name] = path.read_text(encoding="utf-8")
    return files


def stale(skill_dir: Path, files: dict[str, str]) -> list[str]:
    """Compare the bundled copies with the plan.

    :param skill_dir: Skill directory.
    :param files: Planned file name to content.
    :return: File names that are missing, outdated or no longer needed.
    """
    target = skill_dir / "scripts" / BUNDLE_DIR
    present = {p.name for p in target.glob("*.py")} if target.is_dir() else set[str]()
    problems = sorted(present - files.keys())
    for name, content in files.items():
        path = target / name
        if not path.is_file() or path.read_text(encoding="utf-8") != content:
            problems.append(name)
    return problems


def write_bundle(skill_dir: Path, files: dict[str, str]) -> None:
    """Write the planned copies and delete stale ones.

    :param skill_dir: Skill directory.
    :param files: Planned file name to content.
    """
    target = skill_dir / "scripts" / BUNDLE_DIR
    if target.is_dir():
        for path in target.glob("*.py"):
            if path.name not in files:
                path.unlink()
    if not files:
        if target.is_dir() and not any(target.iterdir()):
            target.rmdir()
        return
    target.mkdir(exist_ok=True)
    for name, content in files.items():
        (target / name).write_text(content, encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    """:return: The command-line parser."""
    parser = argparse.ArgumentParser(
        description="Bundle tools/shared/ modules into skill directories."
    )
    parser.add_argument("skill_dirs", type=Path, nargs="+", metavar="skill_dir")
    parser.add_argument(
        "--check", action="store_true", help="report stale copies, write nothing"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI.

    :param argv: Arguments (default ``sys.argv[1:]``).
    :return: 0 on success, 1 on bad input or (with ``--check``) stale copies.
    """
    args = build_parser().parse_args(argv)
    status = 0
    for skill_dir in cast(list[Path], args.skill_dirs):
        if not (skill_dir / "SKILL.md").is_file():
            sys.stderr.write(f"not a skill directory: {skill_dir}\n")
            return 1
        try:
            files = planned_files(skill_dir)
        except (OSError, SyntaxError) as exc:
            sys.stderr.write(f"bundle_shared.py: {exc}\n")
            return 1
        problems = stale(skill_dir, files)
        if args.check:
            if problems:
                print(f"{skill_dir}: stale {', '.join(problems)}")
                status = 1
        elif problems:
            write_bundle(skill_dir, files)
            print(f"{skill_dir}: bundled {', '.join(sorted(files)) or 'nothing'}")
    return status


if __name__ == "__main__":
    sys.exit(main())
