"""StemScore AI v6.17 smoke tests. Run from the extracted release directory."""
from __future__ import annotations
import sys
import tempfile
from pathlib import Path
import numpy as np
import pandas as pd
from stemscore_ai.core import load_bundle, rank_normalize
from stemscore_ai.input_engine import load_local_expression
from stemscore_ai.engine import classify_expression
from stemscore_ai.lineage import score_all_lineages
from stemscore_ai.microscopy import analyze_image

ROOT = Path(__file__).resolve().parent
MODEL = ROOT / 'stemscore_core.joblib'

def check(condition, message):
    if not condition:
        raise AssertionError(message)
    print('PASS:', message)

def main():
    bundle = load_bundle(MODEL)
    check(len(bundle.model_genes) == 2000, 'frozen model has 2,000 configured model genes')
    check(len(bundle.rank_universe) >= bundle.min_shared_genes, 'rank universe meets minimum shared-gene threshold')
    check(set(bundle.states) == {'Pluripotent','Progenitor','Differentiated'}, 'three expected biological states are present')

    # Deterministic synthetic expression smoke test across the complete model rank universe.
    rng = np.random.default_rng(20261009)
    genes = bundle.rank_universe
    synthetic = pd.DataFrame(rng.lognormal(mean=1.0, sigma=1.0, size=(len(genes), 3)), index=genes, columns=['D0','D5','D21'])
    synthetic.loc[['NANOG','SOX2','LIN28A','DPPA4','TDGF1','DNMT3B','ZFP42','GDF3'], 'D0'] *= 10
    synthetic.loc[['NANOG','SOX2','LIN28A','DPPA4','TDGF1','DNMT3B','ZFP42','GDF3'], 'D21'] *= 0.1
    out, meta = classify_expression(bundle, synthetic)
    prob_cols = ['Pluripotent','Progenitor','Differentiated']
    check(out.shape[0] == 3, 'prediction returns one row per sample')
    check(np.isfinite(out[prob_cols].to_numpy()).all(), 'predicted probabilities are finite')
    check(np.allclose(out[prob_cols].sum(axis=1).to_numpy(), 1.0, atol=1e-6), 'state probabilities sum to one')
    check(meta.get('analysis_mode') in {'Frozen ML core','Frozen core + training-only feature refit'}, 'prediction reports the actual prediction mode')
    check('_prediction_model' in out.attrs and '_prediction_genes' in out.attrs, 'prediction retains the exact model/features for consistent explainability')
    used_model = out.attrs['_prediction_model']
    used_genes = out.attrs['_prediction_genes']
    used_clf = used_model.named_steps['logreg']
    check(used_clf.coef_.shape[1] == len(used_genes), 'explainability feature list matches the estimator actually used')

    lineages, coverage = score_all_lineages(synthetic)
    check({'Neural','Cardiac','Hepatic'}.issubset(lineages.columns), 'all three lineage scores are generated')
    check(len(coverage.columns) == 3, 'coverage is reported for all lineage panels')

    # Optional full local-data test. This uses the supplied compatible matrix if provided.
    if len(sys.argv) > 1:
        expr_path = Path(sys.argv[1]).resolve()
        expr = load_local_expression(str(expr_path), reference_genes=bundle.rank_universe)
        result, meta = classify_expression(bundle, expr)
        check(len(result) == expr.shape[1], 'optional local dataset returns predictions for all samples')
        check(np.isfinite(result[prob_cols].to_numpy()).all(), 'optional local dataset probabilities are finite')
        check(np.allclose(result[prob_cols].sum(axis=1).to_numpy(), 1.0, atol=1e-6), 'optional local dataset probabilities sum to one')
        print('Local dataset:', expr.shape, '| model coverage:', round(meta['model_gene_coverage'], 4), '| training-only refit:', meta['training_only_refit'])
        if {'D0','D1','D2','D3','D5','D7','D9','D11','D13','D21'}.issubset(set(result.index)):
            expected = {'D0':'Pluripotent','D1':'Pluripotent','D2':'Progenitor','D3':'Progenitor','D5':'Progenitor','D7':'Differentiated','D9':'Differentiated','D11':'Differentiated','D13':'Differentiated','D21':'Differentiated'}
            check(all(str(result.loc[s,'Predicted_State']) == state for s,state in expected.items()), 'GSE70741 time-course predictions match the recorded smoke-test pattern')

    refs = ROOT / 'microscopy_reference_library' / 'images'
    candidates = sorted(refs.glob('*.png')) if refs.exists() else []
    if candidates:
        r = analyze_image(str(candidates[0]))
        check(r['Width'] > 0 and r['Height'] > 0, 'microscopy image dimensions are measured')
        check('Morphology_Index' in r and 'QC' in r, 'microscopy morphology and QC fields are returned')
        check(not any(k in r for k in ('Predicted_State','Microscopy_State')), 'microscopy QC does not invent a biological-state label')
    # Release UI safeguards: explicit validation action and global clear/new-samples action.
    app_source = (ROOT / 'StemScoreAI_v7.py').read_text(encoding='utf-8')
    check("text='Run Validation'" in app_source and 'def _run_lineage_validation(self):' in app_source, 'lineage validation has an explicit Run Validation control')
    check("text='Clear All Results / New Samples'" in app_source and 'def clear_all_results(self):' in app_source, 'global clear-all/new-samples control is available')
    check('self.expected_lineage=None; self.validation_results=None' in app_source, 'new dataset invalidates prior validation labels/results')
    print('\nAll acceptance smoke tests passed. GUI actions and Windows EXE must still be tested on Windows.')

if __name__ == '__main__':
    main()
