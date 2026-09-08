"""Bounded diagnostics on saved independent incumbents; no algorithm edits.

Only successful native-search records are eligible inputs. Controls use the
same saved incumbent and fixed groups, not cumulative best-of-controls output.
Additional-root scans use the existing tree builder and validate every claimed
single-chain gain. They are opportunity probes, not a new runtime algorithm.
"""
from __future__ import annotations

import argparse
from collections import deque
from contextlib import contextmanager
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "packages/ember-qc/src"))

import networkx as nx
from ember_qc.algorithms.factored import contact_repair as cr


def read_graph(path):
    data = json.loads(path.read_text())
    graph = nx.Graph()
    graph.add_nodes_from(data["nodes"])
    graph.add_edges_from(data["edges"])
    for v, attrs in data.get("node_attributes", []):
        graph.nodes[v].update(attrs)
    graph.graph.update(data.get("metadata", {}))
    return graph, data


def digest(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True,
                                    separators=(",", ":")).encode()).hexdigest()


def independently_valid(embedding, source, target):
    assert set(embedding) == set(source)
    seen = set()
    for chain in embedding.values():
        assert chain and len(set(chain)) == len(chain)
        assert set(chain) <= set(target) and not seen.intersection(chain)
        assert nx.is_connected(target.subgraph(chain))
        seen.update(chain)
    assert all(any(target.has_edge(q, r) for q in embedding[v] for r in embedding[w])
               for v, w in source.edges())


@contextmanager
def root_attempt_cap(limit):
    """Diagnostic isolation of route quota from root quota, without source edits."""
    original_alternatives = cr._alternatives

    def limited(*args, **kwargs):
        original_grow = cr._grow
        attempts = 0

        def grow(*grow_args, **grow_kwargs):
            nonlocal attempts
            attempts += 1
            if attempts > limit:
                return None
            return original_grow(*grow_args, **grow_kwargs)

        cr._grow = grow
        try:
            return original_alternatives(*args, **kwargs)
        finally:
            cr._grow = original_grow

    cr._alternatives = limited
    try:
        yield
    finally:
        cr._alternatives = original_alternatives


def exact_short_tree(region, masks, required, ctx, cap):
    """Enumerate only connected sets of sizes 1--3 in the fixed free region."""
    tested = 0
    layer = {frozenset((q,)) for q in region}
    for size in range(1, min(cap, 3) + 1):
        for chain in layer:
            tested += 1
            mask = 0
            for q in chain:
                mask |= masks.get(q, 0)
            if mask == required:
                return chain, tested, size
        if size < min(cap, 3):
            layer = {chain | {r} for chain in layer for q in chain
                     for r in ctx.adj[q] if r in region and r not in chain}
    return None, tested, min(cap, 3)


def global_singleton_probes(embedding, source, target, ctx):
    """Enumerate all legal singleton sites, including disconnected free regions."""
    owner = {q: v for v, chain in embedding.items() for q in chain}
    probes = []
    start = time.perf_counter()
    for v in ctx.nodes:
        if len(embedding[v]) <= 1:
            continue
        sites = set(ctx.adj)
        for w in ctx.src_adj[v]:
            sites &= {r for q in embedding[w] for r in ctx.adj[q]}
        sites = {q for q in sites if q not in owner or owner[q] == v}
        region = cr._region(ctx, embedding, {v}, 2, 512, cr._Budget(20000, None))
        assert region is not None
        for q in sites:
            trial = dict(embedding)
            trial[v] = [q]
            independently_valid(trial, source, target)
        outside = sites - region
        distances = {}
        if outside:
            distances = {q: 0 for q in embedding[v]}
            queue = deque(embedding[v])
            while queue:
                q = queue.popleft()
                for r in ctx.adj[q]:
                    if (r not in owner or owner[r] == v) and r not in distances:
                        distances[r] = distances[q] + 1
                        queue.append(r)
        probes.append({"vertex": v, "old_size": len(embedding[v]),
                       "sites": sorted(sites), "sites_in_region": sorted(sites & region),
                       "sites_outside_region": sorted(outside),
                       "outside_free_distance": {q: distances.get(q) for q in sorted(outside)},
                       "region_size": len(region)})
    return {"wall": time.perf_counter() - start, "probes": probes}


