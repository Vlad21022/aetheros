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

- Direction: calm, ambient, premium, Apple-oriented (system font, translucent
  widgets over a soft wallpaper, iOS colours, Home-style icon circles, iOS sheets).
  An earlier serif + mono "funky" direction was rejected.
- Design system and screens live on claude.ai (links in `CLAUDE.md`).
- Screens designed so far: ambient at rest; agent asking for confirmation.
  Next candidates: agent listening and replying (animated orb), room controls sheet,
  Light theme.

## Open questions

- Licence for the open-source release (not chosen yet).
- Hub hardware.
- Icon set for non-Apple platforms (outline icons at 1.8px stroke until then).
- Which tablet model for the first wall screen.
