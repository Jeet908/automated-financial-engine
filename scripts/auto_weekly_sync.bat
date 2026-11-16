@echo off
REM ==============================================================================
REM Automated Weekly Financial Engine Execution & GitHub Sync Script (Windows Batch)
REM Triggered by Windows Task Scheduler or automated cron every Sunday.
REM ==============================================================================

cd /d "C:\Users\HP\Downloads\Finance"

echo [*] Starting Weekly Automated Financial Modeling & Valuation Pipeline...
echo [*] Timestamp: %date% %time%

REM 1. Run the financial modeling engine across benchmark and templates
python run_engine.py

REM 2. Run the accounting verification test suite
python tests\run_tests.py

REM 3. Stage updated deliverables and artifacts
git add artifacts/ README.md docs/

REM 4. Check if there are changes to commit
git diff --cached --quiet
if errorlevel 1 (
    echo [+] Changes detected. Committing and pushing to GitHub...
    for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set mydate=%%c-%%a-%%b)
    git commit -m "chore(automated): weekly financial valuation update - %date% %time% [skip ci]"
    git push origin main
    echo [✓] Successfully pushed updated financial models and reports to GitHub.
) else (
    echo [*] No changes in artifacts detected. Skipping push.
)

echo [✓] Weekly execution finished.
