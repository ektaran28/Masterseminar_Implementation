"""Stitch dictionary -- Table 1 of Gray, Bell & Kobourov (2024).

Each stitch is described by how many new loops it *creates* on the needle
(``add``) and how many loops *below* it consumes / connects to (``below``).
These two numbers fully determine the edges that Algorithm 1 adds to the graph:

* ``add`` new nodes are created and chained to the previous node with a
  *yarn* edge (the sequential "along the needle" connection);
* each new node is linked to every consumed lower node with a *loop* edge
  (the "pulled through" connection).

The paper also notes that stitches are generally taller than they are wide,
so we attach two base edge lengths: a (short) yarn/row length and a (long)
loop/column length.  Some stitches -- e.g. dropped stitches -- stretch the
yarn edge, which is captured by ``yarn_factor``.

Stitches whose graph contains crossings (cables) are *not* planar and belong
to complexity class >= 1 (Table 2); they are marked ``planar=False`` and are
excluded from the class-0 layout experiments.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Stitch:
    """One entry of the stitch dictionary."""

    name: str
    add: int           # number of new loops created on the needle
    below: int         # number of loops below that are connected / consumed
    planar: bool = True
    yarn_factor: float = 1.0   # multiplies the base yarn (row) edge length
    loop_factor: float = 1.0   # multiplies the base loop (column) edge length
    description: str = ""


# The class-0 stitch dictionary used throughout the planar experiments.
STITCHES: dict[str, Stitch] = {
    "co": Stitch("co", add=1, below=0, description="cast on"),
    "k": Stitch("k", add=1, below=1, description="knit"),
    "p": Stitch("p", add=1, below=1, description="purl"),
    "yo": Stitch("yo", add=1, below=0, description="yarn over (eyelet/hole)"),
    "kfb": Stitch("kfb", add=2, below=1, description="knit front and back (increase)"),
    "m1": Stitch("m1", add=1, below=0, description="make one (increase)"),
    "k2tog": Stitch("k2tog", add=1, below=2, description="knit two together (decrease)"),
    "ssk": Stitch("ssk", add=1, below=2, description="slip slip knit (decrease)"),
    "sl1-k2-psso": Stitch(
        "sl1-k2-psso", add=1, below=3, description="central double decrease"
    ),
    # A dropped stitch: a previously knit loop is let down, leaving a long
    # horizontal float of yarn between its neighbours (Fig. 7).  Topologically
    # it behaves like a knit, but the yarn edge is stretched.
    "drop": Stitch("drop", add=1, below=1, yarn_factor=3.0, description="dropped stitch"),
    # Cables -- class 1 (non-planar): edges acquire a front/back orientation.
    "c1b": Stitch("c1b", add=2, below=2, planar=False, description="cable one behind"),
    "c2b": Stitch("c2b", add=4, below=4, planar=False, description="cable two behind"),
}


# Base edge lengths.  Knit stitches are taller than wide, so the loop/column
# edge is longer than the yarn/row edge (Section 6).
BASE_YARN_LENGTH = 1.0
BASE_LOOP_LENGTH = 1.4


def is_known(token: str) -> bool:
    return token in STITCHES


def get(token: str) -> Stitch:
    if token not in STITCHES:
        raise KeyError(f"Unknown stitch token: {token!r}")
    return STITCHES[token]
