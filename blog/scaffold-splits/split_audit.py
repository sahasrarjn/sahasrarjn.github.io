"""
Audit a train/test split by the chemical distance it creates -- and by what it
does to a model's reported score.

v2 fixes four defects in v1:

  1. GROUPING and ORDERING were confounded. v1 compared a "random order" arm
     that gave every acyclic molecule its own group against a "DeepChem order"
     arm that pooled all acyclics into one. Those differ in grouping rule as
     well as assignment order. Here the two axes are orthogonal and every
     comparison holds one fixed.

  2. The assignment rule was not DeepChem's. v1 used max-deficit greedy;
     DeepChem fills train to capacity, then valid, then test. That exact rule
     is implemented here and used for every arm, so ordering is the only thing
     that varies between ordering arms.

  3. Single seed. Shuffled arms now run over N_SEEDS and report mean +/- sd.

  4. Circular evaluation. Butina clusters on Morgan/Tanimoto and v1 then scored
     with Morgan/Tanimoto, so Butina optimised the scoreboard directly. Every
     distance is now also reported on MACCS keys -- a substructure-key basis
     independent of the circular fingerprint used for clustering.

New: a RandomForest is trained across every split so we can say whether a shift
in split distance moves a number anyone would actually report.

Public data only: MoleculeNet CSVs from the DeepChem S3 bucket.
"""

import gzip
import json
import random
import sys
from collections import defaultdict

import numpy as np
import pandas as pd
from rdkit import Chem, DataStructs, RDLogger
from rdkit.Chem import MACCSkeys, rdFingerprintGenerator
from rdkit.Chem.Scaffolds import MurckoScaffold
from rdkit.ML.Cluster import Butina
from scipy.stats import spearmanr
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import roc_auc_score

RDLogger.DisableLog("rdApp.*")

N_SEEDS = 5
SEEDS = [42, 43, 44, 45, 46][:N_SEEDS]
FRACS = (0.70, 0.15, 0.15)
BANDS = [(0.0, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.01)]
BUTINA_CUTOFF = 0.4
BUTINA_MAX_N = 15000
BIG_GROUP_FRAC = 0.02
RF_TREES = 200

MFPGEN = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=2048)

# name, path, smiles col, label col, task ("clf" | "reg")
DATASETS = [
    ("BBBP",          "data/BBBP.csv",          "smiles", "p_np",  "clf"),
    ("Lipophilicity", "data/Lipophilicity.csv", "smiles", "exp",   "reg"),
    ("Tox21",         "data/tox21.csv.gz",      "smiles", "NR-AR", "clf"),
    ("HIV",           "data/HIV.csv",           "smiles", "HIV_active", "clf"),
]


# ---------------------------------------------------------------- loading

def load(path, smi_col, label_col):
    opener = gzip.open if path.endswith(".gz") else open
    with opener(path, "rt") as fh:
        df = pd.read_csv(fh)
    smi_col = next(c for c in df.columns if c.lower() == smi_col.lower())
    df = df[[smi_col, label_col]].dropna(subset=[smi_col])

    mols, canon, labels = [], [], []
    seen = {}
    n_unparsed = n_multi = 0
    raw_strings = defaultdict(set)     # canonical -> set of distinct raw spellings
    n_exact_dupes = 0

    for raw, y in zip(df[smi_col].astype(str), df[label_col]):
        m = Chem.MolFromSmiles(raw)
        if m is None:
            n_unparsed += 1
            continue
        if "." in raw:
            n_multi += 1
        cs = Chem.MolToSmiles(m)
        if cs in seen:
            if raw in raw_strings[cs]:
                n_exact_dupes += 1          # byte-identical repeat
            raw_strings[cs].add(raw)
            continue
        raw_strings[cs].add(raw)
        seen[cs] = len(mols)
        mols.append(m)
        canon.append(cs)
        labels.append(y)

    # duplicates that are the SAME molecule spelled DIFFERENTLY -- the ones that
    # a raw-SMILES grouping key would wrongly split across a train/test boundary
    n_respelled = sum(len(v) - 1 for v in raw_strings.values())

    prov = {
        "rows": len(df),
        "unparsed": n_unparsed,
        "multicomponent_raw": n_multi,
        "unique_canonical": len(canon),
        "exact_duplicate_rows": n_exact_dupes,
        "respelled_duplicates": n_respelled,
    }
    return mols, canon, np.array(labels, dtype=float), prov


# ---------------------------------------------------------------- scaffolds

def murcko(mol):
    try:
        return MurckoScaffold.MurckoScaffoldSmiles(mol=mol)
    except Exception:
        return None


def generic(mol):
    try:
        core = MurckoScaffold.GetScaffoldForMol(mol)
        if core.GetNumAtoms() == 0:
            return ""
        return Chem.MolToSmiles(MurckoScaffold.MakeScaffoldGeneric(core))
    except Exception:
        return None


