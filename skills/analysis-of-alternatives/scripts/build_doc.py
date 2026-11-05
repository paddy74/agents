#!/usr/bin/env python3
"""Fill an AoA template from the engine output, check the document, and write the verification log.

Build:
    python3 build_doc.py template.md --build build/ -o Subject_AoA_v1.1.md \
        [--stale "old phrase" ...] [--allow word ...] [--analyst-review "what you checked"]

Audit an existing document (no writing):
    python3 build_doc.py --check-only Subject_AoA_v1.1.md [--build build/]

Placeholders in the template:
    {{KEY}}                    a value from build/out.json "placeholders" (for example {{TOP1}}, {{MARGIN}})
    {{TABLE:name}}             build/tables/name.md (for example {{TABLE:ranking_primary}})
    {{SCORE:Profile:Alt}}      one weighted score, two decimals
    {{MODEL_JSON}}             build/model.json as a fenced block (Appendix C)
    {{VERIFICATION_LOG}}       filled last with the results of the checks below

Checks: placeholders left, table structure (incl. blank lines inside tables),
template sections present, stale wording outside the history/answers/change/
verification sections, two-decimal scores in table rows vs engine output,
leftover TODOs, and spelling (codespell, when installed).
Exit status 1 if any check fails; warnings do not fail the build.
"""

import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

PH_RE = re.compile(r"\{\{\s*(.+?)\s*\}\}")
SEP_RE = re.compile(r"^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$")
VERIF_RE = re.compile(r"verification", re.I)
EXCLUDE_RE = re.compile(
    r"revision history|answers received|score change|changes from|appendix b|verification",
    re.I,
)
RECOMMEND_RE = re.compile(
    r"recommend|adopt|\bchoose\b|\bpick\b|winner|ranks? first", re.I
)
SCORE_CELL_RE = re.compile(r"^[\s*~]*([1-5]\.\d\d)[\s*~✗]*$")
REQUIRED_SECTIONS = [f"## {i}." for i in range(1, 19)] + [
    "## Appendix A",
    "## Appendix B",
    "## Appendix C",
]


def strip_md(cell):
    return re.sub(r"[*~✗`]", "", cell).strip()


def split_cells(line):
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|") and not s.endswith("\\|"):
        s = s[:-1]
    return [c.strip() for c in re.split(r"(?<!\\)\|", s)]


def code_mask(lines):
    """True for lines inside fenced code blocks."""
    mask, inside = [], False
    for ln in lines:
        if ln.lstrip().startswith("```") or ln.lstrip().startswith("~~~"):
            mask.append(True)
            inside = not inside
            continue
        mask.append(inside)
    return mask


def section_mask(lines, cmask, pattern=EXCLUDE_RE):
    """True for lines in sections whose heading matches `pattern` (until the next heading of the same or higher level)."""
    mask, excl_level = [], None
    for ln, inc in zip(lines, cmask, strict=False):
        m = re.match(r"^(#{1,6})\s+(.*)", ln) if not inc else None
        if m:
            lvl = len(m.group(1))
            if excl_level is not None and lvl <= excl_level:
                excl_level = None
            if excl_level is None and pattern.search(m.group(2)):
                excl_level = lvl
        mask.append(excl_level is not None)
    return mask


# ----------------------------------------------------------------- fill
def compact_jsondumps(v):
    return json.dumps(v, ensure_ascii=False, separators=(", ", ": "))


