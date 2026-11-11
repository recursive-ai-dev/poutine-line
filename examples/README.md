# Trays the model ordered for itself

Not customer orders. Each one is a tray the model walked the line for, with its own
reasoning recorded in `ticket.md` under **Why this order** and **Next time**.

Regenerate any of them exactly:

```bash
python3 scripts/poutine.py order --seed <seed from order.json> ...
```

| Tray | Fries / cut | Gravy | Curds | Toppings | crisp · squeak · soak · chaos · **joy** | Folder |
|---|---|---|---|---|---|---|
| **Context Window** | extra_crispy / shoestring | peppercorn | fresh_curds | jalapeno, sour_cream | 8.3 · 8.2 · 6.6 · 3.8 · **7.3** | `context-window-9887/` |
| **Cook's Choice** | crispy / regular | house | extra_curds | pulled_pork, pickles | 6.7 · 7.6 · 8.3 · 2.4 · **6.3** | `cook-s-choice-8811/` |
| **First Tray** | golden / thick | chicken | fresh_curds | bacon, green_onion | 5.0 · 8.4 · 5.8 · 2.1 · **6.4** | `first-tray-9379/` |
| **Something Green, Allegedly** | golden / shoestring | vegan | extra_curds | green_onion, pickles, corn | 4.9 · 7.9 · 6.9 · 3.6 · **5.6** | `something-green-allegedly-5108/` |
| **The 2 A.M. Confabulation** | dark / thick | red_wine | cold_curds | mushroom, caramelized_onion, fried_egg | 8.8 · 4.2 · 2.8 · 3.6 · **7.2** | `the-2-a-m-confabulation-8173/` |
| **The Purist Audit** | golden / regular | house | fresh_curds | — | 5.0 · 8.3 · 7.2 · 0.0 · **5.8** | `the-purist-audit-3078/` |
| **The Regret Audit** | dark / thick | house | no_curds | chili, cheddar_shreds, hot_dog, peas, corn, sour_cream | 8.2 · 0.0 · 0.0 · 10.0 · **3.3** | `the-regret-audit-6194/` |
