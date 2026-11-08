# Crystalline Drop — a 1993 demo (asm edition)

The real-hardware companion to [part 1](../1993-crystalline-drop/): a DOS `.COM`
in x86 real-mode assembler (386+), VGA Mode 13h. v0.1, about 78 s, no music yet.

![frames](shots/contact.png)

## Scenes (beat grid 171.60 BPM, same as part 1)

| beats | scene | what |
|---|---|---|
| 0–32 | INTRO | stateless 3D starfield, "VENTURE OF XANADU PRESENTS" |
| 32–64 | LOGO | four copper bars, sine-wobbled logo with drop shadow |
| 64–112 | PLASMA | 4-term plasma, crystal-night palette rotation, sine scroller with greetings |
| 112–176 | DANCER | LED wall (4 patterns, one per bar), gold-rim silhouette + mirrored cyan AI dancer, 4 arm moves |
| 176–224 | END | typed message, "SHOW ME WHAT AMAZING LOOKS LIKE!", big wobbling "2027" |

## Build and test

```sh
python3 tools/build.py                       # tables + nasm -> CDROP.COM
python3 tools/shoot.py /tmp/shots 6000 50000 # headless DOSBox frames -> PNG + contact sheet
```

Every frame is a pure function of time (`CDROP <ms>` renders exactly the realtime
frame), so the test rig checks the same code path as the demo, minus the timer,
mode switch and blit. Realtime was checked separately in DOSBox on a virtual X
display: right scene at 20/40/57 s, clean exit at the end.

## Layout

| file | what |
|---|---|
| `CDROP.COM` | the prod (entry) |
| `src/cdrop.asm` | all of the code |
| `src/tables.inc` | generated: sine tables and palette (`tools/gentables.py`) |
| `tools/` | build, table generator, headless test rig |
| `shots/` | frames from the test rig |

## Not yet (v0.2+)

- Music: Sound Blaster playback (PCM or a small MOD player) of the ProTracker edition.
- Part 1's other scenes: voxel, glenz, twister, tunnel, fire greetings, rotozoom.
- Not checked: speed on a real 386/486 (DOSBox only).
