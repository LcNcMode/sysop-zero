; ===========================================================================
;  CRYSTALLINE DROP - a 1993 demo - asm edition v0.2
;  Venture of Xanadu, code with Claude
;
;  DOS .COM, x86 real mode (386+), VGA Mode 13h 320x200x256.
;  Build:  nasm -f bin src/cdrop.asm -o CDROP.COM   (see tools/build.py)
;  Run:    CDROP           realtime, ESC quits
;          CDROP <ms>      test mode: render the frame at <ms> into SHOT.RAW
;                          (768 bytes palette + 64000 bytes pixels) and exit
;
;  Timing: PIT channel 0 reprogrammed to ~1000 Hz, beat grid 171.60 BPM
;  (same grid as part 1). Music: MUSIC.RAW streamed to a Sound Blaster
;  (src/sb.inc), started on the same instant as the timer. Everything is a pure function of time, so test
;  frames match realtime frames exactly.
; ===========================================================================

        cpu 386
        bits 16
        org 100h

PIT_DIV     equ 1193            ; 1193182 / 1193 = 1000.15 Hz
BEATMUL     equ 47982           ; beat*256 = ms * 47982 >> 16  (171.6 BPM)
NSTARS      equ 220

; palette indices (see tools/gentables.py)
C_GOLD      equ 224
C_CYAN      equ 225
C_WHITE     equ 226
C_MAGENTA   equ 227
C_FLOOR     equ 228
C_SHADOW    equ 229
C_HAZE      equ 230
C_DGOLD     equ 231
C_DMAG      equ 232

start:
        cld
        ; back buffer = 64 KiB segment after ours
        mov ax, cs
        add ax, 1000h
        mov [bufseg], ax

        ; copy the 8x8 ROM font (int 10h / 1130h, bh=3) into fontbuf
        push es
        mov ax, 1130h
        mov bh, 3
        int 10h                 ; es:bp -> font
        push ds
        push es
        pop ds
        mov si, bp
        pop es                  ; es = our segment
        push es
        mov di, fontbuf
        mov cx, 2048
        rep movsb
        pop ds
        pop es

        call init_stars
        call parse_cmdline      ; sets shotmode / shotms

        cmp byte [shotmode], 0
        jne .loop

        ; realtime: sound blaster (optional), mode 13h, timer, music
        call sb_init
        mov ax, 13h
        int 10h
        call timer_install
        call sb_start
        cli
        mov dword [ticks], 0    ; t=0 is the first sample of the music
        sti

.loop:
        call get_time           ; -> [ms], [beat]
        mov es, [bufseg]
        call run_scene          ; draws into back buffer, sets pal/fade/flash
        jc .quit                ; demo over
        call finalize_pal

        cmp byte [shotmode], 0
        jne .shot

        ; wait for vertical retrace, upload palette, blit
        mov dx, 3DAh
.w1:    in al, dx
        test al, 8
        jnz .w1
.w2:    in al, dx
        test al, 8
        jz .w2
        mov dx, 3C8h
        xor al, al
        out dx, al
        inc dx
        mov si, fpal
        mov cx, 768
        rep outsb
        push ds
        push word 0A000h
        pop es
        mov ds, [bufseg]
        xor si, si
        xor di, di
        mov cx, 16000
        rep movsd
        pop ds

        call sb_service         ; refill the DMA ring

        mov ah, 1               ; key?
        int 16h
        jz .loop
        xor ah, ah
        int 16h
        cmp al, 27
        jne .loop
.quit:
        cmp byte [shotmode], 0
        jne .exit
        mov bl, [sbon]
        push bx
        call sb_stop
        call timer_remove
        mov ax, 3
        int 10h
        pop bx
        mov dx, msg_bye
        test bl, bl
        jnz .msg
        mov dx, msg_silent
.msg:   mov ah, 9
        int 21h
.exit:
        mov ax, 4C00h
        int 21h

.shot:  ; write palette + frame to SHOT.RAW
        mov ah, 3Ch
        xor cx, cx
        mov dx, shotname
        int 21h
        jc .exit
        mov bx, ax
        mov ah, 40h
        mov cx, 768
        mov dx, fpal
        int 21h
        mov ax, [bufseg]
        push ds
        mov ds, ax
        mov ah, 40h
        mov cx, 64000
        xor dx, dx
        int 21h
        pop ds
        mov ah, 3Eh
        int 21h
        jmp .exit

; ---------------------------------------------------------------------------
;  command line: "CDROP 12345" -> shotmode=1, shotms=12345
; ---------------------------------------------------------------------------
parse_cmdline:
        mov si, 81h
        movzx cx, byte [80h]
        xor eax, eax
        xor bl, bl              ; digits seen
.p:     jcxz .done
        dec cx
        movzx edx, byte [si]
        inc si
        cmp dl, ' '
        je .p
        sub dl, '0'
        cmp dl, 9
        ja .done
        imul eax, eax, 10
        add eax, edx
        inc bl
        jmp .p
.done:  test bl, bl
        jz .r
        mov [shotms], eax
        mov byte [shotmode], 1
