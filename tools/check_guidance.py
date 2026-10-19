#!/usr/bin/env python3
"""Detect changes to the official guidance a skill condenses in ``official-*.md``.

Fetches the source pages listed in a guidance manifest
(``tools/guidance/<skill>/manifest.json``), extracts each tracked section by heading,
normalizes it, and compares its hash with the stored one. Prints one JSON object on
stdout. Run by the scheduled guidance workflow, which turns changes into a pull
request; the skill itself never runs it.

Exit codes: 0 unchanged or accepted, 10 changed, 11 structure_changed, 20 unreachable,
1 usage or internal error.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import difflib
import hashlib
import json
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, cast

from shared.mdparse import fence_mask

EXIT_CODES: dict[str, int] = {
    "unchanged": 0,
    "accepted": 0,
    "changed": 10,
    "structure_changed": 11,
    "unreachable": 20,
}
USER_AGENT = "agents-check-guidance/2.0 (+https://github.com/paddy74/agents)"
ACCEPTED_MEDIA_TYPES = frozenset({"text/markdown", "text/plain"})
PENDING_MAX_AGE = timedelta(hours=24)
DEFAULT_MAX_AGE_DAYS = 30
REPO_ROOT = Path(__file__).resolve().parent.parent

ATX_RE = re.compile(r"^ {0,3}(#{1,6})(?:[ \t]+(.*?))?[ \t]*$")
HTML_HEADING_RE = re.compile(
    r"^[ \t]*<h([1-6])\b[^>]*>(.*?)</h\1>[ \t]*$", re.MULTILINE | re.DOTALL
)
ANCHOR_RE = re.compile(r"\s*\{#[^}]*\}\s*$")
CLOSING_HASHES_RE = re.compile(r"(?:^|[ \t]+)#+[ \t]*$")
LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")
THEME_RE = re.compile(r"^(\s*(?:`{3,}|~{3,})[^\n]*?)[ \t]+theme=\{[^}\n]*\}", re.M)
MDX_TAG_RE = re.compile(
    r"</?(?:Tip|Note|Warning|Callout|Steps|Step|CardGroup|Card|Frame)\b[^>]*>"
)
VERSION_RE = re.compile(r"\bv\d+\.\d+\.\d+\b")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
AS_OF_RE = re.compile(r"^as_of: .*$", re.MULTILINE)


class ManifestError(ValueError):
    """Raised when the manifest is missing a field or has a bad type."""


class UsageError(ValueError):
    """Raised when the command line names something the manifest lacks."""


class FetchError(Exception):
    """Raised when a source can't be fetched as Markdown or plain text."""


@dataclass
class Section:
    """A tracked guidance section.

    :ivar id: Section id, used for snapshots and ``[id]`` tags in reference files.
    :ivar source: Key into the manifest's ``sources``.
    :ivar target: Reference file that condenses this section.
    :ivar heading: Heading text that starts the section.
    :ivar sha256: Hash of the normalized section text; empty until accepted.
    """

    id: str
    source: str
    target: str
    heading: str
    sha256: str = ""


@dataclass
class Watch:
    """An overlap-watch entry for a built-in this skill defers to.

    Exactly one of ``url``, ``heading`` or ``row`` is set; ``heading`` and ``row``
    also need ``source``. ``match`` narrows a ``url`` watch to matching lines.

    :ivar id: Watch id reported in ``watch_changed``.
    :ivar source: Key into the manifest's ``sources`` (``heading``/``row`` forms).
    :ivar url: Whole file to watch.
    :ivar heading: Section heading to watch.
    :ivar row: Command whose table row to watch.
    :ivar match: Case-insensitive regex; only ``url`` lines matching it are watched.
    :ivar sha256: Hash of the normalized watched text; empty until accepted.
    """

    id: str
    source: str = ""
    url: str = ""
    heading: str = ""
    row: str = ""
    match: str = ""
    sha256: str = ""


