# Shared QEMU invocation for run-qemu.sh and smoke-test.sh. Sourced, not run.
# Expects IMAGES to point at an output/images directory.

QEMU_ARGS=(
  -M pc -m 1024 -smp 2
  -kernel "${IMAGES}/bzImage"
  -drive "file=${IMAGES}/rootfs.ext2,if=virtio,format=raw,snapshot=on"
  -nic user,model=virtio
  -no-reboot
)

# Use KVM when available (Linux host with /dev/kvm access); fall back to TCG.
if [ -w /dev/kvm ]; then
  QEMU_ARGS+=(-enable-kvm -cpu host)
fi