.r:     ret

; ---------------------------------------------------------------------------
;  timer: int 8 at ~1000 Hz, chains to the BIOS at ~18.2 Hz
; ---------------------------------------------------------------------------
timer_install:
        mov ax, 3508h
        int 21h
        mov [old8], bx
        mov [old8+2], es
        mov ax, 2508h
        mov dx, isr8
        int 21h
        cli
        mov al, 36h
        out 43h, al
        mov ax, PIT_DIV
        out 40h, al
        mov al, ah
        out 40h, al
        sti
        ret

timer_remove:
        cli
        mov al, 36h
        out 43h, al
        xor al, al
        out 40h, al
        out 40h, al
        sti
        push ds
        mov dx, [old8]
        mov ds, [old8+2]
        mov ax, 2508h
        int 21h
        pop ds
        ret

isr8:
        inc dword [cs:ticks]
        add word [cs:chainacc], PIT_DIV
        jc .chain
        push ax
        mov al, 20h
        out 20h, al
        pop ax
        iret
.chain: jmp far [cs:old8]

get_time:
        cmp byte [shotmode], 0
        je .rt
        mov eax, [shotms]
        jmp .set
.rt:    cli
        mov eax, [ticks]
        sti
.set:   mov [ms], eax
        mov edx, BEATMUL
        mul edx
        shrd eax, edx, 16
        mov [beat], eax
        ret

; ---------------------------------------------------------------------------
;  scene table: start beat, end beat, routine
; ---------------------------------------------------------------------------
scenes:
        dw 0,   32,  scene_intro
        dw 32,  64,  scene_logo
        dw 64,  112, scene_plasma
        dw 112, 176, scene_dancer
        dw 176, 224, scene_end
        dw 0FFFFh

; picks the scene, computes [lb] (local beat*256) and the fade, calls it.
; CF=1 when the demo is over.
run_scene:
        mov eax, [beat]
        shr eax, 8              ; whole beats
        mov si, scenes
.f:     mov bx, [si]
        cmp bx, 0FFFFh
        je .over
        cmp ax, [si+2]
        jb .hit
        add si, 6
        jmp .f
.over:  stc
        ret
.hit:   movzx ebx, word [si]
        shl ebx, 8
        mov eax, [beat]
        sub eax, ebx
        mov [lb], eax
        movzx ecx, word [si+2]
        sub cx, [si]
        shl ecx, 8
        sub ecx, eax            ; ecx = beats left * 256
        ; fade = min(64, lb/8, left/8)  -> 2 beats in, 2 beats out
        shr eax, 3
        shr ecx, 3
        cmp eax, ecx
        jbe .m1
        mov eax, ecx
.m1:    cmp eax, 64
        jbe .m2
        mov eax, 64
.m2:    mov [fade], al
        mov byte [flash], 0
        ; reset palette to the static base
        push si
        mov si, basepal
        mov di, pal
        push es
        push ds
        pop es
        mov cx, 768
        rep movsb
        pop es
        pop si
        call word [si+4]
        clc
        ret

; pal * fade / 64 + flash -> fpal (flash only lifts non-zero channels)
finalize_pal:
        mov si, pal
        mov di, fpal
        push es
        push ds
        pop es
        mov cx, 768
        mov bl, [fade]
        mov bh, [flash]
.l:     lodsb
        test al, al             ; black stays black under the beat flash
        jz .ok
        mul bl
        shr ax, 6
        add al, bh
        cmp al, 63
        jbe .ok
        mov al, 63
.ok:    stosb
        loop .l
        pop es
        ret

; beat flash: flash = (255 - frac) >> shift for the first part of each beat
; in: cl = shift (higher = softer)
beat_flash:
        mov al, [lb]
        not al
        shr al, cl
        mov [flash], al
        ret

; ===========================================================================
;  drawing primitives (es = back buffer)
; ===========================================================================

; clear back buffer with al
clear:
        mov ah, al
        mov dx, ax
        shl eax, 16
        mov ax, dx
        xor di, di
        mov cx, 16000
        rep stosd
        ret

; fill_rect: ax=x, bx=y, cx=w, dx=h, color [col]; clipped; honours [dither]
fill_rect:
        pusha
        cmp ax, 0
        jge .x0
        add cx, ax
        xor ax, ax
.x0:    mov si, ax
        add si, cx
        sub si, 320
        jle .x1
        sub cx, si
.x1:    cmp cx, 0
        jle .out
        cmp bx, 0
        jge .y0
        add dx, bx
        xor bx, bx
.y0:    mov si, bx
        add si, dx
        sub si, 200
        jle .y1
        sub dx, si
.y1:    cmp dx, 0
        jle .out
        ; di = y*320 + x
        imul di, bx, 320
        add di, ax
        mov [fr_w], cx
        mov si, dx
        mov al, [col]
        cmp byte [dither], 0
        jne .dith
.row:   mov cx, [fr_w]
        push di
        rep stosb
        pop di
        add di, 320
        dec si
        jnz .row
        jmp .out