@dataclass
class Manifest:
    """Parsed guidance manifest.

    :ivar max_age_days: Days after which an unchanged check re-confirms the date.
    :ivar last_checked: Date the stored guidance was last confirmed current.
    :ivar references_dir: Repo-relative directory holding the ``target`` files.
    :ivar sources: Source key to page URL.
    :ivar watch: Overlap-watch entries.
    :ivar sections: Tracked sections.
    """

    max_age_days: int
    last_checked: date
    references_dir: str
    sources: dict[str, str]
    watch: list[Watch] = field(default_factory=lambda: list[Watch]())
    sections: list[Section] = field(default_factory=lambda: list[Section]())


@dataclass
class Paths:
    """File locations for one manifest.

    :ivar manifest: The manifest file; pending results and snapshots sit beside it.
    :ivar root: Repo root that ``references_dir`` is relative to.
    """

    manifest: Path
    root: Path = REPO_ROOT

    @property
    def pending(self) -> Path:
        """:return: Path of ``.pending.json`` beside the manifest."""
        return self.manifest.parent / ".pending.json"

    @property
    def snapshots(self) -> Path:
        """:return: Path of the ``snapshots/`` directory beside the manifest."""
        return self.manifest.parent / "snapshots"

    def reference(self, manifest: Manifest, target: str) -> Path:
        """Locate a reference file.

        :param manifest: Parsed manifest.
        :param target: Reference file name, as in a section's ``target``.
        :return: Path of that reference file.
        """
        return self.root / manifest.references_dir / target


@dataclass
class CheckResult:
    """Outcome of a check, before it is printed.

    :ivar status: One of the statuses in :data:`EXIT_CODES`.
    :ivar last_checked: Manifest ``last_checked`` after the run.
    :ivar age_days: Days since ``last_checked``.
    :ivar changed: One entry per changed section, with its diff.
    :ivar missing: Ids of tracked sections whose heading wasn't found.
    :ivar watch_changed: Ids of watch entries whose hash differs.
    :ivar errors: Fetch and write problems that didn't stop the run.
    """

    status: str
    last_checked: date
    age_days: int
    changed: list[dict[str, str]] = field(
        default_factory=lambda: list[dict[str, str]]()
    )
    missing: list[str] = field(default_factory=lambda: list[str]())
    watch_changed: list[str] = field(default_factory=lambda: list[str]())
    errors: list[str] = field(default_factory=lambda: list[str]())

    def to_json(self) -> dict[str, Any]:
        """:return: The result as a JSON-serializable mapping."""
        return {
            "status": self.status,
            "last_checked": self.last_checked.isoformat(),
            "age_days": self.age_days,
            "changed": self.changed,
            "missing": self.missing,
            "watch_changed": self.watch_changed,
            "errors": self.errors,
        }


@dataclass
class Pending:
    """Fetched results waiting for ``--accept``.

    :ivar created: When the check that produced them ran (UTC).
    :ivar sections: Section id to raw section text.
    :ivar watch: Watch id to hash of the normalized watched text.
    """

    created: datetime
    sections: dict[str, str]
    watch: dict[str, str]


# --- Manifest -----------------------------------------------------------------


def _require(data: dict[str, Any], key: str, kind: type, where: str) -> Any:
    """Return ``data[key]`` after checking its type.

    :param data: Mapping to read.
    :param key: Key to read.
    :param kind: Expected type.
    :param where: Location for the error message.
    :return: The value.
    :raises ManifestError: If the key is absent or has the wrong type.
    """
    if key not in data:
        raise ManifestError(f"{where}: missing '{key}'")
    value = data[key]
    if not isinstance(value, kind) or (kind is int and isinstance(value, bool)):
        raise ManifestError(f"{where}: '{key}' must be {kind.__name__}")
    return value


def _str_fields(data: dict[str, Any], keys: tuple[str, ...], where: str) -> list[str]:
    """Read optional string fields, defaulting to empty strings.

    :param data: Mapping to read.
    :param keys: Keys to read.
    :param where: Location for the error message.
    :return: The values in ``keys`` order.
    :raises ManifestError: If a present value isn't a string.
    """
    values: list[str] = []
    for key in keys:
        value = data.get(key, "")
        if not isinstance(value, str):
            raise ManifestError(f"{where}: '{key}' must be str")
        values.append(value)
    return values


