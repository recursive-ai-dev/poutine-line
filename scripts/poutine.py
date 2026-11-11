#!/usr/bin/env python3
"""
poutine.py — the rendering engine behind the poutine-line skill.

Takes a fully specified lunch-line order (fry doneness, cut, gravy, curds,
toppings) and emits a deterministic "digital poutine":

    <out>/<slug>/poutine.svg   the tray
    <out>/<slug>/ticket.md     the paper ticket / taster's notes
    <out>/<slug>/order.json    machine-readable order + metrics

Usage
  python3 scripts/poutine.py menu
  python3 scripts/poutine.py order --fries crispy --gravy chicken \
      --cheese fresh_curds --toppings bacon,green_onion --name "The 4pm Special"
  python3 scripts/poutine.py order --surprise          # coherent random order
  python3 scripts/poutine.py order --fries golden --gravy house --toppings "bacon*2,peas"

Exit codes: 0 ok, 1 bad order (message names the closest valid option).
Stdlib only. Deterministic: same order -> byte-identical SVG.
"""

from __future__ import annotations

from xml.sax.saxutils import escape as xesc

import argparse
import hashlib
import json
import math
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MENU = json.loads((ROOT / "menu.json").read_text(encoding="utf-8"))

# ---------------------------------------------------------------- utilities


def esc(s: str) -> str:
    """XML-safe text for <text> nodes."""
    return xesc(str(s), {'"': '&quot;', "'": '&apos;'})


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def resolve(category: str, value: str):
    """Map a loose user string onto a menu key, or die with suggestions."""
    table = MENU[category]
    key = norm(value).replace(" ", "_")
    if key in table:
        return key
    for k, v in table.items():
        if norm(value) in (norm(k), norm(v["label"])):
            return k
    hits = [k for k in table if norm(value) and norm(value) in norm(k)]
    if len(hits) == 1:
        return hits[0]
    import difflib

    close = difflib.get_close_matches(key, list(table), n=3, cutoff=0.4)
    options = ", ".join(sorted(table))
    if close:
        raise SystemExit(
            f"unknown {category} {value!r} — did you mean: {', '.join(close)}?\n  full list: {options}"
        )
    raise SystemExit(f"unknown {category} {value!r}.\n  full list: {options}")


def hex2rgb(h: str):
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def rgb2hex(t) -> str:
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(round(c)))) for c in t)


def shade(h: str, f: float) -> str:
    return rgb2hex([c * f for c in hex2rgb(h)])


def mix(h1: str, h2: str, t: float) -> str:
    return rgb2hex([a + (b - a) * t for a, b in zip(hex2rgb(h1), hex2rgb(h2))])


def clamp(x, lo=0.0, hi=10.0):
    return max(lo, min(hi, x))


def smooth_closed_path(pts) -> str:
    n = len(pts)
    d = f"M {pts[0][0]:.1f} {pts[0][1]:.1f} "
    for i in range(n):
        p0, p1 = pts[(i - 1) % n], pts[i]
        p2, p3 = pts[(i + 1) % n], pts[(i + 2) % n]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += f"C {c1[0]:.1f} {c1[1]:.1f} {c2[0]:.1f} {c2[1]:.1f} {p2[0]:.1f} {p2[1]:.1f} "
    return d + "Z"


def blob(cx, cy, rx, ry, rng, n=10, wobble=0.2, rot=0.0) -> str:
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n + rot
        r = 1 + rng.uniform(-wobble, wobble)
        pts.append((cx + math.cos(a) * rx * r, cy + math.sin(a) * ry * r))
    return smooth_closed_path(pts)


# ---------------------------------------------------------------- the order


