---
name: agents-md-improver
description: Rewrites, merges and writes agent instruction files using Anthropic's official guidance (condensed into its reference files). Use when asked to rewrite, tighten, clean up or optimize the wording of an AGENTS.md, CLAUDE.md, CLAUDE.local.md, .claude/rules file or SKILL.md; to merge or combine instruction files or fold preferences into one; or to write, create or turn a workflow into a new skill (drafts with skill-creator, then rewrites and validates). Not for audit-only, trim-only, eval-only or description-tuning requests; those go to /doctor, /doctor prompt-audit or skill-creator.
---

# Agent instructions

## Route
- Rewrite one file → "Rewrite"
- Merge 2+ instruction files → "Merge"
- Write or substantially update a skill → "Write a skill"
- Audit only (find problems, no rewrite) → run prompt-audit (see "Verify and report") and relay its findings; if no route runs it, run "Rewrite" without editing and report findings. Stop.
- Trim, de-duplicate or relocate only, checked-in CLAUDE.md, Claude Code → tell the user `/doctor` does this. Stop.
- Add missing context or session learnings → mention `claude-md-improver` / `/revise-claude-md` if installed; otherwise say this skill doesn't add content. Stop.
- Evals, benchmarks or description tuning only → say so in one line and invoke skill-creator (`skill-creator:skill-creator`, `anthropic-skills:skill-creator` or `skill-creator`).
- Operation or target unclear → ask one question first.

## Preflight
1. Read the two reference files for the profile:
   - instruction files (Rewrite, Merge): [official-instructions.md](references/official-instructions.md) and [method-instructions.md](references/method-instructions.md);
   - skills: [official-skills.md](references/official-skills.md) and [method-skills.md](references/method-skills.md).
2. Read every input in full. In a repo, also read the instruction files that load alongside the target (CLAUDE.md, CLAUDE.local.md, AGENTS.md, `.claude/rules/*.md`) and the build config (`pyproject.toml`, `package.json`, `Makefile`), so the rewrite uses real commands and doesn't contradict a sibling file.

## Rewrite
Apply the profile for the file type from the method file. Leave what its "Left to built-ins" section lists. For a skill, then run "Validate". Edit in place; write new files for pasted input. If the target is a symlink, edit its target.

## Merge
Apply "Merge" in `method-instructions.md`, which ends with "Rewrite".

## Write a skill
1. Find skill-creator in the available skills. None → step 8.
2. Invoke it. Pass the user's request plus: write the draft to `<scratch>/<name>/`; stop after its "Test Cases" step (SKILL.md, bundled files, `evals/evals.json` prompts; no assertions, no runs); don't package, install or tune the description yet. Relay its questions to the user.
3. Baseline: copy the draft to `<scratch>/<name>-baseline/` (not skill-creator's `skill-snapshot/`, which its improve mode overwrites), make it read-only (`chmod -R a-w`), and record its hash: `find <dir> -type f -exec sha256sum {} + | sort | sha256sum`.
4. Apply the skill profile to SKILL.md, every reference file and every script docstring. Never change script behaviour. Keep a cut list.
5. Run "Validate".
6. Re-enter skill-creator in its improve-existing-skill mode on the rewritten draft. Tell it the `old_skill` baseline is already taken at `<scratch>/<name>-baseline/`: point the baseline runs there and don't snapshot. After each iteration, check the baseline hash is unchanged and the `old_skill` runs read that path; re-run any that didn't, and stop and report if the hash changed. A test that passes on the baseline and fails on the rewritten draft is a regression: restore the related cut, re-validate. Re-apply steps 4–5 to changed lines after each skill-creator edit. Run description tuning last, only when the `claude` CLI exists, then re-validate. Without subagents (claude.ai) there is no baseline: report "no regression check possible".
7. Deliver: Claude Code → `~/.claude/skills/<name>/` or `.claude/skills/<name>/` (ask which if unsaid); claude.ai → the host's skill-save tool, else skill-creator's `package_skill.py`. Then run "Verify and report" on the delivered SKILL.md and reference files, including prompt-audit; skipping it is not allowed when a route works.
8. No skill-creator: draft inline from the two skills reference files, write at least three scenarios to `evals/evals.json` (`id`, `prompt`, `expected_output`, `files`), then run steps 4, 5 and 7. Report that the draft wasn't eval-tested or script-validated and that `/plugin install skill-creator@claude-plugins-official` installs skill-creator in Claude Code.

When guidance conflicts: official guidance, then the method file, then skill-creator's or plugin-dev's style advice. Example: write the description in third person within 1,024 characters, keeping the broad trigger contexts skill-creator adds.

## Validate
1. Frontmatter: run `python3 <skill-creator dir>/scripts/quick_validate.py <skill-dir>` (the directory skill-creator loaded from). It needs PyYAML; if it's missing, use `uv run --with pyyaml python3 ...` or ask before installing. Fix errors and re-run until it exits 0. No skill-creator → skip this step.
2. Apply "Validate" in `method-skills.md`. Fix and recheck. Report what remains.

## Verify and report
- Lines before → after.
- No duplicate lines.
- Merge: every input rule accounted for. Skill: validation passes; eval results.
- Prompt-audit on the changed paths, report only, using the first route that works, and fold its findings in:
  1. a subagent (fresh context) that invokes the `claude-api` skill with `prompt-audit <paths>` and returns its findings without editing;
  2. no subagents → invoke `claude-api` with `prompt-audit <paths>` here;
  3. no `claude-api` skill, `claude` CLI (v2.1.283+) on PATH → `claude -p "/doctor prompt-audit <path>"`;
  4. otherwise list `/doctor prompt-audit <path>` as a follow-up.
- Only when prompt-audit didn't run: check every referenced command and path exists.
- Don't commit unless asked.
- Guidance date: the `as_of` date in the official file's frontmatter. With a shell, compute its age, never estimate it: `python3 -c "import datetime as d; print((d.date.today() - d.date.fromisoformat('<as_of>')).days)"`; over 90 → add "update or re-package this skill" to follow-ups. Without a shell, report `as_of` and today's date and don't judge the age.
- Report tersely: cuts as one line per kind (persona, default behaviour, linter-enforced, decision tree, emphasis, other), each `<kind>: <what was cut>, because <reason>`; other changes; conflicts (merge); guidance date; follow-ups: in Claude Code always `/doctor` (trimming and relocation), `/doctor prompt-audit` if it didn't run, then hooks, settings, the `@AGENTS.md` bridge, placeholders.
