from __future__ import annotations

from pathlib import Path
from math import hypot

import matplotlib.pyplot as plt
import networkx as nx

YARN_COLOR = "#6f6f6f"
LOOP_COLOR = "#c83d3d"
NODE_COLOR = "#2f7fc7"


def _edge_colors(g: nx.Graph) -> list[str]:
    return [
        YARN_COLOR if d.get("kind") == "yarn" else LOOP_COLOR
        for _, _, d in g.edges(data=True)
    ]


def draw_layout(g: nx.Graph, pos: dict, ax, title: str = "") -> None:
    nx.draw(
        g, pos, ax=ax,
        node_size=10, width=0.7,
        edge_color=_edge_colors(g), node_color=NODE_COLOR,
    )
    for signature in g.graph.get("crossing_signature", []):
        (a, b), (c, d) = signature["edges"]
        x1, y1 = pos[a]
        x2, y2 = pos[b]
        x3, y3 = pos[c]
        x4, y4 = pos[d]
        den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(den) < 1e-12:
            continue
        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
        x, y = x1 + t * (x2 - x1), y1 + t * (y2 - y1)
        over = signature["over"]
        u, v = over
        dx, dy = pos[v][0] - pos[u][0], pos[v][1] - pos[u][1]
        length = hypot(dx, dy)
        if length:
            gap = 0.06 / length
            ax.plot([x - gap * dx, x + gap * dx], [y - gap * dy, y + gap * dy],
                    color="white", linewidth=2.4, zorder=2)
            color = YARN_COLOR if g.edges[over].get("kind") == "yarn" else LOOP_COLOR
            ax.plot([x - gap * dx, x + gap * dx], [y - gap * dy, y + gap * dy],
                    color=color, linewidth=0.9, zorder=3)
    ax.set_title(title, fontsize=9)
    ax.set_aspect("equal")
    ax.set_axis_off()


def compare_figure(g: nx.Graph, results: dict, out_path: Path, suptitle: str = "") -> None:
    drawable = [(name, r) for name, r in results.items() if r.get("pos") is not None]
    if not drawable:
        return
    fig, axes = plt.subplots(1, len(drawable), figsize=(4.6 * len(drawable), 4.8))
    if len(drawable) == 1:
        axes = [axes]
    for ax, (name, r) in zip(axes, drawable):
        title = f"{name}\nDEL={r['del']:.3f}  cross={r['crossings']}  {r['time']:.2f}s"
        draw_layout(g, r["pos"], ax, title)
    if suptitle:
        fig.suptitle(suptitle, fontsize=11)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