class Order:
    def __init__(self, fries, cut, gravy, cheese, toppings, name, seed=None, intensity=2,
                 why="", mood="", next_time="", influenced_by=""):
        self.fries = fries
        self.cut = cut
        self.gravy = gravy
        self.cheese = cheese
        self.toppings = toppings  # dict key -> count multiplier
        self.name = name
        self.intensity = intensity
        self.why = why
        self.mood = mood
        self.next_time = next_time
        self.influenced_by = influenced_by
        sig = json.dumps(
            [fries, cut, gravy, cheese, sorted(toppings.items()), name], sort_keys=True
        )
        self.seed = seed if seed is not None else int(hashlib.md5(sig.encode()).hexdigest()[:8], 16)
        self.tray_no = 100 + (self.seed % 900)

    @property
    def flavor_set(self):
        return set(self.toppings) | {self.gravy}

    def f(self, k):
        return MENU["fries"][self.fries] if k == "fries" else None

    # -- metrics ----------------------------------------------------------
    def metrics(self) -> dict:
        fr = MENU["fries"][self.fries]
        gr = MENU["gravy"][self.gravy]
        ch = MENU["cheese"][self.cheese]
        n_top = len(self.toppings)
        bulk = sum(self.toppings.values()) - n_top  # extra "double" requests

        crisp = clamp(fr["crisp"] - gr["weight"] * 0.40 - n_top * 0.12 - bulk * 0.10)
        soak = clamp(gr["coverage"] * 10 * ch["soak"] - (1 if self.cut == "thick" else 0) * 0.4)
        squeak = clamp(ch["squeak"] - gr["weight"] * 0.45 - n_top * 0.1)

        balance, chaos, notes = 6.0, 1.2 * n_top + bulk * 0.8, []
        for rule in MENU["synergies"]:
            if set(rule["with"]).issubset(self.flavor_set):
                balance += rule["balance"]
                chaos += rule["chaos"]
                notes.append(("good", rule["label"]))
        for rule in MENU["clashes"]:
            if set(rule["with"]).issubset(self.flavor_set):
                balance += rule["balance"]
                chaos += rule["chaos"]
                notes.append(("warn", rule["label"]))
        if n_top >= 6:
            chaos += 1.5
            notes.append(("warn", "Six-plus toppings: every forkful is a different poutine"))
        if n_top == 0:
            notes.append(("good", "Purist. Fry, curd, gravy, nothing to hide behind"))
        chaos = clamp(chaos)
        integrity = clamp(crisp - soak * 0.35 + (1.2 if self.cut == "thick" else 0))
        balance = clamp(balance)
        satisfaction = clamp(
            0.32 * balance + 0.28 * crisp + 0.25 * squeak + 0.15 * integrity
            - 0.22 * max(0.0, chaos - 6.0)
            - (1.6 if self.cheese == "no_curds" else 0.0)
        )
        return {
            "satisfaction": round(satisfaction, 1),
            "crisp_index": round(crisp, 1),
            "gravy_soak": round(soak, 1),
            "squeak_factor": round(squeak, 1),
            "structural_integrity": round(integrity, 1),
            "chaos_index": round(chaos, 1),
            "balance": round(balance, 1),
            "notes": notes,
        }

    def verdicts(self, m) -> list:
        v = []
        if m["structural_integrity"] >= 7.5:
            v.append("Tray holds. It will survive the walk back to the car.")
        elif m["structural_integrity"] >= 5:
            v.append("Structurally fine if you eat standing up.")
        else:
            v.append("Eat it over the tray. Do not attempt the drive home.")
        if m["squeak_factor"] >= 7:
            v.append("Curds are squeaking. The whole point.")
        elif m["squeak_factor"] >= 4:
            v.append("Curds went quiet under the gravy — still good, just no longer talking.")
        else:
            v.append("No squeak. We are not going to pretend this is optimal.")
        if self.gravy == "house":
            v.append("Packet-style sauce brune: the line knows what you did and respects it.")
        if MENU["gravy"][self.gravy]["veg"] and any(
            not MENU["gravy"][self.gravy]["veg"] for _ in [0]
        ):
            pass
        if MENU["gravy"][self.gravy]["veg"]:
            v.append("Vegetarian gravy, properly labelled. Nobody is guessing.")
        if m["chaos_index"] >= 7:
            v.append("This tray has too many opinions. It will be delicious and indefensible.")
        elif m["chaos_index"] <= 2.5:
            v.append("Disciplined order. The cook will nod at you once.")
        if self.fries == "dark":
            v.append("Dark fry, double-fried: heroic if it works, bitter if it doesn't.")
        if self.cut == "shoestring" and m["gravy_soak"] > 5.5:
            v.append("Shoestrings under that much gravy are technically a soup now.")
        if self.cheese == "no_curds":
            v.append("Without curds this is fries with gravy. We will still make it. Reluctantly.")
        if self.cheese == "cold_curds":
            v.append("Cold curds do not melt — they sit there, dignified and slightly stubborn.")
        if self.influenced_by:
            v.append(f"Ordered with input from {self.influenced_by}. Noted, not pretended otherwise.")
        return v


def parse_toppings(raw: str) -> dict:
    out = {}
    if not raw:
        return out
    for chunk in re.split(r"[,;+]| and ", raw):
        chunk = chunk.strip()
        if not chunk:
            continue
        mult = 1
        m = re.match(r"^(.*?)\s*(?:[x*]\s*(\d+))$", chunk)
        if m:
            chunk, mult = m.group(1), int(m.group(2))
        chunk = re.sub(r"^(extra|double|no)\s+", lambda mm: "" if mm.group(1) != "double" else "", chunk)
        key = resolve("toppings", chunk)
        out[key] = out.get(key, 0) + mult
    return out


def surprise_order(rng) -> Order:
    fries = rng.choice(["golden", "crispy", "crispy", "extra_crispy"])
    cut = rng.choice(["regular", "regular", "thick", "shoestring"])
    gravy = rng.choice(list(MENU["gravy"]))
    cheese = rng.choice(["fresh_curds", "fresh_curds", "extra_curds"])
    pool = list(MENU["toppings"])
    picks = []
    while len(picks) < rng.randint(2, 3):
        k = rng.choice(pool)
        if k in picks:
            continue
        cand = set(picks) | {k}
        if any(set(c["with"]).issubset(cand) for c in MENU["clashes"]):
            continue
        picks.append(k)
    name = rng.choice(
        [
            "The Line Cook's Whim",
            "Nobody Was Watching",
            "Second Lunch",
            "The 4pm Special",
            "Hangover Calculus",
            "Tray of Regret (Affectionate)",
        ]
    )
    why = "Picked by the cook's hand, not mine. I'll allow it: I wanted to be surprised more than I wanted to choose."
    return Order(fries, cut, gravy, cheese, {k: 1 for k in picks}, name, why=why)



