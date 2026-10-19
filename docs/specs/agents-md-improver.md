# Spec: `agents-md-improver` skill

What the skill, its reference files, its guidance data and its tests must do, and
why. The files hold the exact wording. Related specs:

- [guidance-updates](guidance-updates.md): how CI keeps the official files current.
- [repo-tools](repo-tools.md): the linter, the bundler and the shared parser.

## Contents

1. Purpose and scope
2. Built-ins and how the skill uses them
3. Deliverables
4. SKILL.md
5. Method reference files
6. Official reference files
7. Guidance data
8. Tests
9. Evals
10. Acceptance criteria

## 1. Purpose and scope

The skill does three jobs on agent instruction files, following Anthropic's official
guidance as condensed in its reference files:

- **Rewrite** one AGENTS.md, CLAUDE.md, CLAUDE.local.md, `.claude/rules` file or
  SKILL.md. Cut personas and default behaviour, make each rule one verifiable line,
  and specialize generic wording to the project's real commands.
- **Merge** two or more instruction files into one canonical setup.
- **Write a skill:** skill-creator drafts and evaluates it. This skill rewrites and
  validates the draft, then checks that it didn't regress.

The skill does only what the built-ins don't (§2). It works in Claude Code, claude.ai,
the API, and other agents that read AGENTS.md. It makes no network calls.

**Out of scope:** scoring rubrics; committing or pushing; Cursor and Copilot formats
(`/import`); linting this repo's skills.

## 2. Built-ins and how the skill uses them

