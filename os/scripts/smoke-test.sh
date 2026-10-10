#!/usr/bin/env bash
# Headless boot test. Passes when the image reaches a login prompt with no
# failed systemd units reported on the console.
set -euo pipefail

IMAGES="${1:?usage: smoke-test.sh <images-dir>}"
TIMEOUT="${TIMEOUT:-240}"
LOG="$(mktemp)"
source "$(dirname "$0")/qemu-args.sh"

qemu-system-x86_64 "${QEMU_ARGS[@]}" \
  -display none -serial "file:${LOG}" \
  -append "rootwait root=/dev/vda console=ttyS0" &
QPID=$!

cleanup() { kill "$QPID" 2>/dev/null || true; rm -f "$LOG"; }
trap cleanup EXIT

fail() {
  echo "SMOKE TEST FAILED: $1"
  echo "----- serial log -----"
  cat "$LOG"
  exit 1
}

for ((t = 0; t < TIMEOUT; t++)); do
  if grep -q "aetheros login:" "$LOG"; then
    if grep -q "\[FAILED\]" "$LOG"; then fail "systemd reported failed units"; fi
    echo "SMOKE TEST PASSED: login prompt after ~${t}s"
    exit 0
  fi
  kill -0 "$QPID" 2>/dev/null || fail "QEMU exited before reaching login"
  sleep 1
done

fail "no login prompt within ${TIMEOUT}s"