.dith:  ; plot only where (x + y) is even, x+y parity tracked in dl
        ; parity of (clipped x + clipped y): di = y*320+x, 320 even -> parity(di) = parity(x)
        mov dx, bx
        add dx, di
.drow:  mov cx, [fr_w]
        push di
        push dx
.dpx:   test dl, 1
        jnz .dskip
        mov [es:di], al
.dskip: inc di
        inc dx
        loop .dpx
        pop dx
        pop di
        add di, 320
        inc dx
        dec si
        jnz .drow
.out:   popa
        ret

; fill_circle: ax=cx, bx=cy, cx=r, color [col]
fill_circle:
        pusha
        mov [fc_x], ax
        mov [fc_y], bx
        mov [fc_r], cx
        imul cx, cx
        mov [fc_r2], cx
        mov si, [fc_r]
        neg si                  ; dy = -r
.dy:    mov ax, si
        imul ax, ax
        mov bp, [fc_r2]
        sub bp, ax              ; r2 - dy2
        mov di, [fc_r]          ; w = r
.w:     mov ax, di
        imul ax, ax
        cmp ax, bp
        jle .wok
        dec di
        jmp .w
.wok:   mov ax, [fc_x]
        sub ax, di
        mov bx, [fc_y]
        add bx, si
        mov cx, di
        shl cx, 1
        inc cx
        mov dx, 1
        call fill_rect
        inc si
        cmp si, [fc_r]
        jle .dy
        popa
        ret

; capsule: [cp_x0],[cp_y0] -> [cp_x1],[cp_y1], radius [cp_r], color [col]
capsule:
        pusha
        mov ax, [cp_x1]
        sub ax, [cp_x0]
        mov [cp_dx], ax
        mov bx, [cp_y1]
        sub bx, [cp_y0]
        mov [cp_dy], bx
        ; n = max(|dx|,|dy|)/2 + 1
        mov cx, ax
        test cx, cx
        jns .a1
        neg cx
.a1:    mov dx, bx
        test dx, dx
        jns .a2
        neg dx
.a2:    cmp cx, dx
        jae .a3
        mov cx, dx
.a3:    shr cx, 1
        inc cx
        mov [cp_n], cx
        xor si, si
.s:     mov ax, [cp_dx]
        imul si
        idiv word [cp_n]
        add ax, [cp_x0]
        mov di, ax
        mov ax, [cp_dy]
        imul si
        idiv word [cp_n]
        add ax, [cp_y0]
        mov bx, ax
        mov ax, di
        mov cx, [cp_r]
        call fill_circle
        inc si
        cmp si, [cp_n]
        jle .s
        popa
        ret

; draw_char: al=char, [tx],[ty] position, [tscale], color [col]
draw_char:
        pusha
        movzx si, al
        shl si, 3
        add si, fontbuf
        mov bx, [ty]
        mov byte [dc_row], 8
.r:     mov dl, [si]
        mov ax, [tx]
        mov byte [dc_col], 8
.c:     shl dl, 1
        jnc .n
        push dx
        mov cx, [tscale]
        mov dx, cx
        call fill_rect
        pop dx
.n:     add ax, [tscale]
        dec byte [dc_col]
        jnz .c
        add bx, [tscale]
        inc si
        dec byte [dc_row]
        jnz .r
        popa
        ret

; draw_string: si=string (0-terminated), [tx],[ty],[tscale],[col]
;   per-char wobble: y += sintab[(wphase + i*wstep)&255] * wamp >> 7
;   only the first [maxch] chars are drawn; chars outside the screen are skipped
draw_string:
        pusha
        mov ax, [tx]
        mov [ds_x], ax
        xor cx, cx              ; char index
.l:     lodsb
        test al, al
        jz .e
        cmp cx, [maxch]
        jae .e
        ; skip offscreen chars
        mov bx, [ds_x]
        cmp bx, 320
        jge .next
        mov dx, [tscale]
        shl dx, 3
        add dx, bx
        cmp dx, 0
        jle .next
        push ax
        mov [tx], bx
        ; wobble
        mov ax, cx
        imul ax, [wstep]
        add ax, [wphase]
        movzx bx, al
        movsx ax, byte [sintab+bx]
        imul word [wamp]
        sar ax, 7
        add ax, [ds_y]
        mov [ty], ax
        pop ax
        call draw_char
.next:  mov ax, [tscale]
        shl ax, 3
        add [ds_x], ax
        inc cx
        jmp .l
.e:     mov ax, [ds_x0]
        mov [tx], ax
        popa
        ret

; text: si=string, bx=y, cl=scale, ch=color; centred horizontally.
; wobble params as set in [wamp],[wstep],[wphase]
text_c:
        pusha
        mov [ds_y], bx
        mov [col], ch
        movzx ax, cl
        mov [tscale], ax
        ; length (full string, so typing does not shift the line)
        push si
        xor dx, dx
.len:   lodsb
        test al, al
        jz .lend
        inc dx
        jmp .len
.lend:  pop si
        imul dx, [tscale]
        shl dx, 2               ; len*8*scale/2
        mov ax, 160
        sub ax, dx
        mov [tx], ax
        mov [ds_x0], ax
        call draw_string
        popa
        ret

