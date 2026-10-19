# AGENTS.md

Ledgerly: a personal-finance CLI that imports bank CSV exports and prints monthly reports.

## Commands
- Install: `uv sync`
- Format: `uv run ruff format .`
- Lint: `uv run ruff check .`
- Type check: `uv run basedpyright`
- Test: `uv run pytest`

## Code style
- Type hints on every function; strict basedpyright must pass.
- Docstrings on public functions.

## Testing
- Add or update tests with every change.
- Plain pytest functions with fixtures; no unittest.TestCase.

## Git
- Default branch: `main`.
- Conventional Commits (`feat:`, `fix:`, `docs:`).
- Never force-push.
