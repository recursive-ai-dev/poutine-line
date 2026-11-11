# The board at Chez la Ligne

Everything below is real, in the sense that the engine will render it and the metrics
will move. Quote from here in chat; `menu.json` is the source of truth.

## Fries — how cooked

| Key | On the board | Crisp | Note |
|---|---|---|---|
| `blanched` | Blanched & Limp | 2.5 | pale, floppy, still remembers the potato |
| `golden` | Golden Classic | 6.0 | the reference fry |
| `crispy` | Crispy | 8.0 | audible from the next tray over |
| `extra_crispy` | Extra Crispy (double-fried) | 9.5 | armored. survives a slow gravy pour. |
| `dark` | Dark & Shattery (confit) | 10.0 | deep amber, borderline burnt, extremely your call |

## Cut

| Key | On the board | Width | Effect |
|---|---|---|---|
| `shoestring` | Shoestring | 6 px | soaks fast, gets soupy under heavy gravy |
| `regular` | Regular cut | 10 px | neutral |
| `thick` | Thick cut | 15.5 px | +1.2 structural integrity, slower soak |

## Gravy

| Key | On the board | Weight | Coverage | Veg |
|---|---|---|---|---|
| `chicken` | Classic Chicken Gravy | 2.0 | 0.62 | no |
| `turkey` | Country Turkey Gravy | 1.7 | 0.58 | no |
| `peppercorn` | Cracked Peppercorn | 2.4 | 0.66 | no — visible speckle |
| `red_wine` | Red Wine & Beef Demi | 2.2 | 0.64 | no |
| `mushroom` | Vegetarian Mushroom | 2.0 | 0.62 | **yes** — mushroom chunks |
| `vegan` | Vegan Brown Gravy | 1.8 | 0.60 | **yes** |
| `house` | House 'Sauce Brune' (packet style) | 2.6 | 0.72 | no — heaviest pour |
| `chipotle` | Smoked Chipotle | 2.2 | 0.65 | no |

Heavier weight = more crisp lost, more squeak lost. `house` is the one that kills a
delicate fry.

## Curds

| Key | On the board | Squeak | Behaviour |
|---|---|---|---|
| `fresh_curds` | Fresh Squeaky Curds (room temp) | 9.5 | softens properly under gravy |
| `extra_curds` | Double Squeaky Curds | 9.0 | more, bigger curds on the tray |
| `cold_curds` | Fridge-Cold Curds | 5.5 | doesn't melt, sits there dignified |
| `no_curds` | No Curds (an impostor) | 0.0 | fries with gravy. legally distinct. |

## Toppings

`bacon` · `smoked_meat` · `pulled_pork` · `pepperoni` · `hot_dog` · `green_onion` ·
`caramelized_onion` · `mushroom` · `jalapeno` · `corn` · `peas` · `pickles` ·
`fried_egg` · `sour_cream` · `chili` · `cheddar_shreds`

Double a portion with `*2` (`--toppings "bacon*2,green_onion"`).

## House rules (synergies)

| Pair | Called |
|---|---|
| bacon + green onion | The diner classic |
| pulled pork + green onion | Smoke and scallion |
| smoked meat + pickles | Montreal deli logic |
| mushroom + caramelized onion | Deep brown umami |
| jalapeño + sour cream | Cooling heat |
| fried egg + bacon | Breakfast gravity |
| chili + cheddar shreds | Chili-cheese convergence |
| corn + peas | Cafeteria nostalgia |

## Known clashes

| Pair | Called |
|---|---|
| pickles + sour cream | Dairy meets brine |
| peas + chili | Two different stews |
| hot dog + pepperoni | Carnival tray |
| sour cream + peppercorn | Cream on cream |

Six or more toppings triggers *"every forkful is a different poutine"*.
Zero toppings triggers *"Purist."* — which is a compliment.
