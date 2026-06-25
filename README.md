# Knitting Pattern Graph Layout — Master Seminar Implementation

A Python implementation of the paper:

> **"A Graph Model and a Layout Algorithm for Knitting Patterns"**
> Gray, Bell & Kobourov (2024)

This project models a knitting pattern as a mathematical graph, then lays it out visually so that edges never cross — matching the structure described in the paper.

---

## What it does

A knitting pattern is represented as a graph where:

- **Nodes (dots)** = individual stitches
- **Edges (lines)** come in two types:
  - **Yarn edges** (grey) — stitches connected along the same strand of yarn
  - **Loop edges** (red) — stitches pulled through one another (the defining action of knitting)

The algorithm has three stages:

1. **Parse** — reads real knitting pattern text (e.g. `k7, k2tog, yo, k1, yo, ssk, k7`) into a flat list of stitch operations
2. **Build** — constructs the graph using a needle-stack model that mirrors how flat knitting physically flips every row
3. **Layout** — starts from a planar embedding, then settles node positions using spring forces while rejecting any move that would create an edge crossing

The demo pattern used is **"Antique Diamonds"** lace (Figure 1 from the paper), cast on with 19 stitches.

---

## Output

The script produces a side-by-side plot saved as `antique_diamonds.png`:

| Left panel | Right panel |
|---|---|
| Planar starting layout (before settling) | Final settled layout with no crossings |
| DEL score shown as a quality metric | Lower DEL = edge lengths closer to targets |

DEL (Deviation from Edge Lengths) measures how evenly spaced the graph looks — lower is better.

---

## Requirements

- Python 3.8+
- [NetworkX](https://networkx.org/)
- [Matplotlib](https://matplotlib.org/)
- [NumPy](https://numpy.org/)

Install all dependencies with:

```bash
pip install networkx matplotlib numpy
```

---

## How to run

```bash
python implemention_ms.py
```

The script will:
1. Print graph statistics (node count, edge count, planarity check)
2. Print DEL scores before and after layout settling
3. Display the plot and save it as `antique_diamonds.png`

Example console output:

```
Built graph: 170 dots, 207 lines, planar = True
DEL before: 0.847
DEL after:  0.213
```

---

## Supported stitch types

| Symbol | Name | Nodes created | Nodes consumed |
|---|---|---|---|
| `k` | Knit | 1 | 1 |
| `p` | Purl | 1 | 1 |
| `yo` | Yarn over | 1 | 0 (creates a hole) |
| `k2tog` | Knit 2 together | 1 | 2 (decrease) |
| `ssk` | Slip slip knit | 1 | 2 (decrease) |

---

## Pattern syntax supported by the parser

| Syntax | Meaning |
|---|---|
| `k7` | 7 knit stitches |
| `k2tog` | one decrease stitch |
| `yo` | one yarn over |
| `(k2tog, yo) 3 times` | repeat group 3 times |
| `(yo, ssk) twice` | repeat group 2 times |
| `purl to end` | fill the entire row with purls |
| `knit to end` | fill the entire row with knits |

---

## Tuning the demo

Inside `implemention_ms.py`, two constants control the output:

```python
USE_ROWS = 8      # number of rows to render (higher = bigger graph, slower)
ITERS    = 350    # layout settling iterations (higher = better quality)
STEP     = 0.08   # step size per iteration
```

Increasing `USE_ROWS` to 20 renders the full diamond motif but takes longer to settle.

---

## Project structure

```
master_seminar/
├── implemention_ms.py            # main script
├── antique_diamonds.png          # output image (generated on run)
├── Figure_1.png                  # reference figure from the paper
├── knitting_patterns_report.tex  # LaTeX seminar report
├── knitting_patterns_references.bib  # bibliography
├── draft_master_report.docx      # draft report (Word)
└── Masterseminar_Implementaation/
    └── README.md                 # this file
```

---

## Reference

Gray, A., Bell, S., & Kobourov, S. (2024). *A Graph Model and a Layout Algorithm for Knitting Patterns*. Proceedings of the 32nd International Symposium on Graph Drawing and Network Visualization (GD 2024).
