# AetherOS design system

Exported from the AetherOS design system on claude.ai (the source of truth; link in
`CLAUDE.md`). `tokens.json` beside this file holds the values; this file holds the rules.
Re-export both together when the design system changes.

AetherOS is a calm screen that lives in the home and an assistant that can act. The screen is read from across a room far more often than it is touched, so it changes with distance: from far away it is a clock and one useful line; when someone steps up, the widgets and controls arrive. Its look is its own: graphite and pale stone, a sky that follows the hour, mist for what you can touch, ember for Aether itself.

## Principles

- **Two distances.** *Far*: the clock (`clock-far`), one `glance` line, the orb. Nothing else. *Near*: the clock moves to `clock-near` and the widgets, home tiles and the Now bar appear. The change is triggered by presence, never by a tap.
- **The sky is the wallpaper.** A soft gradient over `ground` that follows the time of day: cool blue-grey in the morning, warm at dusk, near-black at night. Generated, never a photo, never another product's wallpaper.
- **One focus.** At most one `surface-raised` sheet on screen. Widgets sit on `material`.
- **Colour means something.** `mist` is what you can tap. `ember` is Aether. `sage` and `candle` are home state. `coral` needs a person. Nothing is coloured for decoration.
- **Shared and personal.** The home, music and timers are shared. Calendars and messages belong to one person and only appear for them.

## Ambients

The far screen is one of several ambients the household picks from: **Ceas** (clock and glance line, the default), **Fotografii** (photos from the local library, slow crossfade), **Casa** (home tiles always visible), **Camere** (camera feeds) and **Cer** (generative sky that drifts with the hour and brightens when someone moves). Never call them faces, and never use licensed characters.

## Now bar

A pill at the bottom of the near screen for what is happening right now: a running timer, music, Aether working on something. Up to two items, left to right by start time. Ember marks Aether's items; the rest use `label`.

## Layout of the near screen

- A 12-column grid: `space-12` margins, 16px gutters. Widgets span 8 + 4 columns, so every row shares the same two vertical edges; the weather line starts on the edge of the 4-column widgets.
- Rows: header 152px (date and `clock-near`), two widget rows of 220px, the Now bar at 64px; 16px between rows.
- Every widget starts the same way: a `caption` row with the widget's name on the left and its status on the right, then the content. Same padding (`space-6`) everywhere.

## Consum

- The energy widget shows power now in `large-title`, a 24-hour sparkline of today so far (2px `mist` line, a faint `mist` area under it, a dot on the latest value) and one `footnote` row: today's kWh with the cost, and the biggest consumer.
- Costs use the tariff the owner sets; always prefix estimates with ≈.
- Appliance events read from power ("Mașina de spălat · gata în ~10 min") go in the Now bar, never as alerts.

## Content

- Aether speaks in short, plain Romanian sentences, first person: "Am stins luminile." The user is "tu".
- Before anything consequential, Aether asks a question that names the action: "Opresc și PC-ul din birou?" Buttons say the verb: **Pune PC-ul în sleep**, never "OK".
- Units with a space: `21,5 °C`, `30 %`, `18:30`. 24-hour time, decimal comma.
- No exclamation marks, no emoji.

## Colour

- Dark is the default; Light only when the room is bright. Night mode dims everything to `label` at 40 % on `ground`, clock only.
- Text: `label` for primary and the clock, `label-secondary` for secondary. Both read on `ground`, `material` and `surface-raised` in both themes.
- Primary button: `mist` fill, `on-mist` label. Secondary: `fill-control` with `label`. Tertiary: text in `mist`.
- Icon discs: `candle` for lights on, `sage` for locks and healthy devices, `fill-control` for anything off.

## Type

- One family everywhere: Hanken Grotesk (SIL Open Font License), bundled with the app so it looks the same on every device and never depends on a platform font.
- `clock-far` and `clock-near` use the thin weight. `glance` is the only text on the far screen besides the clock.
- `title`, `headline`, `body`, `footnote`, `caption` for everything near. Body never below 19px, footnotes never below 15px. Tabular figures wherever numbers update.

