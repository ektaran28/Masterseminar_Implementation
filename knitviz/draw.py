"""Drawing helpers: render a knitting graph with yarn edges in grey and loop
edges in red, matching the figure convention of the paper."""

from __future__ import annotations

from pathlib import Path

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
    ax.set_title(title, fontsize=9)
    ax.set_aspect("equal")
    ax.set_axis_off()


def compare_figure(g: nx.Graph, results: dict, out_path: Path, suptitle: str = "") -> None:
    """`results` maps algorithm name -> dict with keys pos, del, crossings, time."""
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
