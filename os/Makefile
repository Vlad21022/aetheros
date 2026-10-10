# AetherOS build entry point. Wraps a pinned Buildroot with this repo as the
# BR2_EXTERNAL tree. Run `make help` for targets.

BR_VERSION ?= 2026.02.3
BR_COMMIT  ?= 679b9ead7620bbf193620d1ebf56f53c1764d37a
BR_URL     ?= https://gitlab.com/buildroot.org/buildroot.git

TARGET    ?= x86_64
DEFCONFIG := aetheros_$(TARGET)_defconfig
BR_DIR    := $(CURDIR)/buildroot
O         := $(CURDIR)/output/$(TARGET)
IMAGES    := $(O)/images

BR_MAKE = $(MAKE) -C $(BR_DIR) O=$(O) BR2_EXTERNAL=$(CURDIR)

.PHONY: all build config menuconfig savedefconfig linux-menuconfig \
        linux-savedefconfig run run-gui smoke clean distclean help

all: build

# Fetch Buildroot at the pinned tag and verify the commit, so a moved tag
# can never silently change what we build.
$(BR_DIR)/Makefile:
	git clone --quiet --depth 1 --branch $(BR_VERSION) $(BR_URL) $(BR_DIR)
	@actual=$$(git -C $(BR_DIR) rev-parse HEAD); \
	if [ "$$actual" != "$(BR_COMMIT)" ]; then \
	  echo "Buildroot $(BR_VERSION) is at $$actual, expected $(BR_COMMIT)"; \
	  rm -rf $(BR_DIR); exit 1; \
	fi

$(O)/.config: $(BR_DIR)/Makefile configs/$(DEFCONFIG)
	$(BR_MAKE) $(DEFCONFIG)

config: $(O)/.config

build: $(O)/.config
	$(BR_MAKE)

menuconfig: $(O)/.config
	$(BR_MAKE) menuconfig

# Writes the current config back to configs/$(DEFCONFIG). Commit the diff.
savedefconfig: $(O)/.config
	$(BR_MAKE) savedefconfig

linux-menuconfig: $(O)/.config
	$(BR_MAKE) linux-menuconfig

linux-savedefconfig: $(O)/.config
	$(BR_MAKE) linux-update-defconfig

run:
	scripts/run-qemu.sh $(IMAGES)

run-gui:
	scripts/run-qemu.sh $(IMAGES) --gui

smoke:
	scripts/smoke-test.sh $(IMAGES)

clean:
	rm -rf $(O)

distclean:
	rm -rf output $(BR_DIR)

help:
	@echo "make build       Build the image (first run fetches Buildroot)"
	@echo "make run         Boot in QEMU, serial console (Ctrl-A X to quit)"
	@echo "make run-gui     Boot in QEMU with a display window"
	@echo "make smoke       Headless boot test (what CI runs)"
	@echo "make menuconfig  Tweak config; then 'make savedefconfig' and commit"
	@echo "make clean       Remove output/ for this target"
	@echo "make distclean   Remove output/ and the Buildroot checkout"
