;=============================================================================
;  giant.asm  -  GIANT-splashscreen voor DOS (GIANT.COM), v1.2 (NASM)
;
;  Toont het GIANT-logo (grote gestreepte G met GIANT eronder), zoals bij het
;  starten van de Cardiff Giant in Halt and Catch Fire.
;
;  Kiest zelf de weergave:
;    VGA        320x200x256 (mode 13h), geel met twee-tint strepen
;    CGA / EGA  320x200x4   (mode 4), geel met blauwe strepen
;    Hercules   720x348 graphics, oplichtend scherm met donker gestreept logo
;    MDA        tekstmode met halve blokjes (ook als terugval)
;
;  Gebruik:  GIANT        3 seconden tonen (een toets breekt af)
;            GIANT n      n seconden tonen (n = 1-9)
;            GIANT 0      tonen tot er een toets wordt ingedrukt
;            GIANT C      CGA-weergave forceren   (ook op EGA/VGA)
;            GIANT T      tekstweergave forceren  (ook op CGA/EGA/VGA)
;            (combineren mag, bijv. GIANT C 0)
;
;  Na afloop wordt de oorspronkelijke videomode hersteld.
;  Alleen 8088-instructies.
;
;  Bouwen:   python mklogo.py            (maakt logo.inc en logo_data.inc)
;            nasm -f bin -o GIANT.COM giant.asm
;=============================================================================

        cpu     8086
        org     0x100

%include "logo.inc"

start:  cld
        mov     ah, 0x0F                ; huidige videomode bewaren
        int     0x10
        mov     [oldmode], al

; --- opdrachtregel ------------------------------------------------------------
        mov     si, 0x81
        mov     cl, [0x80]
        xor     ch, ch
argloop:
        jcxz    argdone
        lodsb
        dec     cx
        or      al, 0x20                ; hoofdletter -> kleine letter
        cmp     al, 'c'
        jne     argnotc
        mov     byte [force], 1
        jmp     argloop
argnotc:
        cmp     al, 't'
        jne     argnott
        mov     byte [force], 2
        jmp     argloop
argnott:
        cmp     al, '0'
        jb      argloop
        cmp     al, '9'
        ja      argloop
        sub     al, '0'
        mov     [secs], al
        jmp     argloop
argdone:
        mov     al, [secs]              ; ticks = seconden * 18,2 = s * 91 / 5
        mov     bl, 91
        mul     bl
        mov     bl, 5
        div     bl
        xor     ah, ah
        mov     [ticks], ax

; --- weergave kiezen -------------------------------------------------------------
        mov     al, [force]
        cmp     al, 1
        jne     notforcec
        jmp     show_cga
notforcec:
        cmp     al, 2
        jne     notforcet
        jmp     show_text
notforcet:
        mov     ax, 0x1A00              ; VGA? (INT 10h AX=1A00h: BL = 7/8)
        int     0x10
        cmp     al, 0x1A
        jne     novga
        cmp     bl, 7
        jb      novga
        cmp     bl, 8
        ja      novga
        jmp     show_vga
novga:  cmp     byte [oldmode], 7       ; kleur (CGA/EGA) of monochroom?
        je      mono
        jmp     show_cga
mono:   mov     dx, 0x3BA               ; Hercules: bit 7 van 3BAh wisselt met de
        in      al, dx                  ; verticale sync; bij MDA blijft hij gelijk
        and     al, 0x80
        mov     ah, al
        mov     cx, 0x8000
hgcchk: in      al, dx
        and     al, 0x80
        cmp     al, ah
        jne     ishgc
        loop    hgcchk
        jmp     show_text
ishgc:  jmp     show_herc

;=============================================================================
;  VGA: mode 13h, even/oneven lijnen in twee tinten
;=============================================================================
show_vga:
        mov     ax, 0x0013
        int     0x10
        mov     dx, 0x3C8               ; DAC: kleuren 1-3 (6 bits per kanaal)
        mov     al, 1
        out     dx, al
        inc     dx
        mov     si, palette
        mov     cx, 9
