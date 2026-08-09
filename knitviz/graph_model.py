from __future__ import annotations

import networkx as nx
import numpy as np

from .patterns import Pattern, parse_pattern
from .stitches import BASE_LOOP_LENGTH, BASE_YARN_LENGTH, get


def _edge_key(u, v) -> tuple:
    return (u, v) if u <= v else (v, u)


def build_graph(
    cast_on: int,
    rows: list[list[str]],
    yarn_length: float = BASE_YARN_LENGTH,
    loop_length: float = BASE_LOOP_LENGTH,
) -> nx.Graph:
    g = nx.Graph()
    node = 0
    prev: int | None = None

    # --- cast-on row -------------------------------------------------------
    left: list[int] = []  # live stitches, in needle order
    for col in range(cast_on):
        g.add_node(node, row=0, col=float(col), stitch="co")
        if prev is not None:
            g.add_edge(prev, node, kind="yarn", length=yarn_length)
        left.append(node)
        prev = node
        node += 1

    # --- worked rows -------------------------------------------------------
    for r, row in enumerate(rows, start=1):
        right: list[int] = []
        # Each new row is worked from the opposite end: consume the left
        # needle from its far end (LIFO), matching the paper's stack.
        cursor = len(left)
        col_cursor = 0.0
        for token in row:
            spec = get(token)
            if cursor < spec.below:
                raise ValueError(
                    f"row {r}: stitch {token!r} needs {spec.below} live stitches, "
                    f"{cursor} remain"
                )
            lower = [left[cursor - 1 - k] for k in range(spec.below)]
            cursor -= spec.below

            if lower:
                base_col = float(np.mean([g.nodes[n]["col"] for n in lower]))
            else:
                base_col = col_cursor
            col_cursor = base_col + 1.0

            created: list[int] = []
            for a in range(spec.add):
                # spread multiple created loops (e.g. kfb) around the base col
                offset = (a - (spec.add - 1) / 2.0) * 0.4
                col = base_col + offset
                if spec.cable_hold:
                    # The top-row order stays fixed; the loop connections swap
                    # the held and worked blocks, creating the cable crossings.
                    col = float(g.nodes[list(reversed(lower))[::-1][a]]['col'])
                g.add_node(node, row=r, col=col, stitch=token)
                if prev is not None:
                    g.add_edge(
                        prev, node, kind="yarn",
                        length=yarn_length * spec.yarn_factor,
                    )
                if not spec.cable_hold:
                    for lo in lower:
                        g.add_edge(
                            lo, node, kind="loop",
                            length=loop_length * spec.loop_factor,
                        )
                right.append(node)
                created.append(node)
                prev = node
                node += 1
            if spec.cable_hold:
                lower_left_to_right = list(reversed(lower))
                strand_edges = []
                for a, nd in enumerate(created):
                    top_index = spec.add - 1 - a
                    lo = lower_left_to_right[(top_index + spec.cable_shift) % spec.below]
                    g.add_edge(lo, nd, kind="loop", length=loop_length * spec.loop_factor)
                    strand_edges.append(_edge_key(lo, nd))
                strand_edges.sort(key=lambda edge: g.nodes[edge[1]]['col'])
                event = {
                    "row": r,
                    "token": token,
                    "columns": (min(g.nodes[n]["col"] for n in lower),
                                max(g.nodes[n]["col"] for n in lower)),
                    "front": spec.cable_front,
                    "crossings": [],
                }
                for a, edge in enumerate(strand_edges):
                    for b in range(a + 1, len(strand_edges)):
                        if g.nodes[edge[0]]['col'] > g.nodes[strand_edges[b][0]]['col']:
                            signature = {
                                "edges": (edge, strand_edges[b]),
                                "over": edge if spec.cable_front else strand_edges[b],
                                "row": r,
                                "token": token,
                            }
                            g.graph.setdefault("crossing_signature", []).append(signature)
                            event["crossings"].append(signature["edges"])
                if event["crossings"]:
                    g.graph.setdefault("crossing_events", []).append(event)
        # turn the work over: the stitches just made become the live row.
        left = right

    return g


def graph_from_pattern(pattern: Pattern, **kwargs) -> nx.Graph:
    cast_on, rows = parse_pattern(pattern)
    g = build_graph(cast_on, rows, **kwargs)
    g.graph["name"] = pattern.name
    g.graph["family"] = pattern.family
    return g


# --------------------------------------------------------------------------- #
# Knittable-graph properties (Section 3.1)
# --------------------------------------------------------------------------- #
def has_creation_hamiltonian_path(g: nx.Graph) -> bool:
    nodes = sorted(g.nodes())
    return all(g.has_edge(nodes[i], nodes[i + 1]) for i in range(len(nodes) - 1))


def summary(g: nx.Graph) -> dict:
    is_planar, _ = nx.check_planarity(g)
    return {
        "name": g.graph.get("name", "?"),
        "family": g.graph.get("family", "?"),
        "nodes": g.number_of_nodes(),
        "edges": g.number_of_edges(),
        "planar": bool(is_planar),
        "hamiltonian_creation_path": has_creation_hamiltonian_path(g),
    }
