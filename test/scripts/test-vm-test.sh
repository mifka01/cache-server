#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
FLAKE_REF="${TEST_FLAKE_REF:-${TESTS_FLAKE_REF:-${QA_FLAKE_REF:-$ROOT_DIR/test}}}"
CHECK_ATTR="blackbox-pytest-vm"
CHECK_REF="$FLAKE_REF#checks.x86_64-linux.${CHECK_ATTR}"
DRV_PATH="$(nix eval --raw "$CHECK_REF.drvPath")"

echo "[test-vm] Running pytest suite in VMs..."

if [[ "${QA_NIX_VERBOSE:-0}" == "1" ]]; then
  nix build "$CHECK_REF" -L --print-build-logs
  exit 0
fi

BUILD_LOG="$(mktemp)"
if ! nix build "$CHECK_REF" >"$BUILD_LOG" 2>&1; then
  echo "[test-vm] VM test failed before pytest output."
  echo "[test-vm] Re-run with QA_NIX_VERBOSE=1 for full Nix/VM logs."
  echo "[test-vm] Last build log lines:"
  tail -n 40 "$BUILD_LOG"
  rm -f "$BUILD_LOG"
  exit 1
fi
rm -f "$BUILD_LOG"

# Print only pytest-focused output by default.
nix log "$DRV_PATH" 2>/dev/null | python3 -c '
import sys

inside = False
for raw in sys.stdin:
    line = raw.rstrip("\n")
    if "pytest output:" in line:
        inside = True
        print(line.split("pytest output:", 1)[1].lstrip())
        continue
    if inside:
        if "==============================" in line and "passed" in line:
            if "> " in line:
                print(line.split("> ", 1)[1])
            else:
                print(line)
            break
        if "cleanup" in line:
            break
        if "(finished: run the VM test script" in line:
            break
        if "> " in line:
            print(line.split("> ", 1)[1])
        else:
            print(line)
'
