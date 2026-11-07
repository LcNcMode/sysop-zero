# Render the demo to a 9:16 video

Requires: Python 3 + Playwright (Chromium), ffmpeg.

1. Build `render.html`: take `../index.html`, replace the Google Fonts `<link>` with local `@font-face` rules pointing to `fonts/ps2p.woff2`, `fonts/orb600.woff2` and `fonts/orb900.woff2`, and paste `hook.js` in before the line `/* debug hook`.
2. Put `render.html`, `fonts/` and `../protracker.mp3` in the same folder and serve it: `python3 -m http.server 8770`
3. `python3 render.py full` produces `video_only.mp4` (7200 frames, 30 fps, 240 s). `python3 render.py test` renders six stills for a quick check.
4. Audio (a WAV of the original track gives the best quality):

```
ffmpeg -i video_only.mp4 -i music.wav -filter_complex "[1:a]apad=whole_dur=240[a]" -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 256k -t 240 -movflags +faststart full_9x16.mp4
ffmpeg -i video_only.mp4 -i music.wav -filter_complex "[0:v]trim=146.5:188,setpts=PTS-STARTPTS[v1];[0:v]trim=228.5:240,setpts=PTS-STARTPTS[v2];[v1][v2]concat=n=2:v=1:a=0,fade=t=in:st=0:d=0.5[v];[1:a]atrim=146.5:199.5,asetpts=PTS-STARTPTS,afade=t=in:st=0:d=0.5,afade=t=out:st=50:d=3[a]" -map "[v]" -map "[a]" -c:v libx264 -preset veryfast -crf 18 -pix_fmt yuv420p -c:a aac -b:a 256k -movflags +faststart teaser_9x16.mp4
```

The fonts in `fonts/` are third-party and licensed under the SIL Open Font License 1.1 (`OFL-*.txt`), not under the prod license.
