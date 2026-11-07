/* ===== offline video render hook ===== */
const comp = document.createElement("canvas"); comp.width = 1080; comp.height = 1920; const cx2 = comp.getContext("2d");
const DY = 622, DW = 1080, DH = 675;
window.__R = {
  init() { cur = CFG.tracks.pt; analyser = null; fdata = null; running = false; ended = false; window.__hold = true; document.getElementById("menu").style.display = "none"; sceneIdx = -1; },
  step(t, dt) {
    tNow = t; analyse(t, dt);
    const cues = cur.cues; let i = 0;
    while (i < cues.length - 1 && t >= cues[i + 1][0]) i++;
    if (i !== sceneIdx) { if (sceneIdx >= 0) flash = 1; sceneIdx = i; }
    const local = t - cues[i][0], left = (cues[i + 1] ? cues[i + 1][0] : t + 99) - t, nm = cues[i][1];
    if (nm !== "dancer" && nm !== "end") hiShow(false, true);
    FX[nm](t, dt, local, left);
    if (SAFE) flash = Math.min(flash, .12);
    if (flash > .01) { ctx.fillStyle = `rgba(255,255,255,${flash})`; ctx.fillRect(0, 0, W, H); flash *= Math.exp(-dt * 7); }
    // compose 9:16 frame
    const g = cx2; g.setTransform(1, 0, 0, 1, 0, 0); g.globalAlpha = 1; g.globalCompositeOperation = "source-over";
    const bg = g.createLinearGradient(0, 0, 0, 1920); bg.addColorStop(0, "#07021a"); bg.addColorStop(.5, "#000"); bg.addColorStop(1, "#07021a");
    g.fillStyle = bg; g.fillRect(0, 0, 1080, 1920);
    g.imageSmoothingEnabled = false; g.drawImage(cv, 0, DY, DW, DH);
    let ha = 0; if (hiOn) ha = nm === "end" ? smooth((local - 11.3) / 1.2) : 1;
    if (ha > 0) { g.globalAlpha = ha; g.imageSmoothingEnabled = true; g.drawImage(hi, 0, DY, DW, DH); g.globalAlpha = 1; }
    g.fillStyle = "rgba(0,0,0,.26)"; for (let y = 0; y < 200; y++) g.fillRect(0, DY + y * DH / 200 + DH / 400, DW, DH / 400);
    const vg = g.createRadialGradient(540, DY + DH / 2, DH * .35, 540, DY + DH / 2, DW * .75); vg.addColorStop(0, "rgba(0,0,0,0)"); vg.addColorStop(1, "rgba(0,0,0,.6)");
    g.fillStyle = vg; g.fillRect(0, DY, DW, DH);
    g.strokeStyle = "rgba(120,255,255,.35)"; g.lineWidth = 3; g.strokeRect(1.5, DY - 1.5, DW - 3, DH + 3);
    // titles
    g.textAlign = "center"; g.textBaseline = "alphabetic";
    const tg = g.createLinearGradient(0, 300, 0, 470); tg.addColorStop(0, "#fff"); tg.addColorStop(.45, "#7ff"); tg.addColorStop(.55, "#a4f"); tg.addColorStop(1, "#fff");
    g.font = '64px "Press Start 2P"'; g.fillStyle = "#204"; g.fillText("CRYSTALLINE", 546, 386); g.fillText("DROP", 546, 476);
    g.fillStyle = tg; g.fillText("CRYSTALLINE", 540, 380); g.fillText("DROP", 540, 470);
    g.font = '26px "Press Start 2P"'; g.fillStyle = "#ffe27a"; g.fillText("A 1993-STYLE DEMO", 540, 545);
    g.font = '24px "Press Start 2P"'; g.fillStyle = "#9ff"; g.fillText("VENTURE OF XANADU", 540, 1420);
    g.font = '18px "Press Start 2P"'; g.fillStyle = "#c8f"; g.fillText("MUSIC & DESIGN BY VENTURE", 540, 1470);
    g.font = '900 40px Orbitron'; g.fillStyle = "#fff"; g.shadowColor = "#f0f"; g.shadowBlur = 24; g.fillText("1993 → 2027", 540, 1600); g.shadowBlur = 0;
    g.font = '600 26px Orbitron'; g.fillStyle = "rgba(255,255,255,.8)"; g.fillText("THE AI DEMOSCENE REVIVAL STARTS NOW", 540, 1660);
    return comp.toDataURL("image/jpeg", .9);
  }
};
