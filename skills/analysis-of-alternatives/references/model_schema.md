# model.json: schema, modeling patterns and outputs

Read this before writing `model.json`. The engine (`scripts/aoa_engine.py`) validates everything below and stops with a list of problems if anything is off.

## Contents
1. Top-level fields
2. Criteria and the four treatments
3. Alternatives, scores and unknowns
4. Weights, gates and variants
5. Modeling patterns (tiers, deployments, stacks, cost, status quo, derived inputs)
6. What the engine writes (tables and placeholders)
7. Worked example

## 1. Top-level fields

| Field                             | Required | Meaning                                                                                                                                                |
| --------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `title`, `version`                | yes      | Shown in tables and placeholders                                                                                                                       |
| `criteria`                        | yes      | List of criteria (Section 2)                                                                                                                           |
| `alternatives`                    | yes      | List of alternatives (Section 3)                                                                                                                       |
| `scores`                          | yes      | Integer 1–5 or `"?"` per alternative per weighted and what-if criterion                                                                                |
| `weights`                         | yes      | `{profile: {criterion: weight}}`; every weighted criterion listed, each profile totals 100                                                             |
| `primary`                         | no       | Primary profile (default: the first)                                                                                                                   |
| `gates`                           | no       | `{profile: {alternative: "reason it fails"}}`: alternatives failing that profile's must-haves                                                          |
| `gate_variants`                   | no       | `{name: {"profile": p, "fail": {alternative: reason}}}`: alternative readings of ambiguous or unverified gates; `fail` replaces the profile's failures |
| `recorded`                        | no       | `{alternative: {criterion: value}}` for recorded (unweighted) criteria                                                                                 |
| `unknown_policy`                  | no       | `{"score": 2, "alternate": 3}`: what `"?"` scores, and the value used in the re-score test                                                             |
| `stability`                       | no       | `{"robust_mc": 0.90, "tie_mc": 0.70, "tie_margin": 0.05}`                                                                                              |
| `seed`, `mc_draws`, `weight_step` | no       | Defaults 1, 10000 and 0.25                                                                                                                             |
| `group_order`                     | no       | Display order of `group` values (for example, price tiers)                                                                                             |
| `change_reasons`                  | no       | Reasons for the change log (Section 4)                                                                                                                 |

## 2. Criteria and the four treatments

Every requirement the stakeholder cares about gets exactly one treatment:

| Treatment            | Where it lives                                     | Effect                                                                                        |
| -------------------- | -------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| **Gate** (must-have) | `gates` (and `gate_variants`)                      | Pass/fail before scoring; failures are never ranked                                           |
| **Weighted**         | criterion with `"treatment": "weighted"` (default) | Scored 1–5 and weighted in every profile                                                      |
| **What-if**          | `"treatment": "whatif"`                            | Scored 1–5 at weight 0; the engine reports the weight at which it would change the top pick   |
| **Recorded**         | `"treatment": "recorded"`                          | Collected for every alternative (yes/no, a number or text) and shown in a table, never scored |

```json
{"id": "C4", "name": "Portability of data", "iso25010": "Flexibility (portability)", "treatment": "weighted"}
{"id": "C11", "name": "Cost at expected usage", "treatment": "weighted", "cost": true}
{"id": "C12", "name": "Ecosystem fit", "treatment": "whatif"}
{"id": "R1", "name": "ARC/eARC audio return", "treatment": "recorded"}
```

`"cost": true` marks criteria that the cost-vs-effectiveness view removes when it computes effectiveness. A criterion can be both a gate (a minimum threshold) and weighted (the degree above the threshold). Say so in Section 6 when you do this.

## 3. Alternatives, scores and unknowns

```json
{"name": "Vendor X Pro", "group": "Below $1,000", "baseline": false, "tco": 1200, "tco_basis": "USD per year, 25 users"}
```

