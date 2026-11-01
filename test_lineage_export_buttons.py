"""Source-level regression checks for lineage/figure export controls (v7.1: journal-standard multi-format export)."""
from pathlib import Path

def main():
    source = (Path(__file__).resolve().parent / "StemScoreAI_v7.py").read_text(encoding="utf-8")
    assert "text='Export Lineage Trajectory (PDF/SVG/TIFF/PNG)',command=self._save_lineage_trajectory" in source
    assert "text='Export Lineage Heatmap (PDF/SVG/TIFF/PNG)',command=self._save_lineage_heatmap" in source
    assert "command=self._export_publication_pack" in source
    assert "def _save_lineage_trajectory(self):" in source
    assert "def _save_lineage_heatmap(self):" in source
    assert "pub.save_figure_all(fig,p)" in source
    print("PASS: lineage trajectory export button is wired to multi-format export")
    print("PASS: lineage heatmap export button is wired to multi-format export")
    print("PASS: publication-pack button is present")
    print("All lineage export button checks passed.")

if __name__ == "__main__":
    main()
