"""Tests for ``check_guidance.py``. No network: ``urlopen`` is replaced per test."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import check_guidance as cg
import pytest

TODAY = date(2026, 10, 16)
OLD = "2026-08-01"

MEM_URL = "https://docs.example/mem"
CMDS_URL = "https://docs.example/cmds"
RAW_URL = "https://raw.example/SKILL.md"
CHANGELOG_URL = "https://raw.example/CHANGELOG.md"

MEM_PAGE = """\
# Memory

## Write effective instructions

Be concrete. See [the docs](/docs/a).

### Audit your instruction files

Run the audit.

```bash theme={null}
# not a heading
```

## Rules

#### Path-specific rules

Rules here.

````markdown
## Extract PDF text
````

<h4 id="rules-ref">
  Rule frontmatter reference
</h4>

Reference body.

## Last
"""

CMDS_PAGE = """\
# Commands

| Command | Purpose |
| :- | :- |
| `/debug` | Debug. |
| `/doctor [prompt-audit [path]]` | **Skill.** Run a setup checkup with a very long single-line description. Alias: `/checkup` |
| `/doctorx` | Not it. |
"""

REFERENCE = "---\nsources:\n  mem: https://docs.example/mem\n---\n# Guidance\n"

RAW_FILE = "---\nname: skill-creator\n---\nBody\n"
CHANGELOG = (
    "# Changelog\n\n## 2.0.2\n- Fixed a crash on start\n\n"
    "## 2.0.1\n- Added `/doctor prompt-audit` for instruction files\n"
)


@dataclass
class FakeResponse:
    """Minimal stand-in for an ``urlopen`` response.

    :ivar body: Response body.
    :ivar content_type: ``Content-Type`` header.
    """

    body: str
    content_type: str = "text/markdown; charset=utf-8"
    headers: dict[str, str] = field(default_factory=lambda: dict[str, str]())

    def __post_init__(self) -> None:
        """Fill the headers from ``content_type``."""
        self.headers = {"Content-Type": self.content_type}

    def read(self) -> bytes:
        """:return: The encoded body."""
        return self.body.encode()

    def __enter__(self) -> FakeResponse:
        """:return: Self."""
        return self

    def __exit__(self, *_: object) -> None:
        """Do nothing."""


Route = FakeResponse | Exception


@dataclass
class FakeNet:
    """Routes requests by full URL and records them.

    :ivar routes: URL to response or exception; unknown URLs raise ``URLError``.
    :ivar calls: Requested URLs in order.
    """

    routes: dict[str, Route]
    calls: list[str] = field(default_factory=lambda: list[str]())

    def __call__(self, request: urllib.request.Request, timeout: float) -> Any:
        """Serve one request.

        :param request: The request.
        :param timeout: Ignored.
        :return: The routed response.
        :raises Exception: The routed exception.
        """
        url = request.full_url
        self.calls.append(url)
        route = self.routes.get(url, urllib.error.URLError("no route"))
        if isinstance(route, Exception):
            raise route
        return route


def pages(
    mem: str = MEM_PAGE,
    cmds: str = CMDS_PAGE,
    raw: str = RAW_FILE,
    changelog: str = CHANGELOG,
) -> dict[str, Route]:
    """Build routes serving each page at ``<url>.md``.

    :param mem: Memory page text.
    :param cmds: Commands page text.
    :param raw: Watched raw file text.
    :param changelog: Watched changelog text.
    :return: Routes for :class:`FakeNet`.
    """
    return {
        MEM_URL + ".md": FakeResponse(mem),
        CMDS_URL + ".md": FakeResponse(cmds),
        RAW_URL: FakeResponse(raw, "text/plain; charset=utf-8"),
        CHANGELOG_URL: FakeResponse(changelog, "text/plain; charset=utf-8"),
    }


def base_manifest(**overrides: Any) -> dict[str, Any]:
    """Build manifest JSON for the fake pages.

    :param overrides: Top-level keys to replace.
    :return: Manifest JSON.
    """
    manifest: dict[str, Any] = {
        "max_age_days": 30,
        "last_checked": OLD,
        "references_dir": "refs",
        "sources": {"mem": MEM_URL, "cmds": CMDS_URL},
        "watch": [
            {"id": "w-row", "source": "cmds", "row": "/doctor", "sha256": ""},
            {"id": "w-head", "source": "mem", "heading": "Last", "sha256": ""},
            {"id": "w-url", "url": RAW_URL, "sha256": ""},
            {
                "id": "w-lines",
                "url": CHANGELOG_URL,
                "match": "prompt-audit",
                "sha256": "",
            },
        ],
        "sections": [
            {
                "id": "write",
                "source": "mem",
                "target": "official-instructions.md",
                "heading": "Write effective instructions",
                "sha256": "",
            },
            {
                "id": "audit",
                "source": "mem",
                "target": "official-instructions.md",
                "heading": "Audit your instruction files",
                "sha256": "",
            },
            {
                "id": "paths",
                "source": "mem",
                "target": "official-instructions.md",
                "heading": "Path-specific rules",
                "sha256": "",
            },
        ],
    }
    manifest.update(overrides)
    return manifest


@dataclass
class Repo:
    """A temporary repo with a manifest and a reference file, on a fake network.

    :ivar dir: Repo root.
    :ivar net: The fake network.
    """

    dir: Path
    net: FakeNet

    @property
    def manifest_path(self) -> Path:
        """:return: Manifest path."""
        return self.dir / "guidance" / "manifest.json"

    @property
    def pending_path(self) -> Path:
        """:return: Pending file path."""
        return self.dir / "guidance" / ".pending.json"

    @property
    def snapshots(self) -> Path:
        """:return: Snapshot directory."""
        return self.dir / "guidance" / "snapshots"

    @property
    def reference(self) -> Path:
        """:return: The reference file the sections target."""
        return self.dir / "refs" / "official-instructions.md"

    def manifest(self) -> dict[str, Any]:
        """:return: The manifest JSON on disk."""
        return json.loads(self.manifest_path.read_text())

    def write_manifest(self, data: dict[str, Any]) -> None:
        """:param data: Manifest JSON to write."""
        self.manifest_path.write_text(json.dumps(data))

    def run(
        self, capsys: pytest.CaptureFixture[str], *argv: str
    ) -> tuple[int, dict[str, Any]]:
        """Run the CLI.

        :param capsys: Pytest capture fixture.
        :param argv: CLI arguments.
        :return: Exit code and parsed JSON output.
        """
        args = ["--manifest", str(self.manifest_path), *argv]
        code = cg.main(args, root=self.dir, today=TODAY)
        return code, json.loads(capsys.readouterr().out)

    def accept_baseline(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Accept the current pages and watch entries, then backdate the manifest.

        :param capsys: Pytest capture fixture.
        """
        assert self.run(capsys, "--accept")[0] == 0
        ids = [w["id"] for w in self.manifest()["watch"]]
        assert self.run(capsys, "--accept-watch", *ids)[0] == 0
        data = self.manifest()
        data["last_checked"] = OLD
        self.write_manifest(data)
        self.net.calls.clear()


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Repo]:
    """Create a repo with a manifest and reference file, and patch ``urlopen``.

    :param tmp_path: Pytest temp directory.
    :param monkeypatch: Pytest monkeypatch.
    :return: The repo fixture.
    """
    (tmp_path / "guidance").mkdir()
    (tmp_path / "refs").mkdir()
    net = FakeNet(pages())
    monkeypatch.setattr(cg.urllib.request, "urlopen", net)
    result = Repo(tmp_path, net)
    result.write_manifest(base_manifest())
    result.reference.write_text(REFERENCE)
    yield result


