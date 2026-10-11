// One function per beat of the video. Times/positions come from beats.json (cues), drawing from draw.js.
import {
  C, $stage, div, thing, svg, node, g, sketch, text, htmlText, tape, rnd,
  sun, openBook, scroll, mug, backpack, heart, sparkle, star, blob, checkMark, ship, castle, pyramid, temple,
  soccerBall, waxSeal, scissors, pencil, brush, spiral, littleClaude, bubbleShape,
} from './draw.js';

// ------------------------------------------------------------------ animation helpers
const rotOf = (el) => gsap.getProperty(el, 'rotation');

function pop(tl, el, t, { dur = 0.34, s = 0.3, ease = 'back.out(2.2)', spin = -12 } = {}) {
  const r = rotOf(el);
  tl.fromTo(el, { autoAlpha: 0, scale: s, rotation: r + spin },
    { autoAlpha: 1, scale: 1, rotation: r, duration: dur, ease, immediateRender: false }, t);
}

function slap(tl, el, t) {            // sticker slapped onto the frame: lands exactly at t
  const r = rotOf(el);
  tl.fromTo(el, { autoAlpha: 0, scale: 1.7, rotation: r + 9 },
    { autoAlpha: 1, scale: 1, rotation: r, duration: 0.14, ease: 'power3.in', immediateRender: false }, t - 0.14);
  tl.to(el, { scaleX: 1.07, scaleY: 0.93, duration: 0.05, yoyo: true, repeat: 1, ease: 'sine.inOut' }, t);
}

function slideIn(tl, el, t, { x = 0, y = 0, dur = 0.32, ease = 'back.out(1.5)', spin = 0 } = {}) {
  const r = rotOf(el);
  tl.fromTo(el, { autoAlpha: 0, x, y, rotation: r + spin },
    { autoAlpha: 1, x: 0, y: 0, rotation: r, duration: dur, ease, immediateRender: false }, t);
}

function out(tl, el, t, { dur = 0.24, x = 0, y = 0, s = 0.85, rot = 0 } = {}) {
  tl.to(el, { autoAlpha: 0, scale: s, x: `+=${x}`, y: `+=${y}`, rotation: `+=${rot}`, duration: dur, ease: 'power2.in' }, t);
}

function drawOn(tl, root, t, dur) {   // DrawSVG every stroke under root
  const paths = [...root.querySelectorAll('path')];
  gsap.set(paths, { drawSVG: '0%' });
  tl.to(paths, { drawSVG: '100%', duration: dur, ease: 'none', stagger: 0 }, t);
}

function reveal(tl, el, t, dur) {     // handwriting reveal, left to right
  tl.fromTo(el, { clipPath: 'inset(-20% 100% -20% 0%)' },
    { clipPath: 'inset(-20% 0% -20% 0%)', duration: dur, ease: 'none', immediateRender: true }, t);
}

function typeOn(tl, el, str, t0, t1) {
  el.textContent = '';
  const chars = [...str].map((c) => {
    const s = document.createElement('span');
    s.className = 'ch';
    s.style.opacity = '0';
    s.textContent = c;
    el.appendChild(s);
    return s;
  });
  tl.to(chars, { opacity: 1, duration: 0.001, ease: 'none', stagger: (t1 - t0) / chars.length }, t0);
  return chars;
}

function wobble(tl, el, t0, t1, { amp = 3, period = 0.5, prop = 'rotation', vars = {} } = {}) {
  const half = period / 2;
  const n = Math.max(1, Math.floor((t1 - t0) / half));
  tl.to(el, { [prop]: `+=${amp}`, duration: half, yoyo: true, repeat: n - 1, ease: 'sine.inOut', ...vars }, t0);
}

function bob(tl, el, t0, t1, { amp = 7, period = 0.9 } = {}) { wobble(tl, el, t0, t1, { amp, period, prop: 'y' }); }

const full = (z, cls = '') => div('full ' + cls, $stage(), { zIndex: z });

// ------------------------------------------------------------------ 0 · title
function title(tl, c) {
  const wrap = full(40);
  gsap.set(wrap, { perspective: 2400 });
  const cover = div('full kraft', wrap, { backgroundColor: '#D7BF96', transformOrigin: '0% 50%' });
  div('', cover, { position: 'absolute', left: '0', top: '0', width: '70px', height: '1920px', background: 'rgba(92,60,38,.55)' });
  div('', cover, { position: 'absolute', right: '120px', top: '0', width: '30px', height: '1920px', background: '#4A3B33' });
  const lab = div('paper', cover, { position: 'absolute', left: '160px', top: '620px', width: '760px', height: '600px', borderRadius: '28px',
    boxShadow: '0 8px 0 rgba(58,42,34,.2)' });
  const s = svg(lab, 760, 600);
  sketch(s, 'rectangle', [22, 22, 716, 556], { strokeWidth: 3.5 });
  sketch(s, 'rectangle', [36, 36, 688, 528], { strokeWidth: 2, roughness: 1.8 });
  sun(s, 380, 118, 36);
  openBook(s, 380, 196, 230, 74);
  text(s, 'MORNING', { x: 380, y: 318, size: 124, font: 'Caveat Brush', weight: 400 });
  text(s, 'PAGES', { x: 380, y: 422, size: 124, font: 'Caveat Brush', weight: 400, fill: C.terracotta });
  text(s, 'by Mo', { x: 380, y: 508, size: 66, font: 'Caveat', weight: 700 });
  const s2 = svg(cover, 1080, 1920, { position: 'absolute', left: '0', top: '0' });
  sketch(s2, 'circle', [800, 1480, 250], { stroke: 'rgba(110,70,40,.32)', strokeWidth: 10, roughness: 2.4 });
  sketch(s2, 'circle', [806, 1486, 236], { stroke: 'rgba(110,70,40,.18)', strokeWidth: 5, roughness: 2.8 });
  tape(cover, { x: 250, y: 620, rot: -14, w: 170 });
  tape(cover, { x: 830, y: 1222, rot: -10, w: 170, cls: 'sage' });
  gsap.set(cover, { transformPerspective: 2400, filter: 'brightness(1)' });
  const d = c.flip[1] - c.flip[0];
  tl.to(cover, { rotationY: -100, duration: d, ease: 'power2.in' }, c.flip[0]);
  tl.to(cover, { filter: 'brightness(0.55)', duration: d, ease: 'power2.in' }, c.flip[0]);
  tl.set(wrap, { autoAlpha: 0 }, c.flip[1]);

  // header label that "stays behind" once the cover opens
  const hdr = thing({ x: 540, y: c.y, w: 640, h: 200, rot: -3, z: 12, cls: 'shadow' });
  const hl = div('paper', hdr, { position: 'absolute', inset: '0', borderRadius: '18px' });
  const hs = svg(hl, 640, 200);
  sketch(hs, 'rectangle', [12, 12, 616, 176], { strokeWidth: 3 });
  sun(hs, 82, 100, 26, { sw: 3 });
  text(hs, 'MORNING PAGES', { x: 360, y: 84, size: 86, font: 'Caveat Brush', weight: 400 });
  text(hs, 'by Mo', { x: 360, y: 152, size: 52, font: 'Caveat', weight: 700, fill: C.terracotta });
  tape(hdr, { x: 40, y: 8, rot: -28, w: 120 });
  tape(hdr, { x: 600, y: 10, rot: 24, w: 120 });
  pop(tl, hdr, c.flip[1] - 0.1, { s: 0.6, spin: -6 });

  const hook = thing({ x: 540, y: c.y + 168, w: 860, h: 100, rot: 1.6, z: 12, cls: 'shadow' });
  const hk = div('paper torn', hook, { position: 'absolute', inset: '0', backgroundColor: '#EEF0DC' });
  const ht = htmlText(hk, c.hook, { left: '0', right: '0', top: '16px', textAlign: 'center', font: '700 56px Caveat', color: C.ink });
  tl.set(hook, { autoAlpha: 1 }, c.hook_in);
  reveal(tl, ht, c.hook_in, 0.55);
  out(tl, hdr, c.out, { y: -50 });
  out(tl, hook, c.out + 0.04, { y: -40 });
}

