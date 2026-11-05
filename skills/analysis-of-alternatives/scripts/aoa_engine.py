#!/usr/bin/env python3
"""AoA scoring engine: gated weighted scoring, sensitivity suite and Markdown tables.

Usage:
    python3 aoa_engine.py model.json --out build/ [--previous old_model.json]

Reads one model.json (schema: references/model_schema.md), validates it, scores
the gate survivors under every weight profile, runs the sensitivity suite, and
writes:
    build/out.json      every computed number, plus ready-made placeholder values
    build/model.json    a copy of the input (embed it in Appendix C)
    build/tables/*.md   Markdown tables to paste or fill into the document
Exits with status 1 and a list of problems if the model is invalid.
Standard library only.
"""

import argparse
import json
import os
import random
import re
import shutil
import sys

ENGINE_VERSION = "1.0"
EPS = 1e-9
TREATMENTS = ("weighted", "whatif", "recorded")


# ----------------------------------------------------------------- helpers
def slug(text):
    return re.sub(r"[^A-Z0-9]+", "_", str(text).upper()).strip("_")


def f2(x):
    return f"{x:.2f}"


def pct(x):
    return f"{100 * x:.1f}%"


def md_table(header, rows):
    out = [
        "| " + " | ".join(str(h) for h in header) + " |",
        "|" + "|".join(["---"] * len(header)) + "|",
    ]
    for r in rows:
        assert len(r) == len(header), (header, r)
        out.append(
            "| "
            + " | ".join(str(c).replace("|", "\\|").replace("\n", " ") for c in r)
            + " |"
        )
    return "\n".join(out) + "\n"


def norm(w):
    tot = sum(w.values())
    return {c: v * 100.0 / tot for c, v in w.items()} if tot > 0 else dict(w)


def wscore(w, s):
    return sum(w[c] * s[c] for c in w) / 100.0


def fmt_value(v):
    if v is True:
        return "Yes"
    if v is False:
        return "No"
    if v is None or v == "":
        return "—"
    return str(v)