# --- CLI behaviour --------------------------------------------------------------


def test_unchanged_after_accept(repo: Repo, capsys: pytest.CaptureFixture[str]) -> None:
    """Sections identical to the snapshots are ``unchanged``; nothing is stored."""
    repo.accept_baseline(capsys)
    code, out = repo.run(capsys)
    assert (code, out["status"], out["changed"], out["watch_changed"]) == (
        0,
        "unchanged",
        [],
        [],
    )
    assert out["age_days"] == (TODAY - date.fromisoformat(OLD)).days
    assert repo.manifest()["last_checked"] == OLD


def test_one_section_changed(repo: Repo, capsys: pytest.CaptureFixture[str]) -> None:
    """An edit reports only that section, with its target and a diff."""
    repo.accept_baseline(capsys)
    repo.net.routes.update(pages(mem=MEM_PAGE.replace("Rules here.", "Rules moved.")))
    code, out = repo.run(capsys)
    assert (code, out["status"]) == (10, "changed")
    assert [c["id"] for c in out["changed"]] == ["paths"]
    change = out["changed"][0]
    assert change["target"] == "official-instructions.md"
    assert change["url"] == MEM_URL
    assert "-Rules here." in change["diff"] and "+Rules moved." in change["diff"]
    assert repo.manifest()["last_checked"] == OLD