; text with a dark drop shadow: same as text_c, shadow colour in dl, offset = scale
text_cs:
        pusha
        push cx
        push bx
        mov ch, dl
        movzx ax, cl
        add bx, ax
        call text_c             ; shadow, shifted down
        pop bx
        pop cx
        call text_c
        popa
        ret

no_wobble:
        mov word [wamp], 0
        mov word [wstep], 0
        mov word [wphase], 0
        mov word [maxch], 0FFFFh
        ret

; ---------------------------------------------------------------------------
;  starfield (stateless: z depends only on time)
;  in: cx = speed shift (ms >> cx is the distance travelled)
; ---------------------------------------------------------------------------
init_stars:
        mov di, stars
        mov cx, NSTARS
        mov eax, 0C0FFEEh
.l:     imul eax, eax, 1103515245
        add eax, 12345
        mov edx, eax
        shr edx, 16
        and dx, 1023
        sub dx, 512
        mov [di], dx            ; x
        imul eax, eax, 1103515245
        add eax, 12345
        mov edx, eax
        shr edx, 16
        and dx, 1023
        sub dx, 512
        sar dx, 1               ; y range narrower
        mov [di+2], dx
        imul eax, eax, 1103515245
        add eax, 12345
        mov edx, eax
        shr edx, 16
        and dx, 511
        mov [di+4], dx          ; z0
        add di, 6
        loop .l
        ret

starfield:
        mov eax, [ms]
        shr eax, cl
        mov [sf_t], ax
        mov si, stars
        mov word [sf_i], NSTARS
.l:     mov bp, [si+4]
        sub bp, [sf_t]
        and bp, 511
        add bp, 8               ; z in 8..519
        ; sx = 160 + x*96/z
        movzx ebp, bp
        movsx eax, word [si]
        imul eax, eax, 96
        cdq
        idiv ebp
        add ax, 160
        mov di, ax
        movsx eax, word [si+2]
        imul eax, eax, 96
        cdq
        idiv ebp
        add ax, 100
        mov bx, ax
        ; colour 63 - z/9 (grey ramp 1..63)
        mov ax, bp
        xor dx, dx
        mov cx, 9
        div cx
        mov cx, 63
        sub cx, ax
        jg .c
        mov cx, 1
.c:     mov [col], cl
        mov ax, di
        mov cx, 1
        mov dx, 1
        cmp bp, 120
        ja .p
        inc cx
        inc dx
.p:     call fill_rect
        add si, 6
        dec word [sf_i]
        jnz .l
        ret

; ===========================================================================
;  S0 INTRO: starfield, "VENTURE OF XANADU" / "PRESENTS"
; ===========================================================================
scene_intro:
        xor al, al
        call clear
        mov cl, 3
        call starfield
        call no_wobble
        mov eax, [lb]
        cmp eax, 4*256
        jb .r
        cmp eax, 28*256
        jae .r
        mov si, s_venture
        mov bx, 78
        mov cx, 2 | (C_GOLD << 8)
        mov dl, C_DGOLD
        call text_cs
        cmp dword [lb], 12*256
        jb .r
        mov si, s_presents
        mov bx, 108
        mov cx, 1 | (C_WHITE << 8)
        call text_c
.r:     ret

; ===========================================================================
;  S1 LOGO: copper bars + wobbling logo
; ===========================================================================
scene_logo:
        xor al, al
        call clear
        ; 4 copper bars
        mov word [cb_i], 0
.bar:   mov ax, [cb_i]
        imul ax, ax, 40
        mov bx, [lb]
        shr bx, 1
        add ax, bx
        movzx bx, al
        movsx ax, byte [sintab+bx]
        imul ax, ax, 74
        sar ax, 7
        add ax, 92
        mov bx, ax              ; top y
        mov ax, [cb_i]
        shl ax, 4
        add ax, 128
        mov [col], al
        mov word [cb_s], 16
.row:   push bx
        xor ax, ax
        mov cx, 320
        mov dx, 1
        call fill_rect
        pop bx
        inc bx
        inc byte [col]
        dec word [cb_s]
        jnz .row
        inc word [cb_i]
        cmp word [cb_i], 4
        jb .bar

        ; logo
        call no_wobble
        mov word [wamp], 10
        mov word [wstep], 22
        mov ax, [lb]
        shr ax, 2
        mov [wphase], ax
        mov si, s_crystalline
        mov bx, 46
        mov cx, 3 | (C_WHITE << 8)
        mov dl, C_SHADOW
        call text_cs
        mov word [wamp], 14
        mov word [wstep], 40
        mov ax, [lb]
        shr ax, 1
        neg ax
        mov [wphase], ax
        mov si, s_drop
        mov bx, 92
        mov cx, 5 | (C_MAGENTA << 8)
        mov dl, C_DMAG
        call text_cs
        call no_wobble
        cmp dword [lb], 8*256
        jb .nf
        mov si, s_a1993
        mov bx, 178
        mov cx, 1 | (C_GOLD << 8)
        call text_c
