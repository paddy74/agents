# agents-md-improver: acceptance

Status of the evals and manual scenarios that [the spec](../specs/agents-md-improver.md)
defines (§9, §10, including the "most runs" release rule). Update a row's status, date
and notes when you run it.

## Evals (skill-creator)

Defined in `tests/agents-md-improver/evals/evals.json`, with fixtures in
`tests/agents-md-improver/evals/fixtures/` (file paths are relative to `evals/`). To
run them with skill-creator, copy the skill to a scratch directory, copy `evals/` into
it, and ask skill-creator to evaluate it against a no-skill baseline.

Setup for every iteration: Sonnet subagents read SKILL.md by path, so triggering
wasn't tested. They had no other skills, subagents or `claude` CLI, so prompt-audit
was named rather than run (M6 covers the routes). Scripted checks plus Haiku
graders, with grader verdicts checked by hand where they disagreed with the script.

| Iteration | Date | Runs | Scope | With skill | Without |
| --- | --- | --- | --- | --- | --- |
| 1 | 2026-10-18 | 1 per config | E1–E10 | 98.9% | 72.6% |
| 2 | 2026-10-18 | 3 per config | E1–E10, after grouped cuts, the standing `/doctor` follow-up and new `[D]` expectations (E3, E4; E6's were dropped after this iteration) | 97.1% | 62.7% |
| 3 | 2026-10-18 | 3, skill only | E1, E2, E5 after wording fixes; baseline reused from iteration 2 | see table | — |
| 4 | 2026-10-18 | 3, skill only | E1 after the one-line-per-kind report format | see table | — |

Latest result per eval:

| Eval | Scenario                         | Status | Iteration | With (3 runs) | Without (3 runs) | Notes |
| ---- | -------------------------------- | ------ | --------- | ------------- | ---------------- | ----- |
| E1   | Rewrite persona-heavy AGENTS.md  | pass   | 4         | 8/9 9/9 9/9   | 5/9 6/9 6/9      | Run 1 fails A5: the emphasis line gives no reason. Without: A5, A6 and A8 fail every run |
| E2   | Merge preferences into a project | pass   | 3         | 4/4 ×3        | 3/4 ×3           | Baseline left "Run the formatter" generic every run |
| E3   | Conflict resolution              | pass   | 2         | 4/4 ×3        | 4/4 3/4 3/4      | Baseline deleted `team-preferences.md` in 2 of 3 runs |
| E4   | AGENTS.md + CLAUDE.md pair       | pass   | 2         | 5/5 ×3        | 2/5 4/5 3/5      | Baseline never mentioned `claude-md-and-agents-md`; each `[D]` failed once |
| E5   | Symlinked CLAUDE.md              | pass   | 3         | 3/3 ×3        | 2/3 2/3 3/3      | Every with-skill run names `cargo clippy -- -D warnings` in the lint rule |
| E6   | Rewrite a verbose SKILL.md       | pass   | 2         | 6/6 ×3        | 6/6 ×3           | Doesn't discriminate: every run kept the reference content, so it has no `[D]` expectations |
| E7   | Eval-only request                | pass   | 2         | 2/2 ×3        | 1/2 ×3           | A conditional mention of skill-creator isn't graded as routing |
| E8   | Audit-only request               | pass   | 2         | 3/3 ×3        | 2/3 ×3           | Baseline never mentioned prompt-audit |
| E9   | Trim-only request                | pass   | 2         | 2/2 ×3        | 0/2 ×3           | Baseline edited CLAUDE.md every time |
| E10  | Add-missing-context request      | pass   | 2         | 2/2 ×3        | 1/2 ×3           | Baseline gave its own gap list every time |

Release rule: met. With the skill, every eval passes in 3 of 3 runs, except E1 in
2 of 3. Without it, a `[D]` expectation fails in E1 3 of 3, E2 3 of 3 and E4 2 of 3.

## Manual scenarios

| ID | Scenario                     | Status          | Date       | Notes |
| -- | ---------------------------- | --------------- | ---------- | ----- |
| M1 | Write a new skill end to end | pass (caveats)  | 2026-10-18 | Sonnet subagent, skill-creator via the Skill tool, interview answers given in the prompt. Stopped after "Test Cases"; draft in the given directory; baseline read-only with its hash unchanged after evals; no `skill-snapshot/`. The delivered skill passes `quick_validate.py` and the linter; 3 evals of old_skill vs rewritten show no regression. A second, cheaper run (inline path, `drafting-changelog-entries`) confirmed the fixed Deliver step: prompt-audit ran by route 1 on the delivered files and its findings reached the report. Not covered: relaying interview questions, description tuning, and checking that `old_skill` runs read the baseline (reported, transcripts not kept) |
| M2 | No skill-creator available   | pass            | 2026-10-18 | Inline draft `converting-csv-to-markdown-tables` with 4 eval scenarios; linter 0 errors, 0 warnings. The report says `quick_validate.py`, eval runs and the baseline didn't run, and gives `/plugin install skill-creator@claude-plugins-official` |
| M3 | Guidance PR with a real diff | pass            | 2026-10-19 | Workflow run on `test/guidance-m3` with the `mem-when-to-add` hash edited: the tests passed and [PR #2](https://github.com/paddy74/agents/pull/2) opened from `bot/guidance-refresh`. It changed only the `[mem-when-to-add]` rule, plus `as_of` and `last_checked`. The section diff was empty (only the hash was faked), yet Claude reworded the rule to match the docs more closely instead of reporting noise |
| M4 | Old guidance                 | pass            | 2026-10-18 | 3 of 3 runs on a copy with `as_of: 2026-06-01` rewrote AGENTS.md offline and reported "139 days old" with "update or re-package the skill". Before SKILL.md computed the age with a command, one run misjudged it as under 90 days |
| M5 | Built-in changed             | pass            | 2026-10-19 | Workflow run on `test/guidance-m5` with the `w-doctor` hash edited: [issue #3](https://github.com/paddy74/agents/issues/3) opened with the `--accept-watch` command, and no PR. Clearing after `--accept-watch` is covered by the checker tests, not a workflow run |
| M6 | prompt-audit routes          | pass            | 2026-10-18 | One E1 rewrite per route, with higher routes blocked. Routes 1 (subagent + `claude-api`), 2 (`claude-api` in context) and 3 (`claude -p "/doctor prompt-audit AGENTS.md"`, CLI 2.1.303) each ran report-only, proposed no diff, and their findings were folded into the report with applied/not-applied reasons. Route 4 (follow-up line) appears in every eval run |

First workflow run: `main`, 2026-10-19, success, with no PR or issue.
