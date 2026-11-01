# StemScore AI v6.17 — Release Validation Protocol

## Scope
This protocol separates software acceptance checks from scientific validation. The application is intended for compatible human stem-cell gene-expression matrices. It does not claim universal performance across every cell type, species, assay, or platform.

## Software acceptance checks
1. Load the frozen model bundle and verify its expected three states and model-gene universe.
2. Parse a compatible local expression matrix and preserve sample names.
3. Reject inputs with too few compatible genes rather than forcing a prediction.
4. Confirm predicted probabilities are finite and sum to approximately 1 for each sample.
5. Confirm the same fixed input and model produce the same results within numerical tolerance.
6. Confirm CSV/PDF and microscopy exports are available; manually test GUI interactions on Windows.
7. Confirm microscopy output labels its morphology index as exploratory and does not assign an unvalidated biological state.

## Biological evaluation datasets
- Development/training: GSE304806 and GSE314132.
- Independent evaluation examples: Zenodo record 8009633 and GSE70741.
- GSE70741 is an independent hepatic differentiation example, not proof of universal cross-lineage performance.

## Leakage and reporting controls
- Do not retrain the frozen model on an unlabeled uploaded dataset.
- Keep independent evaluation labels out of feature selection and model fitting.
- Report class balance, accuracy, balanced accuracy, macro-F1, coverage, and limitations where expected labels are available.
- Treat unexpectedly perfect cross-dataset metrics as an audit trigger for sample overlap, label leakage, and split independence.
- Distinguish model probabilities from marker scores and lineage scores.
- Distinguish microscopy QC/morphology features from validated biological-state prediction.

## Interpretation safeguards
A low-coverage or out-of-scope dataset should be reported as insufficient evidence rather than silently forced into a biological state. Reference deviation is not equivalent to differentiation failure. Marker contribution is not causality. A morphology index is not a biological-state score.
