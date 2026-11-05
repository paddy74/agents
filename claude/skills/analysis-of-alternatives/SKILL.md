---
name: "analysis-of-alternatives"
description: Conduct and write an Analysis of Alternatives (AoA) or tool/product selection study using GAO/DoD AoA practice, ISO/IEC 25010 criteria, gated weighted scoring, sensitivity analysis and a standard Markdown template.
---

# Analysis of Alternatives (AoA)

Use this skill when the user asks for an analysis of alternatives, a trade study, a tool or vendor selection, a "which X should I use" comparison that needs a defensible method, or an update to an existing AoA after stakeholder answers.

The goal is a **defensible, reproducible, re-scorable** decision document. Every number in the document comes from a script, every judgment has a stated anchor, and every assumption the stakeholder has not confirmed is listed as an open question.

---

## 1. Standards to cite and follow

| Standard | Use it for |
|---|---|
| **GAO-16-22, AoA best practices** (22 practices; 4 characteristics: well-documented, comprehensive, unbiased, credible) | Process discipline; self-assessment table |
| **DoDI 5000.84 / DAF Office of Aerospace Studies (OAS) AoA Handbook** | Document structure: problem → alternatives → criteria and measures → cost → effectiveness → risk → sensitivity → recommendation |
| **ISO/IEC 25010 product quality model** | Criteria taxonomy (functional suitability, interaction capability/usability, compatibility, security, reliability, maintainability, flexibility/portability) |
| **Weighted-sum multi-criteria decision analysis with must-have gates** (Kepner-Tregoe "musts and wants") | Gates screen first; weighted scores rank only the survivors |
| **Total Cost of Ownership (TCO)** | Cost section: license + hosting + labor + migration |

Swap in a domain-specific standard when it fits better (e.g., NIST SP 800-53 for security controls, FAR Part 10 market research for acquisitions), but keep the GAO characteristics and the gated weighted-sum core.

---

## 2. Process

Track these phases in the task list. Do not skip the verification phase.

### Phase 0 — Frame
1. Restate the decision, scope, out-of-scope items and assumptions.
2. Define **use-case profiles** (e.g., individual, family, small enterprise, large enterprise, free, open source, self-hosted). One profile becomes **primary** once the stakeholder answers; until then, score all of them.
3. If the user will not be available, work autonomously: make the most reasonable assumption, record it in Assumptions, and add it to Open Questions.

### Phase 1 — Market survey and screening
1. Build a **long list** (typically 20–30 candidates) across the market's archetypes.
2. Apply explicit **screening criteria** (S1 actively maintained; S2 in category; S3 platform/market reach; S4 materially distinct). Record every screened-out candidate with its failed screen and a one-line rationale.
3. Produce a **shortlist** (typically 8–15) with archetype, license and publisher.

### Phase 2 — Requirements and features
1. List common category requirements (R1…Rn) with a category priority (Mandatory / Profile-dependent) and an ISO/IEC 25010 mapping.
2. Once the stakeholder answers, add a **stakeholder priority** column: MH (must-have → becomes a gate), H, D (desired), N (nice-to-have), — (not required).
3. Build a feature matrix: ✅ native · ◐ partial/paid/beta/plugin/workaround · ❌ absent. Explain every ◐ that matters in a note under the table.

### Phase 3 — Criteria, anchors, weights, gates
1. Define 10–15 criteria (C1…Cn), each with what is measured and its ISO/IEC 25010 characteristic.
2. Use the general 1–5 scale, plus a **criterion-specific anchor table** for any criterion tied to a stakeholder requirement (platforms, portability, cost vs. budget, optional AI, and so on). A score without an anchor is not defensible.
3. Set weights per profile; **each profile's weights sum to 100**. Fix weights before scoring and state the rationale.
4. Convert must-haves into **gates** (pass/fail) applied before scoring. Present a gate-screen table with one column per gate and a one-line reason for every failure.
5. Facets the stakeholder wants understood but not weighted (for example, ecosystem fit) are **scored at weight 0 and analyzed as a what-if**.
6. Facets the stakeholder wants recorded but not scored (for example, compliance certifications) go in a **register** with an explicit "recorded, not scored" note.

### Phase 4 — Research
1. Search for anything that describes the world as it is now: prices, plan limits, licenses, ownership, release status. Prefer vendor pages; use aggregators only as fallbacks and flag conflicts with `*`.
2. Delegate simple, parallel fact-gathering (fetching pricing pages, certification lookups, and per-candidate facts for Phase 1 screening) to **subagents on the cheapest capable model (Haiku-class)**, one candidate or fact set per subagent. Use a Sonnet-class subagent only when the source needs interpretation (ambiguous licensing terms, conflicting claims across sources). Give each a tight prompt: exact URLs or tools, the fields to extract, "write 'not found' rather than guess", a word limit, and source URLs.
3. **Spot-check personally** any subagent finding that decides a gate or flips a ranking.
4. Record the exact source URL for every fact that goes in the document.
5. Subagents return facts and source URLs only. Keep all judgment on the main thread: criteria and weights, gate interpretation, anchor-based scores, screening decisions, interpreting the sensitivity results, and the recommendation.

