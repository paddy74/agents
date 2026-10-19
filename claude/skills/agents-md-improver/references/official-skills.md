---
as_of: 2026-10-17
sources:
  skills: https://code.claude.com/docs/en/skills
  sbp: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
  spec: https://agentskills.io/specification
---
# Official guidance: skills (condensed)

## Contents
- Structure and frontmatter
- Descriptions
- Body
- References and scripts
- Checklist

## Structure and frontmatter
- Only `name` + `description` load up front; SKILL.md loads on trigger; other files load when read. [sbp-concise, sk-supporting-files]
- `name`: ≤64 chars, lowercase letters/digits/hyphens, no XML tags, no "anthropic" or "claude"; gerund form preferred (`processing-pdfs`); avoid vague names (`helper`, `utils`). [sbp-yaml, sbp-naming]
- Agent Skills spec (portable): `name` matches the directory, no leading/trailing hyphen, no `--`; `compatibility` ≤500 chars; `metadata` maps strings to strings. [spec-frontmatter]
- Spec loading tiers: metadata ~100 tokens at startup; SKILL.md body under ~5,000 tokens on activation; other files only when needed. [spec-disclosure]
- Frontmatter is read only when the opening `---` is the file's first line. [sk-frontmatter]
- For claude.ai uploads, the Skills API and `package_skill.py`, frontmatter is limited to `name`, `description`, `license`, `compatibility`, `metadata`, `allowed-tools`; other fields fail packaging. Claude Code ignores unknown fields silently. [sk-frontmatter-ext, sk-frontmatter]
- Claude Code fields: `disable-model-invocation: true` for side-effect tasks the user should trigger; `user-invocable: false` for background knowledge; `context: fork` to run in a subagent. [sk-frontmatter, sk-invocation]

## Descriptions
- Non-empty, ≤1,024 chars, no XML tags, always third person ("Processes Excel files…", not "I can…" or "You can…"). [sbp-yaml, sbp-descriptions]
- State what it does and when to use it, with specific key terms; key use case first. Claude Code truncates `description` + `when_to_use` at 1,536 chars in listings. [sbp-descriptions, sk-frontmatter]

## Body
- Assume Claude is already smart; justify every paragraph's token cost. [sbp-concise]
- Once loaded, skill content stays in context across turns; write like CLAUDE.md: state what to do, not how or why. [sk-lifecycle, sk-content-types]
- After compaction only the first ~5,000 tokens of each invoked skill are kept; put the most important instructions first. [sk-lifecycle]
- Body under 500 lines; split beyond that. [sbp-checklist, sk-supporting-files]
- Match freedom to fragility: heuristics for open tasks, parameterized scripts for preferred patterns, exact scripts for fragile operations. [sbp-freedom]
- One term per concept. [sbp-terms]
- No time-sensitive statements; put old material under an "Old patterns" section. [sbp-time]
- Give a default with an escape hatch, not many options; forward-slash paths only. [sbp-anti]
- Complex tasks: numbered steps or a copyable checklist, plus validate → fix → repeat loops. [sbp-checklist]

## References and scripts
- Link reference files directly from SKILL.md; never nest references more than one level. [sbp-nesting]
- Reference files over 100 lines start with a contents list. [sbp-toc]
- Organize references by domain with descriptive names. [sbp-disclosure]
- Scripts: handle errors themselves, justify constants, list required packages, say whether to execute or read. [sbp-checklist]

## Checklist
- At least three evaluations; test with the models the skill will run on; review with real usage. [sbp-checklist]
- Measure with a baseline: run realistic prompts in a fresh session with the skill on and off; skill-creator automates this for single skills, `claude plugin eval` for plugin skills (formats aren't interchangeable). [sk-evaluate]
