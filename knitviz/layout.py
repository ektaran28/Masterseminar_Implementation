from __future__ import annotations

import networkx as nx
import numpy as np

from .metrics import CROSS_EPS, _edge_arrays, crossing_report, optimal_scale, required_crossings


# --------------------------------------------------------------------------- #
# Stage 1: initial planar layout
# --------------------------------------------------------------------------- #
def planar_layout(g: nx.Graph) -> dict:
    ok, _ = nx.check_planarity(g)
    if not ok:
        raise ValueError("graph is not planar; KnitLayout requires a class-0 pattern")
    pos = nx.planar_layout(g)
    return _scale_to_targets(g, {n: np.asarray(p, float) for n, p in pos.items()})


def _scale_to_targets(g: nx.Graph, pos: dict) -> dict:
    nodes = list(g.nodes())
    pts = np.array([pos[n] for n in nodes], float)
    pts -= pts.mean(axis=0)
    _, _, a, b, lengths = _edge_arrays(g)
    d = np.linalg.norm(pts[a] - pts[b], axis=1)
    pts *= optimal_scale(d, lengths)
    return {n: pts[i] for i, n in enumerate(nodes)}


def knitting_layout(g: nx.Graph, loop_length: float = 1.4) -> dict:
    rows: dict[int, list] = {}
    for nd, data in g.nodes(data=True):
        rows.setdefault(data["row"], []).append(nd)

    x: dict = {}
    for i, nd in enumerate(sorted(rows[0])):
        x[nd] = float(i)

    for r in sorted(rows)[1:]:
        order = sorted(rows[r])
        lower_x = {}
        for nd in order:
            below = [m for m in g.neighbors(nd) if g.nodes[m]["row"] == r - 1]
            if below:
                lower_x[nd] = float(np.mean([x[m] for m in below]))

        anchored = [nd for nd in order if nd in lower_x]
        # Flat knitting turns over each row, so creation order may run right to
        # left; flip it so x increases left to right.
        if len(anchored) >= 2 and lower_x[anchored[0]] > lower_x[anchored[-1]]:
            order = order[::-1]

        xs = [lower_x.get(nd) for nd in order]
        for i, v in enumerate(xs):  # interpolate / extrapolate yarn-overs
            if v is None:
                prev = next((xs[j] for j in range(i - 1, -1, -1) if xs[j] is not None), None)
                nxt = next((xs[j] for j in range(i + 1, len(xs)) if xs[j] is not None), None)
                if prev is not None and nxt is not None:
                    xs[i] = (prev + nxt) / 2.0
                elif prev is not None:
                    xs[i] = prev + 1.0
                elif nxt is not None:
                    xs[i] = nxt - 1.0
                else:
                    xs[i] = float(i)
        for i in range(1, len(xs)):  # break ties to keep order strict
            if xs[i] <= xs[i - 1]:
                xs[i] = xs[i - 1] + 1e-3
        for nd, xv in zip(order, xs):
            x[nd] = xv

    pos = {nd: np.array([x[nd], -g.nodes[nd]["row"] * loop_length]) for nd in g.nodes()}
    return _scale_to_targets(g, pos)


def cable_layout(g: nx.Graph, loop_length: float = 1.4) -> dict:
    pos = {
        nd: np.array([data["col"], -data["row"] * loop_length])
        for nd, data in g.nodes(data=True)
    }
    pos = _scale_to_targets(g, pos)
    report = crossing_report(g, pos)
    if report["missing"] or report["unexpected"]:
        raise ValueError(f"cable signature is not realized by its initial layout: {report}")
    return pos


# --------------------------------------------------------------------------- #
# Stage 2: safe force-directed improvement
# --------------------------------------------------------------------------- #
def _build_incidence(g: nx.Graph, idx: dict, a: np.ndarray, b: np.ndarray):
    incident: list[list[int]] = [[] for _ in range(len(idx))]
    for e, (u, v) in enumerate(g.edges()):
        incident[idx[u]].append(e)
        incident[idx[v]].append(e)
    return [np.array(lst, dtype=int) for lst in incident]