palloop:
        lodsb
        out     dx, al
        loop    palloop

        mov     ax, 0xA000
        mov     es, ax
        xor     di, di
        mov     ax, 0x0101              ; scherm geel
        mov     cx, 32000
        rep     stosw

        mov     si, logo
        mov     bx, LOGO_Y
        mov     bp, LOGO_H
vgarow: mov     di, bx                  ; DI = y * 320 + LOGO_X
        mov     cl, 6
        shl     di, cl
        mov     ah, bl
        xor     al, al
        add     di, ax
        add     di, LOGO_X
        mov     al, bl                  ; kleur 2 (donker) of 3 (licht)
        and     al, 1
        add     al, 2
        mov     ch, LOGO_WB
vgabyte:
        mov     dl, [si]
        inc     si
        mov     cl, 8
vgabit: shl     dl, 1
        jnc     vganopix
        mov     [es:di], al
vganopix:
        inc     di
        dec     cl
        jnz     vgabit
        dec     ch
        jnz     vgabyte
        inc     bx
        dec     bp
        jnz     vgarow
        jmp     waitkey

;=============================================================================
;  CGA (ook EGA): mode 4, palet 0 intens, kleur 0 = blauw, kleur 3 = geel.
;  Logo in kleur 0 op de even lijnen; de oneven lijnen blijven geel (strepen).
;=============================================================================
show_cga:
        mov     ax, 0x0004
        int     0x10
        mov     ax, 0x0B00              ; achtergrond = blauw, intens palet
        mov     bx, 0x0011
        int     0x10
        mov     ax, 0x0B00              ; palet 0: groen / rood / geel
        mov     bx, 0x0100
        int     0x10

        mov     ax, 0xB800
        mov     es, ax
        xor     di, di
        mov     ax, 0xFFFF              ; alles kleur 3 = geel
        mov     cx, 8192
        rep     stosw

        mov     si, logo
        mov     di, CGA_OFS
        mov     bx, nibtab
        mov     bp, LOGO_H2
cgarow: mov     cx, LOGO_WB
cgabyte:
        lodsb                           ; 8 pixels -> 2 bytes van 4 pixels
        mov     ah, al
        shr     al, 1
        shr     al, 1
        shr     al, 1
        shr     al, 1
        xlatb
        not     al
        and     [es:di], al
        inc     di
        mov     al, ah
        and     al, 0x0F
        xlatb
        not     al
        and     [es:di], al
        inc     di
        loop    cgabyte
        add     si, LOGO_WB             ; oneven lijn overslaan
        add     di, CGA_SKIP
        dec     bp
        jnz     cgarow
        jmp     waitkey

;=============================================================================
;  Hercules: 720x348 graphics op B000:0000 (pagina 0). Scherm oplichtend,
;  logo donker; de strepen zitten al in de bitmap (hlogo).
;=============================================================================
show_herc:
        mov     byte [isherc], 1
        mov     dx, 0x3BF               ; graphics toestaan, alleen pagina 0
        mov     al, 1
        out     dx, al
        mov     dx, 0x3B8               ; graphics, beeld uit
        mov     al, 0x02
        out     dx, al
        mov     dx, 0x3B4               ; 6845 voor 720x348
        mov     si, hgc_crtc
        xor     ah, ah
hgccrt: mov     al, ah
        out     dx, al
        inc     dx
        lodsb
        out     dx, al
        dec     dx
        inc     ah
        cmp     ah, 12
        jb      hgccrt

        mov     ax, 0xB000
        mov     es, ax
        xor     di, di
        mov     ax, 0xFFFF              ; alles oplichtend
        mov     cx, 16384
        rep     stosw

        mov     si, hlogo
        mov     bx, HLOGO_Y
        mov     bp, HLOGO_H
hgcrow: mov     ax, bx                  ; DI = 2000h*(y mod 4) + 90*(y/4) + x
        shr     ax, 1
        shr     ax, 1
        mov     dl, 90
        mul     dl
        mov     di, ax
        mov     ax, bx
        and     ax, 3
        mov     cl, 13
        shl     ax, cl
        add     di, ax
        add     di, HLOGO_XB
        mov     cx, HLOGO_WB