def butina_labels(fps, cutoff=BUTINA_CUTOFF):
    n = len(fps)
    dists = []
    for i in range(1, n):
        sims = DataStructs.BulkTanimotoSimilarity(fps[i], fps[:i])
        dists.extend(1.0 - s for s in sims)
    clusters = Butina.ClusterData(dists, n, 1.0 - cutoff, isDistData=True)
    labels = [None] * n
    for cid, members in enumerate(clusters):
        for idx in members:
            labels[idx] = cid
    return labels


# ------------------------------------------------------- grouping (axis 1)
#
# Every scheme names its acyclic policy explicitly, so no comparison can
# silently vary it.

def group_keys(scheme, mols, canon, fps):
    n = len(mols)

    if scheme == "random":
        return list(range(n))

    if scheme.startswith("scaffold") or scheme.startswith("generic"):
        base = murcko if scheme.startswith("scaffold") else generic
        keys = [base(m) for m in mols]
        policy = scheme.split("__")[1]
        acyclic = [i for i, k in enumerate(keys) if not k]

        out = [f"S:{k}" if k else None for k in keys]
        if policy == "pooled":                      # DeepChem: one shared bucket
            for i in acyclic:
                out[i] = "A:__all__"
        elif policy == "own":                       # each acyclic its own group
            for i in acyclic:
                out[i] = f"A:{canon[i]}"
        elif policy == "butina":                    # cluster the acyclics
            if acyclic:
                sub = butina_labels([fps[i] for i in acyclic])
                for i, c in zip(acyclic, sub):
                    out[i] = f"A:c{c}"
        else:
            raise ValueError(policy)
        return out

    if scheme == "butina":
        return butina_labels(fps)

    if scheme == "hybrid":
        # Murcko + Butina acyclics + sub-cluster any oversized scaffold group
        keys = group_keys("scaffold__butina", mols, canon, fps)
        by = defaultdict(list)
        for i, k in enumerate(keys):
            by[k].append(i)
        limit = max(2, int(BIG_GROUP_FRAC * n))
        out = list(keys)
        for k, idxs in by.items():
            if len(idxs) > limit:
                sub = butina_labels([fps[i] for i in idxs])
                for i, c in zip(idxs, sub):
                    out[i] = f"{k}|c{c}"
        return out

    raise ValueError(scheme)


# ------------------------------------------------------- ordering (axis 2)

def assign_split(keys, order, seed):
    """DeepChem's assignment rule. `order` decides only the iteration order."""
    groups = defaultdict(list)
    for i, k in enumerate(keys):
        groups[k].append(i)

    if order == "largest_first":
        # deepchem.splits.ScaffoldSplitter.generate_scaffolds, verbatim:
        # indices sorted ascending within a group, then groups sorted by
        # (size, first index) DESCENDING. The tie-break is load-bearing --
        # ~75% of scaffold groups are singletons, so it decides most of them.
        g = {k: sorted(v) for k, v in groups.items()}
        sets = [s for (_, s) in sorted(g.items(),
                                       key=lambda x: (len(x[1]), x[1][0]),
                                       reverse=True)]
    elif order == "largest_first_tiesarbitrary":
        # same size ordering, ties left to dict insertion order
        sets = sorted(groups.values(), key=len, reverse=True)
    elif order == "shuffled":
        sets = list(groups.values())
        random.Random(seed).shuffle(sets)
    else:
        raise ValueError(order)

    n = sum(len(s) for s in sets)
    train_cut = FRACS[0] * n
    valid_cut = (FRACS[0] + FRACS[1]) * n

    tr, va, te = [], [], []
    for s in sets:                       # exactly deepchem.splits.ScaffoldSplitter
        if len(tr) + len(s) > train_cut:
            if len(tr) + len(va) + len(s) > valid_cut:
                te.extend(s)
            else:
                va.extend(s)
        else:
            tr.extend(s)
    return tr, va, te


# ---------------------------------------------------------------- measurement

def nn_sim(train_idx, test_idx, fps):
    tf = [fps[i] for i in train_idx]
    return np.array([max(DataStructs.BulkTanimotoSimilarity(fps[i], tf)) for i in test_idx])


def bands(sims):
    return [round(float(np.mean((sims >= lo) & (sims < hi)) * 100), 1) for lo, hi in BANDS]


def fit_score(tr, te, X, y, task, seed):
    ytr, yte = y[tr], y[te]
    ok_tr = ~np.isnan(ytr)
    ok_te = ~np.isnan(yte)
    if ok_tr.sum() < 30 or ok_te.sum() < 30:
        return None
    Xtr, Xte = X[tr][ok_tr], X[te][ok_te]
    ytr, yte = ytr[ok_tr], yte[ok_te]

    if task == "clf":
        if len(np.unique(ytr)) < 2 or len(np.unique(yte)) < 2:
            return None
        m = RandomForestClassifier(n_estimators=RF_TREES, n_jobs=-1, random_state=seed)
        m.fit(Xtr, ytr)
        return float(roc_auc_score(yte, m.predict_proba(Xte)[:, 1]))

    m = RandomForestRegressor(n_estimators=RF_TREES, n_jobs=-1, random_state=seed)
    m.fit(Xtr, ytr)
    return float(spearmanr(yte, m.predict(Xte)).statistic)


