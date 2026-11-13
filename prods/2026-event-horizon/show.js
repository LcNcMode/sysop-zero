(() => {
  'use strict';
  const titles = ['Liquid Matter', 'Space Folds', 'Beyond Infinity', 'A Star Is Born', 'Reality Becomes Data', 'City of Light', 'The Signal Breaks', 'Sea of Light'];
  const names = ['MATTER', 'FOLD', 'INFINITY', 'RELEASE', 'SCAN', 'VOXEL TIDE', 'DATAMOSH', 'PHOTON SEA'];
  const bases = [0, 2.8, 5.5, 7.6, 10, 12.5, 15, 17.5];
  const hosts = ['Brumm the Troll', 'Nova the Superhero', 'Lumi the Dragon', 'Mylla the Mushroom'];
  const lines = ['Follow me. Space itself folds here.', 'Come on. We’re going beyond infinity.', 'Even a tiny spark can become a star.', 'What if reality could become data?', 'Let’s build an entire city out of light.', 'Hold tight. The signal is breaking up.', 'And out of the noise … a sea of light.'];
  const introDuration = 9;
  const outroDuration = 8;
  const worldDuration = 16;
  const transitionDuration = 8;
  const worlds = names.flatMap((name, world) => {
    const start = introDuration + world * (worldDuration + transitionDuration);
    const scene = {kind: 'world', world, start, duration: worldDuration};
    if (world === names.length - 1) return [scene];
    return [scene, {kind: 'host', world: world + 1, from: world, presenter: world % hosts.length, start: start + worldDuration, duration: transitionDuration}];
  });
  const lastWorld = worlds.at(-1);
  const outroStart = lastWorld.start + lastWorld.duration;
  const duration = outroStart + outroDuration;
  const segments = [
    {kind: 'intro', world: 0, start: 0, duration: introDuration},
    ...worlds,
    {kind: 'outro', world: lastWorld.world, start: outroStart, duration: outroDuration}
  ];
  function at(time) {
    const t = Math.max(0, Math.min(duration - .00001, time));
    const s = segments.find(scene => t < scene.start + scene.duration);
    return {...s, local: t - s.start};
  }
  const clock = t => String(Math.floor(t / 60)).padStart(2, '0') + ':' + String(Math.floor(t % 60)).padStart(2, '0');
  window.EventHorizon = {segments, duration, at, clock};
  const totalClock = clock(duration);
  window.demoInfo = {renderer: 'WebGL2', duration, introDuration, outroDuration, worlds: names.length, worldDuration, transitions: names.length - 1, transitionDuration, presenters: hosts.length};

  const $ = id => document.getElementById(id);
  const canvas = $('screen');
  const chapters = [...document.querySelectorAll('[data-world]')];
  let state = 'idle', elapsed = 0, epoch = 0, dirty = true, lastSegment = -1;
  const audio = $('soundtrack');
  let muted = false;
  let mediaClock = true;
  let pendingSeek = null;
  let playbackRequest = 0;
  let mouse = [0, 0];

  function stopAudio() {
    playbackRequest++;
    audio.pause();
  }

  function seekAudio(time) {
    if (audio.readyState < 1) {
      pendingSeek = time;
      return;
    }
    pendingSeek = null;
    audio.currentTime = time * audio.playbackRate;
  }

  function syncAudioDuration() {
    if (Number.isFinite(audio.duration) && audio.duration > 0) {
      audio.defaultPlaybackRate = audio.duration / duration;
      audio.playbackRate = audio.defaultPlaybackRate;
    }
    if (pendingSeek !== null) seekAudio(pendingSeek);
  }
  audio.addEventListener('loadedmetadata', syncAudioDuration);
  if (audio.readyState >= 1) syncAudioDuration();

  function useSilentClock() {
    mediaClock = false;
    epoch = performance.now() - elapsed * 1000;
  }

  audio.addEventListener('error', useSilentClock);

  function soundtrack() {
    const request = ++playbackRequest;
    mediaClock = true;
    audio.play().catch(error => {
      if (request !== playbackRequest || state !== 'playing') return;
      console.warn('Audio could not start', error);
      useSilentClock();
    });
  }

  function playbackTime(now) {
    if (!mediaClock) return (now - epoch) / 1000;
    if (audio.ended) return duration;
    if (pendingSeek !== null || audio.seeking) return elapsed;
    return audio.currentTime / audio.playbackRate;
  }

  function play(from = 0, paused = false) {
    if (state === 'lost') return;
    elapsed = Math.max(0, Math.min(duration - .01, from));
    epoch = performance.now() - elapsed * 1000;
    state = paused ? 'paused' : 'playing';
    document.body.className = paused ? 'playing paused' : 'playing';
    lastSegment = -1;
    dirty = true;
    stopAudio();
    seekAudio(elapsed);
    if (!paused) soundtrack();
  }
  function pause() {
    if (state === 'playing') {
      elapsed = Math.min(duration, playbackTime(performance.now()));
      state = 'paused';
      document.body.className = 'playing paused';
      stopAudio();
      $('pause').textContent = 'RESUME';
    } else if (state === 'paused') {
      epoch = performance.now() - elapsed * 1000;
      state = 'playing';
      document.body.className = 'playing';
      seekAudio(elapsed);
      soundtrack();
      $('pause').textContent = 'PAUSE';
    }
  }
  function fail(error) {
    state = 'lost';
    stopAudio();
    $('error').textContent = error.message;
    $('error').style.display = 'grid';
    $('start').disabled = true;
  }
  function showCard(id, opacity) {
    const card = $(id);
    card.style.opacity = opacity;
    card.setAttribute('aria-hidden', String(opacity === 0));
  }
  function cardOpacity(time, start, end, fade) {
    return Math.max(0, Math.min(1, (time - start) / fade, (end - time) / fade));
  }
  function update(scene) {
    const speaking = scene.kind === 'host';
    const isIntro = scene.kind === 'intro';
    const isOutro = scene.kind === 'outro';
    const bookend = isIntro || isOutro;
    $('clock').textContent = clock(elapsed) + ' / ' + totalClock;
    $('bar').style.width = elapsed / duration * 100 + '%';
    $('seek').value = elapsed;
    $('pause').textContent = state === 'paused' ? 'RESUME' : 'PAUSE';
    chapters.forEach((el, i) => {
      const active = !bookend && i === scene.world;
      el.classList.toggle('active', active);
      el.setAttribute('aria-current', active ? 'step' : 'false');
    });
    $('worldlabel').classList.toggle('visible', !bookend);
    $('worldnumber').textContent = speaking ? hosts[scene.presenter].toUpperCase() + ' PRESENTS' : 'WORLD ' + String(scene.world + 1).padStart(2, '0') + ' / 08';
    $('worldname').textContent = titles[scene.world];
    $('speech').classList.toggle('visible', speaking && scene.local > 1.1 && scene.local < 6.4);
    $('speech').textContent = speaking ? '”' + lines[scene.world - 1] + '”' : '';
    $('nextbadge').classList.toggle('visible', speaking && scene.local > 2 && scene.local < 6.5);
    $('nextbadge').textContent = speaking ? names[scene.world] : '';
    showCard('xanadu', isIntro ? cardOpacity(scene.local, .35, 3.8, .75) : 0);
    showCard('sequence', isIntro ? cardOpacity(scene.local, 3.75, 7.35, .7) : 0);
    const creditsOpacity = isOutro ? Math.max(0, Math.min(1, (scene.local - 1.8) / 1.15)) : 0;
    showCard('credits', state === 'finished' ? 1 : creditsOpacity);
  }

  function setup(gl) {
    function program(vertex, fragment) {
      const p = gl.createProgram();
      for (const [type, id] of [[gl.VERTEX_SHADER, vertex], [gl.FRAGMENT_SHADER, fragment]]) {
        const shader = gl.createShader(type);
        gl.shaderSource(shader, $(id).textContent);
        gl.compileShader(shader);
        if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) throw Error(gl.getShaderInfoLog(shader));
        gl.attachShader(p, shader);
      }
      gl.linkProgram(p);
      if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw Error(gl.getProgramInfoLog(p));
      return p;
    }
    const scene = program('vertex', 'scene'), post = program('vertex', 'post');
    const portal = program('vertex', 'portal'), bookend = program('vertex', 'bookend');
    const particles = program('particles-vertex', 'particles-fragment');
    const toys = window.createToyRenderer(gl);
    const quad = gl.createVertexArray();
    gl.bindVertexArray(quad);
    gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer());
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1,-1, 1,-1, -1,1, -1,1, 1,-1, 1,1]), gl.STATIC_DRAW);
    for (const p of [scene, post, portal, bookend]) {
      const a = gl.getAttribLocation(p, 'aPos');
      gl.enableVertexAttribArray(a);
      gl.vertexAttribPointer(a, 2, gl.FLOAT, false, 0, 0);
    }
    gl.bindVertexArray(null);
    const locations = (p, list) => Object.fromEntries(list.map(name => [name, gl.getUniformLocation(p, name)]));
    const sl = locations(scene, ['uScene','uLocal','uTime','uDelta','uRes','uMouse','uPrev','uCapture']);
    const pl = locations(post, ['uTime','uRes','uTex','uDigital','uPulse']);
    const cl = locations(portal, ['uPhase','uAspect','uFX','uHost','uOld']);
    const bl = locations(bookend, ['uLocal', 'uAspect', 'uWorld', 'uClosing']);
    const pt = locations(particles, ['uTime','uRes']);
    function texture(unit, tex) {
      gl.activeTexture(gl.TEXTURE0 + unit);
      gl.bindTexture(gl.TEXTURE_2D, tex);
    }
    function target(depth = false) {
      const tex = gl.createTexture(), fbo = gl.createFramebuffer();
      texture(0, tex);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
      gl.bindFramebuffer(gl.FRAMEBUFFER, fbo);
      gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tex, 0);
      const depthBuffer = depth ? gl.createRenderbuffer() : null;
      if (depthBuffer) {
        gl.bindRenderbuffer(gl.RENDERBUFFER, depthBuffer);
        gl.framebufferRenderbuffer(gl.FRAMEBUFFER, gl.DEPTH_ATTACHMENT, gl.RENDERBUFFER, depthBuffer);
      }
      return {tex, fbo, depthBuffer};
    }
    const fx = [target(), target()], host = target(true), mixed = target(), capture = target(), outgoing = target();
    const targets = [...fx, host, mixed, capture, outgoing];
    let width = 0, height = 0, index = 0, previousWorld = -1, captured = false, previousTime = 0;
    let quality = 1, frames = 0, qualityAt = 0;

    function resize() {
      const aspect = innerWidth / innerHeight;
      const budget = (innerWidth < 700 ? 380000 : 800000) * quality;
      const h = Math.max(1, Math.round(Math.min(innerHeight * devicePixelRatio, Math.sqrt(budget / aspect))));
      const w = Math.max(1, Math.round(h * aspect));
      if (w === width && h === height) return false;
      canvas.width = width = w;
      canvas.height = height = h;
      gl.viewport(0, 0, width, height);
      for (const f of targets) {
        texture(0, f.tex);
        gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, w, h, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
        gl.bindFramebuffer(gl.FRAMEBUFFER, f.fbo);
        if (f.depthBuffer) {
          gl.bindRenderbuffer(gl.RENDERBUFFER, f.depthBuffer);
          gl.renderbufferStorage(gl.RENDERBUFFER, gl.DEPTH_COMPONENT16, w, h);
        }
        if (gl.checkFramebufferStatus(gl.FRAMEBUFFER) !== gl.FRAMEBUFFER_COMPLETE) throw Error('The graphics buffer could not be initialized.');
        gl.clearColor(0, 0, 0, 1);
        gl.clear(gl.COLOR_BUFFER_BIT);
      }
      captured = false;
      lastSegment = -1;
      previousWorld = -1;
      return true;
    }
    function drawEffect(world, local, dest, delta, useCapture = true) {
      gl.bindFramebuffer(gl.FRAMEBUFFER, dest.fbo);
      gl.bindVertexArray(quad);
      gl.useProgram(scene);
      gl.disable(gl.DEPTH_TEST);
      gl.disable(gl.BLEND);
      const previous = fx[1 - index].tex;
      texture(0, previous);
      texture(1, useCapture ? capture.tex : previous);
      gl.uniform1i(sl.uPrev, 0);
      gl.uniform1i(sl.uCapture, 1);
      gl.uniform1i(sl.uScene, world);
      gl.uniform1f(sl.uLocal, local);
      gl.uniform1f(sl.uTime, bases[world] + local);
      gl.uniform1f(sl.uDelta, delta);
      gl.uniform2f(sl.uRes, width, height);
      gl.uniform2fv(sl.uMouse, mouse);
      gl.drawArrays(gl.TRIANGLES, 0, 6);
      if (world === 7) {
        gl.useProgram(particles);
        gl.uniform1f(pt.uTime, bases[world] + local);
        gl.uniform2f(pt.uRes, width, height);
        gl.enable(gl.BLEND);
        gl.blendFunc(gl.ONE, gl.ONE);
        gl.drawArrays(gl.POINTS, 0, 55296);
        gl.disable(gl.BLEND);
      }
      return dest;
    }
    function effect(world, local, delta) {
      if (world === 6 && !captured) {
        drawEffect(5, 9, capture, delta, false);
        captured = true;
      }
      const result = drawEffect(world, local, fx[index], delta);
      index = 1 - index;
      previousWorld = world;
      return result;
    }
    function transition(s, delta) {
      if (lastSegment !== s.start) {
        const previous = previousWorld === s.from ? fx[1 - index] : effect(s.from, 15.8, delta);
        gl.bindFramebuffer(gl.FRAMEBUFFER, previous.fbo);
        texture(2, outgoing.tex);
        gl.copyTexSubImage2D(gl.TEXTURE_2D, 0, 0, 0, 0, 0, width, height);
      }
      const preview = effect(s.world, Math.max(0, s.local - 2) * .25, delta);
      gl.bindFramebuffer(gl.FRAMEBUFFER, host.fbo);
      toys.renderPresentation(s.presenter, s.local, width, height);
      gl.bindFramebuffer(gl.FRAMEBUFFER, mixed.fbo);
      gl.bindVertexArray(quad);
      gl.useProgram(portal);
      texture(0, preview.tex);
      texture(1, host.tex);
      texture(2, outgoing.tex);
      gl.uniform1i(cl.uFX, 0);
      gl.uniform1i(cl.uHost, 1);
      gl.uniform1i(cl.uOld, 2);
      gl.uniform1f(cl.uPhase, s.local);
      gl.uniform1f(cl.uAspect, width / height);
      gl.drawArrays(gl.TRIANGLES, 0, 6);
      return mixed;
    }
    function drawBookend(s, delta) {
      const closing = s.kind === 'outro';
      const showingWorld = closing ? s.local < 2.65 : s.local > 6.65;
      const world = showingWorld ? effect(s.world, closing ? worldDuration + 1.5 : 0, delta) : fx[1 - index];
      gl.bindFramebuffer(gl.FRAMEBUFFER, mixed.fbo);
      gl.bindVertexArray(quad);
      gl.useProgram(bookend);
      texture(0, world.tex);
      gl.uniform1i(bl.uWorld, 0);
      gl.uniform1i(bl.uClosing, Number(closing));
      gl.uniform1f(bl.uLocal, s.local);
      gl.uniform1f(bl.uAspect, width / height);
      gl.drawArrays(gl.TRIANGLES, 0, 6);
      return mixed;
    }
    function frame(now) {
      if (state === 'lost') return;
      requestAnimationFrame(frame);
      if (document.hidden) return;
      try {
        const changed = resize();
        if ((state === 'paused' || state === 'finished') && !changed && !dirty) {
          previousTime = now;
          return;
        }
        if (state === 'playing') {
          elapsed = Math.min(duration, playbackTime(now));
          if (elapsed === duration) {
            state = 'finished';
            document.body.className = 'finished';
            stopAudio();
          }
        }
        const s = state === 'idle' ? {kind: 'world', world: 0, local: 1.15 + Math.sin(now * .0003) * .35, start: -1} : at(elapsed);
        const delta = previousTime ? Math.min(.05, (now - previousTime) / 1000) : 1 / 60;
        let result;
        if (s.kind === 'host') result = transition(s, delta);
        else if (s.kind === 'world') result = effect(s.world, s.local + (s.world ? 1.5 : 0), delta);
        else result = drawBookend(s, delta);
        gl.bindFramebuffer(gl.FRAMEBUFFER, null);
        gl.bindVertexArray(quad);
        gl.useProgram(post);
        texture(0, result.tex);
        gl.uniform1i(pl.uTex, 0);
        gl.uniform2f(pl.uRes, width, height);
        gl.uniform1f(pl.uTime, state === 'idle' ? 1 : elapsed);
        gl.uniform1f(pl.uDigital, s.world >= 4 && s.world <= 6 ? 1 : 0);
        gl.uniform1f(pl.uPulse, s.kind === 'host' ? Math.exp(-Math.abs(s.local - 7.8) * 12) * .2 : 0);
        gl.drawArrays(gl.TRIANGLES, 0, 6);
        gl.bindVertexArray(null);
        lastSegment = s.start;
        dirty = false;
        if (state !== 'idle') update(s);
        frames++;
        if (now - qualityAt > 2000) {
          if (s.world !== 6) {
            if (frames < 43 && quality > .4) quality *= .8;
            if (frames > 108 && quality < 1) quality = Math.min(1, quality * 1.15);
          }
          frames = 0;
          qualityAt = now;
        }
        previousTime = now;
      } catch (error) {
        console.error(error);
        fail(error);
      }
    }
    canvas.addEventListener('webglcontextlost', event => {
      event.preventDefault();
      fail(Error('The graphics connection was lost. Reload the page to restart.'));
    });
    requestAnimationFrame(frame);
  }

  $('start').onclick = () => play();
  $('replay').onclick = () => play();
  $('new').onclick = () => play(introDuration + worldDuration);
  $('pause').onclick = pause;
  $('seek').oninput = event => play(Number(event.target.value), state === 'paused');
  chapters.forEach((button, i) => {
    const introduction = segments.find(s => s.world === i && s.kind === (i ? 'host' : 'world'));
    button.onclick = () => play(introduction.start);
  });
  $('sound').onclick = () => {
    muted = !muted;
    $('sound').textContent = muted ? 'SOUND OFF' : 'SOUND ON';
    $('sound').setAttribute('aria-pressed', String(!muted));
    audio.muted = muted;
    if (!muted && state === 'playing' && !mediaClock) {
      seekAudio(elapsed);
      soundtrack();
    }
  };
  $('full').onclick = async () => {
    try {
      if (document.fullscreenElement) await document.exitFullscreen();
      else if (document.documentElement.requestFullscreen) await document.documentElement.requestFullscreen();
      else $('full').textContent = '↔ ROTATE YOUR SCREEN';
    } catch { $('full').textContent = '↔ ROTATE YOUR SCREEN'; }
  };
  document.addEventListener('pointermove', event => {
    mouse = [event.clientX / innerWidth - .5, .5 - event.clientY / innerHeight];
  });
  document.addEventListener('keydown', event => {
    if (event.code === 'Space' && !['BUTTON', 'INPUT'].includes(event.target.tagName)) {
      event.preventDefault();
      if (state === 'playing' || state === 'paused') pause();
      else play();
    }
    if (event.key === 'Escape' && (state === 'playing' || state === 'paused')) {
      stopAudio();
      state = 'idle';
      elapsed = 0;
      $('clock').textContent = '00:00 / ' + totalClock;
      $('bar').style.width = '0%';
      $('seek').value = 0;
      $('speech').classList.toggle('visible', false);
      $('nextbadge').classList.toggle('visible', false);
      for (const id of ['xanadu', 'sequence', 'credits']) showCard(id, 0);
      document.body.className = '';
    }
  });
  document.addEventListener('visibilitychange', () => {
    if (document.hidden && state === 'playing') pause();
  });
  try {
    const gl = canvas.getContext('webgl2', {alpha: false, antialias: false, powerPreference: 'high-performance', depth: false, stencil: false});
    if (!gl) throw Error('WebGL2 is unavailable in this browser. Open the demo in Safari or Chrome with hardware acceleration enabled.');
    setup(gl);
  } catch (error) {
    console.error(error);
    fail(error);
  }
})();