@pytest.mark.parametrize(
    "edit",
    [
        ("Be concrete.", "Be concrete. Requires v2.1.300 or later."),
        ("Run the audit.", "Before v2.1.217, run the audit. Run the audit."),
        ("(/docs/a)", "(/docs/b)"),
        ("theme={null}", 'theme={"dark"}'),
        ("Rules here.", "Rules   here.  "),
    ],
    ids=["version-sentence", "version-gated", "link-target", "fence-theme", "spaces"],
)
def test_noise_only_changes_are_unchanged(
    repo: Repo, capsys: pytest.CaptureFixture[str], edit: tuple[str, str]
) -> None:
    """Version notes, link targets, fence themes and spacing don't count."""
    repo.accept_baseline(capsys)
    repo.net.routes.update(pages(mem=MEM_PAGE.replace(*edit)))
    code, out = repo.run(capsys)
    assert (code, out["status"]) == (0, "unchanged")


def test_missing_heading_is_structure_changed(
    repo: Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    """A tracked heading that's gone is reported; other sections are still diffed."""
    repo.accept_baseline(capsys)
    page = MEM_PAGE.replace("Path-specific rules", "Scoped rules").replace(
        "Be concrete.", "Be specific."
    )
    repo.net.routes.update(pages(mem=page))
    code, out = repo.run(capsys)
    assert (code, out["status"], out["missing"]) == (11, "structure_changed", ["paths"])
    assert [c["id"] for c in out["changed"]] == ["write"]


def test_all_fetches_fail(repo: Repo, capsys: pytest.CaptureFixture[str]) -> None:
    """Total failure is ``unreachable`` and writes nothing."""
    repo.net.routes.clear()
    code, out = repo.run(capsys)
    assert (code, out["status"]) == (20, "unreachable")
    assert out["errors"]
    assert repo.manifest() == base_manifest()
    assert not repo.pending_path.exists()


def test_html_md_url_falls_back_to_accept_header(
    repo: Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    """When ``<url>.md`` returns HTML, the plain URL is fetched as Markdown."""
    repo.net.routes[MEM_URL + ".md"] = FakeResponse("<html/>", "text/html")
    repo.net.routes[MEM_URL] = FakeResponse(MEM_PAGE)
    _, out = repo.run(capsys)
    assert out["status"] == "changed"
    assert MEM_URL in repo.net.calls


def test_accept_header_sent_on_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """The fallback request asks for Markdown and identifies itself."""
    seen: list[urllib.request.Request] = []

    def opener(request: urllib.request.Request, timeout: float) -> FakeResponse:
        seen.append(request)
        if request.full_url.endswith(".md"):
            raise urllib.error.HTTPError(request.full_url, 404, "nf", {}, None)  # type: ignore[arg-type]
        return FakeResponse("# ok")

    monkeypatch.setattr(cg.urllib.request, "urlopen", opener)
    assert cg.fetch(MEM_URL, 1) == "# ok"
    assert "text/markdown" in (seen[1].get_header("Accept") or "")
    assert seen[1].get_header("User-agent") == cg.USER_AGENT


def test_url_with_extension_skips_md_suffix(monkeypatch: pytest.MonkeyPatch) -> None:
    """Raw files are fetched once, without appending ``.md``."""
    net = FakeNet(pages())
    monkeypatch.setattr(cg.urllib.request, "urlopen", net)
    cg.fetch(RAW_URL, 1)
    assert net.calls == [RAW_URL]


@pytest.mark.parametrize(
    ("content_type", "accepted"),
    [
        ("text/markdown; charset=utf-8", True),
        ("text/plain", True),
        ("Text/Markdown", True),
        ("text/html; charset=utf-8", False),
        (None, False),
    ],
)
def test_media_type_acceptance(content_type: str | None, accepted: bool) -> None:
    """Only Markdown and plain text media types are accepted."""
    assert (cg.media_type(content_type) in cg.ACCEPTED_MEDIA_TYPES) is accepted


def test_accept_uses_pending_without_refetch(
    repo: Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    """``--accept`` after a check writes from the pending file."""
    repo.run(capsys)
    assert repo.pending_path.exists()
    repo.net.calls.clear()
    code, out = repo.run(capsys, "--accept")
    assert (code, out["status"]) == (0, "accepted")
    assert repo.net.calls == []
    data = repo.manifest()
    assert data["last_checked"] == TODAY.isoformat()
    assert all(s["sha256"] for s in data["sections"])
    snapshot = (repo.snapshots / "paths.md").read_text()
    assert snapshot.startswith("#### Path-specific rules")


def test_accept_writes_date_into_reference(
    repo: Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    """``--accept`` records today as ``as_of`` in each target reference file."""
    repo.run(capsys, "--accept")
    text = repo.reference.read_text()
    assert text.startswith(f"---\nas_of: {TODAY.isoformat()}\nsources:")
    assert text.endswith("# Guidance\n")


def test_accept_without_frontmatter_is_an_error(
    repo: Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    """A reference file without frontmatter can't take a date."""
    repo.reference.write_text("# Guidance\n")
    code, out = repo.run(capsys, "--accept")
    assert (code, out["status"]) == (1, "error")


@pytest.mark.parametrize("stale", [False, True], ids=["no-pending", "stale-pending"])
def test_accept_refetches_without_fresh_pending(
    repo: Repo, capsys: pytest.CaptureFixture[str], stale: bool
) -> None:
    """``--accept`` re-fetches when the pending file is absent or over 24 hours old."""
    if stale:
        created = datetime.now(UTC) - timedelta(hours=25)
        repo.pending_path.write_text(
            json.dumps(
                {
                    "created": created.isoformat(),
                    "sections": {"write": "x"},
                    "watch": {},
                }
            )
        )
    code, out = repo.run(capsys, "--accept")
    assert (code, out["status"]) == (0, "accepted")
    assert repo.net.calls
    assert (repo.snapshots / "write.md").read_text() != "x"


def test_accept_leaves_watch_hashes(
    repo: Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    """``--accept`` stores sections only; watch hashes need ``--accept-watch``."""
    repo.run(capsys, "--accept")
    assert not any(w["sha256"] for w in repo.manifest()["watch"])


def test_accept_watch_stores_only_named_hashes(
    repo: Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    """``--accept-watch`` fills in the named watch hashes and nothing else."""
    code, out = repo.run(capsys, "--accept-watch", "w-row", "w-url")
    assert (code, out["status"]) == (0, "accepted")
    data = repo.manifest()
    assert [w["id"] for w in data["watch"] if w["sha256"]] == ["w-row", "w-url"]
    assert not any(s["sha256"] for s in data["sections"])
    assert data["last_checked"] == OLD


def test_accept_watch_clears_the_alert(
    repo: Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    """After a watch change is accepted, the next check no longer reports it."""
    repo.accept_baseline(capsys)
    repo.net.routes.update(pages(raw=RAW_FILE + "More.\n"))
    assert repo.run(capsys)[1]["watch_changed"] == ["w-url"]
    repo.run(capsys, "--accept-watch", "w-url")
    assert repo.run(capsys)[1]["watch_changed"] == []


def test_accept_watch_unknown_id_is_an_error(
    repo: Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    """An id that isn't a watch entry is a usage error and fetches nothing."""
    code, out = repo.run(capsys, "--accept-watch", "write")
    assert (code, out["status"]) == (1, "error")
    assert "unknown watch id: write" in out["errors"][0]
    assert repo.net.calls == []


def test_accept_unreachable_writes_nothing(
    repo: Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    """``--accept`` with no pending file and no network stores no hashes."""
    repo.net.routes.clear()
    code, out = repo.run(capsys, "--accept")
    assert (code, out["status"]) == (20, "unreachable")
    assert not repo.snapshots.exists()
    assert not any(s["sha256"] for s in repo.manifest()["sections"])


def test_nested_sections_both_reported(
    repo: Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    """An edit inside a nested tracked section flags the outer one too."""
    repo.accept_baseline(capsys)
    repo.net.routes.update(pages(mem=MEM_PAGE.replace("Run the audit.", "Audit it.")))
    _, out = repo.run(capsys)
    assert sorted(c["id"] for c in out["changed"]) == ["audit", "write"]


def test_watch_change_does_not_affect_status(
    repo: Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    """Each watch form reports changes without changing ``status``."""
    repo.accept_baseline(capsys)
    cmds = CMDS_PAGE.replace("very long", "much longer")
    mem = MEM_PAGE + "Appended to the last section.\n"
    changelog = CHANGELOG + "- Improved prompt-audit ordering\n"
    repo.net.routes.update(
        pages(mem=mem, cmds=cmds, raw=RAW_FILE + "More.\n", changelog=changelog)
    )
    code, out = repo.run(capsys)
    assert (code, out["status"]) == (0, "unchanged")
    assert sorted(out["watch_changed"]) == ["w-head", "w-lines", "w-row", "w-url"]
    assert repo.manifest()["last_checked"] == OLD


def test_match_watch_ignores_other_lines(
    repo: Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    """New changelog lines that don't match the pattern don't flag the watch."""
    repo.accept_baseline(capsys)
    changelog = "# Changelog\n\n## 2.0.3\n- Faster startup\n\n" + CHANGELOG[13:]
    repo.net.routes.update(pages(changelog=changelog))
    _, out = repo.run(capsys)
    assert out["watch_changed"] == [] and out["errors"] == []


def test_match_watch_without_matches_is_an_error(
    repo: Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    """A match watch whose pattern finds nothing goes to ``errors``."""
    repo.accept_baseline(capsys)
    repo.net.routes.update(pages(changelog="# Changelog\n"))
    code, out = repo.run(capsys)
    assert (code, out["status"], out["watch_changed"]) == (0, "unchanged", [])
    assert any("w-lines" in e and "no line matches" in e for e in out["errors"])


def test_watch_fetch_failure_is_an_error(
    repo: Repo, capsys: pytest.CaptureFixture[str]
) -> None:
    """A failed watch fetch goes to ``errors``, not ``watch_changed``."""
    repo.accept_baseline(capsys)
    del repo.net.routes[RAW_URL]
    code, out = repo.run(capsys)
    assert (code, out["status"], out["watch_changed"]) == (0, "unchanged", [])
    assert any(RAW_URL in e for e in out["errors"])


def test_bad_manifest_exits_1(repo: Repo, capsys: pytest.CaptureFixture[str]) -> None:
    """A malformed manifest is a usage error."""
    repo.write_manifest(base_manifest(sources={"mem": "http://insecure"}))
    code, out = repo.run(capsys)
    assert (code, out["status"]) == (1, "error")


# --- Parsing (pure) -------------------------------------------------------------


def section(text: str, heading: str) -> str:
    """Extract a section after the HTML pre-pass, failing if absent.

    :param text: Markdown text.
    :param heading: Heading to find.
    :return: The section text.
    """
    found = cg.extract_section(cg.html_headings_to_atx(text), heading)
    assert found is not None
    return found


def test_section_ends_at_same_or_higher_level() -> None:
    """Deeper subheadings stay inside; a same-level heading ends the section."""
    text = section(MEM_PAGE, "Write effective instructions")
    assert "### Audit your instruction files" in text
    assert "Path-specific" not in text


@pytest.mark.parametrize("fence", ["```", "````", "~~~"])
def test_fenced_hash_lines_do_not_end_section(fence: str) -> None:
    """``#`` lines inside 3- and 4-character fences aren't headings."""
    page = f"## A\n\n{fence}md\n# Inner\n## Inner two\n{fence}\n\nafter\n\n## B\n"
    assert "after" in section(page, "A")


def test_shorter_fence_does_not_close_longer_one() -> None:
    """A ``\\`\\`\\``` line inside a four-backtick fence is content."""
    page = "## A\n\n````\n```\n## Inner\n```\n````\n\nafter\n\n## B\n"
    assert "after" in section(page, "A")


def test_multiline_html_heading_ends_section() -> None:
    """``<h4 id>\\n Text\\n</h4>`` becomes ``####`` and ends a ``####`` section."""
    text = section(MEM_PAGE, "Path-specific rules")
    assert "## Extract PDF text" in text
    assert "Reference body" not in text
    assert section(MEM_PAGE, "Rule frontmatter reference").startswith(
        "#### Rule frontmatter reference"
    )


def test_html_heading_inside_fence_untouched() -> None:
    """HTML headings in code blocks stay as they are."""
    page = "```html\n<h1>Title</h1>\n```\n"
    assert cg.html_headings_to_atx(page) == page


@pytest.mark.parametrize(
    "line",
    [
        "### Check your setup with `/doctor`",
        "### Check your setup with /doctor {#check-setup}",
        "### Check your setup with [/doctor](/docs/doctor) ###",
    ],
)
def test_heading_cleanup_matches(line: str) -> None:
    """Backticks, anchors, closing hashes and links don't affect matching."""
    page = f"# Top\n\n{line}\n\nbody\n"
    assert "body" in section(page, "Check your setup with `/doctor`")


def test_extract_row_matches_command_only() -> None:
    """The row whose first cell starts with ``/doctor`` is returned whole."""
    row = cg.extract_row(CMDS_PAGE, "/doctor")
    assert row is not None
    assert row.startswith("| `/doctor [prompt-audit") and "Alias" in row
    assert cg.extract_row(CMDS_PAGE, "/missing") is None


def test_extract_lines_is_case_insensitive() -> None:
    """Matching lines are kept in order; no match gives ``None``."""
    text = "a Prompt-Audit\nb\nc prompt-audit\n"
    assert cg.extract_lines(text, "prompt-audit") == "a Prompt-Audit\nc prompt-audit\n"
    assert cg.extract_lines(text, "nothing") is None


def test_normalize_drops_mdx_tags_and_keeps_text() -> None:
    """Component tags go; their text stays."""
    assert cg.normalize("<Tip>Keep it short.</Tip>\n<Steps>\n<Step title='x'>") == (
        "Keep it short."
    )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("---\na: 1\n---\nbody\n", "---\nas_of: 2026-10-16\na: 1\n---\nbody\n"),
        (
            "---\nas_of: 2020-01-01\na: 1\n---\nas_of: body\n",
            "---\nas_of: 2026-10-16\na: 1\n---\nas_of: body\n",
        ),
    ],
    ids=["insert", "replace"],
)
def test_set_as_of(text: str, expected: str) -> None:
    """The date is inserted or replaced in the frontmatter only."""
    assert cg.set_as_of(text, TODAY) == expected


def test_set_as_of_needs_closed_frontmatter() -> None:
    """Text without a closed frontmatter block is rejected."""
    with pytest.raises(ValueError, match="not closed"):
        cg.set_as_of("---\na: 1\n", TODAY)


def _first(data: dict[str, Any], key: str) -> dict[str, Any]:
    """:param data: Manifest JSON. :param key: List key. :return: Its first entry."""
    return data[key][0]


MANIFEST_MUTATIONS: dict[str, tuple[Callable[[dict[str, Any]], object], str]] = {
    "no-sources": (lambda m: m.pop("sources"), "missing 'sources'"),
    "unknown-source": (
        lambda m: _first(m, "sections").update(source="nope"),
        "unknown source",
    ),
    "duplicate-id": (
        lambda m: m["sections"].append(dict(_first(m, "sections"))),
        "unique",
    ),
    "two-watch-forms": (
        lambda m: _first(m, "watch").update(url=RAW_URL),
        "exactly one",
    ),
    "match-without-url": (
        lambda m: _first(m, "watch").update(match="x"),
        "match needs url",
    ),
    "bad-match": (
        lambda m: m["watch"][-1].update(match="("),
        "bad match pattern",
    ),
    "bad-date": (lambda m: m.update(last_checked="yesterday"), "bad date"),
    "no-references-dir": (
        lambda m: m.pop("references_dir"),
        "missing 'references_dir'",
    ),
    "bool-int": (lambda m: m.update(max_age_days=True), "must be int"),
}


@pytest.mark.parametrize("case", MANIFEST_MUTATIONS)
def test_parse_manifest_rejects(case: str) -> None:
    """Manifest validation fails fast with a specific message."""
    mutate, message = MANIFEST_MUTATIONS[case]
    data = base_manifest()
    mutate(data)
    with pytest.raises(cg.ManifestError, match=message):
        cg.parse_manifest(data)


def test_manifest_round_trip() -> None:
    """Serialized manifests parse back to the same data."""
    manifest = cg.parse_manifest(base_manifest())
    assert cg.parse_manifest(json.loads(cg.manifest_to_json(manifest))) == manifest
