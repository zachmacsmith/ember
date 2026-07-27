"""
docs/paper3/data/m4_analysis.py
================================
M4 headline analysis: reads m4_eval.csv (+ m4_race.csv) written by
m4_eval.py and renders m4_headline.txt + m4_headline.md with five tables:

  1. Per cell x arm vs minorminer — n both-succeed pairs, median paired
     dACL_spur, d%, win rate, Wilcoxon signed-rank p on the per-pair deltas
     (scipy.stats.wilcoxon, two-sided), Holm-corrected ACROSS THE 14 CELLS
     WITHIN EACH ARM, rank-biserial effect size; success rates reported
     separately and unpaired (protocol rule 4). Pairs are literal
     (inst_seed, algo_seed); the deterministic p3-template pairs its one
     value per instance against EVERY minorminer run of that instance (the
     §4.5 convention — those 5 pairs share one template value, so they are
     not independent; the p-value for the template row is flagged).
  2. Per-arm cross-seed ACL variance — per (cell, instance) the sample std
     of acl_spur across the eval algo seeds (both arms succeed-only rows,
     >= 2 successes required), then the per-cell median of those stds, and
     the arm/minorminer ratio. p3-template rows are zero-variance by
     construction — reported as 0.00x.
  3. Frontier — success counts on the past-cliff cells (P16 K180, Z12 K179)
     per arm, plus median acl_spur of the successes.
  4. Racer — the §4.6 pre-registered reads on eval seeds: [seq] race8-seq vs
     bestof8-seq (1 core) and [par] race8-par vs bestof8-par (8 cores), per
     cell and pooled, both-succeed pairs on (inst_seed, base_seed); plus the
     winner=template-excluded variant of each read (the §4.6 selection-claim
     exclusion) and per-mode success / acl_spur / wall / winner counts.
  5. Time — median wall per arm per cell. WITHIN-BATCH ONLY (protocol rule
     5): arms were interleaved in one queue on one host; no cross-batch or
     cross-host comparison is valid, and headline speed claims re-measure at
     --workers 1 on an idle machine.

Everything is computed from the CSVs; no network, no reruns. ACL column:
acl_spur everywhere except table 5 (rule 3; the one polish was applied
identically to every arm by the runner).

Guard: in full mode the script exits NONZERO if any expected (cell, arm)
block is missing rows or short of its expected row count (14 cells x 9 arms
for the main CSV; 6 cells x 4 modes x 75 rows for the race CSV) — partial
CSVs must never silently produce headline tables. --smoke relaxes the guard
to warnings and reads the *_smoke.csv files.

Run:
  .venv/bin/python docs/paper3/data/m4_analysis.py             # full CSVs
  .venv/bin/python docs/paper3/data/m4_analysis.py --smoke     # smoke CSVs
Flags: --smoke | --eval-csv PATH | --race-csv PATH
"""

import argparse
import csv
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# ── frozen registries (protocol.md; duplicated here so the analysis is
#    standalone — these are frozen, that is the point) ────────────────────────
SUITE = [
    ("P16", 100, 0.2), ("P16", 100, 0.3), ("P16", 140, 0.12),
    ("P16", 140, 0.2), ("P16", 140, 1.0), ("P16", 180, 1.0),
    ("P16", 160, 0.05),
    ("Z12", 100, 0.2), ("Z12", 100, 0.3), ("Z12", 140, 0.12),
    ("Z12", 140, 0.2), ("Z12", 140, 1.0), ("Z12", 179, 1.0),
    ("Z12", 160, 0.05),
]
ARMS = ("minorminer", "mmfork-cuthill", "p3-template", "p3-ate", "p3-clmm",
        "p3-clmm-core", "p3-mmpolish", "pssa", "attraction")
DET_SEED = "-1"
N_INST, N_SEEDS = 15, 5           # eval registries: inst 901-915, algo 10-14
FRONTIER = [("P16", 180, 1.0), ("Z12", 179, 1.0)]

RACE_CELLS = [("P16", 100, 0.2), ("P16", 100, 0.3), ("P16", 160, 0.05),
              ("Z12", 100, 0.2), ("Z12", 100, 0.3), ("Z12", 160, 0.05)]
MODES = ("race8-seq", "bestof8-seq", "bestof8-par", "race8-par")
READS = [("seq (1 core)", "race8-seq", "bestof8-seq"),
         ("par (8 cores)", "race8-par", "bestof8-par")]