def _entries(raw: dict[str, Any], key: str) -> list[tuple[str, dict[str, Any]]]:
    """Read a list of objects from the manifest.

    :param raw: Manifest mapping.
    :param key: ``sections`` or ``watch``.
    :return: ``(location, object)`` pairs.
    :raises ManifestError: If the list or an item has the wrong type.
    """
    items = raw.get(key, [])
    if not isinstance(items, list):
        raise ManifestError(f"manifest: '{key}' must be list")
    entries: list[tuple[str, dict[str, Any]]] = []
    for i, item in enumerate(cast(list[Any], items)):
        if not isinstance(item, dict):
            raise ManifestError(f"{key}[{i}]: must be an object")
        entries.append((f"{key}[{i}]", cast(dict[str, Any], item)))
    return entries


def _parse_sections(raw: dict[str, Any], sources: dict[str, str]) -> list[Section]:
    """Parse tracked sections.

    :param raw: Manifest mapping.
    :param sources: Parsed sources.
    :return: The sections.
    :raises ManifestError: On a bad field, unknown source or duplicate id.
    """
    sections: list[Section] = []
    for where, entry in _entries(raw, "sections"):
        sid, source, target, heading = (
            _require(entry, k, str, where)
            for k in ("id", "source", "target", "heading")
        )
        (sha,) = _str_fields(entry, ("sha256",), where)
        if source not in sources:
            raise ManifestError(f"{where}: unknown source '{source}'")
        sections.append(Section(sid, source, target, heading, sha))
    return sections


def _parse_watch(raw: dict[str, Any], sources: dict[str, str]) -> list[Watch]:
    """Parse overlap-watch entries.

    :param raw: Manifest mapping.
    :param sources: Parsed sources.
    :return: The watch entries.
    :raises ManifestError: On a bad field or unknown source.
    """
    watch: list[Watch] = []
    for where, entry in _entries(raw, "watch"):
        wid = _require(entry, "id", str, where)
        source, url, heading, row, match, sha = _str_fields(
            entry, ("source", "url", "heading", "row", "match", "sha256"), where
        )
        if sum(bool(v) for v in (url, heading, row)) != 1:
            raise ManifestError(f"{where}: set exactly one of url, heading, row")
        if (heading or row) and source not in sources:
            raise ManifestError(f"{where}: unknown source '{source}'")
        if match and not url:
            raise ManifestError(f"{where}: match needs url")
        if match:
            try:
                re.compile(match)
            except re.error as exc:
                raise ManifestError(f"{where}: bad match pattern: {exc}") from exc
        watch.append(Watch(wid, source, url, heading, row, match, sha))
    return watch


def parse_manifest(data: object) -> Manifest:
    """Validate and parse manifest JSON.

    :param data: Decoded JSON.
    :return: The parsed manifest.
    :raises ManifestError: On any missing field, bad type or bad reference.
    """
    if not isinstance(data, dict):
        raise ManifestError("manifest must be a JSON object")
    raw = cast(dict[str, Any], data)
    sources: dict[str, str] = {}
    for key, url in cast(
        dict[str, Any], _require(raw, "sources", dict, "manifest")
    ).items():
        if not isinstance(url, str) or not url.startswith("https://"):
            raise ManifestError(f"sources.{key}: must be an https URL")
        sources[key] = url
    try:
        last_checked = date.fromisoformat(
            _require(raw, "last_checked", str, "manifest")
        )
    except (TypeError, ValueError) as exc:
        raise ManifestError(f"manifest: bad date: {exc}") from exc
    sections = _parse_sections(raw, sources)
    watch = _parse_watch(raw, sources)
    ids = [s.id for s in sections] + [w.id for w in watch]
    if len(ids) != len(set(ids)):
        raise ManifestError("manifest: section and watch ids must be unique")
    max_age = raw.get("max_age_days", DEFAULT_MAX_AGE_DAYS)
    if not isinstance(max_age, int) or isinstance(max_age, bool):
        raise ManifestError("manifest: max_age_days must be int")
    references_dir = _require(raw, "references_dir", str, "manifest")
    return Manifest(max_age, last_checked, references_dir, sources, watch, sections)


