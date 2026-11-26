# Screen designs (design/screens/)

Copies of the artboards on the AetherOS Ambient design canvas on claude.ai (link in
`CLAUDE.md`). Use them as the visual spec when building the Flutter screens; the
rules behind them are in `../system.md`.

| File | What it shows |
|---|---|
| `Far.dc.html` | Far: nobody at the screen. Clock, glance line, orb |
| `Near.dc.html` | Near: someone at the screen. 12-column grid, calendar, Consum, Acasă, music, Now bar |
| `Confirm.dc.html` | Aether asks before a consequential action (the PC) |
| `Live.dc.html` | Interactive: far to near, a light tile answering, live power, a timer, the washer finishing |
| `Agent.dc.html` | Interactive: Aether from idle to reply (wake, listen, think, act, speak, return) |

These are canvas sources: plain HTML with inline styles, plus `{{ }}` bindings,
`<sc-if>`/`<sc-for>` and a small script that only the canvas runtime executes. Opening
them directly in a browser shows the layout with the bindings unfilled. To watch the
two interactive prototypes, open the canvas and press Play on their artboards.

Exact sizes, colours, durations and curves are in the inline styles and in the
`<helmet><style>` blocks (`@keyframes`, transitions). They follow `../system.md`; where the
two disagree, `system.md` wins.