def root_probe(v, embedding, source, target, ctx, root_limit, work_limit):
    """Scan extra roots for exactly the same singleton replacement region."""
    cap = len(embedding[v]) - 1
    if cap < ctx.lower_bound(v):
        return None
    setup = cr._Budget(work_limit, None)
    region = cr._region(ctx, embedding, {v}, 2, 512, setup)
    if region is None:
        return None
    masks = {}
    for i, w in enumerate(ctx.src_adj[v]):
        boundary = {r for q in embedding[w] for r in ctx.adj[q] if r in region}
        for q in boundary:
            masks[q] = masks.get(q, 0) | (1 << i)
    required = (1 << len(ctx.src_adj[v])) - 1
    old = set(embedding[v])
    roots = sorted(region, key=lambda q: (-cr._popcount(masks.get(q, 0)),
                                         q not in old, ctx.rank[q]))
    base, info = cr._repair(
        embedding, ctx, (v,), beam_width=4, alternatives=3, halo=2,
        max_region=512, max_expansions=work_limit, max_orders=1, deadline=None)
    baseline_size = len(base[v])
    budget = cr._Budget(work_limit, None)
    best_size = len(embedding[v])
    best_rank = None
    best_chain = None
    scanned = 0
    start = time.perf_counter()
    for index, root in enumerate(roots[:root_limit]):
        if not budget.check():
            break
        chain = cr._grow(root, region, masks, required, ctx, budget, cap,
                         reverse=bool(index % 2))
        scanned += 1
        if chain is not None and len(chain) < best_size:
            trial = dict(embedding)
            trial[v] = sorted(chain)
            independently_valid(trial, source, target)
            best_size = len(chain)
            best_rank = index + 1
            best_chain = sorted(chain)
    exact_chain, exact_tests, exact_depth = exact_short_tree(
        region, masks, required, ctx, min(cap, best_size - 1))
    witness_trials = []
    if exact_chain is not None:
        trial = dict(embedding)
        trial[v] = sorted(exact_chain)
        independently_valid(trial, source, target)
        for root in sorted(exact_chain):
            for reverse in (False, True):
                route = cr._grow(root, region, masks, required, ctx,
                                 cr._Budget(work_limit, None), cap, reverse=reverse)
                if route is not None:
                    trial = dict(embedding)
                    trial[v] = sorted(route)
                    independently_valid(trial, source, target)
                witness_trials.append({"root": root, "rank": roots.index(root) + 1,
                                       "reverse": reverse,
                                       "chain": sorted(route) if route is not None else None})
    return {"vertex": v, "old_size": len(embedding[v]),
            "baseline_size": baseline_size, "scan_size": best_size,
            "best_root_rank": best_rank, "best_chain": best_chain,
            "roots_scanned": scanned, "available_roots": len(roots),
            "baseline_expansions": info["expansions"],
            "scan_expansions": budget.expansions,
            "scan_stopped_by": budget.stopped_by,
            "exact_size": len(exact_chain) if exact_chain is not None else None,
            "exact_chain": sorted(exact_chain) if exact_chain is not None else None,
            "exact_sets_tested": exact_tests, "exact_depth": exact_depth,
            "exact_witness_root_trials": witness_trials,
            "scan_wall": time.perf_counter() - start}


