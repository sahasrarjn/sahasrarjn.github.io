<!--
================================================================
MEDIUM VERSION. Do not paste this file's raw text into Medium:
Medium does not parse markdown on paste, so you would get literal
`##` and `**` characters on the page.

Use one of these instead:

  A. IMPORT (best, once the post is live)
     medium.com/p/import -> paste the public URL of the post.
     Medium pulls the text, headings and images automatically.
     Tables will not survive; upload the 5 table PNGs by hand.

  B. RICH-TEXT PASTE (works offline)
     Open index.html in a browser, Select All, Copy, paste into
     the Medium editor. Headings, bold, italic, links, lists and
     code blocks all survive. Images and tables do not; add the
     10 PNGs from img/png/ by hand at the marked positions.

This file is the running order + asset checklist for either path.

ASSETS, in the order they appear:
   1. img/png/spread.png                 (top figure)
   2. img/png/scaffold_chain.png
   3. img/png/scaffold_sink.png
   4. img/png/scaffold_hole.png
   5. img/png/hist.png
   6. img/png/table_1_distances.png
   7. img/png/table_2_acyclic_policy.png
   8. img/png/table_3_tiebreak.png
   9. img/png/table_4_model_scores.png
  10. img/png/table_5_maccs.png

CODE BLOCKS: Medium's own code blocks lose syntax colour. For the
two Python snippets, either type ``` then space in the editor, or
put them in a GitHub Gist and paste the gist URL on its own line,
which Medium embeds with highlighting.

Delete this comment block before publishing.
================================================================
-->

# Your Scaffold Split Is Not One Thing

*Two implementation choices that no paper reports moved a reported AUC by 0.185 on one dataset and did nothing on another. Which one bites you depends on a property of your data you probably haven't checked.*

![Spread of mean nearest-neighbour Tanimoto across six variants of a scaffold split, on four datasets](img/png/spread.png)

*Every blue dot is a split someone would describe in a methods section as "a scaffold split." They differ only in choices that go unreported. On Tox21 and HIV the spread **within** that one name (0.111, 0.105) is larger than the gap between the best scaffold split and a plain random split (0.067, 0.070).*

---

We argue about splits by name. Someone says "we used a scaffold split" and the room relaxes, because a scaffold split is the hard one. Someone says "random split" and the room gets suspicious.

But a split is not its name. A split is a distance: the chemical gap it puts between training and test. And that distance gets decided as much by undocumented implementation details as by the rule you cite in your methods section.

I measured this on four MoleculeNet datasets with five seeds, and trained a model on every split so I could say what the choices actually cost. Three results:

1. **Two free choices inside "scaffold split" swing a reported score by up to 0.185 AUC.** Neither one appears in anybody's methods section.
2. **Which choice matters is dataset-dependent.** It tracks a statistic you can compute in ten seconds. On the dataset where 22.7% of molecules have no scaffold, the acyclic policy is everything and group ordering does nothing. On another dataset it's the other way round.
3. **Split distance predicts the reported score** (pooled Spearman +0.67, p ≈ 9×10⁻⁶). This is not a geometric curiosity. It's your leaderboard.

There's a fourth result that came out of auditing my own first draft, which had a confounded comparison sitting in it. That story is at the end, because it's the most useful part.

---

## This alarm is not new. The quantification is what's missing.

Worth placing this honestly before going further:

- **Wallach & Heifets (2018)** introduced *AVE bias* and showed that redundancy between training and validation sets explains much of the reported performance of ligand-based methods. ([JCIM](https://pubs.acs.org/doi/10.1021/acs.jcim.7b00403), [arXiv:1706.06619](https://arxiv.org/abs/1706.06619))
- **Steshin's Lo-Hi benchmark (NeurIPS 2023)** makes essentially the measurement below, and reports that under a recommended scaffold split, 78% of test molecules still have a training neighbour above 0.4 Tanimoto. ([arXiv:2310.06399](https://arxiv.org/abs/2310.06399))
- **Yang et al. (2019)**, the chemprop paper, already randomizes scaffold-set assignment in its `scaffold_balanced` splitter. So the fact that assignment order is a free choice is documented, not discovered. ([JCIM](https://pubs.acs.org/doi/10.1021/acs.jcim.9b00237), [arXiv:1904.01561](https://arxiv.org/abs/1904.01561))

So "scaffold splits leak" is old news. What I couldn't find anywhere was a number for **what the undocumented choices cost you**, held constant one at a time, over multiple seeds, with a model attached. That's what follows.

---

## What a scaffold actually is

Bemis and Murcko (1996) split a molecule into four disjoint parts: **ring systems**, **linkers** (the paths joining rings), **side chains**, and the **framework**, which is rings plus linkers with the side chains deleted. That framework is what everyone now means by "the scaffold." A scaffold split groups molecules by it, so no framework shows up on both sides of the split.

Strip the side chains, then optionally strip the atom types as well:

![Aspirin and a benzimidazole reduced to their Murcko and generic frameworks](img/png/scaffold_chain.png)

*Two real molecules through the reduction. Aspirin keeps only its benzene ring. The whole acetyl ester and the carboxylic acid count as side chains, so they vanish. `MakeScaffoldGeneric` then turns every atom into carbon and every bond into a single bond, which is the "generic framework" row in the tables below.*

Two consequences fall straight out of that definition, and between them they explain most of what follows.

### Stripping side chains merges molecules that are not alike

![Four chemically unlike Tox21 molecules that all reduce to the same benzene scaffold](img/png/scaffold_sink.png)

*An anaesthetic-like amide, a polychlorinated dinitrile, a bromo-fluoroarene, a nitro-aniline. Every ring here is a plain benzene, so every side chain is deleted and all four reduce to `c1ccccc1`. **1,474 Tox21 molecules, 18.8% of the dataset, collapse into that one group**, which then has to move to one side of the split as a single indivisible block. Mean pairwise similarity inside it is 0.152, against 0.082 for the dataset as a whole. Barely more coherent than a random sample.*

### And a molecule with no ring has no scaffold at all

![Real acyclic Tox21 molecules, which have no Murcko scaffold at all](img/png/scaffold_hole.png)

*There's no framework to extract, so `MurckoScaffoldSmiles` returns the empty string. It isn't an error and nothing warns you. On Tox21 that's **22.7% of the dataset**, and what happens to those molecules next turns out to be the single biggest lever in this whole post.*

---

## The measurement

For each test molecule, find its nearest neighbour in the training set by Morgan fingerprint Tanimoto.

```python
from rdkit import DataStructs
from rdkit.Chem import rdFingerprintGenerator

