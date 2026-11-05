@echo off
cd /d "%~dp0"
python scripts\verify_team.py
if errorlevel 1 (
  echo All three upload packages must be merged before setup.
  pause
  exit /b 1
)
set APP_ENV=local
set DATABASE_URL=
set STORAGE_MODE=local
set DATA_DIR=%~dp0data
set JWT_SECRET_KEY=
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\setup.ps1" -SkipModels
if errorlevel 1 (
  echo Dependency setup failed. Read the error above.
  pause
  exit /b 1
)
"%~dp0.venv\Scripts\python.exe" -m scripts.fetch_assets
if errorlevel 1 (
  echo Model setup failed. Check internet access and rerun SETUP_MEMBER.cmd.
  pause
  exit /b 1
)
"%~dp0.venv\Scripts\python.exe" scripts\verify_team.py --ready
if errorlevel 1 (
  pause
  exit /b 1
)
echo Setup complete. Optionally run LOAD_DEMO_DATA.cmd, then START_PROJECT.cmd.
pause
