#!/usr/bin/env bash
# run_hil.sh - mini-HIL: the ECU firmware runs on an emulated STM32 as a real CAN
# node on vcan0; the bench plays plant + BCM in real time.
# Usage (Ubuntu, repo root, .venv active):   bash 05_HIL/run_hil.sh
# Without vcan0 (e.g. CI):                  HIL_BUS=tcp bash 05_HIL/run_hil.sh
set -e

if [ "${HIL_BUS:-socketcan}" = "socketcan" ]; then
  echo "=== 0/3 vcan0 ==="
  if ! ip link show vcan0 >/dev/null 2>&1; then
    sudo modprobe vcan
    sudo ip link add dev vcan0 type vcan
  fi
  sudo ip link set up vcan0
  if pgrep -f "run_live.py|bcm_live.py" >/dev/null; then
    echo "Stop run_live.py / bcm_live.py first: only the HIL bench may drive vcan0 during the tests."
    exit 1
  fi
fi

echo "=== 1/3 Build the HIL firmware ==="
make -C 05_HIL/target

echo "=== 2/3 HIL tests (real time, about 1-2 minutes) ==="
pytest 05_HIL/tests -v --junitxml=reports/junit_hil.xml "$@"

echo "=== 3/3 Done ==="