gen = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=2048)
fps = [gen.GetFingerprint(m) for m in mols]

train_fps = [fps[i] for i in train_idx]
nn = [max(DataStructs.BulkTanimotoSimilarity(fps[i], train_fps)) for i in test_idx]

print(f"mean NN Tanimoto: {sum(nn) / len(nn):.3f}")
```

The mean is a summary; the distribution is the story. Three splits of the same 4,200 ChEMBL compounds (MoleculeNet Lipophilicity):

![Nearest-neighbour Tanimoto distributions for random, scaffold and Butina splits](img/png/hist.png)

The random split leaves **21.9% of test molecules within 0.8 Tanimoto of something in training**, including a spike at 1.0 where the fingerprint is identical to a training example. A scaffold split cuts that to 6.2%. A Butina cluster split cuts it to 0.3%.

---

## What the splits deliver

Four datasets, 70/15/15, deduplicated to unique canonical SMILES, Morgan r=2/2048. Shuffled arms are mean ± sd over 5 seeds; deterministic arms have no seed. **Lower = harder test set.**

![Mean nearest-neighbour Tanimoto for seven splits across four datasets](img/png/table_1_distances.png)

Look at the scaffold rows. They span 0.398 to 0.505 on Tox21 alone, and every one of them would go into a paper as "a scaffold split." One arm also carries a standard deviation of 0.077, which is bigger than most of the differences people publish between methods.

---

## Choice #1: what you do with molecules that have no scaffold

`MurckoScaffoldSmiles` returns `""` for any molecule with no ring. There's no principled scaffold for ethanol, and implementations disagree about what to do:

- **DeepChem's `ScaffoldSplitter`** keys on the returned string, so every acyclic molecule lands in **one shared group** that moves as a unit.
- **The common alternative** falls back to the molecule's own SMILES, giving each acyclic its own group, which is a random split for that slice.
- **Or** you cluster them by fingerprint, which is what I'd argue for.

Holding assignment order fixed (shuffled, 5 seeds) and changing *only* this:

![Changing only the acyclic policy: Tox21 moves 0.185 AUC, Lipophilicity moves nothing](img/png/table_2_acyclic_policy.png)

*(BBBP, Tox21 and HIV are AUC. Lipophilicity is Spearman.)*

On Tox21 this one undocumented choice is worth **0.185 AUC**, larger than the gap between most published methods on that benchmark. On Lipophilicity it's worth nothing at all, because Lipophilicity is 0.1% acyclic.

The error bars deserve as much attention as the means. Pooling acyclics on Tox21 creates one 1,775-molecule mega-group, and whichever side of the split it lands on dominates everything else, which gives you ±0.126 AUC across seeds. The problem with that configuration isn't difficulty. It's instability, and a single-seed paper would never notice.

---

## Choice #2: how you break ties between equal-sized scaffold groups

DeepChem sorts scaffold groups largest-first. But roughly **75% of scaffold groups contain exactly one molecule**, and that holds on every dataset here, from 2k to 41k compounds. So "sort by size" leaves most of the ordering undetermined. Something has to break the ties, and that something is an implementation detail.

DeepChem breaks them by first-index descending:

```python
scaffold_sets = [s for (scaffold, s) in sorted(
    scaffolds.items(), key=lambda x: (len(x[1]), x[1][0]), reverse=True)]
