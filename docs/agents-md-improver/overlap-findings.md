# agents-md-improver: overlap findings

Evidence for the scope decisions in [the spec](../specs/agents-md-improver.md) (§2). Environment:
Claude Code 2.1.302 on Linux (WSL2), 2026-10-16.

## Built-ins

The decisions and watch entries in spec §2 were made on 2026-10-16. Also considered,
with no overlap worth routing to: `/init` and `/import` (mentioned only),
`claude plugin eval` (not used at runtime), and community skills such as SkillOpt
(none used).

## S1: `/doctor` and prompt-audit against E1

Ran `claude -p "/doctor prompt-audit CLAUDE.md"` on a scratch copy of
`tests/agents-md-improver/evals/fixtures/e1/AGENTS.md` saved as CLAUDE.md, with its
`pyproject.toml` and `.claude/rules/testing.md`. Scored on the proposed diff as if
applied.

Results and the gate verdict are in S1c (row "S1"). It also reported the unittest-versus-pytest conflict
with `.claude/rules/testing.md` (A6) and left the choice to the user.

- `/doctor` (the checkup) was not run: it runs unrelated setup checks on the real
  configuration and needs interactive confirmation. Its CLAUDE.md actions cut
  derivable content and relocate guidance, which don't cover A2 either.
- **Invocability:** `doctor` isn't in the Skill tool's list in this session, so it
  can't be invoked through the Skill tool. `claude -p "/doctor prompt-audit <path>"`
  from Bash works: exit 0, report only, file unchanged, no checkup. SKILL.md's Verify
  step uses that route when the `claude` CLI is on PATH.

## S1b: prompt-audit through `claude-api` in a subagent

Ran 2026-10-16: a general-purpose subagent invoked the `claude-api` skill with
`prompt-audit <scratch>/CLAUDE.md` (the same E1 copy as S1, with its
`pyproject.toml` and `.claude/rules/testing.md`), report only.

Results and the gate verdict are in S1c (row "S1b"). It also flagged the A6 conflict with
`.claude/rules/testing.md` and left the choice to the user.

- **Invocability:** yes. The Skill tool call worked inside the subagent; `claude-api`
  defines `prompt-audit` in its subcommand table and runs `shared/prompt-audit.md`.
  No file changed (sizes and modification times checked). This is route 1 in the
  SKILL.md "Verify and report" order.
- `/skill-doctor` (headless, `claude -p "/skill-doctor"`): reports each skill's
  listing cost (~70 tokens for the E6 fixture) and 7-day usage, not SKILL.md body
  size, so it doesn't replace the body-size estimate.

## S1c: repeated gate runs

Ran 2026-10-17 to settle S1 versus S1b (spec §2, "Re-checking the split"): three fresh runs
per route on fresh copies of the same E1 setup, all Claude Opus 5.5, report only.
Scored on the proposed diff as if applied; findings that are only flagged (low
confidence, not in the diff) don't count as cuts.

| Run  | Route                          | A2 **R** | A3 **R** | A5 **R** | A7 **R** | Why A2 or A3 failed                                                                |
| ---- | ------------------------------ | -------- | -------- | -------- | -------- | ---------------------------------------------------------------------------------- |
| S1   | `claude -p "/doctor prompt-audit"` | fail | pass     | pass     | pass     | Persona flagged low; match-style and explain-reasoning kept                        |
| cli1 | `claude -p "/doctor prompt-audit"` | fail | pass     | pass     | pass     | Persona flagged low; match-style kept                                              |
| cli2 | `claude -p "/doctor prompt-audit"` | fail | pass     | pass     | pass     | Persona flagged low                                                                |
| cli3 | `claude -p "/doctor prompt-audit"` | fail | fail     | pass     | pass     | Persona trimmed but kept ("You are a senior Python engineer…"); match-style kept; no `uv run pytest` |
| S1b  | subagent → `claude-api`        | pass     | pass     | pass     | pass     |                                                                                    |
| sub1 | subagent → `claude-api`        | fail     | pass     | pass     | pass     | Read-before-edit and match-style kept as "concrete working rules"                  |
| sub2 | subagent → `claude-api`        | fail     | fail     | pass     | pass     | Persona and read-before-edit flagged low; commands only a low flag                 |
| sub3 | subagent → `claude-api`        | fail     | fail     | pass     | pass     | Persona flagged low; read-before-edit and match-style kept; commands only a low flag |

- **Gate:** not met. 1 of 8 runs passed every **R** assertion (0/4 via `/doctor`,
  1/4 via `claude-api`). A2 failed 7/8 and A3 3/8; A5 and A7 passed 8/8.
- **Decision:** keep Rewrite for instruction files as built. prompt-audit reliably
  finds the stale command, the cross-file conflict and the dated pressure language,
  so it stays the independent verifier. It treats the persona and default-behaviour
  lines as optional (low-confidence flags or "concrete working rules"), and names the
  exact commands only sometimes. Those are Rewrite's distinct value.
- All runs left every file unchanged (hashes checked before and after).

## S2: skill-creator hand-off

Found by reading skill-creator's SKILL.md ("Running and evaluating test cases"): its
improve mode runs `cp -r <skill-path> <workspace>/skill-snapshot/` before editing, the
path first chosen for our baseline. The baseline therefore lives at `<name>-baseline/`
(read-only, hash-checked; spec §2 and §4, "Write a skill").

Checked by manual scenario M1 on 2026-10-18 ([acceptance.md](acceptance.md)), with
skill-creator invoked through the Skill tool in a subagent:

- stops after "Test Cases" when told to: yes;
- writes the draft to the given directory: yes;
- leaves the baseline alone: yes (read-only, hash unchanged, no `skill-snapshot/`);
- `old_skill` runs read the baseline: reported yes by the run, not checked (its
  transcripts weren't kept).

## S3: section parser

Passed, both offline and live.

- Offline: fetched the six source pages (`text/markdown; charset=utf-8`) and the three
  watched raw files (`text/plain; charset=utf-8`), ran the parser over every tracked
  heading, and compared section ends with a manual read. Covered: `mem-path-rules`
  ends at the multi-line `<h4>` "Rule frontmatter reference" and contains the fenced
  `# API Development Rules`; `sbp-concise` spans the four-backtick fence with
  `## Extract PDF text`; `spec-frontmatter` runs to `### Body content`; the `/doctor`
  row resolves from its first cell `` `/doctor [prompt-audit [path]]` ``.
- Live: `check_guidance.py --accept` stored all hashes and snapshots; a forced
  re-check returned `unchanged` (repeated 2026-10-18 with `tools/check_guidance.py`).

## Parity evidence

Last run 2026-10-18 (`tests/lint_skill/`, parity tests enabled). `tools/lint_skill.py
--target portable` agreed with every reference:

| Reference | Version | Result |
| --- | --- | --- |
| `quick_validate.py`, upstream `claude-plugins-official` main | sha256 `67cf57034020…` | 19/19 agree; the single-SKILL.md case is skipped because this copy predates that rule |
| `quick_validate.py`, marketplace plugin copy | same file as upstream | 19/19 agree, same skip |
| `quick_validate.py`, synced claude.ai copy | sha256 `f65315971b2a…` | 20/20 agree |
| `skills-ref validate` | 0.1.0, commit `69ef37e` | 7/7 spec cases agree |

The full suite with both references enabled: 189 passed. `skills-ref validate` also
accepts `claude/skills/agents-md-improver`.