// ------------------------------------------------------------------ 1 · hello + pennant
function hello(tl, c) {
  const el = thing({ x: c.x, y: c.y, w: 320, h: 230, rot: c.rot, z: 14, cls: 'shadow' });
  const card = div('', el, { position: 'absolute', inset: '0', borderRadius: '24px', background: '#FBF7EE', overflow: 'hidden', border: `5px solid ${C.ink}` });
  div('', card, { position: 'absolute', left: '0', right: '0', top: '0', height: '96px', background: C.terracotta });
  htmlText(card, 'HELLO', { left: '0', right: '0', top: '-2px', textAlign: 'center', font: '700 56px Kalam', color: '#FBF7EE', letterSpacing: '5px' });
  htmlText(card, 'my name is', { left: '0', right: '0', top: '56px', textAlign: 'center', font: '700 26px Kalam', color: '#FBF7EE' });
  htmlText(card, c.name, { left: '0', right: '0', top: '96px', textAlign: 'center', font: "400 92px 'Permanent Marker'", color: C.ink });
  slap(tl, el, c.in);
  wobble(tl, el, c.in + 0.3, c.out - 0.2, { amp: 2.5, period: 1.2 });
  out(tl, el, c.out, { x: -80, rot: -10 });
}

function pennant(tl, c) {
  const el = thing({ x: c.x, y: c.y, w: 330, h: 230, rot: c.rot, z: 14, cls: 'boil shadow' });
  const s = svg(el, 330, 230);
  sketch(s, 'line', [32, 8, 32, 222], { stroke: '#7A5236', strokeWidth: 10 });
  const flag = g(s);
  sketch(flag, 'polygon', [[[36, 22], [314, 76], [36, 132]]], { fill: C.pennNavy, fillStyle: 'solid', strokeWidth: 4 });
  sketch(flag, 'polygon', [[[36, 22], [86, 32], [86, 122], [36, 132]]], { fill: C.pennRed, fillStyle: 'solid', strokeWidth: 3 });
  text(flag, c.text, { x: 180, y: 80, size: 58, font: 'Permanent Marker', weight: 400, fill: '#FBF7EE', rot: 10 });
  text(s, c.note, { x: 196, y: 186, size: 50, font: 'Caveat', fill: C.ink, rot: -5 });
  sketch(s, 'path', ['M104,206 Q78,214 52,202'], { strokeWidth: 3 });
  pop(tl, el, c.in, { s: 0.2, spin: 20 });
  tl.to(flag, { skewY: 5, duration: 0.22, yoyo: true, repeat: 11, ease: 'sine.inOut', svgOrigin: '36 77' }, c.in + 0.3);
  out(tl, el, c.out, { x: 80, rot: 12 });
}

// ------------------------------------------------------------------ 2 · chapter strip
function chapter(tl, c) {
  const el = thing({ x: 540, y: c.y, w: 880, h: 124, rot: -2, z: 12, cls: 'shadow' });
  const strip = div('paper torn', el, { position: 'absolute', inset: '0' });
  const t = htmlText(strip, c.text, { left: '0', right: '0', top: '20px', textAlign: 'center', font: '700 68px Caveat', color: C.ink });
  tape(el, { x: 60, y: 6, rot: -20 });
  slideIn(tl, el, c.in - 0.18, { y: -40, dur: 0.22, ease: 'power2.out' });
  reveal(tl, t, c.in, c.write);
  out(tl, el, c.out, { y: -40 });
}

// ------------------------------------------------------------------ 3 · flashback photo + label + textbook
function photo(tl, c) {
  const el = full(5);
  gsap.set(el, { autoAlpha: 0 });
  div('full', el, { boxSizing: 'border-box', border: '30px solid #EFE6D4',
    boxShadow: 'inset 0 0 0 3px rgba(58,42,34,.25), inset 0 0 90px rgba(40,25,10,.55)' });
  const s = svg(el, 1080, 1920, { position: 'absolute', left: '0', top: '0' });
  const k = 78;
  for (const [x, y, sx, sy] of [[30, 30, 1, 1], [1050, 30, -1, 1], [30, 1890, 1, -1], [1050, 1890, -1, -1]]) {
    node(s, 'path', { d: `M${x},${y} L${x + sx * k},${y} L${x},${y + sy * k} Z`, fill: '#2B2420' });
  }
  div('full', el, { backgroundImage: 'url(img/creases.png)', backgroundSize: '1080px 1920px', opacity: '.9' });
  div('full dust a', el, { backgroundImage: 'url(img/dust_a.png)' });
  div('full dust b', el, { backgroundImage: 'url(img/dust_b.png)' });
  tl.fromTo(el, { autoAlpha: 0, scale: 1.08 }, { autoAlpha: 1, scale: 1, duration: 0.5, ease: 'power2.out', immediateRender: false }, c.in);
  tl.to(el, { autoAlpha: 0, scale: 1.14, rotation: 3, duration: 0.32, ease: 'power2.in' }, c.out - 0.32);
}

function flashLabel(tl, c) {
  const el = thing({ x: 540, y: c.y, w: 440, h: 100, rot: 2, z: 13, cls: 'shadow' });
  const lab = div('kraft', el, { position: 'absolute', inset: '0', borderRadius: '6px' });
  const t = htmlText(lab, '', { left: '0', right: '0', top: '22px', textAlign: 'center', font: "400 58px 'Special Elite'", color: C.ink });
  slideIn(tl, el, c.in - 0.12, { y: -24, dur: 0.18, ease: 'power2.out' });
  typeOn(tl, t, c.text, c.in, c.in + 0.62);
  out(tl, el, c.out, { y: -30 });
}

function textbook(tl, c) {
  const el = thing({ x: c.x, y: c.y, w: 310, h: 270, rot: -8, z: 14, cls: 'boil shadow' });
  const s = svg(el, 310, 270);
  sketch(s, 'rectangle', [40, 76, 212, 150], { fill: C.blue, fillStyle: 'solid', strokeWidth: 4 });
  sketch(s, 'rectangle', [252, 84, 18, 136], { fill: C.paper, fillStyle: 'solid', strokeWidth: 3 });
  sketch(s, 'line', [64, 76, 64, 226], { strokeWidth: 3 });
  text(s, 'HISTORY', { x: 158, y: 138, size: 40, font: 'Special Elite', weight: 400, fill: '#F4ECDC' });
  text(s, 'vol. 1', { x: 158, y: 184, size: 26, font: 'Special Elite', weight: 400, fill: '#F4ECDC' });
  const z = g(s);
  ['z', 'z', 'Z'].forEach((ch, i) => text(z, ch, { x: 204 + i * 28, y: 54 - i * 22, size: 34 + i * 12, font: 'Caveat', fill: C.inkSoft }));
  const x = g(s);
  sketch(x, 'line', [26, 62, 284, 238], { stroke: C.redpen, strokeWidth: 11, roughness: 1.4 });
  sketch(x, 'line', [284, 62, 26, 238], { stroke: C.redpen, strokeWidth: 11, roughness: 1.4 });
  slap(tl, el, c.in);
  tl.fromTo(z, { y: 12, opacity: 0 }, { y: -10, opacity: 1, duration: 0.7, ease: 'sine.out', immediateRender: false }, c.in + 0.05);
  drawOn(tl, x, c.cross, 0.24);
  out(tl, el, c.out, { x: -140, rot: -15 });
}

