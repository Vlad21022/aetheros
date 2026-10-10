# AetherOS image (os/)

The appliance Linux image for the AetherOS hub.
Built with [Buildroot](https://buildroot.org) as a BR2_EXTERNAL tree.

**Status: milestone 1** - image builds in CI and boots in QEMU to a login prompt.
This is phase 7 of the roadmap in the root README; it waits until the hub works.

## Quick start

Run these from `os/`. Needs a Linux build host (or Docker, see below) and ~15 GB of disk.

    make build     # first run fetches Buildroot + sources; 20-40 min
    make run       # boot in QEMU; Ctrl-A then X to quit
    make smoke     # headless boot test, same as CI

Log in as `root` (no password - development builds only).

### On macOS / Windows

From the repo root, so the build can read git history for the version stamp:

    docker build -t aetheros-builder os/docker/
    docker run --rm -it -v "$PWD":/work -w /work/os aetheros-builder make build

## Layout

    configs/aetheros_x86_64_defconfig   what goes into the image
    board/aetheros/common/              overlay + post-build, all targets
    board/aetheros/x86_64/              kernel config for this target
    board/aetheros/patches/             hashes/patches for Buildroot packages
    package/                            AetherOS's own packages (empty for now)
    scripts/                            QEMU run + smoke test
    ../docs/decisions.md                why things are the way they are

## Changing the config

    make menuconfig        # or linux-menuconfig for the kernel
    make savedefconfig     # writes back into configs/
    git diff               # review, then commit

Never hand-edit output/ - it is disposable.

## Image milestones

1. **Scaffold + CI + QEMU boot** (done)
2. A/B partition layout, read-only root, persistent /data
3. Boot-to-hub: the hub service starts at boot, no login
4. RAUC signed updates with automatic rollback
5. Hardening: boot time, trimmed kernel, debug vs release builds