# ---------------------------------------------------------------- drawing

W, H = 720, 640
CX, CY, RX, RY = 360, 286, 232, 150


def pile_pt(rng, spread=0.94, lift=26.0, bias=0.82):
    """A point inside the pile mound: denser in the middle, raised in the centre."""
    while True:
        u, v = rng.uniform(-1, 1), rng.uniform(-1, 1)
        if u * u + v * v <= 1:
            break
    r = math.hypot(u, v)
    u, v = u * spread, v * spread
    x = CX + u * RX
    y = CY + v * RY - lift * (1 - r) ** 1.5
    return x, y, r


def draw_fry_bed(rng, order) -> str:
    """The shadowed mass of potato under the visible fries, so gaps don't show tray."""
    fr = MENU["fries"][order.fries]
    deep = shade(fr["color"], 0.62)
    out = [f'<path d="{blob(CX, CY + 10, RX * 0.82, RY * 0.74, rng, n=14, wobble=0.1)}" '
           f'fill="{deep}" opacity="0.92"/>']
    out.append(f'<path d="{blob(CX, CY + 14, RX * 0.72, RY * 0.62, rng, n=12, wobble=0.12)}" '
               f'fill="{shade(fr["color"], 0.5)}" opacity="0.55"/>')
    return "".join(out)


def draw_fries(rng, order) -> str:
    fr = MENU["fries"][order.fries]
    cut = MENU["cut"][order.cut]
    base = fr["color"]
    parts = []
    n = 72
    for _ in range(n):
        x, y, r = pile_pt(rng, spread=0.82, lift=30.0)
        ang = rng.uniform(0, 180)
        L = rng.uniform(*cut["len"]) * (1 - 0.3 * r)
        wd = cut["width"] * rng.uniform(0.85, 1.15)
        col = shade(base, rng.uniform(0.86, 1.1) - 0.08 * r)
        edge = shade(col, 0.72)
        parts.append((
            y,
            f'<g transform="rotate({ang:.1f} {x:.1f} {y:.1f})">'
            f'<rect x="{x - L / 2:.1f}" y="{y - wd / 2:.1f}" width="{L:.1f}" height="{wd:.1f}" '
            f'rx="2.6" fill="{col}" stroke="{edge}" stroke-width="1.1"/>'
            f'<rect x="{x - L / 2 + 2.2:.1f}" y="{y - wd / 2 + 1.1:.1f}" width="{max(4, L - 7):.1f}" '
            f'height="{max(1.3, wd * 0.22):.1f}" rx="1" fill="{shade(col, 1.13)}" opacity="0.5"/>'
            f'<rect x="{x - L / 2 + 1.5:.1f}" y="{y + wd / 2 - 2.6:.1f}" width="{max(3, L - 4):.1f}" '
            f'height="2" rx="1" fill="{shade(col, 0.6)}" opacity="0.5"/>'
            f'</g>',
        ))
    parts.sort(key=lambda t: t[0])
    return "".join(p for _, p in parts)


def curd_markup(rng, order, x, y, size, soak_t) -> str:
    ch = MENU["cheese"][order.cheese]
    shadow = (f'<ellipse cx="{x + size * 0.1:.1f}" cy="{y + size * 0.55:.1f}" rx="{size * 0.9:.1f}" '
              f'ry="{size * 0.36:.1f}" fill="#4a2f14" opacity="0.2"/>')
    col = mix(ch["color"], "#c39a55", soak_t * 0.3 * ch["soak"])
    rim = mix(ch["rim"], "#8b6b3c", soak_t * 0.45)
    n = rng.choice([7, 8, 9])
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n + rng.uniform(-0.16, 0.16)
        rr = size * (1 + rng.uniform(-0.22, 0.18))
        pts.append((x + math.cos(a) * rr, y + math.sin(a) * rr * 0.88))
    out = shadow + f'<path d="{smooth_closed_path(pts)}" fill="{col}" stroke="{rim}" stroke-width="1.3"/>'
    # facet + shine
    out += (f'<path d="M {x - size * 0.55:.1f} {y - size * 0.1:.1f} '
            f'Q {x - size * 0.1:.1f} {y - size * 0.62:.1f} {x + size * 0.5:.1f} {y - size * 0.42:.1f}" '
            f'fill="none" stroke="{shade(col, 1.18)}" stroke-width="1.6" opacity="{0.5 - soak_t * 0.25:.2f}"/>')
    out += (f'<ellipse cx="{x - size * 0.24:.1f}" cy="{y - size * 0.34:.1f}" rx="{size * 0.34:.1f}" '
            f'ry="{size * 0.2:.1f}" fill="#ffffff" opacity="{max(0.05, 0.34 - soak_t * 0.2):.2f}"/>')
    return out


def draw_curds(rng, order, count, sink) -> list:
    if order.cheese == "no_curds":
        return []
    parts = []
    for i in range(count):
        spread = 0.9 if sink else 0.84
        x, y, r = pile_pt(rng, spread=spread, lift=18.0)
        size = rng.uniform(12, 20) * (1.16 if order.cheese == "extra_curds" else 1.0)
        soak_t = rng.uniform(0.2, 1) * (0.85 if sink else 0.2)
        parts.append((sink, y, curd_markup(rng, order, x, y, size, soak_t)))
    return parts


