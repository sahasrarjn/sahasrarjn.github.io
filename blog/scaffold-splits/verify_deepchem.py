"""
Verify the class-balance claim against DeepChem's ScaffoldSplitter EXACTLY.

deepchem 2.5.0 cannot be imported without tensorflow, so we transcribe
`ScaffoldSplitter.split` + `generate_scaffolds` + `_generate_scaffold`
verbatim from the installed source and run them on the raw CSV, with
DeepChem's own defaults (0.8 / 0.1 / 0.1, no deduplication, scaffolds keyed
on the raw SMILES string exactly as `dataset.ids` supplies them).
"""

import gzip
import sys
from collections import Counter

import numpy as np
import pandas as pd
from rdkit import Chem, RDLogger
from rdkit.Chem.Scaffolds.MurckoScaffold import MurckoScaffoldSmiles

RDLogger.DisableLog("rdApp.*")


def _generate_scaffold(smiles, include_chirality=False):
    mol = Chem.MolFromSmiles(smiles)
    return MurckoScaffoldSmiles(mol=mol, includeChirality=include_chirality)


def generate_scaffolds(ids):
    scaffolds = {}
    for ind, smiles in enumerate(ids):
        scaffold = _generate_scaffold(smiles)
        scaffolds.setdefault(scaffold, []).append(ind)
    scaffolds = {k: sorted(v) for k, v in scaffolds.items()}
    return [s for (_, s) in sorted(scaffolds.items(),
                                   key=lambda x: (len(x[1]), x[1][0]),
                                   reverse=True)]


def split(ids, frac_train=0.8, frac_valid=0.1, frac_test=0.1):
    np.testing.assert_almost_equal(frac_train + frac_valid + frac_test, 1.0)
    scaffold_sets = generate_scaffolds(ids)
    train_cutoff = frac_train * len(ids)
    valid_cutoff = (frac_train + frac_valid) * len(ids)
    tr, va, te = [], [], []
    for s in scaffold_sets:
        if len(tr) + len(s) > train_cutoff:
            if len(tr) + len(va) + len(s) > valid_cutoff:
                te += s
            else:
                va += s
        else:
            tr += s
    return tr, va, te


CASES = [
    ("BBBP",  "data/BBBP.csv",     "smiles", "p_np"),
    ("Tox21", "data/tox21.csv.gz", "smiles", "NR-AR"),
    ("HIV",   "data/HIV.csv",      "smiles", "HIV_active"),
]

FRACS = [(0.8, 0.1, 0.1), (0.7, 0.15, 0.15)]

for name, path, smi_col, lab in CASES:
    opener = gzip.open if path.endswith(".gz") else open
    with opener(path, "rt") as fh:
        df = pd.read_csv(fh)
    # DeepChem's featurizers drop molecules RDKit cannot parse; do the same,
    # but keep duplicates -- DeepChem does not deduplicate.
    keep = [i for i, s in enumerate(df[smi_col].astype(str))
            if Chem.MolFromSmiles(s) is not None]
    ids = df[smi_col].astype(str).values[keep]
    y = pd.to_numeric(df[lab], errors="coerce").values[keep]

    print(f"\n=== {name}  (n={len(ids)}, label={lab}) ===")
    for ft, fv, fte in FRACS:
        tr, va, te = split(ids, ft, fv, fte)
        yte = y[te][~np.isnan(y[te])]
        ytr = y[tr][~np.isnan(y[tr])]
        c = Counter(yte.tolist())
        frac_pos_te = (yte == 1).mean() if len(yte) else float("nan")
        frac_pos_tr = (ytr == 1).mean() if len(ytr) else float("nan")
        single = len(set(yte.tolist())) < 2
        print(f"  fracs {ft}/{fv}/{fte}: |train|={len(tr)} |valid|={len(va)} |test|={len(te)}"
              f"  test labelled={len(yte)}  test class counts={dict(c)}")
        print(f"     train %pos={frac_pos_tr:.3f}   test %pos={frac_pos_te:.3f}"
              f"   -> AUC computable: {'NO (single class)' if single else 'yes'}")