def knit_layout(
    g: nx.Graph,
    iterations: int = 400,
    step: float = 0.08,
    edge_strength: float = 1.0,
    collision_distance: float = 0.7,
    collision_strength: float = 0.6,
    repulsion: float = 0.3,
    cooling: float = 0.99,
    initial: dict | None = None,
    seed: int | None = None,
) -> dict:
    nodes, idx, ea, eb, target = _edge_arrays(g)
    n = len(nodes)
    if initial is None:
        initial = cable_layout(g) if required_crossings(g) else knitting_layout(g)
    pts = np.array([initial[node] for node in nodes], dtype=float)
    incident = _build_incidence(g, idx, ea, eb)
    required = required_crossings(g)
    edge_keys = [frozenset(((min(u, v), max(u, v)))) for u, v in g.edges()]

    # characteristic length used by collision / repulsion forces
    L = float(np.mean(target))
    collide_d = collision_distance * L

    def move_is_safe(i: int, p: np.ndarray) -> bool:
        cx, cy = pts[ea, 0], pts[ea, 1]
        dx, dy = pts[eb, 0], pts[eb, 1]
        for e in incident[i]:
            iu, iv = ea[e], eb[e]
            ax, ay = (p if iu == i else pts[iu])
            bx, by = (p if iv == i else pts[iv])
            o1 = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
            o2 = (bx - ax) * (dy - ay) - (by - ay) * (dx - ax)
            o3 = (dx - cx) * (ay - cy) - (dy - cy) * (ax - cx)
            o4 = (dx - cx) * (by - cy) - (dy - cy) * (bx - cx)
            crosses = ((o1 > CROSS_EPS) != (o2 > CROSS_EPS)) & (
                (o3 > CROSS_EPS) != (o4 > CROSS_EPS)
            )
            shares = (ea == iu) | (eb == iu) | (ea == iv) | (eb == iv)
            expected = np.fromiter(
                (frozenset((edge_keys[e], edge_keys[f])) in required for f in range(len(ea))),
                dtype=bool,
                count=len(ea),
            )
            if np.any((crosses != expected) & ~shares):
                return False
        return True

    rng = np.random.default_rng(seed)
    order = np.arange(n)
    s = step

    for it in range(iterations):
        forces = np.zeros((n, 2))

        # (1) edge-length force: relative, attractive if too long.
        delta = pts[eb] - pts[ea]
        d = np.linalg.norm(delta, axis=1)
        d[d < 1e-9] = 1e-9
        unit = delta / d[:, None]
        mag = edge_strength * (d - target) / target
        ef = mag[:, None] * unit
        np.add.at(forces, ea, ef)
        np.add.at(forces, eb, -ef)

        # pairwise differences (O(n^2)) for collision + repulsion
        diff = pts[:, None, :] - pts[None, :, :]
        dist = np.linalg.norm(diff, axis=2)
        np.fill_diagonal(dist, np.inf)
        u = diff / dist[:, :, None]

        # (2) collision force: push apart pairs closer than collide_d
        overlap = np.clip(collide_d - dist, 0.0, None)
        forces += collision_strength * (overlap[:, :, None] * u).sum(axis=1)

        # (3) universal electrostatic repulsion, annealed towards 0
        anneal = repulsion * L * L * (1.0 - it / iterations)
        rep = anneal * u / (dist[:, :, None] ** 2)
        rep[~np.isfinite(rep)] = 0.0
        forces += rep.sum(axis=1)

        # clip extreme forces for stability
        fn = np.linalg.norm(forces, axis=1)
        cap = 5.0 * L
        big = fn > cap
        forces[big] *= (cap / fn[big])[:, None]

        proposals = pts + s * forces
        rng.shuffle(order)
        for i in order:
            if move_is_safe(i, proposals[i]):
                pts[i] = proposals[i]

        s *= cooling

    return _scale_to_targets(g, {node: pts[i] for i, node in enumerate(nodes)})
