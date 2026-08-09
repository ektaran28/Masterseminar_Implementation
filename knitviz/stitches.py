from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Stitch:
    name: str
    add: int           # number of new loops created on the needle
    below: int         # number of loops below that are connected / consumed
    planar: bool = True
    yarn_factor: float = 1.0   # multiplies the base yarn (row) edge length
    loop_factor: float = 1.0   # multiplies the base loop (column) edge length
    description: str = ""
    cable_hold: int = 0        # held stitches in a class-1 cable
    cable_shift: int = 0       # left/right block permutation on the next row
    cable_front: bool = False  # held block passes in front instead of behind


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
    "c1b": Stitch("c1b", add=2, below=2, planar=False, description="cable one behind", cable_hold=1, cable_shift=1),
    "c2b": Stitch("c2b", add=4, below=4, planar=False, description="cable two behind", cable_hold=2, cable_shift=2),
    "c1f": Stitch("c1f", add=2, below=2, planar=False, description="cable one front", cable_hold=1, cable_shift=-1, cable_front=True),
    "c2f": Stitch("c2f", add=4, below=4, planar=False, description="cable two front", cable_hold=2, cable_shift=-2, cable_front=True),
}


# Base edge lengths.  Knit stitches are taller than wide, so the loop/column
# edge is longer than the yarn/row edge (Section 6).
BASE_YARN_LENGTH = 1.0
BASE_LOOP_LENGTH = 1.4


def is_known(token: str) -> bool:
    return token in STITCHES or bool(re.fullmatch(r"c[1-9]\d*[bf]", token))


def get(token: str) -> Stitch:
    if token in STITCHES:
        return STITCHES[token]
    match = re.fullmatch(r"c([1-9]\d*)([bf])", token)
    if not match:
        raise KeyError(f"Unknown stitch token: {token!r}")
    held, side = int(match.group(1)), match.group(2)
    return Stitch(
        token, add=2 * held, below=2 * held, planar=False,
        description=f"cable {held} {'front' if side == 'f' else 'behind'}",
        cable_hold=held, cable_shift=-held if side == "f" else held,
        cable_front=side == "f",
    )