EPS = 1e-9

# ── stats helpers: reuse the analysis package where available ────────────────
try:
    from ember_qc_analysis.statistics import _holm_bonferroni, _rank_biserial
    import numpy as _np

    def holm(ps):
        return _holm_bonferroni(list(ps))

    def rank_biserial(deltas):
        d = _np.asarray(deltas, dtype=float)
        return _rank_biserial(d, _np.zeros_like(d))
except ImportError:                                     # minimal reimplements
    def holm(ps):
        n = len(ps)
        if n == 0:
            return []
        order = sorted(range(n), key=lambda i: ps[i])
        out, prev = [None] * n, 0.0
        for rank, i in enumerate(order):
            c = min(max(ps[i] * (n - rank), prev), 1.0)
            out[i], prev = c, c
        return out

    def rank_biserial(deltas):
        from scipy.stats import rankdata
        d = [x for x in deltas if x != 0]
        if not deltas:
            return float("nan")
        if not d:
            return 0.0
        ranks = rankdata([abs(x) for x in d])
        w_pos = sum(r for r, x in zip(ranks, d) if x > 0)
        w_neg = sum(r for r, x in zip(ranks, d) if x < 0)
        max_w = len(d) * (len(d) + 1) / 2
        return float(1 - 2 * min(w_pos, w_neg) / max_w) if max_w else 0.0

from scipy.stats import wilcoxon  # noqa: E402


def wilcoxon_p(deltas):
    """Two-sided signed-rank p on paired deltas; (p, note)."""
    if len(deltas) < 3:
        return None, "n<3"
    nz = [d for d in deltas if abs(d) > EPS]
    if not nz:
        return 1.0, "all-tie"
    try:
        return float(wilcoxon(deltas, alternative="two-sided").pvalue), ""
    except ValueError as e:
        return None, str(e)[:40]


# ── small formatting helpers ─────────────────────────────────────────────────

def fnum(x, nd=3, plus=False):
    if x is None or (isinstance(x, float) and x != x):
        return "n/a"
    return f"{x:+.{nd}f}" if plus else f"{x:.{nd}f}"


def fp(p):
    if p is None:
        return "n/a"
    return f"{p:.1e}" if p < 0.001 else f"{p:.3f}"


def cell_label(topo, n, p):
    return f"{topo} K{n}" if p >= 1.0 else f"{topo} ({n},{p:g})"


def med(xs):
    return statistics.median(xs) if xs else None


# ──────────────────────────────────────────────────────────────────────────────
# Loading
# ──────────────────────────────────────────────────────────────────────────────

def load_rows(path):
    if not os.path.exists(path):
        return None
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))


def ckey(r):
    return (r["topo"], int(r["n"]), float(r["p"]))


def by_cell(rows):
    d = {}
    for r in rows:
        d.setdefault(ckey(r), []).append(r)
    return d


# ──────────────────────────────────────────────────────────────────────────────
# Pairing vs minorminer (main CSV)
# ──────────────────────────────────────────────────────────────────────────────

def mm_pairs_for_arm(cell_rows, arm):
    """Both-succeed (arm, mm) acl_spur pairs for one cell.

    Seeded rows pair per (inst_seed, algo_seed); the deterministic template
    row pairs against every minorminer run of its instance (§4.5 convention).
    """
    mm = {(r["inst_seed"], r["algo_seed"]): float(r["acl_spur"])
          for r in cell_rows if r["arm"] == "minorminer"
          and r["success"] == "1" and r["acl_spur"]}
    pairs = []
    for r in cell_rows:
        if r["arm"] != arm or r["success"] != "1" or not r["acl_spur"]:
            continue
        a = float(r["acl_spur"])
        if r["algo_seed"] == DET_SEED:
            pairs += [(a, v) for (i, _s), v in sorted(mm.items())
                      if i == r["inst_seed"]]
        else:
            key = (r["inst_seed"], r["algo_seed"])
            if key in mm:
                pairs.append((a, mm[key]))
    return pairs


def succ_str(cell_rows, arm):
    rows = [r for r in cell_rows if r["arm"] == arm]
    k = sum(1 for r in rows if r["success"] == "1")
    return f"{k}/{len(rows)}", (k, len(rows))


# ──────────────────────────────────────────────────────────────────────────────
# Table builders — each returns dict(title, notes, header, rows)
# ──────────────────────────────────────────────────────────────────────────────