def compact_json(obj):
    """Valid JSON, one line per alternative, score row, weight profile or gate list, so the
    embedded model stays readable but short."""
    lines, items = ["{"], list(obj.items())
    for i, (k, v) in enumerate(items):
        end = "," if i < len(items) - 1 else ""
        if (
            isinstance(v, dict)
            and v
            and all(isinstance(x, (dict, list)) for x in v.values())
        ):
            lines.append(f"  {compact_jsondumps(k)}: {{")
            sub = list(v.items())
            lines += [
                f"    {compact_jsondumps(k2)}: {compact_jsondumps(v2)}"
                + ("," if j < len(sub) - 1 else "")
                for j, (k2, v2) in enumerate(sub)
            ]
            lines.append("  }" + end)
        elif isinstance(v, list) and v and all(isinstance(x, dict) for x in v):
            lines.append(f"  {compact_jsondumps(k)}: [")
            lines += [
                "    " + compact_jsondumps(x) + ("," if j < len(v) - 1 else "")
                for j, x in enumerate(v)
            ]
            lines.append("  ]" + end)
        else:
            lines.append(f"  {compact_jsondumps(k)}: {compact_jsondumps(v)}{end}")
    text = "\n".join(lines + ["}"])
    assert json.loads(text) == obj
    return text


def fill(template, build):
    with open(os.path.join(build, "out.json"), encoding="utf-8") as fh:
        out = json.load(fh)
    ph = out.get("placeholders", {})
    missing = []

    def repl(m):
        key = m.group(1)
        if key == "VERIFICATION_LOG":
            return m.group(0)
        if key == "MODEL_JSON":
            p = os.path.join(build, "model.json")
            if not os.path.exists(p):
                missing.append(key)
                return m.group(0)
            return (
                "```json\n"
                + compact_json(json.load(open(p, encoding="utf-8")))
                + "\n```"
            )
        if key.startswith("TABLE:"):
            p = os.path.join(build, "tables", key[6:].strip() + ".md")
            if not os.path.exists(p):
                missing.append(key)
                return m.group(0)
            return open(p, encoding="utf-8").read().rstrip()
        if key.startswith("SCORE:"):
            parts = key.split(":", 2)
            try:
                return f"{out['scores_by_profile'][parts[1]][parts[2]]:.2f}"
            except (KeyError, IndexError):
                missing.append(key)
                return m.group(0)
        if key in ph:
            return str(ph[key])
        missing.append(key)
        return m.group(0)

    return PH_RE.sub(repl, template), missing, out