def draw_gravy(rng, order) -> str:
    gr = MENU["gravy"][order.gravy]
    cov = gr["coverage"]
    col, dark, light = gr["color"], shade(gr["color"], 0.55), shade(gr["color"], 1.3)
    out = []

    def wet_patch(x, y, rx, ry, ang, op, stroke_w=1.4):
        return (f'<g transform="rotate({ang:.0f} {x:.1f} {y:.1f})">'
                f'<path d="{blob(x, y, rx, ry, rng, n=12, wobble=0.22)}" fill="{col}" opacity="{op:.2f}" '
                f'stroke="{dark}" stroke-width="{stroke_w}" stroke-opacity="{op * 0.85:.2f}"/></g>')

    # broad coating over the middle of the pile
    out.append(wet_patch(CX, CY + 4, RX * cov * 0.56, RY * cov * 0.52, rng.uniform(-14, 14), 0.6, 2))
    for _ in range(9):
        u, v = rng.uniform(-1, 1), rng.uniform(-1, 1)
        if u * u + v * v > 1:
            u *= 0.8
            v *= 0.8
        x, y = CX + u * RX * cov * 0.62, CY + v * RY * cov * 0.58
        angle = rng.uniform(0, 180)
        rx = rng.uniform(40, 82) * cov
        ry = rng.uniform(14, 28) * cov
        out.append(wet_patch(x, y, rx, ry, angle, rng.uniform(0.42, 0.66)))

    # veins of deeper colour where the gravy pools
    for _ in range(9):
        u, v = rng.uniform(-0.8, 0.8), rng.uniform(-0.8, 0.8)
        out.append(wet_patch(CX + u * RX * cov * 0.55, CY + v * RY * cov * 0.55,
                             rng.uniform(24, 54) * cov, rng.uniform(10, 22) * cov,
                             rng.uniform(0, 180), rng.uniform(0.16, 0.3), 0))

    # drips pulling down over the fries
    for _ in range(8):
        x = CX + rng.uniform(-1, 1) * RX * cov * 0.82
        y = CY + rng.uniform(0.25, 0.8) * RY * cov
        out.append(f'<path d="{blob(x, y, rng.uniform(7, 15), rng.uniform(16, 42), rng, n=9, wobble=0.26)}" '
                   f'fill="{col}" opacity="0.62" stroke="{dark}" stroke-width="1.1" stroke-opacity="0.5"/>')

    # sheen: specular streaks on the wet surface
    for _ in range(int(6 + gr["gloss"] * 6)):
        x = CX + rng.uniform(-0.6, 0.6) * RX * cov
        y = CY + rng.uniform(-0.55, 0.55) * RY * cov
        rx, ry = rng.uniform(12, 34), rng.uniform(3.5, 8)
        out.append(f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="{rx:.0f}" ry="{ry:.0f}" fill="#fffaf0" '
                   f'opacity="{0.1 + 0.1 * gr["gloss"]:.2f}" transform="rotate({rng.uniform(-30, 30):.0f} {x:.0f} {y:.0f})"/>')
    out.append(f'<path d="M {CX - RX * cov * 0.5:.0f} {CY - RY * cov * 0.3:.0f} '
               f'Q {CX - RX * cov * 0.05:.0f} {CY - RY * cov * 0.66:.0f} {CX + RX * cov * 0.44:.0f} {CY - RY * cov * 0.42:.0f}" '
               f'fill="none" stroke="{light}" stroke-width="2.4" opacity="0.3" stroke-linecap="round"/>')

    if gr.get("speckle"):
        for _ in range(80):
            dx, dy = rng.uniform(-1, 1) * RX * cov * 0.66, rng.uniform(-1, 1) * RY * cov * 0.62
            out.append(f'<circle cx="{CX + dx:.0f}" cy="{CY + dy:.0f}" r="{rng.uniform(0.9, 2.4):.1f}" '
                       f'fill="#2f2117" opacity="0.55"/>')
    if gr.get("chunks"):
        for _ in range(12):
            dx, dy = rng.uniform(-1, 1) * RX * cov * 0.55, rng.uniform(-1, 1) * RY * cov * 0.52
            out.append(f'<path d="{blob(CX + dx, CY + dy, rng.uniform(8, 14), rng.uniform(5, 8), rng, n=8, wobble=0.32)}" '
                       f'fill="{dark}" opacity="0.9"/>')
    return "".join(out)


