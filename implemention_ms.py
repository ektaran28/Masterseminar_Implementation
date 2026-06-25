# knitting_full.py  -- read a REAL knitting pattern and draw it
# Run with:  python knitting_full.py
# Needs:     pip install networkx matplotlib numpy
#
# This builds on knitting_layout.py. The new part is the PARSER: it reads
# real pattern text like "k7, k2tog, yo, k1, yo, ssk, k7" and builds the
# dots-and-lines graph automatically, instead of you hand-coding a grid.

import networkx as nx
import matplotlib.pyplot as plt
import numpy as np
import re

# ======================================================================
# 1. STITCH DICTIONARY
#    For each stitch: how many new dots it creates ("add"),
#    and how many dots below it it connects down to ("below").
# ======================================================================
STITCHES = {
    "k":              {"add": 1, "below": 1},   # knit
    "p":              {"add": 1, "below": 1},   # purl
    "yo":             {"add": 1, "below": 0},   # yarn over -> makes a hole, no dot below
    "k2tog":          {"add": 1, "below": 2},   # knit 2 together -> decrease
    "ssk":            {"add": 1, "below": 2},   # slip slip knit -> decrease
}

# ======================================================================
# 2. THE PARSER  (text  ->  list of stitch names)
# ======================================================================
def normalize(text):
    # fix multi-word stitch spellings so "k2 tog" becomes "k2tog"
    return text.lower().replace("k2 tog", "k2tog")

def parse_row(text, live_count):
    """Turn one row of pattern text into a flat list of stitch names."""
    t = normalize(text)

    # whole-row shortcuts: "knit to end" / "purl to end"
    if "to end" in t:
        return (["p"] if "purl" in t else ["k"]) * live_count

    def expand(tok):
        tok = tok.strip()
        if not tok:
            return []
        m = re.match(r"([a-z]+)(\d+)$", tok)      # e.g. "k7" -> seven knits
        if m and m.group(1) in STITCHES:
            return [m.group(1)] * int(m.group(2))
        if tok in STITCHES:
            return [tok]
        raise ValueError(f"unknown stitch: '{tok}'")

    out = []
    # match either  "(group) twice / N times"  or  a single token
    pat = re.compile(r"\(([^)]*)\)\s*(twice|\d+\s*times)|([a-z0-9]+)")
    for m in pat.finditer(t):
        if m.group(1) is not None:                # a parenthetical group
            inner = [x for x in re.split(r"[,\s]+", m.group(1)) if x]
            mult = 2 if m.group(2) == "twice" else int(re.match(r"\d+", m.group(2)).group())
            group = []
            for tk in inner:
                group += expand(tk)
            out += group * mult
        else:
            tok = m.group(3)
            if tok in ("twice", "times") or tok.isdigit():
                continue
            out += expand(tok)
    return out

# ======================================================================
# 3. THE PATTERN  -- "Antique Diamonds" lace from the paper (Figure 1)
#    Even rows are lace; all odd rows are "purl to end" (wrong-side rows).
# ======================================================================
CAST_ON = 19
LACE_ROWS = {
    4:  "k7, k2 tog, yo, k1, yo, ssk, k7",
    6:  "k6, k2 tog, yo, k3, yo, ssk, k6",
    8:  "k5, (k2 tog, yo) twice, k1, (yo, ssk) twice, k5",
    10: "k4, (k2 tog, yo) twice, k3, (yo, ssk) twice, k4",
    12: "k3, (k2 tog, yo) 3 times, k1, (yo, ssk) 3 times, k3",
    14: "k2, (k2 tog, yo) 3 times, k3, (yo, ssk) 3 times, k2",
    16: "k1, (k2 tog, yo) 3 times, k5, (yo, ssk) 3 times, k1",
    18: "k2, (yo, ssk) 3 times, k3, (k2 tog, yo) 3 times, k2",
    20: "k3, (yo, ssk) 3 times, k1, (k2 tog, yo) 3 times, k3",
}

# How many rows to actually draw. 8 is a good, fast demo (~170 dots).
# Higher shows more of the diamond but runs slower and settles less neatly
# (the paper hits the same limit -- its weak starting layout struggles at scale).
USE_ROWS = 8

# build the full row list, then parse it row by row
row_texts = []
for r in range(1, USE_ROWS + 1):
    if r == 2:
        row_texts.append("knit to end")
    elif r % 2 == 1:
        row_texts.append("purl to end")     # all wrong-side rows
    else:
        row_texts.append(LACE_ROWS[r])

live = CAST_ON
parsed = []
for txt in row_texts:
    row = parse_row(txt, live)
    live = sum(STITCHES[s]["add"] for s in row)
    parsed.append(row)

# ======================================================================
# 4. BUILD THE GRAPH (the corrected Algorithm 1 from the paper)
#    The "needle" is a stack of live stitches. A stack reverses order,
#    which automatically matches how flat knitting flips every row.
# ======================================================================
def build_graph(cast_on, rows):
    G = nx.Graph(); needle = []; n = 0; prev = None
    for _ in range(cast_on):                    # cast-on row
        G.add_node(n)
        if prev is not None: G.add_edge(prev, n, kind="yarn")
        needle.append(n); prev = n; n += 1
    for row in rows:
        new_live = []
        for st in row:
            spec = STITCHES[st]
            lowers = [needle.pop() for _ in range(spec["below"])]  # consume below
            for _ in range(spec["add"]):                           # create new dot
                G.add_node(n)
                if prev is not None: G.add_edge(prev, n, kind="yarn")  # along the yarn
                for lo in lowers: G.add_edge(lo, n, kind="loop")       # pulled through
                new_live.append(n); prev = n; n += 1
        needle = new_live
    return G