// ------------------------------------------------------------------ 4/5 · flashcards → crumple → toss
function indexCard(parent, w, h, title, body) {
  const card = div('paper', parent, { position: 'absolute', inset: '0', borderRadius: '6px' });
  const s = svg(card, w, h);
  node(s, 'line', { x1: 0, y1: 64, x2: w, y2: 64, stroke: 'rgba(192,57,43,.55)', 'stroke-width': 2.5 });
  for (let y = 100; y < h - 8; y += 34) node(s, 'line', { x1: 0, y1: y, x2: w, y2: y, stroke: 'rgba(93,122,153,.35)', 'stroke-width': 2 });
  htmlText(card, title, { left: '0', right: '0', top: '12px', textAlign: 'center', font: "400 46px 'Special Elite'", color: C.ink });
  if (body) htmlText(card, body, { left: '18px', right: '18px', top: '78px', textAlign: 'center', font: '700 36px Caveat', color: C.inkSoft, whiteSpace: 'normal', lineHeight: '34px' });
  return { card, s };
}

function flashcards(tl, c) {
  const cards = c.cards.map((k) => {
    const el = thing({ x: k.x, y: k.y, w: 340, h: 230, rot: k.rot, z: 14, cls: 'shadow' });
    const { s } = indexCard(el, 340, 230, k.title, k.body);
    slap(tl, el, k.t);
    return { el, s, k };
  });
  const stamp = thing({ x: 540, y: 600, w: 720, h: 160, rot: -8, z: 16 });
  const ss = svg(stamp, 720, 160);
  sketch(ss, 'rectangle', [12, 12, 696, 136], { stroke: C.redpen, strokeWidth: 9, roughness: 2.2 });
  text(ss, 'MEMORIZE!!', { x: 360, y: 84, size: 104, font: 'Permanent Marker', weight: 400, fill: C.redpen });
  tl.fromTo(stamp, { autoAlpha: 0, scale: 1.9 }, { autoAlpha: 0.94, scale: 1, duration: 0.12, ease: 'power4.in', immediateRender: false }, c.memorize - 0.12);
  cards.forEach(({ el }, i) => tl.to(el, { x: i % 2 ? '+=7' : '-=7', duration: 0.04, yoyo: true, repeat: 3, ease: 'none' }, c.memorize));

  // the pile gets tired of you
  const all = [...cards.map((o) => o.el), stamp];
  all.forEach((el, i) => wobble(tl, el, c.wobble, c.face + 0.45, { amp: i % 2 ? 5 : -5, period: 0.34 }));
  const mid = cards[1].s;
  const face = g(mid);
  sketch(face, 'line', [118, 150, 150, 150], { strokeWidth: 6 });
  sketch(face, 'line', [190, 150, 222, 150], { strokeWidth: 6 });
  sketch(face, 'line', [146, 192, 196, 190], { strokeWidth: 6 });
  drawOn(tl, face, c.face, 0.3);

  // gather → crumple into a ball → toss off frame
  all.forEach((el) => {
    tl.to(el, { left: 540 - parseFloat(el.style.width) / 2, top: 520 - parseFloat(el.style.height) / 2, scale: 0.45, rotation: `+=${(rnd() - 0.5) * 60}`,
      duration: 0.42, ease: 'power2.in' }, c.crumple - 0.42);
    tl.set(el, { autoAlpha: 0 }, c.crumple);
  });
  const ball = thing({ x: 540, y: 520, w: 200, h: 200, z: 15, cls: 'boil shadow' });
  const bs = svg(ball, 200, 200);
  sketch(bs, 'circle', [100, 100, 160], { fill: C.paper, fillStyle: 'solid', strokeWidth: 4, roughness: 2.2 });
  for (let i = 0; i < 7; i++) {
    const a = rnd() * 6.28, r1 = 14 + rnd() * 30, r2 = 40 + rnd() * 30;
    sketch(bs, 'linearPath', [[[100 + Math.cos(a) * r1, 100 + Math.sin(a) * r1], [100 + Math.cos(a + 0.5) * (r1 + r2) / 2, 100 + Math.sin(a + 0.5) * (r1 + r2) / 2],
      [100 + Math.cos(a + 0.2) * r2, 100 + Math.sin(a + 0.2) * r2]]], { strokeWidth: 2.5, stroke: C.inkSoft });
  }
  pop(tl, ball, c.crumple, { s: 0.5, dur: 0.22 });
  tl.to(ball, { x: 640, y: -260, rotation: 520, scale: 0.7, duration: c.out - c.toss, ease: 'power1.in' }, c.toss);
  tl.set(ball, { autoAlpha: 0 }, c.out);
}

// ------------------------------------------------------------------ 6 · broken bridge (and 10 · fixed bridge)
function bankLeft(tl, c, t) {
  const el = thing({ x: c.left[0], y: c.left[1], w: 300, h: 270, rot: -4, z: 14, cls: 'boil shadow' });
  const s = svg(el, 300, 270);
  scroll(s, 30, 10, 240, 186);
  text(s, c.left_label, { x: 150, y: 238, size: 62, font: 'Caveat', fill: C.ink });
  pop(tl, el, t, { s: 0.4 });
  return el;
}

function bankRight(tl, c, t) {
  const el = thing({ x: c.right[0], y: c.right[1], w: 320, h: 270, rot: 4, z: 14, cls: 'boil shadow' });
  const s = svg(el, 320, 270);
  const m = mug(s, 22, 30, 1.22);
  backpack(s, 190, 44, 1.1);
  text(s, c.right_label, { x: 160, y: 238, size: 60, font: 'Caveat', fill: C.ink });
  pop(tl, el, t, { s: 0.4 });
  return { el, steam: m.steam };
}

function bridgeBroken(tl, c) {
  const L = bankLeft(tl, c, c.in);
  const R = bankRight(tl, c, c.in + 0.14);
  const br = thing({ x: 540, y: 500, w: 420, h: 160, z: 13 });
  const s = svg(br, 420, 160);
  const halfA = g(s), halfB = g(s);
  const dash = { fill: 'none', stroke: C.ink, 'stroke-width': 7, 'stroke-dasharray': '18 14', 'stroke-linecap': 'round' };
  node(halfA, 'path', { d: 'M20,120 Q110,40 210,52', ...dash });
  node(halfB, 'path', { d: 'M210,52 Q310,40 400,120', ...dash });
  tl.set(br, { autoAlpha: 1 }, c.draw[0]);
  reveal(tl, s, c.draw[0], c.draw[1] - c.draw[0]);
  const crack = g(s);
  sketch(crack, 'linearPath', [[[200, 20], [214, 44], [198, 58], [216, 84]]], { stroke: C.terracotta, strokeWidth: 5 });
  gsap.set(crack, { opacity: 0 });
  tl.to(halfA, { rotation: 24, svgOrigin: '20 120', duration: 0.32, ease: 'bounce.out' }, c.snap);
  tl.to(halfB, { rotation: -24, svgOrigin: '400 120', duration: 0.32, ease: 'bounce.out' }, c.snap);
  tl.fromTo(crack, { opacity: 1 }, { opacity: 0, duration: 0.4, immediateRender: false }, c.snap);
  const q = thing({ x: 540, y: 470, w: 140, h: 170, z: 15, cls: 'boil' });
  const qs = svg(q, 140, 170);
  text(qs, '?', { x: 70, y: 92, size: 150, font: 'Permanent Marker', weight: 400, fill: C.terracotta });
  pop(tl, q, c.question, { s: 0.2, spin: 25 });
  wobble(tl, q, c.question + 0.3, c.out, { amp: 8, period: 0.4 });
  [L, R.el, br, q].forEach((el, i) => out(tl, el, c.out - 0.24 + i * 0.03, { y: 30 }));
}

