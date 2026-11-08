#!/usr/bin/env python3
"""Generate src/tables.inc: sine tables and the static VGA palette (6-bit DAC values)."""
import math, pathlib

out = []
def db(name, vals, per=16):
    out.append(f"{name}:")
    for i in range(0, len(vals), per):
        out.append("    db " + ",".join(str(v) for v in vals[i:i + per]))

sintab = [round(127 * math.sin(2 * math.pi * i / 256)) & 0xFF for i in range(256)]
usin = [round(31.5 + 31.5 * math.sin(2 * math.pi * i / 256)) for i in range(256)]

def c6(rgb):  # 8-bit hex colour -> 6-bit DAC
    return tuple(min(63, round(v * 63 / 255)) for v in rgb)

INK, VIOLET = c6((0x05, 0x03, 0x0F)), c6((0x1A, 0x0F, 0x3A))
CYAN, MAGENTA, GOLD = c6((0x4F, 0xF6, 0xFF)), c6((0xFF, 0x3A, 0xD0)), c6((0xFF, 0xD2, 0x7A))
WHITE, PURPLE = (63, 63, 63), c6((0x8A, 0x4F, 0xFF))

def lerp(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))

pal = [(0, 0, 0)] * 256
for i in range(1, 64):            # 1..63: grey ramp (stars)
    pal[i] = (i, i, i)
for bar, col in enumerate((CYAN, MAGENTA, GOLD, PURPLE)):   # 128..191: copper bars
    for s in range(16):
        f = max(0.0, 1 - abs(s - 7.5) / 8)
        base = tuple(v * f ** 0.8 for v in col)
        hi = max(0.0, f - 0.8) * 3
        pal[128 + bar * 16 + s] = tuple(min(63, round(b + (63 - b) * hi)) for b in base)
for i in range(32):               # 192..223: LED wall ramp, ink -> violet -> magenta -> pink
    t = i / 31                    # (cyan is reserved for the AI dancer)
    if t < 0.4:
        pal[192 + i] = lerp(INK, PURPLE, t / 0.4)
    elif t < 0.85:
        pal[192 + i] = lerp(PURPLE, MAGENTA, (t - 0.4) / 0.45)
    else:
        pal[192 + i] = lerp(MAGENTA, (63, 48, 60), (t - 0.85) / 0.15)
pal[224], pal[225], pal[226], pal[227] = GOLD, CYAN, WHITE, MAGENTA
pal[228], pal[229], pal[230] = (4, 2, 10), (2, 1, 6), VIOLET
pal[231] = lerp(GOLD, (0, 0, 0), 0.6)     # dark gold (text shadow)
pal[232] = lerp(MAGENTA, (0, 0, 0), 0.5)  # dark magenta (text shadow)

# 256-step cyclic "crystal night" gradient for the plasma (colours 64..127 rotate through it)
keys = [INK, VIOLET, PURPLE, CYAN, WHITE, CYAN, MAGENTA, GOLD, MAGENTA, VIOLET, INK]
cpal = []
for i in range(256):
    p = i / 256 * (len(keys) - 1)
    k = int(p)
    cpal.append(lerp(keys[k], keys[k + 1], p - k))

db("sintab", sintab)
db("usin", usin)
db("basepal", [v for c in pal for v in c], 24)
db("cpal", [v for c in cpal for v in c], 24)
pathlib.Path(__file__).resolve().parent.parent.joinpath("src", "tables.inc").write_text("\n".join(out) + "\n")
