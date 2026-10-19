# Refresh condensed guidance

The guidance check found changes to official docs that a skill condenses. Update the
condensed files to match. Don't run commands, commit or touch other files.

Inputs, given in the request:
- `result.json`: the check result. `changed` lists sections with `id`, `target` (a
  file in the references directory), `url` and `diff` (stored snapshot → live page).
  `missing` lists section ids whose heading wasn't found.
- The references directory and the manifest path.

Steps:
1. Group `changed` by `target`. For each group, read the target file once.
2. For each changed section, find the rules tagged with its `[section-id]`. Make the
   smallest edit that matches the new meaning. Paraphrase the docs, never copy them;
   keep one rule per line and keep every `[section-id]` tag. If a change adds
   guidance no rule covers, add one tagged rule under the closest heading.
3. Ignore changes that don't change meaning: version notes, link targets, wording
   with the same meaning, reordering. An empty `diff` is noise: make no edit.
4. For each `missing` id, fetch its source page (the manifest's `sources`), find the
   heading that now holds that content, and set the section's `heading` in the
   manifest. Change nothing else in the manifest. If no heading fits, leave it and
   say so in the summary.
5. Write `summary.md` in the working directory: one line per change, as
   `- <target> [<section-id>]: <what changed>`, or `- [<section-id>]: no edit (noise)`.
