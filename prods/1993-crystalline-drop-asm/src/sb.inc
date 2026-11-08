; ===========================================================================
;  Sound Blaster streaming (DSP 2.00+, 8-bit mono, auto-init DMA)
;
;  MUSIC.RAW: unsigned 8-bit mono PCM at 1000000/(256-SB_TC) Hz, trimmed so
;  that sample 0 is beat 0 (tools/mkmusic.py). It is streamed from disk into
;  a 16 KiB DMA ring: the card raises an IRQ after each 8 KiB half, the ISR
;  only counts it, and the main loop refills the finished half with a DOS
;  read (no DOS calls inside interrupts).
;
;  Settings from BLASTER (A, I, D), defaults A220 I7 D1. IRQ 3/5/7 and
;  8-bit DMA 0..3 are supported; anything else, a missing card or a missing
;  MUSIC.RAW means the demo runs silent.
; ===========================================================================

SB_TC       equ 211             ; 1000000 / (256 - 211) = 22222 Hz
DMABUF      equ 16384
HALF        equ 8192

; sb_init: detect, open the music, prefill the ring. Sets [sbon]=1 on success.
sb_init:
        mov word [sbbase], 220h
        mov byte [sbirq], 7
        mov byte [sbdma], 1
        call parse_blaster
        mov al, [sbirq]
        cmp al, 3
        je .irqok
        cmp al, 5
        je .irqok
        cmp al, 7
        jne .fail
.irqok: cmp byte [sbdma], 3
        ja .fail
        ; reset the DSP
        mov dx, [sbbase]
        add dx, 6
        mov al, 1
        out dx, al
        mov cx, 64
.dl:    in al, dx               ; a few microseconds
        loop .dl
        xor al, al
        out dx, al
        mov cx, 0FFFFh
.wr:    mov dx, [sbbase]
        add dx, 0Eh
        in al, dx
        test al, 80h
        jz .next
        sub dx, 4               ; 0Ah: read data
        in al, dx
        cmp al, 0AAh
        je .found
.next:  loop .wr
        jmp .fail
.found: ; music file
        mov ax, 3D00h
        mov dx, musicname
        int 21h
        jc .fail
        mov [mfile], ax
        ; DMA ring: physical address that does not cross a 64 KiB page
        mov ax, cs
        add ax, 2000h
        movzx eax, ax
        shl eax, 4
        mov edx, eax
        and edx, 0FFFFh
        add edx, DMABUF
        cmp edx, 10000h
        jbe .pok
        add eax, 0FFFFh
        and eax, 0FFFF0000h
.pok:   mov [dmaphys], eax
        shr eax, 4
        mov [dmaseg], ax
        mov byte [meof], 0
        xor bl, bl
        call sb_fill
        mov bl, 1
        call sb_fill
        mov byte [sbnext], 0
        mov byte [sbpend], 0
        mov byte [sbon], 1
.fail:  ret

; sb_start: hook the IRQ, program DMA and the DSP. Playback starts here.
sb_start:
        cmp byte [sbon], 0
        je .r
        ; IRQ vector 8+irq
        mov al, [sbirq]
        add al, 8
        mov ah, 35h
        int 21h
        mov [oldsb], bx
        mov [oldsb+2], es
        mov al, [sbirq]
        add al, 8
        mov ah, 25h
        mov dx, isr_sb
        int 21h
        ; unmask on the master PIC
        mov cl, [sbirq]
        mov bl, 1
        shl bl, cl
        not bl
        in al, 21h
        mov [oldmask], al
        and al, bl
        out 21h, al
        ; DMA channel: mask, clear flip-flop, mode, address, count, page, unmask
        movzx bx, byte [sbdma]
        mov al, bl
        or al, 4
        out 0Ah, al
        xor al, al
        out 0Ch, al
        mov al, 58h             ; single, auto-init, read (memory -> card)
        or al, bl
        out 0Bh, al
        mov dx, bx
        shl dx, 1               ; address port = 2*ch
        mov eax, [dmaphys]
        out dx, al
        mov al, ah
        out dx, al
        inc dx                  ; count port = 2*ch+1
        mov ax, DMABUF-1
        out dx, al
        mov al, ah
        out dx, al
        mov dl, [dmapage+bx]
        xor dh, dh
        mov eax, [dmaphys]
        shr eax, 16
        out dx, al
        mov al, bl
        out 0Ah, al             ; unmask
        ; DSP: speaker on, rate, block size, auto-init 8-bit output
        mov al, 0D1h
        call dsp_write
        mov al, 40h
        call dsp_write
        mov al, SB_TC
        call dsp_write
        mov al, 48h
        call dsp_write
        mov al, (HALF-1) & 0FFh
        call dsp_write
        mov al, (HALF-1) >> 8
        call dsp_write
        mov al, 1Ch
        call dsp_write