def table1_paired(cells_present, cellmap):
    header = ["cell", "arm", "n_pairs", "med dACL", "d%", "W/L/T", "win%",
              "p (Wilcoxon)", "p_holm", "r (rb)", "succ arm", "succ MM"]
    rows, stats_by_arm = [], {}
    for cell in cells_present:
        crows = cellmap[cell]
        for arm in ARMS:
            if arm == "minorminer":
                continue
            if not any(r["arm"] == arm for r in crows):
                continue
            pairs = mm_pairs_for_arm(crows, arm)
            deltas = [a - m for a, m in pairs]
            if deltas:
                m_d = med(deltas)
                ref = med([m for _a, m in pairs])
                pct = 100.0 * m_d / ref if ref else None
                w = sum(1 for d in deltas if d < -EPS)
                l = sum(1 for d in deltas if d > EPS)
                t = len(deltas) - w - l
                winp = 100.0 * w / len(deltas)
                p, note = wilcoxon_p(deltas)
                r_es = rank_biserial(deltas)
            else:
                m_d = pct = winp = p = r_es = None
                w = l = t = 0
                note = "no pairs"
            sa, _ = succ_str(crows, arm)
            sm, _ = succ_str(crows, "minorminer")
            entry = {"cell": cell, "arm": arm, "n": len(deltas), "med": m_d,
                     "pct": pct, "wlt": f"{w}/{l}/{t}", "winp": winp,
                     "p": p, "note": note, "r": r_es, "sa": sa, "sm": sm}
            stats_by_arm.setdefault(arm, []).append(entry)

    # Holm across the cells WITHIN each arm (<=14 tests per arm).
    for arm, entries in stats_by_arm.items():
        idx = [i for i, e in enumerate(entries) if e["p"] is not None]
        corr = holm([entries[i]["p"] for i in idx])
        for j, i in enumerate(idx):
            entries[i]["ph"] = corr[j]
        for e in entries:
            e.setdefault("ph", None)

    for arm in ARMS:
        for e in stats_by_arm.get(arm, []):
            tag = " *det" if arm == "p3-template" else ""
            p_txt = fp(e["p"]) + (f" [{e['note']}]" if e["note"] else "") + tag
            rows.append([cell_label(*e["cell"]), arm, str(e["n"]),
                         fnum(e["med"], 3, plus=True),
                         (fnum(e["pct"], 1, plus=True) + "%"
                          if e["pct"] is not None else "n/a"),
                         e["wlt"],
                         fnum(e["winp"], 0) if e["winp"] is not None else "n/a",
                         p_txt, fp(e["ph"]), fnum(e["r"], 2), e["sa"], e["sm"]])
    return {
        "title": "Table 1 — per cell x arm vs minorminer "
                 "(acl_spur; both-succeed pairs on (inst_seed, algo_seed))",
        "notes": [
            "Holm correction applied across the cells within each arm.",
            "*det: p3-template is deterministic — its one value per instance "
            "pairs against all 5 MM seeds of that instance; those pairs are "
            "not independent, so its p is anti-conservative (flagged, "
            "reported under the §4.5 convention).",
            "Success rates are separate and unpaired (rule 4); dACL uses "
            "both-succeed pairs only."],
        "header": header, "rows": rows}


def table2_variance(cells_present, cellmap):
    var_arms = [a for a in ARMS if a != "minorminer"]
    header = ["cell", "MM med-std"] + [a for a in var_arms]
    rows = []
    ratios_by_arm = {a: [] for a in var_arms}

    def cell_medstd(crows, arm):
        per_inst = {}
        for r in crows:
            if r["arm"] == arm and r["success"] == "1" and r["acl_spur"]:
                per_inst.setdefault(r["inst_seed"], []).append(
                    float(r["acl_spur"]))
        stds = [statistics.stdev(v) for v in per_inst.values() if len(v) >= 2]
        return med(stds)

    for cell in cells_present:
        crows = cellmap[cell]
        mm_std = cell_medstd(crows, "minorminer")
        line = [cell_label(*cell), fnum(mm_std, 4)]
        for arm in var_arms:
            if arm == "p3-template":
                line.append("0.00x")        # zero-variance by construction
                ratios_by_arm[arm].append(0.0)
                continue
            a_std = cell_medstd(crows, arm)
            if a_std is None or mm_std is None or mm_std <= 0:
                line.append("n/a")
            else:
                ratio = a_std / mm_std
                ratios_by_arm[arm].append(ratio)
                line.append(f"{ratio:.2f}x")
        rows.append(line)
    pooled = ["MEDIAN across cells", ""]
    for arm in var_arms:
        m = med(ratios_by_arm[arm])
        pooled.append(f"{m:.2f}x" if m is not None else "n/a")
    rows.append(pooled)
    return {
        "title": "Table 2 — per-arm cross-seed ACL variance "
                 "(per (cell, instance): sample std of acl_spur across the "
                 "eval algo seeds; per-cell median of those stds; arm/MM "
                 "ratio)",
        "notes": [
            "Successful rows only; an instance needs >= 2 successes to "
            "contribute a std.",
            "p3-template is deterministic: zero cross-seed variance by "
            "construction, reported as 0.00x."],
        "header": header, "rows": rows}


