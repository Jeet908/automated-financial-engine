@echo off
REM ==============================================================================
REM Automated Weekly Financial Engine Execution & GitHub Sync Script (Windows Batch)
REM Logs all output to scripts\sync.log for full auditability
REM ==============================================================================

cd /d "C:\Users\HP\Downloads\Finance"
set LOGFILE=C:\Users\HP\Downloads\Finance\scripts\sync.log

echo ======================================================== >> "%LOGFILE%" 2>&1
echo [*] Weekly Sync Started: %date% %time% >> "%LOGFILE%" 2>&1
echo ======================================================== >> "%LOGFILE%" 2>&1

REM 1. Run the financial modeling engine
echo [*] Step 1: Running financial engine... >> "%LOGFILE%" 2>&1
python run_engine.py >> "%LOGFILE%" 2>&1
if errorlevel 1 (
    echo [!] ERROR: Engine run failed with exit code %errorlevel% >> "%LOGFILE%" 2>&1
    exit /b %errorlevel%
)

REM 2. Run the test suite
echo [*] Step 2: Running verification tests... >> "%LOGFILE%" 2>&1
python tests\run_tests.py >> "%LOGFILE%" 2>&1
if errorlevel 1 (
    echo [!] ERROR: Test suite failed with exit code %errorlevel% >> "%LOGFILE%" 2>&1
    exit /b %errorlevel%
)

REM 3. Stage updated deliverables
echo [*] Step 3: Staging updated artifacts... >> "%LOGFILE%" 2>&1
git add artifacts/ README.md docs/ >> "%LOGFILE%" 2>&1

REM 4. Commit and push if changes exist
git diff --cached --quiet
if errorlevel 1 (
    echo [*] Step 4: Staged changes detected. Committing... >> "%LOGFILE%" 2>&1
    git commit -m "chore(automated): weekly financial valuation update - %date% %time% [skip ci]" >> "%LOGFILE%" 2>&1
    
    echo [*] Step 5: Pushing to GitHub (origin main)... >> "%LOGFILE%" 2>&1
    git push origin main >> "%LOGFILE%" 2>&1
    if errorlevel 1 (
        echo [!] ERROR: git push failed. Check credentials or remote URL. >> "%LOGFILE%" 2>&1
        exit /b 1
    )
    echo [✓] Successfully pushed to GitHub. >> "%LOGFILE%" 2>&1
) else (
    echo [*] Step 4: No changes in artifacts detected. Skipping push. >> "%LOGFILE%" 2>&1
)

echo [*] Weekly Sync Completed: %date% %time% >> "%LOGFILE%" 2>&1
echo ======================================================== >> "%LOGFILE%" 2>&1