# ----------------------------------------------------------------- checks
def check_doc(text, out=None, stale=(), allow=()):
    lines = text.split("\n")
    cmask = code_mask(lines)
    smask = section_mask(lines, cmask)
    vmask = section_mask(
        lines, cmask, VERIF_RE
    )  # the verification log describes the checks; don't let it trip them
    inline_code = re.compile(r"`[^`]*`")
    results = {}

    # 1. placeholders
    left = []
    for i, (ln, c, v) in enumerate(zip(lines, cmask, vmask, strict=False), 1):
        if c or v:
            continue
        for m in PH_RE.finditer(inline_code.sub("", ln)):
            if m.group(1) != "VERIFICATION_LOG":
                left.append(f"L{i} {{{{{m.group(1)}}}}}")
    results["Placeholders"] = ("fail" if left else "pass", left)

    # 2. tables
    probs, i, n = [], 0, len(lines)
    while i < n:
        if cmask[i] or not lines[i].lstrip().startswith("|"):
            i += 1
            continue
        j = i
        while j < n and not cmask[j] and lines[j].lstrip().startswith("|"):
            j += 1
        block = lines[i:j]
        if len(block) < 2 or not SEP_RE.match(block[1].strip()):
            # rows with no header: often the tail of a table split by a blank line
            k = i - 1
            while k >= 0 and not lines[k].strip():
                k -= 1
            if k >= 0 and SEP_RE.match(lines[k].strip()):
                probs.append(
                    f"L{i + 1}: blank line splits a table (rows continue after the separator on L{k + 1})"
                )
            else:
                probs.append(f"L{i + 1}: table without a header separator row")
        else:
            ncol = len(split_cells(block[0]))
            if len(split_cells(block[1])) != ncol:
                probs.append(
                    f"L{i + 2}: separator has {len(split_cells(block[1]))} columns, header has {ncol}"
                )
            for k, row in enumerate(block[2:], i + 3):
                if len(split_cells(row)) != ncol:
                    probs.append(
                        f"L{k}: {len(split_cells(row))} columns, header has {ncol}"
                    )
            if len(block) == 2:
                probs.append(f"L{i + 1}: table has a header but no rows")
        i = j
    results["Tables"] = ("fail" if probs else "pass", probs)

    # 3. template sections
    heads = [
        ln
        for ln, c in zip(lines, cmask, strict=False)
        if not c and ln.startswith("## ")
    ]
    miss = [s for s in REQUIRED_SECTIONS if not any(h.startswith(s) for h in heads)]
    results["Template sections"] = (
        "fail" if miss else "pass",
        [
            f"missing '{s}' (keep the heading; write 'Not applicable: <reason>' if it does not apply)"
            for s in miss
        ],
    )

    # 4. stale text
    hits, warn = [], []
    terms = [t for t in stale if t]
    prev_top = (out or {}).get("previous_top")
    cur_top = (
        (out or {}).get("profiles", {}).get((out or {}).get("primary"), {}).get("top")
    )
    for i, (ln, c, s) in enumerate(zip(lines, cmask, smask, strict=False), 1):
        if c or s:
            continue
        low = ln.lower()
        for t in terms:
            if t.lower() in low:
                hits.append(f"L{i}: '{t}'")
        if (
            prev_top
            and cur_top
            and prev_top != cur_top
            and prev_top.lower() in low
            and RECOMMEND_RE.search(ln)
        ):
            warn.append(
                f"L{i}: previous top pick '{prev_top}' next to recommendation wording; confirm it is intended"
            )
    results["Stale text"] = (
        "fail" if hits else ("warn" if warn else "pass"),
        hits + warn,
    )

    # 5. scores in table rows vs engine output
    unmatched = []
    if out:
        alts = {a.lower(): a for a in out.get("alternatives", [])}
        alls = dict(out.get("all_scores", {}))
        for i, (ln, c) in enumerate(zip(lines, cmask, strict=False), 1):
            if c or not ln.lstrip().startswith("|") or SEP_RE.match(ln.strip()):
                continue
            cells = split_cells(ln)
            named = [
                alts[strip_md(x).lower()] for x in cells if strip_md(x).lower() in alts
            ]
            if len(named) != 1:
                continue
            a = named[0]
            for x in cells:
                mm = SCORE_CELL_RE.match(x)
                if mm:
                    v = float(mm.group(1))
                    if not any(abs(v - s) <= 0.0051 for s in alls.get(a, [])):
                        unmatched.append(f"L{i}: {a} {v:.2f} matches no engine score")
    results["Scores in tables"] = (
        "warn" if unmatched else ("pass" if out else "not run"),
        unmatched,
    )

    # 6. TODO markers
    todos = [
        f"L{i}"
        for i, (ln, c, v) in enumerate(zip(lines, cmask, vmask, strict=False), 1)
        if not (c or v) and "TODO" in ln
    ]
    results["Change reasons / TODO"] = ("fail" if todos else "pass", todos)

    # 7. spelling
    exe = shutil.which("codespell")
    cmd = (
        [exe]
        if exe
        else (
            [sys.executable, "-m", "codespell_lib"]
            if importlib.util.find_spec("codespell_lib")
            else None
        )
    )
    if cmd:
        words = {w.lower() for w in allow}
        for a in (out or {}).get("alternatives", []):
            words.update(re.findall(r"[a-z]{3,}", a.lower()))
        with tempfile.NamedTemporaryFile(
            "w", suffix=".md", delete=False, encoding="utf-8"
        ) as tf:
            tf.write(text)
            tmp = tf.name
        try:
            args = cmd + ([tmp, "-L", ",".join(sorted(words))] if words else [tmp])
            r = subprocess.run(args, capture_output=True, text=True)
            found = [
                ln.replace(tmp, "doc") for ln in r.stdout.splitlines() if ln.strip()
            ]
        finally:
            os.unlink(tmp)
        results["Spelling"] = ("fail" if found else "pass", found)
    else:
        results["Spelling"] = (
            "not run",
            [
                "codespell is not installed; proofread manually and say so in Limitations"
            ],
        )
    return results


