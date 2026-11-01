# StemScore AI v7.1 Change Log

## Publication-standard output release
- NEW `stemscore_ai/publication.py`: one drawing/export engine used for both the on-screen charts and every export, so what you see is what you publish.
- Figures: PDF + SVG (vector, editable text), TIFF (600 dpi, LZW) and PNG (600 dpi); Arial/Helvetica 6.5-8 pt; journal widths (89 / 120 / 183 mm); Okabe-Ito colour-blind-safe palette; viridis heatmaps; bold panel letters; italic gene symbols.
- State trajectory: replicates sharing a timepoint are shown as individual points plus mean +/- SD.
- Marker heatmap: rows grouped and labelled by lineage panel, labelled colour bar.
- Confusion matrix: reports n, accuracy and balanced accuracy on the panel.
- NEW one-click **Export Publication Pack**: Figure 1 (panels A-D) + individual panels, supplementary tables (tidy CSV and a multi-sheet XLSX with README/Methods and a column dictionary), Methods.txt, Figure_legends.txt and provenance.json (software versions, frozen-model SHA-256, export settings).
- Every existing figure button now saves all four formats. Microscopy PNG exports raised to 600 dpi.
- Frozen model, scores, lineage panels and all analytical results are UNCHANGED from v7.0.
- Tests: new `test_publication_export.py`; export-button tests updated; build script runs the new test.

## Not changed / still required for publication
- Independent, leakage-controlled validation and benchmark comparison against established methods are scientific work the software cannot supply.
- The Windows EXE must be rebuilt with BUILD_WINDOWS_EXE_v7.bat.

## v7.1 build fix
- Fixed "No module named matplotlib.backends.backend_pdf" in the built EXE: the PyInstaller spec now bundles all matplotlib backends and the PIL TIFF/PNG plugins, and publication.py imports the PDF/SVG writers explicitly. A test guards the spec.

## v7.1 diagnostics
- The app now writes every error and hard crash to `%USERPROFILE%\StemScoreAI_Results\StemScoreAI_crash_log.txt` and shows an error box instead of closing silently.
- BUILD_WINDOWS_EXE_v7.bat re-launches itself in a window that stays open.

## v7.1 GEO error-handling fix
- Fixed `NameError: cannot access free variable 'e'` (present since v7.0): a failed GEO download or file load now shows the REAL error (with a network hint when relevant) instead of hiding it. Traceback is also written to the crash log.
- PyInstaller spec now bundles HTTPS certificates (certifi) and requests dependencies.
- New test `test_no_deleted_exception_vars.py` prevents this bug class from returning.
