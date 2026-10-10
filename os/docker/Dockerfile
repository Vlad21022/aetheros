# Linux build host for machines that aren't Linux (macOS, Windows).
#   docker build -t aetheros-builder os/docker/  (from the repo root)
#   docker run --rm -it -v "$PWD":/work -w /work/os aetheros-builder make build
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential bc bzip2 ca-certificates cpio file git gzip \
      libncurses-dev patch perl python3 rsync sed tar unzip wget which \
      qemu-system-x86 \
    && rm -rf /var/lib/apt/lists/*

# Buildroot refuses to run as root.
RUN useradd -m builder
USER builder
ENV BR2_DL_DIR=/work/os/.cache/dl BR2_CCACHE_DIR=/work/os/.cache/ccache
