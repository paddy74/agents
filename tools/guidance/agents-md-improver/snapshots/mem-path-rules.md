#### Path-specific rules

Rules can be scoped to specific files using YAML frontmatter with the `paths` field. These conditional rules only apply when Claude is working with files matching the specified patterns.

```markdown theme={null}
---
paths:
  - "src/api/**/*.ts"
---

# API Development Rules

- All API endpoints must include input validation
- Use the standard error response format
- Include OpenAPI documentation comments
```

A path-scoped rule loads when Claude uses the Read, Write, or Edit tool on a matching file. It also loads when Claude views a matching file with a Bash command that [counts as a read](https://code.claude.com/docs/en/tools-reference.md#edit-tool-behavior), such as `cat` or `head` on a single file. Matching also works when Claude reaches a file through a symlinked path to the project directory, for example in a symlinked checkout.

Each pattern is relative to the rule's base directory:

* **Project rules**: the directory that contains the rule's `.claude` folder
* **[User-level rules](#user-level-rules)**: the session's [primary working directory](https://code.claude.com/docs/en/permissions.md#working-directories)

To have path-scoped rules load for files in a sibling git worktree, start Claude Code in that worktree or [move the session there with `/cd`](https://code.claude.com/docs/en/permissions#move-the-session-to-another-directory).

Use glob patterns in the `paths` field to match files by extension, directory, or any combination:

| Pattern | Matches |
| - | - |
| `**/*.ts` | `.ts` files anywhere under the base directory |
| `src/**/*` | All files under the base directory's `src/` |
| `*.md` | `.md` files anywhere under the base directory |
| `/*.md` | `.md` files directly in the base directory, not in subfolders |
| `src/components/*.tsx` | `.tsx` files directly in the base directory's `src/components/`, not in subfolders |

Glob syntax treats `[` as the start of a bracket expression such as `[abc]`. A pattern with a `[` that can't be read as a bracket expression, such as `photos [2024/**`, is invalid: it matches nothing, and the rule's other patterns keep working. To match a literal `[` in a file name, escape it inside single quotes, as in `'photos \[2024/**'`.

You can specify multiple patterns and use brace expansion to match multiple extensions in one pattern:

```markdown theme={null}
---
paths:
  - "src/**/*.{ts,tsx}"
  - "lib/**/*.ts"
  - "tests/**/*.test.ts"
---
```

Each brace group multiplies the number of expanded patterns: `src/*.{ts,tsx}` expands to two patterns, and `{a,b}/{c,d}/*.{ts,tsx}` to eight. To keep expansion bounded, a rule's whole `paths` list shares one budget of 1,000 expanded patterns and 4 MiB, and patterns without braces don't count against it.

Claude Code uses any pattern that would exceed the budget unexpanded, and its literal braces match no files.