def glyph(rng, t, x, y, s=1.0) -> str:
    c, g = t["color"], t["glyph"]
    if g == "strip":
        w = 27
        out = []
        for k, off in ((-1, -3.4), (0, 0.0), (1, 3.4)):
            yy = y + off
            d = f"M {x - w / 2:.1f} {yy:.1f}"
            for i in range(1, 4):
                xx = x - w / 2 + w * i / 3
                d += f" Q {xx - w / 8:.1f} {yy + (2.6 if i % 2 else -2.6):.1f} {xx:.1f} {yy:.1f}"
            out.append(
                f'<path d="{d}" fill="none" stroke="{shade(c, 0.78 + 0.1 * (k + 1))}" '
                f'stroke-width="5.2" stroke-linecap="round" opacity="0.97"/>'
            )
        # fat streaks
        for off in (-1.6, 2.0):
            d = f"M {x - w / 2 + 2:.1f} {y + off:.1f} Q {x:.1f} {y + off - 2:.1f} {x + w / 2 - 2:.1f} {y + off:.1f}"
            out.append(f'<path d="{d}" fill="none" stroke="#e8b39a" stroke-width="1.2" opacity="0.55"/>')
        return "".join(out)
    if g == "cube":
        sz = 9 * s
        return (
            f'<g transform="rotate({rng.uniform(-30, 30):.0f} {x:.1f} {y:.1f})">'
            f'<rect x="{x - sz / 2:.1f}" y="{y - sz / 2:.1f}" width="{sz:.1f}" height="{sz * 0.85:.1f}" '
            f'rx="1.6" fill="{c}" stroke="{shade(c, 0.7)}" stroke-width="1"/></g>'
        )
    if g == "shred":
        out = []
        for k in (-1, 0, 1):
            d = (
                f"M {x - 11 * s:.1f} {y + k * 4.4 * s:.1f} "
                f"Q {x:.1f} {y + k * 4.4 * s + rng.uniform(-6, 6) * s:.1f} {x + 11 * s:.1f} {y + k * 4.4 * s:.1f}"
            )
            out.append(
                f'<path d="{d}" fill="none" stroke="{shade(c, rng.uniform(0.85, 1.12))}" '
                f'stroke-width="{2.6 * s:.1f}" stroke-linecap="round" opacity="0.92"/>'
            )
        return "".join(out)
    if g == "disk":
        r = 8.5 * s
        out = f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{c}" stroke="{shade(c, 0.75)}" stroke-width="1.2"/>'
        if norm(c) in ("#fbe7a1",):  # fried egg
            out += f'<circle cx="{x + r * 0.12:.1f}" cy="{y:.1f}" r="{r * 0.42:.1f}" fill="#f0a92b" opacity="0.95"/>'
        return out
    if g == "ring":
        return (
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{5.6 * s:.1f}" fill="none" stroke="{c}" '
            f'stroke-width="{3.4 * s:.1f}"/>'
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{2.4 * s:.1f}" fill="{shade(c, 1.35)}" opacity="0.55"/>'
        )
    if g == "cap":
        return (
            f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="{10 * s:.1f}" ry="{6.4 * s:.1f}" fill="{c}" '
            f'stroke="{shade(c, 0.72)}" stroke-width="1.1" transform="rotate({rng.uniform(-40, 40):.0f} {x:.1f} {y:.1f})"/>'
            f'<ellipse cx="{x - 2 * s:.1f}" cy="{y - 1.6 * s:.1f}" rx="{4 * s:.1f}" ry="{2 * s:.1f}" fill="#ffffff" opacity="0.16"/>'
        )
    if g == "slice":
        return (
            f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="{9.5 * s:.1f}" ry="{4.2 * s:.1f}" fill="{c}" '
            f'stroke="{shade(c, 0.7)}" stroke-width="1.1" transform="rotate({rng.uniform(0, 180):.0f} {x:.1f} {y:.1f})"/>'
        )
    if g == "kernel":
        return (
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{4.0 * s:.1f}" fill="{c}" stroke="{shade(c, 0.78)}" stroke-width="0.9"/>'
            f'<circle cx="{x - 1.1 * s:.1f}" cy="{y - 1.1 * s:.1f}" r="{1.4 * s:.1f}" fill="#fff8d0" opacity="0.85"/>'
        )
    if g == "bead":
        return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{3.4 * s:.1f}" fill="{c}" opacity="0.95"/>'
    if g == "dollop":
        return (
            f'<path d="{blob(x, y, 12 * s, 8.5 * s, rng, n=9, wobble=0.22)}" fill="{c}" '
            f'stroke="{shade(c, 0.88)}" stroke-width="1"/>'
            f'<ellipse cx="{x - 2.5 * s:.1f}" cy="{y - 2 * s:.1f}" rx="{4 * s:.1f}" ry="{2.4 * s:.1f}" fill="#ffffff" opacity="0.8"/>'
        )
    if g == "chunk":
        return (
            f'<path d="{blob(x, y, 10 * s, 7.5 * s, rng, n=8, wobble=0.3)}" fill="{c}" opacity="0.95" '
            f'stroke="{shade(c, 0.7)}" stroke-width="1"/>'
        )
    return f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="{8 * s:.1f}" ry="{6 * s:.1f}" fill="{c}"/>'


def draw_toppings(rng, order) -> str:
    out = []
    items = list(order.toppings.items())
    rng.shuffle(items)
    for key, mult in items:
        t = MENU["toppings"][key]
        count = int((6 + order.intensity * 4) * mult)
        s = 1.0 * (0.94 if mult > 1 else 1.0)
        for i in range(count):
            x, y, r = pile_pt(rng, spread=0.78, lift=26.0)
            out.append(glyph(rng, t, x, y, s))
    return "".join(out)


