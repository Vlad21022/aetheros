# AetherOS — product vision and context

The background behind the code: what AetherOS is for, what was decided and why, and
what is still open. Read this with `CLAUDE.md` and `docs/decisions.md`.

## The product in one paragraph

A calm, Apple-quality assistant for the home that can **act**, and that keeps
everything local. A hub in the house runs the agent and the models; good-looking
screens on walls and shelves show what matters right now and let you talk to it. It
controls the home, controls the owner's desktop PC, and later acts in other apps
(calendar, Teams, shopping), always asking before anything consequential. No AI
company ever sees what happens in the house.

## Why not just Home Assistant?

People will ask. The honest answer:

- Home Assistant OS already is an appliance image (Buildroot, A/B updates). The image
  layer is not the differentiator; it is plumbing.
- Home Assistant is a control panel: entities, automations, dashboards someone builds.
  AetherOS is an assistant: say what you want, the agent does it.
- Its scope stops at the home. AetherOS spans the home, the desktop PC and, later,
  the owner's apps.
- It is ambient and proactive without anyone building a dashboard.
- It is local-first by design, not an LLM add-on.
- Positioning: **AetherOS uses Home Assistant, it doesn't replace it.** HA is one
  plugin underneath and brings thousands of integrations for free.

## Scope now, scope later

- **Now:** the home (through Home Assistant) and the owner's desktop PC.
- **Later:** third-party actions — calendar, Teams meetings, eMAG orders. eMAG has no
  public consumer ordering API (its API is for sellers), so the plan there is a
  "prepared checkout": the agent finds the product and builds the cart, the person pays.

## Desktop PC ideas (the part Siri can't do)

- Wake-on-LAN on, sleep, lock or shut down; open apps and games (Steam, CS2,
  a project in VS Code); audio output, volume, media; status (GPU temperature,
  a training run, a download); file chores (move today's downloads, find a PDF).
- Scenes across home and PC: "mod gaming" (PC on, lights down, Steam, notifications
  off), "mod lucru", "plec de acasă" (PC sleeps or locks, lights off).
- Implementation: a small MCP server on Windows with an explicit allowlist. Reference
  for ideas: HASS.Agent. The PC's RTX 5070 doubles as the tier-2 model host.

## Energy

Smart plugs with power metering show what the home consumes and let Aether act on it.

- **Plugs work locally, no cloud.** Good fits: Shelly (Wi-Fi, local API, native in
  Home Assistant), Zigbee plugs with metering (need a Zigbee dongle on the hub),
  Tasmota-flashed plugs. Matter energy reporting is still uneven: check the exact model.
  Romanian sockets are Schuko (type F); check the amp rating for heaters and other big loads.
- **Optional whole-home meter** in the panel (e.g. Shelly EM / Pro 3EM, fitted by an
  electrician) for total consumption, not just what goes through plugs.
- **Home Assistant keeps the history** (recorder, long-term statistics, its energy
  dashboard). The hub reads it through the same WebSocket API; no database of our own yet.
- **Protocol:** an optional `energy` section in the snapshot (v1-compatible): power now,
  today's kWh and cost, a 24-hour series, the top consumers.
- **Tariff** in lei/kWh lives in `aether.toml`, set by the owner. Prices change; never
  hard-code them.

What it gives:

- A **Consum** widget on the near screen: now, today, cost, the biggest consumer.
- **Events from power curves:** "Mașina de spălat a terminat" in the Now bar or as the
  far screen's glance line. Probably the most useful part day to day.
- **Agent questions:** "cât a consumat PC-ul azi?", "ce stă în standby noaptea?",
  "cât m-a costat sesiunea de gaming?".
- **Scenes:** "plec de acasă" can switch off needless loads.

Safety, because a plug cuts power for real:

- **Protected plugs never switch off:** fridge, freezer, router, the hub itself. Listed in
  `aether.toml`; the hub refuses with `not_allowed`.
- **Switching a plug off is a consequential action** (confirmation), unlike lights.
- **The PC's plug is never cut while the PC is on.** The PC plugin shuts the PC down
  first; only then may the plug switch off.

## Hardware

- **Hub:** must be always on, so a dedicated low-power box, not the gaming PC. Options
  discussed: a mini PC with lots of unified memory (e.g. AMD Ryzen AI Max) for larger
  local models; a used GPU desktop (cheaper per flop, louder, higher idle draw). Not
  decided. Develop on the MacBook meanwhile.
- **Screens:** thin clients; no model runs on them (at most wake-word detection).
  - Android tablet in kiosk mode (Samsung Galaxy Tab A9+ is the leading pick: looks
    premium, can cap charging at 85 % for always-on use), mounted flush, magnetic or in
    a 3D-printed frame (Makes by Mike, Smart Home Mount). This is the default path.
  - Hacked Amazon photo frames (rooted Android, 1280×800 touch, USB power, motion
    sensor) as in Wes Bos's write-up: cheap and frame-shaped, but weak and model-specific.
  - To run real Linux on a screen later: Xiaomi Pad 5 has near-mainline support in
    postmarketOS (CPU, GPU, touch, audio, Wi-Fi working).
- All screen design targets 1280×800 at 10".

## Design

- Direction: calm, ambient, premium, with **its own identity**: graphite and pale
  stone, a generated sky that follows the hour, `mist` for what you can touch,
  `ember` for Aether, Hanken Grotesk everywhere. Two earlier directions were
  dropped: serif + mono ("funky"), then an Apple-like look with iOS colours and
  SF Pro (too close to Apple's trade dress).
- Design system and screens live on claude.ai (links in `CLAUDE.md`).
- Screens designed: far (nobody near), near (someone at the screen, with the Now
  bar), agent asking for confirmation. Next candidates: agent listening and
  replying, room controls sheet, night mode, Light theme.

## Learned from Apple HomeView (announced 13 Oct 2026)

HomeView is Apple's $299 home display. It is **not sold in the EU**, so nothing like
it is officially available in Romania. Patterns worth adopting, in our own form:

- **Two distances.** Far: the clock and one line. Near: widgets and controls.
  Driven by presence, never by a tap. Needs an optional distance band on the
  `presence` message (a v1-compatible addition).
- **Ambients** (our word; never "faces"): Ceas, Fotografii (local library), Casa,
  Camere, Cer (generative sky that reacts to movement).
- **Now bar** (our word; never "Live Activities"): a pill for what's happening now,
  such as a timer, music, or Aether working.
- **Shared vs. personal.** The home, music and timers are shared; calendars and
  messages belong to one person and appear only for them.
- **Contextual offers**, like a timer appearing when a recipe step needs one.
- **Night mode** dimmed to near-black for bedrooms.

Where AetherOS goes further: everything local (Apple sends hard Siri requests to its
cloud), it controls the desktop PC, one hub serves many screens, open, in Romanian.

### Legal guardrails (not legal advice; check with a lawyer before any release)

- Copy behaviour, never the look: no Apple layouts, icons, wallpapers or palette.
- Never use their names in the product: HomeView, Live Activities, faces, Siri,
  Liquid Retina, Flow. No licensed characters.
- Don't recreate a specific, distinctive Apple mechanism (e.g. face-gated personal
  content tied to a nearby phone). Do a freedom-to-operate check before selling.
- Face recognition is biometric data under GDPR. If used at all: on-device only,
  opt-in per person, easy to delete. Prefer voice ID or the person's phone being
  home to unlock personal content.

## Open questions

- Licence for the open-source release (not chosen yet).
- Hub hardware.
- Icon set (outline icons at 1.8px stroke until one is chosen).
- Which tablet model for the first wall screen.
