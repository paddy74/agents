# Spec: shared repo tools

What the repo-wide tools in `tools/` must do. They serve every skill in this repo, and
no skill calls them. The files are the source of truth for exact wording.

## Contents

1. Layout and config
2. `shared/mdparse.py`
3. `bundle_shared.py`
4. `lint_skill.py`
5. Tests
6. Conventions

## 1. Layout and config

```text
tools/
├── shared/__init__.py, mdparse.py   # code shared by tools and skill scripts (§2)
├── bundle_shared.py                 # copies shared modules into skills (§3)
└── lint_skill.py, lint_rules.json   # skill linter (§4)
tests/
├── conftest.py                      # puts tools/ first on sys.path
├── shared/, bundle_shared/, lint_skill/
```

- `.gitignore` ignores `/skills/*/scripts/shared/` and
  `/claude/skills/*/scripts/shared/`.
- `pyproject.toml`: basedpyright excludes `**/scripts/shared`, and its
  `executionEnvironments` add `tools` as an extra path for `tests`, `claude/skills`
  and `skills`.
- README and AGENTS.md tell contributors to lint every changed skill and to put
  shared code in `tools/shared/`.

## 2. `shared/mdparse.py`

`fence_mask(lines) -> list[bool]` marks the lines of fenced code blocks, fence lines
included, following CommonMark:

- an opener matches `^\s*(`{3,}|~{3,})(.*)$`;
- a backtick opener whose info string contains a backtick isn't a fence;
- a fence closes on a line holding only the same character, at least as many times
  as the opener.

`__init__.py` is empty.

## 3. `bundle_shared.py`

`bundle_shared.py <skill-dir>... [--check]`

A skill ships only its own folder, so before install or packaging this tool copies
in the shared code:

- It finds each `shared.<module>` import in a skill's scripts with `ast`, and copies
  those modules plus `__init__.py` into the skill's gitignored `scripts/shared/`.
- It removes stale copies, and deletes the folder if it ends up empty.
- A missing module raises `FileNotFoundError`.
- `--check` exits 1 when a copy is missing, outdated or unneeded.
- Tests import from `tools/`, never a bundled copy.

## 4. `lint_skill.py`

`lint_skill.py <skill-dir> [--target portable|claude-code] [--json]`

- **Exit codes:** 0 with no errors (warnings are allowed), 1 with errors or bad
  input. Without PyYAML, it exits 1 with an install hint.
- **Frontmatter rules** match skill-creator's `quick_validate.py`, and are stricter
  where the Agent Skills spec is. A skill that passes the linter therefore passes
  packaging.
- **Parsing:** fences come from `fence_mask`, and `scripts/shared/` is skipped.
- **`lint_rules.json`** lists the allowed fields per target. Field lists are data,
  not code:
  - `portable`: `name`, `description`, `license`, `compatibility`, `metadata`,
    `allowed-tools`;
  - `claude-code` adds `when_to_use`, `argument-hint`, `arguments`,
    `disable-model-invocation`, `user-invocable`, `disallowed-tools`, `model`,
    `effort`, `context`, `agent`, `background`, `hooks`, `paths`, `shell`.

| Check | Severity | Rule |
| --- | --- | --- |
| Frontmatter | error | parses, is a mapping, and opens with `---` on line 1 |
| `name` | error | 1–64 chars, `^[a-z0-9-]+$`, no edge or double hyphen, no `anthropic`/`claude`, not `synced`/`anthropic-skills` |
| `name` = directory | error (portable), warning (claude-code) | |
| `name` style | warning | not a gerund; vague (`helper`, `utils`, `tools`, `documents`, `data`, `files`) |
| `description` | error | a string, 1–1,024 chars trimmed, no `<` or `>` |
| `compatibility` | error | if present, a string of 1–500 chars |
| `metadata` | error (portable), warning (claude-code) | if present, string → string |
| `description` + `when_to_use` | error (claude-code) | ≤ 1,536 chars together |
| `description` voice | warning | first or second person |
| `description` trigger | warning | no "use when"-style clause |
| Fields | warning | not in the target's list |
| Single SKILL.md | error | another SKILL.md outside `evals/`, `__pycache__` or `node_modules` |
| Body size | error > 500 lines; warning > 300 lines or > 5,000 tokens (chars ÷ 4) | |
| Top of body | warning | no workflow, steps or routing heading in the first 40 lines |
| Reference depth | error | a file linked from SKILL.md links to another reference |
| Long references | warning | > 100 lines with no contents list near the top |
| Broken links | error | a relative link or `${CLAUDE_SKILL_DIR}` path that doesn't exist |
| Windows paths | error | backslashes in links or code |
| Time-sensitive text | warning | dated phrases outside "Old patterns" |
| Emphasis | warning | more than 2 lines with `IMPORTANT`, `MUST` or `NEVER` |
| Scripts | warning | a file under `scripts/` that SKILL.md and the reference files never mention |

## 5. Tests

Every behaviour above has a test:

- `tests/shared/` covers fence opening and closing.
- `tests/bundle_shared/` covers import detection, copying only what's imported,
  stale and unneeded copies, and `--check`.
- `tests/lint_skill/` has one fixture per check, with its severity and exit code per
  target; a clean skill; bundled modules not flagged; and fences parsed by
  `fence_mask`.
- **Parity tests** check that the portable lint result agrees with `quick_validate.py`
  on its rules, and with `skills-ref validate` on the spec's rules. They're the only
  place `quick_validate.py` runs, and they're skipped unless `QUICK_VALIDATE_PATH`
  or `SKILLS_REF_BIN` is set (or `skills-ref` is on PATH). They must pass at least once against the real
  `quick_validate.py`.

## 6. Conventions

- `tools/shared/` uses the standard library only.
- PyYAML is a dev dependency, used by the linter and by tests that parse YAML.
- Never define a function both in `tools/shared/` and in a skill script.
- Fail fast with specific exceptions, and don't swallow errors.
