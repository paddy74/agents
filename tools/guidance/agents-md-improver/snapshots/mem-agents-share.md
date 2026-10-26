### Share one file with other coding tools

When Claude isn't reading your `AGENTS.md` directly, you can still keep it as the one file every tool shares by putting an `@AGENTS.md` import in a `CLAUDE.md` next to it. Do this when your project also has a `CLAUDE.md`, when you've set **Project instructions** to `claude-md`, or in sessions that [can't load `AGENTS.md`](#when-agents-md-support-is-unavailable). Add any Claude-specific instructions below the import, and Claude reads the imported file first, then the rest:

```markdown CLAUDE.md theme={null}
@AGENTS.md

## Claude Code

Use plan mode for changes under `src/billing/`.
```

If you don't need Claude-specific content, a symlink also works:

```bash theme={null}
ln -s AGENTS.md CLAUDE.md
```

The command prints no output on success. Before you choose the symlink over the import, check these constraints:

* **Editing**: Claude reads `CLAUDE.md` through the link, but the Edit and Write tools [refuse to write through a symlink](https://code.claude.com/docs/en/errors.md#refusing-after-a-symlink-changed), and the refusal directs Claude to edit the link's target, `AGENTS.md`, instead
* **Windows**: if you or anyone who clones the repository works on Windows, use the `@AGENTS.md` import instead. Creating a symlink there needs Administrator privileges or Developer Mode, and Git checks a committed symlink out as a plain text file unless `core.symlinks` is enabled, which leaves that clone with a one-line `CLAUDE.md` in place of your instructions

With either approach, run `/context` in your next session and confirm `CLAUDE.md` appears under **Memory files**.
