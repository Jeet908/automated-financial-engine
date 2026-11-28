#!/usr/bin/env python
import subprocess, sys
result = subprocess.run(
    ["py", "-m", "pytest", "tests/test_gates.py", "tests/test_parity_gate6.py", "-v", "--tb=short", "--no-header"],
    cwd="C:/Users/HP/Downloads/Finance",
    capture_output=True, text=True
)
print(result.stdout)
print(result.stderr)
sys.exit(result.returncode)
