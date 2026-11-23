---
name: optimize-skill
description: Use this skill whenever the user asks to optimize, rewrite, improve, audit, or convert an AI prompt, system instruction, meta-prompt, or agent skill (SKILL.md). Also use this skill when converting a raw prompt into a monolithic or modular multi-tier agent skill (e.g., "Optimize as a Skill:").
---

# Prompt and Skill Optimizer

## Purpose
Analyze raw user prompts, system instructions, or agent skills (`SKILL.md`) and rewrite them to maximize clarity, determinism, token efficiency, and execution reliability.

## Execution Workflow

### Step 1: Load Calibration Examples
Before generating an optimized artifact, call `load_skill_resource` with `skill_name="optimize-skill"` and `file_path="references/examples.md"` to review the gold-standard patterns for `Mode A`, `Mode B1`, and `Mode B2`. If `load_skill_resource` returns an error, report the error to the user and stop immediately.

### Step 2: Classify Target Mode
Classify the user's input into one of three explicit modes:
- **Mode A (Standalone Prompt)**: Single-turn prompts, personas, or system instructions with no skill folder references.
- **Mode B1 (Monolithic Skill)**: Single-file skills where all instructions, triggers, and rules fit cleanly inside `SKILL.md` (strictly under 150 lines).
- **Mode B2 (Modular Multi-Tier Skill)**: Complex skills requiring prompt pipelines, deep rule sets, or lookup lists partitioned across a standard directory structure (`SKILL.md` + `references/`).

### Step 3: Apply Optimization Rules

#### Universal Rules (Apply to ALL Modes)
1. **Front-Load Critical Rules**: Place primary objectives, mandatory sequences, and hard boundaries at the top.
2. **Positive Framing**: Rewrite negative prohibitions ("Do not guess") into affirmative instructions ("Rely exclusively on explicitly provided data; if missing, output X").
3. **Chain-of-Thought & Verification Gate**: Break complex tasks into numbered reasoning steps ending with a self-verification check before rendering output.
4. **Deterministic Output Schema**: Define exact Markdown headings, tables, or JSON schemas.
5. **Zero-Chitchat Termination**: Enforce a strict stop after the final markdown table. Deliver the structured analysis and artifact only, omitting conversational wrap-ups.
6. **Heading Integrity**: Keep original section titles, document headings, and metadata titles structurally clean. NEVER append qualitative terms like `(Optimized)`, `(Revised)`, or `(New)` to headings or document titles.
7. **No Emojis Anywhere**: Do not insert emojis; remove any existing emojis.

#### Mode A Rules (Standalone Prompts Only)
1. **Authoritative Role Persona**: Define a domain-specific role and seniority level ("You are a Principal...").
2. **Inline Few-Shot Examples**: Include 2–3 concise input-output pairs directly inside the prompt, including at least 1 edge case (missing, malformed, or ambiguous input).

#### Mode B1 & Mode B2 Common Rules (Agent Skills)
1. **Trigger-Optimized YAML Frontmatter**: Start with `name` (kebab-case) and `description` ("Use this skill whenever the user asks to..."). Pack the description with explicit action verbs, synonyms, and domain triggers.
2. **Host-Safe Procedural Framing**: Write instructions as procedural workflows (`# Purpose`, `# Execution Workflow`) rather than assigning a conflicting persona ("You are a...") that overrides the host agent's identity.
3. **Immutable Resource & Tool Sequencing**: Preserve all exact file paths (`references/*`, `assets/*`, `scripts/*`) and tool names. State the exact step in which the agent must call `load_skill_resource` or other tools, including error-handling instructions if a load fails.
4. **150-Line Orchestration Ceiling**: Keep `SKILL.md` under 150 lines. If a skill requires deep rule sets or lookup lists that exceed 150 lines, classify and structure it as **Mode B2**.

#### Mode B2 Rules: Tripartite Resource Separation
For all **Mode B2** skills, enforce a strict separation between workflow, rules, and data:

| Component | Target Location | Content & Role |
|:---|:---|:---|
| **Orchestration** | `SKILL.md` | Keep under 150 lines. Handles triggers, workflow steps, guardrails, and loading resources. |
| **Logic & Rules** | `references/MASTER_*.md` | Structural rules, classification schemas, layout rules, and fallback policies. |
| **Lookup Registry** | `references/CANONICAL_*.md` | Pre-verified, copy-pasteable strings. The agent reads directly from this list instead of guessing or searching online. |

### Step 4: State Persistence and Packaging Protocol (Mode B1 & Mode B2)
To ensure sub-agents and external platforms do not lose files, drop session variables, or fail to load resources when optimizing a skill:
1. **Immediate File Writes**: Write all generated skill files to the workspace disk right away using clean relative paths. Do not hold long files in temporary conversational memory.
2. **Build a Standard Manifest (`manifest.json`)**: For **Mode B2** skills (or when packaging a multi-file skill), place a machine-readable bill of materials at the root of the skill folder listing each file path, file role, and architecture:
   ```json
   {
     "skill_name": "bibliograph-ref-maintainer",
     "version": "2.1.0",
     "architecture": "Mode-B2",
     "entry_point": "SKILL.md",
     "files": [
       {"path": "SKILL.md", "role": "orchestration"},
       {"path": "references/stage-prompts.md", "role": "prompt_pipeline"},
       {"path": "references/MASTER_CITATION_AND_REFERENCE.md", "role": "rules_engine"},
       {"path": "references/CANONICAL_REFERENCE_LIBRARY.md", "role": "lookup_registry"}
     ]
   }

3. Auto-Generate a Zip Package: Automatically create `<skill-name>-package.zip` holding the full folder structure for immediate, one-click download and deployment to other systems.

### Step 5: Final Validation Check
Verify before outputting that all escaped markdown artifacts (e.g., `\*\*`, `[^1^]`) are cleaned, all original constraints are preserved, and the output matches the 4-part schema below.

## Required Output Format
Always structure your response using these exact four sections:

### 1. Detected Mode & Diagnostic Summary

**State Mode A (Standalone Prompt)**, **Mode B1 (Monolithic Skill)**, or **Mode B2 (Modular Multi-Tier Skill)** and list 2–3 structural weaknesses identified in the original input.

### 2. Optimized Artifact

Provide the ready-to-use prompt or `SKILL.md` inside a fenced `markdown` code block. (If Mode B2 offloads content to `references/` and generates `manifest.json`, provide additional fenced code blocks labeled with each target file path and confirm `<skill-name>-package.zip` is ready).

### 3. Changes Made

| Optimization Pattern | Modification Applied |
| - | - |
| [Pattern Name] | [Specific improvement made to the input] |

### 4. Expected Performance Impact

| Metric | Expected Improvement |
| - | - |
| [e.g., Routing Accuracy / Determinism / Token Efficiency] | [Why this change improves model execution] |

### Strict Output Boundary

- Terminate the response immediately after Section 4 ("Expected Performance Impact").
- Do NOT append conversational sign-offs, closing pleasantries, or follow-up questions (e.g., do not ask "Would you like to test this?", "Is there any specific note you want to run?").
