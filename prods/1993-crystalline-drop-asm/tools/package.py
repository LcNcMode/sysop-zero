#!/usr/bin/env python3
"""Build the download package: CDROP_asm_v0.2.zip

One zip, three uses:
  - plain DOSBox / real DOS: unzip, run CDROP
  - js-dos (js-dos Studio, DOS.Zone): the zip is a js-dos bundle (.jsdos/dosbox.conf autostarts CDROP)
  - archive.org: upload as a DOS software item, emulator start command CDROP.COM
Deterministic: fixed timestamps and order, so rebuilding gives the same bytes.
"""
import pathlib, zipfile
root = pathlib.Path(__file__).resolve().parent.parent
OUT = root / "CDROP_asm_v0.2.zip"
DOSBOX_CONF = """\
[sdl]
autolock=false
[render]
aspect=true
[cpu]
core=auto
cputype=auto
cycles=max
[sblaster]
sbtype=sb16
sbbase=220
irq=7
dma=1
hdma=5
[autoexec]
mount c .
c:
CDROP
"""
files = [
    ("CDROP.COM", (root / "CDROP.COM").read_bytes()),
    ("MUSIC.RAW", (root / "MUSIC.RAW").read_bytes()),
    ("NFO.TXT", (root / "nfo.txt").read_bytes().replace(b"\n", b"\r\n")),
    ("DOSBOX.CONF", DOSBOX_CONF.replace("\n", "\r\n").encode()),
    (".jsdos/dosbox.conf", DOSBOX_CONF.encode()),
]
with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for name, data in files:
        info = zipfile.ZipInfo(name, date_time=(1993, 8, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o644 << 16
        z.writestr(info, data)
print(f"{OUT.name}: {OUT.stat().st_size} bytes")
