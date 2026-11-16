# ==============================================================================
# Automated Weekly Financial Engine Execution & GitHub Sync Script (PowerShell)
# ==============================================================================

$WorkingDir = "C:\Users\HP\Downloads\Finance"
Set-Location -Path $WorkingDir

Write-Host "[*] Executing Automated Financial Modeling & Valuation Engine..." -ForegroundColor Cyan

# 1. Run the financial engine
python run_engine.py

# 2. Run the invariant verification tests
python tests/run_tests.py

# 3. Stage the generated artifacts
git add artifacts/ README.md docs/

# 4. Check if changes are staged
$gitStatus = git status --porcelain
if ($gitStatus) {
    $timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    Write-Host "[+] Staged changes detected. Committing and pushing to GitHub..." -ForegroundColor Green
    git commit -m "chore(automated): weekly financial valuation update - $timestamp [skip ci]"
    git push origin main
    Write-Host "[✓] Push complete." -ForegroundColor Green
} else {
    Write-Host "[*] No model changes detected. Working tree clean." -ForegroundColor Yellow
}
