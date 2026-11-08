#!/usr/bin/env python3
"""Make MUSIC.RAW from part 1's ProTracker edition (needs ffmpeg).

- trims the lead-in so sample 0 is beat 0 (part 1 measured the first beat at 0.335 s)
- keeps 224 beats at 171.60 BPM (the demo's length) and fades out over the last 2 beats
- 8-bit unsigned mono at the Sound Blaster rate 1000000/(256-211) = 22222 Hz
"""
import pathlib, subprocess
root = pathlib.Path(__file__).resolve().parent.parent
src = root.parent / "1993-crystalline-drop" / "protracker.mp3"
FIRST_BEAT, BPM, BEATS = 0.335, 171.60, 224
RATE = round(1_000_000 / (256 - 211))
length = BEATS * 60 / BPM
fade = 2 * 60 / BPM
subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{FIRST_BEAT}", "-t", f"{length:.3f}", "-i", str(src),
                "-af", f"afade=t=in:d=0.02,afade=t=out:st={length - fade:.3f}:d={fade:.3f}",
                "-ac", "1", "-ar", str(RATE), "-f", "u8", str(root / "MUSIC.RAW")], check=True)
n = (root / "MUSIC.RAW").stat().st_size
print(f"MUSIC.RAW: {n} bytes, {n / RATE:.2f} s at {RATE} Hz")
