### Choose which instruction files load

To change which files Claude reads, type `/config` in a Claude Code session to open the settings panel, then set **Project instructions** to one of these values:

| Value | What Claude reads |
| :- | :- |
| `claude-md-or-agents-md` | Your `CLAUDE.md` files, or your `AGENTS.md` files when you have no `CLAUDE.md` or `CLAUDE.local.md` in your working directory or above it. This is the default |
| `claude-md-and-agents-md` | Your `CLAUDE.md` and `AGENTS.md` files together, each directory's `CLAUDE.md` files first and its `AGENTS.md` after them. Claude Code skips an `AGENTS.md` it has already loaded, so one that your `CLAUDE.md` imports or symlinks to isn't read twice |
| `claude-md` | Your `CLAUDE.md` files only |
| `managed-only` | Only your organization's managed `CLAUDE.md` and [auto memory](#auto-memory) at launch. Your project, local, and user `CLAUDE.md` files, your `.claude/rules/` files, and every `AGENTS.md` are left out. A subdirectory's `CLAUDE.md` and `.claude/rules/` files, and [path-scoped rules](#path-specific-rules), still load on demand |

You can also set the value in a settings file instead of `/config`. Add it to [`pluginConfigs`](/docs/en/settings-reference#pluginconfigs) under `cc-plugin-agents-md@builtin`, the ID of the built-in plugin that reads `AGENTS.md`. Claude Code reads the entry from `~/.claude/settings.json`, a `--settings` file, or [managed settings](/docs/en/managed-settings), and ignores it in project and local settings files. This example has Claude read both files:

```json settings.json theme={null}
{
  "pluginConfigs": {
    "cc-plugin-agents-md@builtin": {
      "options": { "instructionFiles": "claude-md-and-agents-md" }
    }
  }
}
```

Before v2.1.285, the plugin's ID was `agents-md@builtin`, and Claude Code ignored an entry under `cc-plugin-agents-md@builtin`. If earlier versions also read your settings file, use `agents-md@builtin` there. Claude Code v2.1.285 and later reads an entry under either ID.

Your change applies from the next message you send and in every new session.