# ---------------------------------------------------------------- per-dataset

ARMS = [
    # label,                              grouping,             ordering
    ("Random",                            "random",             "shuffled"),
    ("Scaffold (acyclic=own)",            "scaffold__own",      "shuffled"),
    ("Scaffold (acyclic=pooled)",         "scaffold__pooled",   "shuffled"),
    ("Scaffold (acyclic=Butina)",         "scaffold__butina",   "shuffled"),
    # ordering axis, grouping held at DeepChem's own (acyclic=pooled)
    ("Scaffold (pooled), DeepChem order",  "scaffold__pooled",  "largest_first"),
    # same size ordering, ties broken differently -- isolates the tie-break alone
    ("Scaffold (pooled), other tie-break", "scaffold__pooled",  "largest_first_tiesarbitrary"),
    ("Scaffold (own), DeepChem order",     "scaffold__own",     "largest_first"),
    ("Generic framework (acyclic=own)",   "generic__own",       "shuffled"),
    ("Hybrid",                            "hybrid",             "shuffled"),
    ("Butina cluster",                    "butina",             "shuffled"),
]


def audit(name, path, smi_col, label_col, task):
    print(f"\n=== {name} ({task}, label={label_col}) ===", flush=True)
    mols, canon, y, prov = load(path, smi_col, label_col)
    n = len(mols)
    fps = [MFPGEN.GetFingerprint(m) for m in mols]
    maccs = [MACCSkeys.GenMACCSKeys(m) for m in mols]
    X = np.array([list(fp) for fp in fps], dtype=np.uint8)
    print(f"  n={n}  prov={prov}", flush=True)

    big = n > BUTINA_MAX_N
    results = []

    for label, grouping, order in ARMS:
        if big and ("butina" in grouping or grouping == "hybrid"):
            print(f"  {label:36s} SKIPPED (Butina O(n^2), n={n})", flush=True)
            continue

        keys = group_keys(grouping, mols, canon, fps)
        seeds = SEEDS if order == "shuffled" else [SEEDS[0]]

        mo, ma, b8, sc, ng = [], [], [], [], []
        for s in seeds:
            tr, va, te = assign_split(keys, order, s)
            if not tr or not te:
                continue
            sm = nn_sim(tr, te, fps)
            sk = nn_sim(tr, te, maccs)
            mo.append(sm.mean()); ma.append(sk.mean()); b8.append(bands(sm)[3])
            ng.append(len(set(map(str, keys))))
            v = fit_score(tr, te, X, y, task, s)
            if v is not None:
                sc.append(v)

        row = {
            "arm": label, "grouping": grouping, "ordering": order,
            "n_seeds": len(mo), "n_groups": ng[0] if ng else None,
            "morgan_mean": round(float(np.mean(mo)), 3),
            "morgan_sd": round(float(np.std(mo)), 3),
            "maccs_mean": round(float(np.mean(ma)), 3),
            "maccs_sd": round(float(np.std(ma)), 3),
            "near_dup_pct": round(float(np.mean(b8)), 1),
            "near_dup_sd": round(float(np.std(b8)), 1),
            "score_mean": round(float(np.mean(sc)), 3) if sc else None,
            "score_sd": round(float(np.std(sc)), 3) if sc else None,
            "metric": "AUC" if task == "clf" else "Spearman",
        }
        results.append(row)
        sm_s = f"{row['morgan_mean']:.3f}±{row['morgan_sd']:.3f}"
        mk_s = f"{row['maccs_mean']:.3f}±{row['maccs_sd']:.3f}"
        sc_s = (f"{row['score_mean']:.3f}±{row['score_sd']:.3f}"
                if row["score_mean"] is not None else "n/a")
        print(f"  {label:36s} morgan={sm_s}  maccs={mk_s}  "
              f"≥0.8={row['near_dup_pct']:.1f}%  {row['metric']}={sc_s}", flush=True)

    # scaffold structure, for the article's descriptive tables
    scafs = [murcko(m) for m in mols]
    cyc = [s for s in scafs if s]
    cnt = defaultdict(int)
    for s in cyc:
        cnt[s] += 1
    structure = {
        "n_molecules": n,
        "provenance": prov,
        "acyclic_pct": round(100 * sum(1 for s in scafs if not s) / n, 1),
        "murcko": len(cnt),
        "generic": len({g for g in (generic(m) for m in mols) if g}),
        "singleton_pct": round(100 * sum(1 for v in cnt.values() if v == 1) / max(1, len(cnt)), 1),
    }
    return {"dataset": name, "task": task, "structure": structure, "arms": results}


if __name__ == "__main__":
    only = sys.argv[1:] or None
    out = []
    for name, path, smi, lab, task in DATASETS:
        if only and name not in only:
            continue
        out.append(audit(name, path, smi, lab, task))
    with open("audit_v2.json", "w") as fh:
        json.dump(out, fh, indent=2)
    print("\nwrote audit_v2.json")