```

Change only the tie-break, holding the grouping rule and the size ordering fixed:

![Changing only the tie-break: BBBP's test set loses its negative class](img/png/table_3_tiebreak.png)

On BBBP one tie-break gives you a working benchmark and the other gives you a test set with no negatives in it, so AUC can't be computed. Same grouping rule, same sort key, same fractions.

Worth stating plainly, since this is the kind of thing that gets misread: **DeepChem's own tie-break is the good one here.** I only found the degenerate case because I'd first written the sort as `sorted(groups, key=len, reverse=True)`, which leaves ties to dict insertion order. That's the natural way to write it, it looks equivalent, and it isn't.

---

## Does any of this change the number you'd report?

This is the question my first draft never answered. A RandomForest (200 trees, Morgan counts) on every split:

![RandomForest scores across every split, four datasets](img/png/table_4_model_scores.png)

Across all 36 (dataset, split) combinations, z-scored within dataset, mean NN Tanimoto correlates with the reported score at **Spearman +0.67, p ≈ 9×10⁻⁶**. Per dataset it runs from +0.88 on HIV and +0.85 on Lipophilicity down to +0.39 on Tox21, which isn't significant on its own. Call it a strong pooled relationship rather than a law.

One anomaly worth flagging rather than burying. **On Tox21 the scaffold split scores *higher* than the random split** (0.826 vs 0.810), which is the opposite of the standard story. It sits inside the error bars, but it's there, and anyone who says "scaffold splits always lower your score" should go and look at it.

---

## The trap I fell into

My first draft recommended Butina clustering on the strength of one observation: it drove near-duplicates down to 0.2% to 1.8%, where scaffold splits left 2% to 9%.

That recommendation was circular. I'd clustered molecules by Morgan/Tanimoto and then scored the resulting split by Morgan/Tanimoto nearest-neighbour distance. Butina wins that comparison because it directly optimises the thing being measured.

The fix is to score with a fingerprint that had no part in building the split. Re-measuring with MACCS keys, 166 substructure keys on a completely different basis:

![The same splits scored with MACCS keys instead of Morgan](img/png/table_5_maccs.png)

Butina's advantage largely evaporates. On BBBP a plain DeepChem-ordered scaffold split produces a *harder* test set (0.718) than Butina does (0.755). On Tox21 they tie. Only on Lipophilicity does Butina still clearly win.

**If you build a split by optimising a similarity metric, you can't then evaluate that split with the same metric.** I'd have shipped this error if a reader hadn't torn the draft apart and spotted it.

---

## What to actually do

1. **Report mean NN Tanimoto and the ≥0.8 share next to your metric.** Twenty lines of code, and it makes results comparable across papers that currently aren't.
2. **Compute your acyclic fraction before you pick a scaffold splitter.** Above roughly 10%, the acyclic policy is a bigger lever than the split family, and you need to say which one you used.
3. **Run more than one seed and report the spread.** Some of these configurations carry ±0.12 AUC of seed variance. A single-seed comparison between two methods separated by 0.02 is measuring nothing.
4. **Never evaluate a split with the metric that built it.** Score with an independent representation, or you'll conclude your clustering method is the best splitter, which it will be, by construction.
5. **Scope your negative results.** If you ran an ablation on a split whose test molecules sat at 0.60 mean similarity to train, you have evidence about the interpolation regime. You don't have evidence about extrapolation, because extrapolation was never on your test set. That doesn't make the result wrong. It makes it narrower than the sentence you wrote about it.

The measurement takes a minute. Run it before you trust the split's name, especially when the name is the reassuring one.

---

## I published the confound first

The first version of this post claimed that group *ordering* was the big undocumented lever, and quoted a 0.078 swing on Tox21 as proof.

That comparison was confounded. My "random order" arm gave every acyclic molecule its own group, while my "DeepChem order" arm pooled them. The two arms differed in **grouping rule as well as ordering**. And I'd headlined the effect on Tox21, the one dataset out of four where 22.7% acyclics made that confound as large as it could possibly get. On the other three the ordering effect came out between 0.015 and 0.029, nowhere near 0.078.

I'd also labelled an arm "DeepChem order" without ever running DeepChem. When I finally transcribed `ScaffoldSplitter` out of the installed source and ran it properly, the real algorithm behaved differently from my reimplementation. That's how I found the tie-break result, which is now the more interesting half of this post.

So: a post telling you to measure your split instead of trusting its label, with a comparison in it whose label didn't match what it measured. I'd rather say that out loud than quietly fix it and move on.

Cheaper to learn from my draft than from your paper: **the mislabelled arm looked completely fine until someone ran the code.**

---

## Reproducing this

MoleculeNet CSVs from DeepChem's S3 bucket:

```
https://deepchemdata.s3-us-west-1.amazonaws.com/datasets/BBBP.csv
https://deepchemdata.s3-us-west-1.amazonaws.com/datasets/Lipophilicity.csv
https://deepchemdata.s3-us-west-1.amazonaws.com/datasets/tox21.csv.gz
https://deepchemdata.s3-us-west-1.amazonaws.com/datasets/HIV.csv
```

- [`split_audit.py`](split_audit.py) is the full audit: grouping and ordering as orthogonal axes, 5 seeds, MACCS cross-check, RF training.
- [`verify_deepchem.py`](verify_deepchem.py) transcribes DeepChem's `ScaffoldSplitter` verbatim and runs it under its own defaults, to check my reimplementation against the real thing.
- [`make_histogram.py`](make_histogram.py), [`make_spread.py`](make_spread.py) and [`make_scaffold_figs.py`](make_scaffold_figs.py) build the figures. The molecule drawings are RDKit depictions of real dataset entries, not illustrations.
- [`audit_results.json`](audit_results.json) holds every number in this post.
- [`svg2png.sh`](svg2png.sh) renders the figures to PNG via headless Chrome, for places that won't take SVG (Medium among them).

Needs `rdkit`, `pandas`, `numpy`, `scikit-learn`, `scipy`, and RDKit 2022.09+ for `rdFingerprintGenerator`. Butina is skipped above 15,000 molecules, since the distance matrix is O(n²), so the Butina and hybrid rows are missing for HIV.

**References**

- Bemis & Murcko, *The Properties of Known Drugs. 1. Molecular Frameworks*, J. Med. Chem. 39(15), 1996.
- Butina, *Unsupervised Data Base Clustering Based on Daylight's Fingerprint and Tanimoto Similarity*, J. Chem. Inf. Comput. Sci. 39(4), 1999.
- Wu et al., *MoleculeNet: A Benchmark for Molecular Machine Learning*, Chem. Sci. 9, 2018.
- Wallach & Heifets, *Most Ligand-Based Classification Benchmarks Reward Memorization Rather than Generalization*, JCIM 58(5), 2018.
- Yang et al., *Analyzing Learned Molecular Representations for Property Prediction*, JCIM 59(8), 2019.
- Steshin, *Lo-Hi: Practical ML Drug Discovery Benchmark*, NeurIPS 2023 Datasets & Benchmarks.
