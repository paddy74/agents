### Set up hooks

> [!TIP]
>
> Use hooks for actions that must happen every time with zero exceptions.

[Hooks](https://code.claude.com/docs/en/hooks-guide.md) run scripts automatically at specific points in Claude's workflow. Unlike CLAUDE.md instructions which are advisory, hooks are deterministic and guarantee the action happens.

Claude can write hooks for you. Try prompts like *"Write a hook that runs eslint after every file edit"* or *"Write a hook that blocks writes to the migrations folder."* Edit `.claude/settings.json` directly to configure hooks by hand, and run `/hooks` to browse what's configured.
