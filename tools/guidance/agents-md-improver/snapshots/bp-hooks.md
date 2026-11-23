### Enforce steps with hooks

[Hooks](https://code.claude.com/docs/en/hooks-guide.md) run something of yours at fixed points in Claude's loop: before or after a tool call, when Claude tries to stop, when a session starts, and so on. That something can be:

* A shell command (the usual case)
* A POST to an HTTP endpoint
* A tool call on one of your MCP servers
* A [`prompt` or `agent` hook](https://code.claude.com/docs/en/hooks#hook-handler-fields), which lets a model decide

A `prompt` or `agent` hook asks *another model* to decide, so it isn't deterministic either. For real enforcement, use a `command`, `http`, or `mcp_tool` hook, and add [`onFailure: "block"`](https://code.claude.com/docs/en/hooks#block-the-action-when-a-hook-fails) if the action should also be stopped when the hook itself crashes or times out. For a hook that scans commits for secrets, say, you'd rather block the commit than let it through unscanned while the scanner is down.

Here's the formatter rule as a `PostToolUse` hook. It runs after every `Edit` or `Write`, and whether Claude remembers the rule no longer matters, because Claude isn't the one running it:

```json .claude/settings.json theme={null}
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          { "type": "command", "command": "f=$(jq -r '.tool_input.file_path') && npx prettier --write --ignore-unknown \"$f\"" }
        ]
      }
    ]
  }
}
```

To check the hook, ask Claude to add a badly indented line to a file Prettier formats. The saved file comes back with the indentation fixed.

The migrations rule becomes a [`PreToolUse` hook](https://code.claude.com/docs/en/hooks-guide#block-edits-to-protected-files) that exits with code 2 for any path under `migrations/`. You don't have to write it yourself: `write a hook that blocks edits to the migrations folder` works as a prompt, and `/hooks` shows the result. Don't overdo it, though: a hook is for a rule with *zero* exceptions, and `Prefer named exports` has plenty, so that one stays in `CLAUDE.md`.
