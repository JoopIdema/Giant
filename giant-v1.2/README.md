# GIANT.COM - splashscreen (v1.2, NASM)

Toont het GIANT-logo van de Cardiff Giant (Halt and Catch Fire): een grote,
gestreepte G met GIANT eronder. Bedoeld voor AUTOEXEC.BAT. Kiest zelf de weergave:

| Kaart | Weergave |
|---|---|
| VGA | 320x200x256: geel met twee-tint blauwgrijze strepen |
| CGA / EGA | 320x200x4: geel met blauwe strepen |
| Hercules | 720x348 graphics: oplichtend scherm, donker gestreept logo |
| MDA | tekstmode met halve blokjes (ook als terugval) |

    GIANT        3 seconden (een toets breekt af)
    GIANT n      n seconden (1-9)
    GIANT 0      tot er een toets wordt ingedrukt
    GIANT C      CGA-weergave forceren (ook op EGA/VGA)
    GIANT T      tekstweergave forceren
                 (combineren mag: GIANT C 0)

Hercules wordt herkend aan bit 7 van poort 3BAh (verticale sync); bij een
gewone MDA blijft dat bit gelijk. Na afloop wordt de oude videomode hersteld.
Alleen 8088-instructies; ca. 11 KB.

## Bouwen in MSYS2 (UCRT64)
    pacman -S make mingw-w64-ucrt-x86_64-nasm mingw-w64-ucrt-x86_64-python mingw-w64-ucrt-x86_64-python-pillow
    make

of zonder make: `nasm -f bin -o GIANT.COM giant.asm`
(`logo.inc` en `logo_data.inc` zitten al in de zip; `python mklogo.py` is
alleen nodig als je het logo verandert).

Test: `make test` (vereist `pip install unicorn`) maakt test_vga/cga/herc/mda.png.

## Aanpassen
* VGA-kleuren: `palette` in giant.asm (0-63 per kanaal)
* CGA-kleuren: de twee INT 10h AH=0Bh-aanroepen in `show_cga`
* Logo en strepen (Hercules): `mklogo.py`