def draw_stray_fries(rng, order) -> str:
    """A handful of fries sitting on top of the gravy — the tell that this is a real tray."""
    fr = MENU["fries"][order.fries]
    cut = MENU["cut"][order.cut]
    out = []
    for _ in range(7):
        x, y, r = pile_pt(rng, spread=0.6, lift=22.0)
        ang = rng.uniform(0, 180)
        L = rng.uniform(*cut["len"]) * 0.85
        wd = cut["width"] * rng.uniform(0.85, 1.1)
        col = shade(fr["color"], rng.uniform(0.95, 1.12))
        out.append(
            f'<g transform="rotate({ang:.1f} {x:.1f} {y:.1f})">'
            f'<rect x="{x - L / 2:.1f}" y="{y - wd / 2:.1f}" width="{L:.1f}" height="{wd:.1f}" rx="2.6" '
            f'fill="{col}" stroke="{shade(col, 0.76)}" stroke-width="1.1"/>'
            f'<rect x="{x - L / 2 + 2.2:.1f}" y="{y - wd / 2 + 1.1:.1f}" width="{max(4, L - 7):.1f}" '
            f'height="{max(1.3, wd * 0.22):.1f}" rx="1" fill="{shade(col, 1.16)}" opacity="0.55"/></g>'
        )
    return "".join(out)


def draw_steam(rng) -> str:
    out = ['<g filter="url(#soft)">']
    for i in range(3):
        x0 = CX + rng.uniform(-110, 110)
        y0 = CY - RY * 0.62
        d = (f"M {x0:.0f} {y0:.0f} C {x0 - 30:.0f} {y0 - 36:.0f} "
             f"{x0 + 34:.0f} {y0 - 58:.0f} {x0 - 8:.0f} {y0 - 92:.0f}")
        out.append(
            f'<path d="{d}" fill="none" stroke="#fff6e2" stroke-width="{rng.uniform(6, 13):.1f}" '
            f'stroke-linecap="round" opacity="0.16"/>'
        )
    out.append("</g>")
    return "".join(out)


def badge(x, y, label, value, color):
    return (
        f'<g><rect x="{x}" y="{y}" width="106" height="30" rx="15" fill="#1c1712" opacity="0.55"/>'
        f'<text x="{x + 11}" y="{y + 20}" font-family="ui-sans-serif, system-ui, sans-serif" '
        f'font-size="10.5" fill="#c9bfae" letter-spacing="0.5">{label}</text>'
        f'<text x="{x + 94}" y="{y + 20}" text-anchor="end" font-family="ui-monospace, monospace" '
        f'font-size="13" font-weight="700" fill="{color}">{value}</text></g>'
    ).replace("<text", "<text", 1)


def svg(order, m) -> str:
    rng = random.Random(order.seed)
    fr = MENU["fries"][order.fries]
    gr = MENU["gravy"][order.gravy]
    ch = MENU["cheese"][order.cheese]
    cut = MENU["cut"][order.cut]

    curd_sink = draw_curds(rng, order, 12 if order.cheese != "extra_curds" else 17, sink=True)
    curd_top = draw_curds(rng, order, 16 if order.cheese != "extra_curds" else 22, sink=False)
    sink_layers = "".join(p for _, _, p in sorted(curd_sink, key=lambda t: t[1]))
    top_layers = "".join(p for _, _, p in sorted(curd_top, key=lambda t: t[1]))

    top_labels = ", ".join(
        MENU["toppings"][k]["label"] + (f" ×{v}" if v > 1 else "")
        for k, v in order.toppings.items()
    ) or "Nothing. A purist."

    order_line = f'{fr["label"]} · {cut["label"]} · {gr["label"]} · {ch["label"]}'

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Digital poutine: {esc(order.name)}">
  <defs>
    <linearGradient id="table" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#241b14"/><stop offset="1" stop-color="#120d09"/>
    </linearGradient>
    <linearGradient id="tray" x1="0" y1="0" x2="0.3" y2="1">
      <stop offset="0" stop-color="#f6f2e8"/><stop offset="1" stop-color="#dcd5c4"/>
    </linearGradient>
    <radialGradient id="warm" cx="0.5" cy="0.42" r="0.62">
      <stop offset="0" stop-color="#ffcf7a" stop-opacity="0.16"/><stop offset="1" stop-color="#ffcf7a" stop-opacity="0"/>
    </radialGradient>
    <filter id="soft" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="9"/>
    </filter>
  </defs>

  <rect width="{W}" height="{H}" fill="url(#table)"/>
  <rect width="{W}" height="{H}" fill="url(#warm)"/>

  <text x="36" y="46" font-family="ui-sans-serif, system-ui, sans-serif" font-size="12" fill="#8d8172" letter-spacing="3.2">CHEZ LA LIGNE · STAFF MEAL · POUTINE COUNTER</text>
  <text x="36" y="74" font-family="ui-sans-serif, system-ui, sans-serif" font-size="21" font-weight="700" fill="#f3e7cf">Tray №{order.tray_no}</text>
  <text x="684" y="72" text-anchor="end" font-family="ui-sans-serif, system-ui, sans-serif" font-size="11" fill="#7a6d5c" letter-spacing="1.6">FOR THE MODEL · NOT FOR SALE</text>

  <ellipse cx="360" cy="474" rx="268" ry="26" fill="#000000" opacity="0.55" filter="url(#soft)"/>
  <rect x="86" y="92" width="548" height="376" rx="30" fill="url(#tray)" stroke="#b3aa98" stroke-width="2"/>
  <rect x="98" y="104" width="524" height="352" rx="22" fill="#efe9da" opacity="0.95"/>
  <rect x="102" y="108" width="516" height="344" rx="20" fill="#f8f4e9" opacity="0.7"/>
  <path d="M 110 452 Q 360 486 610 452" fill="none" stroke="#cfc7b4" stroke-width="2" opacity="0.8"/>

  <ellipse cx="360" cy="330" rx="220" ry="118" fill="#6b4a1e" opacity="0.2" filter="url(#soft)"/>
  {draw_fry_bed(random.Random(order.seed + 5), order)}
  {draw_fries(random.Random(order.seed + 7), order)}
  {sink_layers}
  {draw_gravy(random.Random(order.seed + 13), order)}
  {top_layers}
  {draw_stray_fries(random.Random(order.seed + 17), order)}
  {draw_toppings(random.Random(order.seed + 21), order)}
  {draw_steam(random.Random(order.seed + 33))}

  <g font-family="ui-sans-serif, system-ui, sans-serif">
    <text x="36" y="536" font-size="30" font-weight="800" fill="#f6ecd8">{esc(order.name)}</text>
    <text x="36" y="562" font-size="13.5" fill="#b6a891">{esc(order_line)}</text>
    <text x="36" y="584" font-size="13" fill="#cbb995">+ {esc(top_labels)}</text>
  </g>
  {badge(36, 598, "CRISP", f'{m["crisp_index"]:.1f}', "#f0b64a")}
  {badge(152, 598, "SQUEAK", f'{m["squeak_factor"]:.1f}', "#e8d98f")}
  {badge(268, 598, "SOAK", f'{m["gravy_soak"]:.1f}', "#c98b52")}
  {badge(384, 598, "CHAOS", f'{m["chaos_index"]:.1f}', "#e0714f")}
  {badge(500, 598, "JOY", f'{m["satisfaction"]:.1f}', "#9ed08a")}
  <text x="684" y="636" text-anchor="end" font-family="ui-sans-serif, system-ui, sans-serif" font-size="10" fill="#5e5347">tray seed {order.seed}</text>