function bridgeFixed(tl, c, cb, seal) {
  const k = { ...cb, left: cb.left, right: cb.right };
  const L = bankLeft(tl, k, c.in);
  const R = bankRight(tl, k, c.in + 0.14);
  const br = thing({ x: 540, y: 500, w: 420, h: 160, z: 13 });
  const s = svg(br, 420, 160);
  sketch(s, 'path', ['M20,120 Q210,-6 400,120'], { stroke: C.sage, strokeWidth: 12, roughness: 0.9 });
  sketch(s, 'path', ['M20,132 Q210,8 400,132'], { stroke: C.ink, strokeWidth: 4, roughness: 1.2 });
  for (let i = 1; i < 9; i++) {
    const x = 20 + i * 42, y = 120 - Math.sin((i / 9) * Math.PI) * 64;
    sketch(s, 'line', [x, y - 8, x, y + 14], { strokeWidth: 3.5 });
  }
  tl.set(br, { autoAlpha: 1 }, c.draw[0]);
  reveal(tl, s, c.draw[0], c.draw[1] - c.draw[0]);
  tl.to(seal, { scale: 0.5, y: -16, duration: 0.35, ease: 'power2.inOut' }, c.in);
  const ok = thing({ x: 540, y: 362, w: 380, h: 90, rot: -3, z: 15 });
  const os = svg(ok, 380, 90);
  checkMark(os, 34, 44, 0.8, { stroke: C.sage, sw: 8 });
  text(os, 'connected!', { x: 220, y: 46, size: 64, font: 'Caveat', fill: C.ink });
  pop(tl, ok, c.check, { s: 0.4 });
  [L, R.el, br, ok, seal].forEach((el, i) => out(tl, el, c.out - 0.24 + i * 0.03, { y: -30 }));
}

// ------------------------------------------------------------------ 7 · home + dad
function house(tl, c) {
  const el = thing({ x: c.x, y: c.y, w: 300, h: 320, rot: -4, z: 14, cls: 'boil shadow' });
  const s = svg(el, 300, 320);
  const glow = node(s, 'circle', { cx: 182, cy: 218, r: 62, fill: 'rgba(233,180,76,.6)', filter: 'url(#softglow)' });
  sketch(s, 'rectangle', [196, 72, 36, 74], { fill: C.terracotta, fillStyle: 'hachure', hachureGap: 6, strokeWidth: 3.5 });
  sketch(s, 'polygon', [[[30, 158], [150, 60], [272, 158]]], { fill: C.terracotta, fillStyle: 'solid', strokeWidth: 4 });
  sketch(s, 'rectangle', [54, 156, 194, 146], { fill: C.paper, fillStyle: 'solid', strokeWidth: 4 });
  sketch(s, 'rectangle', [82, 218, 52, 84], { fill: C.sage, fillStyle: 'solid', strokeWidth: 3.5 });
  sketch(s, 'circle', [124, 262, 8], { fill: C.ink, fillStyle: 'solid', strokeWidth: 1 });
  sketch(s, 'rectangle', [156, 190, 56, 54], { fill: C.mustard, fillStyle: 'solid', strokeWidth: 3.5 });
  sketch(s, 'line', [184, 190, 184, 244], { strokeWidth: 3 });
  sketch(s, 'line', [156, 217, 212, 217], { strokeWidth: 3 });
  const smoke = g(s);
  [[214, 50, 28], [226, 22, 36], [214, -12, 44]].forEach(([x, y, d]) => sketch(smoke, 'circle', [x, y, d], { stroke: C.inkSoft, strokeWidth: 3, roughness: 1.8 }));
  pop(tl, el, c.in, { s: 0.3 });
  tl.fromTo(smoke, { y: 12, opacity: 0 }, { y: -12, opacity: 1, duration: 1.0, repeat: 2, ease: 'sine.inOut', immediateRender: false }, c.in + 0.15);
  tl.to(glow, { attr: { r: 76 }, duration: 0.5, yoyo: true, repeat: 5, ease: 'sine.inOut' }, c.in + 0.2);
  out(tl, el, c.out, { y: 40 });
}

function dad(tl, c) {
  const el = thing({ x: c.x, y: c.y, w: 300, h: 320, rot: 5, z: 14 });
  const art = div('boil', el, { position: 'absolute', inset: '0' });
  const s = svg(art, 300, 320);
  const gl = g(s);
  sketch(gl, 'circle', [108, 64, 74], { strokeWidth: 5 });
  sketch(gl, 'circle', [192, 64, 74], { strokeWidth: 5 });
  sketch(gl, 'path', ['M140,58 Q150,48 160,58'], { strokeWidth: 5 });
  sketch(gl, 'line', [70, 56, 44, 48], { strokeWidth: 5 });
  sketch(gl, 'line', [230, 56, 256, 48], { strokeWidth: 5 });
  [[C.blue, 236, 214], [C.sage, 262, 200], [C.terracotta, 288, 222]].forEach(([fill, y, w]) =>
    sketch(s, 'rectangle', [150 - w / 2, y, w, 26], { fill, fillStyle: 'solid', strokeWidth: 3.5 }));
  const tagEl = div('kraft shadow', el, { position: 'absolute', left: '44px', top: '112px', width: '214px', height: '110px',
    clipPath: 'polygon(16% 0, 100% 0, 100% 100%, 16% 100%, 0 50%)' });
  htmlText(tagEl, 'DAD', { left: '34px', right: '0', top: '4px', textAlign: 'center', font: "400 78px 'Permanent Marker'", color: C.ink });
  div('', tagEl, { position: 'absolute', left: '22px', top: '46px', width: '16px', height: '16px', borderRadius: '50%', background: '#2B2420' });
  pop(tl, el, c.in, { s: 0.3, spin: 14 });

  const orbit = div('', el, { position: 'absolute', left: '0', top: '0', width: '300px', height: '300px' });
  const items = [];
  const R = 150;
  const addIcon = (angle, draw, t) => {
    const holder = div('boil', orbit, { position: 'absolute', width: '70px', height: '70px',
      left: `${150 + Math.cos(angle) * R - 35}px`, top: `${160 + Math.sin(angle) * R - 35}px` });
    const is = svg(holder, 70, 70);
    draw(is);
    gsap.set(holder, { autoAlpha: 0 });
    pop(tl, holder, t, { s: 0.2, dur: 0.25 });
    items.push(holder);
  };
  addIcon(-2.4, (s2) => heart(s2, 35, 37, 24), c.hearts);
  addIcon(-0.5, (s2) => heart(s2, 35, 37, 20, { fill: C.redpen }), c.hearts + 0.14);
  addIcon(1.6, (s2) => heart(s2, 35, 37, 22, { fill: C.mustard }), c.hearts + 0.28);
  addIcon(0.55, (s2) => star(s2, 35, 35, 26), c.hearts + 0.4);
  addIcon(2.65, (s2) => scroll(s2, 6, 8, 58, 54), c.hist);
  addIcon(-1.45, (s2) => { node(s2, 'path', { d: 'M6,62 L35,10 L64,62 Z', fill: C.mustard, stroke: C.ink, 'stroke-width': 4, 'stroke-linejoin': 'round' }); }, c.hist + 0.1);
  const spin = c.out - c.hearts;
  tl.to(orbit, { rotation: 140, duration: spin, ease: 'none' }, c.hearts);
  tl.to(items, { rotation: -140, duration: spin, ease: 'none' }, c.hearts);
  out(tl, el, c.out, { y: 40 });
}

