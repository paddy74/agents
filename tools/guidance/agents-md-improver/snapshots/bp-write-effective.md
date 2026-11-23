### Keep CLAUDE.md short

Claude Code loads [`CLAUDE.md`](https://code.claude.com/docs/en/memory) into every session, which means every line in it takes a little of Claude's attention on *every* task, whether it's relevant or not. That's why the file works best when it only holds what Claude couldn't work out from the code itself:

* How to confirm work in this repo: the exact test, typecheck, and lint commands, and how to run a single test file
* Places where the code is misleading: an old pattern that's everywhere but that new code must not copy, or a directory that looks unused but isn't
* Decisions that aren't in the repo: which error helper the team settled on, how deploys work, what needs a migration review
* Anything you've had to correct twice already

A `CLAUDE.md` that passes that test stays short:

```markdown CLAUDE.md theme={null}
# Commands
- Install: pnpm install
- Run one test file: pnpm vitest run path/to/file.test.ts
- Typecheck: pnpm tsc --noEmit

# Conventions
- Use the error helpers in src/lib/errors.ts, never throw raw strings
- src/legacy/ is still live but don't copy its patterns into new code

# Gotchas
- Integration tests need DATABASE_URL set, see .env.example
```

In a session, run [`/context all`](https://code.claude.com/docs/en/commands#all-commands) to confirm that Claude loaded the file.

Notice that the typecheck line is only the command. Claude needs to know the command so it can check its own work as it goes. If you also want Claude Code to *enforce* a passing typecheck before Claude finishes, that's a job for a [`Stop` hook](#enforce-the-check-with-a-stop-hook). A line like `Always typecheck before you finish` in this file works most of the time, not every time.

You don't have to write the file from scratch:

* `/init` generates a starting version from your codebase. From there the work is mostly removing lines. The [memory guide](https://code.claude.com/docs/en/memory.md#write-effective-instructions) recommends staying under 200.
* `/doctor` suggests cuts for anything Claude can [already work out from the code](https://code.claude.com/docs/en/memory.md#my-claude-md-is-too-large).
* `/doctor prompt-audit` flags instructions that were written for older models, point at files that no longer exist, or [contradict each other](https://code.claude.com/docs/en/memory.md#audit-your-instruction-files).

Your personal preferences go in `CLAUDE.local.md` instead of `CLAUDE.md`, and you add that file to `.gitignore` so it stays out of the repo.

> [!NOTE]
>
> If Claude keeps ignoring a line that *is* in `CLAUDE.md`, adding IMPORTANT probably won't fix it. Either the file has grown long enough that the line gets lost, or the line is a rule that can't have exceptions, in which case it belongs in a [hook](#enforce-the-rules-that-cant-have-exceptions).
