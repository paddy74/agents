---
name: cleanup-vault
description: Converts OneNote-style HTML exports to Obsidian Markdown, then cleans up, consolidates and reorganizes a folder of notes (frontmatter, wikilinks, merges, folder hierarchy) without changing any facts. Use when asked to convert .html notes, tidy or refactor a vault folder, merge tiny notes, or resolve Proton Drive sync conflicts.
disable-model-invocation: true
---

# Obsidian Vault Cleanup

Work recursively only in the folder the user named. Facts never change; structure, spelling, grammar, formatting, frontmatter and links do.

## Workflow

1. Check what is really in the folder (there may be no `.html`), then back it up.
2. Convert HTML (section 1), if any.
3. Clean up notes (2), add frontmatter and links (3).
4. Consolidate (4) and reorganize (5) when it helps.
5. Resolve sync conflicts (6), verify and report (7).

Run the link check after every stage.

## Ground rules

- **Scope:** modify only the named folder and its subfolders. Other vault files are read-only.
  - Find inbound links with one `grep -rIl --include=*.md -F` on wikilink forms (`[[Name`, `[[Folder/Name`), not bare names. Use `-l` only; don't `ls` other folders.
  - Report outside notes that link in and ask before editing them.
- **Data integrity:** keep every phone number, name, address, date, amount, URL, passcode and quote verbatim. Never anonymize, redact or invent. Garbled or ambiguous text stays as written and is listed for the user.
- **Ask before informational changes:** a corrected name, number, date or uncertain wording needs the user's OK. Cosmetic fixes (section 2) go ahead. List every judgment call at the end.
- **Backups:** copy the folder to `$TMPDIR/bak/<name>_orig` before changing anything, and again before each later restructure. The vault is not a git repo. Do the backup, folder listing and resources-folder check in one command.
- **Plan first** when asked (`/plan`).
- **Sandbox:** write temp files and scripts to `$TMPDIR`, not the vault. Use absolute paths (`cd` can persist between calls).
- **Before overwriting or deleting:** check the target. Never convert into a path that already holds a note.

## 1. Convert HTML to Markdown

- pandoc, bs4 and markdownify may be missing; write a stdlib `html.parser` converter in `$TMPDIR`.
- OneNote exports use `div.title` / `div.outline-element` / `p` / `span` / `ul` `ol` `li` / `h1` `h2` / `a` / `img` / `br`. Bold and italic are inline `style` on `<p>` and `<span>`, so handle both.
- Keep the original `---` frontmatter. Move the title/date header into properties. Collapse doubled link URLs, superscript spacing (`9 th` to `9th`) and tracking parameters.
- Convert images to `![[file]]` embeds when the file is in the vault.
- Verify by script: word-by-word text comparison of each `.html` against its `.md`, then bold/italic/list/link/image counts. Re-run until only expected differences remain.
- Then delete the `.html` originals and empty converted notes, and say how many of each.

## 2. Clean up each note

- **Triage first.** Profile each note without printing it: size, lines, frontmatter keys, counts of `&nbsp;`, tabs, bare URLs, `[[TOC]]`, `$`, `<`, long lines, reference-style links. Then split:
  - **Mechanical** (formatting only): fix with a `$TMPDIR` script (frontmatter, tabs, TOC, bare URLs, listed typos). Review by diff against the backup, not by re-reading.
  - **Manual** (garbled outline, unclear structure, merges): read only these, in full only if rewriting by hand. For notes over ~4 KB read headings and the first ~20 lines, then more where needed.
- Pasted chat or web text (reference-style links, `utm_` URLs, sign-off) stays verbatim apart from frontmatter and whitespace. Don't print it in full.
- Remove `&nbsp;`, duplicate title lines, date/time stamp headers (move to `date`), stray HTML tags and manual tables of contents.
- Normalize bullets (`•`, `○`, `▪`, `§` to nested `-`), turn letter/roman outlines (`a.` `i.`) into nested lists, tighten loose lists, add headings, tables for attribute data, callouts (`> [!note]`) for annotations, and `[^1]` footnotes.
- **Fix without asking** (report only a count, plus any that change a word's meaning or touch a name):
  - Misspelled common words, including inside quotations (`Boarder Czar` → `Border Czar`).
  - Unambiguous misspellings of well-known proper nouns and brands (`Robinhold` → `Robinhood`).
  - Wrong word forms with one clear fix: agreement, `a`/`an`, doubled words, inflection, missing letters, hyphenated modifiers, apostrophes.
  - Mojibake (`ÅŒkami` → `Ōkami`).
- **Still ask (leave as written and list):** invented names or spellings that vary between notes, anything changing a number, date or fact, truncated or fragmentary text, unclear intended words.
- **Spell-check:** use `aspell list` or `hunspell -l` to print only unknown words with line numbers; else a stdlib script against `/usr/share/dict/words`. It misses wrong real words (`date` for `data`).
- **Obsidian gotchas:**
  - Escape bare `$` as `\$` (two on a line trigger LaTeX).
  - Escape or backtick `<placeholder>` text, which renders as a hidden tag.
  - Clean URL artifacts (`%EF%BF%BC`, trailing `\\`) and broken link targets; wrap bare links as `<url>`.
  - In scripts, `'' in 'abc'` is True: guard empty lines.

## 3. Frontmatter and links

- Properties: `type`, `date` (ISO, with time if known), `tags` (nested, e.g. `hoa/meeting`), `created` / `updated` (keep original values), quoted wikilink properties (`previous: "[[Note]]"`, `next`, `course`, `show`).
- Use aliases and heading links (`[[Note#Heading|alias]]`). Link people, places and related notes. Add a hub/index note per folder linking everything, and previous/next links for dated series.
- Link check script: every `[[link]]`, `[[a/b|alias]]` and `![[embed]]` must resolve.

## 4. Consolidate

- Merge very short or empty related notes (per-class notes into one per course, sub-notes into parent, stubs into a related note). Keep long notes separate. Delete empty notes.
- Redirect links to merged notes and say which properties were dropped.
- Remove only exact duplicate lines or blocks, and say so.

## 5. Reorganize folders

- Group by topic (Governance, Management, Property, IT, Meeting Notes, ...), date undated filenames, remove folders left with one file, update the hub, re-run the link check.
- The filesystem (drvfs / Proton Drive) is case-insensitive: renaming a folder by case needs a temporary name, and writing to `improv 501` may land in `Improv 501`.

## 6. Sync conflicts

- Proton Drive creates `Name (# Edit conflict ... #).md`. Diff against the real note, merge anything new, delete the stale copy.
- Sync or the user may move or delete files mid-session. Re-check the folder against the backup before copying results in; stop if anything differs.

## 7. Verify and report

- Stage rewrites in `$TMPDIR`, then check that every word, number and URL from the backup appears in the cleaned files. Review leftovers (stamps, ToC, duplicate links, fixed typos). Compare file and folder listings before and after.
- **Final report: short, only what the user must act on or could be surprised by,** in this order:
  1. One line: notes before → after, and the backup path.
  2. Structural changes: files merged, renamed, moved or deleted (one line each), new folders and index.
  3. **Please confirm:** numbered open judgment calls (exact text, note, question). The most important section.
  4. One closing line: Obsidian rendering was not checked, plus any tool or step that limited the work.
- Omit routine formatting, clean word-check results, "nothing found" notes, and the list of obvious spelling fixes (give a count). Mention a check only if it found a problem.
