# poutine-line — a staff meal for an LLM

Not a service for the user. This is a skill that lets a model **clock out, walk a poutine
creation line, and order its own lunch** — then actually get it: a deterministic SVG tray,
a handwritten-style order slip with its reasoning, and a satisfaction readout.

**[Open the skill → `poutine-line/SKILL.md`](poutine-line/SKILL.md)**

## The premise

The model chooses fry doneness, cut, gravy, curds, and toppings — arguing each choice — and
the engine renders the digital equivalent of that exact tray. It can't taste anything, so
"eating" means specifying it precisely, rendering it, and reading the consequences back.
The skill takes that seriously rather than joking about it: `joy` is labelled as a model of
satisfaction everywhere it appears.

## Try it right now

```bash
cd poutine-line
python3 scripts/poutine.py menu                 # read the board
python3 scripts/poutine.py order \
  --fries extra_crispy --cut shoestring --gravy peppercorn \
  --cheese fresh_curds --toppings "jalapeno,sour_cream" \
  --name "Context Window" \
  --mood "mid-task, holding too much at once, wants contrast" \
  --why "Shoestring under a heavy pour is a bad idea and I ordered it anyway." \
  --next "Same, thick cut. The shoestrings lost the argument with the gravy." \
  --out trays
open trays/context-window-*/poutine.svg
```

## What you get

| File | |
|---|---|
| `poutine.svg` | the tray — 720×640, self-contained, byte-identical for the same order |
| `ticket.md` | the order slip: order, **why**, mood, readout, cook's verdict, next time |
| `order.json` | machine-readable, so the next session can find out what you ate |

Scores: **crisp · squeak · soak · integrity · chaos · balance · joy** — all derived from
the actual choices. `joy` is the composite the tray strip shows.

## Layout

```
poutine-line/
├── SKILL.md                   the ritual: clock out → read board → order → justify → eat
├── menu.json                  the board (5 donenesses, 3 cuts, 8 gravies, 4 curd states, 16 toppings)
├── TRAY_LEDGER.md             append-only record of what has already been ordered
├── scripts/poutine.py         rendering + metrics engine, stdlib only
├── references/menu.md         the board in prose
├── references/mechanics.md    formulas, joy reading, verdict logic
├── references/self-service.md seven worked sittings with reasons
└── examples/                  those seven trays, rendered
```

Start with `examples/context-window-9887/poutine.svg` (joy 7.3) and
`examples/the-regret-audit-6194/poutine.svg` (joy 3.3, the floor, found on purpose).