def table3_frontier(cellmap):
    header = ["cell", "arm", "success", "med acl_spur"]
    rows = []
    for cell in FRONTIER:
        crows = cellmap.get(cell, [])
        if not crows:
            rows.append([cell_label(*cell), "(no rows)", "", ""])
            continue
        for arm in ARMS:
            if not any(r["arm"] == arm for r in crows):
                continue
            s, _ = succ_str(crows, arm)
            accs = [float(r["acl_spur"]) for r in crows
                    if r["arm"] == arm and r["success"] == "1"
                    and r["acl_spur"]]
            rows.append([cell_label(*cell), arm, s, fnum(med(accs), 3)])
    return {
        "title": "Table 3 — frontier: success on the past-cliff cells "
                 "(P16 K180, Z12 K179; unpaired counts)",
        "notes": ["K_n cells run one instance (instance-invariant); seeded "
                  "arms n=5 eval algo seeds, p3-template n=1 (deterministic)."],
        "header": header, "rows": rows}


def race_read(cell_rows, mode_a, mode_b, excl_template=False):
    vals, winner = {}, {}
    for r in cell_rows:
        k = (r["mode"], r["inst_seed"], r["base_seed"])
        if r["success"] == "1" and r["acl_spur"]:
            vals[k] = float(r["acl_spur"])
        winner[k] = r.get("winner", "")
    pairs = []
    for (m, i, b), va in sorted(vals.items()):
        if m != mode_a:
            continue
        if excl_template and winner.get((mode_a, i, b), "").startswith(
                "template"):
            continue
        vb = vals.get((mode_b, i, b))
        if vb is not None:
            pairs.append((va, vb))
    return pairs


def fmt_race_read(pairs):
    if not pairs:
        return ["0", "n/a", "n/a", "-", "n/a", "n/a"]
    deltas = [a - b for a, b in pairs]
    w = sum(1 for d in deltas if d < -EPS)
    l = sum(1 for d in deltas if d > EPS)
    t = len(deltas) - w - l
    m_d = med(deltas)
    ref = med([b for _a, b in pairs])
    pct = 100.0 * m_d / ref if ref else None
    le = 100.0 * sum(1 for d in deltas if d <= EPS) / len(deltas)
    p, note = wilcoxon_p(deltas)
    return [str(len(pairs)), fnum(m_d, 3, plus=True),
            (fnum(pct, 2, plus=True) + "%") if pct is not None else "n/a",
            f"{w}/{l}/{t}", f"{le:.0f}%",
            fp(p) + (f" [{note}]" if note else "")]


