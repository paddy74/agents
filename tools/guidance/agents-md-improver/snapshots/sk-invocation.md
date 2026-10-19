### Control who invokes a skill

By default, both you and Claude can invoke any skill. You can type `/skill-name` to invoke it directly, and Claude can load it automatically when relevant to your conversation. Two frontmatter fields let you restrict this:

* **`disable-model-invocation: true`**: Claude can't invoke the skill on its own. Use this for workflows with side effects or that you want to control timing, like `/commit`, `/deploy`, or `/send-slack-message`. You don't want Claude deciding to deploy because your code looks ready.

* **`user-invocable: false`**: Only Claude can invoke the skill. Use this for background knowledge that isn't actionable as a command. A `legacy-system-context` skill explains how an old system works. Claude should know this when relevant, but `/legacy-system-context` isn't a meaningful action for users to take.

This example creates a deploy skill. If you set `disable-model-invocation: true`, Claude can't run the skill automatically:

```yaml theme={null}
---
name: deploy
description: Deploy the application to production
disable-model-invocation: true
---

Deploy $ARGUMENTS to production:

1. Run the test suite
2. Build the application
3. Push to the deployment target
4. Verify the deployment succeeded
```

If Claude tries anyway, Claude Code blocks the call and instructs it not to reproduce the deploy steps another way, so expect Claude to suggest running `/deploy` yourself.

Here's how the two fields affect invocation and context loading:

| Frontmatter | You can invoke | Claude can invoke | When loaded into context |
| :- | :- | :- | :- |
| (default) | Yes | Yes | Description always in context, full skill loads when invoked |
| `disable-model-invocation: true` | Yes | Not on its own | Description not in context, full skill loads when invoked |
| `user-invocable: false` | No | Yes | Description always in context, full skill loads when invoked |

<Note>
  In a regular session, skill descriptions are loaded into context so Claude knows what's available, but full skill content only loads when invoked. [Subagents with preloaded skills](/docs/en/sub-agents#preload-skills-into-subagents) work differently: the full skill content is injected at startup.
</Note>

#### Where you write the skill's name

To run a skill directly, put its name at the start of your message. After plain text, the name gives Claude permission to run the skill but doesn't run it:

| Where | Example | What happens |
| :- | :- | :- |
| At the start of your message | `/deploy staging` | Claude Code runs the skill directly |
| After plain text, as a separate word with no punctuation attached | `go ahead and /deploy to staging` | Nothing runs directly. The name counts as your permission for that message: Claude can run the skill while it responds, and judges from your wording whether you asked it to |

To write about the skill without permitting a run, leave off the slash.