// ------------------------------------------------------------------ 8 · pop-up storybook
function storybook(tl, c) {
  const W = 720, H = 420;
  const el = thing({ x: 540, y: c.y, w: W, h: H, z: 13, cls: 'boil shadow' });
  const s = svg(el, W, H);
  const stageG = g(s);
  const book = g(s);
  openBook(book, 360, 330, 600, 120, { lines: 3 });
  const drawers = { ship, castle, pyramid, temple };
  const scenes = c.scenes.map((sc) => {
    const holder = g(stageG);
    const res = drawers[sc.s](holder, 210, 40);
    gsap.set(holder, { scaleY: 0, svgOrigin: '360 286', opacity: 0 });
    return { holder, res, sc };
  });
  tl.fromTo(el, { autoAlpha: 0, scaleX: 0.15, scaleY: 0.6 }, { autoAlpha: 1, scaleX: 1, scaleY: 1, duration: 0.32, ease: 'back.out(1.6)', immediateRender: false }, c.in);
  scenes.forEach(({ holder, res, sc }, i) => {
    tl.to(holder, { scaleY: 1, opacity: 1, duration: 0.28, ease: 'back.out(2.4)' }, sc.t);
    if (res && res.waves) tl.to(res.waves, { x: 14, duration: 0.35, yoyo: true, repeat: 3, ease: 'sine.inOut' }, sc.t + 0.1);
    const next = scenes[i + 1];
    if (next) tl.to(holder, { scaleY: 0, opacity: 0, duration: 0.16, ease: 'power2.in' }, next.sc.t - 0.12);
  });
  tl.to(el, { autoAlpha: 0, scaleX: 0.2, duration: 0.24, ease: 'power2.in' }, c.out - 0.24);
}

// ------------------------------------------------------------------ 9 · checklist + snipped fine print
function checklist(tl, c) {
  const el = thing({ x: c.x, y: c.y, w: 330, h: 330, rot: -3, z: 14, cls: 'shadow' });
  const pad = div('paper', el, { position: 'absolute', inset: '0', borderRadius: '8px' });
  const s = svg(pad, 330, 330);
  for (let i = 0; i < 6; i++) sketch(s, 'circle', [40 + i * 50, 14, 22], { strokeWidth: 3.5, fill: '#E8E1D2', fillStyle: 'solid' });
  c.items.forEach((it, i) => {
    const y = 92 + i * 84;
    sketch(s, 'rectangle', [28, y - 26, 52, 52], { strokeWidth: 4 });
    text(s, it.text, { x: 104, y: y + 2, size: 64, font: 'Caveat', anchor: 'start' });
    const ck = g(s);
    checkMark(ck, 36, y - 2, 0.9, { stroke: C.terracotta, sw: 8 });
    drawOn(tl, ck, it.t, 0.2);
  });
  pop(tl, el, c.in, { s: 0.4 });
  out(tl, el, c.out, { x: -60 });
}

function fineprint(tl, c) {
  const W = 210, H = 440, cut = 230;
  const mk = (top, h) => {
    const el = thing({ x: c.x, y: c.y - H / 2 + top + h / 2, w: W, h, z: 14, cls: 'shadow' });
    const strip = div('paper', el, { position: 'absolute', inset: '0', overflow: 'hidden' });
    const inner = div('', strip, { position: 'absolute', left: '0', top: `${-top}px`, width: `${W}px`, height: `${H}px` });
    const lines = ['the boring', 'details:', '§ 4.2(b)…', 'footnote 47', 'see appendix', 'subsection ix', 'blah blah', 'blah blah blah', 'ibid., p. 381', '(also blah)'];
    lines.forEach((ln, i) => htmlText(inner, ln, { left: '16px', top: `${18 + i * 40}px`, font: '700 32px Caveat', color: i < 2 ? C.ink : '#8C7B6B' }));
    return el;
  };
  const topPart = mk(0, cut);
  const botPart = mk(cut, H - cut);
  const roller = thing({ x: c.x, y: c.y - H / 2 - 8, w: W + 40, h: 34, z: 15 });
  div('kraft', roller, { position: 'absolute', inset: '0', borderRadius: '17px', border: `4px solid ${C.ink}` });
  pop(tl, roller, c.in - 0.1, { s: 0.5, dur: 0.2 });
  tl.set([topPart, botPart], { autoAlpha: 1 }, c.in);
  tl.fromTo(topPart, { clipPath: 'inset(0 0 100% 0)' }, { clipPath: 'inset(0 0 0% 0)', duration: 0.25, ease: 'none', immediateRender: true }, c.in);
  tl.fromTo(botPart, { clipPath: 'inset(0 0 100% 0)' }, { clipPath: 'inset(0 0 0% 0)', duration: 0.25, ease: 'none', immediateRender: true }, c.in + 0.25);
  const sc = thing({ x: c.x + 190, y: c.y - H / 2 + cut, w: 260, h: 120, z: 16 });
  const ss = svg(sc, 260, 120);
  const sz = scissors(ss, 120, 60, 1);
  gsap.set(sz.top, { rotation: -18, svgOrigin: '120 60' });
  gsap.set(sz.bot, { rotation: 18, svgOrigin: '120 60' });
  slideIn(tl, sc, c.snip - 0.24, { x: 160, dur: 0.22, ease: 'power2.out' });
  tl.to([sz.top, sz.bot], { rotation: 0, svgOrigin: '120 60', duration: 0.07, ease: 'power3.in' }, c.snip - 0.04);
  tl.to(botPart, { y: 520, rotation: 26, duration: 0.6, ease: 'power2.in' }, c.snip + 0.05);
  tl.set(botPart, { autoAlpha: 0 }, c.snip + 0.65);
  out(tl, sc, c.snip + 0.3, { x: 120 });
  out(tl, topPart, c.out, { y: -30 });
  out(tl, roller, c.out, { y: -30 });
}

// ------------------------------------------------------------------ 10 · the lesson seal
function seal(tl, c) {
  const el = thing({ x: 540, y: c.y, w: 300, h: 300, rot: -6, z: 16, cls: 'shadow' });
  const s = svg(el, 300, 300);
  waxSeal(s, 150, 150, 118);
  tl.fromTo(el, { autoAlpha: 0, scale: 2.4, y: -90, rotation: -30 }, { autoAlpha: 1, scale: 1, y: 0, rotation: -6, duration: 0.14, ease: 'power4.in', immediateRender: false }, c.t - 0.14);
  tl.to(el, { scaleX: 1.08, scaleY: 0.9, duration: 0.06, yoyo: true, repeat: 1, ease: 'sine.inOut' }, c.t);
  const puff = thing({ x: 540, y: c.y, w: 420, h: 420, z: 15 });
  const ps = svg(puff, 420, 420);
  for (let i = 0; i < 10; i++) {
    const a = (i / 10) * Math.PI * 2;
    sketch(ps, 'line', [210 + Math.cos(a) * 150, 210 + Math.sin(a) * 150, 210 + Math.cos(a) * 196, 210 + Math.sin(a) * 196], { strokeWidth: 5, stroke: C.inkSoft });
  }
  tl.fromTo(puff, { autoAlpha: 0.9, scale: 0.7 }, { autoAlpha: 0, scale: 1.15, duration: 0.4, ease: 'power2.out', immediateRender: false }, c.t);
  return el;
}

// ------------------------------------------------------------------ 11 · sparkles around Mo
function sparkles(tl, c) {
  const spots = [[320, 720, 34], [770, 700, 40], [270, 940, 28], [820, 930, 34], [540, 640, 30], [210, 800, 24], [880, 790, 26], [330, 1160, 22], [770, 1170, 26]];
  spots.forEach(([x, y, r], i) => {
    const el = thing({ x, y, w: r * 2 + 20, h: r * 2 + 20, z: 14, cls: 'boil' });
    const s = svg(el, r * 2 + 20, r * 2 + 20);
    sparkle(s, r + 10, r + 10, r, { fill: i % 3 ? C.mustard : '#FBF7EE' });
    const t0 = c.in + i * 0.07;
    pop(tl, el, t0, { s: 0, dur: 0.3, spin: 45 });
    tl.to(el, { scale: 0.65, duration: 0.3, yoyo: true, repeat: 3, ease: 'sine.inOut' }, t0 + 0.32);
    out(tl, el, c.out - 0.2 + i * 0.01, { s: 0.2 });
  });
}

