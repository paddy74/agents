# AGENTS.md

Personal agent configuration repo: skills, instruction files and tool-specific config that agents load directly. See README.md for the full layout and install steps.

## Where things go

- `skills/<name>/`: one Agent Skill per folder; the folder name equals the `name` field.
- `instructions/`: AGENTS.md / CLAUDE.md templates and rule snippets.
- `claude/`: config that only works in claude.
- `codex/`: config that only works in codex.
- `gemini/`: config that only works in gemini.
- `tools/`: shared scripts. `tests/<name>/`: tests for the matching skill or tool.
- `docs/`: decisions and references. Never put standalone software (MCP servers, CLIs)
  or notes meant only for people in this repo.
- Portable (works in more than one tool) → shared folder; single tool → that tool's folder.

## Skills

- Frontmatter: only `name`, `description`, `license`, `compatibility`, `metadata`,
  `allowed-tools`. Claude Code-only fields go in a copy under `claude/`, not `skills/`.
- `name`: lowercase letters, digits, single hyphens, ≤64 chars, no "claude" or "anthropic".
- `description`: third person, what it does and when to use it, ≤1,024 chars, no `<` or `>`.
- SKILL.md body under 500 lines; reference files linked directly from SKILL.md, one level deep.
- Keep tests and dev files out of skill folders; everything in a skill folder ships.
- Run `uv run python tools/lint_skill.py <skill-dir>` on every skill you change and fix all errors.
- Shared Python for skill scripts goes in `tools/shared/`, imported as `shared.<module>`; never copy it into a skill by hand. `uv run python tools/bundle_shared.py <skill-dir>` bundles it.

## Commands

- Install: `uv sync`
- Lint and format: `uv run ruff check .` and `uv run ruff format .`
- Type check: `uv run basedpyright`
- Test: `uv run pytest`

## Code

- Python 3.12+, 88-char lines, full type annotations (strict basedpyright), reST docstrings on every class and function.
- Standard library first; ask before adding a dependency.
- Add or update tests with every change.

## Git

- Conventional Commits, short and imperative. One logical change per commit.
- Never commit to `main`. Never push.
- Never commit secrets; use environment variables or a gitignored `.env`.