def manifest_to_json(manifest: Manifest) -> str:
    """Serialize a manifest with one section or watch entry per line.

    :param manifest: Manifest to serialize.
    :return: JSON text ending in a newline.
    """

    def line(obj: dict[str, str]) -> str:
        return json.dumps({k: v for k, v in obj.items() if v or k == "sha256"})

    watch = [
        line(
            {
                "id": w.id,
                "source": w.source,
                "url": w.url,
                "heading": w.heading,
                "row": w.row,
                "match": w.match,
                "sha256": w.sha256,
            }
        )
        for w in manifest.watch
    ]
    sections = [
        line(
            {
                "id": s.id,
                "source": s.source,
                "target": s.target,
                "heading": s.heading,
                "sha256": s.sha256,
            }
        )
        for s in manifest.sections
    ]
    head = {
        "max_age_days": manifest.max_age_days,
        "last_checked": manifest.last_checked.isoformat(),
        "references_dir": manifest.references_dir,
        "sources": manifest.sources,
    }
    body = json.dumps(head, indent=2)[:-2]
    return (
        f"{body},\n"
        f'  "watch": [\n    {",\n    ".join(watch)}\n  ],\n'
        f'  "sections": [\n    {",\n    ".join(sections)}\n  ]\n}}\n'
    )


# --- Markdown parsing (pure) --------------------------------------------------


def html_headings_to_atx(text: str) -> str:
    """Convert line-level HTML headings outside fenced code into ATX headings.

    ``<h4 id="x">\\n  Text\\n</h4>`` becomes ``#### Text``.

    :param text: Markdown text.
    :return: Text with HTML headings converted.
    """
    lines = text.split("\n")
    mask = fence_mask(lines)
    out: list[str] = []
    chunk: list[str] = []

    def flush() -> None:
        if chunk:
            out.append(
                HTML_HEADING_RE.sub(
                    lambda m: (
                        "#" * int(m.group(1)) + " " + " ".join(m.group(2).split())
                    ),
                    "\n".join(chunk),
                )
            )
            chunk.clear()

    for text_line, fenced in zip(lines, mask, strict=True):
        if fenced:
            flush()
            out.append(text_line)
        else:
            chunk.append(text_line)
    flush()
    return "\n".join(out)


def clean_heading(text: str) -> str:
    """Reduce heading text to its comparable form.

    Removes a trailing ``{#anchor}``, closing ``#`` characters, backticks and link
    markup.

    :param text: Raw heading text.
    :return: Cleaned text.
    """
    text = ANCHOR_RE.sub("", text)
    text = CLOSING_HASHES_RE.sub("", text)
    text = LINK_RE.sub(r"\1", text)
    return text.replace("`", "").strip()


def headings(lines: list[str]) -> list[tuple[int, int, str]]:
    """List ATX headings outside fenced code.

    :param lines: Document lines (after :func:`html_headings_to_atx`).
    :return: ``(line index, level, cleaned text)`` per heading.
    """
    found: list[tuple[int, int, str]] = []
    for i, (text, fenced) in enumerate(zip(lines, fence_mask(lines), strict=True)):
        if fenced:
            continue
        match = ATX_RE.match(text)
        if match:
            found.append((i, len(match.group(1)), clean_heading(match.group(2) or "")))
    return found


def extract_section(text: str, heading: str) -> str | None:
    """Extract the first section whose heading matches ``heading``.

    The section runs from its heading line up to the next heading of the same or a
    higher level (lower level number).

    :param text: Markdown text (after :func:`html_headings_to_atx`).
    :param heading: Tracked heading text.
    :return: The section text including its heading, or ``None`` if not found.
    """
    lines = text.split("\n")
    wanted = clean_heading(heading)
    found = headings(lines)
    for pos, (start, level, title) in enumerate(found):
        if title != wanted:
            continue
        end = next((i for i, lvl, _ in found[pos + 1 :] if lvl <= level), len(lines))
        return "\n".join(lines[start:end]).strip("\n") + "\n"
    return None


def extract_row(text: str, command: str) -> str | None:
    """Extract the table row whose first cell starts with ``command``.

    :param text: Markdown text.
    :param command: Command such as ``/doctor``.
    :return: The row line, or ``None`` if not found.
    """
    lines = text.split("\n")
    for line, fenced in zip(lines, fence_mask(lines), strict=True):
        stripped = line.strip()
        if fenced or not stripped.startswith("|"):
            continue
        first = stripped.split("|")[1].replace("`", "").strip()
        if first == command or first.startswith(command + " "):
            return stripped + "\n"
    return None