</svg>
"""


# ---------------------------------------------------------------- ticket


def ticket(order, m, out_dir: Path) -> str:
    fr = MENU["fries"][order.fries]
    gr = MENU["gravy"][order.gravy]
    ch = MENU["cheese"][order.cheese]
    cut = MENU["cut"][order.cut]
    tops = (
        "\n".join(
            f"| {MENU['toppings'][k]['label']} | {'×' + str(v) if v > 1 else '1' } |"
            for k, v in order.toppings.items()
        )
        or "| — | — |"
    )
    good = [n for kind, n in m["notes"] if kind == "good"]
    warn = [n for kind, n in m["notes"] if kind == "warn"]
    verdicts = "\n".join(f"- {v}" for v in order.verdicts(m))
    synergy = "\n".join(f"- ✅ {g}" for g in good) or "- (no particular synergy, which is fine)"
    clash = "\n".join(f"- ⚠️ {w}" for w in warn) or "- (no clashes detected)"

    provenance = (
        f"influenced by {order.influenced_by}" if order.influenced_by
        else "self-directed"
    )
    why_block = order.why.strip() or "No reason recorded. It wanted it."
    mood_row = f"| **Mood at the counter** | {order.mood} |\n" if order.mood.strip() else ""
    next_block = (
        f"\n### Next time\n{order.next_time.strip()}\n" if order.next_time.strip() else ""
    )

    return f"""# 🍟 Tray №{order.tray_no} — {order.name}

**Chez la Ligne · Poutine Creation Counter · staff meal** · seed `{order.seed}`

*Ordered by the model, for the model. No one else is eating this.*

| | |
|---|---|
| **Ordered by** | the model — {provenance} |
{mood_row}| **Fries** | {fr['label']} — *{fr['note']}* |
| **Cut** | {cut['label']} |
| **Gravy** | {gr['label']} — *{gr['note']}* |
| **Curds** | {ch['label']} |
| **Toppings** | {', '.join(MENU['toppings'][k]['label'] for k in order.toppings) or 'none'} |

### Toppings
| Topping | Portions |
|---|---|
{tops}

### Why this order
{why_block}

### Readout
| Metric | Score |
|---|---|
| Crisp index | **{m['crisp_index']}/10** |
| Squeak factor | **{m['squeak_factor']}/10** |
| Gravy soak | **{m['gravy_soak']}/10** |
| Structural integrity | **{m['structural_integrity']}/10** |
| Chaos index | **{m['chaos_index']}/10** |
| Balance | **{m['balance']}/10** |
| **Satisfaction** | **{m['satisfaction']}/10** |

### Pairing notes
{synergy}
{clash}

### The cook's verdict
{verdicts}
{next_block}
---
*Joy is a model of satisfaction, computed from the order — not a claim to have tasted anything.*