## Space and shape

- Margins: `space-20` far, `space-12` near. Widget and sheet padding `space-6`; gaps `space-4`.
- Widgets and sheets `radius-lg`; tiles and rows `radius-sm`; buttons, discs, the Now bar and the orb `radius-full`.

## Motion: a home that is alive

The screen feels alive because **every movement reports something real**. Nothing moves for decoration. Alive like breathing, never like a casino: slow, soft, one thing at a time.

- **The sky is the weather.** Clouds drift slowly (60–120 s per pass), denser when it is cloudy; rain falls as faint streaks when it rains; the warm glow at the horizon follows the real sunrise and sunset. The slow drift also keeps a static image from sitting on the panel.
- **Far to near.** The clock shrinks and glides to the top left, the glance line fades down, the orb moves to its corner, and the widgets rise 28px and fade in, staggered 40 ms apart, weather first. One curve for all of it: about 0.6 s, `cubic-bezier(.2,.8,.2,1)`, no bounce. Near to far reverses it after 20 s without presence.
- **Aether is the orb.** It breathes (about 4 s) when idle, follows the voice level while listening, swirls (about 0.9 s per turn) while thinking or acting. Its glow is the only thing on screen that may pulse continuously.
- **Aether's states**, one orb throughout, never a second visual. Colour carries who is speaking: `mist` rings are your voice, `ember` rings are Aether's.
  - *Repaus:* small orb in its corner, breathing about every 4 s.
  - *Declanșat* (wake word heard, visible in under 300 ms): the orb inhales (shrinks to 82 %, swells to 114 %), one ring ignites outward, and it glides to the lower centre while everything behind blurs and dims to about a third. This is also the visible sign that the microphone is streaming to the hub.
  - *Ascultă:* `mist` rings expand and contract with your voice level; your words appear above as they are recognised, the newest word in `label-secondary` until it is certain.
  - *Procesează:* your sentence settles and fades back slightly; the orb's light swirls and one `ember` arc orbits it (about 1.1 s per turn). If the request goes to the PC's model, the caption says so ("Trezesc PC-ul din birou…"), never a silent wait.
  - *Acționează:* the arc speeds up and each action lands as a pill with a `sage` check, staggered 120 ms; on the near screen, the touched tile answers at the same moment.
  - *Vorbește:* `ember` rings follow Aether's voice; the reply is written out and each word lights up as it is spoken, the rest waiting at 30 %.
  - *Revine:* for 3 s a thin ring winds down around the orb, a window in which you can continue without the wake word; then the orb glides home, the background sharpens, and the conversation is saved to Discuții.
  - Not understood: the orb sways twice and the caption says "N-am înțeles. Mai spune o dată?". Microphone off: the orb becomes a hollow ring.
  - Stay distinct: no glow around the screen's edges, no light bar, no row of dots.
- **The home answers.** When a device changes state, its tile answers once: the icon disc fades to its state colour, a light that turns on glows in `candle`, and a single ring ripples outward (0.9 s). If Aether caused it, the orb swirls at the same moment, so cause and effect read together.
- **Live numbers.** The energy sparkline draws itself when the widget appears (1.4 s); the latest point pulses gently; power updates every few seconds without jumping layout. Timers deplete continuously, never in steps.
- **Events arrive softly.** A finished appliance swaps in its Now bar item (rise and fade, 0.5 s) with one `sage` glow on its disc, and becomes the far screen's glance line. No sounds or flashing unless something needs a person.
- **Budget.** Only `transform` and `opacity` animate, plus colour on a few discs; at most one continuous animation per region; everything holds 60 fps on a budget tablet.
- **Dim and wake.** Dim after 60 s without presence, over 3 s; wake in under 300 ms. Night mode stops the clouds and the orb's glow.
- **Reduced motion:** crossfades only; the sky, the orb and the ripples hold still.

## Iconography

- Outline icons, 1.8px stroke, round caps and joins, 22px inside 44px discs. No platform icon sets, no emoji.
