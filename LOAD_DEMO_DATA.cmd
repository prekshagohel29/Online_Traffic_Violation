@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run SETUP_MEMBER.cmd first.
  pause
  exit /b 1
)
"%~dp0.venv\Scripts\python.exe" -m scripts.seed_showcase
if errorlevel 1 (
  echo Demo setup failed. Existing accounts were not intentionally replaced.
  pause
  exit /b 1
)
echo Local test logins are in LOCAL_TEST_ACCOUNTS.md.
pause