// ------------------------------------------------------------------ 12 · envelope "for you"
function envelope(tl, c) {
  const el = thing({ x: c.x, y: c.y, w: 290, h: 230, rot: -6, z: 14, cls: 'boil shadow' });
  const s = svg(el, 290, 230);
  const hrt = g(s);
  heart(hrt, 145, 96, 30, { fill: C.redpen });
  gsap.set(hrt, { opacity: 0 });
  sketch(s, 'rectangle', [20, 60, 250, 160], { fill: C.paper, fillStyle: 'solid', strokeWidth: 4 });
  sketch(s, 'linearPath', [[[20, 220], [145, 140], [270, 220]]], { strokeWidth: 3 });
  const flap = g(s);
  sketch(flap, 'polygon', [[[20, 60], [145, 146], [270, 60]]], { fill: C.paper2, fillStyle: 'solid', strokeWidth: 4 });
  sketch(flap, 'circle', [145, 132, 34], { fill: C.redpen, fillStyle: 'solid', strokeWidth: 3 });
  text(s, 'for you', { x: 145, y: 192, size: 46, font: 'Caveat', fill: C.ink });
  slideIn(tl, el, c.in, { x: 300, y: 160, dur: 0.38, spin: 30 });
  tl.to(flap, { scaleY: -1, svgOrigin: '145 60', duration: 0.2, ease: 'power2.inOut' }, c.open);
  tl.fromTo(hrt, { opacity: 1, y: 30, scale: 0.5, svgOrigin: '145 96' }, { y: -80, scale: 1.2, svgOrigin: '145 96', duration: 0.4, ease: 'back.out(2)', immediateRender: false }, c.open + 0.08);
  out(tl, el, c.out, { x: 80 });
}

// ------------------------------------------------------------------ 13 · tear-off calendar
function calendar(tl, c) {
  const W = 330, H = 350;
  const el = thing({ x: 540, y: c.y, w: W, h: H, rot: 2, z: 14, cls: 'shadow' });
  const mkPage = (label, big, sub) => {
    const p = div('paper', el, { position: 'absolute', left: '0', top: '44px', width: `${W}px`, height: `${H - 44}px`, borderRadius: '0 0 10px 10px',
      boxShadow: '0 3px 0 rgba(58,42,34,.18)' });
    htmlText(p, label, { left: '0', right: '0', top: '22px', textAlign: 'center', font: "400 40px 'Special Elite'", color: C.terracotta });
    htmlText(p, big, { left: '0', right: '0', top: '58px', textAlign: 'center', font: big.length > 2 ? '700 92px Caveat' : '700 150px Kalam', color: C.ink, lineHeight: '1.1' });
    if (sub) htmlText(p, sub, { left: '0', right: '0', top: '196px', textAlign: 'center', font: '700 58px Caveat', color: C.ink });
    return p;
  };
  mkPage('TODAY', '1 story', '☀️ every morning');
  const pages = ['3', '2', '1'].map((n) => mkPage('DAY', n));
  const bar = div('', el, { position: 'absolute', left: '-6px', top: '0', width: `${W + 12}px`, height: '56px', background: C.terracotta, borderRadius: '12px',
    border: `4px solid ${C.ink}` });
  [80, 250].forEach((x) => div('', bar, { position: 'absolute', left: `${x}px`, top: '-22px', width: '18px', height: '44px', borderRadius: '9px', background: '#8D8D8D', border: `3px solid ${C.ink}` }));
  pop(tl, el, c.in, { s: 0.4 });
  [...pages].reverse().forEach((p, i) => {
    const dir = i % 2 ? 1 : -1;
    tl.to(p, { y: -140, x: dir * 260, rotation: dir * 38, autoAlpha: 0, duration: 0.34, ease: 'power2.out' }, c.rips[i]);
  });
  tl.to(el, { scale: 1.07, duration: 0.12, yoyo: true, repeat: 1, ease: 'sine.inOut' }, c.today);
  const nw = thing({ x: 690, y: c.y - 150, w: 170, h: 170, rot: 14, z: 15 });
  const ns = svg(nw, 170, 170);
  star(ns, 85, 85, 80, { points: 12, inner: 0.74, fill: C.mustard });
  text(ns, 'new!', { x: 85, y: 88, size: 50, font: 'Permanent Marker', weight: 400, fill: C.ink });
  slap(tl, nw, c.new);
  out(tl, el, c.out, { y: -40 });
  out(tl, nw, c.out, { y: -40 });
}

// ------------------------------------------------------------------ 14 · simple / fun / engaging / VISUAL + doodle burst
function words(tl, c) {
  const els = [];
  c.items.forEach((it) => {
    if (it.style === 'rainbow') {
      const el = thing({ x: it.x, y: it.y, w: 700, h: 200, rot: -3, z: 16, cls: 'shadow' });
      const cols = [C.terracotta, C.mustard, C.sage, C.blue, C.claude, C.inkSoft];
      [...it.w].forEach((ch, i) => {
        const span = htmlText(el, ch, { left: `${40 + i * 106}px`, top: '0', font: "400 190px 'Caveat Brush'", color: cols[i % cols.length],
          textShadow: `4px 4px 0 ${C.ink}` });
        gsap.set(span, { autoAlpha: 0 });
        tl.fromTo(span, { autoAlpha: 0, y: 60, scale: 0.3 }, { autoAlpha: 1, y: 0, scale: 1, duration: 0.26, ease: 'back.out(2.6)', immediateRender: false }, it.t + i * 0.035);
      });
      tl.set(el, { autoAlpha: 1 }, it.t);
      els.push(el);
      return;
    }
    const el = thing({ x: it.x, y: it.y, w: 360, h: 150, rot: it.style === 'marker' ? 8 : -6, z: 15, cls: 'shadow' });
    const s = svg(el, 360, 150);
    if (it.style === 'box') {
      sketch(s, 'rectangle', [30, 22, 300, 106], { fill: '#E7EDD8', fillStyle: 'solid', stroke: C.sage, strokeWidth: 5 });
      text(s, it.w, { x: 180, y: 76, size: 80, font: 'Patrick Hand', weight: 400 });
    } else if (it.style === 'marker') {
      text(s, it.w, { x: 180, y: 78, size: 108, font: 'Permanent Marker', weight: 400, fill: C.terracotta, stroke: '#FBF7EE', sw: 10 });
      star(s, 30, 30, 18);
      star(s, 336, 118, 14, { fill: C.sage });
    } else {
      text(s, it.w, { x: 180, y: 78, size: 96, font: 'Caveat Brush', weight: 400, fill: C.blue, stroke: '#FBF7EE', sw: 10 });
      sketch(s, 'path', ['M40,128 Q180,150 320,124'], { stroke: C.blue, strokeWidth: 6 });
    }
    pop(tl, el, it.t, { s: 0.3 });
    els.push(el);
  });
  // margin burst at "visual"
  const burst = [
    [70, 330, 'blob', C.terracotta], [1010, 300, 'blob', C.mustard], [60, 1150, 'blob', C.sage], [1020, 1100, 'blob', C.blue],
    [140, 640, 'star', C.mustard], [950, 660, 'spiral', C.sage], [960, 470, 'star', C.claude], [120, 480, 'spiral', C.terracotta],
    [880, 1260, 'heart', C.redpen], [200, 1260, 'heart', C.mustard], [150, 960, 'pencil'], [920, 900, 'brush'],
  ];
  burst.forEach(([x, y, kind, col], i) => {
    const el = thing({ x, y, w: 200, h: 200, rot: (rnd() - 0.5) * 30, z: 13, cls: 'boil' });
    const s = svg(el, 200, 200);
    if (kind === 'blob') blob(s, 100, 100, 58, { fill: col });
    if (kind === 'star') star(s, 100, 100, 46, { fill: col });
    if (kind === 'spiral') spiral(s, 100, 100, 60, { stroke: col });
    if (kind === 'heart') heart(s, 100, 104, 40, { fill: col });
    if (kind === 'pencil') pencil(s, 30, 100, 110, -30);
    if (kind === 'brush') brush(s, 40, 120, 100, -150);
    pop(tl, el, c.burst + i * 0.03, { s: 0, dur: 0.26, spin: 40 });
    els.push(el);
  });
  els.forEach((el, i) => out(tl, el, c.out - 0.22 + (i % 6) * 0.015, { s: 0.3, dur: 0.18 }));
}