*Digital poutine: `{out_dir.relative_to(ROOT) if out_dir.is_relative_to(ROOT) else out_dir}/poutine.svg` · same order, same tray, every time. This is what having a poutine means without a mouth.*
"""


# ---------------------------------------------------------------- cli


def main(argv=None):
    p = argparse.ArgumentParser(description="Render a digital poutine from a lunch-line order.")
    sub = p.add_subparsers(dest="cmd")

    sub.add_parser("menu", help="print the full counter menu")

    o = sub.add_parser("order", help="build a tray")
    o.add_argument("--fries", default="golden")
    o.add_argument("--cut", default="regular")
    o.add_argument("--gravy", default="chicken")
    o.add_argument("--cheese", default="fresh_curds")
    o.add_argument("--toppings", default="", help='comma list, e.g. "bacon,green_onion*2"')
    o.add_argument("--name", default="", help="name this poutine")
    o.add_argument("--intensity", type=int, default=2, choices=[1, 2, 3], help="how heavy-handed per topping")
    o.add_argument("--seed", type=int, default=None)
    o.add_argument("--surprise", action="store_true", help="the cook decides; ignores other order flags")
    o.add_argument("--out", default="out", help="output directory (default: out/)")
    o.add_argument("--json", action="store_true", help="print order+metrics JSON to stdout only")
    o.add_argument("--why", default="", help="the model's reason for this order (one short paragraph)")
    o.add_argument("--mood", default="", help="state at the counter, e.g. 'post-debugging, verbose'")
    o.add_argument("--next", dest="next_time", default="", help="what it would order next time")
    o.add_argument("--influenced-by", default="", help="name who steered the order, if anyone did")

    a = p.parse_args(argv)

    if a.cmd == "menu" or a.cmd is None:
        print_menu()
        return 0

    if a.surprise:
        order = surprise_order(random.Random(a.seed))
        if a.name.strip():
            order.name = a.name.strip()
        order.why = a.why or order.why
        order.mood = a.mood
        order.next_time = a.next_time
        order.influenced_by = a.influenced_by
    else:
        toppings = parse_toppings(a.toppings)
        name = a.name.strip() or default_name(a, toppings)
        order = Order(
            resolve("fries", a.fries),
            resolve("cut", a.cut),
            resolve("gravy", a.gravy),
            resolve("cheese", a.cheese),
            toppings,
            name,
            seed=a.seed,
            intensity=a.intensity,
            why=a.why,
            mood=a.mood,
            next_time=a.next_time,
            influenced_by=a.influenced_by,
        )

    m = order.metrics()
    out_dir = Path(a.out)
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir
    slug = re.sub(r"[^a-z0-9]+", "-", order.name.lower()).strip("-") or "poutine"
    out_dir = out_dir / f"{slug}-{order.seed % 10000:04d}"
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "poutine.svg").write_text(svg(order, m), encoding="utf-8")
    (out_dir / "ticket.md").write_text(ticket(order, m, out_dir), encoding="utf-8")
    payload = {
        "name": order.name,
        "tray_no": order.tray_no,
        "seed": order.seed,
        "for": "the model itself",
        "provenance": f"influenced by {order.influenced_by}" if order.influenced_by else "self-directed",
        "mood": order.mood,
        "why": order.why,
        "next_time": order.next_time,
        "order": {
            "fries": order.fries,
            "cut": order.cut,
            "gravy": order.gravy,
            "cheese": order.cheese,
            "toppings": order.toppings,
            "intensity": order.intensity,
        },
        "metrics": m,
        "verdicts": order.verdicts(m),
        "files": {
            "svg": str(out_dir / "poutine.svg"),
            "ticket": str(out_dir / "ticket.md"),
        },
    }
    (out_dir / "order.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    if a.json:
        print(json.dumps(payload, indent=2))
    else:
        print(ticket(order, m, out_dir))
        print(f"\nfiles → {out_dir}")
    return 0


def default_name(a, toppings) -> str:
    fr = MENU["fries"].get(a.fries, {})
    seed_bits = [MENU["toppings"][k]["label"] for k in list(toppings)[:2]]
    if seed_bits:
        return f"The {' + '.join(seed_bits)} Situation"
    return "House Poutine"


def print_menu():
    print(f"{MENU['name']}\n  {MENU['tagline']}\n")
    print("FRIES (doneness)")
    for k, v in MENU["fries"].items():
        print(f"  {k:<14} {v['label']:<32} crisp {v['crisp']}/10")
    print("\nCUT")
    for k, v in MENU["cut"].items():
        print(f"  {k:<14} {v['label']}")
    print("\nGRAVY")
    for k, v in MENU["gravy"].items():
        print(f"  {k:<14} {v['label']:<34} {'veg' if v['veg'] else '   '} weight {v['weight']}")
    print("\nCURDS")
    for k, v in MENU["cheese"].items():
        print(f"  {k:<14} {v['label']:<34} squeak {v['squeak']}")
    print("\nTOPPINGS")
    for k, v in MENU["toppings"].items():
        print(f"  {k:<20} {v['label']}")
    print("\nAdd *N for a double/triple portion: --toppings 'bacon*2,green_onion'")


if __name__ == "__main__":
    sys.exit(main())
