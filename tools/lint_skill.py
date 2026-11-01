#!/usr/bin/env python3
"""Lint a skill directory: frontmatter, body size, structure, links and wording.

The repo's linter for every skill it holds. Frontmatter rules match skill-creator's
``quick_validate.py`` (stricter where the Agent Skills spec is); the parity tests
keep them in step. Requires PyYAML. Exit 0 when there are no errors (warnings
allowed), 1 otherwise.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal, cast

from bundle_shared import BUNDLE_DIR
from shared.mdparse import fence_mask

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - depends on the environment
    sys.stderr.write("lint_skill.py needs PyYAML: pip install pyyaml\n")
    sys.exit(1)

Severity = Literal["error", "warning"]
Target = Literal["portable", "claude-code"]

RULES_PATH = Path(__file__).resolve().with_name("lint_rules.json")
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)
NAME_RE = re.compile(r"^[a-z0-9-]+$")
RESERVED_NAMES = frozenset({"synced", "anthropic-skills"})
VAGUE_SEGMENTS = frozenset({"helper", "helpers", "util", "utils", "tools", "misc"})
GENERIC_NAMES = frozenset({"documents", "data", "files"})
FIRST_SECOND_PERSON_RE = re.compile(
    r"\b(?:I can|I will|I'll|you can|you should|you will)\b", re.IGNORECASE
)
TRIGGER_RE = re.compile(
    r"use when|use this|when the user|when asked|if the user|should be used when",
    re.IGNORECASE,
)
TOP_HEADING_RE = re.compile(
    r"^#{1,6}\s+.*\b(?:workflows?|steps?|route|routing|quick ?start|usage|process"
    r"|procedure|instructions)\b",
    re.IGNORECASE,
)
LINK_RE = re.compile(r"\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
SKILL_DIR_PATH_RE = re.compile(r"\$\{CLAUDE_SKILL_DIR\}/([\w./-]+)")
WINDOWS_PATH_RE = re.compile(
    r"\b[A-Za-z]:\\[\w.-]|\b[\w.-]+\\[\w.-]+\.[A-Za-z]{1,5}\b|\b\w+\\\w+\\\w+"
)
INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
MONTHS = (
    "January|February|March|April|May|June|July|August|September|October|November"
    "|December"
)
TIME_SENSITIVE_RE = re.compile(
    rf"\b(?:before|after)\s+(?:{MONTHS})\s+20\d\d\b"
    r"|\bas of\s+(?:\w+\s+)?20\d\d\b"
    r"|\bcurrently\b[^.\n]{0,40}\b20\d\d\b",
    re.IGNORECASE,
)
EMPHASIS_RE = re.compile(r"\b(?:IMPORTANT|MUST|NEVER)\b")
OLD_PATTERNS_RE = re.compile(r"^(#{1,6})\s+.*old patterns", re.IGNORECASE)
HEADING_RE = re.compile(r"^(#{1,6})\s")
CONTENTS_RE = re.compile(r"^#{1,6}\s+(?:table of )?contents\b", re.IGNORECASE)
SCRIPT_SUFFIXES = frozenset(
    {".py", ".sh", ".bash", ".js", ".mjs", ".cjs", ".ts", ".rb", ".pl", ".ps1"}
)
EXCLUDED_DIRS = frozenset({"__pycache__", "node_modules"})
BODY_MAX_LINES = 500
BODY_WARN_LINES = 300
BODY_WARN_TOKENS = 5000
CHARS_PER_TOKEN = 4
TOP_LINES = 40
REFERENCE_TOC_LINES = 100
CONTENTS_WITHIN = 30
EMPHASIS_MAX_LINES = 2


@dataclass
class Finding:
    """One lint result.

    :ivar severity: ``error`` or ``warning``.
    :ivar check: Short check id.
    :ivar message: What is wrong.
    :ivar file: Path relative to the skill directory.
    """

    severity: Severity
    check: str
    message: str
    file: str = "SKILL.md"


@dataclass
class Report:
    """All findings for one skill.

    :ivar skill: Skill directory as given.
    :ivar target: Lint target.
    :ivar findings: Findings in check order.
    """

    skill: str
    target: Target
    findings: list[Finding] = field(default_factory=lambda: list[Finding]())

    def add(
        self, severity: Severity, check: str, message: str, file: str = "SKILL.md"
    ) -> None:
        """Record a finding.

        :param severity: ``error`` or ``warning``.
        :param check: Short check id.
        :param message: What is wrong.
        :param file: Path relative to the skill directory.
        """
        self.findings.append(Finding(severity, check, message, file))

    @property
    def errors(self) -> int:
        """:return: Number of errors."""
        return sum(f.severity == "error" for f in self.findings)

    @property
    def warnings(self) -> int:
        """:return: Number of warnings."""
        return sum(f.severity == "warning" for f in self.findings)


@dataclass
class Document:
    """A Markdown file of the skill.

    :ivar rel: Path relative to the skill directory.
    :ivar lines: File lines.
    :ivar fenced: Per line, whether it is inside fenced code.
    """

    rel: str
    lines: list[str]
    fenced: list[bool]

    @staticmethod
    def of(rel: str, text: str) -> Document:
        """:param rel: Relative path. :param text: Content. :return: The document."""
        lines = text.split("\n")
        return Document(rel, lines, fence_mask(lines))

    def prose(self) -> list[tuple[int, str]]:
        """:return: ``(line number, text)`` for lines outside fenced code."""
        return [(i + 1, t) for i, t in enumerate(self.lines) if not self.fenced[i]]

    def links(self) -> list[str]:
        """:return: Link targets outside fenced code and inline code."""
        found: list[str] = []
        for _, text in self.prose():
            found.extend(LINK_RE.findall(INLINE_CODE_RE.sub("", text)))
        return found

    def code(self) -> list[str]:
        """:return: Fenced code lines and inline code spans."""
        spans = [t for i, t in enumerate(self.lines) if self.fenced[i]]
        for _, text in self.prose():
            spans.extend(INLINE_CODE_RE.findall(text))
        return spans


def load_fields(path: Path = RULES_PATH) -> dict[str, frozenset[str]]:
    """Load the allowed frontmatter fields per target.

    :param path: ``lint_rules.json`` path.
    :return: Target name to allowed fields.
    :raises ValueError: If the file has the wrong shape.
    """
    data: object = json.loads(path.read_text(encoding="utf-8"))
    fields = (
        cast(dict[str, Any], data).get("fields") if isinstance(data, dict) else None
    )
    if not isinstance(fields, dict):
        raise ValueError(f"{path.name}: missing 'fields' object")
    result: dict[str, frozenset[str]] = {}
    for target in ("portable", "claude-code"):
        names = cast(dict[str, Any], fields).get(target)
        if not isinstance(names, list) or not all(
            isinstance(n, str) for n in cast(list[Any], names)
        ):
            raise ValueError(
                f"{path.name}: 'fields.{target}' must be a list of strings"
            )
        result[target] = frozenset(cast(list[str], names))
    return result


# --- Frontmatter ---------------------------------------------------------------


def split_frontmatter(text: str) -> tuple[str | None, str]:
    """Split SKILL.md into frontmatter text and body.

    :param text: SKILL.md content.
    :return: Frontmatter (``None`` when absent or malformed) and the body.
    """
    match = FRONTMATTER_RE.match(text) if text.startswith("---") else None
    if match is None:
        return None, text
    return match.group(1), text[match.end() :].lstrip("\n")


def parse_frontmatter(text: str, report: Report) -> dict[str, Any] | None:
    """Parse the frontmatter mapping, recording structural errors.

    :param text: SKILL.md content.
    :param report: Receives findings.
    :return: The mapping, or ``None`` if it is missing or invalid.
    """
    raw, _ = split_frontmatter(text)
    if raw is None:
        message = (
            "no frontmatter: the opening '---' must be the file's first line"
            if not text.startswith("---")
            else "frontmatter has no closing '---'"
        )
        report.add("error", "frontmatter", message)
        return None
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        report.add("error", "frontmatter", f"invalid YAML: {exc}")
        return None
    if not isinstance(data, dict):
        report.add("error", "frontmatter", "frontmatter must be a YAML mapping")
        return None
    return cast(dict[str, Any], data)


def check_name(
    meta: dict[str, Any], dir_name: str, target: Target, report: Report
) -> None:
    """Check ``name``: format, reserved words, directory match and style.

    :param meta: Frontmatter.
    :param dir_name: Skill directory name.
    :param target: Lint target.
    :param report: Receives findings.
    """
    if "name" not in meta:
        report.add("error", "name", "missing 'name'")
        return
    value = meta["name"]
    if not isinstance(value, str):
        report.add(
            "error", "name", f"'name' must be a string, got {type(value).__name__}"
        )
        return
    name = value.strip()
    for problem in name_problems(name):
        report.add("error", "name", f"'name' {problem}")
    if name and name != dir_name:
        severity: Severity = "error" if target == "portable" else "warning"
        report.add(
            severity, "name-dir", f"'name' ({name}) differs from directory ({dir_name})"
        )
    if style := name_style(name):
        report.add("warning", "name-style", style)


def name_problems(name: str) -> list[str]:
    """List the format rules ``name`` breaks.

    :param name: Stripped ``name`` value.
    :return: One message per broken rule.
    """
    problems: list[str] = []
    if not 1 <= len(name) <= 64:
        problems.append(f"must be 1-64 characters (got {len(name)})")
    if name and not NAME_RE.match(name):
        problems.append("only lowercase letters, digits and hyphens are allowed")
    if name.startswith("-") or name.endswith("-") or "--" in name:
        problems.append("no leading or trailing hyphen and no '--'")
    if "anthropic" in name or "claude" in name:
        problems.append("must not contain 'anthropic' or 'claude'")
    if name in RESERVED_NAMES:
        problems.append(f"'{name}' is reserved")
    return problems


def name_style(name: str) -> str | None:
    """Suggest a better ``name`` style.

    :param name: Stripped ``name`` value.
    :return: A suggestion, or ``None`` if the style is fine.
    """
    segments = name.split("-")
    if name in GENERIC_NAMES or VAGUE_SEGMENTS.intersection(segments):
        return f"'name' ({name}) is vague or generic"
    if name and not any(s.endswith("ing") for s in segments):
        return "consider a gerund name (processing-pdfs); noun phrases are acceptable"
    return None


def check_description(meta: dict[str, Any], target: Target, report: Report) -> None:
    """Check ``description``: type, length, characters, voice and trigger clause.

    :param meta: Frontmatter.
    :param target: Lint target.
    :param report: Receives findings.
    """
    if "description" not in meta:
        report.add("error", "description", "missing 'description'")
        return
    value = meta["description"]
    if not isinstance(value, str):
        report.add(
            "error",
            "description",
            f"'description' must be a string, got {type(value).__name__}",
        )
        return
    text = value.strip()
    if not 1 <= len(text) <= 1024:
        report.add(
            "error",
            "description",
            f"'description' must be 1-1024 characters ({len(text)})",
        )
    if "<" in text or ">" in text:
        report.add("error", "description", "'description' must not contain '<' or '>'")
    when = meta.get("when_to_use")
    if target == "claude-code" and isinstance(when, str):
        combined = len(text) + len(when.strip())
        if combined > 1536:
            report.add(
                "error",
                "description",
                f"'description' + 'when_to_use' exceed 1536 characters ({combined})",
            )
    if match := FIRST_SECOND_PERSON_RE.search(text):
        report.add(
            "warning",
            "description-voice",
            f"write in third person (found '{match.group(0)}')",
        )
    trigger_text = text + " " + (when if isinstance(when, str) else "")
    if text and not TRIGGER_RE.search(trigger_text):
        report.add(
            "warning", "description-trigger", "no trigger clause such as 'Use when ...'"
        )


def check_optional_fields(meta: dict[str, Any], target: Target, report: Report) -> None:
    """Check ``compatibility`` and ``metadata``.

    :param meta: Frontmatter.
    :param target: Lint target.
    :param report: Receives findings.
    """
    if "compatibility" in meta:
        value = meta["compatibility"]
        if not isinstance(value, str) or not 1 <= len(value) <= 500:
            report.add(
                "error",
                "compatibility",
                "'compatibility' must be a 1-500 character string",
            )
    if "metadata" in meta:
        value = meta["metadata"]
        ok = isinstance(value, dict) and all(
            isinstance(k, str) and isinstance(v, str)
            for k, v in cast(dict[Any, Any], value).items()
        )
        if not ok:
            severity: Severity = "error" if target == "portable" else "warning"
            report.add(
                severity, "metadata", "'metadata' must map string keys to string values"
            )


def check_fields(
    meta: dict[str, Any], allowed: frozenset[str], target: Target, report: Report
) -> None:
    """Check that every frontmatter field is allowed for the target.

    :param meta: Frontmatter.
    :param allowed: Allowed fields for the target.
    :param target: Lint target.
    :param report: Receives findings.
    """
    unknown = sorted(str(k) for k in meta if k not in allowed)
    if unknown:
        report.add(
            "warning",
            "fields",
            f"field(s) not allowed for target '{target}': {', '.join(unknown)}",
        )


def check_single_skill_md(skill_dir: Path, report: Report) -> None:
    """Check that the skill packages exactly one SKILL.md (as ``package_skill.py``).

    :param skill_dir: Skill directory.
    :param report: Receives findings.
    """
    extras: list[str] = []
    for path in skill_dir.rglob("SKILL.md"):
        parts = path.relative_to(skill_dir).parts[:-1]
        if not parts or EXCLUDED_DIRS.intersection(parts) or parts[0] == "evals":
            continue
        extras.append(path.relative_to(skill_dir).as_posix())
    if extras:
        report.add(
            "error",
            "single-skill-md",
            f"extra SKILL.md files would be packaged: {', '.join(sorted(extras))}",
        )


def lint_frontmatter(
    skill_dir: Path, text: str, target: Target, fields: dict[str, frozenset[str]]
) -> Report:
    """Run every frontmatter check for one target.

    :param skill_dir: Skill directory.
    :param text: SKILL.md content.
    :param target: Lint target.
    :param fields: Allowed fields per target.
    :return: A report with frontmatter findings only.
    """
    report = Report(str(skill_dir), target)
    meta = parse_frontmatter(text, report)
    if meta is not None:
        check_fields(meta, fields[target], target, report)
        check_name(meta, skill_dir.resolve().name, target, report)
        check_description(meta, target, report)
        check_optional_fields(meta, target, report)
    check_single_skill_md(skill_dir, report)
    return report


# --- Body and structure ------------------------------------------------------------


def check_body(body: str, report: Report) -> None:
    """Check body length, the top of the body and emphasis.

    :param body: SKILL.md without frontmatter.
    :param report: Receives findings.
    """
    lines = body.rstrip("\n").split("\n")
    tokens = len(body) // CHARS_PER_TOKEN
    if len(lines) > BODY_MAX_LINES:
        report.add("error", "body-size", f"body is {len(lines)} lines (max 500)")
    elif len(lines) > BODY_WARN_LINES or tokens > BODY_WARN_TOKENS:
        report.add(
            "warning",
            "body-size",
            f"body is {len(lines)} lines / ~{tokens} tokens (aim for <300 / <5000)",
        )
    doc = Document.of("SKILL.md", body)
    top = [t for n, t in doc.prose() if n <= TOP_LINES]
    if not any(TOP_HEADING_RE.match(t) for t in top):
        report.add(
            "warning",
            "body-top",
            "no workflow, steps or routing heading in the first 40 body lines",
        )
    emphatic = [n for n, t in doc.prose() if EMPHASIS_RE.search(t)]
    if len(emphatic) > EMPHASIS_MAX_LINES:
        report.add(
            "warning",
            "emphasis",
            f"{len(emphatic)} lines use IMPORTANT/MUST/NEVER (max {EMPHASIS_MAX_LINES})",
        )


def local_target(link: str) -> str | None:
    """Return the path part of a relative link, or ``None`` for external ones.

    :param link: Link target.
    :return: Relative path without fragment or query.
    """
    if re.match(r"^[a-z][a-z0-9+.-]*:", link, re.IGNORECASE) or link.startswith("#"):
        return None
    path = link.split("#", 1)[0].split("?", 1)[0]
    return path or None


def resolve_in(base: Path, rel: str, skill_dir: Path) -> Path | None:
    """Resolve ``rel`` against ``base`` if it stays inside the skill.

    :param base: Directory the link is relative to.
    :param rel: Relative path.
    :param skill_dir: Skill directory.
    :return: The resolved path, or ``None`` if it points outside the skill.
    """
    path = (base / rel).resolve()
    return path if path.is_relative_to(skill_dir.resolve()) else None


def referenced_docs(skill_dir: Path, skill_doc: Document) -> list[Path]:
    """List Markdown files linked from SKILL.md inside the skill.

    :param skill_dir: Skill directory.
    :param skill_doc: SKILL.md document.
    :return: Existing linked ``.md`` files, in link order, without duplicates.
    """
    found: dict[Path, None] = {}
    for link in skill_doc.links():
        rel = local_target(link)
        if rel is None or not rel.endswith(".md"):
            continue
        path = resolve_in(skill_dir, rel, skill_dir)
        if path is not None and path.is_file() and path.name != "SKILL.md":
            found[path] = None
    return list(found)


def check_links(
    skill_dir: Path, docs: list[tuple[Path, Document]], report: Report
) -> None:
    """Check relative links and ``${CLAUDE_SKILL_DIR}`` paths exist.

    :param skill_dir: Skill directory.
    :param docs: ``(path, document)`` for SKILL.md and its reference files.
    :param report: Receives findings.
    """
    for path, doc in docs:
        for link in doc.links():
            rel = local_target(link)
            if rel is None or "\\" in rel:
                continue
            if not (path.parent / rel).exists():
                report.add(
                    "error", "broken-link", f"link target not found: {rel}", doc.rel
                )
        for line in doc.lines:
            for rel in SKILL_DIR_PATH_RE.findall(line):
                rel = rel.rstrip(".,;:)")
                if rel and not (skill_dir / rel).exists():
                    report.add(
                        "error",
                        "broken-link",
                        f"${{CLAUDE_SKILL_DIR}} path not found: {rel}",
                        doc.rel,
                    )


def check_reference_structure(
    skill_dir: Path, refs: list[tuple[Path, Document]], report: Report
) -> None:
    """Check reference depth and contents lists in long reference files.

    :param skill_dir: Skill directory.
    :param refs: ``(path, document)`` for each file linked from SKILL.md.
    :param report: Receives findings.
    """
    for path, doc in refs:
        for link in doc.links():
            rel = local_target(link)
            if rel is None or not rel.endswith(".md"):
                continue
            nested = resolve_in(path.parent, rel, skill_dir)
            if nested is not None and nested != path and nested.name != "SKILL.md":
                report.add(
                    "error",
                    "reference-depth",
                    f"links to another reference ({rel}); link it from SKILL.md instead",
                    doc.rel,
                )
        if len(doc.lines) > REFERENCE_TOC_LINES and not any(
            CONTENTS_RE.match(t) for n, t in doc.prose() if n <= CONTENTS_WITHIN
        ):
            report.add(
                "warning",
                "reference-toc",
                f"{len(doc.lines)} lines without a contents list near the top",
                doc.rel,
            )


def check_wording(docs: list[tuple[Path, Document]], report: Report) -> None:
    """Check for Windows paths and time-sensitive text.

    Time-sensitive text under an "Old patterns" heading is allowed.

    :param docs: ``(path, document)`` for SKILL.md and its reference files.
    :param report: Receives findings.
    """
    for _, doc in docs:
        targets = [link for link in doc.links() if "\\" in link]
        for text in targets + [c for c in doc.code() if WINDOWS_PATH_RE.search(c)]:
            report.add(
                "error",
                "windows-path",
                f"use forward slashes: {text.strip()[:60]}",
                doc.rel,
            )
        old_level = 0
        for number, text in doc.prose():
            heading = HEADING_RE.match(text)
            if heading:
                level = len(heading.group(1))
                if old_level and level <= old_level:
                    old_level = 0
                if OLD_PATTERNS_RE.match(text):
                    old_level = level
            if not old_level and (match := TIME_SENSITIVE_RE.search(text)):
                report.add(
                    "warning",
                    "time-sensitive",
                    f"line {number}: '{match.group(0)}'; move it under 'Old patterns'",
                    doc.rel,
                )


def check_scripts(
    skill_dir: Path, docs: list[tuple[Path, Document]], report: Report
) -> None:
    """Warn about scripts that no SKILL.md or reference file mentions.

    Bundled shared modules (``scripts/shared/``) are imported, not run, so they're
    skipped.

    :param skill_dir: Skill directory.
    :param docs: ``(path, document)`` for SKILL.md and its reference files.
    :param report: Receives findings.
    """
    scripts_dir = skill_dir / "scripts"
    if not scripts_dir.is_dir():
        return
    corpus = "\n".join("\n".join(doc.lines) for _, doc in docs)
    for path in sorted(scripts_dir.rglob("*")):
        rel_parts = path.relative_to(skill_dir).parts
        if (
            not path.is_file()
            or path.name == "__init__.py"
            or path.suffix not in SCRIPT_SUFFIXES
            or EXCLUDED_DIRS.intersection(rel_parts)
            or rel_parts[1] == BUNDLE_DIR
        ):
            continue
        module = ".".join(path.with_suffix("").relative_to(skill_dir).parts)
        if path.name not in corpus and module not in corpus:
            report.add(
                "warning",
                "unreferenced-script",
                "not mentioned in SKILL.md or a reference file",
                Path(*rel_parts).as_posix(),
            )


# --- Entry points ----------------------------------------------------------------


def lint(
    skill_dir: Path,
    target: Target = "portable",
    fields: dict[str, frozenset[str]] | None = None,
) -> Report:
    """Lint a skill directory.

    :param skill_dir: Skill directory.
    :param target: ``portable`` or ``claude-code``.
    :param fields: Allowed fields per target (default: ``lint_rules.json``).
    :return: The report.
    """
    fields = fields or load_fields()
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        report = Report(str(skill_dir), target)
        report.add("error", "skill-md", "SKILL.md not found")
        return report
    text = skill_md.read_text(encoding="utf-8")
    report = lint_frontmatter(skill_dir, text, target, fields)
    _, body = split_frontmatter(text)
    check_body(body, report)

    skill_doc = Document.of("SKILL.md", text)
    refs = [
        (
            path,
            Document.of(
                path.relative_to(skill_dir.resolve()).as_posix(),
                path.read_text(encoding="utf-8"),
            ),
        )
        for path in referenced_docs(skill_dir, skill_doc)
    ]
    docs = [(skill_md, skill_doc), *refs]
    check_reference_structure(skill_dir, refs, report)
    check_links(skill_dir, docs, report)
    check_wording(docs, report)
    check_scripts(skill_dir, docs, report)
    return report


def format_text(report: Report) -> str:
    """:param report: Lint report. :return: Human-readable findings and a summary."""
    lines = [
        f"{f.severity.upper():7} {f.file}: [{f.check}] {f.message}"
        for f in report.findings
    ]
    lines.append(f"{report.errors} error(s), {report.warnings} warning(s)")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    """:return: The command-line parser."""
    parser = argparse.ArgumentParser(description="Lint an Agent Skill directory.")
    parser.add_argument("skill_dir", type=Path)
    parser.add_argument(
        "--target", choices=["portable", "claude-code"], default="portable"
    )
    parser.add_argument("--json", action="store_true", help="print JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI.

    :param argv: Arguments (default ``sys.argv[1:]``).
    :return: 0 without errors, 1 with errors or on bad input.
    """
    args = build_parser().parse_args(argv)
    skill_dir = cast(Path, args.skill_dir)
    if not skill_dir.is_dir():
        sys.stderr.write(f"not a directory: {skill_dir}\n")
        return 1
    try:
        report = lint(skill_dir, cast(Target, args.target))
    except (OSError, ValueError) as exc:
        sys.stderr.write(f"lint_skill.py: {exc}\n")
        return 1
    if args.json:
        payload = asdict(report) | {
            "errors": report.errors,
            "warnings": report.warnings,
        }
        print(json.dumps(payload, indent=2))
    else:
        print(format_text(report))
    return 1 if report.errors else 0


if __name__ == "__main__":
    sys.exit(main())
