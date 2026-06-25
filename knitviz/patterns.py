"""Knitting-pattern text parser and a small library of test patterns.

A pattern is stored the way a knitter writes it: a cast-on count plus one
string per row, e.g. ``"k7, k2tog, yo, k1, yo, ssk, k7"``.  :func:`parse_row`
expands a row string into a flat list of stitch tokens, resolving repeats
(``(k2tog, yo) 3 times``) and the ``knit/purl to end`` shorthand against the
number of live stitches currently on the needle.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .stitches import STITCHES


@dataclass(frozen=True)
class Pattern:
    name: str
    cast_on: int
    rows: list[str]
    family: str = "misc"


_NORMALISE = [
    (r"k\s*2\s*tog", "k2tog"),
    (r"sl\s*1\s*,?\s*k2tog\s*,?\s*psso", "sl1-k2-psso"),
    (r"sl\s*1\s*,?\s*k1\s*,?\s*psso", "ssk"),
]


def normalise(text: str) -> str:
    text = text.lower().strip()
    for pat, repl in _NORMALISE:
        text = re.sub(pat, repl, text)
    return text


def _expand_token(token: str) -> list[str]:
    """Expand a single token such as ``k7`` or ``yo`` into stitch names."""
    token = token.strip()
    if not token:
        return []
    m = re.fullmatch(r"([a-z][a-z0-9-]*?)(\d+)", token)
    if m and m.group(1) in STITCHES:
        return [m.group(1)] * int(m.group(2))
    if token in STITCHES:
        return [token]
    raise ValueError(f"Unknown stitch token: {token!r}")


_GROUP_RE = re.compile(r"\(([^)]*)\)\s*(twice|\d+\s*times)|([a-z0-9-]+)")


def parse_row(text: str, live_count: int) -> list[str]:
    """Expand one written row into a flat list of stitch tokens."""
    text = normalise(text)

    # Whole-row shorthands.
    if "to end" in text and "," not in text:
        stitch = "p" if "purl" in text or text.strip().startswith("p") else "k"
        return [stitch] * live_count

    # "k1, yo, knit to end" style: a literal prefix followed by a fill.
    if "to end" in text:
        prefix_text, tail = text.rsplit(",", 1)
        prefix = parse_row(prefix_text, live_count)
        consumed = sum(STITCHES[s].below for s in prefix)
        fill_stitch = "p" if "purl" in tail else "k"
        remaining = max(0, live_count - consumed)
        return prefix + [fill_stitch] * remaining

    row: list[str] = []
    for m in _GROUP_RE.finditer(text):
        if m.group(1) is not None:  # a "( ... ) N times" group
            inner = [t for t in re.split(r"[,\s]+", m.group(1)) if t]
            repeat_txt = m.group(2)
            repeat = 2 if repeat_txt == "twice" else int(re.match(r"\d+", repeat_txt).group())
            expanded: list[str] = []
            for tok in inner:
                expanded.extend(_expand_token(tok))
            row.extend(expanded * repeat)
        else:
            tok = m.group(3)
            if tok in {"times", "twice"} or tok.isdigit():
                continue
            row.extend(_expand_token(tok))
    return row


def parse_pattern(pattern: Pattern) -> tuple[int, list[list[str]]]:
    """Return ``(cast_on, rows_as_token_lists)`` with live-count tracking."""
    live = pattern.cast_on
    parsed: list[list[str]] = []
    for i, text in enumerate(pattern.rows, start=1):
        row = parse_row(text, live)
        delta = sum(STITCHES[s].add - STITCHES[s].below for s in row)
        live += delta
        if live < 0:
            raise ValueError(
                f"{pattern.name}: row {i} consumes more live stitches than available"
            )
        parsed.append(row)
    return pattern.cast_on, parsed


# --------------------------------------------------------------------------- #
# Pattern library
# --------------------------------------------------------------------------- #
def stockinette(rows: int, width: int) -> Pattern:
    """Plain stockinette rectangle -- the simplest planar knit (baseline)."""
    body = []
    for r in range(rows):
        body.append("knit to end" if r % 2 == 0 else "purl to end")
    return Pattern("stockinette", width, body, family="plain")


def garter(rows: int, width: int) -> Pattern:
    return Pattern("garter", width, ["knit to end"] * rows, family="plain")


# Antique Diamonds lace -- transcribed from the standard knittingfool chart.
# Odd rows are purled (wrong side); even rows carry the lace motif.
_ANTIQUE_LACE = {
    4: "k7, k2tog, yo, k1, yo, ssk, k7",
    6: "k6, k2tog, yo, k3, yo, ssk, k6",
    8: "k5, (k2tog, yo) twice, k1, (yo, ssk) twice, k5",
    10: "k4, (k2tog, yo) twice, k3, (yo, ssk) twice, k4",
    12: "k3, (k2tog, yo) 3 times, k1, (yo, ssk) 3 times, k3",
    14: "k2, (k2tog, yo) 3 times, k3, (yo, ssk) 3 times, k2",
    16: "k1, (k2tog, yo) 3 times, k5, (yo, ssk) 3 times, k1",
    18: "k2, (yo, ssk) 3 times, k3, (k2tog, yo) 3 times, k2",
    20: "k3, (yo, ssk) 3 times, k1, (k2tog, yo) 3 times, k3",
}


def antique_diamonds(rows: int = 20, cast_on: int = 19) -> Pattern:
    body: list[str] = []
    for r in range(1, rows + 1):
        if r == 2:
            body.append("knit to end")
        elif r % 2 == 1:
            body.append("purl to end")
        else:
            body.append(_ANTIQUE_LACE.get(r, "knit to end"))
    return Pattern(f"antique_diamonds_{rows}", cast_on, body, family="lace")


def triangle(rows: int, cast_on: int = 5) -> Pattern:
    """Centre-out triangle shawl: a yarn-over increase early in each RS row.

    This is the simple growing triangle of Table 6 -- two stitches are added
    every right-side row, so the live count (and the graph) grows quadratically
    with the number of rows.
    """
    body: list[str] = []
    for r in range(1, rows + 1):
        if r % 2 == 1:
            body.append("k1, yo, knit to end")
        else:
            body.append("purl to end")
    return Pattern(f"triangle_{rows}", cast_on, body, family="triangle")


def eyelet_lace(rows: int, cast_on: int = 21) -> Pattern:
    """A regular eyelet (k2tog, yo) lace -- mesh-like, fully planar."""
    body: list[str] = []
    for r in range(1, rows + 1):
        if r % 4 == 2:
            body.append("k1, (k2tog, yo) 9 times, k2")
        elif r % 4 == 0:
            body.append("k2, (yo, ssk) 9 times, k1")
        else:
            body.append("purl to end")
    return Pattern(f"eyelet_{rows}", cast_on, body, family="lace")


def drop_stitch(rows: int, cast_on: int = 18, drop_every: int = 6) -> Pattern:
    """A drop-stitch fabric: every ``drop_every`` rows a row of dropped stitches
    stretches the yarn (Fig. 7).  Dropped stitches are class 0 but exercise the
    variable-edge-length part of the model."""
    drop_row = ", ".join(["k1", "drop"] * (cast_on // 2))
    if cast_on % 2:
        drop_row += ", k1"
    body: list[str] = []
    for r in range(1, rows + 1):
        if r % drop_every == 0:
            body.append(drop_row)
        elif r % 2 == 1:
            body.append("purl to end")
        else:
            body.append("knit to end")
    return Pattern(f"drop_stitch_{rows}", cast_on, body, family="drop")


def library() -> dict[str, Pattern]:
    """A representative class-0 set spanning plain / lace / drop / triangle.

    (``garter`` is intentionally omitted: knit and purl have identical
    subgraphs in Table 1, so garter and stockinette yield the same graph.)
    """
    return {
        "stockinette": stockinette(12, 16),
        "antique_diamonds": antique_diamonds(12, 19),
        "eyelet_lace": eyelet_lace(12, 21),
        "drop_stitch": drop_stitch(12, 18),
        "triangle": triangle(11, 5),
    }
