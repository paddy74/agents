# Method: instruction files

## Contents
- Rewrite
- Merge
- Left to built-ins

## Rewrite
- Keep test for every line: "would removing this cause the agent to make mistakes?" If not, cut it.
- Cut: personas and motivation ("You are a senior engineer..."); default model behaviour ("read files before editing", "match existing conventions"); rules a configured linter or formatter enforces; decision trees that restate other rules; emphasis on more than one line.
- Rewrite each rule as one imperative, verifiable line. Add a short clause of reason only where the purpose isn't obvious.
- Specialize generic wording to the project's real tools ("the formatter" → `uv run ruff format .`). Take commands from build config (`pyproject.toml`, `package.json`, `Makefile`); never invent one, and flag a command that build config doesn't define.
- Structure: one-line project summary first, then Hard rules, Commands, Code style, Design, Testing, Git, Scope, Communication, with only the sections that have content.
- Don't introduce a rule that contradicts a sibling instruction file (CLAUDE.md, CLAUDE.local.md, AGENTS.md, `.claude/rules/*.md`) you read in preflight.
- If the user wants personal preferences in the shared file, keep them and note it once.
- Preserve `paths:` frontmatter in `.claude/rules/*.md` and leave `@imports` intact.
- If the target is a symlink, edit its target and leave the link in place.
- Fix typos and broken list nesting.
- Flag HTML-comment placeholders: Claude Code strips them, but other agents may read them.
- Report cuts grouped by kind, each group with its reason: persona (adds no instruction), default behaviour (the model already does it), linter-enforced (the tool enforces it), decision tree (restates other rules), emphasis (emphasis on many lines cancels out), other (fails the keep test).
- Report follow-ups outside the file: hooks, settings, the `@AGENTS.md` bridge, the `/config` "Project instructions" setting.

## Merge
1. Precedence: as given by the user. Default: project-specific beats generic; the merge target is the base.
2. Output shape: for an AGENTS.md and a CLAUDE.md of the same repo, default to a canonical AGENTS.md plus a CLAUDE.md that starts with `@AGENTS.md` and holds only Claude-specific lines. Use a single file only when the user asks. Mention the `claude-md-and-agents-md` setting as the alternative.
3. Split every input into atomic rules.
4. Classify each against the base:
   - Duplicate (same meaning) → keep the most specific wording once.
   - Refinement (same topic, adds detail) → combine into one line.
   - Conflict → higher precedence wins; list it in the report.
   - New → keep, specialized to the project's tools.
5. Inclusive by default: keep every non-duplicate, non-conflicting rule even if it fails the keep test; list such rules as optional cuts instead of removing them.
6. Place rules under the base's existing headings; add a heading only when none fits.
7. Account for every input rule: kept, combined, or dropped as a duplicate or conflict.
8. Run "Rewrite" on the result.

## Left to built-ins (Claude Code)
Don't do these; list the command as a follow-up in the report.
- Cutting content derivable from the code, de-duplicating CLAUDE.local.md against CLAUDE.md, moving guidance into skills or nested CLAUDE.md files → `/doctor`.
- Finding old-model wording, missing files or commands, and contradictions across all instruction files → `/doctor prompt-audit <path>` (run by the skill by the route order in SKILL.md "Verify and report").
- Outside Claude Code, where neither exists: note relocation candidates (path-scoped rules, skills, hooks) in the report instead, without creating files.