METHODS = {
    "Placeholders": "Scan for unfilled double-brace placeholders outside code",
    "Tables": "Header, separator and column count per row; no blank line inside a table",
    "Template sections": "All 18 numbered sections and Appendices A–C present",
    "Stale text": "Listed stale terms, and the previous top pick next to recommendation wording, outside history/answers/change/verification sections",
    "Scores in tables": "Two-decimal scores in rows naming an alternative vs aoa_engine.py output",
    "Change reasons / TODO": "No to-do markers left (including change-log reasons)",
    "Spelling": "codespell with domain allow-list",
}


def verification_table(results, out, analyst):
    rows = ["| Check | Method | Result |", "|---|---|---|"]
    if out:
        rows.append(
            f"| Arithmetic and inputs | aoa_engine.py v{out.get('engine_version', '?')} asserts: weights total 100, scores 1–5 or ?, "
            f"valid names; seed {out.get('seed')} | {'Pass' if out.get('asserts_passed') else 'Fail'} |"
        )
    for k, (status, items) in results.items():
        res = {
            "pass": "Pass",
            "fail": "Fail",
            "warn": "Pass with notes",
            "not run": "Not run",
        }[status]
        if items:
            res += f" ({len(items)}: {'; '.join(items[:3])}{'; …' if len(items) > 3 else ''})"
        rows.append(f"| {k} | {METHODS[k]} | {res.replace('|', '/')} |")
    rows.append(
        f"| Prose vs model | Analyst read-through of the summary and recommendation against the ranking and gate tables | {analyst or 'PENDING: read the summary against the tables, then rebuild with --analyst-review'} |"
    )
    return "\n".join(rows)


def report(results):
    bad = False
    for k, (status, items) in results.items():
        print(f"[{status.upper():7}] {k}")
        for it in items[:15]:
            print("           " + it)
        if len(items) > 15:
            print(f"           … {len(items) - 15} more")
        bad |= status == "fail"
    return bad


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("template", nargs="?")
    ap.add_argument("--build", default="build")
    ap.add_argument("-o", "--output")
    ap.add_argument("--stale", nargs="*", default=[])
    ap.add_argument(
        "--allow", nargs="*", default=[], help="extra words codespell should accept"
    )
    ap.add_argument(
        "--analyst-review", default="", help="one line on what you checked by reading"
    )
    ap.add_argument("--check-only", metavar="DOC")
    a = ap.parse_args()

    if a.check_only:
        text = open(a.check_only, encoding="utf-8").read()
        out = None
        p = os.path.join(a.build, "out.json")
        if os.path.exists(p):
            out = json.load(open(p, encoding="utf-8"))
        bad = report(check_doc(text, out, a.stale, a.allow))
        sys.exit(1 if bad else 0)

    if not a.template or not a.output:
        ap.error("template and -o are required unless --check-only is used")
    text, missing, out = fill(open(a.template, encoding="utf-8").read(), a.build)
    if missing:
        print(
            "UNKNOWN PLACEHOLDERS (no value in out.json / tables): "
            + ", ".join(sorted(set(missing)))
        )
    results = check_doc(text, out, a.stale, a.allow)
    log = verification_table(results, out, a.analyst_review)
    if "{{VERIFICATION_LOG}}" in text:
        text = text.replace("{{VERIFICATION_LOG}}", log)
    else:
        results["Placeholders"][1].append(
            "template has no {{VERIFICATION_LOG}}; the log was not written"
        )
    with open(a.output, "w", encoding="utf-8") as fh:
        fh.write(text)
    bad = report(results) or bool(missing)
    if not a.analyst_review:
        print(
            "[REMINDER] Prose vs model is PENDING: read the summary against the tables, then rebuild with --analyst-review."
        )
    print(
        ("NOT READY: fix the failures above and rebuild." if bad else "BUILD OK")
        + f"  -> {a.output}"
    )
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
