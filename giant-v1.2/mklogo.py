#!/usr/bin/env python3
"""Tekent het GIANT-logo (grote G met GIANT eronder) en maakt er bitmaps van
voor drie weergaven:

  logo    320x200  VGA mode 13h en CGA mode 4   (1 bit per pixel)
  hlogo   720x348  Hercules-graphics            (strepen al ingebakken)
  tlogo    80x50   tekstmode met halve blokjes  (MDA en overige)

Het ontwerp gebeurt in 'vierkante pixels' op 320x240 (4:3) en wordt per
weergave geschaald, zodat het logo op een 4:3-monitor steeds dezelfde vorm heeft.

Uitvoer:  logo.inc       constanten voor NASM (equ)
          logo_data.inc  de bitmaps (db-regels, MSB = links)
          preview.png    optioneel: python mklogo.py preview.png
"""
import sys
from PIL import Image, ImageDraw

SS = 4                                  # supersampling
W, H = 320, 240                         # ontwerpvlak (vierkante pixels)
img = Image.new("L", (W * SS, H * SS), 0)
d = ImageDraw.Draw(img)

def box(x0, y0, x1, y1):
    return [round(x0 * SS), round(y0 * SS), round(x1 * SS) - 1, round(y1 * SS) - 1]

def rect(x0, y0, x1, y1, r=0, on=True):
    if r:
        d.rounded_rectangle(box(x0, y0, x1, y1), radius=round(r * SS), fill=255 if on else 0)
    else:
        d.rectangle(box(x0, y0, x1, y1), fill=255 if on else 0)

def poly(pts, on=True):
    d.polygon([(round(x * SS), round(y * SS)) for x, y in pts], fill=255 if on else 0)

# --- de grote G (ontwerp 100 x 90 eenheden) ---------------------------------
GX, GY, GS = 100, 34, 1.2
def g_rect(x0, y0, x1, y1, r=0, on=True):
    rect(GX + x0 * GS, GY + y0 * GS, GX + x1 * GS, GY + y1 * GS, r * GS, on)

g_rect(0, 0, 100, 90, r=13)             # buitenvorm, afgeronde hoeken
g_rect(25, 23, 75, 67, r=4, on=False)   # binnenruimte
g_rect(70, 23, 101, 41, on=False)       # opening rechtsboven
g_rect(50, 41, 76, 57)                  # de tong van de G

# --- het woord GIANT (letters 16 x 18 eenheden, lijndikte 5) -----------------
TS = 1.55
TW = (16 + 3 + 5 + 3 + 16 + 3 + 16 + 3 + 16) * TS
TX, TY = (W - TW) / 2, GY + 90 * GS + 20

def t_rect(ox, x0, y0, x1, y1, r=0, on=True):
    rect(ox + x0 * TS, TY + y0 * TS, ox + x1 * TS, TY + y1 * TS, r * TS, on)

def t_poly(ox, pts):
    poly([(ox + x * TS, TY + y * TS) for x, y in pts])

x = TX
t_rect(x, 0, 0, 16, 18, r=3)            # G
t_rect(x, 5, 5, 11, 13, on=False)
t_rect(x, 11, 5, 16.5, 8, on=False)
t_rect(x, 8, 8, 11, 11)
x += (16 + 3) * TS
t_rect(x, 0, 0, 5, 18)                  # I
x += (5 + 3) * TS
t_rect(x, 0, 0, 16, 18, r=3)            # A
t_rect(x, 0, 12, 16, 18)
t_rect(x, 5, 5, 11, 9, on=False)
t_rect(x, 5, 13, 11, 18.5, on=False)
x += (16 + 3) * TS
t_rect(x, 0, 0, 5, 18)                  # N
t_rect(x, 11, 0, 16, 18)
t_poly(x, [(0, 0), (5.5, 0), (16, 17.6), (10.5, 17.6)])
x += (16 + 3) * TS
t_rect(x, 0, 0, 16, 5)                  # T
t_rect(x, 5.5, 0, 10.5, 18)

# --- bitmaps -------------------------------------------------------------------
def bitmap(w, h, xalign=8, even=False, keep=lambda y: True, thr=128):
    small = img.resize((w, h), Image.BOX)
    px = small.load()
    pts = [(xx, yy) for yy in range(h) for xx in range(w) if px[xx, yy] >= thr]
    x0 = min(p[0] for p in pts); x1 = max(p[0] for p in pts)
    y0 = min(p[1] for p in pts); y1 = max(p[1] for p in pts)
    x0 -= x0 % xalign
    if even:
        y0 -= y0 % 2
        if (y1 - y0 + 1) % 2: y1 += 1
    wb = (x1 - x0 + 8) // 8
    assert x0 + wb * 8 <= w + 7 and y1 < h
    rows = []
    for yy in range(y0, y1 + 1):
        row = bytearray(wb)
        if keep(yy):
            for xx in range(x0, min(x1 + 1, w)):
                if px[xx, yy] >= thr:
                    row[(xx - x0) // 8] |= 0x80 >> ((xx - x0) % 8)
        rows.append(row)
    return x0, y0, wb, rows

vx, vy, vwb, vrows = bitmap(320, 200, 8, even=True)
hx, hy, hwb, hrows = bitmap(720, 348, 8, keep=lambda y: y % 3 != 2)
tx, ty, twb, trows = bitmap(80, 50, 1, even=True)

equ = {
    "LOGO_X": vx, "LOGO_Y": vy, "LOGO_WB": vwb, "LOGO_H": len(vrows),
    "LOGO_H2": len(vrows) // 2,
    "CGA_OFS": 80 * (vy // 2) + vx // 4, "CGA_SKIP": 80 - 2 * vwb,
    "HLOGO_XB": hx // 8, "HLOGO_Y": hy, "HLOGO_WB": hwb, "HLOGO_H": len(hrows),
    "TLOGO_WB": twb, "TLOGO_H2": len(trows) // 2,
    "TLOGO_OFS": 160 * (ty // 2) + 2 * tx,
}
with open("logo.inc", "w") as f:
    f.write("; gegenereerd door mklogo.py - niet met de hand bewerken\n")
    for k, v in equ.items():
        f.write(f"{k:9s} equ {v}\n")
with open("logo_data.inc", "w") as f:
    f.write("; gegenereerd door mklogo.py - niet met de hand bewerken\n")
    for label, rows in (("logo", vrows), ("hlogo", hrows), ("tlogo", trows)):
        f.write(f"{label}:\n")
        for r in rows:
            f.write("        db      " + ",".join(f"0x{b:02X}" for b in r) + "\n")
print(f"VGA/CGA {vwb*8}x{len(vrows)}  Hercules {hwb*8}x{len(hrows)}  tekst {twb*8}x{len(trows)}"
      f"  -> {sum(len(r) for r in vrows + hrows + trows)} bytes")

if len(sys.argv) > 1:
    pal = {1: (232, 212, 72), 2: (52, 72, 96), 3: (92, 112, 134)}
    out = Image.new("RGB", (320, 200), pal[1]); o = out.load()
    for i, r in enumerate(vrows):
        for xx in range(vwb * 8):
            if r[xx // 8] & (0x80 >> (xx % 8)) and vx + xx < 320:
                o[vx + xx, vy + i] = pal[2 + ((vy + i) & 1)]
    out.resize((960, 720), Image.NEAREST).save(sys.argv[1])
