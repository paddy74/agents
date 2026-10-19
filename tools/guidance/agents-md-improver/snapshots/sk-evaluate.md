## Evaluate and iterate on a skill

Seeing a skill trigger tells you Claude found it, not that it did what you intended. To know a skill is working, measure separately whether Claude invokes it on the prompts it should, and whether the output matches what you expect when it does.

The check for both is a baseline comparison. Collect a few realistic prompts, run each one in a fresh session with the skill available and again with it turned off, and compare the results. A fresh session matters because leftover context from authoring the skill will mask gaps in the written instructions.

How you turn the skill off for the second run depends on where it comes from:

* **Personal or project skill**: set it to `"off"` in [`skillOverrides`](#override-skill-visibility-from-settings).
* **Skill that a plugin provides**: `skillOverrides` doesn't apply to plugin skills. Use [`claude plugin eval`](/docs/en/plugin-evals#the-no-plugin-baseline) instead, which repeats each run with no plugin loaded.

Two tools automate the baseline comparison. For a skill that ships in a [plugin](/docs/en/plugins/overview), [`claude plugin eval`](/docs/en/plugin-evals) runs each prompt in an isolated session with and without the plugin, scores it with graders you define or that it writes for you, and exits non-zero below a threshold so you can gate CI on it. For iterating on a single skill inside a Claude Code conversation, the skill-creator plugin below runs a similar loop with its own `evals/evals.json` format. The two formats aren't interchangeable.

### Run evals with skill-creator

The [`skill-creator` plugin](https://github.com/anthropics/claude-plugins-official/tree/main/plugins/skill-creator) automates the comparison loop inside Claude Code. In the VS Code extension or the desktop app, install it from the official marketplace by following [Install a plugin](/docs/en/plugins/install#install-a-plugin). In a terminal, start Claude Code by running `claude`, then enter this at its prompt:

```text theme={null}
/plugin install skill-creator@claude-plugins-official
```

If the install fails, match the message Claude Code reports:

* `Marketplace "claude-plugins-official" not found`: add the marketplace with `/plugin marketplace add anthropics/claude-plugins-official`, then retry the install.
* `Plugin "<name>" not found in marketplace "claude-plugins-official"`: your local copy of the marketplace catalog may be out of date. Refresh it with `/plugin marketplace update claude-plugins-official`, then retry the install. If the retry prints the same message, see [Plugin not found in marketplace](/docs/en/plugins/troubleshooting#plugin-not-found-in-marketplace).

If the install summary reports `Run /reload-plugins to apply.`, Claude Code then runs that reload for you. If the reload warns that your next message would re-read the conversation, run `/reload-plugins --force` to make the plugin's skills available in the current session. Then ask Claude to evaluate an existing skill, for example `evaluate my summarize-changes skill with skill-creator`. The plugin walks you through writing test cases and runs the loop:

* **Test cases**: stores prompts, input files, and expected behavior in `evals/evals.json` inside the skill directory
* **Isolated runs**: spawns a [subagent](/docs/en/sub-agents) per test case so each run starts with a clean context, and records token count and duration
* **Grading**: checks each assertion against the output and writes pass or fail with evidence to `grading.json`
* **Benchmark**: aggregates pass rate, time, and tokens for with-skill versus without-skill into `benchmark.json` so you can compare the pass-rate improvement against the token and time overhead
* **Version comparison**: runs a blind A/B between two versions of the skill so you can confirm an edit is an improvement before committing it
* **Description tuning**: generates should-trigger and should-not-trigger prompts, measures the hit rate, and proposes description edits when the skill activates on the wrong requests
* **Review viewer**: opens an HTML report where you inspect each output and record qualitative feedback that the next iteration reads

For the eval file format and the full iteration workflow, see [Evaluating skill output quality](https://agentskills.io/skill-creation/evaluating-skills) on agentskills.io. For background on the benchmark and comparison modes, see the [skill-creator announcement](https://claude.com/blog/improving-skill-creator-test-measure-and-refine-agent-skills).
