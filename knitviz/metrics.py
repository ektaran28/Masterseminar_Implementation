"""Evaluation metrics from Section 6.2.

* ``desired_edge_length`` implements the DEL measure of Eq. (1): the root mean
  square of the *relative* edge-length error.  Because the comparison methods
  (SFDP, Kamada-Kawai, the planar initialisation) do not know the absolute
  target scale, we first apply the single uniform scale factor that minimises
  the relative error -- this is the standard scale-invariant form of the
  measure and gives every algorithm its best possible score.
* ``count_crossings`` counts pairs of non-adjacent edges that properly cross.
"""

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
    """Scale s minimising sum((s*d - l)/l)^2  =>  s = sum(d/l) / sum((d/l)^2)."""
    ratio = distances / lengths
    denom = float(np.sum(ratio * ratio))
    return float(np.sum(ratio) / denom) if denom > 0 else 1.0


def desired_edge_length(g: nx.Graph, pos: dict) -> float:
    """DEL measure (Eq. 1).  Lower is better; 0 is perfect."""
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


def count_crossings(g: nx.Graph, pos: dict) -> int:
    """Number of properly crossing pairs of non-adjacent edges."""
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
