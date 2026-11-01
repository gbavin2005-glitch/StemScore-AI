from pathlib import Path
def main():
    s=(Path(__file__).resolve().parent/"StemScoreAI_v7.py").read_text(encoding="utf-8")
    assert "export_bar=ttk.Frame(f)" in s
    assert "export_bar.pack(fill='x',pady=(0,6))" in s
    assert "Export Lineage Trajectory (PDF/SVG/TIFF/PNG)',command=self._save_lineage_trajectory).pack(side='left'" in s
    assert "Export Lineage Heatmap (PDF/SVG/TIFF/PNG)',command=self._save_lineage_heatmap).pack(side='left'" in s
    print("PASS: lineage graph export buttons occupy a separate full-width row")
if __name__=="__main__": main()
