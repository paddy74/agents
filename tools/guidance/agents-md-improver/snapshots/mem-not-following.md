### Claude isn't following my CLAUDE.md

CLAUDE.md content is delivered as a user message after the system prompt, not as part of the system prompt itself. Claude reads it and tries to follow it, but there's no guarantee of strict compliance, especially for vague or conflicting instructions.

To debug:

* Run `/context` and check the list under **Memory files** to verify the CLAUDE.md and CLAUDE.local.md files that should load at launch. If one is missing there, Claude can't see it. Use `/memory` to open and edit the files.
* If an `Instruction file not loaded` notice appears, see [what it means and what to do about it](/docs/en/errors#instruction-file-not-loaded).
* A `CLAUDE.md` in a subdirectory of your working directory doesn't appear under **Memory files**, because it loads on demand rather than at launch. When it loads, a `Loaded` line with its path appears in the terminal. To test a new one, create it from your shell rather than asking Claude to write it, then ask Claude to read a file in that subdirectory.
* Check that the relevant CLAUDE.md is in a location that gets loaded for your session (see [Choose where to put CLAUDE.md files](#choose-where-to-put-claude-md-files)).
* Make instructions more specific. "Use 2-space indentation" works better than "format code nicely."
* Look for conflicting instructions across CLAUDE.md files. If two files give different guidance for the same behavior, Claude may pick one arbitrarily.
* Check whether your instruction competes with guidance Claude Code adds on its own. If your CLAUDE.md sets commit or pull request rules, turn off the built-in ones with [`includeGitInstructions`](/docs/en/settings-reference#includegitinstructions) and set the attribution text with [`attribution`](/docs/en/settings-reference#attribution).

If the instruction is something that must run at a specific point, such as before every commit or after each file edit, write it as a [hook](/docs/en/hooks-guide) instead. Hooks execute as shell commands at fixed lifecycle events and apply regardless of what Claude decides to do.

For instructions you want at the system prompt level, use [`--append-system-prompt`](/docs/en/cli-reference#system-prompt-flags). You pass it at launch, so it's better suited to scripts and automation than interactive use. For how it behaves when you resume a conversation, see [System prompt flags in resumed conversations](/docs/en/cli-reference#system-prompt-flags-in-resumed-conversations).

<Tip>
  Use the [`InstructionsLoaded` hook](/docs/en/hooks#instructionsloaded) to log which `CLAUDE.md` and rules files are loaded, when they load, and why. This is useful for debugging path-specific rules or lazy-loaded files in subdirectories.
</Tip>
