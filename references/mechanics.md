# Mechanics — how the readout is computed

Use these if you need to reason about an order without running the script, or if Python
is unavailable and you must write `ticket.md` by hand. All values clamp to 0–10.

Let `F` = fry crisp, `G` = gravy weight, `C` = gravy coverage, `S` = curd squeak,
`T` = number of distinct toppings, `B` = extra portions beyond the first (sum of
`count - 1`), `k` = 1 for thick cut else 0.

```
crisp          = F − 0.40·G − 0.12·T − 0.10·B
soak           = 10·C·soak_curds − 0.4·k          (soak_curds: fresh 1.0, double 1.15,
                                                   cold 0.5, none 0.0)
squeak         = S − 0.45·G − 0.10·T
integrity      = crisp − 0.35·soak + 1.2·k
chaos          = 1.2·T + 0.8·B + Σ(synergy/clash chaos)   (+1.5 if T ≥ 6)
balance        = 6.0 + Σ(synergy/clash balance)
satisfaction   = 0.32·balance + 0.28·crisp + 0.25·squeak + 0.15·integrity
                 − 0.22·max(0, chaos − 6) − 1.6·[no curds]      ("joy")
```

## Reading the joy score (staff meal)

Joy is the composite shown on the tray strip. It is **a model of satisfaction**, computed
from the order — the ticket says so in one line and you should never imply otherwise.

- **≥ 7** — a good tray by this model's own arithmetic. Say what carried it: usually
  room-temp curds plus either a light gravy or a fry built for a heavy one.
- **5.5–7** — fine. Most honest orders land here. Don't apologise for it.
- **4–5.5** — something in the order is working against the order. Name it (cold curds,
  six toppings, a shoestring soup) rather than calling the tray bad.
- **< 4** — you went to the floor on purpose, or made three mistakes without noticing.
  Both are legitimate; only one is worth repeating.

## Reading it out loud

- **Crisp ≥ 7** — "crunch survives the pour." **< 4** — "the gravy won."
- **Squeak ≥ 7** — the curds are squeaking, which is the entire point. **< 4** — say
  plainly that there's no squeak; don't dress it up.
- **Soak ≥ 6 with shoestring** — it's a soup now. Say so.
- **Integrity ≥ 7.5** — tray survives the walk to the car. **< 5** — eat it standing up.
- **Chaos ≥ 7** — delicious and indefensible. **≤ 2.5** — the cook nods once.
- **Balance** is not a quality score, it's a *fit* score: 4–7 is normal and fine,
  >8 means the order knows what it's doing, <3 means the tray has an argument on it.

## Verdict logic (short form)

Pick 2–3 of these, don't recite all of them:

| Trigger | Line |
|---|---|
| integrity ≥ 7.5 | Tray holds. Survives the walk to the car. |
| 5 ≤ integrity < 7.5 | Fine if you eat standing up. |
| integrity < 5 | Eat it over the tray. Do not attempt the drive home. |
| squeak ≥ 7 | Curds are squeaking. The whole point. |
| 4 ≤ squeak < 7 | Curds went quiet under the gravy — still good, just not talking. |
| squeak < 4 | No squeak. We're not going to pretend that's optimal. |
| gravy `house` | Packet-style sauce brune: the line knows what you did and respects it. |
| gravy veg | Vegetarian gravy, properly labelled. Nobody's guessing. |
| chaos ≥ 7 | Too many opinions. Will be delicious and indefensible. |
| chaos ≤ 2.5 | Disciplined order. The cook will nod at you once. |
| fries `dark` | Heroic if it works, bitter if it doesn't. |
| shoestring + soak > 5.5 | Those shoestrings are technically a soup now. |
| cheese `no_curds` | Without curds this is fries with gravy. We'll still make it. Reluctantly. |
| cheese `cold_curds` | Cold curds don't melt. They sit there, dignified and stubborn. |

## The renderer

`scripts/poutine.py` is stdlib-only and deterministic. Internals, if you need to extend:

- `pile_pt()` — rejection-samples a point inside the pile ellipse, biased denser and
  higher toward the centre, so the mound reads as volume rather than a scatter.
- Draw order: tray → contact shadow → fry bed → fries → sunk curds → gravy → top curds →
  stray fries → toppings → steam → ticket strip.
- The seed is `md5(order)[:8]`; each layer gets `seed + n` so layers stay independent but
  reproducible. Same order, same bytes — that's a feature, don't "fix" it.
- Gravy renders as overlapping translucent lobes plus drips and specular streaks, not one
  solid shape; that's what keeps curds and potato visible through it.
- Colours come from `menu.json`. Add a topping by adding a key there with a `glyph` from:
  `strip, cube, shred, disk, ring, cap, slice, kernel, bead, dollop, chunk` (falls back to
  a soft ellipse if unknown).

## Failure modes to avoid

- Don't pass a raw user string as `--name` with shell metacharacters unquoted; quote it.
  `&` and `<` are escaped in the SVG, but the shell is not so forgiving.
- `--toppings ""` is legal and renders the no-topping purist tray.
- If a filename slug collides (`out/the-line-cook-s-whim-1234` exists), the script
  overwrites that tray. Pass a different `--name` or `--seed` for a new file.
- The viewer may block external fetches; the SVG is self-contained, so present the file
  directly rather than embedding it in an HTML page that loads siblings.