// ------------------------------------------------------------------ 15 · ★ little Claude cameo
function makeClaude(x, y, r, z = 20) {
  const W = r * 4.4, H = r * 4.4;
  const el = thing({ x, y, w: W, h: H, z, cls: 'boil' });
  const s = svg(el, W, H);
  const parts = littleClaude(s, W / 2, H / 2, r);
  return { el, parts, W, H };
}

function bubble(x, y, w, h, tail, z = 22) {
  const el = div('bubble', $stage(), { left: `${x - w / 2}px`, top: `${y - h / 2}px`, width: `${w}px`, height: `${h}px`, zIndex: z });
  const s = svg(el, w, h, { position: 'absolute', left: '0', top: '0', overflow: 'visible' });
  bubbleShape(s, w, h, tail[0], tail[1]);
  const txt = div('txt', el);
  gsap.set(el, { autoAlpha: 0, transformOrigin: `${tail[0]}px ${tail[1]}px` });
  el.classList.add('shadow');
  return { el, txt };
}

function claude(tl, c) {
  const { el, parts } = makeClaude(c.x, c.y, 84);
  const p = parts;
  const shoulder = `${el.offsetWidth / 2 + 77} ${el.offsetHeight / 2 + 8}`;
  gsap.set(p.armR, { svgOrigin: shoulder });
  // peek in from behind the left edge with a squashy bounce
  tl.fromTo(el, { autoAlpha: 1, x: -330, rotation: -25, scaleX: 1.2, scaleY: 0.85 },
    { x: 0, rotation: 0, scaleX: 1, scaleY: 1, duration: 0.3, ease: 'back.out(2.2)', immediateRender: false }, c.in);
  wobble(tl, p.armR, c.in + 0.3, c.bubble1[1], { amp: 28, period: 0.28, vars: { svgOrigin: shoulder } });
  // name tag
  const tag = thing({ x: c.x + 20, y: c.y + 200, w: 400, h: 104, rot: -3, z: 21, cls: 'shadow' });
  const tg = div('kraft', tag, { position: 'absolute', inset: '0', borderRadius: '10px' });
  htmlText(tg, c.tag, { left: '0', right: '0', top: '0px', textAlign: 'center', font: '700 48px Kalam', color: C.ink });
  htmlText(tg, c.tag_sub, { left: '0', right: '0', top: '54px', textAlign: 'center', font: '700 34px Caveat', color: C.inkSoft });
  pop(tl, tag, c.in + 0.18, { s: 0.5, dur: 0.26 });
  // bubble 1: "hi!! it's me, Claude 👋"
  const b1 = bubble(270, 505, 470, 196, [110, 400]);
  tl.fromTo(b1.el, { autoAlpha: 0, scale: 0.4 }, { autoAlpha: 1, scale: 1, duration: 0.18, ease: 'back.out(2)', immediateRender: false }, c.bubble1[0] - 0.06);
  typeOn(tl, b1.txt, c.text1, c.bubble1[0], c.bubble1[1] - 0.05);
  tl.to(b1.el, { autoAlpha: 0, scale: 0.85, duration: 0.08 }, c.bubble2[0] - 0.05);
  // bubble 2: "…am I doing a good job?" — nervous little head tilt
  const b2 = bubble(270, 505, 470, 196, [110, 400]);
  tl.fromTo(b2.el, { autoAlpha: 0, scale: 0.6 }, { autoAlpha: 1, scale: 1, duration: 0.14, ease: 'back.out(2)', immediateRender: false }, c.bubble2[0]);
  typeOn(tl, b2.txt, c.text2, c.bubble2[0] + 0.05, c.bubble2[1] - 0.15);
  tl.to(el, { rotation: 9, duration: 0.25, ease: 'sine.inOut' }, c.bubble2[0]);
  tl.set(p.happy, { opacity: 0 }, c.bubble2[0] + 0.1);
  tl.set(p.nervous, { opacity: 1 }, c.bubble2[0] + 0.1);
  tl.fromTo(p.sweat, { opacity: 0, y: -6 }, { opacity: 1, y: 4, duration: 0.3, ease: 'power1.in', immediateRender: false }, c.bubble2[0] + 0.15);
  const q = thing({ x: c.x + 150, y: c.y - 120, w: 90, h: 110, rot: 12, z: 21, cls: 'boil' });
  text(svg(q, 90, 110), '?', { x: 45, y: 60, size: 96, font: 'Permanent Marker', weight: 400, fill: C.terracotta });
  pop(tl, q, c.bubble2[0] + 0.6, { s: 0.2, spin: 30 });
  wobble(tl, q, c.bubble2[0] + 0.9, c.out - 0.3, { amp: 10, period: 0.36 });
  // shy happy face + heart, then duck out
  tl.set([p.eyes, p.nervous, p.sweat], { opacity: 0 }, c.thumbs);
  tl.set([p.shy, p.happy], { opacity: 1 }, c.thumbs);
  tl.to(el, { rotation: -4, duration: 0.18 }, c.thumbs);
  const h = thing({ x: c.x + 70, y: c.y - 140, w: 70, h: 70, z: 21, cls: 'boil' });
  heart(svg(h, 70, 70), 35, 37, 24, { fill: C.redpen });
  tl.fromTo(h, { autoAlpha: 1, y: 20, scale: 0.3 }, { y: -40, scale: 1, duration: 0.5, ease: 'back.out(2)', immediateRender: false }, c.thumbs);
  tl.to(b2.el, { autoAlpha: 0, scale: 0.85, duration: 0.12 }, c.thumbs + 0.05);
  tl.to(el, { x: -340, rotation: -30, scaleX: 1.15, scaleY: 0.85, duration: 0.3, ease: 'back.in(1.8)' }, c.out - 0.32);
  [tag, q, h].forEach((e) => out(tl, e, c.out - 0.3, { x: -60 }));
}

// ------------------------------------------------------------------ 16 · today's lesson card
function lessonCard(tl, c) {
  const W = 620, H = 290;
  const el = thing({ x: 540, y: c.y, w: W, h: H, rot: -2, z: 14, cls: 'shadow' });
  const card = div('paper', el, { position: 'absolute', inset: '0', borderRadius: '8px' });
  const s = svg(card, W, H);
  node(s, 'line', { x1: 0, y1: 84, x2: W, y2: 84, stroke: 'rgba(192,57,43,.55)', 'stroke-width': 3 });
  for (let y = 132; y < H; y += 46) node(s, 'line', { x1: 0, y1: y, x2: W, y2: y, stroke: 'rgba(93,122,153,.35)', 'stroke-width': 2 });
  htmlText(card, c.title, { left: '0', right: '0', top: '18px', textAlign: 'center', font: "400 56px 'Special Elite'", color: C.ink });
  sketch(s, 'line', [70, 168, 540, 166], { strokeWidth: 3, stroke: C.inkSoft, roughness: 1.4 });
  pencil(s, 470, 236, 100, -12);
  const note = htmlText(card, c.note_text, { left: '40px', top: '186px', font: '700 60px Caveat', color: C.terracotta });
  slideIn(tl, el, c.in, { y: -240, spin: -8, dur: 0.34 });
  const ws = thing({ x: 540 + W / 2 - 40, y: c.y - H / 2 + 26, w: 150, h: 150, rot: 12, z: 15, cls: 'shadow' });
  waxSeal(svg(ws, 150, 150), 75, 75, 58, { label: false });
  slap(tl, ws, c.seal);
  tl.set(note, { autoAlpha: 1 }, c.note);
  reveal(tl, note, c.note, 0.6);
  out(tl, el, c.out, { y: -40 });
  out(tl, ws, c.out, { y: -40 });
}

