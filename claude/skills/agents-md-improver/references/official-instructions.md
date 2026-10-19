---
as_of: 2026-10-19
sources:
  mem: https://code.claude.com/docs/en/memory
  bp: https://code.claude.com/docs/en/best-practices
---
# Official guidance: instruction files (condensed)

## Contents
- What belongs
- How to write
- Where content goes
- Loading
- AGENTS.md
- Compliance

## What belongs
- Facts needed every session: commands, conventions, "always do X" rules; layout only when it can't be derived from the code. [mem-when-to-add]
- Add an entry when the agent makes the same mistake a second time, a review catches missing context, the same correction is retyped in a later session, or a new teammate would need it. [mem-when-to-add]
- Include: commands the agent can't guess; style rules that differ from defaults; testing instructions and preferred runners; repo etiquette (branches, PR conventions); project-specific architectural decisions; environment quirks (required env vars); non-obvious gotchas. [bp-write-effective]
- Exclude: anything derivable from the code; standard language conventions; detailed API docs (link instead); frequently changing info; long explanations or tutorials; file-by-file descriptions; self-evident advice ("write clean code"). [bp-write-effective]
- `/doctor` (Claude Code) proposes cuts for derivable content (directory layouts, dependency lists, architecture overviews) and keeps pitfalls, rationale and conventions that differ from tool defaults. [mem-too-large]
- Claude Code warns at startup and in `/status` when a file is over the recommended length, and when files within it add up past a combined limit; each CLAUDE.md, rules file and `@path` import counts separately. [mem-too-large]

## How to write
- Make every instruction concrete enough to verify ("Use 2-space indentation", not "format code properly"). [mem-write-effective]
- Target under 200 lines per file; longer files cost context and reduce adherence. [mem-write-effective]
- Group under markdown headings with bullets, not dense paragraphs. [mem-write-effective]
- Remove contradictions across CLAUDE.md, nested CLAUDE.md and `.claude/rules/`; the agent may pick either side. [mem-write-effective]
- `/doctor prompt-audit [path]` (Claude Code) reports old-model instructions, missing files and commands, and contradictions across CLAUDE.md, CLAUDE.local.md, AGENTS.md, rules, skills, commands, subagents and output styles; it proposes edits and applies none. [mem-audit]
- Prune test: "Would removing this cause mistakes?" If not, cut it. If a rule is ignored, the file is probably too long. [bp-write-effective]
- Emphasis ("IMPORTANT") on a single line only; emphasizing many lines cancels out. [bp-write-effective]

## Where content goes
- Multi-step procedure or occasional domain knowledge → skill. [mem-when-to-add, bp-write-effective]
- Relevant only to some files → `.claude/rules/*.md` with `paths:` globs; loads when Read/Write/Edit touches a matching file. `paths` is the only frontmatter field read. Rules without `paths` load at launch. [mem-path-rules]
- Must happen every time with no exceptions → hook; instructions are advisory, hooks are deterministic. [bp-hooks, mem-not-following]
- `@path` imports organize a file but don't reduce context; imported files load at launch. [mem-write-effective]

## Loading
- Block-level HTML comments are stripped before injection; comments inside code blocks stay. [mem-how-load]
- CLAUDE.md and CLAUDE.local.md files from the working directory upward are concatenated, root first; subdirectory files load when Claude reads files there. [mem-how-load]

## AGENTS.md
- Default: Claude Code reads AGENTS.md only when no CLAUDE.md, `.claude/CLAUDE.md` or CLAUDE.local.md exists in the working directory or above. User and managed CLAUDE.md and `.claude/rules/` don't count. AGENTS.local.md, AGENTS.override.md and `.agents/` are never read. [mem-agents-reads]
- Adding a CLAUDE.local.md to an AGENTS.md project stops AGENTS.md being read. [mem-agents-reads]
- `/config` → "Project instructions": `claude-md-or-agents-md` (default), `claude-md-and-agents-md` (both), `claude-md`, `managed-only`. Recommend `/config` rather than a settings-file entry; the built-in plugin ID used in settings has changed between versions. Some sessions can't read AGENTS.md directly. [mem-choose-files]
- Bridge: put `@AGENTS.md` at the top of CLAUDE.md and Claude-specific rules below. A symlink also works, but Edit/Write refuse to write through it (edit the target) and Windows clones break. [mem-agents-share]

## Compliance
- CLAUDE.md arrives as a user message after the system prompt; compliance isn't guaranteed for vague or conflicting rules. [mem-not-following]
- If the file sets commit or PR rules, turn off the built-in ones with `includeGitInstructions` and set `attribution`. [mem-not-following]
