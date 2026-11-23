#### Using skill frontmatter outside Claude Code

Claude Code accepts every field in the table above. Outside Claude Code, you can use only the fields in the [Agent Skills](https://agentskills.io) spec:

| Distribution path | Frontmatter fields you can use |
| :- | :- |
| Claude Code skills at [any level](#where-skills-live), including [plugin](https://code.claude.com/docs/en/plugins/overview.md) skills | Every field in the table above |
| claude.ai skill uploads, the Skills API, and packaging with `package_skill.py` from [anthropics/skills](https://github.com/anthropics/skills) | `name`, `description`, `license`, `compatibility`, `metadata`, `allowed-tools` |

When you enable a personal skill for your claude.ai account, for example to use it in [Cowork and cloud sessions](#skills-in-cowork-and-cloud-sessions) and scheduled tasks, you upload it to claude.ai. The same rules apply to that upload.

If you include any field the spec doesn't allow, packaging or upload fails with a hard error instead of ignoring the field:

```
Unexpected key(s) in SKILL.md frontmatter: argument-hint. Allowed properties are: allowed-tools, compatibility, description, license, metadata, name
```

Restricting frontmatter to the spec's six fields avoids the unexpected-key error above. The [Agent Skills spec](https://agentskills.io) and the [Skills API requirements](https://docs.claude.com/en/api/skills-guide) define everything else those paths validate. Claude Code-only body features, such as [dynamic context injection](#inject-dynamic-context), don't function in claude.ai chat or through the API. Claude Code accepts all six fields, so frontmatter that follows the spec loads in Claude Code without changes.
