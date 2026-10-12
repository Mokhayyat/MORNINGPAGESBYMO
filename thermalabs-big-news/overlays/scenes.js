// Every graphic in the reel, placed on the master timeline in output time. Cue times come from
// timeline.json (source seconds) through ctx.out(); things pinned to a hand use the hand tracks and
// the picture pass's per-frame mapping (ctx.anchor), so they stay on the hand through zooms.
import { ICONS, GARMENT } from './icons.js';
import { Frost, buildCrack } from './frost.js';

const TOP = 262;          // first line below the 250 px top safe area
const CAP_TOP = 1392;     // caption pill top edge; nothing on the chest may come below this

function el(stage, cls, html = '') {
  const d = document.createElement('div');
  d.className = `${cls} abs`;
  d.innerHTML = html;
  stage.appendChild(d);
  return d;
}

function handAt(rows, src) {
  if (!rows || !rows.length) return [0, 0];
  if (src <= rows[0][0]) return [rows[0][1], rows[0][2]];
  for (let i = 1; i < rows.length; i++) {
    if (rows[i][0] >= src) {
      const [t0, x0, y0] = rows[i - 1], [t1, x1, y1] = rows[i];
      const u = (src - t0) / Math.max(1e-6, t1 - t0);
      return [x0 + (x1 - x0) * u, y0 + (y1 - y0) * u];
    }
  }
  const r = rows[rows.length - 1];
  return [r[1], r[2]];
}

const clamp = (v, a, b) => Math.max(a, Math.min(b, v));

