### My CLAUDE.md is too large

Files over 200 lines consume more context and may reduce adherence. Claude Code skips a file over 4 MiB. Use [path-scoped rules](#path-specific-rules) to load instructions only when Claude works with matching files, or trim content that isn't needed in every session. Splitting into [`@path` imports](#import-additional-files) helps organization but doesn't reduce context, since imported files load with the CLAUDE.md importing them.

If one of your instruction files is over the recommended length, you see a warning at startup and when you run `/status`. You also see a warning when files that are each within that length add up past a combined limit at session start. Each CLAUDE.md, rules file, and `@path` import counts as a separate file.

The [`/doctor`](https://code.claude.com/docs/en/commands#all-commands) checkup proposes trims for a checked-in CLAUDE.md: it cuts content Claude can derive from the codebase, such as directory layouts, dependency lists, and architecture overviews, and keeps pitfalls, rationale, and conventions that differ from tool defaults.

> [!NOTE]
>
> Keep each path-scoped rules file within [its own per-file size limit](#claude-ignores-the-end-of-my-subdirectory-claude-md), because Claude receives only the start of a file that's over it.
