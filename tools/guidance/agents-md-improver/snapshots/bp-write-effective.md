### Write an effective CLAUDE.md

> [!TIP]
>
> Run `/init` to generate a starter CLAUDE.md file based on your current project structure, then refine over time.

CLAUDE.md is a special file that Claude reads at the start of every conversation. Include Bash commands, code style, and workflow rules. This gives Claude persistent context it can't infer from code alone.

There's no required format for CLAUDE.md files, but keep it short and human-readable. For example:

```markdown CLAUDE.md theme={null}
# Code style
- Use ES modules (import/export) syntax, not CommonJS (require)
- Destructure imports when possible (eg. import { foo } from 'bar')

# Workflow
- Be sure to typecheck when you're done making a series of code changes
- Prefer running single tests, and not the whole test suite, for performance
```

Run `/context` to confirm Claude loaded the file. CLAUDE.md is loaded every session, so only include things that apply broadly. For domain knowledge or workflows that are only relevant sometimes, use [skills](https://code.claude.com/docs/en/skills.md) instead. Claude loads them on demand without bloating every conversation.

Keep it concise. For each line, ask: *"Would removing this cause Claude to make mistakes?"* If not, cut it. Bloated CLAUDE.md files cause Claude to ignore your actual instructions!

| ✅ Include | ❌ Exclude |
| - | - |
| Bash commands Claude can't guess | Anything Claude can figure out by reading code |
| Code style rules that differ from defaults | Standard language conventions Claude already knows |
| Testing instructions and preferred test runners | Detailed API documentation (link to docs instead) |
| Repository etiquette (branch naming, PR conventions) | Information that changes frequently |
| Architectural decisions specific to your project | Long explanations or tutorials |
| Developer environment quirks (required env vars) | File-by-file descriptions of the codebase |
| Common gotchas or behaviors that aren't self-evident | Self-evident practices like "write clean code" |

If Claude keeps doing something you don't want despite having a rule against it, the file is probably too long and the rule is getting lost. If Claude asks you questions that are answered in CLAUDE.md, the phrasing might be ambiguous. Treat CLAUDE.md like code: review it when things go wrong, prune it regularly, and test changes by observing whether Claude's behavior actually shifts. For a checked-in CLAUDE.md, run [`/doctor`](https://code.claude.com/docs/en/commands#all-commands) and Claude proposes cuts for content it can derive from the codebase.

If Claude keeps skipping one instruction, add emphasis such as "IMPORTANT" to that line alone. If you emphasize many lines, none of them stands out. Check CLAUDE.md into git so your team can contribute. The file compounds in value over time.

CLAUDE.md files can import additional files using `@path/to/import` syntax. For import rules and where CLAUDE.md files can live, see [CLAUDE.md files](https://code.claude.com/docs/en/memory.md#claude-md-files).
