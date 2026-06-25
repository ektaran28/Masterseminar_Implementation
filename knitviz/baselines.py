"""Comparison algorithms (Section 6.1).

* ``knit_grid_layout`` -- the grid placement of Counts ("KnitGrid"): every
  stitch is dropped on its (column, -row) grid point.  Fast and simple, but it
  can introduce crossings and cannot represent every technique.
* ``sfdp_layout`` -- Graphviz SFDP [25], a scalable force-directed placement
  with prism overlap removal.  High quality but does not avoid crossings.
* ``kamada_kawai_layout`` -- a classic stress/force-directed embedder that also
  targets edge lengths but ignores planarity (a stand-in for the family of
  force-directed methods discussed in the paper).

ImPrEd [34] is described in the paper but relies on Tulip, which is not part of
this Python environment; it is therefore reported as "not available" rather
than approximated.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

import networkx as nx
import numpy as np

from .layout import _scale_to_targets


def knit_grid_layout(g: nx.Graph) -> dict:
    pos = {
        node: np.array([data["col"], -float(data["row"])], dtype=float)
        for node, data in g.nodes(data=True)
    }
    return _scale_to_targets(g, pos)


def kamada_kawai_layout(g: nx.Graph) -> dict:
    # use the pre-specified edge lengths as target distances
    dist = dict(nx.all_pairs_dijkstra_path_length(g, weight="length"))
    pos = nx.kamada_kawai_layout(g, dist=dist, weight="length")
    return _scale_to_targets(g, {n: np.asarray(p, float) for n, p in pos.items()})


def sfdp_available() -> bool:
    return shutil.which("sfdp") is not None


def sfdp_layout(g: nx.Graph) -> dict:
    if not sfdp_available():
        raise RuntimeError("Graphviz 'sfdp' executable not found")
    nodes = list(g.nodes())
    with tempfile.TemporaryDirectory() as tmp:
        dot = Path(tmp) / "g.dot"
        with dot.open("w", encoding="utf-8") as fh:
            fh.write("graph G {\n  graph [overlap=\"prism\"];\n")
            for node in nodes:
                fh.write(f'  "{node}";\n')
            for u, v, data in g.edges(data=True):
                fh.write(f'  "{u}" -- "{v}" [len="{float(data.get("length", 1.0)):.5f}"];\n')
            fh.write("}\n")
        out = subprocess.run(
            ["sfdp", "-Tplain", str(dot)],
            check=True, capture_output=True, text=True,
        ).stdout

    pos: dict = {}
    for line in out.splitlines():
        parts = line.split()
        if parts and parts[0] == "node":
            pos[int(parts[1].strip('"'))] = np.array([float(parts[2]), float(parts[3])])
    if len(pos) != g.number_of_nodes():
        raise RuntimeError("could not parse all node positions from sfdp output")
    return _scale_to_targets(g, pos)
