# cleanup-vault

Manual-only Claude Code skill (`disable-model-invocation`): Claude never runs it on its own. What it does is described in `SKILL.md`.

## Usage

Run from the vault root:

```
/cleanup-vault "HOA"
```

- The skill only edits inside the folder you name; other vault files are read-only.
- It copies the folder to `$TMPDIR/bak/<name>_orig` before changing anything.
- The vault is not a git repo, so nothing is committed. Check the backup if you need to roll back.

## Setup

- **Spell checker (recommended):** `sudo apt install aspell aspell-en` (or `hunspell hunspell-en-us`). It lets the skill list misspelled words instead of reading every note, which saves tokens. Without it, the skill falls back to a slower word-list script.
- `pandoc`, `bs4` and `markdownify` are optional.
