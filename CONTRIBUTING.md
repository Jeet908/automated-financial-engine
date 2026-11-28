# Contributing to MarketLens Analytics

Thank you for your interest in contributing to **MarketLens Analytics** (`automated-financial-engine`).

## Development Workflow

1. **Fork & Branch:** Create a descriptive feature or fix branch from `main` (e.g., `feat/sector-benchmark` or `fix/dcf-edge-case`).
2. **Environment Setup:**
   ```bash
   python -m pip install -r requirements.txt
   ```
3. **Accounting & Quality Standards:**
   - All 3-statement and DCF changes must preserve the **6 accounting invariant gates** (`Max Err: 0.000000e+00`, zero plug figures).
   - Generated `.xlsx` workbooks must pass `FormulaChecker` with zero `#REF!`, `#DIV/0!`, `#VALUE!`, or `#NAME?` errors.
   - Never commit secrets, `.env` files, or confidential client workbooks.
4. **Run the Test Suite:**
   ```bash
   py -m pytest
   ```
   Ensure all tests pass before opening a Pull Request.
5. **Commit & PR:** Use clear [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, `test:`, `chore:`) and complete the Pull Request template.
