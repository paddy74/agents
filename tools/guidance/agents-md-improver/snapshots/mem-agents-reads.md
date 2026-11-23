### When Claude Code reads AGENTS.md

By default, Claude reads `AGENTS.md` only when you have no `CLAUDE.md` in your working directory or above it. Here's which of your files count for that check:

* **Count, so Claude reads them instead of `AGENTS.md`**: a `CLAUDE.md`, `.claude/CLAUDE.md`, or `CLAUDE.local.md` in your working directory or any directory above it
* **Don't count, and keep loading alongside `AGENTS.md`**: your `~/.claude/CLAUDE.md`, your organization's managed `CLAUDE.md`, and `.claude/rules/` files

When none count, here's what Claude reads and how you can tell:

* **At session start**: every `AGENTS.md` and `.claude/AGENTS.md` in your working directory and the directories above it. In an interactive session you see a line such as `no CLAUDE.md found; AGENTS.md loaded: /home/you/repo/AGENTS.md` in the conversation
* **As Claude works in subdirectories**: a subdirectory's `AGENTS.md`, when Claude opens a file there with the Read tool and that subdirectory has none of the three `CLAUDE.md` files of its own
* **Inside each `AGENTS.md`**: [`@path` imports](#import-additional-files) are expanded, [`claudeMdExcludes`](#exclude-specific-claude-md-files) patterns apply, and subagents that [start without project instructions](https://code.claude.com/docs/en/sub-agents.md#what-loads-at-startup) start without these files too
* **Not read**: `AGENTS.local.md`, `AGENTS.override.md`, or anything under a `.agents/` directory

> [!NOTE]
>
> Because `CLAUDE.local.md` counts, adding one to keep your own uncommitted instructions in a project that relies on `AGENTS.md` stops Claude from reading `AGENTS.md` for you. To keep your `CLAUDE.local.md` and still have Claude read `AGENTS.md`, set **Project instructions** to [`claude-md-and-agents-md`](#choose-which-instruction-files-load).