### Phase 5 — Score and analyze (scripted)
Keep all scoring in a Python script (template in Section 4) so the document can be regenerated after every stakeholder answer. The script must:
- assert every weight profile totals 100, every score is an integer from 1 to 5, and every gate references a valid alternative;
- compute weighted scores (Σ weight × score / 100) for gate survivors only;
- run the **sensitivity suite**:
  1. single-weight ±25% (renormalized) — count flips of the top pick;
  2. equal weights;
  3. Monte Carlo — 10,000 draws, each weight ×U(0.5, 1.5), renormalized; report the win percentage for each alternative;
  4. single-score ±1 on the top two alternatives;
  5. gate variants — relaxed and strict interpretations of any ambiguous must-have;
  6. what-if for zero-weight facets, including the weight at which the top pick changes;
- write Markdown tables (raw scores, weights, all-profile scores with ✗ for gate failures, primary ranking, score change log) that are pasted into the document.

### Phase 6 — Write
Use the output template in Section 3. Build the document from a **template with placeholders** (for example, `{{PRIMARY_TOP3}}` or `{{MARGIN}}`) filled from the script output, so prose numbers never drift from the model. Assert that no placeholder remains.

### Phase 7 — Verify (always)
1. **Arithmetic:** the script's asserts pass.
2. **Consistency:** every number in the prose is regenerated from the model; the recommendation matches the gate screen and rankings.
3. **Stale text:** after any revision, grep for wording from the prior version (the old winner's name next to "recommended", old version numbers, "strict/relaxed" wording, resolved questions) and fix it.
4. **Tables:** every table has a consistent column count (script check).
5. **Spelling and grammar:** run `codespell` (allow-list domain terms) and proofread.
6. Record all of this in the Verification Log table.

### Phase 8 — Iterate on stakeholder answers
1. Log each answer in "Answers received" with its **effect on the AoA**.
2. Update gates, anchors, scores and weights in the script; re-run; regenerate the document.
3. Add a row to the revision history and a **score change log** (tool, criterion, old, new, reason).
4. Bump the minor version (1.0 → 1.1 → 1.2). Keep prior versions as separate files.
5. Ask new questions only if they could change the recommendation; say explicitly when none block it.

---

## 3. Output template (Markdown)

```markdown
# Analysis of Alternatives (AoA): <Subject>

| Field | Value |
|---|---|
| Document | Analysis of Alternatives — <subject> |
| Version | <x.y> (<status note>) |
| Date | <DD Month YYYY> |
| Status | <Draft / Final; open questions?> |
| Prepared for | <stakeholder> |
| Governing use case | <primary profile, once known> |
| Market data as of | <month year> |

### Revision history
| Version | Date | Change |

## 1. Executive Summary
- Scope in one paragraph: alternatives, criteria, profiles, and the method's standards.
- Gate outcome: which alternatives fail, grouped by reason.
- **Recommendation** (bold, one sentence, including the configuration if relevant).
- Top-3 table: Rank | Alternative | Score | Why.
- "Why it wins" (bullets) and the key trade-off.
- Stability of the result: sensitivity headline, margin, and the one condition that would reverse it.
- Other use cases table: Use case | Recommended | Runner-up.
- Not recommended for new adoption (if any), with the reason.

## 2. Background, Scope, and Assumptions
2.1 Problem statement · 2.2 Scope · 2.3 Stakeholder-provided parameters (Parameter | Value | Treatment) · 2.4 Assumptions (numbered)

## 3. Methodology
3.1 Standards table · 3.2 Process steps · 3.3 Use-case profiles with gates · 3.4 GAO characteristic self-assessment (Characteristic | How addressed | Residual gap)

## 4. Market Survey and Alternative Identification
4.1 Long list · 4.2 Screening criteria · 4.3 Screened-out candidates (Candidate | Screen failed | Rationale) · 4.4 Shortlist (#, Alternative, Archetype, License, Publisher)

## 5. Common Requirements and Feature Baseline
5.1 Requirements (ID | Requirement | Category priority | Stakeholder priority | ISO/IEC 25010) · 5.2 Feature matrix (✅ ◐ ❌) with notes

## 6. Evaluation Criteria and Measures
6.1 Criteria definitions · 6.2 General 1–5 scale · 6.3 Criterion-specific anchors · 6.4 Weights by profile (each column totals 100) with rationale

## 7. Must-Have Gate Screen (primary profile)
One column per gate; Result column; notes on gate variants and corrections to earlier versions

## 8. Alternative Profiles
One paragraph per alternative: what it is, strengths, pricing/licensing essentials, *Weaknesses:*. Mark eligibility.

## 9. Cost Analysis
9.1 Verified list prices (flag conflicts with *) · 9.2 TCO scenarios for the primary profile vs. budget

## 10. Registers recorded but not scored (e.g., certifications/attestations)
State that vendor attestations do not transfer to self-hosted deployments, where relevant. "Not found" ≠ absent.

## 11. Portability and Migration Matrix (if relevant)
Native storage | Usable without the product? | Imports from | Exports to

## 12. Scoring Results
12.1 Raw scores · 12.2 Primary ranking · 12.3 All profiles (struck through + ✗ for gate failures)

## 13. Sensitivity and Risk Analysis
13.1 Primary sensitivity table · 13.2 Gate-variant ranking · 13.3 Other profiles (Top | Runner-up | Margin | Flips | Equal-weight top) · 13.4 Zero-weight what-if (crossover weights) · 13.5 Risk register (Risk | Affected | Likelihood | Impact | Mitigation)

## 14. Recommendation
14.1 Primary, with a numbered recommended configuration and cost · 14.2 Runner-up and when to choose it · 14.3 Other eligible options · 14.4 Watch list (what would change the answer, and when to re-evaluate)

## 15. Implementation and Migration Plan
Pilot (2–4 weeks, top 1–2 options) → test the gates in practice → test portability/exit → test recovery → adopt → operate

## 16. Open Questions
16.1 Answers received (ID | Question | Answer | Effect on the AoA) · 16.2 Remaining questions (ID | Question | Why it matters), or "None block the recommendation"

## 17. Limitations and Verification Log
17.1 Limitations (analyst judgment, volatility, unverified claims, execution notes such as subagent use) · 17.2 Verification cycle (Check | Method | Result)

## 18. Sources
Methodology references, then vendor/market sources with URLs, grouped by alternative, with access date.

## Appendix A. Scoring Rationale Highlights
## Appendix B. Score Changes (per version: Tool | Criterion | Old | New | Reason)
## Appendix C. Reproducing the Model
```

---

## 4. Scoring script template

```python
import json, random
tools = [...]                                   # shortlist
crit  = ["C1 ...", "C2 ...", ...]               # scored criteria
S = {"ToolA": [..], ...}                        # integer 1-5 per criterion
W = {"Primary": [..], "Baseline": [..], ...}    # each sums to 100
G = {"Primary": ["ToolX", ...], ...}            # tools FAILING each profile's gates
VARIANT_FAIL = [...]                            # relaxed or strict gate variant
SCENARIO = {"Scenario": {tool: score}}          # zero-weight what-if facet

for k, w in W.items(): assert sum(w) == 100 and len(w) == len(crit), k
for t, s in S.items(): assert len(s) == len(crit) and all(isinstance(x, int) and 1 <= x <= 5 for x in s), t
for k, g in G.items(): assert all(x in tools for x in g), k

sc   = lambda w, s: sum(a * b for a, b in zip(w, s)) / 100
rank = lambda w, fail: sorted([t for t in tools if t not in fail], key=lambda t: -sc(w, S[t]))
norm = lambda w: [x * 100 / sum(w) for x in w]

# 1) single-weight ±25%   2) equal weights   3) Monte Carlo 10,000 x U(0.5,1.5)
# 4) single-score ±1 on the top two   5) gate variant   6) scenario crossover weight
# -> write scores.md, weights.md, all.md, primary.md, changes.md and out.json
```

Fill the document from `out.json` and the `.md` tables with a small script that replaces `{{PLACEHOLDERS}}` and asserts that none remain.

---

## 5. Conventions and lessons learned

- **Interpretation of a must-have can decide the whole AoA.** If a gate is ambiguous (for example, "self-hosted" meaning vendor-supported vs. community-maintained, or production vs. beta), score both variants and make that the first open question.
- **Gates before weights.** Never let a high weighted score rescue an alternative that fails a must-have.
- **Separate "scored", "scenario-only" and "recorded" facets**, and say which is which.
- **Budget is a criterion, not a gate,** unless the stakeholder calls it a hard cutoff.
- **Re-anchor, don't just re-weight,** when the stakeholder's answers redefine what "good" means for a criterion (for example, portability meaning "editable without the product"). Log every resulting score change.
- **Be consistent across alternatives.** If one tool passes a gate via a workaround, the same workaround must count for the others; record the correction if an earlier version was inconsistent.
- **Disclose conflicts:** flag conflicting prices with `*`, mark vendor-reported claims as such, and treat "not found" as unknown rather than absent.
- **Close with a pilot.** A desk AoA is analyst judgment; recommend a short hands-on pilot that tests the gates in practice.
- **Style:** tables for comparisons, prose for rationale; bold only the recommendation and decisive facts; spell out acronyms on first use; U.S. list prices with the billing basis stated.
- **Deliverable:** a single Markdown file named `<Subject>_AoA_v<x.y>.md`, delivered with a short summary: the recommendation, the stability headline, what changed since the last version, and any questions that could still change the answer.
