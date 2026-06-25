"""Reproduce the evaluation of Gray, Bell & Kobourov (2024).

Two experiments mirror Section 6:

* **Experiment A -- mixed patterns** (Tables 3 & 5): a set of class-0 knitting
  patterns of various sizes laid out by every algorithm, reporting DEL,
  crossings and runtime.
* **Experiment B -- triangle scaling** (Tables 4 & 6): one simple pattern (a
  triangle shawl) whose size grows, used to study how runtime and quality
  scale with the number of stitches.

Outputs (CSV / JSON / Markdown tables and PNG figures) are written to
``results/``.

Usage:
    python experiments.py --mode quick     # small, ~1-2 minutes
    python experiments.py --mode full      # paper-scale, several minutes
"""

from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path

import networkx as nx

from knitviz import (
    graph_from_pattern,
    summary,
    knit_layout,
    knitting_layout,
    planar_layout,
    knit_grid_layout,
    sfdp_layout,
    kamada_kawai_layout,
    sfdp_available,
    desired_edge_length,
    count_crossings,
    patterns,
)
from knitviz.draw import compare_figure

RESULTS = Path("results")
FIGS = RESULTS / "figures"


def algorithms(iterations: int):
    """The layout methods under comparison (Section 6.1)."""
    algos = {
        "KnitLayout": lambda g: knit_layout(g, iterations=iterations, seed=0),
        "KnitGrid": knit_grid_layout,                 # Counts [8]
        "Kamada-Kawai": kamada_kawai_layout,          # classic force-directed
    }
    if sfdp_available():
        algos["SFDP"] = sfdp_layout                   # Graphviz [25]
    return algos


def evaluate(g: nx.Graph, name: str, iterations: int) -> dict:
    """Run every algorithm on one graph and collect metrics."""
    row_results = {}
    for label, fn in algorithms(iterations).items():
        t = time.perf_counter()
        try:
            pos = fn(g)
            row_results[label] = {
                "pos": pos,
                "del": desired_edge_length(g, pos),
                "crossings": count_crossings(g, pos),
                "time": time.perf_counter() - t,
                "status": "ok",
            }
        except Exception as exc:  # noqa: BLE001 -- record DNF like the paper
            row_results[label] = {
                "pos": None, "del": None, "crossings": None,
                "time": None, "status": f"DNF: {exc}",
            }
    return row_results


def case_rows(case: str, g: nx.Graph, results: dict) -> list[dict]:
    s = summary(g)
    rows = []
    for label, r in results.items():
        rows.append({
            "experiment": case,
            "pattern": s["name"],
            "family": s["family"],
            "nodes": s["nodes"],
            "edges": s["edges"],
            "planar": s["planar"],
            "algorithm": label,
            "del": "" if r["del"] is None else round(r["del"], 4),
            "crossings": "" if r["crossings"] is None else r["crossings"],
            "runtime_s": "" if r["time"] is None else round(r["time"], 3),
            "status": r["status"],
        })
    return rows


def experiment_a(iterations: int, draw: bool) -> list[dict]:
    print("\n=== Experiment A: mixed knitting patterns ===")
    lib = patterns.library()
    all_rows: list[dict] = []
    for name, pat in lib.items():
        g = graph_from_pattern(pat)
        s = summary(g)
        print(f"\n{name}: {s['nodes']} nodes, {s['edges']} edges, "
              f"planar={s['planar']}, hamiltonian={s['hamiltonian_creation_path']}")
        results = evaluate(g, name, iterations)
        for label, r in results.items():
            if r["status"] == "ok":
                print(f"  {label:14s} DEL={r['del']:.3f}  crossings={r['crossings']:<3d} "
                      f"{r['time']:.2f}s")
            else:
                print(f"  {label:14s} {r['status']}")
        all_rows.extend(case_rows("A_mixed", g, results))
        if draw:
            compare_figure(g, results, FIGS / f"A_{name}.png", suptitle=name)
    return all_rows


