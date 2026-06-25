"""Algorithm 1 -- converting a knitting pattern into a graph.

The graph has one node per stitch and two kinds of edges (Section 3 / Fig. 2):

* **yarn** edges connect stitches that are sequential along the needle
  (adjacent in a row, and the row-to-row transition along the creation path);
* **loop** edges connect a stitch to the loop(s) below it that it is pulled
  through.

Following the paper, every edge carries a *pre-specified length*: yarn edges
get the (short) row length and loop edges the (long) column length, scaled by
the per-stitch factors in the dictionary (e.g. dropped stitches stretch the
yarn edge).

The pseudocode in the paper keeps the live stitches on a single ``Stack``.
Flat knitting turns the work over at the end of every row, so the live
stitches are consumed in reverse order on the next row.  We model this exactly
with a left needle (current live stitches) that is consumed in reverse and a
right needle that collects the new stitches; swapping them at the row boundary
reproduces the stack/LIFO behaviour of the pseudocode while keeping the row
structure that real patterns are written in.
"""

from __future__ import annotations

import networkx as nx
import numpy as np

from .patterns import Pattern, parse_pattern
from .stitches import BASE_LOOP_LENGTH, BASE_YARN_LENGTH, STITCHES


def build_graph(
    cast_on: int,
    rows: list[list[str]],
    yarn_length: float = BASE_YARN_LENGTH,
    loop_length: float = BASE_LOOP_LENGTH,
) -> nx.Graph:
    """Algorithm 1: build the knitting graph from parsed rows."""
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
            spec = STITCHES[token]
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

            for a in range(spec.add):
                # spread multiple created loops (e.g. kfb) around the base col
                offset = (a - (spec.add - 1) / 2.0) * 0.4
                g.add_node(node, row=r, col=base_col + offset, stitch=token)
                if prev is not None:
                    g.add_edge(
                        prev, node, kind="yarn",
                        length=yarn_length * spec.yarn_factor,
                    )
                for lo in lower:
                    g.add_edge(
                        lo, node, kind="loop",
                        length=loop_length * spec.loop_factor,
                    )
                right.append(node)
                prev = node
                node += 1
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
    """The creation order 0,1,2,...,n-1 is a Hamiltonian path iff each
    consecutive pair is joined by a (yarn) edge -- i.e. there is a connected
    way to create every stitch."""
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