def table4_racer(race_rows):
    header = ["cell", "read", "n", "med d", "d%", "W/L/T", "pct(a<=b)",
              "p (Wilcoxon)"]
    mode_hdr = ["cell", "mode", "success", "med acl_spur", "med wall",
                "winners"]
    mode_rows, read_rows = [], []
    pooled = {name: [] for name, _a, _b in READS}
    pooled_x = {name: [] for name, _a, _b in READS}
    cellmap = by_cell(race_rows)
    cells = [c for c in RACE_CELLS if c in cellmap] + \
        sorted(c for c in cellmap if c not in RACE_CELLS)
    for cell in cells:
        crows = cellmap[cell]
        for mode in MODES:
            mrows = [r for r in crows if r["mode"] == mode]
            if not mrows:
                continue
            k = sum(1 for r in mrows if r["success"] == "1")
            accs = [float(r["acl_spur"]) for r in mrows
                    if r["success"] == "1" and r["acl_spur"]]
            walls = [float(r["wall"]) for r in mrows if r["wall"]]
            wins = {}
            for r in mrows:
                if r["success"] == "1" and r["winner"]:
                    kk = r["winner"].split("[")[0]
                    wins[kk] = wins.get(kk, 0) + 1
            mode_rows.append([cell_label(*cell), mode, f"{k}/{len(mrows)}",
                              fnum(med(accs), 3),
                              fnum(med(walls), 1) + "s" if walls else "n/a",
                              " ".join(f"{a}:{c}" for a, c
                                       in sorted(wins.items()))])
        for name, ma, mb in READS:
            pairs = race_read(crows, ma, mb)
            read_rows.append([cell_label(*cell), name] + fmt_race_read(pairs))
            pooled[name] += pairs
            pairs_x = race_read(crows, ma, mb, excl_template=True)
            read_rows.append([cell_label(*cell), name + " excl-tpl"]
                             + fmt_race_read(pairs_x))
            pooled_x[name] += pairs_x
    for name, _a, _b in READS:
        read_rows.append(["POOLED", name] + fmt_race_read(pooled[name]))
        read_rows.append(["POOLED", name + " excl-tpl"]
                         + fmt_race_read(pooled_x[name]))
    return {
        "title": "Table 4 — racer: §4.6 pre-registered reads on eval seeds "
                 "(acl_spur; pairs on (inst_seed, base_seed), both-succeed)",
        "notes": [
            "Reads: [seq] race8-seq vs bestof8-seq at 1 core; [par] "
            "race8-par vs bestof8-par at 8 cores (protocol rule 2 controls).",
            "excl-tpl drops pairs whose race winner is the template — the "
            "§4.6 selection claim excludes template-floor wins (mid cells); "
            "the full read is the ATE story wearing a racer hat there."],
        "header": header, "rows": read_rows,
        "extra": {"title": "Table 4b — per-mode operations view",
                  "notes": [], "header": mode_hdr, "rows": mode_rows}}


def table5_time(cells_present, cellmap):
    header = ["cell"] + list(ARMS)
    rows = []
    for cell in cells_present:
        crows = cellmap[cell]
        line = [cell_label(*cell)]
        for arm in ARMS:
            ts = [float(r["time"]) for r in crows
                  if r["arm"] == arm and r["time"]]
            line.append(fnum(med(ts), 1) if ts else "n/a")
        rows.append(line)
    return {
        "title": "Table 5 — median wall seconds per arm per cell "
                 "(all attempts, success or not)",
        "notes": [
            "WITHIN-BATCH ONLY (rule 5): arms interleaved in one queue on "
            "one host at one worker count. Never compare across batches or "
            "hosts; headline speed claims re-measure at --workers 1 idle."],
        "header": header, "rows": rows}


# ──────────────────────────────────────────────────────────────────────────────
# Guards
# ──────────────────────────────────────────────────────────────────────────────

def expected_main_count(p, arm):
    n_inst = 1 if p >= 1.0 else N_INST
    return n_inst if arm == "p3-template" else n_inst * N_SEEDS


def check_blocks(eval_rows, race_rows, race_csv_exists):
    missing = []
    counts = {}
    for r in eval_rows:
        counts[(ckey(r), r["arm"])] = counts.get((ckey(r), r["arm"]), 0) + 1
    for cell in SUITE:
        for arm in ARMS:
            want = expected_main_count(cell[2], arm)
            have = counts.get((cell, arm), 0)
            if have < want:
                missing.append(f"main {cell_label(*cell)} {arm}: "
                               f"{have}/{want} rows")
    if not race_csv_exists:
        missing.append("race CSV missing entirely (stage race not run or "
                       "not synced)")
    else:
        rcounts = {}
        for r in race_rows:
            rcounts[(ckey(r), r["mode"])] = \
                rcounts.get((ckey(r), r["mode"]), 0) + 1
        for cell in RACE_CELLS:
            for mode in MODES:
                want = N_INST * N_SEEDS
                have = rcounts.get((cell, mode), 0)
                if have < want:
                    missing.append(f"race {cell_label(*cell)} {mode}: "
                                   f"{have}/{want} rows")
    return missing


# ──────────────────────────────────────────────────────────────────────────────
# Rendering
# ──────────────────────────────────────────────────────────────────────────────

