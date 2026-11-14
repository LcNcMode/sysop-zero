'use strict';
const film = document.querySelector('#film');
const cover = document.querySelector('#cover');
const start = document.querySelector('#start');
const status = document.querySelector('#status');
const controls = document.querySelector('#controls');
const toggle = document.querySelector('#toggle');
const dialog = document.querySelector('#declaration');
const format = t => '00:' + String(Math.floor(t || 0)).padStart(2, '0');
function update() {
  document.querySelector('#clock').textContent = format(film.currentTime) + ' / ' + format(film.duration || 36.432);
  document.querySelector('#progress i').style.width = (100 * film.currentTime / (film.duration || 36.432)) + '%';
  toggle.textContent = film.ended ? 'Play again' : film.paused ? 'Play' : 'Pause';
  toggle.setAttribute('aria-label', toggle.textContent);
}
async function play() {
  if (film.ended) film.currentTime = 0;
  film.muted = false;
  film.volume = 1;
  try {
    await film.play();
    cover.hidden = true;
    controls.hidden = false;
  } catch (error) {
    cover.hidden = false;
    status.textContent = 'Press Play with sound to start.';
  }
  update();
}
start.addEventListener('click', play);
toggle.addEventListener('click', () => film.paused ? play() : film.pause());
document.querySelector('#replay').addEventListener('click', () => { film.currentTime = 0; play(); });
for (const event of ['timeupdate', 'play', 'pause', 'ended', 'loadedmetadata']) film.addEventListener(event, update);
film.addEventListener('error', () => { cover.hidden = false; status.textContent = 'The film could not load. Please reload.'; });
document.querySelector('#fullscreen').addEventListener('click', () => {
  const target = document.querySelector('#cinema');
  if (document.fullscreenElement) document.exitFullscreen();
  else if (target.requestFullscreen) target.requestFullscreen().catch(() => {});
  else if (film.webkitEnterFullscreen) film.webkitEnterFullscreen();
});
document.querySelector('#about').onclick = () => { film.pause(); dialog.showModal(); };
document.querySelector('#close').onclick = () => dialog.close();
document.addEventListener('visibilitychange', () => { if (document.hidden) film.pause(); });
status.textContent = '36 seconds · A Venture production';
update();
