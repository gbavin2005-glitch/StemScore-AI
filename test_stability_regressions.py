"""Regression tests for StemScore AI v6.17 stability patch 2."""
from pathlib import Path
import tempfile
import numpy as np
from PIL import Image
from stemscore_ai.microscopy import analyze_image, infer_day

def main():
    root = Path(__file__).resolve().parent
    refs = root / "microscopy_reference_library" / "images"
    images = sorted(refs.glob("*.png")) if refs.exists() else []
    if images:
        result = analyze_image(str(images[0]))
        assert result["Width"] > 0 and result["Height"] > 0
        assert "Morphology_Index" in result and "QC" in result
        print("PASS: microscopy reference image analysis completes")
    with tempfile.TemporaryDirectory() as d:
        # Constant image tests empty/flat-image robustness without requiring a real cell image.
        p = Path(d) / "constant_D7.png"
        Image.fromarray(np.full((128, 128), 127, dtype=np.uint8)).save(p)
        result = analyze_image(str(p))
        assert result["Width"] == 128 and result["Height"] == 128
        assert result["Day"] == 7.0
        assert np.isfinite(result["Sharpness"])
        print("PASS: constant image returns finite QC measurements")
    assert infer_day("sample_DAY_21.png") == 21.0
    print("PASS: day metadata extraction")
    print("All stability regression tests passed.")

if __name__ == "__main__":
    main()
