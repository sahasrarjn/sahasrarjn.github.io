"""
The thesis in one picture: everything below is legitimately called
"a scaffold split", and they are not the same split.

For each dataset, plot every scaffold-family arm as a dot on an axis of mean
nearest-neighbour Tanimoto, with the random split marked for reference. The
spread of the dots is the article's argument.

Reads audit_v2.json. Emits spread.svg (theme-aware, no external deps).
"""

import json

SCAFFOLD_ARMS = {
    "Scaffold (acyclic=own)":            "acyclic = own group",
    "Scaffold (acyclic=pooled)":         "acyclic = pooled",
    "Scaffold (acyclic=Butina)":         "acyclic = clustered",
    "Scaffold (pooled), DeepChem order": "pooled + DeepChem order",
    "Scaffold (pooled), other tie-break": "pooled + other tie-break",
    "Scaffold (own), DeepChem order":    "own + DeepChem order",
}

W = 960
PAD_L, PAD_R, PAD_T, PAD_B = 205, 30, 64, 58
ROW_H = 62
XMIN, XMAX = 0.35, 0.66


def build():
    data = json.load(open("audit_v2.json"))
    rows = []
    for ds in data:
        arms = {a["arm"]: a for a in ds["arms"]}
        pts = [(SCAFFOLD_ARMS[k], arms[k]["morgan_mean"])
               for k in SCAFFOLD_ARMS if k in arms]
        rows.append({
            "name": ds["dataset"],
            "n": ds["structure"]["n_molecules"],
            "acyclic": ds["structure"]["acyclic_pct"],
            "random": arms["Random"]["morgan_mean"],
            "pts": sorted(pts, key=lambda p: p[1]),
        })
    return rows


def svg(rows):
    H = PAD_T + len(rows) * ROW_H + PAD_B
    pw = W - PAD_L - PAD_R

    def X(v):
        return PAD_L + (v - XMIN) / (XMAX - XMIN) * pw

    o = [
        f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" '
        'aria-label="Spread of mean nearest-neighbour Tanimoto across six variants of '
        'a scaffold split, on four datasets" '
        'xmlns="http://www.w3.org/2000/svg" '
        'font-family="ui-monospace, SFMono-Regular, Menlo, monospace">',
        "<style>"
        ".gl{stroke:var(--rule,#D8D7D1);stroke-width:1;stroke-dasharray:2 4;opacity:.7}"
        ".ax{stroke:var(--rule-2,#C4C3BC);stroke-width:1}"
        ".tx{fill:var(--ink-3,#747984);font-size:11px}"
        ".ds{fill:var(--ink,#14161A);font-size:13px;font-weight:600}"
        ".sub{fill:var(--ink-3,#747984);font-size:10px}"
        ".span{stroke:#2D4EC8;stroke-width:7;opacity:.18;stroke-linecap:round}"
        ".dot{fill:#2D4EC8}"
        ".rnd{fill:none;stroke:#9B3B24;stroke-width:2}"
        ".rlab{fill:#9B3B24;font-size:10px}"
        ".dlab{fill:var(--ink-2,#4A4E58);font-size:10px}"
        "</style>",
    ]

    # x gridlines
    t = 0.35
    while t <= XMAX + 1e-9:
        o.append(f'<line class="gl" x1="{X(t):.1f}" y1="{PAD_T-16}" '
                 f'x2="{X(t):.1f}" y2="{PAD_T + len(rows)*ROW_H - 18:.1f}"/>')
        o.append(f'<text class="tx" x="{X(t):.1f}" y="{PAD_T-24}" '
                 f'text-anchor="middle">{t:.2f}</text>')
        t += 0.05

    o.append(f'<text class="tx" x="{PAD_L + pw/2:.1f}" y="{PAD_T-42}" '
             'text-anchor="middle">mean nearest-neighbour Tanimoto, test &#8594; train '
             '(lower = harder)</text>')

    for i, r in enumerate(rows):
        y = PAD_T + i * ROW_H
        o.append(f'<text class="ds" x="{PAD_L-14}" y="{y+4}" text-anchor="end">{r["name"]}</text>')
        o.append(f'<text class="sub" x="{PAD_L-14}" y="{y+18}" text-anchor="end">'
                 f'{r["n"]:,} mols &#183; {r["acyclic"]}% acyclic</text>')

        lo = min(p[1] for p in r["pts"])
        hi = max(p[1] for p in r["pts"])
        o.append(f'<line class="span" x1="{X(lo):.1f}" y1="{y}" x2="{X(hi):.1f}" y2="{y}"/>')

        for _, v in r["pts"]:
            o.append(f'<circle class="dot" cx="{X(v):.1f}" cy="{y}" r="4.5"/>')

        # range annotation
        o.append(f'<text class="dlab" x="{X(lo)-11:.1f}" y="{y+4}" text-anchor="end">{lo:.3f}</text>')
        o.append(f'<text class="dlab" x="{X(hi)+11:.1f}" y="{y+4}">{hi:.3f}</text>')

        # random reference
        rx = X(r["random"])
        o.append(f'<path class="rnd" d="M {rx:.1f} {y-11} L {rx:.1f} {y+11}"/>')

    # legend
    ly = PAD_T + len(rows) * ROW_H + 6
    o.append(f'<line class="ax" x1="{PAD_L}" y1="{ly-22}" x2="{W-PAD_R}" y2="{ly-22}"/>')
    o.append(f'<circle class="dot" cx="{PAD_L+6}" cy="{ly}" r="4.5"/>')
    o.append(f'<text class="tx" x="{PAD_L+18}" y="{ly+4}">'
             'each dot = one thing people call &#8220;a scaffold split&#8221;</text>')
    o.append(f'<path class="rnd" d="M {PAD_L+390} {ly-8} L {PAD_L+390} {ly+8}"/>')
    o.append(f'<text class="rlab" x="{PAD_L+402}" y="{ly+4}">random split, for reference</text>')

    o.append("</svg>")
    return "\n".join(o)


if __name__ == "__main__":
    rows = build()
    open("spread.svg", "w").write(svg(rows))
    for r in rows:
        lo = min(p[1] for p in r["pts"]); hi = max(p[1] for p in r["pts"])
        print(f"{r['name']:14s} random={r['random']:.3f}  scaffold variants "
              f"{lo:.3f}..{hi:.3f}  spread={hi-lo:.3f}  (n={len(r['pts'])})")
    print("wrote spread.svg")
