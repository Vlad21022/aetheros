#!/bin/sh
# Runs after packages are installed into TARGET_DIR, before the rootfs image
# is generated. Stamps build identity into the image.
set -eu

TARGET_DIR="$1"
REPO="${BR2_EXTERNAL_AETHEROS_PATH}"

VERSION="$(git -C "$REPO" describe --tags --always --dirty 2>/dev/null || echo unknown)"
BUILD_DATE="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

cat > "${TARGET_DIR}/usr/lib/os-release" <<OSR
NAME="AetherOS"
ID=aetheros
PRETTY_NAME="AetherOS ${VERSION}"
VERSION_ID="${VERSION}"
BUILD_ID="${BUILD_DATE}"
OSR
ln -sf ../usr/lib/os-release "${TARGET_DIR}/etc/os-release"