export async function buildScenes(tl, ctx, stage) {
  const C = ctx.tl.cues;
  const O = (s) => ctx.out(s);
  const W = ctx.W;

  // ---------------------------------------------------------------- hook: glow, sticker, tape
  const glow = el(stage, 'glow');
  tl.fromTo(glow, { opacity: 0 }, { opacity: 1, duration: 0.07, ease: 'none', immediateRender: false }, O(C.glow.in));
  tl.to(glow, { opacity: 0.72, duration: 0.22, ease: 'sine.inOut', yoyo: true, repeat: 1 }, O(C.glow.in) + 0.12);
  tl.to(glow, { opacity: 0, duration: 0.45, ease: 'power1.in' }, O(C.glow.out) - 0.45);

  const sticker = el(stage, 'sticker', C.sticker.text);
  const sw = sticker.offsetWidth, sh = sticker.offsetHeight;
  gsap.set(sticker, { x: (W - sw) / 2, y: 1190 - sh / 2, rotation: -7, opacity: 0 });
  const tS = Math.max(0.02, O(C.sticker.in) - 0.02);
  tl.fromTo(sticker, { scale: 2.3, rotation: -16, opacity: 0 },
    { scale: 1, rotation: -7, opacity: 1, duration: 0.15, ease: 'back.out(1.5)', immediateRender: false }, tS);
  tl.to(sticker, { x: '+=7', duration: 0.035, yoyo: true, repeat: 3, ease: 'none' }, tS + 0.15);
  tl.to(sticker, { scale: 0.55, opacity: 0, rotation: -3, duration: 0.14, ease: 'power2.in' }, O(C.sticker.out));

  const tape = el(stage, 'tape', `<div class="hz"></div><div class="tb">${ICONS.warn}<span>${C.tape.text}</span>${ICONS.warn}</div><div class="hz"></div>`);
  gsap.set(tape, { x: 1240, y: 276, rotation: -3, transformOrigin: '50% 50%' });
  tl.to(tape, { x: -50, duration: 0.3, ease: 'power3.out' }, O(C.tape.in));
  tl.to(tape, { x: -1560, duration: 0.32, ease: 'power2.in' }, O(C.tape.out));

  // ---------------------------------------------------------------- upgrade card (sticks at 99 %)
  function upgradeCard(withGuess) {
    const c = el(stage, 'card upgrade', `
      <div class="row"><span class="micro">ThermaLabs upgrade</span><span class="pct"><b>0</b><small>%</small></span></div>
      <div class="bar"><i></i></div>
      <div class="foot"><span class="dot"></span><span class="status">Installing upgrade</span></div>
      ${withGuess ? `<div class="guess">${ICONS.comment}<span>Guess who? <em>Comment below</em></span></div>` : ''}`);
    gsap.set(c, { x: (W - 760) / 2, y: TOP, opacity: 0 });
    return c;
  }
  const up = upgradeCard(false);
  const upPct = up.querySelector('.pct b'), upBar = up.querySelector('.bar i'), upStatus = up.querySelector('.status');
  const upDot = up.querySelector('.dot');
  tl.fromTo(up, { y: TOP - 40, opacity: 0, scale: 0.96 }, { y: TOP, opacity: 1, scale: 1, duration: 0.3, ease: 'power3.out', immediateRender: false }, O(C.upgrade.in));
  tl.to(up, { y: TOP - 34, opacity: 0, duration: 0.22, ease: 'power2.in' }, O(C.upgrade.out));
  const f0 = O(C.upgrade.fill_from), f1 = O(C.upgrade.fill_to), stuck = C.upgrade.stuck;
  ctx.updaters.push((t) => {
    const u = clamp((t - f0) / (f1 - f0), 0, 1);
    const e = 1 - Math.pow(1 - u, 2.2);
    const pct = Math.round(e * stuck);
    upPct.textContent = String(pct);
    upBar.style.width = `${pct}%`;
    upStatus.textContent = u >= 1 ? 'Almost there' : 'Installing upgrade';
    upDot.style.opacity = u >= 1 ? String(0.35 + 0.65 * (0.5 + 0.5 * Math.sin(t * 14))) : '1';
  });

  // ---------------------------------------------------------------- ID badge + SIGNING SOON stamp
  const bw = el(stage, 'badge-wrap', `
    <div class="clip"></div>
    <div class="badge">
      <div class="b-head">ThermaLabs</div>
      <div class="b-body">
        <div class="avatar">${ICONS.silhouette}<span class="q">?</span></div>
        <div class="redact"></div>
        <div class="b-title">Technical Expert</div>
      </div>
    </div>`);
  const BADGE_X = 664;
  const bh = bw.offsetHeight;
  const BADGE_Y = CAP_TOP - 22 - bh;
  gsap.set(bw, { x: BADGE_X, y: BADGE_Y, opacity: 0, transformOrigin: '50% 0%' });
  const tB = O(C.badge.in);
  tl.fromTo(bw, { y: BADGE_Y - 520, rotation: -16, opacity: 1 },
    { y: BADGE_Y, rotation: 0, duration: 0.42, ease: 'back.out(1.25)', immediateRender: false }, tB);
  tl.fromTo(bw, { rotation: -16 }, { keyframes: [{ rotation: 7, duration: 0.2 }, { rotation: -3.5, duration: 0.16 }, { rotation: 1.2, duration: 0.14 }, { rotation: 0, duration: 0.12 }], ease: 'sine.inOut', immediateRender: false }, tB);
  const stamp = el(stage, 'stamp', 'SIGNING SOON');
  const stw = stamp.offsetWidth, sth = stamp.offsetHeight;
  gsap.set(stamp, { x: BADGE_X + 131 - stw / 2, y: BADGE_Y + bh * 0.66 - sth / 2, rotation: -10, opacity: 0 });
  const tSt = O(C.badge.stamp);
  tl.fromTo(stamp, { scale: 2.4, opacity: 0 }, { scale: 1, opacity: 0.96, duration: 0.11, ease: 'power4.in', immediateRender: false }, tSt - 0.11);
  tl.to(bw, { x: `+=${5}`, duration: 0.03, yoyo: true, repeat: 3, ease: 'none' }, tSt);
  tl.to([bw, stamp], { y: '+=70', opacity: 0, duration: 0.26, ease: 'power2.in' }, O(C.badge.out));

  // ---------------------------------------------------------------- chips + hologram jacket
  const chips = C.chips.rows.map((r, i) => {
    const c = el(stage, 'chip', `<span class="ic">${ICONS[r.icon]}</span><span>${r.text}</span>`);
    gsap.set(c, { x: 104, y: TOP + i * 82, opacity: 0 });
    tl.fromTo(c, { x: 50, opacity: 0 }, { x: 104, opacity: 1, duration: 0.32, ease: 'power3.out', immediateRender: false }, O(r.t) - 0.04);
    tl.fromTo(c.querySelector('.ic'), { scale: 0.4 }, { scale: 1, duration: 0.3, ease: 'back.out(3)', immediateRender: false }, O(r.t) - 0.04);
    return c;
  });
  tl.to(chips, { x: 40, opacity: 0, duration: 0.22, ease: 'power2.in', stagger: 0.03 }, O(C.chips.out));
  const mer = chips[2].querySelector('.mer');
  ctx.updaters.push((t) => mer.setAttribute('rx', (0.6 + 8.4 * Math.abs(Math.cos(t * 2.6))).toFixed(2)));

  const jk = el(stage, 'jacket', `<div class="tag">COOLING TECH</div>${GARMENT}<div class="scan"></div>`);
  const chipRight = Math.max(...chips.map((c) => c.offsetWidth)) + 104;
  const JX = clamp(chipRight + 26, 640, 728);
  gsap.set(jk, { x: JX, y: TOP + 14, opacity: 0, transformOrigin: '50% 50%' });
  const tJ = O(C.chips.jacket_in);
  tl.fromTo(jk, { scale: 0.82, opacity: 0 }, { scale: 1, opacity: 1, duration: 0.3, ease: 'back.out(1.6)', immediateRender: false }, tJ);
  const gPaths = [...jk.querySelectorAll('path')];
  gPaths.forEach((p) => { const L = p.getTotalLength(); p.style.strokeDasharray = `${L} ${L}`; p.style.strokeDashoffset = `${L}`; p.dataset.len = L; });
  tl.fromTo(gPaths, { strokeDashoffset: (i, p) => +p.dataset.len }, { strokeDashoffset: 0, duration: 0.55, ease: 'power2.out', stagger: 0.008, immediateRender: false }, tJ + 0.05);
  tl.to(jk, { scale: 0.9, opacity: 0, duration: 0.2, ease: 'power2.in' }, O(C.chips.jacket_out));
  const scan = jk.querySelector('.scan');
  ctx.updaters.push((t) => { const u = ((t - tJ) % 1.1 + 1.1) % 1.1 / 1.1; scan.style.top = `${24 + u * 190}px`; scan.style.opacity = String(Math.sin(u * Math.PI)); });

  // ---------------------------------------------------------------- stay tuned: 99 % again + guess who
  const st = upgradeCard(true);
  st.querySelector('.pct b').textContent = String(stuck);
  st.querySelector('.bar i').style.width = `${stuck}%`;
  st.querySelector('.status').innerHTML = 'Reveal <b>in the coming days</b>';
  const guess = st.querySelector('.guess');
  gsap.set(guess, { height: 0, opacity: 0, marginTop: 0, paddingTop: 0, overflow: 'hidden' });
  const stDot = st.querySelector('.dot');
  const tSt2 = O(C.staytuned.in);
  tl.fromTo(st, { y: TOP - 40, opacity: 0, scale: 0.96 }, { y: TOP, opacity: 1, scale: 1, duration: 0.3, ease: 'power3.out', immediateRender: false }, tSt2);
  tl.to(guess, { height: 'auto', marginTop: 16, paddingTop: 16, opacity: 1, duration: 0.28, ease: 'power3.out' }, O(C.staytuned.guess));
  tl.to(st, { y: TOP - 34, opacity: 0, duration: 0.22, ease: 'power2.in' }, O(ctx.pick(C.staytuned.out)));
  ctx.updaters.push((t) => { stDot.style.opacity = String(0.35 + 0.65 * (0.5 + 0.5 * Math.sin(t * 14))); });

  // ---------------------------------------------------------------- Follow button at the pointing finger
  const fol = el(stage, 'follow', `
    <div class="av">${ICONS.mark('#fff')}</div>
    <div class="names"><b>ThermaLabs</b><i>@thermalabs.io</i></div>
    <div class="btn"><span class="f1">Follow</span><span class="f2">${ICONS.check}Following</span></div>`);
  const tF = O(C.follow.in), tTap = O(C.follow.tap);
  const tip = ctx.anchor(handAt(ctx.hands.point, 9.97), O(9.97));
  const fw = fol.offsetWidth, fh = fol.offsetHeight;
  const FX = clamp(tip[0] + 40, 60, W - 150 - fw), FY = clamp(tip[1] - 150 - fh / 2, 900, CAP_TOP - 30 - fh);
  gsap.set(fol, { x: FX, y: FY, opacity: 0, transformOrigin: '0% 100%' });
  tl.fromTo(fol, { scale: 0.55, opacity: 0 }, { scale: 1, opacity: 1, duration: 0.28, ease: 'back.out(1.7)', immediateRender: false }, tF);
  const btn = fol.querySelector('.btn'), f1e = fol.querySelector('.f1'), f2e = fol.querySelector('.f2');
  const tapEl = el(fol, 'tap');
  tapEl.classList.remove('abs');
  tapEl.style.position = 'absolute';
  tapEl.style.left = `${btn.offsetLeft + btn.offsetWidth / 2}px`;
  tapEl.style.top = `${btn.offsetTop + btn.offsetHeight / 2}px`;
  tl.fromTo(tapEl, { scale: 0.3, opacity: 0.95 }, { scale: 1.5, opacity: 0, duration: 0.42, ease: 'power2.out', immediateRender: false }, tTap);
  tl.fromTo(btn, { scale: 1 }, { keyframes: [{ scale: 0.9, duration: 0.07 }, { scale: 1, duration: 0.14 }], immediateRender: false }, tTap);
  tl.to(f1e, { opacity: 0, duration: 0.08 }, tTap + 0.05);
  tl.to(f2e, { opacity: 1, duration: 0.08 }, tTap + 0.05);
  tl.to(fol, { y: FY + 24, opacity: 0, duration: 0.2, ease: 'power2.in' }, O(ctx.pick(C.follow.out)));

  // ---------------------------------------------------------------- URL pill (types itself) + apply line
  const url = el(stage, 'url', `<div class="pill">${ICONS.arrow}<span class="txt"></span><span class="caret"></span></div>
    <div class="apply">Apply by <em>23 November</em> · only 8 teams</div>`);
  gsap.set(url, { x: 0, y: TOP + 10, opacity: 0 });
  const tU = O(C.url.in);
  const pill = url.querySelector('.pill'), apply = url.querySelector('.apply');
  const txt = url.querySelector('.txt'), caret = url.querySelector('.caret');
  const URL_TEXT = 'thermalabs.io/challenge';
  // fix the pill width to the full text so it doesn't grow while typing
  txt.textContent = URL_TEXT; const pw = pill.offsetWidth; pill.style.width = `${pw}px`; txt.textContent = '';
  tl.fromTo(url, { y: TOP - 20, opacity: 0 }, { y: TOP + 10, opacity: 1, duration: 0.28, ease: 'power3.out', immediateRender: false }, tU);
  gsap.set(apply, { opacity: 0, y: 10 });
  tl.to(apply, { opacity: 1, y: 0, duration: 0.25, ease: 'power2.out' }, tU + 0.62);
  tl.to(url, { y: TOP - 20, opacity: 0, duration: 0.22, ease: 'power2.in' }, O(C.url.out));
  ctx.updaters.push((t) => {
    const u = clamp((t - tU - 0.06) / 0.5, 0, 1);
    txt.textContent = URL_TEXT.slice(0, Math.round(u * URL_TEXT.length));
    caret.style.opacity = u < 1 ? '1' : (Math.floor((t - tU) * 2.4) % 2 ? '0' : '1');
  });

  // ---------------------------------------------------------------- journey polaroids
  const POL = [[205, 1236, -9], [408, 1222, 5], [612, 1238, -4], [806, 1224, 8]];
  const pols = C.polaroids.stills.map((src, i) => {
    const p = el(stage, 'pol', `<img src="assets/stills/${src}" alt=""><div class="flashp"></div>`);
    const [cx, cy, rot] = POL[i];
    const pw2 = 214, ph2 = 286;
    p.style.width = `${pw2}px`;
    p.querySelector('img').style.width = '190px';
    p.querySelector('img').style.height = '237px';
    const fl = p.querySelector('.flashp');
    Object.assign(fl.style, { position: 'absolute', left: '12px', top: '12px', width: '190px', height: '237px', background: '#fff', opacity: 0 });
    gsap.set(p, { x: cx - pw2 / 2, y: cy - ph2 / 2, rotation: rot, opacity: 0 });
    const t = O(C.polaroids.in[i]);
    tl.fromTo(p, { y: cy - ph2 / 2 + 330, rotation: rot + (i % 2 ? 20 : -20), scale: 0.85, opacity: 0 },
      { y: cy - ph2 / 2, rotation: rot, scale: 1, opacity: 1, duration: 0.36, ease: 'power3.out', immediateRender: false }, t - 0.06);
    tl.fromTo(fl, { opacity: 0.85 }, { opacity: 0, duration: 0.3, ease: 'power1.out', immediateRender: false }, t + 0.2);
    return p;
  });
  tl.to(pols, { y: '+=260', opacity: 0, duration: 0.24, ease: 'power2.in', stagger: 0.025 }, O(C.polaroids.out));

  // ---------------------------------------------------------------- heart from the hand on the chest
  const tH = O(C.heart.in);
  let [hx, hy] = ctx.anchor(handAt(ctx.hands.chest, C.heart.in), tH);
  hx = clamp(hx + 30, 200, 860); hy = clamp(hy - 170, 1150, 1290);
  const hearts = [[0, 0, 1, 0], [-74, 40, 0.5, 0.1], [70, 52, 0.42, 0.18]].map(([dx, dy, s, dl]) => {
    const h = el(stage, 'heart', ICONS.heart);
    gsap.set(h, { x: hx + dx, y: hy + dy, scale: 0, opacity: 0 });
    tl.fromTo(h, { scale: 0, opacity: 0 }, { scale: s * 1.25, opacity: 1, duration: 0.16, ease: 'back.out(3)', immediateRender: false }, tH + dl);
    tl.to(h, { scale: s, duration: 0.1 }, tH + dl + 0.16);
    tl.to(h, { y: hy + dy - 120, opacity: 0, duration: 0.55, ease: 'power1.in' }, tH + dl + 0.24);
    return h;
  });
  void hearts;

  // ---------------------------------------------------------------- ring on the fist (follows it)
  const ring = el(stage, 'ring'), ring2 = el(stage, 'ring two');
  const tR = O(C.ring.in), tR1 = O(C.ring.out);
  tl.fromTo(ring, { scale: 0.5, opacity: 0 }, { scale: 1, opacity: 1, duration: 0.16, ease: 'back.out(2)', immediateRender: false }, tR);
  tl.fromTo(ring2, { scale: 1, opacity: 0.8 }, { scale: 1.65, opacity: 0, duration: 0.45, ease: 'power2.out', immediateRender: false }, tR + 0.04);
  tl.to(ring, { scale: 1.18, opacity: 0, duration: 0.18, ease: 'power2.in' }, tR1);
  ctx.updaters.push((t) => {
    if (t < tR - 0.05 || t > tR1 + 0.3) return;
    const f = ctx.frameAt(t);
    const [x, y] = ctx.anchor(handAt(ctx.hands.fist, f.ts), t);
    gsap.set([ring, ring2], { x, y });
  });

  // ---------------------------------------------------------------- frost + ice crack on "icy"
  const frost = new Frost(stage, W, ctx.H);
  const tClear = ctx.srcLen + 0.05;
  ctx.updaters.push((t) => frost.draw(ctx.frameAt(t).frost, t, clamp((t - tClear) / 0.45, 0, 1)));
  const tC = O(C.crack.at);
  const [kx, ky] = ctx.anchor(handAt(ctx.hands.fist, C.crack.at), tC);
  const crack = buildCrack(stage, W, ctx.H, kx, clamp(ky, 900, 1500));
  crack.paths.forEach((p) => {
    tl.fromTo(p.el, { strokeDashoffset: p.len }, { strokeDashoffset: 0, duration: 0.16 + p.len / 5000, ease: 'power2.out', immediateRender: false }, tC + p.delay);
  });
  gsap.set(crack.ring, { scale: 0, transformOrigin: `${kx}px ${ky}px` });
  tl.to(crack.ring, { scale: 1, duration: 0.12, ease: 'back.out(2)' }, tC);
  const flash = el(stage, 'flash');
  gsap.set(flash, { x: kx, y: ky });
  tl.fromTo(flash, { opacity: 0.95, scale: 0.5 }, { opacity: 0, scale: 1.3, duration: 0.32, ease: 'power2.out', immediateRender: false }, tC);
  tl.to(crack.svg, { opacity: 0.55, duration: 0.6, ease: 'none' }, ctx.srcLen + 0.1);

  // ---------------------------------------------------------------- end card
  const end = el(stage, 'end', `<div class="lockup">${ICONS.mark('#fff')}<span>BREEZE</span></div><div class="eurl">thermalabs.io/challenge</div>`);
  gsap.set(end, { x: 0, y: 812 });
  const lock = end.querySelector('.lockup'), eurl = end.querySelector('.eurl');
  gsap.set([lock, eurl], { opacity: 0 });
  const tE = ctx.srcLen + C.endcard.logo;
  tl.fromTo(lock, { opacity: 0, scale: 0.9, filter: 'blur(12px)' }, { opacity: 1, scale: 1, filter: 'blur(0px)', duration: 0.45, ease: 'power3.out', immediateRender: false }, tE);
  tl.fromTo(eurl, { opacity: 0, y: 14 }, { opacity: 1, y: 0, duration: 0.35, ease: 'power2.out', immediateRender: false }, ctx.srcLen + C.endcard.url);
}
