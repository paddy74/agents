"""Tests for ``tools/lint_skill.py``. Each case builds a skill in a temp directory.

The parity tests are the only place skill-creator's ``quick_validate.py`` runs.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

import lint_skill as ls
import pytest

NAME = "processing-pdfs"
DESCRIPTION = "Extracts text from PDF files. Use when the user asks to read a PDF."
BODY = """\
# Processing PDFs

## Workflow
1. Run `python ${CLAUDE_SKILL_DIR}/scripts/extract.py <file>`.
2. For forms, read [forms](references/forms.md).
"""
REFERENCE = "# Forms\n\nFill fields in order.\n"


@dataclass
class SkillSpec:
    """Inputs for a fixture skill.

    :ivar frontmatter: Frontmatter text between the ``---`` lines.
    :ivar body: SKILL.md body.
    :ivar files: Extra files, relative path to content.
    :ivar dir_name: Skill directory name.
    :ivar prefix: Text placed before the opening ``---``.
    """

    frontmatter: str = f"name: {NAME}\ndescription: {DESCRIPTION}\n"
    body: str = BODY
    files: dict[str, str] = field(
        default_factory=lambda: {
            "scripts/extract.py": "print('ok')\n",
            "references/forms.md": REFERENCE,
        }
    )
    dir_name: str = NAME
    prefix: str = ""


def build(root: Path, spec: SkillSpec) -> Path:
    """Write a fixture skill.

    :param root: Parent directory.
    :param spec: What to write.
    :return: The skill directory.
    """
    skill = root / spec.dir_name
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        f"{spec.prefix}---\n{spec.frontmatter}---\n\n{spec.body}"
    )
    for rel, content in spec.files.items():
        path = skill / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    return skill


def findings(
    root: Path, spec: SkillSpec, target: ls.Target = "portable"
) -> list[tuple[str, str]]:
    """Lint a fixture skill.

    :param root: Parent directory.
    :param spec: What to write.
    :param target: Lint target.
    :return: ``(severity, check)`` pairs.
    """
    report = ls.lint(build(root, spec), target)
    return [(f.severity, f.check) for f in report.findings]


def fm(**fields: str) -> str:
    """Build frontmatter from the defaults plus overrides.

    :param fields: Fields to set; an empty string removes the field.
    :return: Frontmatter text.
    """
    merged = {"name": NAME, "description": DESCRIPTION} | fields
    return "".join(f"{k}: {v}\n" for k, v in merged.items() if v != "")


def with_files(extra: dict[str, str]) -> dict[str, str]:
    """:param extra: Files to add or replace. :return: The default files plus these."""
    return SkillSpec().files | extra


def test_clean_skill_has_no_findings(tmp_path: Path) -> None:
    """A well-formed skill exits 0 with no findings."""
    assert findings(tmp_path, SkillSpec()) == []
    assert ls.main([str(tmp_path / NAME)]) == 0


CASES: dict[str, tuple[SkillSpec, str, str]] = {
    # Frontmatter structure
    "not-first-line": (SkillSpec(prefix="\n"), "error", "frontmatter"),
    "bad-yaml": (SkillSpec(frontmatter="name: [unclosed\n"), "error", "frontmatter"),
    "not-mapping": (SkillSpec(frontmatter="- a\n- b\n"), "error", "frontmatter"),
    # name
    "name-missing": (SkillSpec(frontmatter=fm(name="")), "error", "name"),
    "name-not-str": (SkillSpec(frontmatter=fm(name="[a]")), "error", "name"),
    "name-upper": (
        SkillSpec(frontmatter=fm(name="Pdfs"), dir_name="Pdfs"),
        "error",
        "name",
    ),
    "name-long": (
        SkillSpec(frontmatter=fm(name="a" * 65), dir_name="a" * 65),
        "error",
        "name",
    ),
    "name-edge-hyphen": (
        SkillSpec(frontmatter=fm(name="-pdfs"), dir_name="-pdfs"),
        "error",
        "name",
    ),
    "name-double-hyphen": (
        SkillSpec(frontmatter=fm(name="pdf--tools"), dir_name="pdf--tools"),
        "error",
        "name",
    ),
    "name-claude": (
        SkillSpec(frontmatter=fm(name="claude-pdfs"), dir_name="claude-pdfs"),
        "error",
        "name",
    ),
    "name-reserved": (
        SkillSpec(frontmatter=fm(name="synced"), dir_name="synced"),
        "error",
        "name",
    ),
    "name-vague": (
        SkillSpec(frontmatter=fm(name="pdf-helper"), dir_name="pdf-helper"),
        "warning",
        "name-style",
    ),
    "name-not-gerund": (
        SkillSpec(frontmatter=fm(name="pdf-reader"), dir_name="pdf-reader"),
        "warning",
        "name-style",
    ),
    # description
    "description-missing": (
        SkillSpec(frontmatter=fm(description="")),
        "error",
        "description",
    ),
    "description-not-str": (
        SkillSpec(frontmatter=fm(description="[a, b]")),
        "error",
        "description",
    ),
    "description-long": (
        SkillSpec(frontmatter=fm(description="Use when " + "x" * 1020)),
        "error",
        "description",
    ),
    "description-angle": (
        SkillSpec(frontmatter=fm(description="Use when given <file> input.")),
        "error",
        "description",
    ),
    "description-voice": (
        SkillSpec(frontmatter=fm(description="I can read PDFs. Use when asked.")),
        "warning",
        "description-voice",
    ),
    "description-trigger": (
        SkillSpec(frontmatter=fm(description="Extracts text from PDF files.")),
        "warning",
        "description-trigger",
    ),
    # optional fields
    "compatibility-long": (
        SkillSpec(frontmatter=fm(compatibility="x" * 501)),
        "error",
        "compatibility",
    ),
    "compatibility-not-str": (
        SkillSpec(frontmatter=fm(compatibility="[a]")),
        "error",
        "compatibility",
    ),
    "unknown-field": (SkillSpec(frontmatter=fm(owner="me")), "warning", "fields"),
    # body and structure
    "body-over-500": (SkillSpec(body=BODY + "line\n" * 500), "error", "body-size"),
    "body-over-300": (SkillSpec(body=BODY + "line\n" * 300), "warning", "body-size"),
    "body-tokens": (
        SkillSpec(body=BODY + ("word " * 900 + "\n") * 5),
        "warning",
        "body-size",
    ),
    "body-top": (
        SkillSpec(body="# PDFs\n\n" + "Text.\n" * 45 + "## Workflow\n" + BODY),
        "warning",
        "body-top",
    ),
    "reference-depth": (
        SkillSpec(
            files=with_files(
                {
                    "references/forms.md": "# Forms\n\nSee [more](more.md).\n",
                    "references/more.md": "# More\n",
                }
            )
        ),
        "error",
        "reference-depth",
    ),
    "reference-toc": (
        SkillSpec(
            files=with_files({"references/forms.md": "# Forms\n" + "line\n" * 110})
        ),
        "warning",
        "reference-toc",
    ),
    "broken-link": (
        SkillSpec(body=BODY + "See [gone](references/gone.md).\n"),
        "error",
        "broken-link",
    ),
    "broken-skill-dir-path": (
        SkillSpec(body=BODY + "Run `${CLAUDE_SKILL_DIR}/scripts/gone.py`.\n"),
        "error",
        "broken-link",
    ),
    "windows-link": (
        SkillSpec(body=BODY + "See [forms](references\\forms.md).\n"),
        "error",
        "windows-path",
    ),
    "windows-code": (
        SkillSpec(body=BODY + "```\npython scripts\\extract.py\n```\n"),
        "error",
        "windows-path",
    ),
    "time-sensitive": (
        SkillSpec(body=BODY + "Before August 2025, use the v1 API.\n"),
        "warning",
        "time-sensitive",
    ),
    "emphasis": (
        SkillSpec(body=BODY + "You MUST a.\nNEVER b.\nIMPORTANT: c.\n"),
        "warning",
        "emphasis",
    ),
    "unreferenced-script": (
        SkillSpec(files=with_files({"scripts/orphan.py": "print()\n"})),
        "warning",
        "unreferenced-script",
    ),
    "extra-skill-md": (
        SkillSpec(files=with_files({"nested/SKILL.md": "---\nname: x\n---\n"})),
        "error",
        "single-skill-md",
    ),
}


@pytest.mark.parametrize("case", CASES)
def test_check_reports_expected_finding(tmp_path: Path, case: str) -> None:
    """Each table row produces its finding with the right severity and exit code."""
    spec, severity, check = CASES[case]
    found = findings(tmp_path, spec)
    assert (severity, check) in found
    has_errors = any(s == "error" for s, _ in found)
    assert ls.main([str(tmp_path / spec.dir_name), "--json"]) == (
        1 if has_errors else 0
    )


@pytest.mark.parametrize(
    ("spec", "check"),
    [
        (SkillSpec(dir_name="other-dir"), "name-dir"),
        (SkillSpec(frontmatter=fm(metadata="{version: 1}")), "metadata"),
    ],
    ids=["name-dir", "metadata-types"],
)
def test_error_under_portable_warning_under_claude_code(
    tmp_path: Path, spec: SkillSpec, check: str
) -> None:
    """Target-dependent checks are errors for portable and warnings for Claude Code."""
    assert ("error", check) in findings(tmp_path / "p", spec, "portable")
    cc = findings(tmp_path / "c", spec, "claude-code")
    assert ("warning", check) in cc
    assert ("error", check) not in cc


def test_claude_code_field_allowed_only_for_claude_code(tmp_path: Path) -> None:
    """A Claude Code-only field is a warning for portable and allowed for Claude Code."""
    spec = SkillSpec(frontmatter=fm(model="opus", when_to_use="Reading PDFs."))
    assert ("warning", "fields") in findings(tmp_path / "p", spec, "portable")
    assert findings(tmp_path / "c", spec, "claude-code") == []


def test_metadata_strings_pass(tmp_path: Path) -> None:
    """String-to-string metadata is valid."""
    spec = SkillSpec(frontmatter=fm(metadata='{version: "1.0"}'))
    assert findings(tmp_path, spec) == []


def test_when_to_use_length_limit(tmp_path: Path) -> None:
    """``description`` + ``when_to_use`` over 1,536 chars is a Claude Code error."""
    spec = SkillSpec(frontmatter=fm(when_to_use="x" * 1500))
    assert ("error", "description") in findings(tmp_path, spec, "claude-code")


def test_time_sensitive_allowed_under_old_patterns(tmp_path: Path) -> None:
    """Dated text under an "Old patterns" heading is fine."""
    body = BODY + "\n## Old patterns\n\nBefore August 2025, use the v1 API.\n"
    assert findings(tmp_path, SkillSpec(body=body)) == []


def test_reference_with_contents_passes(tmp_path: Path) -> None:
    """A long reference file with a contents list near the top is fine."""
    ref = "# Forms\n\n## Contents\n- Fields\n\n## Fields\n" + "line\n" * 110
    spec = SkillSpec(files=with_files({"references/forms.md": ref}))
    assert findings(tmp_path, spec) == []


def test_two_emphatic_lines_pass(tmp_path: Path) -> None:
    """Up to two emphatic lines are allowed."""
    assert findings(tmp_path, SkillSpec(body=BODY + "NEVER a.\nMUST b.\n")) == []


def test_evals_skill_md_not_counted(tmp_path: Path) -> None:
    """A SKILL.md under ``evals/`` isn't packaged, so it's allowed."""
    spec = SkillSpec(files=with_files({"evals/fixture/SKILL.md": "---\n---\n"}))
    assert findings(tmp_path, spec) == []


def test_module_style_script_reference(tmp_path: Path) -> None:
    """``python -m scripts.tool`` counts as a reference to ``scripts/tool.py``."""
    body = BODY + "Run `python -m scripts.tool`.\n"
    spec = SkillSpec(body=body, files=with_files({"scripts/tool.py": "\n"}))
    assert findings(tmp_path, spec) == []


def test_missing_skill_md(tmp_path: Path) -> None:
    """A directory without SKILL.md is an error."""
    (tmp_path / NAME).mkdir()
    assert ls.main([str(tmp_path / NAME)]) == 1


def test_cli_usage_errors(tmp_path: Path) -> None:
    """A missing directory exits 1."""
    assert ls.main([str(tmp_path / "nope")]) == 1


def test_json_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """``--json`` prints counts and findings."""
    skill = build(tmp_path, SkillSpec(dir_name="other-dir"))
    assert ls.main([str(skill), "--json"]) == 1
    out = json.loads(capsys.readouterr().out)
    assert out["errors"] == 1 and out["target"] == "portable"
    assert out["findings"][0]["check"] == "name-dir"


def test_bundled_shared_modules_not_flagged(tmp_path: Path) -> None:
    """Modules in ``scripts/shared/`` are imported, not run, so aren't unreferenced."""
    spec = SkillSpec(files=with_files({"scripts/shared/mdparse.py": "X = 1\n"}))
    assert findings(tmp_path, spec) == []