G = build_graph(CAST_ON, parsed)
print(f"Built graph: {G.number_of_nodes()} dots, {G.number_of_edges()} lines, "
      f"planar = {nx.check_planarity(G)[0]}")

# ======================================================================
# 5. LAY IT OUT  (same idea as before: planar start -> settle with springs,
#    never allowing a crossing). Uses numpy so the big graph runs fast.
# ======================================================================
nodes = list(G.nodes()); idx = {u: i for i, u in enumerate(nodes)}; N = len(nodes)
ea = np.array([idx[u] for u, v in G.edges()])
eb = np.array([idx[v] for u, v in G.edges()])
target = np.array([1.0 if d["kind"] == "yarn" else 1.5 for _, _, d in G.edges(data=True)])

P0 = np.array([nx.planar_layout(G)[u] for u in nodes], float)
# rescale the start so its average line length is near the target (important!)
P0 *= np.mean(target) / np.mean(np.linalg.norm(P0[ea] - P0[eb], axis=1))
P = P0.copy()

# which lines touch each dot (needed for the no-crossing check)
incident = {i: [] for i in range(N)}
for e, (u, v) in enumerate(G.edges()):
    incident[idx[u]].append(e); incident[idx[v]].append(e)

def _side(ax, ay, bx, by, cx, cy):
    return (cy - ay) * (bx - ax) - (by - ay) * (cx - ax)

def causes_crossing(node, new_xy):
    # would moving `node` to new_xy make any of its lines cross another line?
    for e in incident[node]:
        a, b = ea[e], eb[e]
        p1 = new_xy if a == node else P[a]
        p2 = new_xy if b == node else P[b]
        q1, q2 = P[ea], P[eb]                        # all other lines at once
        d1 = _side(q1[:,0], q1[:,1], q2[:,0], q2[:,1], p1[0], p1[1])
        d2 = _side(q1[:,0], q1[:,1], q2[:,0], q2[:,1], p2[0], p2[1])
        d3 = _side(p1[0], p1[1], p2[0], p2[1], q1[:,0], q1[:,1])
        d4 = _side(p1[0], p1[1], p2[0], p2[1], q2[:,0], q2[:,1])
        cross = ((d1 > 0) != (d2 > 0)) & ((d3 > 0) != (d4 > 0))
        cross &= ~((ea == a) | (eb == a) | (ea == b) | (eb == b))  # ignore shared corners
        if cross.any():
            return True
    return False

def del_score(positions):
    got = np.linalg.norm(positions[ea] - positions[eb], axis=1)
    return np.sqrt(np.mean(((got - target) / target) ** 2))

STEP, ITERS = 0.08, 350
for it in range(ITERS):
    F = np.zeros((N, 2))
    # (a) edge-length springs
    diff = P[eb] - P[ea]; dist = np.linalg.norm(diff, axis=1); dist[dist == 0] = 1e-9
    pull = (dist - target)[:, None] * (diff / dist[:, None])
    np.add.at(F, ea, pull); np.add.at(F, eb, -pull)
    # (b) gentle push-apart, fading out
    rep = 0.1 * (1 - it / ITERS)
    d = P[:, None, :] - P[None, :, :]; nn = np.linalg.norm(d, axis=2); nn[nn < 1e-6] = 1e-6
    push = rep * d / (nn ** 2)[:, :, None]
    np.fill_diagonal(push[:, :, 0], 0); np.fill_diagonal(push[:, :, 1], 0)
    F += push.sum(1)
    # (c) move dots one at a time; skip any move that would create a crossing
    for node in range(N):
        proposed = P[node] + STEP * F[node]
        if not causes_crossing(node, proposed):
            P[node] = proposed

print(f"DEL before: {del_score(P0):.3f}")
print(f"DEL after:  {del_score(P):.3f}")

# ======================================================================
# 6. DRAW IT  (grey = yarn lines, red = pulled-through loop lines)
# ======================================================================
pos0 = {u: P0[idx[u]] for u in nodes}
posP = {u: P[idx[u]] for u in nodes}
colors = ["#888888" if d["kind"] == "yarn" else "#cc3333" for _, _, d in G.edges(data=True)]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 7))
ax1.set_title(f"Before: planar start\nDEL = {del_score(P0):.2f}")
nx.draw(G, pos0, ax=ax1, node_size=15, width=0.7, edge_color=colors, node_color="#3399cc")
ax2.set_title(f"After: settled lace, no crossings\nDEL = {del_score(P):.2f}")
nx.draw(G, posP, ax=ax2, node_size=15, width=0.7, edge_color=colors, node_color="#3399cc")
plt.tight_layout()
plt.savefig("antique_diamonds.png", dpi=100)   # also saved as a file
plt.show()