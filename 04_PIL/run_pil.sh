#!/usr/bin/env bash
# run_pil.sh - Processor-in-the-Loop: the same SIL + CAN tests, but the controller
# runs on an emulated STM32F407 (Renode), compiled with arm-none-eabi-gcc.
# Usage (Ubuntu, repo root, .venv active):   bash 04_PIL/run_pil.sh
# Quick run of a few tests:                  bash 04_PIL/run_pil.sh -k "TC_01 or TC_04"
set -e

echo "=== 1/3 Build the firmware (arm-none-eabi-gcc, -Werror) ==="
make -C 04_PIL/target

echo "=== 2/3 Same tests as SIL, controller on the target (Renode starts automatically) ==="
TARGET=pil pytest 02_SIL/tests 03_CAN/tests -q --junitxml=reports/junit_pil.xml "$@"

echo "=== 3/3 Done ==="
echo "Reports: reports/b2b/b2b_pil_report.md (MIL vs. PIL), reports/junit_pil.xml"