hgcbyte:
        lodsb
        not     al
        and     [es:di], al
        inc     di
        loop    hgcbyte
        inc     bx
        dec     bp
        jnz     hgcrow

        mov     dx, 0x3B8               ; graphics, beeld aan
        mov     al, 0x0A
        out     dx, al
        jmp     waitkey

;=============================================================================
;  Tekst (MDA en terugval): omgekeerd beeld, logo met halve blokjes
;=============================================================================
show_text:
        mov     ax, 0x0003
        mov     dx, 0xB800
        cmp     byte [oldmode], 7
        jne     txtmode
        mov     al, 7
        mov     dx, 0xB000
txtmode:
        push    dx
        int     0x10
        mov     ah, 0x01                ; cursor uit
        mov     cx, 0x2000
        int     0x10
        pop     es
        xor     di, di
        mov     ax, 0x7020              ; spaties, omgekeerd beeld
        mov     cx, 2000
        rep     stosw

        mov     si, tlogo
        mov     di, TLOGO_OFS
        mov     bx, tchars
        mov     bp, TLOGO_H2
txtrow: push    di
        mov     cx, TLOGO_WB
txtbyte:
        mov     dl, [si]                ; bovenste halve rij
        mov     dh, [si+TLOGO_WB]       ; onderste halve rij
        inc     si
        mov     ah, 8
txtbit: xor     al, al
        shl     dh, 1
        rcl     al, 1
        shl     dl, 1
        rcl     al, 1                   ; AL = onder*2 + boven
        or      al, al
        jz      txtskip
        xlatb
        mov     [es:di], al
txtskip:
        inc     di
        inc     di
        dec     ah
        jnz     txtbit
        loop    txtbyte
        pop     di
        add     di, 160
        add     si, TLOGO_WB
        dec     bp
        jnz     txtrow

;=============================================================================
;  Wachten (tijd of toets) en herstellen
;=============================================================================
waitkey:
        call    get_ticks
        mov     [t0], dx
waitloop:
        mov     ah, 1
        int     0x16
        jnz     key
        cmp     byte [secs], 0
        je      waitloop
        call    get_ticks
        sub     dx, [t0]
        cmp     dx, [ticks]
        jb      waitloop
        jmp     done
key:    xor     ah, ah                  ; toets uit de buffer halen
        int     0x16

done:   cmp     byte [isherc], 0
        je      restore
        mov     dx, 0x3B8               ; Hercules terug naar tekst
        xor     al, al
        out     dx, al
        mov     dx, 0x3BF
        out     dx, al
restore:
        mov     al, [oldmode]
        xor     ah, ah
        int     0x10
        mov     ax, 0x4C00
        int     0x21

; get_ticks: DX = BIOS-tikteller (0040:006C). Direct lezen in plaats van
; INT 1Ah, zodat de middernachtvlag voor DOS niet wordt 'opgegeten'.
get_ticks:
        push    ds
        mov     dx, 0x40
        mov     ds, dx
        mov     dx, [0x6C]
        pop     ds
        ret

;--- data -----------------------------------------------------------------------
secs:   db      3
force:  db      0                       ; 1 = CGA, 2 = tekst
isherc: db      0
oldmode: db     3
t0:     dw      0
ticks:  dw      0
palette:                                ; VGA: R, G, B (0-63)
        db      58, 53, 18              ; 1: geel scherm
        db      13, 18, 24              ; 2: donkere streep
        db      23, 28, 34              ; 3: lichte streep
nibtab:                                 ; CGA: 4 bits -> 4 pixels van 2 bits
        db      0x00, 0x03, 0x0C, 0x0F, 0x30, 0x33, 0x3C, 0x3F
        db      0xC0, 0xC3, 0xCC, 0xCF, 0xF0, 0xF3, 0xFC, 0xFF
hgc_crtc:                               ; Hercules 720x348
        db      0x35, 0x2D, 0x2E, 0x07, 0x5B, 0x02, 0x57, 0x57
        db      0x02, 0x03, 0x00, 0x00
tchars: db      0x20, 0xDF, 0xDC, 0xDB  ; -, boven, onder, vol

%include "logo_data.inc"
