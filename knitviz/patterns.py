from __future__ import annotations

import re
from dataclasses import dataclass

from .stitches import get, is_known


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
    token = token.strip()
    if not token:
        return []
    if is_known(token):
        return [token]
    m = re.fullmatch(r"([a-z][a-z0-9-]*?)(\d+)", token)
    if m and is_known(m.group(1)):
        return [m.group(1)] * int(m.group(2))
    raise ValueError(f"Unknown stitch token: {token!r}")


_GROUP_RE = re.compile(r"\(([^)]*)\)\s*(twice|\d+\s*times)|([a-z0-9-]+)")


def parse_row(text: str, live_count: int) -> list[str]:
    text = normalise(text)

    # Whole-row shorthands.
    if "to end" in text and "," not in text:
        stitch = "p" if "purl" in text or text.strip().startswith("p") else "k"
        return [stitch] * live_count

    # "k1, yo, knit to end" style: a literal prefix followed by a fill.
    if "to end" in text:
        prefix_text, tail = text.rsplit(",", 1)
        prefix = parse_row(prefix_text, live_count)
        consumed = sum(get(s).below for s in prefix)
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
    live = pattern.cast_on
    parsed: list[list[str]] = []
    for i, text in enumerate(pattern.rows, start=1):
        row = parse_row(text, live)
        consumed = sum(get(s).below for s in row)
        added = sum(get(s).add for s in row)
        live += added - consumed
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
    body: list[str] = []
    for r in range(1, rows + 1):
        if r % 2 == 1:
            body.append("k1, yo, knit to end")
        else:
            body.append("purl to end")
    return Pattern(f"triangle_{rows}", cast_on, body, family="triangle")


def eyelet_lace(rows: int, cast_on: int = 21) -> Pattern:
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


def honeycomb_cable() -> Pattern:
    body = [
        "k4, c1f, c1b, k4", "purl to end",
        "k2, (c1f, c1b) 2 times, k2", "purl to end",
        "(c1f, c1b) 3 times", "purl to end",
        "(c1b, c1f) 3 times", "purl to end",
        "k2, (c1b, c1f) 2 times, k2", "purl to end",
        "k4, c1b, c1f, k4", "purl to end",
    ]
    return Pattern("honeycomb_cable", 12, body, family="cable")


def library() -> dict[str, Pattern]:
    return {
        "stockinette": stockinette(12, 16),
        "antique_diamonds": antique_diamonds(12, 19),
        "eyelet_lace": eyelet_lace(12, 21),
        "drop_stitch": drop_stitch(12, 18),
        "triangle": triangle(11, 5),
    }