def analyze(record, source, target, group_limit, root_vertices, root_limit, work_limit):
    embedding = {int(v): list(c) for v, c in record["embedding"].items()}
    independently_valid(embedding, source, target)
    ctx = cr._Context(source, target)
    all_groups = cr._groups(embedding, ctx, (2, 3, 4), 100000)
    groups = all_groups[:group_limit]
    cost_order = sorted(source, key=lambda v: (
        -(len(embedding[v]) - ctx.lower_bound(v)), -len(embedding[v]), v))
    owner = {q: v for v, c in embedding.items() for q in c}
    candidate_pairs = {frozenset((v, w)) for v, w in source.edges()}
    candidate_pairs.update(frozenset((owner[q], owner[r])) for q in owner
                           for r in ctx.adj[q] if r in owner and owner[r] != owner[q])
    positive_gap = {v for v in source if len(embedding[v]) > ctx.lower_bound(v)}
    covered64 = set().union(*(set(g) for g in all_groups[:64])) if all_groups else set()
    row = {"graph": record["graph"], "task_id": record["task_id"],
           "source_hash": record["source_hash"], "seed": record["seed"],
           "input_source_snapshot": record.get("source_snapshot"),
           "initial_qubits": sum(map(len, embedding.values())),
           "degree_bound_sum": sum(ctx.lower_bound(v) for v in source),
           "positive_bound_gap_vertices": len(positive_gap),
           "positive_gap_covered_by_first64": len(positive_gap & covered64),
           "selected_groups_total": len(all_groups),
           "selected_pairs_total": sum(len(g) == 2 for g in all_groups),
           "physical_or_logical_pairs": len(candidate_pairs),
           "fixed_groups": [list(g) for g in groups], "controls": {},
           "root_probes": [], "omitted_pairs": []}
    controls = {
        "base": {}, "beam1": {"beam_width": 1}, "beam8": {"beam_width": 8},
        "routes8": {"alternatives": 8}, "region1024": {"max_region": 1024},
        "halo3_region1024": {"halo": 3, "max_region": 1024},
        "routes8_roots9": {"alternatives": 8},
    }
    for name, change in controls.items():
        options = dict(beam_width=4, alternatives=3, halo=2, max_region=512,
                       max_expansions=work_limit, max_orders=2, deadline=None)
        options.update(change)
        outcomes = []
        for group in groups:
            if name == "routes8_roots9":
                with root_attempt_cap(9):
                    output, info = cr._repair(embedding, ctx, group, **options)
            else:
                output, info = cr._repair(embedding, ctx, group, **options)
            independently_valid(output, source, target)
            outcomes.append({"group": list(group), **{
                key: info[key] for key in ("qubits_saved", "member_growth", "expansions",
                    "tree_attempts", "beam_expansions", "beam_pruned", "region_size",
                    "unreachable_contacts", "stopped_by", "wall")}})
        row["controls"][name] = outcomes
    for v in cost_order[:root_vertices]:
        probe = root_probe(v, embedding, source, target, ctx, root_limit, work_limit)
        if probe is not None:
            row["root_probes"].append(probe)
    selected_pairs = {frozenset(g) for g in all_groups if len(g) == 2}
    excess = {v: len(embedding[v]) - ctx.lower_bound(v) for v in source}
    omitted = sorted(candidate_pairs - selected_pairs, key=lambda pair: (
        -sum(excess[v] for v in pair), tuple(sorted(pair))))[:group_limit]
    singleton_cache = {}
    for pair in omitted:
        group = tuple(sorted(pair))
        output, info = cr._repair(
            embedding, ctx, group, beam_width=4, alternatives=3, halo=2,
            max_region=512, max_expansions=work_limit, max_orders=2, deadline=None)
        independently_valid(output, source, target)
        for v in group:
            if v not in singleton_cache:
                single, single_info = cr._repair(
                    embedding, ctx, (v,), beam_width=4, alternatives=3, halo=2,
                    max_region=512, max_expansions=work_limit, max_orders=1, deadline=None)
                independently_valid(single, source, target)
                singleton_cache[v] = single_info["qubits_saved"]
        row["omitted_pairs"].append({
            "group": list(group), "qubits_saved": info["qubits_saved"],
            "singleton_savings": [singleton_cache[v] for v in group],
            "member_growth": info["member_growth"], "expansions": info["expansions"],
            "wall": info["wall"], "stopped_by": info["stopped_by"]})
    row["global_singletons"] = global_singleton_probes(embedding, source, target, ctx)
    return row


