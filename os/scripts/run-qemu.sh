#!/usr/bin/env bash
# Boot an AetherOS image interactively.
#   run-qemu.sh <images-dir>          serial console in this terminal
#   run-qemu.sh <images-dir> --gui    QEMU window (virtio-vga) + serial here
# Exit the serial console with Ctrl-A then X.
set -euo pipefail

IMAGES="${1:?usage: run-qemu.sh <images-dir> [--gui]}"
MODE="${2:-}"
source "$(dirname "$0")/qemu-args.sh"

if [ "$MODE" = "--gui" ]; then
  exec qemu-system-x86_64 "${QEMU_ARGS[@]}" \
    -device virtio-vga -serial mon:stdio \
    -append "rootwait root=/dev/vda console=tty1 console=ttyS0"
else
  exec qemu-system-x86_64 "${QEMU_ARGS[@]}" \
    -nographic \
    -append "rootwait root=/dev/vda console=ttyS0"
fi
