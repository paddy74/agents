# Method: skills

## Contents
- Rewrite
- Validate
- Frontmatter

## Rewrite
- Keep test: "would removing this cause the agent to do the task worse?" Workflow steps, checklists, validation loops, templates and input/output examples are the skill's payload: tighten them, don't delete them.
- Description: never shorten it to save tokens; it's the only always-loaded part and decides triggering. Third person, what + when, specific key terms, key use case first, within limits. Keep every trigger context.
- Body: state facts and steps, not narrative. Cut explanations of things Claude already knows (what a PDF is, how a common library works). Keep a reason only as a short clause where a rule would otherwise be misapplied.
- Give one default with an escape hatch, not a list of alternatives.
- Match strictness to fragility: exact commands or scripts for fragile operations, heuristics for open-ended ones.
- One term per concept throughout.
- Remove dated phrasing ("as of" plus a year); put deprecated material under an "Old patterns" heading.
- Move material that matters only sometimes into reference files linked directly from SKILL.md (one level). Add a contents list to any reference file over 100 lines.
- Scripts: say whether to execute or read each one; never change their behaviour in this pass. Comment any unexplained constant.
- Keep a cut list (what was removed and why) for the report and for restoring cuts that regress.

## Validate
Check after `quick_validate.py` passes; it doesn't cover these.
- `name` equals the directory name (portable target); `metadata` values are strings.
- Body under 500 lines and about 5,000 tokens (characters ÷ 4); a workflow, steps or routing heading in the first 40 lines.
- Every file linked from SKILL.md links to no other reference file; reference files over 100 lines start with a contents list.
- Every relative link and `${CLAUDE_SKILL_DIR}` path exists; forward slashes only.
- No dated text ("as of" plus a year) outside an "Old patterns" heading; `IMPORTANT`, `MUST` or `NEVER` on at most two lines.
- Every script under `scripts/` is mentioned in SKILL.md or a reference file.

## Frontmatter
- Portable target (claude.ai, API): `name` and `description` plus spec fields only.
- Claude Code target: prefer `disable-model-invocation: true` for task skills with side effects.