def extract_lines(text: str, pattern: str) -> str | None:
    """Keep the lines that match ``pattern``, case-insensitively.

    :param text: File text.
    :param pattern: Regular expression searched in each line.
    :return: Matching lines joined with newlines, or ``None`` if none match.
    """
    regex = re.compile(pattern, re.IGNORECASE)
    found = [line for line in text.split("\n") if regex.search(line)]
    return "\n".join(found) + "\n" if found else None


def normalize(text: str) -> str:
    """Normalize section text for hashing only.

    Removes fence ``theme={...}`` strings, link targets, MDX component tags and
    sentences that mention a version (``v2.1.0``), then collapses whitespace.

    :param text: Raw section text.
    :return: Normalized text.
    """
    text = THEME_RE.sub(r"\1", text)
    text = LINK_RE.sub(r"[\1]()", text)
    text = MDX_TAG_RE.sub("", text)
    kept_lines: list[str] = []
    for line in text.split("\n"):
        sentences = SENTENCE_SPLIT_RE.split(line)
        kept_lines.append(" ".join(s for s in sentences if not VERSION_RE.search(s)))
    return " ".join("\n".join(kept_lines).split())


def digest(text: str) -> str:
    """:param text: Raw text. :return: SHA-256 hex digest of ``normalize(text)``."""
    return hashlib.sha256(normalize(text).encode()).hexdigest()


def section_diff(old: str, new: str, section_id: str) -> str:
    """Unified diff with 2 lines of context.

    :param old: Stored snapshot text.
    :param new: Fetched section text.
    :param section_id: Used in the file labels.
    :return: The diff text.
    """
    return "".join(
        difflib.unified_diff(
            old.splitlines(keepends=True),
            new.splitlines(keepends=True),
            fromfile=f"snapshots/{section_id}.md",
            tofile=f"live/{section_id}.md",
            n=2,
        )
    )


def set_as_of(text: str, day: date) -> str:
    """Set the ``as_of:`` date in a reference file's frontmatter.

    Replaces an existing ``as_of:`` line, or adds one after the opening ``---``.

    :param text: Reference file text, starting with YAML frontmatter.
    :param day: Date to record.
    :return: The updated text.
    :raises ValueError: If the text has no frontmatter.
    """
    if not text.startswith("---\n"):
        raise ValueError("reference file has no frontmatter")
    end = text.find("\n---\n", 3)
    if end < 0:
        raise ValueError("reference file frontmatter is not closed")
    head, rest = text[: end + 1], text[end + 1 :]
    line = f"as_of: {day.isoformat()}"
    if AS_OF_RE.search(head):
        head = AS_OF_RE.sub(line, head, count=1)
    else:
        head = f"---\n{line}\n{head[4:]}"
    return head + rest


# --- I/O ----------------------------------------------------------------------


def media_type(content_type: str | None) -> str:
    """:param content_type: A ``Content-Type`` header value. :return: Its media type."""
    return (content_type or "").split(";")[0].strip().lower()


def _get(url: str, timeout: float, accept: str | None) -> str:
    """GET ``url`` and return its body if it is Markdown or plain text.

    :param url: URL to fetch.
    :param timeout: Timeout in seconds.
    :param accept: Optional ``Accept`` header.
    :return: Decoded body.
    :raises FetchError: On network errors or another media type.
    """
    headers = {"User-Agent": USER_AGENT}
    if accept:
        headers["Accept"] = accept
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            kind = media_type(response.headers.get("Content-Type"))
            if kind not in ACCEPTED_MEDIA_TYPES:
                raise FetchError(f"{url}: unexpected media type '{kind}'")
            body = cast(bytes, response.read())
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise FetchError(f"{url}: {exc}") from exc
    return body.decode("utf-8", errors="replace")


