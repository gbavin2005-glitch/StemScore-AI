"""Headless regression test for journal-standard figure/table export (v7.1)."""
import json, tempfile, sys
from pathlib import Path
import numpy as np, pandas as pd
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parent))
from stemscore_ai.lineage import LINEAGE_PANELS, score_all_lineages
from stemscore_ai import publication as pub

def synth():
    rng = np.random.default_rng(7); days = [0, 0, 3, 3, 6, 6]
    names = [f"Day{d}_rep{i % 2 + 1}" for i, d in enumerate(days)]
    genes = [f"G{i}" for i in range(1500)] + [g for p in LINEAGE_PANELS.values() for g in p]
    expr = pd.DataFrame(rng.lognormal(2, 1, (len(genes), len(names))), index=genes, columns=names)
    p = rng.dirichlet([1, 1, 1], len(names))
    cur = pd.DataFrame(p, index=names, columns=["Pluripotent", "Progenitor", "Differentiated"])
    cur["Predicted_State"] = cur.idxmax(axis=1); cur["Confidence"] = p.max(1)
    scores, _ = score_all_lineages(expr)
    gl = [g for pl in LINEAGE_PANELS.values() for g in pl if g in expr.index]
    return cur, scores, expr.loc[gl].rank(axis=0, pct=True), expr

def main():
    cur, scores, ranks, expr = synth()
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
        files = pub.export_publication_pack(d, cur, scores, ranks, LINEAGE_PANELS, {"accession": "TEST"}, None,
                                            "StemScore AI test", validation=(["Neural"] * 3 + ["Cardiac"] * 3, ["Neural"] * 3 + ["Cardiac"] * 2 + ["Hepatic"], list(LINEAGE_PANELS)),
                                            expr_shape=expr.shape)
        names = {f.name for f in files}
        for ext in ("pdf", "svg", "tiff", "png"):
            assert f"Figure_1_composite.{ext}" in names, ext
        print("PASS: Figure 1 written as PDF, SVG, TIFF and PNG")
        with Image.open(Path(d) / "Figure_1_composite.tiff") as im:   # close handle (Windows cannot delete open files)
            assert round(im.info["dpi"][0]) == 600 and im.info.get("compression") == "tiff_lzw"
        print("PASS: TIFF is 600 dpi, LZW-compressed")
        assert "<text" in (Path(d) / "Figure_1_composite.svg").read_text(encoding="utf-8")
        print("PASS: SVG keeps editable text")
        pdf = (Path(d) / "Figure_1_composite.pdf").read_bytes()
        assert pdf[:4] == b"%PDF" and b"/Type3" not in pdf, "PDF must embed TrueType (Type 42), not Type 3, fonts"
        print("PASS: PDF is vector with embedded TrueType fonts (no Type 3)")
        for n in ("Table_S1_cell_state_predictions.csv", "Table_S2_lineage_scores.csv", "Table_S3_marker_rank_percentiles.csv",
                  "StemScore_Supplementary_Tables.xlsx", "Methods.txt", "Figure_legends.txt", "provenance.json"):
            assert n in names, n
        s1 = pd.read_csv(Path(d) / "Table_S1_cell_state_predictions.csv")
        assert {"Sample", "Day", "P_Pluripotent", "P_Progenitor", "P_Differentiated", "Predicted_State", "Confidence_MaxProbability"} <= set(s1.columns)
        with pd.ExcelFile(Path(d) / "StemScore_Supplementary_Tables.xlsx") as x:
            assert "README_Methods" in x.sheet_names and "Column_Dictionary" in x.sheet_names
        print("PASS: tidy CSV/XLSX tables with README and column dictionary")
        prov = json.loads((Path(d) / "provenance.json").read_text())
        assert prov["figure_export"]["raster_dpi"] == 600 and "scikit_learn" in prov
        print("PASS: provenance file records versions and export settings")
        # without validation the composite must still render (panel D placeholder)
        fig = pub.fig_composite(cur, scores, ranks, LINEAGE_PANELS, None); assert fig is not None
        print("PASS: composite renders without validation labels")
    spec = (Path(__file__).resolve().parent / "StemScoreAI_v7.spec").read_text(encoding="utf-8")
    for need in ("matplotlib.backends.backend_pdf", "matplotlib.backends.backend_svg", "PIL.TiffImagePlugin"):
        assert need in spec, f"PyInstaller spec must bundle {need}"
    print("PASS: PyInstaller spec bundles the PDF/SVG/TIFF writers")
    assert pub.parse_day("Day7_rep2") == 7.0 and pub.parse_day("sampleX") is None
    print("All publication export checks passed.")

if __name__ == "__main__":
    main()
