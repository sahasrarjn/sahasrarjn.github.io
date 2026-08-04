"""
Draw the distribution the article talks about: nearest-neighbour Tanimoto from
each test molecule into train, for three splits of the same dataset.

Emits a theme-aware inline SVG (no external deps, no raster) to hist.svg.
"""

import json
import sys

import numpy as np

from split_audit_v2 import (MFPGEN, assign_split, group_keys, load, nn_sim)

DATASET = ("Lipophilicity", "data/Lipophilicity.csv", "smiles", "exp")
SEED = 42
BINS = 40

ARMS = [
    ("Random split",        "random",           "shuffled",      "a"),
    ("Scaffold split",      "scaffold__own",    "shuffled",      "b"),
    ("Butina cluster split", "butina",          "shuffled",      "c"),
]

W, H = 880, 380
PAD_L, PAD_R, PAD_T, PAD_B = 56, 18, 26, 52


def build():
    name, path, smi, lab = DATASET
    mols, canon, y, prov = load(path, smi, lab)
    fps = [MFPGEN.GetFingerprint(m) for m in mols]

    series = []
    for label, grouping, order, cls in ARMS:
        keys = group_keys(grouping, mols, canon, fps)
        tr, va, te = assign_split(keys, order, SEED)
        sims = nn_sim(tr, te, fps)
        hist, edges = np.histogram(sims, bins=BINS, range=(0.0, 1.0))
        series.append({
            "label": label, "cls": cls,
            "pct": (hist / hist.sum() * 100).tolist(),
            "edges": edges.tolist(),
            "mean": float(sims.mean()),
            "over80": float((sims >= 0.8).mean() * 100),
        })
    return name, len(mols), series


def svg(name, n, series):
    ymax = max(max(s["pct"]) for s in series) * 1.55
    pw, ph = W - PAD_L - PAD_R, H - PAD_T - PAD_B

    def X(v):
        return PAD_L + v * pw

    def Y(v):
        return PAD_T + ph - (v / ymax) * ph

    out = [
        f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" '
        f'aria-label="Nearest-neighbour Tanimoto distributions for three splits of {name}" '
        'xmlns="http://www.w3.org/2000/svg" font-family="ui-monospace, SFMono-Regular, Menlo, monospace">',
        "<style>"
        ".ax{stroke:var(--rule,#D8D7D1);stroke-width:1}"
        ".gl{stroke:var(--rule,#D8D7D1);stroke-width:1;stroke-dasharray:2 4;opacity:.6}"
        ".tx{fill:var(--ink-3,#747984);font-size:11px}"
        ".tl{fill:var(--ink-2,#4A4E58);font-size:12px}"
        ".a{fill:none;stroke:#9B3B24;stroke-width:2}"
        ".b{fill:none;stroke:#2D4EC8;stroke-width:2}"
        ".c{fill:none;stroke:#1F7A5A;stroke-width:2}"
        ".af{fill:#9B3B24;opacity:.10}.bf{fill:#2D4EC8;opacity:.10}.cf{fill:#1F7A5A;opacity:.10}"
        ".dz{fill:#9B3B24;opacity:.07}"
        ".dl{stroke:#9B3B24;stroke-width:1;stroke-dasharray:3 3;opacity:.7}"
        "</style>",
    ]

    # near-duplicate zone
    out.append(f'<rect class="dz" x="{X(0.8):.1f}" y="{PAD_T}" '
               f'width="{X(1.0)-X(0.8):.1f}" height="{ph}"/>')
    out.append(f'<line class="dl" x1="{X(0.8):.1f}" y1="{PAD_T}" '
               f'x2="{X(0.8):.1f}" y2="{PAD_T+ph}"/>')

    # y gridlines
    step = 5
    v = 0
    while v <= ymax:
        out.append(f'<line class="gl" x1="{PAD_L}" y1="{Y(v):.1f}" x2="{PAD_L+pw}" y2="{Y(v):.1f}"/>')
        out.append(f'<text class="tx" x="{PAD_L-8}" y="{Y(v)+4:.1f}" text-anchor="end">{v}%</text>')
        v += step

    # x axis
    out.append(f'<line class="ax" x1="{PAD_L}" y1="{PAD_T+ph}" x2="{PAD_L+pw}" y2="{PAD_T+ph}"/>')
    for t in [0, 0.2, 0.4, 0.6, 0.8, 1.0]:
        out.append(f'<line class="ax" x1="{X(t):.1f}" y1="{PAD_T+ph}" x2="{X(t):.1f}" y2="{PAD_T+ph+5}"/>')
        out.append(f'<text class="tx" x="{X(t):.1f}" y="{PAD_T+ph+19:.1f}" text-anchor="middle">{t:.1f}</text>')
    out.append(f'<text class="tl" x="{PAD_L+pw/2:.1f}" y="{H-14}" text-anchor="middle">'
               'nearest-neighbour Tanimoto, test molecule &#8594; training set</text>')
    out.append(f'<text class="tx" x="{X(0.9):.1f}" y="{PAD_T+13}" text-anchor="middle">'
               'near-duplicate</text>')

    # stepped curves
    for s in series:
        edges, pct = s["edges"], s["pct"]
        pts = []
        for i, p in enumerate(pct):
            pts.append((X(edges[i]), Y(p)))
            pts.append((X(edges[i + 1]), Y(p)))
        d = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in pts)
        base = PAD_T + ph
        out.append(f'<path class="{s["cls"]}f" d="{d} L {pts[-1][0]:.1f} {base} '
                   f'L {pts[0][0]:.1f} {base} Z"/>')
        out.append(f'<path class="{s["cls"]}" d="{d}"/>')

    # legend
    lx, ly = PAD_L + 12, PAD_T + 12
    for s in series:
        out.append(f'<line class="{s["cls"]}" x1="{lx}" y1="{ly}" x2="{lx+22}" y2="{ly}"/>')
        out.append(f'<text class="tl" x="{lx+29}" y="{ly+4}">{s["label"]} '
                   f'&#183; mean {s["mean"]:.3f} &#183; {s["over80"]:.1f}% &#8805;0.8</text>')
        ly += 17

    out.append("</svg>")
    return "\n".join(out)


if __name__ == "__main__":
    name, n, series = build()
    with open("hist.svg", "w") as fh:
        fh.write(svg(name, n, series))
    with open("hist_data.json", "w") as fh:
        json.dump({"dataset": name, "n": n, "series": series}, fh, indent=2)
    for s in series:
        print(f"{s['label']:22s} mean={s['mean']:.3f}  >=0.8={s['over80']:.1f}%")
    print("wrote hist.svg")
