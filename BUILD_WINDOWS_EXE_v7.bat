@echo off
rem Re-launch inside a window that stays open, so the build output is never lost.
if /i not "%~1"=="inner" (
  start "StemScore build" cmd /k ""%~f0" inner"
  exit /b 0
)
setlocal
cd /d "%~dp0"
echo ============================================================
echo StemScore AI v7.1 - RELEASE BUILD
echo ============================================================
where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher was not found. Install Python 3.11 64-bit and try again.
  pause
  exit /b 1
)
if not exist .venv\Scripts\python.exe py -3.11 -m venv .venv
if not exist .venv\Scripts\python.exe (
  echo Could not create Python 3.11 environment. Check Python 3.11 installation.
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
if errorlevel 1 goto :failed
python -m pip install -r requirements_windows.txt
if errorlevel 1 goto :failed
echo Running StemScore AI acceptance tests...
python run_acceptance_tests.py
if errorlevel 1 goto :failed
echo Running StemScore AI stability regression tests...
python test_stability_regressions.py
if errorlevel 1 goto :failed
echo Running lineage export regression tests...
python test_lineage_export_buttons.py
if errorlevel 1 goto :failed
python test_lineage_export_layout.py
if errorlevel 1 goto :failed
python test_no_deleted_exception_vars.py
if errorlevel 1 goto :failed
echo Running publication export tests...
python test_publication_export.py
if errorlevel 1 goto :failed
python -m pip install --upgrade pyinstaller
if errorlevel 1 goto :failed
python -m PyInstaller --clean --noconfirm StemScoreAI_v7.spec
if errorlevel 1 goto :failed
if exist dist\StemScoreAI_v7.exe (
  echo BUILD SUCCESSFUL
  echo EXE: %CD%\dist\StemScoreAI_v7.exe
  echo You can close this window.
  pause
  exit /b 0
)
:failed
echo BUILD FAILED. Scroll up to the first Python or PyInstaller error.
pause
exit /b 1
