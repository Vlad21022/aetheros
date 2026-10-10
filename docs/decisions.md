# Architecture decisions

Short log of why things are the way they are. Newest at the bottom.
Format: decision, reason, what would make us revisit it.

## 001 - Buildroot, not Yocto or a stock distro
Reason: an appliance image with one job. Buildroot is small, fast to learn,
and produces a complete image from one config. Yocto's layer system pays off
for product lines with many variants, which we don't have.
Revisit if: we need per-package binary updates or many hardware variants.

## 002 - Pin Buildroot LTS by tag + commit, outside the repo
Reason: the Makefile clones 2026.02.3 and verifies the commit hash. LTS gets
security fixes for a year without feature churn. Keeping Buildroot out of
the repo (BR2_EXTERNAL) keeps our diff small and upgrades a one-line change.
Revisit if: we need to patch Buildroot core (switch to a submodule on a fork).

## 003 - x86_64 in QEMU as the first target
Reason: no dedicated hardware yet. QEMU gives a reproducible device that CI
can boot headlessly. An aarch64 (Raspberry Pi) defconfig is added later as
a second target, not a rewrite.

## 004 - systemd as init
Reason: RAUC's boot-confirmation flow (milestone 4) and the future shell and
sidecar services are cleaner with unit files, dependencies and watchdogs.
Cost is a few MB and slightly slower boot versus busybox init.
Revisit if: boot time or image size becomes a hard constraint.

## 005 - Prebuilt Bootlin glibc toolchain
Reason: cuts ~30 minutes from every clean build and CI run. glibc because
systemd requires it.
Revisit if: we need a custom-built toolchain (e.g. specific CPU tuning).

## 006 - Kernel config copied from Buildroot's qemu_x86_64 board
Reason: known-good starting point. We own the copy in board/aetheros/ so we
can trim it without touching Buildroot. Trim it in milestone 5.

## 007 - One monorepo: os/, hub/, shell/, contracts/, design/
Reason: the hub, the screen and the image change together. One repo keeps the
protocol, its examples and both implementations in the same commit, with CI per part.
Revisit if: a part gets its own release cycle or contributors.

## 008 - Everything runs locally
Reason: the point of the product. Models, speech and data stay in the home; no
cloud fallback. External services are reached only when an action needs them
(a calendar invite, an order), never to think.
Revisit if: never for inference; per plugin for actions.

## 009 - The hub is the brain, screens are terminals
Reason: one agent, one set of credentials and plugins, one memory, any number of
screens. Screens never run actions; they send taps, speech and confirmations.
Revisit if: a screen must work while the hub is down (then: cached snapshot only).

## 010 - Hub <-> screen protocol: JSON over WebSocket, JSON Schema as the contract
Reason: simple to debug, works from Flutter and Python, streams naturally. The schema
in contracts/ is the source of truth; both sides are tested against the same examples.
Revisit if: we need binary audio on the same connection (add a second channel).

## 011 - Three tiers of intelligence
Tier 0: fixed rules straight to Home Assistant, no model. Tier 1: a small local model
on the hub, always on. Tier 2: a large local model on the desktop PC's GPU, woken
with Wake-on-LAN when tier 1 can't handle a request.
Reason: most requests need no model at all, and the hub must stay cheap and silent.

## 012 - Consequential actions need confirmation
Reason: read-only actions run, reversible ones run and report, consequential ones
(shutting down a PC, sending anything to another person, spending money) wait for a
confirm.request / confirm.response round trip. Allowlisted actions only, never a free shell.

## 013 - Home Assistant is a plugin, reached over MCP
Reason: it already speaks every home protocol. AetherOS adds the agent and the
experience on top instead of re-implementing HomeKit, Zigbee or Matter.

## 014 - Flutter for every screen; tokens generated from the design system
Reason: one codebase for the Mac (development), Linux and Android tablets (kiosk).
design/tokens.json is exported from the AetherOS design system and turned into Dart by
tools/gen_tokens.py; CI fails if the generated file is stale.

## 015 - Apple-oriented visual language; SF Pro on Apple, Inter elsewhere
Reason: calm, premium, familiar. SF Pro's licence limits it to Apple platforms, so
other platforms use Inter, its closest open alternative.

## 016 - Build order: brain before packaging
Reason: the image (os/) packages a product that must exist first. Phases: contract,
hub with tier 0, screen on the Mac, agent (tier 1), voice, PC plugin and tier 2,
tablet screens, then the image, then external actions.

## 017 - State and tier 0 use Home Assistant's WebSocket API; MCP stays for the agent
Reason: the ambient screen needs changes pushed the moment they happen, and tier 0
must call a service without a model in the loop. Home Assistant's native WebSocket API
gives both (state_changed events, call_service); MCP has no subscriptions. This narrows
013: MCP is how the agent (tier 1 and 2) reaches Home Assistant, from phase 3.
Revisit if: Home Assistant's MCP server gains state subscriptions.

## 018 - Secrets from the environment or an uncommitted .env; entities in a local TOML
Reason: the Home Assistant token must never be in the repo. The hub reads AETHER_HA_URL
and AETHER_HA_TOKEN from the environment, then from hub/.env; the environment wins, so
the appliance image can inject them from a unit file. Which entities a home shows is not
secret but is personal, so it lives in hub/aether.toml, also uncommitted; the repo carries
only the two example files. Without these settings the hub serves demo data.
Revisit if: screens need per-room layouts (then the entities file grows sections per screen).

## 019 - Tier 0 is an allowlist by domain; unlocking waits for confirmations
Reason: a tap may only do something reversible, on an entity the hub was configured
with. The table in hub/src/aether_hub/tier0.py allows lights and switches (on, off,
toggle), media players (play/pause) and locks (lock only). Unlocking a door, covers and
thermostats are refused with not_allowed until the confirm.request flow exists (phase 3).
While Home Assistant is away, controls fail with unavailable and tiles say "Indisponibil":
the hub never falls back to demo data silently.
Revisit if: a domain proves safe enough to add (each new rule needs a test).

## 020 - The hub tells screens what can be tapped; new control actions are additive
Reason: the hub decides, screens display. A tile carries `tap` (the action a tap sends) and
now playing carries `entityId` and `controls`, both computed next to the tier 0 rules, so a
screen never offers what the router would refuse and holds no rules of its own. A screen
also never changes a tile by itself: it shows "Se trimite…" until the reply, and the new
state arrives as state.update. `control.action` gained `next` and `previous`; extending an
enum on a screen-to-hub message stays within v1 because hub and screens ship from one repo
and an older hub answers an unknown value with bad_message instead of misbehaving.
Revisit if: screens and hub are released separately (then new actions need a capability
handshake in hello/welcome).
