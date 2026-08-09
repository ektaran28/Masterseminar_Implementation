from __future__ import annotations

import networkx as nx
import numpy as np


def _edge_arrays(g: nx.Graph):
    nodes = list(g.nodes())
    idx = {n: i for i, n in enumerate(nodes)}
    edges = list(g.edges(data=True))
    a = np.fromiter((idx[u] for u, _, _ in edges), dtype=int, count=len(edges))
    b = np.fromiter((idx[v] for _, v, _ in edges), dtype=int, count=len(edges))
    lengths = np.array([d.get("length", 1.0) for _, _, d in edges], dtype=float)
    return nodes, idx, a, b, lengths


def _points(g: nx.Graph, pos: dict) -> np.ndarray:
    return np.array([pos[n] for n in g.nodes()], dtype=float)


def optimal_scale(distances: np.ndarray, lengths: np.ndarray) -> float:
    ratio = distances / lengths
    denom = float(np.sum(ratio * ratio))
    return float(np.sum(ratio) / denom) if denom > 0 else 1.0


def desired_edge_length(g: nx.Graph, pos: dict) -> float:
    _, _, a, b, lengths = _edge_arrays(g)
    pts = _points(g, pos)
    d = np.linalg.norm(pts[a] - pts[b], axis=1)
    s = optimal_scale(d, lengths)
    rel = (s * d - lengths) / lengths
    return float(np.sqrt(np.mean(rel * rel)))


# Shared orientation epsilon: the safe-step crossing test (layout.py) and this
# counter MUST use the same threshold, otherwise a move accepted as "safe" can
# be flagged here as a crossing.
CROSS_EPS = 1e-7


def _segments_cross(p, q, r, s) -> bool:
    def orient(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    o1, o2 = orient(p, q, r), orient(p, q, s)
    o3, o4 = orient(r, s, p), orient(r, s, q)
    return (o1 > CROSS_EPS) != (o2 > CROSS_EPS) and (o3 > CROSS_EPS) != (o4 > CROSS_EPS)


def _edge_key(u, v) -> tuple:
    return (u, v) if u <= v else (v, u)


def required_crossings(g: nx.Graph) -> set[frozenset[tuple]]:
    return {
        frozenset(signature["edges"])
        for signature in g.graph.get("crossing_signature", [])
    }


def crossing_report(g: nx.Graph, pos: dict) -> dict[str, int]:
    edges = list(g.edges())
    actual: set[frozenset[tuple]] = set()
    for i, (u1, v1) in enumerate(edges):
        for u2, v2 in edges[i + 1:]:
            if {u1, v1}.isdisjoint((u2, v2)) and _segments_cross(
                pos[u1], pos[v1], pos[u2], pos[v2]
            ):
                actual.add(frozenset((_edge_key(u1, v1), _edge_key(u2, v2))))
    required = required_crossings(g)
    signature_rows = {
        frozenset(signature["edges"]): signature["row"]
        for signature in g.graph.get("crossing_signature", [])
    }
    misplaced = 0
    for pair in actual & required:
        row = signature_rows[pair]
        for edge in pair:
            if {g.nodes[edge[0]]["row"], g.nodes[edge[1]]["row"]} != {row - 1, row}:
                misplaced += 1
                break
    return {
        "crossings": len(actual),
        "required": len(required),
        "missing": len(required - actual),
        "unexpected": len(actual - required),
        "misplaced": misplaced,
    }


def count_crossings(g: nx.Graph, pos: dict) -> int:
    edges = list(g.edges())
    n = len(edges)
    count = 0
    for i in range(n):
        u1, v1 = edges[i]
        p, q = pos[u1], pos[v1]
        ends = (u1, v1)
        for j in range(i + 1, n):
            u2, v2 = edges[j]
            if u2 in ends or v2 in ends:
                continue
            if _segments_cross(p, q, pos[u2], pos[v2]):
                count += 1
    return count