- `name` must be unique. Use the configuration name ("Vendor X Pro, managed"), not just the product.
- `group` (optional) gets a best-in-group table for the primary profile under its base gates and each variant.
- `baseline: true` marks the status quo.
- `tco` (number or null) feeds the cost-vs-effectiveness table.

Scores are a dict `{"C1": 4, "C2": "?"}` or a list in criteria order (weighted and what-if criteria only). `"?"` means *looked for and not found*. It scores `unknown_policy.score`, appears as `2?` in the score table, counts against evidence coverage, and is re-scored at `unknown_policy.alternate` in the sensitivity suite. Never use `"?"` for "I didn't look". Look, or screen the alternative out.

## 4. Weights, gates, variants and the change log

- Weights are numbers; each profile's weighted criteria total exactly 100. Use 0 for a weighted criterion a profile ignores. What-if and recorded criteria take no weights.
- `gates` lists only failures, with a one-line reason each. Profiles without gates can be omitted.
- Give an ambiguous must-have (vendor-supported vs community, production vs beta) a `gate_variants` entry, so both readings appear in Section 13.2.
- For "confirmed vs not found", put the strict reading (not found fails) in `gates`. Add a lenient `gate_variants` entry only for candidates whose silence may be a gap in the sources rather than absence of the feature.
- Run with `--previous old_model.json` to get `tables/changes.md`. Each row needs a reason in `change_reasons`, keyed as `score:<alt>:<crit>`, `weight:<profile>:<crit>`, `gate:<profile>:<alt>`, `alternative:<alt>`, `criterion:<crit>`, `profile:<profile>` or `unknown_policy`. Missing reasons show as `TODO: reason`, and `build_doc.py` fails until they are filled.

## 5. Modeling patterns

- **Tiers, deployments, stacks.** Make each adoptable configuration its own alternative when it changes a gate result or moves any score by a point or more (for example, "Vendor X Free" and "Vendor X Pro"; "Engine Y, managed" and "Engine Y, self-hosted"; "Photos app A + Timeline app B"). Otherwise score the best-fitting configuration and name it.
- **Cost treatments:**
  - weighted criterion: `"cost": true`, scored from the TCO by a stated band table;
  - hard cap: a gate;
  - recorded but not scored: a what-if criterion, or `tco` only;
  - price tiers that only group results: `group`, plus `group_order`.

  The cost-vs-effectiveness table is produced in every case.