# ----------------------------------------------------------------- loading
def load_model(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def validate(m):
    """Return (normalized model, list of errors)."""
    err = []
    crits = m.get("criteria") or []
    alts = m.get("alternatives") or []
    if not crits:
        err.append("criteria: empty")
    if not alts:
        err.append("alternatives: empty")
    cids = [c.get("id") for c in crits]
    if len(set(cids)) != len(cids) or None in cids:
        err.append("criteria: every criterion needs a unique 'id'")
    for c in crits:
        c.setdefault("treatment", "weighted")
        c.setdefault("name", c.get("id"))
        if c["treatment"] not in TREATMENTS:
            err.append(
                f"criterion {c.get('id')}: treatment must be one of {TREATMENTS}"
            )
        if c.get("cost") and c["treatment"] == "recorded":
            err.append(
                f"criterion {c['id']}: a cost criterion must be weighted or whatif"
            )
    names = [a.get("name") for a in alts]
    if len(set(names)) != len(names) or None in names:
        err.append("alternatives: every alternative needs a unique 'name'")
    weighted = [c["id"] for c in crits if c.get("treatment") == "weighted"]
    whatif = [c["id"] for c in crits if c.get("treatment") == "whatif"]
    recorded = [c["id"] for c in crits if c.get("treatment") == "recorded"]
    scored = [c["id"] for c in crits if c.get("treatment") in ("weighted", "whatif")]
    if not weighted:
        err.append("criteria: at least one criterion must be 'weighted'")

    # scores: dict per alternative, or a list aligned with the scored criteria
    scores = m.get("scores") or {}
    norm_scores = {}
    for a in names:
        s = scores.get(a)
        if s is None:
            err.append(f"scores: missing alternative '{a}'")
            continue
        if isinstance(s, list):
            if len(s) != len(scored):
                err.append(
                    f"scores['{a}']: list has {len(s)} values; expected {len(scored)} ({', '.join(scored)})"
                )
                continue
            s = dict(zip(scored, s, strict=False))
        row = {}
        for c in scored:
            v = s.get(c)
            if v == "?" or (
                isinstance(v, int) and not isinstance(v, bool) and 1 <= v <= 5
            ):
                row[c] = v
            else:
                err.append(
                    f"scores['{a}']['{c}'] = {v!r}: must be an integer 1-5 or \"?\""
                )
        extra = set(s) - set(scored)
        if extra:
            err.append(f"scores['{a}']: unknown or non-scored criteria {sorted(extra)}")
        norm_scores[a] = row
    for a in set(scores) - set(names):
        err.append(f"scores: '{a}' is not a listed alternative")

    weights = m.get("weights") or {}
    if not weights:
        err.append("weights: at least one profile is required")
    for p, w in weights.items():
        missing = [c for c in weighted if c not in w]
        if missing:
            err.append(
                f"weights['{p}']: missing weighted criteria {missing} (use 0 if unweighted in this profile)"
            )
        bad = [c for c in w if c not in weighted]
        if bad:
            err.append(
                f"weights['{p}']: {bad} are not weighted criteria (what-if and recorded criteria take no weight)"
            )
        if any((not isinstance(v, (int, float))) or v < 0 for v in w.values()):
            err.append(f"weights['{p}']: weights must be non-negative numbers")
        elif not missing and abs(sum(w[c] for c in weighted) - 100) > 1e-6:
            err.append(
                f"weights['{p}']: total is {sum(w[c] for c in weighted):g}, must be 100"
            )
    primary = m.get("primary") or (next(iter(weights)) if weights else None)
    if primary not in weights:
        err.append(f"primary: '{primary}' is not a weight profile")

    gates = m.get("gates") or {}
    for p, fails in gates.items():
        if p not in weights:
            err.append(f"gates: profile '{p}' has no weights")
        for a in fails:
            if a not in names:
                err.append(f"gates['{p}']: '{a}' is not a listed alternative")
    variants = m.get("gate_variants") or {}
    for v, spec in variants.items():
        p = spec.get("profile", primary)
        if p not in weights:
            err.append(f"gate_variants['{v}']: profile '{p}' has no weights")
        for a in spec.get("fail", {}):
            if a not in names:
                err.append(f"gate_variants['{v}']: '{a}' is not a listed alternative")

    rec = m.get("recorded") or {}
    for a, vals in rec.items():
        if a not in names:
            err.append(f"recorded: '{a}' is not a listed alternative")
        for c in vals:
            if c not in recorded:
                err.append(f"recorded['{a}']: '{c}' is not a recorded criterion")

    up = m.get("unknown_policy") or {}
    up = {"score": up.get("score", 2), "alternate": up.get("alternate", 3)}
    for k, v in up.items():
        if not (isinstance(v, int) and 1 <= v <= 5):
            err.append(f"unknown_policy.{k}: must be an integer 1-5")

    st = {"robust_mc": 0.90, "tie_mc": 0.70, "tie_margin": 0.05}
    st.update(m.get("stability") or {})

    for a in alts:
        t = a.get("tco")
        if t is not None and not isinstance(t, (int, float)):
            err.append(f"alternative '{a['name']}': tco must be a number or null")

    nm = {
        "title": m.get("title", "Analysis of Alternatives"),
        "version": str(m.get("version", "1.0")),
        "seed": int(m.get("seed", 1)),
        "mc_draws": int(m.get("mc_draws", 10000)),
        "weight_step": float(m.get("weight_step", 0.25)),
        "primary": primary,
        "criteria": crits,
        "crit": {c["id"]: c for c in crits},
        "weighted": weighted,
        "whatif": whatif,
        "recorded_ids": recorded,
        "scored": scored,
        "alternatives": alts,
        "names": names,
        "alt": {a["name"]: a for a in alts},
        "scores": norm_scores,
        "weights": {
            p: {c: float(w.get(c, 0)) for c in weighted} for p, w in weights.items()
        },
        "gates": {p: dict(gates.get(p, {})) for p in weights},
        "variants": variants,
        "recorded": rec,
        "unknown_policy": up,
        "stability": st,
        "group_order": m.get("group_order"),
        "change_reasons": m.get("change_reasons") or {},
    }
    return nm, err


# ----------------------------------------------------------------- analysis
class Model:
    def __init__(self, nm):
        self.m = nm
        up = nm["unknown_policy"]
        self.S = {
            a: {c: (up["score"] if v == "?" else v) for c, v in s.items()}
            for a, s in nm["scores"].items()
        }
        self.S_alt = {
            a: {c: (up["alternate"] if v == "?" else v) for c, v in s.items()}
            for a, s in nm["scores"].items()
        }
        self.unknown_cells = [
            (a, c) for a, s in nm["scores"].items() for c, v in s.items() if v == "?"
        ]

    def ranking(self, w, survivors, S=None):
        S = S or self.S
        scored = [(a, wscore(w, S[a])) for a in survivors]
        order = {a: i for i, a in enumerate(self.m["names"])}
        return sorted(scored, key=lambda t: (-round(t[1], 9), order[t[0]]))

    @staticmethod
    def top_set(rk):
        if not rk:
            return set()
        best = rk[0][1]
        return {a for a, s in rk if abs(s - best) < EPS}

    def survivors(self, fail, restrict=None):
        return [
            a
            for a in self.m["names"]
            if a not in fail and (restrict is None or a in restrict)
        ]

    def analyze(self, profile, fail, restrict=None, pm1=True, S=None, seed_offset=0):
        m = self.m
        S = S or self.S
        w = m["weights"][profile]
        surv = self.survivors(fail, restrict)
        rk = self.ranking(w, surv, S)
        res = {
            "profile": profile,
            "survivors": surv,
            "ranking": [[a, round(s, 4)] for a, s in rk],
        }
        if not rk:
            res.update(top=None, label="no survivors")
            return res
        tops = self.top_set(rk)
        base_top = rk[0][0]
        res["top"] = base_top
        res["tied_top"] = sorted(tops, key=m["names"].index) if len(tops) > 1 else []
        if len(rk) < 2:
            res.update(runner=None, margin=None, label="only survivor")
            return res
        res["runner"] = rk[1][0]
        res["margin"] = round(rk[0][1] - rk[1][1], 4)

        # 1) single-weight +/- step, renormalized
        step = m["weight_step"]
        trials, flips = 0, []
        for c in m["weighted"]:
            if w[c] <= 0:
                continue
            for f in (1 - step, 1 + step):
                w2 = dict(w)
                w2[c] *= f
                t = self.top_set(self.ranking(norm(w2), surv, S))
                trials += 1
                if t != {base_top}:
                    flips.append(
                        {
                            "criterion": c,
                            "factor": f,
                            "new_top": sorted(t, key=m["names"].index),
                            "kind": "tie" if base_top in t else "flip",
                        }
                    )
        res["weight_trials"], res["weight_flips"] = trials, flips

        # 2) equal weights
        weq = {c: 100.0 / len(m["weighted"]) for c in m["weighted"]}
        erk = self.ranking(weq, surv, S)
        res["equal_ranking"] = [[a, round(s, 4)] for a, s in erk]
        res["equal_top"] = sorted(self.top_set(erk), key=m["names"].index)

        # 3) Monte Carlo: each weight x U(0.5, 1.5), renormalized; tied winners split the credit
        rng = random.Random(m["seed"] + seed_offset)
        crits = list(m["weighted"])
        base = [w[c] for c in crits]
        mat = [[S[a][c] for c in crits] for a in surv]
        wins = [0.0] * len(surv)
        for _ in range(m["mc_draws"]):
            ww = [b * rng.uniform(0.5, 1.5) for b in base]
            vals = [sum(x * y for x, y in zip(ww, row, strict=False)) for row in mat]
            best = max(vals)
            tol = abs(best) * 1e-12 + EPS
            win = [i for i, v in enumerate(vals) if best - v <= tol]
            for i in win:
                wins[i] += 1.0 / len(win)
        mc = {a: wins[i] / m["mc_draws"] for i, a in enumerate(surv)}
        res["mc_win"] = {
            a: round(v, 4) for a, v in sorted(mc.items(), key=lambda t: -t[1])
        }
        share = mc[base_top]

        # 4) single-score +/-1 on the top two (only moves that stay inside 1-5 are trials)
        if pm1:
            ptr, pfl = 0, []
            for who in [a for a, _ in rk[:2]]:
                for c in m["weighted"]:
                    if w[c] <= 0:
                        continue
                    for d in (-1, 1):
                        v = S[who][c] + d
                        if not 1 <= v <= 5:
                            continue
                        S2 = dict(S)
                        S2[who] = dict(S[who])
                        S2[who][c] = v
                        t = self.top_set(self.ranking(w, surv, S2))
                        ptr += 1
                        if t != {base_top}:
                            pfl.append(
                                {
                                    "alternative": who,
                                    "criterion": c,
                                    "delta": d,
                                    "new_top": sorted(t, key=m["names"].index),
                                    "kind": "tie" if base_top in t else "flip",
                                }
                            )
            res["score_trials"], res["score_flips"] = ptr, pfl

        # stability label
        st = m["stability"]
        n_pm1 = len(res.get("score_flips", []))
        if res["tied_top"] or res["margin"] < st["tie_margin"] or share < st["tie_mc"]:
            label = "practical tie"
        elif share >= st["robust_mc"] and n_pm1 == 0 and not flips:
            label = "robust"
        else:
            label = "leaning"
        res["label"] = label
        return res


def crossover(base, fvals, top):
    """Smallest weight x (%) on a zero-weight facet at which another alternative overtakes `top`.
    Scores are linear in x: S_a(x) = (1 - x/100) * base_a + (x/100) * f_a."""
    best_x, who = None, None
    for a in base:
        if a == top:
            continue
        db = base[top] - base[a]
        df = fvals[a] - fvals[top]
        if df <= 0:
            continue
        x = 100.0 * db / (db + df) if db > 0 else 0.0
        if x <= 100 and (best_x is None or x < best_x - EPS):
            best_x, who = x, a
    return best_x, who


# ----------------------------------------------------------------- change log
def change_log(prev, cur, reasons):
    rows = []

    def reason(key):
        return reasons.get(key, "TODO: reason")

    pn, cn = prev["names"], cur["names"]
    for a in cn:
        if a not in pn:
            rows.append(
                ["Alternative added", a, "—", "scored", reason(f"alternative:{a}")]
            )
    for a in pn:
        if a not in cn:
            rows.append(
                ["Alternative removed", a, "scored", "—", reason(f"alternative:{a}")]
            )
    for c in cur["crit"]:
        if c not in prev["crit"]:
            rows.append(
                [
                    "Criterion added",
                    c,
                    "—",
                    cur["crit"][c]["treatment"],
                    reason(f"criterion:{c}"),
                ]
            )
        elif prev["crit"][c]["treatment"] != cur["crit"][c]["treatment"]:
            rows.append(
                [
                    "Criterion treatment",
                    c,
                    prev["crit"][c]["treatment"],
                    cur["crit"][c]["treatment"],
                    reason(f"criterion:{c}"),
                ]
            )
    for c in prev["crit"]:
        if c not in cur["crit"]:
            rows.append(
                [
                    "Criterion removed",
                    c,
                    prev["crit"][c]["treatment"],
                    "—",
                    reason(f"criterion:{c}"),
                ]
            )
    for a in cn:
        if a not in pn:
            continue
        for c in cur["scored"]:
            if c in prev["scores"].get(a, {}):
                o, n = prev["scores"][a][c], cur["scores"][a][c]
                if o != n:
                    rows.append([f"Score: {a}", c, o, n, reason(f"score:{a}:{c}")])
    for p, w in cur["weights"].items():
        if p not in prev["weights"]:
            rows.append(
                ["Weight profile added", p, "—", "added", reason(f"profile:{p}")]
            )
            continue
        for c, v in w.items():
            o = prev["weights"][p].get(c)
            if o is not None and abs(o - v) > 1e-9:
                rows.append(
                    [f"Weight: {p}", c, f"{o:g}", f"{v:g}", reason(f"weight:{p}:{c}")]
                )
    for p in prev["weights"]:
        if p not in cur["weights"]:
            rows.append(
                ["Weight profile removed", p, "present", "—", reason(f"profile:{p}")]
            )
    for p in cur["gates"]:
        o = prev["gates"].get(p, {})
        n = cur["gates"][p]
        for a in cn:
            if a in n and a not in o:
                rows.append(
                    [f"Gate: {p}", a, "pass", f"fail ({n[a]})", reason(f"gate:{p}:{a}")]
                )
            elif a in o and a not in n and a in pn:
                rows.append(
                    [f"Gate: {p}", a, f"fail ({o[a]})", "pass", reason(f"gate:{p}:{a}")]
                )
    if prev["unknown_policy"] != cur["unknown_policy"]:
        rows.append(
            [
                "Unknown-evidence policy",
                "—",
                json.dumps(prev["unknown_policy"]),
                json.dumps(cur["unknown_policy"]),
                reason("unknown_policy"),
            ]
        )
    return rows


# ----------------------------------------------------------------- main
def run(model_path, out_dir, previous=None):
    raw = load_model(model_path)
    nm, errors = validate(raw)
    if errors:
        print("MODEL INVALID:", file=sys.stderr)
        for e in errors:
            print("  - " + e, file=sys.stderr)
        sys.exit(1)
    M = Model(nm)
    m = nm
    P = m["primary"]
    names = m["names"]
    tdir = os.path.join(out_dir, "tables")
    os.makedirs(tdir, exist_ok=True)
    tables, out, ph, warnings = {}, {}, {}, []
    all_scores = {a: set() for a in names}

    def remember(a, s):
        all_scores[a].add(round(s, 2))

    crit_label = {c["id"]: f"{c['id']} {c['name']}" for c in m["criteria"]}

    # raw scores (scored criteria); '?' shows the policy value with a marker
    rows = []
    for a in names:
        rows.append(
            [a]
            + [
                f"{M.S[a][c]}?" if m["scores"][a][c] == "?" else M.S[a][c]
                for c in m["scored"]
            ]
        )
    hdr = ["Alternative"] + [
        c + (" (what-if)" if m["crit"][c]["treatment"] == "whatif" else "")
        for c in m["scored"]
    ]
    tables["scores"] = md_table(hdr, rows) + (
        f"\n`?` = looked for and not found; scored {m['unknown_policy']['score']} under the stated unknown-evidence policy.\n"
        if M.unknown_cells
        else ""
    )

    # weights
    rows = [
        [crit_label[c]] + [f"{m['weights'][p][c]:g}" for p in m["weights"]]
        for c in m["weighted"]
    ]
    rows.append(
        ["**Total**"] + [f"**{sum(m['weights'][p].values()):g}**" for p in m["weights"]]
    )
    tables["weights"] = md_table(["Criterion"] + list(m["weights"]), rows)

    # criteria with treatment
    rows = [
        [
            c["id"],
            c["name"],
            c.get("iso25010", "—"),
            {
                "weighted": "Weighted",
                "whatif": "What-if (weight 0)",
                "recorded": "Recorded, not scored",
            }[c["treatment"]],
        ]
        for c in m["criteria"]
    ]
    tables["criteria"] = md_table(
        ["ID", "Criterion", "ISO/IEC 25010", "Treatment"], rows
    )

    # gates
    rows = []
    for a in names:
        rows.append(
            [a]
            + [
                ("Fail: " + m["gates"][p][a]) if a in m["gates"][p] else "Pass"
                for p in m["weights"]
            ]
        )
    tables["gates"] = md_table(
        ["Alternative"] + [f"{p} gates" for p in m["weights"]], rows
    )

    # per-profile analysis
    out["profiles"] = {}
    scores_by_profile = {}
    for i, p in enumerate(m["weights"]):
        res = M.analyze(p, m["gates"][p], pm1=(p == P), seed_offset=i)
        out["profiles"][p] = res
        scores_by_profile[p] = {
            a: round(wscore(m["weights"][p], M.S[a]), 4) for a in names
        }
        for a, s in scores_by_profile[p].items():
            remember(a, s)
        for a, s in res.get("equal_ranking", []):
            remember(a, s)
        rk = res["ranking"]
        rrows, prev_s, prev_rank = [], None, 0
        for k, (a, s) in enumerate(rk, 1):
            if prev_s is not None and abs(s - prev_s) < EPS:
                rank = f"{prev_rank}="
            else:
                prev_rank, rank = k, str(k)
            prev_s = s
            rrows.append([rank, a, f2(s)])
        # mark ties on the first row too
        for k in range(len(rrows) - 1):
            if rrows[k + 1][0].endswith("=") and not rrows[k][0].endswith("="):
                rrows[k][0] += "="
        tables[f"ranking_{slug(p).lower()}"] = md_table(
            ["Rank", "Alternative", "Weighted score (of 5)"], rrows
        )
    out["scores_by_profile"] = scores_by_profile

    rows = []
    for a in names:
        rows.append(
            [a]
            + [
                (
                    f"~~{f2(scores_by_profile[p][a])}~~ ✗"
                    if a in m["gates"][p]
                    else f2(scores_by_profile[p][a])
                )
                for p in m["weights"]
            ]
        )
    tables["all_profiles"] = md_table(["Alternative"] + list(m["weights"]), rows)

    # profile summary
    rows = []
    for p, r in out["profiles"].items():
        if r.get("top") is None:
            rows.append([p, "none", "—", "—", "—", "—", "—", "no survivors"])
            continue
        if r.get("runner") is None:
            rows.append([p, r["top"], "—", "—", "—", "—", "—", "only survivor"])
            continue
        top = " = ".join(r["tied_top"]) if r["tied_top"] else r["top"]
        rows.append(
            [
                p,
                top,
                r["runner"],
                f2(r["margin"]),
                f"{len(r['weight_flips'])} of {r['weight_trials']}",
                ", ".join(r["equal_top"]),
                pct(r["mc_win"][r["top"]]),
                r["label"],
            ]
        )
    tables["profiles_summary"] = md_table(
        [
            "Profile",
            "Top",
            "Runner-up",
            "Margin",
            f"Single-weight ±{int(m['weight_step'] * 100)}% flips",
            "Equal-weight top",
            "Monte Carlo win (top)",
            "Stability",
        ],
        rows,
    )

    pr = out["profiles"][P]
    if pr.get("runner") is None:
        warnings.append(
            f"Primary profile '{P}' has {len(pr['survivors'])} survivor(s); sensitivity tests need two."
        )

    # Monte Carlo table (primary)
    if pr.get("mc_win"):
        tables["montecarlo"] = md_table(
            ["Alternative", f"Monte Carlo win share ({m['mc_draws']:,} draws)"],
            [[a, pct(v)] for a, v in pr["mc_win"].items()],
        )

    # gate variants
    out["variants"] = {}
    rows = []
    for i, (v, spec) in enumerate(m["variants"].items()):
        p = spec.get("profile", P)
        fail = spec.get("fail", {})
        res = M.analyze(p, fail, pm1=False, seed_offset=100 + i)
        out["variants"][v] = res
        for a, s in res["ranking"]:
            remember(a, s)
        excl = "; ".join(f"{a} ({r})" for a, r in fail.items()) or "none"
        rk = (
            "; ".join(
                f"{k}. {a} ({f2(s)})" for k, (a, s) in enumerate(res["ranking"][:5], 1)
            )
            or "no survivors"
        )
        rows.append([v, p, excl, rk])
    if rows:
        tables["variants"] = md_table(
            ["Gate variant", "Weights", "Excluded", "Ranking of survivors (top 5)"],
            rows,
        )

    # what-if criteria (zero-weight facets) on the primary profile
    out["whatif"] = {}
    surv = pr["survivors"]
    if m["whatif"] and pr.get("top"):
        base = {a: wscore(m["weights"][P], M.S[a]) for a in surv}
        rows, ladder = [], []
        for f in m["whatif"]:
            fv = {a: M.S[a][f] for a in surv}
            x, who = crossover(base, fv, pr["top"])
            out["whatif"][f] = {
                "crossover_pct": None if x is None else round(x, 1),
                "new_top": who,
            }
            rows.append(
                [
                    crit_label[f],
                    "none up to 100%" if x is None else f"{x:.1f}%",
                    who or "—",
                ]
            )
            ph[f"WHATIF_{slug(f)}_CROSSOVER"] = (
                "none up to 100%" if x is None else f"{x:.1f}%"
            )
            ph[f"WHATIF_{slug(f)}_NEW_TOP"] = who or "none"
            for xs in (10, 20, 30, 40, 50):
                sc = sorted(
                    ((a, (1 - xs / 100) * base[a] + xs / 100 * fv[a]) for a in surv),
                    key=lambda t: -t[1],
                )
                ladder.append(
                    [
                        crit_label[f],
                        f"{xs}%",
                        "; ".join(f"{a} ({f2(s)})" for a, s in sc[:3]),
                    ]
                )
        tables["whatif"] = md_table(
            [
                "What-if criterion (weight 0)",
                f"Weight at which the {P} top pick changes",
                "New top",
            ],
            rows,
        )
        tables["whatif_ladder"] = md_table(
            [
                "What-if criterion",
                "Weight given",
                "Top three (other weights scaled down)",
            ],
            ladder,
        )

    # unknown evidence: coverage and alternate-policy re-score
    rows = []
    for c in m["scored"]:
        unk_all = [a for a in names if m["scores"][a][c] == "?"]
        unk_surv = [a for a in surv if m["scores"][a][c] == "?"]
        wt = m["weights"][P].get(c, 0)
        rows.append(
            [
                crit_label[c],
                f"{wt:g}",
                f"{len(surv) - len(unk_surv)} of {len(surv)}",
                ", ".join(unk_all) or "—",
            ]
        )
        if surv and wt >= 10 and len(unk_surv) / len(surv) >= 0.5:
            warnings.append(
                f"{c} carries {wt:g}% of the {P} weight but {len(unk_surv)} of {len(surv)} survivors are unknown on it; "
                "the ranking may reflect evidence availability more than quality."
            )
    tables["coverage"] = md_table(
        ["Criterion", f"{P} weight", "Survivors with evidence", "Unknown (`?`) for"],
        rows,
    )
    alt_res = {}
    for i, p in enumerate(m["weights"]):
        alt_res[p] = M.analyze(
            p, m["gates"][p], pm1=False, S=M.S_alt, seed_offset=200 + i
        )
        for a, s in alt_res[p]["ranking"]:
            remember(a, s)
    out["unknown_alternate"] = {
        p: {"top": r.get("top"), "ranking": r["ranking"]} for p, r in alt_res.items()
    }
    rows = []
    for p in m["weights"]:
        b, a2 = out["profiles"][p].get("top"), alt_res[p].get("top")
        rows.append([p, b or "—", a2 or "—", "no" if b == a2 else "**yes**"])
    tables["unknowns"] = md_table(
        [
            "Profile",
            f"Top with unknowns = {m['unknown_policy']['score']}",
            f"Top with unknowns = {m['unknown_policy']['alternate']}",
            "Changes?",
        ],
        rows,
    )

    # primary sensitivity table
    if pr.get("runner"):
        wf = pr["weight_flips"]
        sf = pr["score_flips"]
        wdet = (
            "; ".join(
                f"{x['criterion']} ×{x['factor']:g} → {' = '.join(x['new_top'])}"
                for x in wf
            )
            or f"top pick stays {pr['top']}"
        )
        sdet = (
            "; ".join(
                f"{x['alternative']} {x['criterion']} {x['delta']:+d} → {' = '.join(x['new_top'])}"
                for x in sf
            )
            or f"top pick stays {pr['top']}"
        )
        rows = [
            [
                f"Single weight ±{int(m['weight_step'] * 100)}% (renormalized)",
                f"{len(wf)} of {pr['weight_trials']} change the top",
                wdet,
            ],
            [
                "Equal weights",
                "top: " + ", ".join(pr["equal_top"]),
                "; ".join(f"{a} {f2(s)}" for a, s in pr["equal_ranking"][:5]),
            ],
            [
                f"Monte Carlo ({m['mc_draws']:,} draws, each weight × U(0.5, 1.5))",
                f"{pr['top']} wins {pct(pr['mc_win'][pr['top']])}",
                "; ".join(f"{a} {pct(v)}" for a, v in pr["mc_win"].items() if v > 0),
            ],
            [
                f"Single score ±1 on {pr['top']} and {pr['runner']}",
                f"{len(sf)} of {pr['score_trials']} change the top",
                sdet,
            ],
        ]
        for v, r in out["variants"].items():
            if r.get("profile") == P:
                rows.append(
                    [
                        f"Gate variant: {v}",
                        f"top: {r.get('top') or 'none'}",
                        "; ".join(f"{a} {f2(s)}" for a, s in r["ranking"][:3]),
                    ]
                )
        for f, d in out["whatif"].items():
            rows.append(
                [
                    f"What-if: {crit_label[f]}",
                    "crossover "
                    + (
                        "none up to 100%"
                        if d["crossover_pct"] is None
                        else f"{d['crossover_pct']}%"
                    ),
                    d["new_top"] or "—",
                ]
            )
        if M.unknown_cells:
            a2 = alt_res[P]
            rows.append(
                [
                    f"Unknowns re-scored at {m['unknown_policy']['alternate']}",
                    f"top: {a2.get('top')}",
                    "; ".join(f"{a} {f2(s)}" for a, s in a2["ranking"][:3]),
                ]
            )
        rows.append(
            [
                "Stability label",
                f"**{pr['label']}**",
                f"margin {f2(pr['margin'])}; robust = Monte Carlo ≥ {pct(m['stability']['robust_mc'])} and no single change flips it; "
                f"practical tie = Monte Carlo < {pct(m['stability']['tie_mc'])} or margin < {m['stability']['tie_margin']:.2f}",
            ]
        )
        tables["sensitivity"] = md_table(["Test", "Result", "Detail"], rows)
        if pr["label"] == "practical tie":
            warnings.append(
                f"Primary result is a practical tie ({pr['top']} vs {pr['runner']}): report co-finalists and let the pilot decide."
            )

    # cost vs effectiveness (primary)
    cost_ids = [c for c in m["weighted"] if m["crit"][c].get("cost")]
    weff = {c: v for c, v in m["weights"][P].items() if c not in cost_ids}
    weff = norm(weff) if sum(weff.values()) > 0 else weff
    ce = []
    baselines = [a for a in names if m["alt"][a].get("baseline") and a not in surv]
    for a in surv + baselines:
        eff = wscore(weff, M.S[a]) if weff else 0
        remember(a, eff)
        ce.append(
            {
                "alternative": a,
                "effectiveness": round(eff, 4),
                "weighted": round(wscore(m["weights"][P], M.S[a]), 4),
                "tco": m["alt"][a].get("tco"),
                "tco_basis": m["alt"][a].get("tco_basis", ""),
                "gated": a in baselines,
            }
        )
    for r in ce:
        if r["gated"]:
            r["status"] = (
                f"Status-quo baseline; fails gates ({m['gates'][P][r['alternative']]})"
            )
            continue
        if r["tco"] is None:
            r["status"] = "TCO not given"
            continue
        dom = [
            o["alternative"]
            for o in ce
            if o is not r
            and o["tco"] is not None
            and not o["gated"]
            and o["effectiveness"] >= r["effectiveness"] - EPS
            and o["tco"] <= r["tco"] + EPS
            and (
                o["effectiveness"] > r["effectiveness"] + EPS
                or o["tco"] < r["tco"] - EPS
            )
        ]
        r["status"] = (
            ("Dominated by " + ", ".join(dom)) if dom else "Efficient (not dominated)"
        )
    ce.sort(key=lambda r: -r["effectiveness"])
    out["cost_effectiveness"] = {"cost_criteria": cost_ids, "rows": ce}
    tables["cost_effectiveness"] = md_table(
        [
            "Alternative",
            "Effectiveness (cost criteria removed)"
            if cost_ids
            else "Effectiveness (no cost criterion scored)",
            "Weighted score (all criteria)",
            "TCO",
            "Basis",
            "Cost-effectiveness",
        ],
        [
            [
                r["alternative"]
                + (" (baseline)" if m["alt"][r["alternative"]].get("baseline") else ""),
                f2(r["effectiveness"]),
                f2(r["weighted"]),
                "—" if r["tco"] is None else f"{r['tco']:,.2f}".rstrip("0").rstrip("."),
                r["tco_basis"] or "—",
                r["status"],
            ]
            for r in ce
        ],
    )

    # groups (for example price tiers): per-group ranking under primary gates and each primary-profile variant
    groups = [a.get("group") for a in m["alternatives"] if a.get("group") is not None]
    if groups:
        order = m["group_order"] or list(dict.fromkeys(groups))
        settings = [("Base gates", m["gates"][P])] + [
            (v, s.get("fail", {}))
            for v, s in m["variants"].items()
            if s.get("profile", P) == P
        ]
        out["groups"] = {}
        rows = []
        for gi, (sname, fail) in enumerate(settings):
            out["groups"][sname] = {}
            for gj, g in enumerate(order):
                members = {a["name"] for a in m["alternatives"] if a.get("group") == g}
                res = M.analyze(
                    P, fail, restrict=members, pm1=True, seed_offset=300 + 10 * gi + gj
                )
                out["groups"][sname][g] = res
                if res.get("top") is None:
                    rows.append([sname, g, "none", "—", "—", "—", "—", "no survivors"])
                elif res.get("runner") is None:
                    rows.append(
                        [
                            sname,
                            g,
                            f"{res['top']} ({f2(res['ranking'][0][1])})",
                            "—",
                            "—",
                            "—",
                            "—",
                            "only survivor",
                        ]
                    )
                else:
                    top = " = ".join(res["tied_top"]) if res["tied_top"] else res["top"]
                    rows.append(
                        [
                            sname,
                            g,
                            f"{top} ({f2(res['ranking'][0][1])})",
                            f"{res['runner']} ({f2(res['ranking'][1][1])})",
                            f2(res["margin"]),
                            pct(res["mc_win"][res["top"]]),
                            f"{len(res['weight_flips'])}/{res['weight_trials']} w; {len(res['score_flips'])}/{res['score_trials']} s",
                            res["label"],
                        ]
                    )
                ph[f"GROUP_{slug(sname)}_{slug(g)}_TOP"] = res.get("top") or "none"
        tables["groups"] = md_table(
            [
                "Gates",
                "Group",
                "Top (score)",
                "Runner-up (score)",
                "Margin",
                "Monte Carlo win (top)",
                "Flips (weight; score ±1)",
                "Stability",
            ],
            rows,
        )

    # recorded (unweighted) criteria
    if m["recorded_ids"]:
        rows = [
            [a]
            + [fmt_value(m["recorded"].get(a, {}).get(c)) for c in m["recorded_ids"]]
            for a in names
        ]
        tables["recorded"] = md_table(
            ["Alternative"] + [crit_label[c] for c in m["recorded_ids"]], rows
        )

    # change log
    if previous:
        pnm, perr = validate(load_model(previous))
        if perr:
            warnings.append(
                "previous model has validation problems; change log may be incomplete: "
                + "; ".join(perr[:3])
            )
        rows = change_log(pnm, nm, m["change_reasons"])
        out["changes"] = rows
        tables["changes"] = md_table(
            ["Item", "Criterion / alternative", "Old", "New", "Reason"],
            rows or [["No changes", "—", "—", "—", "—"]],
        )
        if any(r[4].startswith("TODO") for r in rows):
            warnings.append(
                "Change log has rows without a reason; add them to change_reasons in model.json."
            )
        try:
            prev_top = (
                M.__class__(pnm)
                .analyze(pnm["primary"], pnm["gates"][pnm["primary"]], pm1=False)
                .get("top")
            )
        except Exception:  # previous model may differ structurally
            prev_top = None
        out["previous_top"] = prev_top
        ph["PREVIOUS_TOP"] = prev_top or "—"

    # placeholders
    rk = pr["ranking"]
    ph.update(
        {
            "TITLE": m["title"],
            "VERSION": m["version"],
            "PRIMARY_PROFILE": P,
            "SEED": str(m["seed"]),
            "MC_DRAWS": f"{m['mc_draws']:,}",
            "N_ALTERNATIVES": str(len(names)),
            "N_PROFILES": str(len(m["weights"])),
            "N_WEIGHTED_CRITERIA": str(len(m["weighted"])),
            "N_WHATIF_CRITERIA": str(len(m["whatif"])),
            "N_RECORDED_CRITERIA": str(len(m["recorded_ids"])),
            "N_SURVIVORS": str(len(surv)),
            "N_GATE_FAILURES": str(len(m["gates"][P])),
            "GATE_FAILURES": "; ".join(f"{a} ({r})" for a, r in m["gates"][P].items())
            or "none",
            "UNKNOWN_POLICY": str(m["unknown_policy"]["score"]),
            "UNKNOWN_ALTERNATE": str(m["unknown_policy"]["alternate"]),
            "UNKNOWN_CELLS": str(len(M.unknown_cells)),
            "UNKNOWN_TOP": alt_res[P].get("top") or "none",
        }
    )
    for k in range(3):
        ph[f"TOP{k + 1}"] = rk[k][0] if len(rk) > k else "—"
        ph[f"TOP{k + 1}_SCORE"] = f2(rk[k][1]) if len(rk) > k else "—"
    if pr.get("runner"):
        ph.update(
            {
                "MARGIN": f2(pr["margin"]),
                "STABILITY": pr["label"],
                "MC_TOP_WIN_PCT": pct(pr["mc_win"][pr["top"]]),
                "MC_RUNNER_WIN_PCT": pct(pr["mc_win"].get(pr["runner"], 0)),
                "MC_SUMMARY": "; ".join(
                    f"{a} {pct(v)}" for a, v in pr["mc_win"].items() if v > 0
                ),
                "WEIGHT_FLIPS": f"{len(pr['weight_flips'])} of {pr['weight_trials']}",
                "SCORE_FLIPS": f"{len(pr['score_flips'])} of {pr['score_trials']}",
                "EQUAL_WEIGHT_TOP": ", ".join(pr["equal_top"]),
                "TIED_TOP": " = ".join(pr["tied_top"]) if pr["tied_top"] else "none",
            }
        )
    for p, r in out["profiles"].items():
        s = slug(p)
        ph[f"PROFILE_{s}_TOP"] = r.get("top") or "none"
        ph[f"PROFILE_{s}_RUNNER"] = r.get("runner") or "—"
        ph[f"PROFILE_{s}_MARGIN"] = (
            f2(r["margin"]) if r.get("margin") is not None else "—"
        )
        ph[f"PROFILE_{s}_STABILITY"] = r.get("label", "—")
    for v, r in out["variants"].items():
        ph[f"VARIANT_{slug(v)}_TOP"] = r.get("top") or "none"

    out.update(
        {
            "engine_version": ENGINE_VERSION,
            "title": m["title"],
            "version": m["version"],
            "primary": P,
            "seed": m["seed"],
            "mc_draws": m["mc_draws"],
            "asserts_passed": True,
            "alternatives": names,
            "unknown_cells": [list(x) for x in M.unknown_cells],
            "gate_failures": m["gates"],
            "warnings": warnings,
            "placeholders": ph,
            "all_scores": {a: sorted(v) for a, v in all_scores.items()},
        }
    )

    with open(os.path.join(out_dir, "out.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)
    for name, text in tables.items():
        with open(os.path.join(tdir, name + ".md"), "w", encoding="utf-8") as fh:
            fh.write(text)
    if os.path.abspath(model_path) != os.path.abspath(
        os.path.join(out_dir, "model.json")
    ):
        shutil.copyfile(model_path, os.path.join(out_dir, "model.json"))

    # console summary
    print(f"{m['title']} v{m['version']} — primary profile: {P}")
    for k, (a, s) in enumerate(rk[:5], 1):
        print(f"  {k}. {a} {f2(s)}")
    if pr.get("runner"):
        print(
            f"  stability: {pr['label']} (margin {f2(pr['margin'])}, Monte Carlo {pct(pr['mc_win'][pr['top']])}, "
            f"weight flips {ph['WEIGHT_FLIPS']}, score flips {ph['SCORE_FLIPS']})"
        )
    print(f"  tables: {', '.join(sorted(tables))}")
    for w_ in warnings:
        print("  WARNING: " + w_)
    print("ALL ASSERTS PASSED")
    return out


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("model")
    ap.add_argument("--out", default="build")
    ap.add_argument(
        "--previous", help="previous version's model.json, for the change log"
    )
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    run(a.model, a.out, a.previous)


if __name__ == "__main__":
    main()