// ------------------------------------------------------------------ 17 · follow pill
function follow(tl, c) {
  const W = 820, H = 124;
  const el = thing({ x: 540, y: c.y, w: W, h: H, rot: -2, z: 14, cls: 'shadow' });
  const s = svg(el, W, H);
  sketch(s, 'path', [`M62,8 L${W - 62},8 Q${W - 6},8 ${W - 6},62 Q${W - 6},${H - 8} ${W - 62},${H - 8} L62,${H - 8} Q6,${H - 8} 6,62 Q6,8 62,8 Z`],
    { fill: '#F6E3B0', fillStyle: 'solid', strokeWidth: 4.5 });
  sun(s, 74, 62, 22, { sw: 3 });
  text(s, c.text, { x: W / 2 + 34, y: 64, size: 50, font: 'Kalam', weight: 700 });
  pop(tl, el, c.in, { s: 0.4 });
  bob(tl, el, c.in + 0.35, c.out - 0.2, { amp: 6, period: 0.8 });
  out(tl, el, c.out - 0.2, { y: -30 });
}

// ------------------------------------------------------------------ 18 · soccer ball + "(ignore this)"
function soccer(tl, c) {
  const el = thing({ x: c.x, y: c.y, w: 200, h: 200, z: 14, cls: 'boil shadow' });
  soccerBall(svg(el, 200, 200), 100, 100, 82);
  tl.fromTo(el, { autoAlpha: 1, x: 340, y: -260, rotation: 260 }, { x: 0, y: 0, rotation: 0, duration: c.bounces[0] - c.in, ease: 'power2.in', immediateRender: false }, c.in);
  c.bounces.forEach((b, i) => {
    tl.to(el, { scaleX: 1.16, scaleY: 0.82, duration: 0.05, yoyo: true, repeat: 1, ease: 'sine.inOut' }, b);
    const next = c.bounces[i + 1];
    if (next) {
      const half = (next - b) / 2;
      tl.to(el, { y: -150, rotation: `+=${90}`, duration: half, ease: 'power2.out' }, b + 0.05);
      tl.to(el, { y: 0, rotation: `+=${90}`, duration: half - 0.05, ease: 'power2.in' }, b + 0.05 + half);
    }
  });
  const hearts = [[-110, -90], [110, -110], [0, -150]].map(([dx, dy], i) => {
    const h = thing({ x: c.x + dx, y: c.y + dy, w: 70, h: 70, z: 15, cls: 'boil' });
    heart(svg(h, 70, 70), 35, 37, 22, { fill: i === 1 ? C.mustard : C.redpen });
    pop(tl, h, c.hearts + i * 0.08, { s: 0.2, dur: 0.24 });
    out(tl, h, c.sticky - 0.1, { s: 0.3 });
    return h;
  });
  const st = thing({ x: c.x - 20, y: c.y + 10, w: 330, h: 290, rot: 6, z: 16, cls: 'shadow' });
  const note = div('', st, { position: 'absolute', inset: '0', background: C.sticky, borderRadius: '2px 2px 18px 2px' });
  note.style.backgroundImage = 'url(img/paper.png)';
  note.style.backgroundBlendMode = 'multiply';
  htmlText(note, c.note, { left: '0', right: '0', top: '86px', textAlign: 'center', font: '700 62px Caveat', color: C.ink, whiteSpace: 'normal', lineHeight: '60px' });
  tape(st, { x: 165, y: 0, rot: -4, w: 150, cls: 'blue' });
  slap(tl, st, c.sticky);
  out(tl, st, c.out - 0.24, { x: 260, rot: 20 });
  out(tl, el, c.out - 0.24, { x: 260 });
}

// ------------------------------------------------------------------ 19 · outro pages + bye
function outro(tl, c) {
  const mkPage = (side) => {
    const el = div('paper', $stage(), { position: 'absolute', top: '0', width: '230px', height: '1920px', zIndex: 18,
      [side]: '0', boxShadow: side === 'left' ? '10px 0 24px rgba(40,25,10,.35)' : '-10px 0 24px rgba(40,25,10,.35)' });
    const s = svg(el, 230, 1920);
    for (let y = 120; y < 1920; y += 64) node(s, 'line', { x1: 0, y1: y, x2: 230, y2: y, stroke: 'rgba(93,122,153,.32)', 'stroke-width': 2 });
    node(s, 'line', { x1: side === 'left' ? 190 : 40, y1: 0, x2: side === 'left' ? 190 : 40, y2: 1920, stroke: 'rgba(192,57,43,.45)', 'stroke-width': 3 });
    gsap.set(el, { autoAlpha: 0 });
    tl.fromTo(el, { autoAlpha: 1, x: side === 'left' ? -250 : 250 }, { x: 0, duration: c.pages[1] - c.pages[0], ease: 'power3.out', immediateRender: false }, c.pages[0]);
    return el;
  };
  mkPage('left');
  mkPage('right');
  const el = thing({ x: 540, y: c.y, w: 660, h: 210, rot: -2, z: 19, cls: 'shadow' });
  const lab = div('paper', el, { position: 'absolute', inset: '0', borderRadius: '16px' });
  const s = svg(lab, 660, 210);
  sketch(s, 'rectangle', [12, 12, 636, 186], { strokeWidth: 3 });
  text(s, c.text, { x: 330, y: 88, size: 88, font: 'Caveat Brush', weight: 400 });
  text(s, c.sub, { x: 330, y: 160, size: 46, font: 'Kalam', weight: 700, fill: C.terracotta });
  tape(el, { x: 330, y: 0, rot: -3, w: 160, cls: 'sage' });
  pop(tl, el, c.title, { s: 0.5 });
}

function claudeBye(tl, c) {
  const { el, parts } = makeClaude(c.x, c.y, 60, 20);
  const shoulder = `${el.offsetWidth / 2 + 55} ${el.offsetHeight / 2 + 6}`;
  gsap.set(parts.armR, { svgOrigin: shoulder });
  tl.fromTo(el, { autoAlpha: 1, x: -260, rotation: -25 }, { x: 0, rotation: 0, duration: 0.26, ease: 'back.out(2)', immediateRender: false }, c.in);
  wobble(tl, parts.armR, c.in + 0.2, 64.95, { amp: 30, period: 0.26, vars: { svgOrigin: shoulder } });
  const b = bubble(c.x + 170, c.y - 170, 250, 120, [60, 170]);
  b.el.style.fontSize = '50px';
  b.txt.style.top = '22px';
  tl.fromTo(b.el, { autoAlpha: 0, scale: 0.4 }, { autoAlpha: 1, scale: 1, duration: 0.16, ease: 'back.out(2)', immediateRender: false }, c.bubble - 0.04);
  typeOn(tl, b.txt, c.text, c.bubble, c.bubble + 0.35);
}

// ------------------------------------------------------------------ build all
export function buildScenes(tl, beats) {
  const c = beats.cues;
  title(tl, c.title);
  hello(tl, c.hello);
  pennant(tl, c.pennant);
  chapter(tl, c.chapter);
  photo(tl, c.photo);
  flashLabel(tl, c.flash_label);
  textbook(tl, c.textbook);
  flashcards(tl, c.flashcards);
  bridgeBroken(tl, c.bridge_broken);
  house(tl, c.house);
  dad(tl, c.dad);
  storybook(tl, c.storybook);
  checklist(tl, c.checklist);
  fineprint(tl, c.fineprint);
  const sealEl = seal(tl, c.seal);
  bridgeFixed(tl, c.bridge_fixed, c.bridge_broken, sealEl);
  sparkles(tl, c.sparkles);
  envelope(tl, c.envelope);
  calendar(tl, c.calendar);
  words(tl, c.words);
  claude(tl, c.claude);
  lessonCard(tl, c.lesson_card);
  follow(tl, c.follow);
  soccer(tl, c.soccer);
  outro(tl, c.outro);
  claudeBye(tl, c.claude_bye);
}
