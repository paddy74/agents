# Agent config

[![License](https://img.shields.io/github/license/paddy74/agents)](LICENSE)

Skills, instructions and tool-specific configuration for the AI coding agents I use, kept in one place so the portable parts are written once and shared.

## What belongs here

Anything an agent loads directly: skills, instruction files and templates, subagents, hooks, commands, settings snippets and the small scripts that check them.

What doesn't belong here:

- **Standalone software** (MCP servers, CLIs, anything with its own dependencies and releases) lives in its own repository. Reference it from `docs/`.
- **Notes for people** (prompts, research, saved conversations, general templates) live in the notes repository. If only a person reads it, it doesn't go here.

## Layout

```text
.
├── skills/          # Agent Skills (open spec), portable across tools
├── instructions/    # AGENTS.md templates and shared rule snippets
├── claude/          # claude-only config
├── codex/           # codex-only config
├── gemini/          # gemini-only config
├── tools/           # shared scripts (linter, bundler, guidance checker)
├── tests/           # tests, one folder per skill or tool; never packaged
├── docs/            # specs, decisions and findings
└── .github/         # CI (guidance updates)
```

| Folder          | Contents                                                                                                                                                                |
| --------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `skills/`       | One folder per skill, each with a `SKILL.md`. Frontmatter uses only the portable fields: `name`, `description`, `license`, `compatibility`, `metadata`, `allowed-tools` |
| `instructions/` | Reusable AGENTS.md / CLAUDE.md templates and rule snippets                                                                                                              |
| `claude/`       | Config that only works in claude (agents, hooks, commands, settings snippets, plugin manifests)                                                                         |
| `codex/`        | Config that only works in codex (agents, hooks, commands, settings snippets, plugin manifests)                                                                          |
| `gemini/`       | Config that only works in gemini (agents, hooks, commands, settings snippets, plugin manifests)                                                                         |
| `tools/`        | Scripts shared across skills and tools                                                                                                                                  |
| `tests/`        | Tests, one folder per skill or tool (`tests/<name>/`)                                                                                                                   |
| `docs/`         | Specs (`docs/specs/`), decisions, overlap findings and acceptance records (`docs/<skill>/`), links to related repositories                                              |

**Where does a new thing go?** If it works in more than one tool, it goes in a shared folder (`skills/`, `instructions/`). If it only works in one tool, it goes in that tool's folder. When a tool-specific item becomes portable, move it up.

## Using the skills

**Claude Code (this machine):** link each skill into your personal skills folder. Edits in this repo take effect in the next session.

```bash
mkdir -p ~/.claude/skills
for skill in skills/*/; do
  ln -sfn "$PWD/$skill" ~/.claude/skills/"$(basename "$skill")"
done
```

Claude-only skills live in `claude/skills/`; link them the same way.

Skill scripts that import `shared.<module>` need the shared code bundled first; package after bundling too:

```bash
uv run python tools/bundle_shared.py skills/*/ claude/skills/*/
```

**Several machines:** add a `.claude-plugin/marketplace.json` at the repo root and install with `/plugin marketplace add <owner>/<repo>`.

**claude.ai and Cowork:** these don't read `~/.claude/skills/`. Package the skill folder and upload it to your claude.ai account; it then syncs to Cowork and cloud sessions. This repo stays the source of truth, so re-upload after changes.

**Other tools:** point any tool that reads Agent Skills at `skills/`.

## Development

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run ruff check . && uv run ruff format --check .
uv run basedpyright
uv run pytest
```

Lint every skill you change with `uv run python tools/lint_skill.py <skill-dir>`. Its parity tests run only when `QUICK_VALIDATE_PATH` (skill-creator's `quick_validate.py`) or `SKILLS_REF_BIN` is set, or `skills-ref` is on PATH.

Shared Python for skill scripts lives in `tools/shared/`. Skills import it as `shared.<module>`, and `tools/bundle_shared.py` copies it into each skill's gitignored `scripts/shared/`; `--check` reports stale copies.

### Official guidance updates

Skills that condense Anthropic's docs (currently `agents-md-improver`) are kept current by a weekly workflow: it opens a PR from `bot/guidance-refresh` when the docs change, and a `guidance-watch` issue when a built-in the skill relies on changes. How it works: [docs/specs/guidance-updates.md](docs/specs/guidance-updates.md). One-time setup:

1. Run `claude setup-token` and store the token as the repo secret `CLAUDE_CODE_OAUTH_TOKEN` (uses your Claude subscription, not an API key).
2. In Settings → Actions → General, enable "Allow GitHub Actions to create and approve pull requests".

To clear a `guidance-watch` issue after re-checking the overlap, run `uv run python tools/check_guidance.py --manifest <manifest> --accept-watch <ids>` and commit; the next run closes the issue.

Commits follow [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/). Work on branches; `main` only receives reviewed changes.

## License

Distributed under the [Apache License v2.0](https://www.apache.org/licenses/LICENSE-2.0). See [LICENSE](LICENSE) for details.

## Contact

Questions or issues? Please open an issue on the repository's issue tracker.