def render_text(tables, preamble):
    out = [preamble, ""]
    for t in tables:
        out += ["=" * 100, t["title"]]
        out += [f"  note: {n}" for n in t["notes"]]
        out.append("-" * 100)
        widths = [len(h) for h in t["header"]]
        for row in t["rows"]:
            for i, v in enumerate(row):
                widths[i] = max(widths[i], len(str(v)))
        fmt = "  ".join(f"{{:<{w}}}" for w in widths)
        out.append(fmt.format(*t["header"]))
        for row in t["rows"]:
            out.append(fmt.format(*[str(v) for v in row]))
        out.append("")
    return "\n".join(out)


def render_md(tables, preamble):
    out = ["# M4 frozen-eval headline", "", preamble.replace("\n", "\n\n"), ""]
    for t in tables:
        out += [f"## {t['title']}", ""]
        for n in t["notes"]:
            out.append(f"> {n}")
        if t["notes"]:
            out.append("")
        out.append("| " + " | ".join(t["header"]) + " |")
        out.append("|" + "|".join("---" for _ in t["header"]) + "|")
        for row in t["rows"]:
            out.append("| " + " | ".join(str(v) for v in row) + " |")
        out.append("")
    return "\n".join(out)


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="M4 headline analysis")
    ap.add_argument("--smoke", action="store_true",
                    help="read the *_smoke.csv files; missing-block guard "
                         "relaxed to warnings")
    ap.add_argument("--eval-csv", default=None)
    ap.add_argument("--race-csv", default=None)
    args = ap.parse_args()

    suffix = "_smoke" if args.smoke else ""
    eval_csv = args.eval_csv or os.path.join(HERE, f"m4_eval{suffix}.csv")
    race_csv = args.race_csv or os.path.join(HERE, f"m4_race{suffix}.csv")
    out_txt = os.path.join(HERE, f"m4_headline{suffix}.txt")
    out_md = os.path.join(HERE, f"m4_headline{suffix}.md")

    eval_rows = load_rows(eval_csv)
    if eval_rows is None:
        sys.exit(f"eval CSV not found: {eval_csv}")
    race_rows = load_rows(race_csv)
    race_exists = race_rows is not None

    missing = check_blocks(eval_rows, race_rows or [], race_exists)

    cellmap = by_cell(eval_rows)
    cells_present = [c for c in SUITE if c in cellmap] + \
        sorted(c for c in cellmap if c not in SUITE)

    tables = [table1_paired(cells_present, cellmap),
              table2_variance(cells_present, cellmap),
              table3_frontier(cellmap)]
    if race_exists and race_rows:
        t4 = table4_racer(race_rows)
        tables += [t4, t4.pop("extra")]
    else:
        tables.append({"title": "Table 4 — racer", "notes": [],
                       "header": ["status"],
                       "rows": [[f"no race CSV at {race_csv}"]]})
    tables.append(table5_time(cells_present, cellmap))

    mode = "SMOKE (guard relaxed)" if args.smoke else "FULL"
    preamble = (f"M4 frozen-eval analysis [{mode}] — column: acl_spur "
                f"(tables 1-4; rule 3), wall s (table 5).\n"
                f"eval CSV: {eval_csv} ({len(eval_rows)} rows)   race CSV: "
                f"{race_csv} ({len(race_rows) if race_rows else 0} rows)\n"
                f"Registries: EVAL instances 901-915 (K_n cells "
                f"instance-invariant, one instance recorded as 901), eval "
                f"algo seeds 10-14, 60 s, paired script route (rule 1).")

    text = render_text(tables, preamble)
    mdtext = render_md(tables, preamble)
    print(text)
    with open(out_txt, "w") as fh:
        fh.write(text + "\n")
    with open(out_md, "w") as fh:
        fh.write(mdtext + "\n")
    print(f"wrote {out_txt}\nwrote {out_md}")

    if missing:
        print(f"\n{'WARNING' if args.smoke else 'ERROR'}: "
              f"{len(missing)} expected block(s) missing/short:")
        for m in missing[:40]:
            print(f"  - {m}")
        if len(missing) > 40:
            print(f"  ... and {len(missing) - 40} more")
        if not args.smoke:
            sys.exit(2)
        print("smoke mode: guard relaxed — exit 0")


if __name__ == "__main__":
    main()
