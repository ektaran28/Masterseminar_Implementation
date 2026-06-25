"""knitviz -- a faithful implementation of

    Gray, Bell & Kobourov, "A Graph Model and a Layout Algorithm for
    Knitting Patterns" (GD 2024, arXiv:2406.13800).

Modules:
    stitches     -- stitch dictionary (Table 1)
    patterns     -- pattern parser and a small pattern library
    graph_model  -- Algorithm 1 (pattern -> graph)
    layout       -- Algorithm 2 (KnitLayout: planar init + safe FDA)
    baselines    -- comparison methods (KnitGrid, SFDP, Kamada-Kawai)
    metrics      -- DEL (Eq. 1) and crossing count
    draw         -- visualisation helpers
"""

from .graph_model import build_graph, graph_from_pattern, summary
from .layout import knit_layout, planar_layout, knitting_layout
from .baselines import knit_grid_layout, sfdp_layout, kamada_kawai_layout, sfdp_available
from .metrics import desired_edge_length, count_crossings
from . import patterns

__all__ = [
    "build_graph", "graph_from_pattern", "summary",
    "knit_layout", "planar_layout", "knitting_layout",
    "knit_grid_layout", "sfdp_layout", "kamada_kawai_layout", "sfdp_available",
    "desired_edge_length", "count_crossings",
    "patterns",
]
