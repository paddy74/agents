# Spec: guidance updates

A skill that condenses Anthropic's docs into reference files stays current through
reviewed pull requests, never by editing itself at runtime. A checker detects changes
to the tracked doc sections. A weekly workflow has Claude update the reference files
and opens a PR, and it opens an issue when a built-in the skill relies on changes.
This spec covers the mechanism. Each skill's own spec lists what it tracks; for
example, [agents-md-improver](agents-md-improver.md) §7. The files are the source of
truth for exact wording.

## Contents

1. Layout
2. Contract with the skill
3. Manifest format
4. Checker
5. Workflow
6. Refresh prompt
7. Tests
8. Setup and acceptance

## 1. Layout

```text
.github/workflows/guidance.yml        # §5
tools/
├── check_guidance.py                 # §4
└── guidance/
    ├── refresh-prompt.md             # §6
    └── <skill>/
        ├── manifest.json             # §3
        └── snapshots/<section-id>.md # raw tracked sections, written by --accept
tests/check_guidance/                 # §7
```

`.gitignore` ignores `.pending.json`.

## 2. Contract with the skill

- **Frontmatter.** Each reference file that a section targets has YAML frontmatter
  with `as_of: YYYY-MM-DD` (equal to the manifest's `last_checked`) and `sources:`
  (source key → URL).
- **Tags.** Each rule paraphrases the docs and ends with the `[section-id, ...]` tags
  it came from. A tag must belong to a section that targets that file, and every
  targeted section must be cited at least once. That way an update touches only the
  tagged lines.
- **Runtime.** The skill never runs the checker and makes no network calls. It may
  report `as_of`.
- **Watch issues.** The skill's spec says how to handle a watch issue: re-check what
  depends on the built-in, then run `--accept-watch`.

## 3. Manifest format

When the manifest is written, each section and each watch entry takes one line.

| Key | Value |
| --- | --- |
| `max_age_days` | int (default 30): after this many days, an unchanged check re-confirms the date |
| `last_checked` | ISO date of the last `--accept` |
| `references_dir` | where `target` files live, relative to the repo root |
| `sources` | source key → https URL |
| `sections` | `id`, `source`, `target`, `heading`, `sha256` |
| `watch` | `id`, exactly one form (`url`, `heading` + `source`, or `row` + `source`), an optional `match` (`url` only), and `sha256` |

**Bootstrap:**

1. Write the manifest with empty hashes.
2. Run `--accept`.
3. Run `--accept-watch` with every watch id.

**Validation** fails fast with `ManifestError` on:

- a missing `sources`, `last_checked` or `references_dir`;
- a non-https source, a bad date, or a non-int (or bool) `max_age_days`;
- an unknown source;
- ids duplicated across sections and watch entries;
- a watch entry without exactly one form;
- `match` without `url`, or a `match` regex that doesn't compile.

## 4. Checker

`tools/check_guidance.py --manifest PATH [--accept | --accept-watch ID...]
[--timeout SECONDS]`

- Default timeout: 10 seconds.
- It uses the standard library plus `shared.mdparse` ([repo tools](repo-tools.md)).
- I/O lives in small functions; parsing, normalization and diffing are pure.
- `main(argv, *, root=<repo root>, today=None)` lets tests set the root and the date.

**Check** (the default mode) never edits the manifest.

1. **Fetch** every source and watch URL once, with 8 threads.
   - Try `<url>.md` first, unless the last path segment already has an extension.
   - Then try `<url>` with `Accept: text/markdown, text/plain;q=0.9`.
   - Send a `User-Agent`.
   - Accept only `text/markdown` and `text/plain` responses.
2. **Convert** line-level HTML headings outside fences into ATX headings, including
   multi-line ones such as `<h4 id>…</h4>`.
3. **Extract** each section.
   - Match its heading by cleaned text at any level: drop `{#anchor}`, closing hashes,
     backticks and link markup.
   - The section runs up to the next heading of the same or a higher level.
   - `#` lines inside fences (`fence_mask`) aren't headings.
   - Sections may nest.
4. **Normalize** each section for hashing.
   - Drop fence `theme={...}` strings, link targets, and the MDX tags Tip, Note,
     Warning, Callout, Steps, Step, CardGroup, Card and Frame.
   - Drop any sentence containing `vX.Y.Z`.
   - Collapse whitespace.
5. **Compare** SHA-256 hashes with the manifest, and diff each changed section against
   its snapshot (unified diff, 2 lines of context).
6. **Watch.** Hash each watched text the same way. The forms are:
   - `url`: the whole file;
   - `url` with `match`: only the lines matching the case-insensitive regex;
   - `heading`: one section;
   - `row`: the table row whose first cell, without backticks, is the command or
     starts with the command plus a space.

   A changed hash goes to `watch_changed`; it changes neither the status nor the exit
   code. A failed fetch, or a `match` that finds no line, goes to `errors`.
7. **Save** the fetched sections and watch hashes, with a `created` time, to
   `.pending.json` beside the manifest.

**`--accept`** stores the pending sections. If `.pending.json` is missing or more than
24 hours old, it re-fetches first. It then:

- writes `snapshots/<id>.md` and the section hashes;
- sets `last_checked` to today;
- sets `as_of` to today in every target file, replacing the existing line or
  inserting one after the opening `---`.

Watch hashes are left alone.

**`--accept-watch ID...`** stores only the named watch hashes. An unknown id is an
error and triggers no fetch.

**Output** is one JSON object with `status`, `last_checked`, `age_days`, `changed`
(`id`, `target`, `url`, `diff`), `missing`, `watch_changed` and `errors`.

| Status | Exit | Meaning |
| --- | --- | --- |
| `unchanged`, `accepted` | 0 | The stored copy is current, or an accept stored it |
| `changed` | 10 | A section's hash differs |
| `structure_changed` | 11 | A tracked heading is `missing`; the sections that were found are still diffed |
| `unreachable` | 20 | No source could be fetched |
| `error` | 1 | Usage, I/O or manifest error, or a target file without frontmatter. Prints `{"status": "error", "errors": [...]}` |

## 5. Workflow

`.github/workflows/guidance.yml` runs on Mondays (`17 6 * * 1`) and on
`workflow_dispatch`.

- **Settings:** one `concurrency` group; `contents`, `pull-requests` and `issues` set
  to write.
- **Env:** `MANIFEST`, `REFERENCES`, `SKILL` and `BRANCH=bot/guidance-refresh`. It is
  currently wired to agents-md-improver.
- **Actions** are pinned to commit SHAs, with the version in a comment:
  `actions/checkout` v7.0.1, `astral-sh/setup-uv` v10.3.0 (then `uv sync --locked`),
  and `anthropics/claude-code-action` v1.0.252 (pin the annotated tag's commit).

Steps:

1. **Check.** Run the checker into `result.json`. Any exit other than 0, 10 or 11
   fails the job, which sends GitHub's failure notice. The step outputs `code`,
   `watch` (space-separated ids), `errors` (count) and `stale`
   (`age_days ≥ max_age_days`).
2. **Watch issue.** If `watch` is set:
   - ensure the `guidance-watch` label exists;
   - edit its open issue, or create one;
   - the body names the ids, the `--accept-watch` command, and the skill spec's
     re-check procedure.

   If `watch` is empty and `errors` is 0, close the open `guidance-watch` issue
   with a comment. A failed fetch leaves it open.
3. **Update.** If `code` ≠ 0, run claude-code-action with:
   - `claude_code_oauth_token: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}` (the Pro
     subscription; no API key);
   - `github_token: ${{ github.token }}`;
   - `claude_args: --model claude-haiku-5-5 --allowedTools Read,Edit,Write,WebFetch`.

   The prompt tells it to follow `refresh-prompt.md`, and names `result.json`, the
   references directory and the manifest.
4. **Accept and verify.** If `code` ≠ 0 or `stale`:
   - re-check (ignoring the exit code), so the pending data includes any headings
     Claude fixed;
   - run `--accept`;
   - run ruff (check and format check), basedpyright, pytest and `tools/lint_skill.py
     "$SKILL"`.

   Any failure stops the job before a PR is opened.
5. **PR.** Under the same condition:
   - As `github-actions[bot]`, stage only the references directory and
     `tools/guidance`. If nothing is staged, exit.
   - Commit as `docs(<skill>): refresh official guidance`. The PR body is
     `summary.md`, plus up to 50,000 characters of diffs in a `<details>` block.
     When only the date moved, commit as `chore(<skill>): confirm guidance current`
     instead.
   - Force-push to `$BRANCH` only. Then edit its open PR, or create one against the
     default branch.

## 6. Refresh prompt

`tools/guidance/refresh-prompt.md` gives the edit step its rules:

- Don't run commands, commit, or touch other files.
- Group `changed` by target, and read each target once.
- For each changed section, make the smallest edit to its tagged rules that matches
  the new meaning. Paraphrase, keep one rule per line, and keep the tags. Add a
  tagged rule only for guidance that no rule covers.
- Ignore changes that don't change the meaning: version notes, link targets,
  rewording, reordering. An empty `diff` means no edit.
- For each `missing` id, fetch its source, find the heading that now holds the
  content, and update only that `heading` in the manifest. If no heading fits, say
  so.
- Write `summary.md`, one line per section: `- <target> [<id>]: <change>`, or
  `- [<id>]: no edit (noise)`.

## 7. Tests

Every behaviour in §3 and §4 has a test. Tests never touch the network (they fake
`urllib.request.urlopen`), and each uses its own temp directory. The tests also
cover:

- noise-only edits (version sentence, link target, fence `theme`, spacing) staying
  `unchanged`;
- `--accept-watch` clearing the alert on the next check;
- a manifest round trip.

`test_workflow.py` checks that:

- the env paths and the prompt file exist;
- every action is pinned to a 40-character hex SHA;
- authentication uses `CLAUDE_CODE_OAUTH_TOKEN`, with no API key;
- the only `git push` targets a `bot/` branch;
- the watch issue closes only when `watch` is empty and `errors` is 0;
- every `run` script passes `bash -n` once `${{ }}` is filled in.

## 8. Setup and acceptance

Setup, with steps in the README: a `CLAUDE_CODE_OAUTH_TOKEN` repo secret from
`claude setup-token` (runs count toward the subscription's usage limits), and Actions
allowed to create pull requests. `bot/*` branches belong to CI (AGENTS.md).

Acceptance:

- The workflow has completed a run on GitHub.
- **Real diff:** after one stored hash is edited, a run changes only the tagged lines
  of the file that owns the section, the tests pass, and one PR opens on
  `bot/guidance-refresh`.
- **Watch issue:** after a watch hash is edited, a run opens one `guidance-watch`
  issue and no PR, unless sections also changed. After `--accept-watch`, the next run
  closes the issue.