def fetch(url: str, timeout: float) -> str:
    """Fetch ``url`` as Markdown.

    Tries ``<url>.md`` first (skipped when the last path segment already has a file
    extension), then ``<url>`` with ``Accept: text/markdown``.

    :param url: Page URL.
    :param timeout: Per-request timeout in seconds.
    :return: Page text.
    :raises FetchError: If both attempts fail.
    """
    first_error = ""
    if "." not in url.rstrip("/").rsplit("/", 1)[-1]:
        try:
            return _get(url + ".md", timeout, None)
        except FetchError as exc:
            first_error = f"{exc}; "
    try:
        return _get(url, timeout, "text/markdown, text/plain;q=0.9")
    except FetchError as exc:
        raise FetchError(f"{first_error}{exc}") from exc


def fetch_all(urls: list[str], timeout: float) -> dict[str, str | FetchError]:
    """Fetch distinct URLs concurrently.

    :param urls: URLs to fetch.
    :param timeout: Per-request timeout in seconds.
    :return: URL to text, or to the error that stopped it.
    """
    distinct = list(dict.fromkeys(urls))
    results: dict[str, str | FetchError] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(fetch, url, timeout): url for url in distinct}
        for future in concurrent.futures.as_completed(futures):
            url = futures[future]
            try:
                results[url] = future.result()
            except FetchError as exc:
                results[url] = exc
    return results