- **Status quo.** Add the current tool with `baseline: true`. Put migration and retraining costs into the other alternatives' `tco`, and state them in Section 9.
- **Derived inputs.** When scores follow from numbers (geometry, usage-based cost, limits against expected usage), keep the numbers and the band table in a small `derive.py`. Have it write the resulting scores into `model.json`, and keep it with the deliverables. Then the anchor, the arithmetic and the score can't drift apart.
- **Several sub-categories.** Use one profile per sub-category with its own gates (gate out the alternatives that don't do that job), rather than ranking unlike tools against each other.

## 6. What the engine writes

`build/tables/`:
- `scores`, `weights`, `criteria`, `gates`;
- `ranking_<profile>` (ties shown as `1=`), `all_profiles` (gate failures struck through with ✗), `profiles_summary`;
- `sensitivity` (all seven tests plus the stability label), `montecarlo`, `variants`, `whatif`, `whatif_ladder`;
- `unknowns`, `coverage`, `cost_effectiveness`;
- `groups` (if any alternative has a group), `recorded` (if any recorded criteria), `changes` (with `--previous`).

`build/out.json` → `placeholders` (use as `{{KEY}}` in the template):
- `TITLE`, `VERSION`, `PRIMARY_PROFILE`, `TOP1`–`TOP3` and `TOP1_SCORE`–`TOP3_SCORE`, `MARGIN`, `STABILITY`, `TIED_TOP`;
- `MC_TOP_WIN_PCT`, `MC_RUNNER_WIN_PCT`, `MC_SUMMARY`, `WEIGHT_FLIPS`, `SCORE_FLIPS`, `EQUAL_WEIGHT_TOP`;
- `N_ALTERNATIVES`, `N_SURVIVORS`, `N_GATE_FAILURES`, `GATE_FAILURES`, `N_WEIGHTED_CRITERIA`, `N_WHATIF_CRITERIA`, `N_RECORDED_CRITERIA`, `N_PROFILES`;
- `UNKNOWN_POLICY`, `UNKNOWN_ALTERNATE`, `UNKNOWN_CELLS`, `UNKNOWN_TOP`, `SEED`, `MC_DRAWS`, `PREVIOUS_TOP`;
- per profile `PROFILE_<SLUG>_TOP`, `_RUNNER`, `_MARGIN`, `_STABILITY`;
- per variant `VARIANT_<SLUG>_TOP`;
- per what-if criterion `WHATIF_<ID>_CROSSOVER`, `WHATIF_<ID>_NEW_TOP`;
- per group `GROUP_<GATES>_<GROUP>_TOP`.

`<SLUG>` is the name upper-cased, with every run of non-alphanumeric characters replaced by `_`. `build_doc.py` also resolves `{{TABLE:name}}`, `{{SCORE:Profile:Alternative}}`, `{{MODEL_JSON}}` and `{{VERIFICATION_LOG}}`. Read `out.json` for anything else (full rankings, flip details, Monte Carlo shares) and quote it through a placeholder rather than retyping it.

## 7. Worked example (password manager for a 12-person team)

```json
{
  "title": "Team password manager", "version": "1.0", "seed": 20261103, "primary": "Small team",
  "unknown_policy": {"score": 2, "alternate": 3},
  "criteria": [
    {"id": "C1", "name": "Security architecture", "iso25010": "Security"},
    {"id": "C2", "name": "Ease of use", "iso25010": "Interaction capability"},
    {"id": "C3", "name": "Admin and sharing", "iso25010": "Functional suitability"},
    {"id": "C4", "name": "Cost for 12 users", "iso25010": "—", "cost": true},
    {"id": "C5", "name": "Fit with existing SSO", "treatment": "whatif"},
    {"id": "R1", "name": "Independent audit published", "treatment": "recorded"}
  ],
  "alternatives": [
    {"name": "Shared spreadsheet (status quo)", "baseline": true, "tco": 0, "tco_basis": "USD/yr"},
    {"name": "Vault A Teams", "tco": 576, "tco_basis": "USD/yr incl. migration"},
    {"name": "Vault B Business, self-hosted", "tco": 300, "tco_basis": "USD/yr incl. hosting"}
  ],
  "scores": {
    "Shared spreadsheet (status quo)": {"C1": 1, "C2": 3, "C3": 1, "C4": 5, "C5": 1},
    "Vault A Teams": {"C1": 5, "C2": 5, "C3": 4, "C4": 3, "C5": 4},
    "Vault B Business, self-hosted": {"C1": 4, "C2": 3, "C3": "?", "C4": 4, "C5": 2}
  },
  "recorded": {"Vault A Teams": {"R1": true}, "Vault B Business, self-hosted": {"R1": "2024 audit"}},
  "weights": {"Small team": {"C1": 35, "C2": 25, "C3": 20, "C4": 20},
              "Security-first": {"C1": 50, "C2": 15, "C3": 20, "C4": 15}},
  "gates": {"Small team": {"Shared spreadsheet (status quo)": "No encryption at rest (G1)"}},
  "gate_variants": {"Strict: audit published": {"fail": {"Shared spreadsheet (status quo)": "G1", "Vault B Business, self-hosted": "No current audit found"}}}
}
```

Run `python3 scripts/aoa_engine.py model.json --out build/`, then write the template using `{{TOP1}}`, `{{TABLE:ranking_small_team}}`, `{{TABLE:sensitivity}}` and so on.