def test_fenced_code_uses_shared_parser(tmp_path: Path) -> None:
    """A link inside a four-backtick fence holding a three-backtick fence is ignored."""
    body = BODY + "\n````text\n```\n[x](missing.md)\n```\n````\n"
    assert findings(tmp_path, SkillSpec(body=body)) == []


def test_skill_without_scripts_dir(tmp_path: Path) -> None:
    """A skill with only SKILL.md lints cleanly."""
    spec = SkillSpec(body="# PDFs\n\n## Steps\n1. Read the file.\n", files={})
    assert findings(tmp_path, spec) == []


# --- Parity with the reference validators -------------------------------------------------

QUICK_VALIDATE = os.environ.get("QUICK_VALIDATE_PATH", "")
SKILLS_REF = os.environ.get("SKILLS_REF_BIN", "") or shutil.which("skills-ref") or ""

# Fixtures covering the rules quick_validate.py defines. Ours are stricter on empty
# values, reserved words and metadata types, so those aren't parity cases.
QV_PARITY: dict[str, SkillSpec] = {
    "clean": SkillSpec(),
    "no-frontmatter": SkillSpec(prefix="text\n"),
    "bad-yaml": SkillSpec(frontmatter="name: [unclosed\n"),
    "not-mapping": SkillSpec(frontmatter="- a\n"),
    "unknown-field": SkillSpec(frontmatter=fm(owner="me")),
    "claude-code-field": SkillSpec(frontmatter=fm(model="opus")),
    "no-name": SkillSpec(frontmatter=fm(name="")),
    "no-description": SkillSpec(frontmatter=fm(description="")),
    "name-upper": SkillSpec(frontmatter=fm(name="Pdfs"), dir_name="Pdfs"),
    "name-edge": SkillSpec(frontmatter=fm(name="pdfs-"), dir_name="pdfs-"),
    "name-double": SkillSpec(frontmatter=fm(name="a--b"), dir_name="a--b"),
    "name-long": SkillSpec(frontmatter=fm(name="a" * 65), dir_name="a" * 65),
    "name-int": SkillSpec(frontmatter=fm(name="123"), dir_name="123"),
    "desc-long": SkillSpec(frontmatter=fm(description="Use when " + "x" * 1020)),
    "desc-angle": SkillSpec(frontmatter=fm(description="Use when <x>.")),
    "desc-list": SkillSpec(frontmatter=fm(description="[a]")),
    "compat-long": SkillSpec(frontmatter=fm(compatibility="x" * 501)),
    "compat-ok": SkillSpec(frontmatter=fm(compatibility="Needs Python 3.12")),
    "all-portable-fields": SkillSpec(
        frontmatter=fm(license="MIT", metadata='{a: "b"}', **{"allowed-tools": "Read"})
    ),
    "extra-skill-md": SkillSpec(files=with_files({"sub/SKILL.md": "---\n---\n"})),
}