def load_pending(path: Path) -> Pending | None:
    """Load ``.pending.json``.

    :param path: Pending file path.
    :return: Pending results, or ``None`` if absent or unreadable.
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return Pending(
            datetime.fromisoformat(data["created"]),
            {str(k): str(v) for k, v in data["sections"].items()},
            {str(k): str(v) for k, v in data["watch"].items()},
        )
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None


# --- Check and accept ---------------------------------------------------------


@dataclass
class Fetched:
    """Sections and watch hashes resolved from fetched sources.

    :ivar texts: Section id to raw section text, for found sections.
    :ivar watch: Watch id to hash, for resolved watch entries.
    :ivar missing: Section ids whose heading wasn't found.
    :ivar errors: Fetch and resolution errors.
    :ivar reachable: Whether any guidance source was fetched.
    """

    texts: dict[str, str]
    watch: dict[str, str]
    missing: list[str]
    errors: list[str]
    reachable: bool


def resolve(manifest: Manifest, pages: dict[str, str | FetchError]) -> Fetched:
    """Extract tracked sections and watched text from fetched pages.

    :param manifest: Parsed manifest.
    :param pages: Result of :func:`fetch_all`.
    :return: Resolved sections, watch hashes, missing ids and errors.
    """
    errors = [str(v) for v in pages.values() if isinstance(v, FetchError)]
    prepared: dict[str, str] = {
        key: html_headings_to_atx(page)
        for key, url in manifest.sources.items()
        if isinstance(page := pages.get(url), str)
    }
    reachable = any(
        isinstance(pages.get(manifest.sources[s.source]), str)
        for s in manifest.sections
    )
    texts: dict[str, str] = {}
    missing: list[str] = []
    for section in manifest.sections:
        page = prepared.get(section.source)
        if page is None:
            continue
        found = extract_section(page, section.heading)
        if found is None:
            missing.append(section.id)
        else:
            texts[section.id] = found

    watch: dict[str, str] = {}
    for entry in manifest.watch:
        text, error = watched_text(entry, pages, prepared)
        if error:
            errors.append(error)
        elif text is not None:
            watch[entry.id] = digest(text)
    return Fetched(texts, watch, missing, errors, reachable)


def watched_text(
    entry: Watch, pages: dict[str, str | FetchError], prepared: dict[str, str]
) -> tuple[str | None, str | None]:
    """Find the text one watch entry covers.

    A failed ``url`` fetch gives neither text nor error here; :func:`resolve`
    already reports the fetch error.

    :param entry: Watch entry.
    :param pages: Result of :func:`fetch_all`.
    :param prepared: Source key to page text after the HTML heading pre-pass.
    :return: The watched text and an error message; at most one is set.
    """
    if entry.url:
        raw = pages.get(entry.url)
        if not isinstance(raw, str):
            return None, None
        if not entry.match:
            return raw, None
        text = extract_lines(raw, entry.match)
        if text is None:
            return None, f"watch {entry.id}: no line matches '{entry.match}'"
        return text, None
    page = prepared.get(entry.source)
    if page is None:
        return None, f"watch {entry.id}: source '{entry.source}' unavailable"
    if entry.heading:
        text = extract_section(page, entry.heading)
    else:
        text = extract_row(page, entry.row)
    if text is None:
        return None, f"watch {entry.id}: not found in '{entry.source}'"
    return text, None


def all_urls(manifest: Manifest) -> list[str]:
    """:param manifest: Manifest. :return: Every source and watch URL."""
    return list(manifest.sources.values()) + [w.url for w in manifest.watch if w.url]


def compare(manifest: Manifest, fetched: Fetched, paths: Paths) -> CheckResult:
    """Compare resolved sections and watch hashes with the manifest.

    :param manifest: Parsed manifest.
    :param fetched: Output of :func:`resolve`.
    :param paths: File locations, for reading snapshots.
    :return: The check result (``last_checked``/``age_days`` filled by the caller).
    """
    result = CheckResult("unchanged", manifest.last_checked, 0, errors=fetched.errors)
    if not fetched.reachable:
        result.status = "unreachable"
        return result
    for section in manifest.sections:
        text = fetched.texts.get(section.id)
        if text is None or digest(text) == section.sha256:
            continue
        try:
            old = (paths.snapshots / f"{section.id}.md").read_text(encoding="utf-8")
        except OSError:
            old = ""
        result.changed.append(
            {
                "id": section.id,
                "target": section.target,
                "url": manifest.sources[section.source],
                "diff": section_diff(old, text, section.id),
            }
        )
    result.missing = list(fetched.missing)
    result.watch_changed = [
        w.id
        for w in manifest.watch
        if w.id in fetched.watch and fetched.watch[w.id] != w.sha256
    ]
    if result.missing:
        result.status = "structure_changed"
    elif result.changed:
        result.status = "changed"
    return result


def run_check(
    manifest: Manifest, paths: Paths, today: date, timeout: float
) -> tuple[CheckResult, Fetched]:
    """Fetch and compare; save what was fetched for ``--accept``.

    Never changes the manifest.

    :param manifest: Parsed manifest.
    :param paths: File locations.
    :param today: Current date.
    :param timeout: Per-request timeout in seconds.
    :return: The result and the resolved data.
    :raises OSError: If the pending file can't be written.
    """
    fetched = resolve(manifest, fetch_all(all_urls(manifest), timeout))
    result = compare(manifest, fetched, paths)
    result.age_days = (today - manifest.last_checked).days
    if fetched.reachable:
        pending = {
            "created": datetime.now(UTC).isoformat(),
            "sections": fetched.texts,
            "watch": fetched.watch,
        }
        paths.pending.write_text(json.dumps(pending, indent=1), encoding="utf-8")
    return result, fetched


def current_pending(
    manifest: Manifest, paths: Paths, today: date, timeout: float
) -> tuple[Pending | None, CheckResult | None]:
    """Load the pending results, re-fetching if they're absent or over 24 hours old.

    :param manifest: Parsed manifest.
    :param paths: File locations.
    :param today: Current date.
    :param timeout: Per-request timeout in seconds.
    :return: The pending results and, when a re-fetch ran, its result; the pending
        results are ``None`` when the re-fetch reached no source.
    """
    pending = load_pending(paths.pending)
    if pending is not None and datetime.now(UTC) - pending.created <= PENDING_MAX_AGE:
        return pending, None
    result, fetched = run_check(manifest, paths, today, timeout)
    if result.status == "unreachable":
        return None, result
    return Pending(datetime.now(UTC), fetched.texts, fetched.watch), result


def run_accept(
    manifest: Manifest, paths: Paths, today: date, *, timeout: float
) -> CheckResult:
    """Store pending sections, their hashes and today's date.

    Also writes ``as_of`` into every target reference file. Watch hashes are left
    alone; :func:`run_accept_watch` stores them.

    :param manifest: Parsed manifest.
    :param paths: File locations.
    :param today: Current date.
    :param timeout: Per-request timeout in seconds.
    :return: An ``accepted`` result, or the failed check's result.
    :raises OSError: If a file can't be read or written.
    :raises ValueError: If a reference file has no frontmatter.
    """
    pending, fetched = current_pending(manifest, paths, today, timeout)
    if pending is None:
        assert fetched is not None
        return fetched
    errors = fetched.errors if fetched else []
    missing = [s.id for s in manifest.sections if s.id not in pending.sections]

    paths.snapshots.mkdir(exist_ok=True)
    for section in manifest.sections:
        text = pending.sections.get(section.id)
        if text is not None:
            (paths.snapshots / f"{section.id}.md").write_text(text, encoding="utf-8")
            section.sha256 = digest(text)
    for target in dict.fromkeys(s.target for s in manifest.sections):
        path = paths.reference(manifest, target)
        path.write_text(
            set_as_of(path.read_text(encoding="utf-8"), today), encoding="utf-8"
        )
    manifest.last_checked = today
    paths.manifest.write_text(manifest_to_json(manifest), encoding="utf-8")
    status = "structure_changed" if missing else "accepted"
    return CheckResult(status, today, 0, missing=missing, errors=errors)


def run_accept_watch(
    manifest: Manifest, paths: Paths, today: date, ids: list[str], *, timeout: float
) -> CheckResult:
    """Store the pending hashes of the named watch entries only.

    :param manifest: Parsed manifest.
    :param paths: File locations.
    :param today: Current date.
    :param ids: Watch ids to accept.
    :param timeout: Per-request timeout in seconds.
    :return: An ``accepted`` result, or the failed check's result.
    :raises UsageError: If an id isn't a watch entry or wasn't resolved.
    :raises OSError: If the manifest can't be written.
    """
    entries = {w.id: w for w in manifest.watch}
    unknown = [i for i in ids if i not in entries]
    if unknown:
        raise UsageError(f"unknown watch id: {', '.join(unknown)}")
    pending, fetched = current_pending(manifest, paths, today, timeout)
    if pending is None:
        assert fetched is not None
        return fetched
    unresolved = [i for i in ids if i not in pending.watch]
    if unresolved:
        raise UsageError(f"watch not resolved: {', '.join(unresolved)}")
    for wid in ids:
        entries[wid].sha256 = pending.watch[wid]
    paths.manifest.write_text(manifest_to_json(manifest), encoding="utf-8")
    age = (today - manifest.last_checked).days
    return CheckResult("accepted", manifest.last_checked, age)


def build_parser() -> argparse.ArgumentParser:
    """:return: The command-line parser."""
    parser = argparse.ArgumentParser(
        description="Detect changes to the official guidance sources."
    )
    parser.add_argument("--manifest", type=Path, required=True, metavar="PATH")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--accept", action="store_true", help="store sections, hashes and the date"
    )
    mode.add_argument(
        "--accept-watch", nargs="+", metavar="ID", help="store these watch hashes"
    )
    parser.add_argument("--timeout", type=float, default=10.0, metavar="SECONDS")
    return parser


def main(
    argv: list[str] | None = None,
    *,
    root: Path = REPO_ROOT,
    today: date | None = None,
) -> int:
    """Run the CLI.

    :param argv: Arguments (default ``sys.argv[1:]``).
    :param root: Repo root that ``references_dir`` is relative to.
    :param today: Current date (default: today, local time).
    :return: Exit code.
    """
    args = build_parser().parse_args(argv)
    paths = Paths(cast(Path, args.manifest), root)
    today = today or date.today()
    watch_ids = cast(list[str] | None, args.accept_watch)
    try:
        manifest = parse_manifest(
            json.loads(paths.manifest.read_text(encoding="utf-8"))
        )
        if args.accept:
            result = run_accept(manifest, paths, today, timeout=args.timeout)
        elif watch_ids:
            result = run_accept_watch(
                manifest, paths, today, watch_ids, timeout=args.timeout
            )
        else:
            result, _ = run_check(manifest, paths, today, args.timeout)
    except (ValueError, OSError) as exc:
        print(json.dumps({"status": "error", "errors": [str(exc)]}))
        return 1
    print(json.dumps(result.to_json(), indent=2))
    return EXIT_CODES[result.status]


if __name__ == "__main__":
    sys.exit(main())
