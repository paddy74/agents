### Write effective instructions

Claude treats CLAUDE.md files as context, not enforced configuration, so how you write instructions affects how reliably Claude follows them. Write instructions that are concrete enough to verify:

* "Use 2-space indentation" instead of "Format code properly"
* "Run `npm test` before committing" instead of "Test your changes"
* "API handlers live in `src/api/handlers/`" instead of "Keep files organized"

Keep your files short, organized, and consistent:

* **Size**: target under 200 lines per CLAUDE.md file. Longer files consume more context and reduce adherence. Move instructions that matter for only part of the codebase into [path-scoped rules](#path-specific-rules), which load only when Claude works with matching files. [Imports](#import-additional-files) help you organize a long file but don't reduce its context cost, because imported files load together with the CLAUDE.md that imports them.
* **Structure**: group related instructions under markdown headers and bullets. Organized sections are easier for Claude to follow than dense paragraphs.
* **Consistency**: if two instructions contradict each other, Claude may pick one arbitrarily. Review your CLAUDE.md files, nested CLAUDE.md files in subdirectories, and [`.claude/rules/`](#organize-rules-with-claude/rules/) periodically to remove outdated or conflicting instructions. To have Claude find them for you, [run a prompt audit](#audit-your-instruction-files).

#### Audit your instruction files

To have Claude check your instruction files for outdated or conflicting content, run `/doctor prompt-audit` in a session. Claude looks for problems such as instructions written for older models, references to files or commands that don't exist, and files that contradict each other. You get a report of findings with proposed edits, and nothing in your files changes until you ask Claude to apply them.

By default, the audit covers your CLAUDE.md, CLAUDE.local.md, and AGENTS.md files, plus the rules, skills, commands, subagents, and output styles under `.claude/` and `~/.claude/`. To audit one file or directory instead, pass its path, for example `/doctor prompt-audit .claude/skills/deploy`.

The audit runs through the bundled `/claude-api` skill. It's unavailable while that skill is turned off in [`skillOverrides`](https://code.claude.com/docs/en/skills#override-skill-visibility-from-settings) or with [`disableBundledSkills`](https://code.claude.com/docs/en/settings-reference#disablebundledskills). `/doctor prompt-audit` requires Claude Code v2.1.283 or later.