.nf:    mov cl, 4
        call beat_flash
        ret

; ===========================================================================
;  S2 PLASMA + sine scroller
; ===========================================================================
scene_plasma:
        ; rotate the crystal gradient into colours 64..127
        mov ax, [lb]
        shr ax, 3
        mov [pl_rot], al
        mov di, pal + 64*3
        xor cx, cx
.pp:    mov bl, cl
        shl bl, 2
        add bl, [pl_rot]
        movzx bx, bl
        imul bx, bx, 3
        mov al, [cpal+bx]
        mov [di], al
        mov al, [cpal+bx+1]
        mov [di+1], al
        mov al, [cpal+bx+2]
        mov [di+2], al
        add di, 3
        inc cx
        cmp cx, 64
        jb .pp

        ; column term: usin[(2x + t1)] + usin[(x*3/2 - t2)]
        mov ax, [lb]
        shr ax, 2
        mov [pl_t1], al
        mov ax, [lb]
        shr ax, 3
        mov [pl_t2], al
        mov ax, [lb]
        shr ax, 4
        mov [pl_t3], al
        xor si, si
.ct:    mov ax, si
        shl ax, 1
        add al, [pl_t1]
        movzx bx, al
        mov dl, [usin+bx]
        mov ax, si
        imul ax, ax, 3
        shr ax, 1
        sub al, [pl_t2]
        movzx bx, al
        add dl, [usin+bx]
        mov [colterm+si], dl
        inc si
        cmp si, 320
        jb .ct
        ; row term: usin[(3y + t2)]
        xor si, si
.rt:    mov ax, si
        imul ax, ax, 3
        add al, [pl_t2]
        add al, [pl_t1]
        movzx bx, al
        mov dl, [usin+bx]
        mov [rowterm+si], dl
        inc si
        cmp si, 200
        jb .rt
        ; pixels
        xor di, di
        xor bp, bp              ; y
.ly:    mov ah, [rowterm+bp]
        mov dx, bp
        add dl, [pl_t3]
        xor si, si
        mov cx, 320
.lx:    movzx bx, dl
        mov al, [usin+bx]
        add al, [colterm+si]
        add al, ah
        shr al, 2
        add al, 64
        stosb
        inc si
        inc dl
        loop .lx
        inc bp
        cmp bp, 200
        jb .ly

        ; scroller
        call no_wobble
        mov word [wamp], 16
        mov word [wstep], 18
        mov ax, [lb]
        shr ax, 1
        mov [wphase], ax
        mov word [tscale], 2
        mov eax, [lb]
        imul eax, eax, 52
        shr eax, 8
        mov dx, 320
        sub dx, ax
        mov [tx], dx
        mov [ds_x0], dx
        mov word [ds_y], 150
        mov byte [col], C_SHADOW
        add word [ds_y], 2
        mov si, s_scroll
        call draw_string
        sub word [ds_y], 2
        mov byte [col], C_WHITE
        mov si, s_scroll
        call draw_string
        ret

