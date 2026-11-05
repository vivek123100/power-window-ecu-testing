#!/usr/bin/env bash
# run_all.sh - run the complete SIL pipeline locally (same steps as GitHub Actions).
# Usage (Ubuntu terminal, from the repo root, with .venv active):   bash run_all.sh
set -e   # stop at the first failing step

echo "=== 1/4 Static analysis (cppcheck + MISRA) ==="
mkdir -p reports/static
cppcheck --addon=misra --enable=style --std=c99 --suppress=missingIncludeSystem \
  --suppressions-list=02_SIL/misra_suppressions.txt \
  --error-exitcode=1 -I 02_SIL/src 02_SIL/src/window_ctrl.c 2>&1 | tee reports/static/misra.txt

echo "=== 2/4 SIL + CAN tests + back-to-back (with coverage) ==="
rm -rf build
COVERAGE=1 pytest 02_SIL/tests 03_CAN/tests -q --junitxml=reports/junit.xml

echo "=== 3/4 Coverage (must be >= 90 % lines) ==="
mkdir -p reports/coverage
gcovr -r . --filter 02_SIL/src/ --fail-under-line 90 build/
gcovr -r . --filter 02_SIL/src/ --html-details reports/coverage/index.html build/

echo "=== 4/4 Summary ==="
echo "All checks passed."
echo "Reports: reports/coverage/index.html, reports/b2b/b2b_report.md, reports/junit.xml, reports/static/misra.txt"
