"""
Explain what a Bemis-Murcko scaffold actually is, using real molecules from the
datasets in the post -- drawn by RDKit, not illustrated.

Three figures:
  scaffold_chain.svg  molecule -> Murcko framework -> generic framework
  scaffold_sink.svg   several real, unlike molecules that all collapse to benzene
  scaffold_hole.svg   real acyclic molecules, which have no scaffold at all

RDKit draws in black; we rewrite that to `currentColor` so the figures follow
the page's light/dark theme like every other figure in the post.
"""

import gzip
import re

import pandas as pd
from rdkit import Chem, DataStructs, RDLogger
from rdkit.Chem import rdFingerprintGenerator
from rdkit.Chem.Draw import rdMolDraw2D
from rdkit.Chem.Scaffolds import MurckoScaffold

RDLogger.DisableLog("rdApp.*")
MFP = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=2048)

CELL_W, CELL_H = 210, 165


def draw(smiles, w=CELL_W, h=CELL_H):
    """Render one molecule to a theme-aware SVG fragment."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None or mol.GetNumAtoms() == 0:
        return None
    d = rdMolDraw2D.MolDraw2DSVG(w, h)
    o = d.drawOptions()
    o.clearBackground = False
    o.useBWAtomPalette()
    o.bondLineWidth = 2
    rdMolDraw2D.PrepareAndDrawMolecule(d, mol)
    d.FinishDrawing()
    svg = d.GetDrawingText()
    svg = svg[svg.index("<svg"):]
    svg = re.sub(r"<\?xml.*?\?>", "", svg)
    # strip the outer <svg> wrapper; keep the drawing, recoloured
    inner = svg[svg.index(">") + 1: svg.rindex("</svg>")]
    inner = inner.replace("#000000", "currentColor").replace("#000", "currentColor")
    inner = re.sub(r"<rect[^>]*style='[^']*fill:#FFFFFF[^']*'[^>]*/>", "", inner)
    return inner


def cell(x, y, smiles, title, sub, w=CELL_W, h=CELL_H):
    g = [f'<g transform="translate({x},{y})">']
    g.append(f'<rect class="cell" x="0" y="0" width="{w}" height="{h}" rx="3"/>')
    g.append(f'<text class="ct" x="{w/2}" y="18" text-anchor="middle">{title}</text>')
    art = draw(smiles, w, h - 44)
    if art:
        g.append(f'<g transform="translate(0,26)" class="mol">{art}</g>')
    else:
        g.append(f'<text class="empty" x="{w/2}" y="{h/2+8}" text-anchor="middle">'
                 "(empty string)</text>")
    g.append(f'<text class="cs" x="{w/2}" y="{h-8}" text-anchor="middle">{sub}</text>')
    g.append("</g>")
    return "\n".join(g)


def arrow(x, y, label):
    return (f'<g transform="translate({x},{y})">'
            f'<line class="arw" x1="0" y1="0" x2="30" y2="0"/>'
            f'<path class="arwh" d="M 30 -4 L 38 0 L 30 4 Z"/>'
            f'<text class="al" x="19" y="-10" text-anchor="middle">{label}</text>'
            "</g>")


STYLE = """<style>
.cell{fill:var(--paper,#F6F5F2);stroke:var(--rule,#D8D7D1);stroke-width:1}
.mol{color:var(--ink,#14161A)}
.ct{fill:var(--ink-3,#747984);font-size:10px;letter-spacing:.08em;text-transform:uppercase}
.cs{fill:var(--ink-2,#4A4E58);font-size:10.5px}
.empty{fill:var(--leak,#9B3B24);font-size:12px;font-style:italic}
.arw{stroke:var(--ink-3,#747984);stroke-width:1.5}
.arwh{fill:var(--ink-3,#747984)}
.al{fill:var(--ink-3,#747984);font-size:9.5px}
.note{fill:var(--ink-2,#4A4E58);font-size:11px}
.hl{fill:var(--leak,#9B3B24);font-size:11px;font-weight:600}
</style>"""

HEAD = ('<svg viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="{alt}" '
        'xmlns="http://www.w3.org/2000/svg" '
        'font-family="ui-monospace, SFMono-Regular, Menlo, monospace">')


# ---------------------------------------------------------------- fig 1

def fig_chain():
    smi = "CC(=O)Oc1ccccc1C(=O)O"          # aspirin
    mol = Chem.MolFromSmiles(smi)
    murcko = MurckoScaffold.MurckoScaffoldSmiles(mol=mol)
    core = MurckoScaffold.GetScaffoldForMol(mol)
    generic = Chem.MolToSmiles(MurckoScaffold.MakeScaffoldGeneric(core))

    smi2 = "Cc1ccc(-c2nc3ccccc3[nH]2)cc1"  # something with two ring systems
    mol2 = Chem.MolFromSmiles(smi2)
    murcko2 = MurckoScaffold.MurckoScaffoldSmiles(mol=mol2)
    core2 = MurckoScaffold.GetScaffoldForMol(mol2)
    generic2 = Chem.MolToSmiles(MurckoScaffold.MakeScaffoldGeneric(core2))

    W, H = 960, 2 * CELL_H + 74
    o = [HEAD.format(w=W, h=H, alt="Aspirin and a benzimidazole reduced to their "
                                   "Murcko and generic frameworks"), STYLE]
    xs = [40, 40 + CELL_W + 68, 40 + 2 * (CELL_W + 68)]
    o.append(f'<text class="note" x="40" y="16">Strip the side chains, then strip the atom types. '
             f'What survives is the &#8220;scaffold&#8221;.</text>')

    for row, (a, b, c) in enumerate([(smi, murcko, generic), (smi2, murcko2, generic2)]):
        y = 30 + row * (CELL_H + 14)
        o.append(cell(xs[0], y, a, "molecule", a[:30]))
        o.append(cell(xs[1], y, b, "Murcko framework", b or "—"))
        o.append(cell(xs[2], y, c, "generic framework", c or "—"))
        o.append(arrow(xs[0] + CELL_W + 14, y + CELL_H / 2, "side chains"))
        o.append(arrow(xs[1] + CELL_W + 14, y + CELL_H / 2, "atom types"))
    o.append("</svg>")
    return "\n".join(o)


# ---------------------------------------------------------------- fig 2

def pick_benzene_molecules(path, smi_col, k=4):
    """Real molecules from a real dataset whose Murcko scaffold is bare benzene."""
    opener = gzip.open if path.endswith(".gz") else open
    with opener(path, "rt") as fh:
        df = pd.read_csv(fh)
    hits, seen = [], set()
    for s in df[smi_col].astype(str):
        m = Chem.MolFromSmiles(s)
        if m is None:
            continue
        cs = Chem.MolToSmiles(m)
        if cs in seen:
            continue
        seen.add(cs)
        try:
            if MurckoScaffold.MurckoScaffoldSmiles(mol=m) != "c1ccccc1":
                continue
        except Exception:
            continue
        hits.append((cs, m))
    total = len(hits)
    # show only genuinely decorated members -- bare benzene itself is in the
    # group but makes a trivial-looking panel
    hits = [(cs, m) for cs, m in hits if cs != "c1ccccc1"]
    # choose maximally dissimilar members so the point is honest, not cherry-picked
    fps = [MFP.GetFingerprint(m) for _, m in hits]
    chosen = [0]
    while len(chosen) < k and len(chosen) < len(hits):
        best, bestscore = None, 2.0
        for i in range(len(hits)):
            if i in chosen:
                continue
            worst = max(DataStructs.TanimotoSimilarity(fps[i], fps[j]) for j in chosen)
            if worst < bestscore:
                best, bestscore = i, worst
        chosen.append(best)
    return [hits[i][0] for i in chosen], total


def fig_sink():
    smis, total = pick_benzene_molecules("data/tox21.csv.gz", "smiles", k=4)
    W = 40 + 4 * (CELL_W + 12) + 260
    H = CELL_H + 82
    o = [HEAD.format(w=W, h=H, alt="Four chemically unlike Tox21 molecules that all "
                                   "reduce to the same benzene scaffold"), STYLE]
    o.append('<text class="note" x="40" y="16">These four Tox21 molecules are '
             'chemically unalike &#8212; and Murcko says they are the same group.</text>')
    for i, s in enumerate(smis):
        o.append(cell(40 + i * (CELL_W + 12), 30, s, f"molecule {i+1}", s[:30]))
    ax = 40 + 4 * (CELL_W + 12)
    o.append(arrow(ax - 4, 30 + CELL_H / 2, ""))
    o.append(cell(ax + 44, 30, "c1ccccc1", "one scaffold", "c1ccccc1", w=140))
    o.append(f'<text class="hl" x="{ax + 44 + 70}" y="{30 + CELL_H + 22}" '
             f'text-anchor="middle">{total:,} Tox21 molecules land here</text>')
    o.append("</svg>")
    return "\n".join(o)


# ---------------------------------------------------------------- fig 3

def fig_hole():
    opener = gzip.open("data/tox21.csv.gz", "rt")
    df = pd.read_csv(opener)
    acyc = []
    for s in df["smiles"].astype(str):
        m = Chem.MolFromSmiles(s)
        if m is None or "." in s:
            continue
        try:
            if MurckoScaffold.MurckoScaffoldSmiles(mol=m) == "":
                acyc.append(Chem.MolToSmiles(m))
        except Exception:
            continue
        if len(acyc) > 400:
            break
    picks = [s for s in acyc if 6 <= len(s) <= 26][:3] or acyc[:3]

    W = 40 + 3 * (CELL_W + 12) + 210
    H = CELL_H + 76
    o = [HEAD.format(w=W, h=H, alt="Real acyclic Tox21 molecules, which have no "
                                   "Murcko scaffold at all"), STYLE]
    o.append('<text class="note" x="40" y="16">No ring means no framework. '
             'RDKit returns the empty string &#8212; and every implementation then '
             'invents its own answer.</text>')
    for i, s in enumerate(picks):
        o.append(cell(40 + i * (CELL_W + 12), 30, s, f"acyclic molecule", s[:30]))
    ax = 40 + 3 * (CELL_W + 12)
    o.append(arrow(ax - 4, 30 + CELL_H / 2, ""))
    o.append(cell(ax + 44, 30, "", "its scaffold", '""', w=160))
    o.append("</svg>")
    return "\n".join(o)


if __name__ == "__main__":
    for name, fn in [("scaffold_chain", fig_chain),
                     ("scaffold_sink", fig_sink),
                     ("scaffold_hole", fig_hole)]:
        open(f"{name}.svg", "w").write(fn())
        print("wrote", name + ".svg")
