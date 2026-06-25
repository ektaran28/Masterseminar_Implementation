# A graph model and a layout algorithm for knitting patterns ,Master Seminar paper Implementation

 Python re-implementation of A graph model and a layout algorithm for knitting patterns

> **Kathryn Gray, Brian Bell, Stephen Kobourov.**
> *A Graph Model and a Layout Algorithm for Knitting Patterns.*
> Graph Drawing (GD) 2024 - arXiv:2406.13800.

It implements the paper's two algorithms, its evaluation metrics, and the
competing layout methods, then reproduces the paper's experimental findings and
adds an independent evaluation.

---

## What it does

A knitting pattern is converted into a **graph** (Algorithm 1):

- **nodes** = stitches;
- **yarn edges** (grey) = stitches adjacent along the yarn / needle;
- **loop edges** (red) = a stitch pulled through the loop below it;
- every edge has a **pre specified length** (stitches are taller than wide, so
  loop/column edges are longer than yarn/row edges).

The graph is then drawn (Algorithm 2, **KnitLayout**): a crossing free initial
layout followed by **safe force-directed steps** that pull edges towards their
target lengths while *never* introducing an edge crossing.

---

## Project layout

```
knitviz/                 the library
├── stitches.py          stitch dictionary (Table 1) + base edge lengths
├── patterns.py          pattern text parser + pattern generators
├── graph_model.py       Algorithm 1 (pattern -> graph) + knittability checks
├── layout.py            Algorithm 2 (KnitLayout: init + safe FDA, 3 forces)
├── baselines.py         KnitGrid (Counts), SFDP (Graphviz), Kamada-Kawai
├── metrics.py           DEL (Eq. 1) and crossing count
└── draw.py              figure rendering
experiments.py           reproduction experiments (Tables 3–6) -> results/
analysis.py              ablations, convergence and graph-model checks
EVALUATION.md            the written evaluation / experiment catalogue
```

---

## Requirements

- Python 3.9+ (developed and tested on Python 3.10)
- `networkx`, `numpy`, `scipy`, `matplotlib`  (`pip install -r requirements.txt`)
- **Optional:** [Graphviz](https://graphviz.org/) on `PATH` (provides `sfdp`)
  for the SFDP comparison. If absent, SFDP is skipped automatically.

---

## How to run

```bash
# main reproduction experiments (DEL, crossings, runtime + figures)
python experiments.py --mode quick      # ~1–2 min
python experiments.py --mode full       # paper-scale, several minutes

# supplementary experiments: ablations, convergence, model unit-checks
python analysis.py
```

Outputs are written to `results/`:

- `results.csv`, `results.json` - raw numbers,
- `results.md` - DEL / crossings / runtime tables (Experiments A & B),
- `figures/*.png` - side-by-side layout comparisons.

---

## Headline result

On class0 (planar) knitting patterns, **KnitLayout achieves the lowest
edge-length error among the crossing free, scope correct methods and never
introduces a crossing**, reproducing the paper's central claim. KnitGrid is
fastest but crosses edges at increases/decreases; SFDP is fast and smooth but
does not target the prescribed lengths.

DEL (edge length error, lower is better) / crossings, from `experiments.py --mode full`:

| Pattern | Nodes | KnitLayout | KnitGrid | SFDP | Kamada–Kawai |
|---|---:|---|---|---|---|
| stockinette      | 208 | **0.061 / 0** | 0.164 / 0  | 0.269 / 0 | 0.017 / 0 |
| antique_diamonds | 247 | **0.058 / 0** | 0.292 / 12 | 0.259 / 0 | 0.041 / 0 |
| eyelet_lace      | 273 | **0.064 / 0** | 0.265 / 0  | 0.228 / 0 | 0.046 / 0 |
| drop_stitch      | 234 | **0.124 / 0** | 0.205 / 0  | 0.310 / 0 | 0.118 / 0 |
| triangle (×35)   | 504 | **0.116 / 0** | 0.617 / 34 | 0.296 / 4 | 0.068 / 0 |

KnitLayout's edge-length error is 3–8× smaller than KnitGrid and 2–4× smaller
than SFDP, always crossing free; KnitGrid's crossings grow with size and SFDP
starts crossing on the largest graph. (Kamada–Kawai reaches a lower DEL on these
*planar* instances but gives no crossing guarantee - see the discussion.)

**Reproduction note:** matching the paper's quality requires the
knitting structure aware initial layout the authors motivate (§5.1/§7); the
literal NetworkX planar init traps the hard-constraint step at DEL ≈ 0.4–0.8.
Both inits are in the code (`knitting_layout`, `planar_layout`).

See [EVALUATION.md](EVALUATION.md) for the full setup, results, comparison and
the catalogue of experiments.

---

## Supported stitches (Table 1)

| Token | Name | nodes added | loops below | planar |
|---|---|---:|---:|:--:|
| `k`/`p` | knit / purl | 1 | 1 | ✓ |
| `yo`, `m1` | yarn over / make one (increase) | 1 | 0 | ✓ |
| `kfb` | knit front & back (increase) | 2 | 1 | ✓ |
| `k2tog`, `ssk` | decreases | 1 | 2 | ✓ |
| `sl1-k2-psso` | central double decrease | 1 | 3 | ✓ |
| `drop` | dropped stitch (long yarn float) | 1 | 1 | ✓ |
| `c1b`, `c2b` | cables (complexity class 1) | 2/4 | 2/4 | ✗ |

Cables are modelled for completeness but are non planar (class 1) and out of
scope for the planar layout, exactly as in the paper.
