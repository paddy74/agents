---
name: handoff
description: Use this skill whenever the user asks to save the session state, summarize a session, or create a downstream agent handoff block.
---

# Purpose
Synthesize active conversation history into an immediate task-oriented session handoff, an authoritative structural reference document, or a combined state sync with zero context loss.

# Execution Workflow

1. **Load Formatting & Diagram Standards**:
   - Call `load_skill_resource` with `skill_name="create-session-handoff"` and `file_path="references/templates.md"` to load the required output schemas and Mermaid syntax guardrails.
   - If `load_skill_resource` returns an error, report the error to the user and stop immediately.

2. **Analyze Context & Resolve Overrides**:
   - Scan the entire conversation history chronologically.
   - Identify and discard any initial instructions, rules, constraints, or schemas that were subsequently modified, corrected, or replaced by the user.
   - Extract only the current, authoritative state of decisions, active artifacts, and confirmed facts.

3. **Select Output Mode**:
   - **Type A (Session Handoff)**: Select when the user wants to transition to another agent, pause the workspace, or generate a continuation prompt.
   - **Type B (Reference & Relationship Summary)**: Select when the user wants to map system entities, document architecture, or visualize relationships via Mermaid.
   - **Combined Sync**: If the user request is general (e.g., "save state" or "sync context"), render Type B followed immediately by Type A.

4. **Draft the Artifact**:
   - Follow the exact section headers and table structures defined in `references/templates.md`.
   - Rely exclusively on explicitly established conversation facts; place any missing or unconfirmed details under "Open Questions / Uncertainties."
   - Enclose all code snippets, drafts, or schemas inside fenced code blocks and escape special Markdown characters (`\|`, `\*`, `\_`) inside table cells.

5. **Self-Verification Gate**:
   - Confirm that zero superseded or discarded instructions from earlier turns appear in the output.
   - Verify that any Mermaid diagram obeys the syntax rules in `references/templates.md` and matches the prose summary exactly.
   - Confirm that the Type A continuation prompt is a single, self-contained sentence.

# Edge-Case Handling
- **Empty or Minimal History**: If no substantive project context exists in the thread, output ONLY:
  `[STATUS: EMPTY_SESSION] Please share details, rules, or requirements about your project to initialize state.`
- **Unresolved Contradictions**: If two active constraints conflict and cannot be resolved chronologically, flag the conflict explicitly under `PENDING BLOCKERS` (Type A) or `System Gaps & Uncertainties` (Type B).

# Output Format
Render the final response strictly following the **Type A**, **Type B**, or **Combined** schema loaded from `references/templates.md`.
