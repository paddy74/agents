#### Audit your instruction files

To have Claude check your instruction files for outdated or conflicting content, run `/doctor prompt-audit` in a session. Claude looks for problems such as instructions written for older models, references to files or commands that don't exist, and files that contradict each other. You get a report of findings with proposed edits, and nothing in your files changes until you ask Claude to apply them.

By default, the audit covers your CLAUDE.md, CLAUDE.local.md, and AGENTS.md files, plus the rules, skills, commands, subagents, and output styles under `.claude/` and `~/.claude/`. To audit one file or directory instead, pass its path, for example `/doctor prompt-audit .claude/skills/deploy`.

The audit runs through the bundled `/claude-api` skill. It's unavailable while that skill is turned off in [`skillOverrides`](https://code.claude.com/docs/en/skills#override-skill-visibility-from-settings) or with [`disableBundledSkills`](https://code.claude.com/docs/en/settings-reference#disablebundledskills). `/doctor prompt-audit` requires Claude Code v2.1.283 or later.