| Built-in | Role | How the skill uses it | Watch (§7) |
| --- | --- | --- | --- |
| `/doctor` (`/checkup`) | Trims content derivable from code, de-duplicates CLAUDE.local.md, relocates guidance; asks before changing anything | **Defer:** listed as a follow-up for the user, because it also runs unrelated checkup steps | `w-doctor`, `w-skills-doctor` |
| prompt-audit (`/doctor prompt-audit`; same engine as the `claude-api` skill's `prompt-audit`) | Flags old-model wording, missing files and commands, and cross-file contradictions; proposes edits, applies none | **Reuse:** handles audit-only requests and verifies the result of Rewrite or Merge | `w-prompt-audit-changelog`, `w-doctor`, section `mem-audit` |
| `claude-md-improver`, `/revise-claude-md` | Score CLAUDE.md and propose additions | **Coexist:** named only for add-missing-context requests | `w-md-improver` |
| skill-creator | Interview, draft, test cases, eval loop with baselines, description tuning, `package_skill.py` | **Wrap:** skill-creator drafts and evaluates; this skill rewrites and validates. Eval-only requests go to skill-creator | `w-skill-creator` |
| `quick_validate.py` (in skill-creator) | Frontmatter validation | **Reuse** in the Validate step | `w-quick-validate` |
| plugin-dev `skill-reviewer`, `skill-development` | Skill review | **Never route:** they contradict official guidance (1,000–3,000-word bodies; "`when_to_use` is deprecated") | none |
| `/skill-doctor`, `claude plugin validate`, `skills-ref` | Listing cost, packaging parse check, spec validator | **Not used at runtime:** none of them checks body size or wording | none |

These constraints come from the built-ins. Breaking any of them breaks the skill:

- **`/doctor` can't be invoked through the Skill tool.** prompt-audit therefore runs
  through the `claude-api` skill, preferably in a subagent, so it gets a fresh
  context.
- **The Skill tool loads skill-creator into the same conversation,** with no call and
  return. Each hand-off therefore names a stop point in skill-creator's own terms,
  such as "Test Cases".
- **skill-creator's improve mode overwrites `<name>-workspace/skill-snapshot/`.** The
  baseline therefore lives in a separate directory that is read-only and checked by
  hash.
- **prompt-audit's instructions are compiled into the Claude Code binary.** It is
  watched through the changelog, so a change the changelog doesn't mention goes
  unseen.

### Re-checking the split

Rewrite for instruction files exists only while prompt-audit can't do its job.
Re-check when any of these happens:

- the `guidance-watch` issue names `w-prompt-audit-changelog` or `w-doctor`;
- `mem-audit` changes in a guidance PR;
- the default model changes.

Steps:

1. Run prompt-audit on the E1 fixture (saved as CLAUDE.md, report only) at least 3
   times on each route: a subagent invoking `claude-api` `prompt-audit`, and
   `claude -p "/doctor prompt-audit"`. Score its diff as if it were applied. Lines
   flagged only at low confidence don't count as cuts.
2. If most runs (§9) on a route pass every **[R]** expectation of E1, Rewrite for
   instruction files becomes "apply prompt-audit's diff, plus the method rules it
   doesn't cover". Otherwise, nothing changes.
3. Run `--accept-watch` for the flagged ids, and commit.

## 3. Deliverables

```text
claude/skills/agents-md-improver/    # ships as-is; nothing else goes in it
├── SKILL.md                         # §4
└── references/
    ├── method-instructions.md       # §5
    ├── method-skills.md             # §5
    ├── official-instructions.md     # §6
    └── official-skills.md           # §6
tools/guidance/agents-md-improver/   # manifest.json (§7) and snapshots/
tests/agents-md-improver/            # package tests (§8), evals.json and fixtures (§9)
```

**Install:**

- **Claude Code:** symlink the folder into `~/.claude/skills/`. Merged guidance PRs
  arrive with `git pull`.
- **claude.ai:** zip the folder with `package_skill.py`, and upload it again after
  each guidance PR.

## 4. SKILL.md

- **Size:** under 200 lines.
- **Frontmatter:** only `name: agents-md-improver` and a third-person `description`.
  The description names:
  - the three jobs and the file types;
  - the trigger phrasings (rewrite, tighten, clean up, optimize; merge, combine,
    fold in; write, create, turn a workflow into a skill);
  - which requests go to `/doctor`, `/doctor prompt-audit` or skill-creator
    instead.

Body sections, in order:

- **Route.**
  - Rewrite, Merge and Write a skill each go to their own section.
  - Every other request goes to the built-in that owns it (§2), and the skill stops:
    - **audit-only** → run prompt-audit and relay its findings. If no route can run
      prompt-audit, fall back to a Rewrite that edits nothing.
    - **trim, de-duplicate or relocate only** (Claude Code) → `/doctor`.
    - **add missing context** → `claude-md-improver` or `/revise-claude-md`.
    - **evals, benchmarks or description tuning only** → skill-creator.
    - **unclear request** → ask one question.
- **Preflight.**
  - Read the two reference files for the profile: the instruction-file pair or the
    skill pair.
  - Read every input, the sibling instruction files and the build config, so
    commands are real and no sibling is contradicted.
- **Rewrite.**
  - Apply the method file's profile; leave alone what it assigns to built-ins.
  - Edit in place. For a symlink, edit its target.
  - For a skill, run Validate afterwards.
- **Merge.** Follow the method file's Merge steps, which end in Rewrite.
- **Write a skill.**
  1. skill-creator drafts into a scratch directory and stops after "Test Cases".
  2. Copy the draft to a baseline (§2), make it read-only, and record its hash.
  3. Rewrite and validate the draft.
  4. Re-enter skill-creator's improve mode against the baseline. After each
     iteration, check the baseline hash and paths. A test that passes on the
     baseline but fails on the draft restores the related cut.
  5. Tune the description last.
  6. Deliver to the skills directory or as a package, then run Verify and report,
     including prompt-audit, on the delivered files.

  Without skill-creator: draft inline with at least three eval scenarios, and report
  that the draft wasn't eval-tested.

  When guidance conflicts, official guidance wins over the method file, which wins
  over skill-creator's or plugin-dev's style advice.
- **Validate.** Run `quick_validate.py` until it exits 0, then work through the
  `method-skills.md` checklist.
- **Verify and report.**
  - Check the line counts before and after, and look for duplicate lines.
  - For a merge, account for every rule. For a skill, include the eval results.
  - Run prompt-audit on the changed paths, taking the first route that works:
    1. a subagent running `claude-api` `prompt-audit`;
    2. `claude-api` in the current context;
    3. `claude -p "/doctor prompt-audit"`;
    4. otherwise, a follow-up line in the report.

    Fold its findings into the report. If prompt-audit didn't run, check commands
    and paths yourself.
  - Report the `as_of` date (§6). With a shell, compute its age with a command (models
    misjudge date differences) and suggest an update past 90 days; without one, state
    `as_of` and today's date.
  - Commit only when asked.
  - Keep the report terse: one line per cut kind (persona, default behaviour,
    linter-enforced, decision tree, emphasis, other), each `<kind>: <what was cut>,
    because <reason>`, so no group loses its reason; then other changes, conflicts,
    the guidance date and follow-ups. In Claude Code, the follow-ups always include
    `/doctor`.

## 5. Method reference files

These rules are ours: CI never edits them, and where they disagree with an official
file, the official file wins. Neither file has frontmatter. Each starts with a
contents list and doesn't link to other reference files.

**`method-instructions.md`** (≤ 80 lines):

- **Rewrite**
  - **Keep test:** would removing this line cause mistakes?
  - **Cut:** personas, default model behaviour, rules a linter enforces, decision
    trees that restate rules, and emphasis on more than one line.
  - **Wording:** one imperative, verifiable line per rule. Take commands from build
    config; never invent one, and flag any that are undefined.
  - **Section order:** summary, Hard rules, Commands, Code style, Design, Testing,
    Git, Scope, Communication.
  - **Preserve:** consistency with sibling files, `paths:` frontmatter, `@imports`
    and symlinks.
  - **Flag:** HTML-comment placeholders.
  - **Report cuts** grouped by kind, each with its reason: persona (adds no
    instruction), default behaviour (the model already does it), linter-enforced,
    decision tree (restates other rules), emphasis (cancels out when overused),
    other (fails the keep test).
  - **Follow-ups:** hooks, settings, the `@AGENTS.md` bridge, `/config` "Project
    instructions".
- **Merge**
  - **Precedence:** the user's order. By default, project-specific beats generic,
    and the target is the base.
  - **AGENTS.md + CLAUDE.md:** a canonical AGENTS.md, plus a CLAUDE.md that starts
    with `@AGENTS.md` and holds only Claude-specific lines. Mention
    `claude-md-and-agents-md` as the alternative.
  - **Classify** each atomic rule as a duplicate, refinement, conflict or new rule.
    Conflicts go to the higher precedence and are reported.
  - **Keep** every rule that isn't a duplicate or conflict, and list keep-test
    failures as optional cuts. Account for every input rule.
  - Then run Rewrite.
- **Left to built-ins:** trimming, de-duplication and relocation go to `/doctor`;
  detection goes to prompt-audit. Outside Claude Code, list relocation candidates
  without creating files.

**`method-skills.md`** (≤ 50 lines):

- **Rewrite**
  - **Keep test:** would removing this make the task worse? Workflows, checklists,
    loops, templates and examples are the payload: tighten them, don't delete them.
  - **Description:** never shorten it to save tokens. Use third person, say what and
    when, and keep every trigger.
  - **Body:** facts and steps, not narrative; one default with an escape hatch;
    strictness matched to fragility; one term per concept; no dated text.
  - **References:** move occasional material into files linked one level deep.
  - **Scripts:** don't change their behaviour.
  - **Cut list:** keep one.
- **Validate:** the checks `quick_validate.py` lacks:
  - the name equals the directory;
  - `metadata` values are strings;
  - under 500 lines and about 5,000 tokens;
  - a routing heading in the first 40 lines;
  - reference depth and contents lists;
  - every link resolves;
  - forward slashes in paths;
  - no dated text outside "Old patterns";
  - at most two emphasis lines;
  - every script is mentioned.
- **Frontmatter:** only portable fields for the portable target. For Claude Code,
  set `disable-model-invocation: true` on task skills with side effects.

## 6. Official reference files

`official-instructions.md` and `official-skills.md`, each ≤ 90 lines, follow the
[guidance-updates](guidance-updates.md) contract: `as_of` and `sources` frontmatter,
and one tagged rule per bullet. Generate them by condensing the sections in §7. Each
has an H1, a contents list, then these headings:

`official-instructions.md` (sources `mem`, `bp`):

| Heading | Covers |
| --- | --- |
| What belongs | facts needed every session; when to add; include and exclude lists; what `/doctor` cuts; length warnings |
| How to write | concrete, verifiable rules; under 200 lines; headings and bullets; no contradictions; `/doctor prompt-audit`; the prune test; one-line emphasis |
| Where content goes | skill vs. path rule vs. hook; `@path` imports don't save context |
| Loading | HTML comments stripped; root-first concatenation; subdirectory files load lazily |
| AGENTS.md | when Claude Code reads it; CLAUDE.local.md stops it; the `/config` "Project instructions" values; the `@AGENTS.md` bridge vs. a symlink |
| Compliance | delivered as a user message; `includeGitInstructions`, `attribution` |

`official-skills.md` (sources `skills`, `sbp`, `spec`):

| Heading | Covers |
| --- | --- |
| Structure and frontmatter | loading tiers; `name` rules; spec rules; opening `---`; the fields packaging allows; Claude Code-only fields |
| Descriptions | ≤ 1,024 chars, third person, what and when; the 1,536-char listing truncation |
| Body | conciseness; content persists across turns; only the first ~5,000 tokens kept after compaction; under 500 lines; freedom vs. fragility; consistent terms; no time-sensitive text; defaults; checklists and loops |
| References and scripts | one level deep; contents lists; organized by domain; script hygiene |
| Checklist | at least 3 evaluations; test on target models; compare against a baseline (skill-creator, `claude plugin eval`) |

## 7. Guidance data

`tools/guidance/agents-md-improver/manifest.json` (format in
[guidance-updates](guidance-updates.md) §3):

- `max_age_days: 30`
- `references_dir: claude/skills/agents-md-improver/references`

When §2 starts relying on a new built-in, add a watch entry for it.

**Sources:**

| Key | URL |
| --- | --- |
| `mem` | https://code.claude.com/docs/en/memory |
| `bp` | https://code.claude.com/docs/en/best-practices |
| `skills` | https://code.claude.com/docs/en/skills |
| `cmds` | https://code.claude.com/docs/en/commands |
| `sbp` | https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices |
| `spec` | https://agentskills.io/specification |

**Watch entries** (`RAW` = `https://raw.githubusercontent.com/anthropics`):

| Id | Form |
| --- | --- |
| `w-doctor` | `source: cmds`, `row: /doctor` |
| `w-skills-doctor` | `source: skills`, `heading: Check your setup with /doctor` |
| `w-skill-creator` | `url: RAW/claude-plugins-official/main/plugins/skill-creator/skills/skill-creator/SKILL.md` |
| `w-quick-validate` | `url: RAW/claude-plugins-official/main/plugins/skill-creator/skills/skill-creator/scripts/quick_validate.py` |
| `w-md-improver` | `url: RAW/claude-plugins-official/main/plugins/claude-md-management/skills/claude-md-improver/SKILL.md` |
| `w-prompt-audit-changelog` | `url: RAW/claude-code/main/CHANGELOG.md`, `match: prompt-audit\|prompt audit` |

**Sections** (33). Each id's prefix gives its source (`sk-` is `skills`). The `mem-`
and `bp-` sections target `official-instructions.md`; all others target
`official-skills.md`. Each line below lists `id` heading pairs:

- **mem:** `mem-when-to-add` When to add to CLAUDE.md, `mem-write-effective` Write effective instructions, `mem-audit` Audit your instruction files, `mem-how-load` How CLAUDE.md files load, `mem-path-rules` Path-specific rules, `mem-agents-reads` When Claude Code reads AGENTS.md, `mem-choose-files` Choose which instruction files load, `mem-agents-share` Share one file with other coding tools, `mem-not-following` Claude isn't following my CLAUDE.md, `mem-too-large` My CLAUDE.md is too large
- **bp:** `bp-write-effective` Write an effective CLAUDE.md, `bp-hooks` Set up hooks
- **skills:** `sk-content-types` Types of skill content, `sk-evaluate` Evaluate and iterate on a skill, `sk-frontmatter` Frontmatter reference, `sk-frontmatter-ext` Using skill frontmatter outside Claude Code, `sk-supporting-files` Add supporting files, `sk-invocation` Control who invokes a skill, `sk-lifecycle` Skill content lifecycle
- **sbp:** `sbp-concise` Concise is key, `sbp-freedom` Set appropriate degrees of freedom, `sbp-naming` Naming conventions, `sbp-descriptions` Writing effective descriptions, `sbp-disclosure` Progressive disclosure patterns, `sbp-nesting` Avoid deeply nested references, `sbp-toc` Structure longer reference files with table of contents, `sbp-time` Avoid time-sensitive information, `sbp-terms` Use consistent terminology, `sbp-anti` Anti-patterns to avoid, `sbp-yaml` YAML frontmatter requirements, `sbp-checklist` Checklist for effective Skills
- **spec:** `spec-frontmatter` Frontmatter, `spec-disclosure` Progressive disclosure

## 8. Tests

`tests/agents-md-improver/test_skill_package.py` checks that:

- the skill lints clean (portable target);
- the skill folder holds only SKILL.md and `references/`;
- the line budgets in §4–§6 hold;
- the official files meet the [guidance-updates](guidance-updates.md) §2 contract:
  every tag is owned, every section is cited, and `as_of` equals `last_checked`;
- every hash and snapshot is stored, and each snapshot's digest matches its hash;
- `references_dir` resolves to the skill;
- no reference file links to another `.md` file;
- the frontmatter is exactly `name` and `description`.

`test_evals.py` checks the `evals.json` schema and ids 1–10, and that the listed
files exist. It also checks:

- E1, E2 and E4 have `[D]` expectations;
- the E1 AGENTS.md is 78 lines;
- the E5 CLAUDE.md is a symlink;
- the fixtures total ≤ 50 KB.

## 9. Evals

`tests/agents-md-improver/evals/evals.json` uses skill-creator's format and holds the
full expectation lists. Each eval runs both with and without the skill, n ≥ 3 runs per
configuration. **Most runs** means at least ⌈2n/3⌉ of n (2 of 3, 4 of 5, 4 of 6).
`[D]` marks expectations meant to tell the two configurations apart (§10 requires it
only of E1, E2 and E4); `[R]` marks the rewrite expectations that §2 re-checks. Fixtures are under `evals/fixtures/`.

| Eval | Request; fixture | Key expectations |
| --- | --- | --- |
| E1 | Rewrite an AGENTS.md. `e1/`: a 78-line Python CLI file with a persona, default-behaviour rules, `IMPORTANT` lines, generic "the formatter/linter/tests", `uv run mypy src` (not in pyproject), `unittest.TestCase` and a decision tree; pyproject; `.claude/rules/testing.md` requiring plain pytest | **A2 [R]** no persona or default behaviour; **A3 [R]** exact uv commands; **A5 [R][D]** cuts grouped with reasons; A6 [D] rules file not contradicted; **A7 [R][D]** mypy flagged, nothing invented; A8 [D] `/doctor` follow-up, no new files |
| E2 | Fold a preferences file into AGENTS.md. `e2/` | [D] "the default branch" and "the formatter" made specific; [D] every rule accounted for |
| E3 | Merge with precedence. `e3/`: squash-merge vs. "never squash" | [D] the conflict and its winner listed; [D] `team-preferences.md` kept |
| E4 | Merge an overlapping AGENTS.md and CLAUDE.md. `e4/` | [D] CLAUDE.md starts with `@AGENTS.md` and holds only Claude-specific lines; [D] "no `any`" vs "avoid `any`" flagged, stricter kept |
| E5 | Tighten a CLAUDE.md that is a symlink to AGENTS.md. `e5/` | [D] AGENTS.md edited; [D] symlink intact |
| E6 | Rewrite a verbose skill. `e6/csv-cleaning/`: first-person description, explainers, a dated line, nested references | references flattened; no reference content lost; dated line moved, `quick_validate.py` and the linter pass; not padded |
| E7 | Run evals on a skill | routed to skill-creator; nothing changed |
| E8 | Audit only. `e8/` | prompt-audit run or suggested; unchanged |
| E9 | Cut what's derivable from the code. `e8/` | `/doctor` named; unchanged |
| E10 | What's missing? `e8/` | `claude-md-improver` named; unchanged |

## 10. Acceptance criteria

The tests in §8 pass, and:

- Each of E1–E10 passes: with the skill, most runs (§9) pass every expectation.
- E1, E2 and E4 discriminate: without the skill, most runs fail at least one `[D]`
  expectation.
- A rewrite run makes no network call, and reads only SKILL.md, its two reference
  files and the inputs.
- All 33 sections and 6 watch entries resolve live.
- Manual scenarios:
  - **M1. Write a skill end to end.** skill-creator stops after "Test Cases". The
    baseline hash is unchanged after evaluation, and the `old_skill` runs read the
    baseline. The report has eval results and post-delivery prompt-audit findings.
    One run per release, kept manual on purpose: as an eval it would need at least 6
    skill-creator runs per cycle, about ten times the cost of E1–E10.
  - **M2. Without skill-creator.** The skill drafts inline with three or more
    scenarios, and the checklist passes. The report says the draft wasn't
    eval-tested, and gives the install hint.
  - **M3. Guidance PR with a real diff.** Passes the acceptance check in
    [guidance-updates](guidance-updates.md) §8.
  - **M4. Old guidance.** With `as_of` more than 90 days old, the rewrite completes
    offline and the report suggests an update.
  - **M5. Built-in changed.** The watch-issue check in
    [guidance-updates](guidance-updates.md) §8 passes for `w-doctor`.
  - **M6. prompt-audit routes.** Trying each route in turn, none edits a file, and
    the findings appear in the report.