.r:     ret

; sb_service: refill every half the card has finished with
sb_service:
        cmp byte [sbon], 0
        je .r
.l:     cmp byte [sbpend], 0
        je .r
        cli
        dec byte [sbpend]
        sti
        mov bl, [sbnext]
        call sb_fill
        xor byte [sbnext], 1
        jmp .l
.r:     ret

; sb_stop: stop the DSP, mask DMA, restore IRQ and PIC, close the file
sb_stop:
        cmp byte [sbon], 0
        je .r
        mov al, 0D0h            ; pause 8-bit DMA
        call dsp_write
        mov al, 0DAh            ; leave auto-init
        call dsp_write
        mov al, 0D3h            ; speaker off
        call dsp_write
        mov al, [sbdma]
        or al, 4
        out 0Ah, al
        cli
        mov al, [oldmask]
        out 21h, al
        sti
        push ds
        mov al, [sbirq]
        add al, 8
        mov ah, 25h
        mov dx, [oldsb]
        mov ds, [oldsb+2]
        int 21h
        pop ds
        mov bx, [mfile]
        mov ah, 3Eh
        int 21h
        mov byte [sbon], 0
.r:     ret

; sb_fill: bl = half (0/1). Reads HALF bytes, pads with silence at the end.
sb_fill:
        pusha
        push es
        movzx dx, bl
        shl dx, 13              ; * 8192
        mov di, dx
        xor ax, ax
        cmp byte [meof], 0
        jne .pad
        push ds
        mov bx, [mfile]
        mov cx, HALF
        mov ds, [dmaseg]
        mov ah, 3Fh
        int 21h
        pop ds
        jnc .got
        xor ax, ax
.got:   cmp ax, HALF
        je .done
        mov byte [meof], 1
.pad:   mov es, [dmaseg]
        add di, ax
        mov cx, HALF
        sub cx, ax
        mov al, 80h
        rep stosb
.done:  pop es
        popa
        ret

dsp_write:
        push dx
        push ax
        mov dx, [sbbase]
        add dx, 0Ch
.w:     in al, dx
        test al, 80h
        jnz .w
        pop ax
        out dx, al
        pop dx
        ret

isr_sb:
        push ax
        push dx
        mov dx, [cs:sbbase]
        add dx, 0Eh
        in al, dx               ; acknowledge the 8-bit IRQ
        inc byte [cs:sbpend]
        mov al, 20h
        out 20h, al
        pop dx
        pop ax
        iret

; parse_blaster: BLASTER=A220 I7 D1 ... from the environment
parse_blaster:
        push es
        mov es, [2Ch]
        xor di, di
.var:   cmp byte [es:di], 0
        je .done
        mov si, s_blaster
        mov bx, di
.cmp:   lodsb
        test al, al
        jz .found
        cmp al, [es:bx]
        jne .skip
        inc bx
        jmp .cmp
.skip:  cmp byte [es:di], 0
        je .s2
        inc di
        jmp .skip
.s2:    inc di
        jmp .var
.found: mov al, [es:bx]
        test al, al
        jz .done
        inc bx
        and al, 0DFh            ; upper case
        cmp al, 'A'
        je .a
        cmp al, 'I'
        je .i
        cmp al, 'D'
        je .d
        jmp .found
.a:     mov cx, 16
        call .num
        mov [sbbase], ax
        jmp .found
.i:     mov cx, 10
        call .num
        mov [sbirq], al
        jmp .found
.d:     mov cx, 10
        call .num
        mov [sbdma], al
        jmp .found
.done:  pop es
        ret
.num:   xor ax, ax              ; es:bx digits in base cx -> ax
.n:     movzx dx, byte [es:bx]
        sub dl, '0'
        cmp dl, 9
        jbe .dig
        sub dl, 7               ; 'A'-'0'-10
        and dl, 0DFh
        cmp dl, 10
        jb .ne
        cmp dl, 15
        ja .ne
.dig:   cmp dx, cx
        jae .ne
        push dx
        mul cx
        pop dx
        add ax, dx
        inc bx
        jmp .n
.ne:    ret

dmapage     db 87h, 83h, 81h, 82h
s_blaster   db "BLASTER=", 0
musicname   db "MUSIC.RAW", 0
