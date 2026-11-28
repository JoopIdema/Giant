#!/usr/bin/env python3
"""Test GIANT.COM in een minimale DOS-emulatie (Unicorn) met vier videokaarten:
VGA, CGA, Hercules en MDA. Van elke weergave wordt een PNG gemaakt uit het
echte videogeheugen (test_vga.png, test_cga.png, test_herc.png, test_mda.png).
Vereist: pip install unicorn pillow
"""
import sys
from unicorn import Uc, UC_ARCH_X86, UC_MODE_16, UC_HOOK_INTR, UC_HOOK_INSN
from unicorn.x86_const import *
from PIL import Image

COM = open("GIANT.COM", "rb").read()
SEG = 0x1000
CGA16 = [(0,0,0),(0,0,170),(0,170,0),(0,170,170),(170,0,0),(170,0,170),(170,85,0),(170,170,170),
         (85,85,85),(85,85,255),(85,255,85),(85,255,255),(255,85,85),(255,85,255),(255,255,85),(255,255,255)]
AMBER, DARK = (255, 176, 0), (45, 25, 0)

def run(card, args="", key_after=None):
    uc = Uc(UC_ARCH_X86, UC_MODE_16)
    uc.mem_map(0, 0x100000)
    base = SEG << 4
    cmd = args.encode()
    uc.mem_write(base + 0x80, bytes([len(cmd)]) + cmd + b"\r")
    uc.mem_write(base + 0x100, COM)
    st = {"mode": 7 if card in ("herc", "mda") else 3, "modes": [], "exit": None,
          "polls": 0, "ticks": 0, "dac_i": 0, "dac": {}, "keys": 0, "snap": None,
          "bg": 0, "pal": 1, "hreads": 0, "p3b8": None, "p3bf": None, "crtc_i": 0,
          "crtc": {}, "cursor": None}
    r = lambda x: uc.reg_read(x)
    def setzf(on):
        f = r(UC_X86_REG_EFLAGS)
        uc.reg_write(UC_X86_REG_EFLAGS, (f | 0x40) if on else (f & ~0x40))

    def intr(uc, n, ud):
        ax = r(UC_X86_REG_AX); ah, al = ax >> 8, ax & 0xFF; bx = r(UC_X86_REG_BX)
        if n == 0x10:
            if ax == 0x1A00:
                if card == "vga":
                    uc.reg_write(UC_X86_REG_AX, 0x1A); uc.reg_write(UC_X86_REG_BX, 8)
            elif ah == 0x0F: uc.reg_write(UC_X86_REG_AX, 0x5000 | st["mode"])
            elif ah == 0x00:
                st["mode"] = al; st["modes"].append(al)
                if al == 4: st["bg"], st["pal"] = 0, 1
            elif ah == 0x0B:
                if bx >> 8 == 0: st["bg"] = bx & 0x1F
                else: st["pal"] = bx & 1
            elif ah == 0x01: st["cursor"] = r(UC_X86_REG_CX)
        elif n == 0x16:
            if ah == 1:
                if st["snap"] is None:
                    st["snap"] = {"A000": bytes(uc.mem_read(0xA0000, 64000)),
                                  "B000": bytes(uc.mem_read(0xB0000, 0x8000)),
                                  "B800": bytes(uc.mem_read(0xB8000, 0x4000)),
                                  "mode": st["mode"], "p3b8": st["p3b8"]}
                st["polls"] += 1
                if st["polls"] % 55 == 0:
                    st["ticks"] += 1
                    uc.mem_write(0x46C, (st["ticks"] & 0xFFFF).to_bytes(2, "little"))
                if st["polls"] > 200000: uc.emu_stop(); st["exit"] = "HANGT"
                setzf(not (key_after and st["ticks"] >= key_after and st["keys"] == 0))
            elif ah == 0:
                st["keys"] += 1; uc.reg_write(UC_X86_REG_AX, 0x1C0D)
        elif n == 0x21 and ah == 0x4C:
            st["exit"] = al; uc.emu_stop()

    def pin(uc, port, size, ud):
        if port == 0x3BA:
            st["hreads"] += 1
            if card == "herc": return 0x80 if (st["hreads"] // 50) % 2 else 0x00
            if card == "mda": return 0x00
        return 0xFF
    def pout(uc, port, size, val, ud):
        val &= 0xFF
        if port == 0x3C8: st["dac_i"] = val * 3
        elif port == 0x3C9: st["dac"][st["dac_i"]] = val & 0x3F; st["dac_i"] += 1
        elif port == 0x3B8: st["p3b8"] = val
        elif port == 0x3BF: st["p3bf"] = val
        elif port == 0x3B4: st["crtc_i"] = val
        elif port == 0x3B5: st["crtc"][st["crtc_i"]] = val
    uc.hook_add(UC_HOOK_INTR, intr)
    uc.hook_add(UC_HOOK_INSN, pin, None, 1, 0, UC_X86_INS_IN)
    uc.hook_add(UC_HOOK_INSN, pout, None, 1, 0, UC_X86_INS_OUT)
    for reg in (UC_X86_REG_CS, UC_X86_REG_DS, UC_X86_REG_ES, UC_X86_REG_SS):
        uc.reg_write(reg, SEG)
    uc.reg_write(UC_X86_REG_SP, 0xFFFE)
    uc.emu_start(base + 0x100, 0, count=80_000_000)
    return st

def render(st, png):
    s = st["snap"]; m = s["mode"]
    if m == 0x13:
        pal = [tuple(st["dac"].get(c * 3 + k, 0) * 255 // 63 for k in range(3)) for c in range(256)]
        im = Image.new("RGB", (320, 200)); px = im.load()
        for i, v in enumerate(s["A000"]): px[i % 320, i // 320] = pal[v]
        im = im.resize((960, 720), Image.NEAREST)
    elif m == 4:
        base = [10, 12, 14] if st["pal"] == 0 else [11, 13, 15]
        if not (st["bg"] & 0x10): base = [b - 8 for b in base]
        cols = [CGA16[st["bg"] & 15]] + [CGA16[b] for b in base]
        im = Image.new("RGB", (320, 200)); px = im.load(); v = s["B800"]
        for y in range(200):
            for x in range(320):
                b = v[(y & 1) * 0x2000 + (y >> 1) * 80 + (x >> 2)]
                px[x, y] = cols[(b >> ((3 - (x & 3)) * 2)) & 3]
        im = im.resize((960, 720), Image.NEAREST)
    elif s["p3b8"] and s["p3b8"] & 2:                     # Hercules-graphics
        im = Image.new("RGB", (720, 348)); px = im.load(); v = s["B000"]
        for y in range(348):
            for x in range(720):
                b = v[0x2000 * (y & 3) + 90 * (y >> 2) + (x >> 3)]
                px[x, y] = AMBER if b & (0x80 >> (x & 7)) else DARK
        im = im.resize((960, 720), Image.NEAREST)
    else:                                                 # tekst (mode 3 of 7)
        v = s["B000"] if m == 7 else s["B800"]
        light, dark = (AMBER, DARK) if m == 7 else ((170, 170, 170), (0, 0, 0))
        im = Image.new("RGB", (640, 350)); px = im.load()
        for c in range(2000):
            ch, at = v[c * 2], v[c * 2 + 1]
            fg, bg = (dark, light) if at == 0x70 else (light, dark)
            cx, cy = (c % 80) * 8, (c // 80) * 14
            for yy in range(14):
                on = ch == 0xDB or (ch == 0xDF and yy < 7) or (ch == 0xDC and yy >= 7)
                for xx in range(8): px[cx + xx, cy + yy] = fg if on else bg
        im = im.resize((960, 720), Image.NEAREST)
    im.save(png)

ok = True
def check(name, cond, info):
    global ok
    ok &= bool(cond); print(f"{'OK  ' if cond else 'FOUT'} {name}: {info}")

s = run("vga"); render(s, "test_vga.png")
check("VGA", s["exit"] == 0 and s["modes"] == [0x13, 3] and 53 <= s["ticks"] <= 56,
      f"modes={s['modes']} gewacht={s['ticks']} tikken")
s = run("cga"); render(s, "test_cga.png")
check("CGA", s["exit"] == 0 and s["modes"] == [4, 3] and s["bg"] == 0x11 and s["pal"] == 0,
      f"modes={s['modes']} kleur0={s['bg']:#04x} palet={s['pal']}")
s = run("herc"); render(s, "test_herc.png")
crtc = [s["crtc"].get(i) for i in range(12)]
check("Hercules", s["exit"] == 0 and s["snap"]["p3b8"] == 0x0A and s["p3b8"] == 0 and s["p3bf"] == 0
      and crtc == [0x35,0x2D,0x2E,0x07,0x5B,0x02,0x57,0x57,0x02,0x03,0x00,0x00] and s["modes"] == [7],
      f"3B8 tijdens={s['snap']['p3b8']:#04x} na={s['p3b8']:#04x} 3BF na={s['p3bf']} modes={s['modes']}")
s = run("mda"); render(s, "test_mda.png")
check("MDA (tekst)", s["exit"] == 0 and s["modes"] == [7, 7] and s["cursor"] == 0x2000 and s["p3b8"] is None,
      f"modes={s['modes']} detectielezingen={s['hreads']}")
s = run("vga", " c 5")
check("GIANT C 5 op VGA", s["exit"] == 0 and s["modes"] == [4, 3] and 90 <= s["ticks"] <= 93,
      f"modes={s['modes']} gewacht={s['ticks']}")
s = run("vga", " T 0", key_after=200)
check("GIANT T 0 op VGA", s["exit"] == 0 and s["modes"] == [3, 3] and s["keys"] == 1 and s["ticks"] >= 200,
      f"modes={s['modes']} tikken={s['ticks']}")
s = run("cga", "", key_after=10)
check("toets breekt af", s["exit"] == 0 and s["keys"] == 1 and s["ticks"] < 20, f"tikken={s['ticks']}")
sys.exit(0 if ok else 1)
