### Frontmatter reference

Configure a skill with YAML [frontmatter](/docs/en/glossary#frontmatter) between `---` markers at the top of `SKILL.md`, and write the skill's instructions as Markdown after the closing `---`. Field names use lowercase words separated by hyphens, except `when_to_use`. A [command file](#where-skills-live) in `.claude/commands/` accepts the same fields except `name` and `paths`. This example sets four fields:

```yaml theme={null}
---
name: my-skill
description: What this skill does
disable-model-invocation: true
allowed-tools: Read Grep
---

Your skill instructions here...
```

All fields are optional. Only `description` is recommended so Claude knows when to use the skill. A field name must match the table exactly, hyphens included: Claude Code ignores a field it doesn't recognize without reporting an error.

Claude Code reads the frontmatter only when the opening `---` is the file's first line. Otherwise it treats the whole file, `---` markers included, as skill content. If the YAML between the markers doesn't parse, the skill still loads with no fields set; see [Skill not triggering](#skill-not-triggering) to find and fix the error.

Boolean fields accept `yes`, `no`, `on`, `off`, `1`, and `0` in any letter case, in addition to `true` and `false`. Before v2.1.218, Claude Code recognized only `true` and `false`.

| Field | Required | Description |
| :- | :- | :- |
| `name` | No | Command name shown in the `/` menu. Defaults to the directory name. See [How a skill gets its command name](#how-a-skill-gets-its-command-name) for how the field interacts with the name you type to invoke the skill. |
| `description` | Recommended | What the skill does and when to use it. Claude uses this to decide when to apply the skill. If omitted, uses the first non-empty line of the markdown content. Put the key use case first: the combined `description` and `when_to_use` text is truncated at 1,536 characters in the skill listing to reduce context usage. |
| `when_to_use` | No | Additional context for when Claude should invoke the skill, such as trigger phrases or example requests. Appended to `description` in the skill listing and counts toward the 1,536-character cap. |
| `argument-hint` | No | Hint shown during autocomplete to indicate expected arguments. Example: `[issue-number]` or `[filename] [format]`. |
| `arguments` | No | Named positional arguments for [`$name` substitution](#available-string-substitutions) in the skill content. Accepts a space-separated string or a YAML list. Names map to argument positions in order. |
| `disable-model-invocation` | No | Set to `true` to prevent Claude from automatically loading this skill. Use for workflows you want to trigger manually with `/name`. Also prevents the skill from being [preloaded into subagents](/docs/en/sub-agents#preload-skills-into-subagents) and from running when a [scheduled task](/docs/en/scheduled-tasks) fires with the skill as its prompt. Default: `false`. |
| `user-invocable` | No | Set to `false` when only Claude should invoke the skill: Claude Code hides it from the `/` menu and doesn't run it when you type `/name`. Use for background knowledge users shouldn't invoke directly. Default: `true`. |
| `allowed-tools` | No | Tools Claude can use without asking permission during the turn that invokes this skill. The grant clears when you send your next message. Accepts a space- or comma-separated string, or a YAML list. See [Pre-approve tools for a skill](#pre-approve-tools-for-a-skill). |
| `disallowed-tools` | No | Tools removed from Claude's available pool while this skill is active. Use for autonomous skills that should never call certain tools, such as `AskUserQuestion` for a background loop. Accepts a space- or comma-separated string, or a YAML list. The restriction clears when you send your next message. Like deny rules, the field can't remove [`EndConversation`](/docs/en/tools-reference#endconversation-tool-behavior) while any other tool remains. |
| `model` | No | Model to use when this skill is active. The override applies for the rest of the current turn and isn't saved to settings. The session model resumes when you send your next prompt. Accepts the same values as [`/model`](/docs/en/model-config), or `inherit` to keep the active model. A value excluded by your organization's [`availableModels`](/docs/en/model-config#restrict-model-selection) allowlist isn't used, and the session keeps its current model. In [auto mode](/docs/en/permission-modes#eliminate-prompts-with-auto-mode), and in [plan mode while the classifier reviews commands](/docs/en/permission-modes#analyze-before-you-edit-with-plan-mode), a model that auto mode doesn't support also isn't used, and the session keeps its current model. With `context: fork`, the value sets the [forked subagent's model](#run-skills-in-a-subagent) instead, and an excluded value follows the [same rules as a subagent model override](/docs/en/model-config#restrict-model-selection). |
| `effort` | No | [Effort level](/docs/en/model-config#adjust-effort-level) when this skill is active. Overrides the session effort level. When you omit it, the level comes from the [effort resolution order](/docs/en/model-config#adjust-effort-level). Options: `low`, `medium`, `high`, `xhigh`, `max`; available levels depend on the model. |
| `context` | No | Set to `fork` to run in a forked subagent context. See [Run skills in a subagent](#run-skills-in-a-subagent). |
| `agent` | No | Which subagent type to use when `context: fork` is set. |
| `background` | No | Only applies with `context: fork`. Set to `false` to wait for the forked subagent's result in the turn that invoked the skill, instead of [running it in the background](#run-skills-in-a-subagent). Default: `true`. Requires Claude Code v2.1.218 or later. |
| `hooks` | No | Hooks that Claude Code registers when the skill is invoked and keeps running for the rest of the session. See [Hooks in skills and agents](/docs/en/hooks#hooks-in-skills-and-agents) for the configuration format and the `once` option. |
| `paths` | No | Glob patterns that limit when this skill is activated. Accepts a comma-separated string or a YAML list. When set, Claude loads the skill automatically only when working with files matching the patterns. Uses the same format as [path-specific rules](/docs/en/memory#path-specific-rules). |
| `shell` | No | Shell to use for `` !`command` `` and ` ```! ` blocks in this skill. Accepts `bash` (default) or `powershell`. Setting `powershell` runs inline shell commands via PowerShell when the [PowerShell tool](/en/tools-reference#powershell-tool) is enabled: it's on by default on Windows without Git Bash, on by default with Git Bash for claude.ai and Console accounts, and needs `CLAUDE_CODE_USE_POWERSHELL_TOOL=1` in Amazon Bedrock, Google Cloud's Agent Platform, and Microsoft Foundry sessions and on macOS, Linux, and WSL. Set it to `0` to turn the tool off. |
| `metadata` | No | Free-form YAML map for your own key-value data, such as entitlement or catalog fields, read by your own tooling from `SKILL.md`. Claude Code doesn't act on its contents, and drops a value that isn't a map. Don't reuse frontmatter field names such as `paths` as keys. |
| `license` | No | License covering the skill. Part of the [Agent Skills](https://agentskills.io) spec; see [Using skill frontmatter outside Claude Code](#using-skill-frontmatter-outside-claude-code). Claude Code accepts the field but doesn't act on it. |
| `compatibility` | No | Environment requirements for the skill, such as intended products or system prerequisites, as defined by the [Agent Skills](https://agentskills.io) spec; see [Using skill frontmatter outside Claude Code](#using-skill-frontmatter-outside-claude-code). Accepts a string of up to 500 characters. Claude Code accepts the field but doesn't act on it. |

#### Using skill frontmatter outside Claude Code

Claude Code accepts every field in the table above. Outside Claude Code, you can use only the fields in the [Agent Skills](https://agentskills.io) spec:

| Distribution path | Frontmatter fields you can use |
| :- | :- |
| Claude Code skills at [any level](#where-skills-live), including [plugin](/docs/en/plugins/overview) skills | Every field in the table above |
| claude.ai skill uploads, the Skills API, and packaging with `package_skill.py` from [anthropics/skills](https://github.com/anthropics/skills) | `name`, `description`, `license`, `compatibility`, `metadata`, `allowed-tools` |

When you enable a personal skill for your claude.ai account, for example to use it in [Cowork and cloud sessions](#skills-in-cowork-and-cloud-sessions) and routines, you upload it to claude.ai, so the same rules apply.

If you include any field the spec doesn't allow, packaging or upload fails with a hard error instead of ignoring the field:

```
Unexpected key(s) in SKILL.md frontmatter: argument-hint. Allowed properties are: allowed-tools, compatibility, description, license, metadata, name
```

Restricting frontmatter to the spec's six fields avoids the unexpected-key error above. The [Agent Skills spec](https://agentskills.io) and the [Skills API requirements](https://docs.claude.com/en/api/skills-guide) define everything else those paths validate. Claude Code-only body features, such as [dynamic context injection](#inject-dynamic-context), don't function in claude.ai chat or through the API. Claude Code accepts all six fields, so frontmatter that follows the spec loads in Claude Code without changes.

#### How a skill gets its command name

The command you type to invoke a skill comes from where the skill file lives and, for skill directories and plugin skills, from the frontmatter `name` field. In a personal or project skill directory, `name` sets the command that the `/` menu shows and that you type, unless another command already uses that name. The directory name also invokes the skill. In a plugin skill, `name` sets the last segment of the command and the plugin prefix stays in place.

The table below shows where the command name comes from for each layout:

| Skill location | Command name source | Example |
| :- | :- | :- |
| Skill directory under `~/.claude/skills/` or `.claude/skills/` | Frontmatter `name` or the directory name | `.claude/skills/deploy-staging/SKILL.md` → `/deploy-staging`, or `/deploy` with `name: deploy` |
| [Nested](#where-skills-live) `.claude/skills/` directory, when the directory name clashes with another skill | Subdirectory path relative to the working directory, then the skill directory name | `apps/web/.claude/skills/deploy/SKILL.md` → `/apps/web:deploy` |
| File under `.claude/commands/` | File name without extension | `.claude/commands/deploy.md` → `/deploy` |
| File in a subdirectory of `.claude/commands/` | Subdirectory path relative to `commands/` with each `/` replaced by `:`, then the file name without extension | `.claude/commands/frontend/component.md` → `/frontend:component` |
| Plugin `skills/` subdirectory | Frontmatter `name` or the directory name, namespaced by plugin | `my-plugin/skills/review/SKILL.md` → `/my-plugin:review`, or `/my-plugin:fancy` with `name: fancy` |
| Plugin root `SKILL.md` | Frontmatter `name`, with the plugin directory name as a fallback | `my-plugin/SKILL.md` with `name: review` → `/my-plugin:review`. See [a single skill at the plugin root](/docs/en/plugins/components#skills) |
| Skill [synced from claude.ai](#how-synced-skills-behave) | The skill's name on your claude.ai account, prefixed with `anthropic-skills:` | Account skill `deploy` → `/anthropic-skills:deploy`, or `/deploy` while no other command uses that name |

In a plugin skill, the frontmatter `name` replaces the directory name in the last segment of the command, so `my-plugin/skills/review/SKILL.md` with `name: fancy` becomes `/my-plugin:fancy`. The bare `/fancy` also invokes the skill unless another command already uses that name. If the `name` you write already starts with the plugin's own prefix, Claude Code doesn't add the prefix again on v2.1.246 or later. For example, `name: my-plugin:fancy` still becomes `/my-plugin:fancy`. From v2.1.216 through v2.1.245, Claude Code doubled the prefix when the `name` already carried it.

In [non-interactive sessions](/docs/en/headless), the names `help` and `feedback` aren't reserved for their terminal-only built-in commands, so a plugin skill with one of those names keeps its bare command there. Every other terminal-only built-in's name, such as `/login`, stays reserved even though the command can't run in those sessions.

For a plugin-root `SKILL.md`, there is no skill directory to take the name from, so `name` supplies the whole final segment. Without a `name` field, Claude Code falls back to the plugin's directory name.

#### Characters a skill name can't hold

If a skill or custom command is missing from the `/` menu, or the menu doesn't show a skill's frontmatter `name`, check the name. Claude Code refuses a command name or a frontmatter `name` that contains characters such as these:

* A zero-width space or a control character
* A private-use or unassigned character, such as a glyph from an icon font
* A character that changes the direction of the text around it
* A blank other than one plain space between words, such as a no-break space, two spaces in a row, or a space at the start or end
* `<` or `>`

A custom command or skill doesn't load when Claude Code refuses its directory or file name. Rename that folder or file to remove the characters. A skill still loads when these characters are only in a plugin skill folder's name or in its frontmatter `name`:

* **Folder in a plugin's `skills/` directory or its manifest's [`skills` paths](/docs/en/plugins/components#skills)**: you don't need to rename the folder. These characters become hyphens in the skill's command name, so type the command with the hyphens.
* **Frontmatter `name`**: the `/` menu doesn't show the `name` value and typing it doesn't invoke the skill. Edit the `name:` line to remove the characters.

To find out which name Claude Code refused, start it with [`claude --debug`](/docs/en/cli-reference#cli-flags) from your shell and search the [debug log](/docs/en/debug-your-config) for `[names]`. In an interactive session, a [startup notice](/docs/en/errors#skill-or-command-name-refused) also tells you that names were refused. After a rename or a `name:` edit, restart the session, unless the file is in a directory Claude Code [watches for changes](#live-change-detection).

#### Available string substitutions

Skills support string substitution for dynamic values in the skill content:

| Variable | Description |
| :- | :- |
| `$ARGUMENTS` | All arguments passed when invoking the skill. When no placeholder receives an argument, Claude Code appends them as `ARGUMENTS: <value>`. See [Pass arguments to skills](#pass-arguments-to-skills). |
| `$ARGUMENTS[N]` | Access a specific argument by 0-based index, such as `$ARGUMENTS[0]` for the first argument. |
| `$N` | Shorthand for `$ARGUMENTS[N]`, such as `$0` for the first argument or `$1` for the second. |
| `$name` | Named argument declared in the [`arguments`](#frontmatter-reference) frontmatter list. Names map to positions in order, so with `arguments: [issue, branch]` the placeholder `$issue` expands to the first argument and `$branch` to the second. |
| `${CLAUDE_SESSION_ID}` | The current session ID. Useful for logging, creating session-specific files, or correlating skill output with sessions. |
| `${CLAUDE_EFFORT}` | The current effort level: `low`, `medium`, `high`, `xhigh`, or `max`. Use this to adapt skill instructions to the active effort setting. |
| `${CLAUDE_SKILL_DIR}` | The directory containing the skill's `SKILL.md` file. For plugin skills, this is the skill's subdirectory within the plugin, not the plugin root. Use this in bash injection commands to reference scripts or files bundled with the skill, regardless of the current working directory. |
| `${CLAUDE_PROJECT_DIR}` | The project root directory. This is the same path [hooks](/docs/en/hooks#reference-scripts-by-path) and MCP servers receive as `CLAUDE_PROJECT_DIR`. Use this to reference project-local scripts or files, such as `${CLAUDE_PROJECT_DIR}/.claude/hooks/helper.sh`, independent of where the skill is installed. |
| `${CLAUDE_PLUGIN_ROOT}` | The plugin's installation directory. Substituted only in plugin skills. Use this to reference scripts or files bundled anywhere in the plugin, including resources shared between the plugin's skills. See [plugin environment variables](/docs/en/plugins/manifest-reference#environment-variables). |
| `${CLAUDE_PLUGIN_DATA}` | The plugin's [persistent data directory](/docs/en/plugins/components#path-variables-and-persistent-data), which survives plugin updates. Substituted only in plugin skills. Use this to reference installed dependencies, generated files, or caches that must outlive an update. |

Claude Code substitutes `${CLAUDE_SKILL_DIR}` and `${CLAUDE_PROJECT_DIR}` in two places: the skill's markdown content, and Bash rules in the [`allowed-tools`](#frontmatter-reference) frontmatter. In a plugin skill, Claude Code substitutes `${CLAUDE_PLUGIN_ROOT}` and `${CLAUDE_PLUGIN_DATA}` in the same two places. Using the same variable in both places lets a skill run a bundled script without a permission prompt. The following skill shows the pattern:

```yaml theme={null}
---
name: render-chart
description: Render a chart from a CSV file
allowed-tools: Bash(${CLAUDE_SKILL_DIR}/scripts/render.sh *)
---

Run `${CLAUDE_SKILL_DIR}/scripts/render.sh <csv-file>` to render the chart.
```

If this skill is installed at `~/.claude/skills/render-chart/`, both occurrences of `${CLAUDE_SKILL_DIR}` expand to that directory. The `allowed-tools` rule then matches the exact command the skill body tells Claude to run, so the script runs without prompting.

Indexed arguments use shell-style quoting, so wrap multi-word values in quotes to pass them as a single argument. For example, `/my-skill "hello world" second` makes `$0` expand to `hello world` and `$1` to `second`. The `$ARGUMENTS` placeholder always expands to the full argument string as typed.

An indexed placeholder with no corresponding argument, such as `$2` when only one argument was passed, stays in the content unchanged. A named placeholder from the [`arguments`](#frontmatter-reference) frontmatter with no matching argument expands to an empty string.

If you pass an argument value that itself contains text such as `$1` or `$ARGUMENTS`, Claude Code inserts it as literal text and doesn't expand it. For example, if a skill's body contains `Summarize $0` and you run `/summarize "$ARGUMENTS from yesterday"`, Claude receives `Summarize $ARGUMENTS from yesterday`. Claude Code still replaces `${CLAUDE_*}` variables such as `${CLAUDE_SKILL_DIR}` after it inserts the arguments.

To include a literal `$` before a digit, `ARGUMENTS`, or a declared argument name, such as `$1.00` in prose, escape it with a backslash: `\$1.00`. A backslash before any other `$` is left unchanged. Only a single backslash directly before the token escapes it. A doubled backslash such as `\\$1` leaves both backslashes in place, and `$1` still expands to the argument value. The backslash escape covers only these argument placeholders. A backslash doesn't prevent substitution of a `${CLAUDE_*}` variable where the variable applies.

**Example using substitutions:**

```yaml theme={null}
---
name: session-logger
description: Log activity for this session
---

Log the following to logs/${CLAUDE_SESSION_ID}.log:

$ARGUMENTS
```
