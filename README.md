# StemScore AI — public source review snapshot

**Prepared:** 2026-11-01  
**Proposed software version:** v7.1 (not yet validated as a final release)  
**Copyright holder supplied by author:** Bavin G  
**Proposed source-code licence:** MIT

## Important release status

This is a source-code review snapshot, not a fully validated end-user release. The original package contains mixed version references (including v7.0 and v7.1), and the model provenance/reproducibility review is incomplete. Do not cite this snapshot as a validated v7.1 release until these issues are resolved.

## Contents

This snapshot contains the Python application source, supporting Python modules, test scripts, build configuration, selected documentation and model metadata.

## Deliberately excluded

- `stemscore_core.joblib`: temporarily withheld pending verification of the training-data provenance, contents and redistribution rights.
- Microscopy reference images/library: withheld pending confirmation of image ownership and redistribution permissions.
- Original GEO expression matrices and sample-level datasets: not included.
- A standalone model-training script: none was identified in the uploaded source archive.

The model metadata refers to GSE304806 and GSE314132 and reports 89 training samples. The uploaded data files alone do not establish the exact 89-sample selection, mapping and labels. A reproducible training workflow has therefore not yet been demonstrated.

## Installation and execution

See `requirements_windows.txt` and the included build configuration for the intended Windows environment. Because the trained model and microscopy references are excluded, some application features that depend on those artifacts will not run from this source-only snapshot. No claim of successful clean installation or full test-suite execution is made here.

## Validation status

The included tests and historical test logs are provided as development materials, not as proof that this snapshot passes all tests. Run the tests in a clean, isolated environment and record the exact Python and dependency versions before making a formal release.

## Licence scope

The MIT licence in this repository is intended to cover only original source code authored by the copyright holder, to the extent that the holder has the rights to license it. It does not grant rights to third-party datasets, trained model artifacts, microscopy images, trademarks, or other third-party materials.

## Intended use

StemScore AI is a research-support software tool. It is not a clinical diagnostic device and must not be used to make clinical decisions.
## Contributors

- Bavin G — Software development and project development.
- Sermaraja R — Algorithm development, including classification
  and pluripotency/proliferation scoring algorithms.

## Citation

A permanent citation and DOI will be added after a reviewed, versioned release is archived.