def lint_passes(skill: Path) -> bool:
    """:param skill: Skill directory. :return: Whether portable lint has no errors."""
    return ls.lint(skill, "portable").errors == 0


def run_reference(argv: list[str]) -> bool:
    """:param argv: Command to run. :return: Whether it exited 0."""
    return (
        subprocess.run(argv, capture_output=True, check=False, timeout=60).returncode
        == 0
    )


@pytest.mark.skipif(not QUICK_VALIDATE, reason="set QUICK_VALIDATE_PATH to run parity")
@pytest.mark.parametrize("case", QV_PARITY)
def test_parity_with_quick_validate(tmp_path: Path, case: str) -> None:
    """Portable lint agrees with quick_validate.py on every frontmatter fixture."""
    if (
        case == "extra-skill-md"
        and "SKILL.md files" not in Path(QUICK_VALIDATE).read_text()
    ):
        pytest.skip("this quick_validate.py predates the single-SKILL.md rule")
    skill = build(tmp_path, QV_PARITY[case])
    expected = run_reference([sys.executable, QUICK_VALIDATE, str(skill)])
    assert lint_passes(skill) is expected


# Rules the Agent Skills spec defines, including the directory match.
SPEC_PARITY: dict[str, SkillSpec] = {
    "clean": SkillSpec(),
    "name-dir": SkillSpec(dir_name="other-dir"),
    "name-upper": SkillSpec(frontmatter=fm(name="Pdfs"), dir_name="Pdfs"),
    "name-double": SkillSpec(frontmatter=fm(name="a--b"), dir_name="a--b"),
    "desc-long": SkillSpec(frontmatter=fm(description="Use when " + "x" * 1020)),
    "compat-long": SkillSpec(frontmatter=fm(compatibility="x" * 501)),
    "unknown-field": SkillSpec(frontmatter=fm(owner="me")),
}


@pytest.mark.skipif(not SKILLS_REF, reason="set SKILLS_REF_BIN to run parity")
@pytest.mark.parametrize("case", SPEC_PARITY)
def test_parity_with_skills_ref(tmp_path: Path, case: str) -> None:
    """Portable lint agrees with ``skills-ref validate`` on spec-defined rules."""
    skill = build(tmp_path, SPEC_PARITY[case])
    assert lint_passes(skill) is run_reference([SKILLS_REF, "validate", str(skill)])


def test_lint_rules_file_matches_quick_validate_fields() -> None:
    """The portable field list is quick_validate.py's ALLOWED_PROPERTIES."""
    fields = ls.load_fields()
    assert fields["portable"] == {
        "name",
        "description",
        "license",
        "compatibility",
        "metadata",
        "allowed-tools",
    }
    assert fields["portable"] < fields["claude-code"]


def test_load_fields_rejects_bad_shape(tmp_path: Path) -> None:
    """A malformed rules file fails fast."""
    path = tmp_path / "rules.json"
    path.write_text('{"fields": {"portable": "name"}}')
    with pytest.raises(ValueError, match="portable"):
        ls.load_fields(path)