def report(rows, run, args, wall, raw_sha256):
    lines = ["# Experiment 013: contact reconstruction opportunity diagnostics", "",
             "Design diagnostics only. No algorithm source changed; no MM embeddings were inputs.",
             "The probe selects only valid `native-search` rows from the fixed development run.", "",
             f"Input run: `{run}`. Total diagnostic wall: {wall:.2f} s.",
             f"Fixed groups per incumbent: up to {args.groups}; tree/BFS work cap per move: {args.work}.",
             f"Singleton root probes: up to {args.root_vertices} vertices and {args.roots} roots each.", "",
             "Every control starts from the same saved incumbent and exactly the same groups.",
             "Group savings are independent alternative proposals: they must not be added into a claimed final ACL.",
             "Extra-root scans use the existing tree builder and independently validate every shortening.", "",
             "## Controls on the same groups", "",
             "Counts show improved groups / tested groups, then largest individual qubit saving, total BFS expansions, and summed move time.", "",
             "`routes8` allows up to 24 root attempts and 8 distinct generated trees per prefix; `routes8_roots9` keeps the original 9-root ceiling while retaining up to 8 trees.",
             "The root-ceiling control suppresses surplus `_grow` calls in this script; it restores the original helper after each move. Algorithm files are unchanged.", "",
             "| Source | Control | Improved / tested | Max saving | Growing-member proposals | BFS expansions | Move time s | Region-cap hits |",
             "|---|---|---:|---:|---:|---:|---:|---:|"]
    for row in rows:
        for name, values in row["controls"].items():
            cap = 1024 if "1024" in name else 512
            lines.append(f"| {row['graph']} | {name} | "
                         f"{sum(v['qubits_saved']>0 for v in values)}/{len(values)} | "
                         f"{max((v['qubits_saved'] for v in values),default=0)} | "
                         f"{sum(v['member_growth']>0 for v in values)} | "
                         f"{sum(v['expansions'] for v in values)} | "
                         f"{sum(v['wall'] for v in values):.4f} | "
                         f"{sum(v['region_size']==cap for v in values)} |")
    lines.extend(["", "## Coverage and lower-bound gap", "",
                  "The degree bound is a necessary individual-chain bound, not an attainable embedding objective.", "",
                  "| Source | Incumbent Q | Sum degree bound | Positive-gap vertices | Covered by first 64 groups | Selected pairs / logical-or-physical pairs |",
                  "|---|---:|---:|---:|---:|---:|"])
    for row in rows:
        lines.append(f"| {row['graph']} | {row['initial_qubits']} | {row['degree_bound_sum']} | "
                     f"{row['positive_bound_gap_vertices']} | {row['positive_gap_covered_by_first64']} | "
                     f"{row['selected_pairs_total']}/{row['physical_or_logical_pairs']} |")
    lines.extend(["", "## Extra-root opportunity probes", "",
                  "Only rows where scanning more roots improves upon the default singleton search appear here. Absence is not proof of no opportunity.", "",
                  "| Source | Vertex | Old length | Default singleton | Extra-root result | Best root rank | Roots scanned / available | Expansions |",
                  "|---|---:|---:|---:|---:|---:|---:|---:|"])
    for row in rows:
        for p in row["root_probes"]:
            if p["scan_size"] < p["baseline_size"]:
                lines.append(f"| {row['graph']} | {p['vertex']} | {p['old_size']} | {p['baseline_size']} | "
                             f"{p['scan_size']} | {p['best_root_rank']} | "
                             f"{p['roots_scanned']}/{p['available_roots']} | {p['scan_expansions']} |")
    lines.extend(["", "## Exact small singleton check", "",
                  "On the same root-probe vertices and halo-2 region, enumerate connected singleton, pair, and triple sets smaller than the scan result.",
                  "This is a diagnostic certificate within a fixed region, not an embedding constructor or a global lower bound.", "",
                  "| Source | Probed vertices | Extra-root improvements | Exact additional improvements | Connected sets tested | No shorter tree certified in region |",
                  "|---|---:|---:|---:|---:|---:|"])
    for row in rows:
        probes = row["root_probes"]
        lines.append(f"| {row['graph']} | {len(probes)} | "
                     f"{sum(p['scan_size'] < p['baseline_size'] for p in probes)} | "
                     f"{sum(p['exact_size'] is not None for p in probes)} | "
                     f"{sum(p['exact_sets_tested'] for p in probes)} | "
                     f"{sum(p['exact_size'] is None and p['exact_depth'] >= p['scan_size']-1 for p in probes)} |")
    lines.extend(["", "## Omitted pair probes", "",
                  "Probe up to eight logical-or-physical adjacent pairs absent from the entire default pair list, ranked by total degree-bound excess and then labels.",
                  "The final column compares each independent pair move with the sum of two independent singleton gains; it is not a proof that every possible singleton route fails.", "",
                  "| Source | Improving omitted pairs / tested | Max saving | Pair exceeds independent singleton savings | BFS expansions | Move time s |",
                  "|---|---:|---:|---:|---:|---:|"])
    for row in rows:
        pairs = row["omitted_pairs"]
        lines.append(f"| {row['graph']} | {sum(p['qubits_saved'] > 0 for p in pairs)}/{len(pairs)} | "
                     f"{max((p['qubits_saved'] for p in pairs), default=0)} | "
                     f"{sum(p['qubits_saved'] > sum(p['singleton_savings']) for p in pairs)} | "
                     f"{sum(p['expansions'] for p in pairs)} | {sum(p['wall'] for p in pairs):.4f} |")
    lines.extend(["", "## Singleton sites anywhere in the supplied target", "",
                  "For every non-singleton source chain, intersect the physical boundaries of all frozen logical neighbors, then exclude frozen occupied qubits.",
                  "All remaining sites are enumerated, including the released old chain, and every proposed one-qubit replacement is independently validated.",
                  "Compare membership in the default singleton halo-2 region capped at 512 qubits. Counts refer to independent moves on the original incumbent.", "",
                  "| Source | Non-singleton chains | With any singleton site | With site outside region | With sites only outside region | Valid sites | Diagnostic time s |",
                  "|---|---:|---:|---:|---:|---:|---:|"])
    for row in rows:
        probes = row["global_singletons"]["probes"]
        lines.append(f"| {row['graph']} | {len(probes)} | "
                     f"{sum(bool(p['sites']) for p in probes)} | "
                     f"{sum(bool(p['sites_outside_region']) for p in probes)} | "
                     f"{sum(bool(p['sites']) and not p['sites_in_region'] for p in probes)} | "
                     f"{sum(len(p['sites']) for p in probes)} | {row['global_singletons']['wall']:.4f} |")
    lines.extend(["", "## Reproduction and raw records", "",
                  "```sh", f".venv/codex-native/bin/python scripts/codex/contact_diagnostics.py --run {run} "
                  f"--groups {args.groups} --root-vertices {args.root_vertices} --roots {args.roots} --work {args.work} "
                  "--raw-output /tmp/013_contact_diagnostics.rerun.json",
                  "```", "",
                  f"Complete raw records: [{args.raw_output.name}]({args.raw_output.resolve()}).",
                  f"SHA256: `{raw_sha256}`.", ""])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, default=Path("results/codex/009-first-development-screen"))
    parser.add_argument("--groups", type=int, default=8)
    parser.add_argument("--root-vertices", type=int, default=8)
    parser.add_argument("--roots", type=int, default=64)
    parser.add_argument("--work", type=int, default=20000)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--raw-output", type=Path,
                        default=Path("notes/codex/experiments/data/013_contact_diagnostics.json"))
    args = parser.parse_args()
    target, target_record = read_graph(args.run / "target.json")
    manifest = json.loads((args.run / "manifest.json").read_text())
    assert digest(target_record) == manifest["target_hash"]
    # Filter before accessing the embedding. Comparator embeddings are not used.
    records = []
    for path in sorted((args.run / "worker_results").glob("*.json")):
        record = json.loads(path.read_text())
        if record.get("method") == "native-search" and record.get("status") == "SUCCESS":
            records.append(record)
    rows = []
    start = time.perf_counter()
    for record in sorted(records, key=lambda r: (r["graph"], r["seed"])):
        source, source_record = read_graph(args.run / "graphs" / f"{record['graph']}.json")
        assert digest(source_record) == record["source_hash"]
        assert record["target_hash"] == manifest["target_hash"]
        row = analyze(record, source, target, args.groups, args.root_vertices, args.roots, args.work)
        rows.append(row)
        print(json.dumps({"graph": row["graph"], "controls": {
            k: {"improved": sum(x["qubits_saved"] > 0 for x in v),
                "max_gain": max((x["qubits_saved"] for x in v), default=0),
                "expansions": sum(x["expansions"] for x in v)}
            for k, v in row["controls"].items()},
            "extra_root_wins": sum(p["scan_size"] < p["baseline_size"]
                                   for p in row["root_probes"]),
            "global_singleton_chains": sum(bool(p["sites"]) for p in row["global_singletons"]["probes"]),
            "outside_only_singleton_chains": sum(bool(p["sites"]) and not p["sites_in_region"]
                                                 for p in row["global_singletons"]["probes"])}), flush=True)
    wall = time.perf_counter() - start
    payload = {"contact_source_sha256": hashlib.sha256(Path(cr.__file__).read_bytes()).hexdigest(),
               "python": sys.executable, "prefix": sys.prefix,
               "mm_available": importlib.util.find_spec("minorminer") is not None,
               "rows": rows}
    encoded = (json.dumps(payload, indent=2) + "\n").encode()
    args.raw_output.parent.mkdir(parents=True, exist_ok=True)
    args.raw_output.write_bytes(encoded)
    text = report(rows, args.run, args, wall, hashlib.sha256(encoded).hexdigest())
    if args.output:
        args.output.write_text(text)
        print(f"Wrote {args.output}", flush=True)
    else:
        print(text)


if __name__ == "__main__":
    main()
