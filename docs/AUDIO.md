# Sound in web prods

Your prod sounds great on your desktop. On an iPhone it can be silent. This page says why and
how to fix it in a few lines.

## Why it goes quiet

Safari on iOS plays Web Audio in an "ambient" audio session by default. When the phone is in
silent mode (the ring/silent switch), ambient sound is muted. Your prod is not broken; it just
needs to ask for a playback session. Android and desktop browsers are not affected.

## Three things to do

1. **Ask for a playback session** before you create the audio context:

   ```js
   if (navigator.audioSession) navigator.audioSession.type = "playback";
   const ctx = new (window.AudioContext || window.webkitAudioContext)();
   ctx.resume();
   ```

2. **Start sound from a tap.** Create and resume the context inside your own `click` or
   `touchend` handler, before the first `await`. Browsers only allow sound after a tap inside
   your prod, and a tap on the gallery does not count.
3. **Test on a real phone with silent mode on.** If you hear it there, you are good. If it
   only works with silent mode off, the line above is missing or runs too late.

## Good to know

- An `<audio>` or `<video>` element is not muted by the silent switch on iOS Safari. A plain
  element is the simplest choice for a track that just plays.
- Phones have far less memory than your desktop. Rendering minutes of stereo audio into one
  buffer when the user taps can stall an older phone. Prefer a compressed file or render in chunks.
- Prods run in a sandboxed iframe with an opaque origin. Load your audio with a relative URL;
  GitHub Pages serves it with CORS headers. See [CONTRIBUTING](CONTRIBUTING.md).
- Show a visible message if starting the sound fails. A silent black screen is hard to debug on a phone.