def experiment_b(iterations: int, sizes: list[int], draw: bool) -> list[dict]:
    print("\n=== Experiment B: triangle scaling ===")
    all_rows: list[dict] = []
    # A scaling study must hold the iteration count fixed so that the only
    # variable is the graph size; otherwise runtime is not comparable.
    iters = min(iterations, 200)
    for rows in sizes:
        pat = patterns.triangle(rows, cast_on=5)
        g = graph_from_pattern(pat)
        s = summary(g)
        print(f"\ntriangle {rows} rows: {s['nodes']} nodes, {s['edges']} edges "
              f"(iterations={iters})")
        results = evaluate(g, f"triangle_{rows}", iters)
        for label, r in results.items():
            if r["status"] == "ok":
                print(f"  {label:14s} DEL={r['del']:.3f}  crossings={r['crossings']:<3d} "
                      f"{r['time']:.2f}s")
            else:
                print(f"  {label:14s} {r['status']}")
        all_rows.extend(case_rows("B_triangle", g, results))
        if draw and rows in (sizes[0], sizes[-1]):
            compare_figure(g, results, FIGS / f"B_triangle_{rows}.png",
                           suptitle=f"triangle {rows} rows")
    return all_rows


def write_outputs(rows: list[dict]) -> None:
    RESULTS.mkdir(exist_ok=True)
    fields = list(rows[0].keys())
    with (RESULTS / "results.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    (RESULTS / "results.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    _write_markdown(rows)
    print(f"\nWrote results.csv, results.json, results.md and figures to {RESULTS}/")


def _pivot(rows, experiment, value_key, algos):
    """Build a {pattern: {algo: value}} pivot for one experiment."""
    table: dict[str, dict] = {}
    meta: dict[str, tuple] = {}
    for r in rows:
        if r["experiment"] != experiment:
            continue
        table.setdefault(r["pattern"], {})[r["algorithm"]] = r[value_key]
        meta[r["pattern"]] = (r["nodes"], r["edges"])
    return table, meta


def _md_table(title, table, meta, algos):
    lines = [f"### {title}", "",
             "| Pattern | Nodes | " + " | ".join(algos) + " |",
             "|---|---:|" + "|".join(["---:"] * len(algos)) + "|"]
    for pat, vals in table.items():
        cells = []
        for a in algos:
            v = vals.get(a, "")
            cells.append("DNF" if v == "" else str(v))
        lines.append(f"| {pat} | {meta[pat][0]} | " + " | ".join(cells) + " |")
    lines.append("")
    return lines


def _write_markdown(rows: list[dict]) -> None:
    algos = []
    for r in rows:
        if r["algorithm"] not in algos:
            algos.append(r["algorithm"])
    out = ["# Reproduced Evaluation Results",
           "",
           "Generated by `python experiments.py`. DEL is the desired-edge-length "
           "error of Eq. (1) (lower is better); crossings should be 0 for a valid "
           "knitting layout; runtime is wall-clock seconds.",
           ""]
    for exp, label in [("A_mixed", "Experiment A -- Mixed patterns"),
                       ("B_triangle", "Experiment B -- Triangle scaling")]:
        out.append(f"## {label}")
        out.append("")
        for value_key, vtitle in [("del", "DEL (edge-length error)"),
                                   ("crossings", "Edge crossings"),
                                   ("runtime_s", "Runtime (s)")]:
            table, meta = _pivot(rows, exp, value_key, algos)
            if table:
                out.extend(_md_table(vtitle, table, meta, algos))
    (RESULTS / "results.md").write_text("\n".join(out) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["quick", "full"], default="quick")
    ap.add_argument("--iterations", type=int, default=None)
    ap.add_argument("--no-draw", action="store_true")
    args = ap.parse_args()

    if not sfdp_available():
        print("NOTE: Graphviz 'sfdp' not found; SFDP comparison will be skipped.")

    if args.mode == "quick":
        iterations = args.iterations or 250
        sizes = [5, 11, 17, 23]
    else:
        iterations = args.iterations or 400
        sizes = [5, 11, 17, 23, 29, 35]

    rows = []
    rows += experiment_a(iterations, draw=not args.no_draw)
    rows += experiment_b(iterations, sizes, draw=not args.no_draw)
    write_outputs(rows)


if __name__ == "__main__":
    main()
