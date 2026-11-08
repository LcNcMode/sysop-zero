#!/usr/bin/env python3
"""Headless frame test: run `CDROP <ms>` in DOSBox (dummy video), turn SHOT.RAW into PNGs.

usage: tools/shoot.py OUTDIR ms [ms ...]      (needs dosbox, Pillow)
Writes OUTDIR/frame_<ms>.png (640x400) and OUTDIR/contact.png.
"""
import os, pathlib, shutil, subprocess, sys, tempfile
from PIL import Image

root = pathlib.Path(__file__).resolve().parent.parent
out = pathlib.Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
times = [int(t) for t in sys.argv[2:]]
env = dict(os.environ, SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy")
frames = []
with tempfile.TemporaryDirectory() as tmp:
    tmp = pathlib.Path(tmp)
    shutil.copy(root / "CDROP.COM", tmp / "CDROP.COM")
    conf = tmp / "dosbox.conf"
    conf.write_text("[sdl]\noutput=surface\n[cpu]\ncycles=max\n[mixer]\nnosound=true\n")
    for t in times:
        (tmp / "SHOT.RAW").unlink(missing_ok=True)
        subprocess.run(["dosbox", "-conf", str(conf), "-noconsole",
                        "-c", f"mount c {tmp}", "-c", "c:", "-c", f"CDROP {t}", "-c", "exit"],
                       env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
        raw = (tmp / "SHOT.RAW").read_bytes()
        assert len(raw) == 768 + 64000, f"{t} ms: SHOT.RAW is {len(raw)} bytes"
        pal = [min(255, v * 255 // 63) for v in raw[:768]]
        img = Image.frombytes("P", (320, 200), raw[768:]); img.putpalette(pal)
        img = img.convert("RGB").resize((640, 400), Image.NEAREST)
        img.save(out / f"frame_{t:06d}.png"); frames.append(img)
        print(f"{t} ms ok")
cols = 4
sheet = Image.new("RGB", (cols * 320, ((len(frames) + cols - 1) // cols) * 200))
for i, f in enumerate(frames):
    sheet.paste(f.resize((320, 200)), ((i % cols) * 320, (i // cols) * 200))
sheet.save(out / "contact.png")
