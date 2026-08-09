from __future__ import annotations

import time

from knitviz import (
    graph_from_pattern, build_graph, summary,
    knit_layout, planar_layout, knitting_layout,
    desired_edge_length, count_crossings, patterns,
)
from knitviz.graph_model import has_creation_hamiltonian_path
from knitviz.stitches import STITCHES


def _del_cross(g, pos):
    return desired_edge_length(g, pos), count_crossings(g, pos)


def init_ablation():
    print("\n=== Initialisation ablation (DEL after 300 safe FDA iters) ===")
    print(f"{'pattern':16s} {'planar-init':>22s} {'knitting-init':>22s}")
    for name, pat in patterns.library().items():
        g = graph_from_pattern(pat)
        a = knit_layout(g, iterations=300, seed=0, initial=planar_layout(g))
        b = knit_layout(g, iterations=300, seed=0, initial=knitting_layout(g))
        da, ca = _del_cross(g, a)
        db, cb = _del_cross(g, b)
        print(f"{name:16s} {f'DEL={da:.3f} cr={ca}':>22s} {f'DEL={db:.3f} cr={cb}':>22s}")


def convergence_study():
    print("\n=== Convergence: DEL vs. iterations (antique_diamonds) ===")
    g = graph_from_pattern(patterns.antique_diamonds(12, 19))
    for iters in (0, 50, 100, 200, 400, 800):
        if iters == 0:
            pos = knitting_layout(g)
        else:
            pos = knit_layout(g, iterations=iters, seed=0)
        d, c = _del_cross(g, pos)
        print(f"  iters={iters:4d}  DEL={d:.3f}  crossings={c}")


def force_ablation():
    print("\n=== Force ablation (antique_diamonds, 300 iters) ===")
    g = graph_from_pattern(patterns.antique_diamonds(12, 19))
    configs = {
        "all forces": {},
        "no collision": {"collision_strength": 0.0},
        "no universal repulsion": {"repulsion": 0.0},
        "edge-length force only": {"collision_strength": 0.0, "repulsion": 0.0},
    }
    for label, kw in configs.items():
        pos = knit_layout(g, iterations=300, seed=0, **kw)
        d, c = _del_cross(g, pos)
        print(f"  {label:24s} DEL={d:.3f}  crossings={c}")


def model_checks():
    print("\n=== Graph-model unit checks (Table 1 + knittability) ===")
    print("  (expected loop-edges per stitch = add x below)")
    # Work one isolated test stitch into a row of plain *purl* so the stitch
    # under test is identifiable even when it is itself a knit.
    for token, spec in STITCHES.items():
        if token in {"co", "c1b", "c2b"}:
            continue
        cast = max(4, spec.below + 2)
        fill = "k" if token != "k" else "p"  # filler must differ from the test stitch
        base = [fill] * cast
        # a worked row: fillers, then the single test stitch, then one filler
        consumed_after = cast - spec.below - 1
        row = [fill] * consumed_after + [token] + [fill] * 1
        try:
            g = build_graph(cast, [base, row])
        except ValueError:
            row = [fill] * (cast - spec.below) + [token]
            g = build_graph(cast, [base, row])

        added_nodes = [n for n, d in g.nodes(data=True) if d["stitch"] == token]
        added = len(added_nodes)
        loops = sum(
            1 for u, v, d in g.edges(data=True)
            if d["kind"] == "loop" and (u in added_nodes or v in added_nodes)
        )
        exp_loops = spec.add * spec.below
        ok = (added == spec.add) and (loops == exp_loops)
        print(f"  {token:12s} add={added}/{spec.add}  loop-edges={loops}/{exp_loops}  "
              f"{'OK' if ok else 'MISMATCH'}")

    print("\n  planarity + Hamiltonian creation path:")
    for name, pat in patterns.library().items():
        g = graph_from_pattern(pat)
        s = summary(g)
        print(f"    {name:16s} planar={s['planar']}  "
              f"hamiltonian={has_creation_hamiltonian_path(g)}")


if __name__ == "__main__":
    t = time.perf_counter()
    model_checks()
    convergence_study()
    force_ablation()
    init_ablation()
    print(f"\nTotal {time.perf_counter() - t:.1f}s")
