# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules, collect_data_files
hiddenimports = collect_submodules('sklearn') + collect_submodules('reportlab') + collect_submodules('skimage') + collect_submodules('matplotlib.backends') + ['openpyxl','requests','certifi','urllib3','idna','charset_normalizer','pandas','scipy','matplotlib','PIL','PIL.TiffImagePlugin','PIL.PngImagePlugin','matplotlib.backends.backend_pdf','matplotlib.backends.backend_svg','matplotlib.backends.backend_agg','matplotlib.backends.backend_tkagg','stemscore_ai.publication']
datas = collect_data_files('certifi') + [('stemscore_core.joblib','.'),('stemscore_ai','stemscore_ai'),('microscopy_reference_library','microscopy_reference_library')]
a = Analysis(['StemScoreAI_v7.py'], pathex=['.'], binaries=[], datas=datas, hiddenimports=hiddenimports, hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=['torch'], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name='StemScoreAI_v7', debug=False, bootloader_ignore_signals=False, strip=False, upx=False, console=False)