; ===========================================================================
;  S3 DANCER: LED wall + human silhouette (gold rim) + AI mirror (cyan dots)
; ===========================================================================
scene_dancer:
        mov al, C_FLOOR
        call clear
        call led_wall
        ; floor bands
        mov byte [col], C_HAZE
        xor ax, ax
        mov bx, 140
        mov cx, 320
        mov dx, 2
        call fill_rect
        mov byte [col], C_SHADOW
        mov bx, 186
        mov dx, 14
        call fill_rect

        call pose               ; joints for the human at X=110

        ; human: gold rim (offset +1,-1, r+1), then black body
        mov byte [dither], 0
        mov byte [col], C_GOLD
        mov word [bone_dx], 1
        mov word [bone_dy], -1
        mov word [bone_dr], 1
        mov byte [mirror], 0
        call draw_skel
        mov byte [col], 0
        mov word [bone_dx], 0
        mov word [bone_dy], 0
        mov word [bone_dr], 0
        call draw_skel
        ; AI: mirrored (x' = 320 - x), cyan, dithered "point cloud"
        mov byte [mirror], 1
        mov byte [dither], 1
        mov byte [col], C_CYAN
        call draw_skel
        mov byte [dither], 0
        mov byte [mirror], 0

        call no_wobble
        mov si, s_2027
        mov bx, 190
        mov cx, 1 | (C_GOLD << 8)
        call text_c
        mov cl, 5
        call beat_flash
        ret

; LED wall: 32 x 14 cells of 10x10, pattern changes every bar
led_wall:
        mov eax, [lb]
        shr eax, 10             ; bars
        and al, 3
        mov [lw_pat], al
        mov word [lw_r], 0
.r:     mov word [lw_c], 0
.c:     mov bx, [lw_c]
        mov dx, [lw_r]
        mov al, [lw_pat]
        cmp al, 1
        je .p1
        cmp al, 2
        je .p2
        cmp al, 3
        je .p3
        ; 0: vertical waves
        mov ax, bx
        shl ax, 4
        add ax, [lb]
        movzx si, al
        mov al, [usin+si]
        jmp .set
.p1:    ; 1: rings from the centre
        mov ax, bx
        sub ax, 16
        jns .q1
        neg ax
.q1:    mov cx, dx
        sub cx, 7
        jns .q2
        neg cx
.q2:    add ax, cx
        imul ax, ax, 24
        mov cx, [lb]
        shr cx, 1
        sub ax, cx
        movzx si, al
        mov al, [usin+si]
        jmp .set
.p2:    ; 2: checker that flips on the beat, decaying
        mov ax, bx
        add ax, dx
        add ax, [lb+1]
        and al, 1
        jz .dark
        mov al, [lb]
        not al
        shr al, 2
        jmp .set
.dark:  mov al, 4
        jmp .set
.p3:    ; 3: VU meter bars
        mov ax, bx
        imul ax, ax, 37
        mov cx, [lb]
        shr cx, 1
        add ax, cx
        movzx si, al
        mov al, [usin+si]
        shr al, 2               ; 0..15 height
        mov cl, 14
        sub cl, dl
        cmp cl, al
        jb .lit
        mov al, 3
        jmp .set
.lit:   mov al, 63
.set:   shr al, 1               ; 0..31, scaled to 0..23: the wall glows, it never burns white
        mov ah, 3
        mul ah
        shr ax, 2
        add al, 192
        mov [col], al
        mov ax, [lw_c]
        imul ax, ax, 10
        mov bx, [lw_r]
        imul bx, bx, 10
        mov cx, 9
        mov dx, 9
        call fill_rect
        inc word [lw_c]
        cmp word [lw_c], 32
        jb .c
        inc word [lw_r]
        cmp word [lw_r], 14
        jb .r
        ret

; helpers: ax = sin/cos(a) * len >> 7   (in: bl = angle, cx = len)
sinmul: movzx bx, bl
        movsx ax, byte [sintab+bx]
        imul cx
        sar ax, 7
        ret
cosmul: add bl, 64
        jmp sinmul

; signed 8-bit angle lerp: al = a + (b - a) * t >> 8 ; in al=a, ah=b, dl=t
alerp:  push bx
        push dx
        mov bl, al
        sub ah, al
        movsx ax, ah
        movzx dx, dl
        imul dx
        sar ax, 8
        add al, bl
        pop dx
        pop bx
        ret

; pose: fills J_* (x,y words) from the local beat
DX0     equ 110
pose:
        mov ax, [lb]
        shr ax, 1               ; 2-beat cycle
        mov [ps_h], al
        ; sway = sin(h) * 8 >> 7
        mov bl, al
        mov cx, 8
        call sinmul
        mov [ps_sway], ax
        ; dip = usin[(lb + 64)] >> 3 : 0..7, peaks on every beat
        mov bl, [lb]
        add bl, 64
        movzx bx, bl
        mov al, [usin+bx]
        shr al, 3
        cbw
        mov [ps_dip], ax

        ; pelvis
        mov ax, DX0
        add ax, [ps_sway]
        mov [J_PEL], ax
        mov ax, 118
        add ax, [ps_dip]
        mov [J_PEL+2], ax
        ; chest: counter sway
        mov ax, [ps_sway]
        sar ax, 1
        neg ax
        add ax, DX0
        mov [J_CHE], ax
        mov ax, [ps_dip]
        sar ax, 1
        add ax, 88
        mov [J_CHE+2], ax
        ; neck / head
        mov ax, [J_CHE]
        mov bx, [ps_sway]
        sar bx, 2
        sub ax, bx
        mov [J_NEC], ax
        mov [J_HEA], ax
        mov ax, [J_CHE+2]
        sub ax, 11
        mov [J_NEC+2], ax
        sub ax, 7
        mov [J_HEA+2], ax
        ; hair: swings against the sway, falls down the back
        mov ax, [J_HEA]
        add ax, [ps_sway]
        add ax, 3
        mov [J_HAI], ax
        mov ax, [J_HEA+2]
        add ax, 15
        mov [J_HAI+2], ax
        ; hips
        mov ax, [J_PEL]
        sub ax, 6
        mov [J_LHI], ax
        add ax, 12
        mov [J_RHI], ax
        mov ax, [J_PEL+2]
        mov [J_LHI+2], ax
        mov [J_RHI+2], ax
        ; feet (planted)
        mov word [J_LFO], DX0-13
        mov word [J_RFO], DX0+13
        mov word [J_LFO+2], 174
        mov word [J_RFO+2], 174
        ; knees: midpoints, pushed in on the dip
        mov ax, [J_LHI]
        add ax, [J_LFO]
        sar ax, 1
        sub ax, 2
        add ax, [ps_dip]
        mov [J_LKN], ax
        mov ax, [J_RHI]
        add ax, [J_RFO]
        sar ax, 1
        add ax, 2
        sub ax, [ps_dip]
        mov [J_RKN], ax
        mov ax, [J_LHI+2]
        add ax, 174
        sar ax, 1
        mov [J_LKN+2], ax
        mov [J_RKN+2], ax
        ; shoulders
        mov ax, [J_CHE]
        sub ax, 11
        mov [J_LSH], ax
        add ax, 22
        mov [J_RSH], ax
        mov ax, [J_CHE+2]
        sub ax, 4
        mov [J_LSH+2], ax
        mov [J_RSH+2], ax

        ; arm move: m = (beat / 4) & 3, blend into the next move over the last beat
        mov eax, [lb]
        shr eax, 10
        and ax, 3
        mov si, ax
        mov eax, [lb]
        shr eax, 8
        and al, 3
        xor dl, dl
        cmp al, 3
        jne .nb
        mov dl, [lb]            ; frac of the last beat
.nb:    mov bx, si
        shl bx, 1
        mov al, [moves+bx]      ; upper
        mov di, si
        inc di
        and di, 3
        shl di, 1
        mov ah, [moves+di]
        call alerp
        mov [ps_lu], al
        mov al, [moves+bx+1]    ; fore
        mov ah, [moves+di+1]
        call alerp
        mov [ps_lf], al
        ; wave
        mov bl, [ps_h]
        mov cx, 10
        call sinmul
        add [ps_lu], al
        shl al, 1
        add [ps_lf], al

        ; left arm
        mov bl, [ps_lu]
        mov cx, 16
        call cosmul
        add ax, [J_LSH]
        mov [J_LEL], ax
        mov bl, [ps_lu]
        call sinmul
        add ax, [J_LSH+2]
        mov [J_LEL+2], ax
        mov bl, [ps_lf]
        mov cx, 15
        call cosmul
        add ax, [J_LEL]
        mov [J_LHA], ax
        mov bl, [ps_lf]
        call sinmul
        add ax, [J_LEL+2]
        mov [J_LHA+2], ax
        ; right arm = mirror of left (angle a -> 128 - a), half a beat later
        mov al, 128
        sub al, [ps_lu]
        mov [ps_ru], al
        mov al, 128
        sub al, [ps_lf]
        mov [ps_rf], al
        mov bl, [ps_ru]
        mov cx, 16
        call cosmul
        add ax, [J_RSH]
        mov [J_REL], ax
        mov bl, [ps_ru]
        call sinmul
        add ax, [J_RSH+2]
        mov [J_REL+2], ax
        mov bl, [ps_rf]
        mov cx, 15
        call cosmul
        add ax, [J_REL]
        mov [J_RHA], ax
        mov bl, [ps_rf]
        call sinmul
        add ax, [J_REL+2]
        mov [J_RHA+2], ax
        ret

; arm moves: upper angle, forearm angle (0 = right, 64 = down, 192 = up)
moves:  db 176, 212             ; ARMS UP, wrists crossed overhead
        db 150, 236             ; hand in the hair
        db 100, 28              ; hands slide down to the hips
        db 140, 168             ; open out

; draw_skel: bones list with radius; honours [mirror], [bone_dx/dy/dr]
draw_skel:
        pusha
        mov si, bones
.b:     mov bx, [si]
        cmp bx, 0FFFFh
        je .e
        mov ax, [bx]
        mov dx, [bx+2]
        call .xf
        mov [cp_x0], ax
        mov [cp_y0], dx
        mov bx, [si+2]
        mov ax, [bx]
        mov dx, [bx+2]
        call .xf
        mov [cp_x1], ax
        mov [cp_y1], dx
        mov ax, [si+4]
        add ax, [bone_dr]
        mov [cp_r], ax
        call capsule
        add si, 6
        jmp .b
.e:     popa
        ret
.xf:    cmp byte [mirror], 0
        je .nm
        neg ax
        add ax, 320
.nm:    add ax, [bone_dx]
        add dx, [bone_dy]
        ret

bones:  dw J_HAI, J_HEA, 4      ; hair
        dw J_LHI, J_RHI, 8      ; hips
        dw J_PEL, J_CHE, 6      ; waist
        dw J_LSH, J_RSH, 4      ; shoulders
        dw J_CHE, J_CHE, 8      ; ribcage
        dw J_CHE, J_NEC, 3      ; neck
        dw J_HEA, J_HEA, 7      ; head
        dw J_LHI, J_LKN, 5      ; thighs
        dw J_RHI, J_RKN, 5
        dw J_LKN, J_LFO, 3      ; calves
        dw J_RKN, J_RFO, 3
        dw J_LSH, J_LEL, 3      ; arms
        dw J_LEL, J_LHA, 2
        dw J_RSH, J_REL, 3
        dw J_REL, J_RHA, 2
        dw 0FFFFh

; ===========================================================================
;  S4 END: the message, then a big "2027"
; ===========================================================================
scene_end:
        xor al, al
        call clear
        mov cl, 4
        call starfield
        call no_wobble
        ; typing: 4 chars per beat
        mov eax, [lb]
        shr eax, 6
        mov [maxch], ax
        mov si, s_what1
        mov bx, 36
        mov cx, 1 | (C_WHITE << 8)
        call text_c
        mov ax, [maxch]
        sub ax, 26
        jns .t2
        xor ax, ax
.t2:    mov [maxch], ax
        mov si, s_what2
        mov bx, 50
        mov cx, 1 | (C_WHITE << 8)
        call text_c
        call no_wobble
        cmp dword [lb], 14*256
        jb .r
        mov eax, [lb]
        sub eax, 14*256
        shr eax, 6
        mov [maxch], ax
        mov si, s_amazing
        mov bx, 164
        mov cx, 1 | (C_GOLD << 8)
        call text_c
        call no_wobble
        cmp dword [lb], 24*256
        jb .r
        mov word [wamp], 8
        mov word [wstep], 48
        mov ax, [lb]
        shr ax, 1
        mov [wphase], ax
        mov si, s_y2027
        mov bx, 80
        mov cx, 6 | (C_CYAN << 8)
        mov dl, C_DMAG
        call text_cs
        mov cl, 4
        call beat_flash
.r:     ret

; ===========================================================================
;  data
; ===========================================================================
s_venture       db "VENTURE OF XANADU", 0
s_presents      db "PRESENTS", 0
s_crystalline   db "CRYSTALLINE", 0
s_drop          db "DROP", 0
s_a1993         db "A 1993 DEMO - ASM EDITION", 0
s_2027          db "1993 LIVES ON INSIDE 2027", 0
s_what1         db "WHAT DOES THE AI DEMOSCENE", 0
s_what2         db "LOOK LIKE IN 2027?", 0
s_amazing       db "SHOW ME WHAT AMAZING LOOKS LIKE!", 0
s_y2027         db "2027", 0
s_scroll        db "    REAL MODE, REAL MODE 13H, REAL 386 ASSEMBLER ... "
                db "GREETINGS TO MINI AND ZODIAK / CASCADA ... ALL OF XANADU, "
                db "AROS-D, PARAMOUNT, THE PARTY 1993 CREW IN HERNING ... "
                db "FUTURE CREW, SPACEBALLS, SANITY, KEFRENS ... "
                db "CODE BY CLAUDE, DIRECTION BY VENTURE ...      ", 0
shotname        db "SHOT.RAW", 0
msg_bye         db "CRYSTALLINE DROP - a 1993 demo - asm edition v0.2", 13, 10
                db "Venture of Xanadu, code with Claude. See you in 2027!", 13, 10, "$"
msg_silent      db "CRYSTALLINE DROP - asm edition v0.2 (ran silent: no Sound Blaster", 13, 10
                db "found via BLASTER / A220 I7 D1, or MUSIC.RAW missing)", 13, 10, "$"

%include "sb.inc"

%include "tables.inc"

; ---------------------------------------------------------------------------
section .bss
ticks       resd 1
sbon        resb 1
sbbase      resw 1
sbirq       resb 1
sbdma       resb 1
sbpend      resb 1
sbnext      resb 1
meof        resb 1
oldmask     resb 1
mfile       resw 1
oldsb       resw 2
dmaphys     resd 1
dmaseg      resw 1
chainacc    resw 1
old8        resw 2
shotmode    resb 1
shotms      resd 1
ms          resd 1
beat        resd 1
lb          resd 1
bufseg      resw 1
fade        resb 1
flash       resb 1
col         resb 1
dither      resb 1
mirror      resb 1
fr_w        resw 1
fc_x        resw 1
fc_y        resw 1
fc_r        resw 1
fc_r2       resw 1
cp_x0       resw 1
cp_y0       resw 1
cp_x1       resw 1
cp_y1       resw 1
cp_r        resw 1
cp_dx       resw 1
cp_dy       resw 1
cp_n        resw 1
tx          resw 1
ty          resw 1
tscale      resw 1
ds_x        resw 1
ds_x0       resw 1
ds_y        resw 1
dc_row      resb 1
dc_col      resb 1
wamp        resw 1
wstep       resw 1
wphase      resw 1
maxch       resw 1
sf_t        resw 1
sf_i        resw 1
cb_i        resw 1
cb_s        resw 1
pl_rot      resb 1
pl_t1       resb 1
pl_t2       resb 1
pl_t3       resb 1
lw_pat      resb 1
lw_r        resw 1
lw_c        resw 1
ps_h        resb 1
ps_lu       resb 1
ps_lf       resb 1
ps_ru       resb 1
ps_rf       resb 1
ps_sway     resw 1
ps_dip      resw 1
bone_dx     resw 1
bone_dy     resw 1
bone_dr     resw 1
J_PEL       resw 2
J_CHE       resw 2
J_NEC       resw 2
J_HEA       resw 2
J_HAI       resw 2
J_LHI       resw 2
J_RHI       resw 2
J_LKN       resw 2
J_RKN       resw 2
J_LFO       resw 2
J_RFO       resw 2
J_LSH       resw 2
J_RSH       resw 2
J_LEL       resw 2
J_REL       resw 2
J_LHA       resw 2
J_RHA       resw 2
pal         resb 768
fpal        resb 768
fontbuf     resb 2048
colterm     resb 320
rowterm     resb 200
stars       resw NSTARS*3
