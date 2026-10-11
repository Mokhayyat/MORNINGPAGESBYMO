// Sketchy drawing helpers + the doodle library. Everything is deterministic (seeded),
// so every render of a frame is identical.
import rough from '../node_modules/roughjs/bundled/rough.esm.js';

export const NS = 'http://www.w3.org/2000/svg';
export const C = {};                       // palette, from beats.json
export const setPalette = (p) => Object.assign(C, p);

let _seed = 11;
export function seed() { _seed = (_seed * 16807) % 2147483647; return _seed; }
let _rnd = 12345;
export function rnd() { _rnd = (_rnd * 16807) % 2147483647; return _rnd / 2147483647; }

export const $stage = () => document.getElementById('stage');

export function div(cls = '', parent = $stage(), style = {}) {
  const d = document.createElement('div');
  d.className = cls;
  Object.assign(d.style, style);
  parent.appendChild(d);
  return d;
}

/** Absolutely positioned box centred on (x, y). Starts hidden. */
export function thing({ x, y, w, h, rot = 0, z = 10, cls = '', parent = $stage() }) {
  const d = div('thing ' + cls, parent, {
    left: `${x - w / 2}px`, top: `${y - h / 2}px`, width: `${w}px`, height: `${h}px`, zIndex: z,
  });
  gsap.set(d, { rotation: rot, autoAlpha: 0 });
  return d;
}

export function svg(parent, w, h, style = {}) {
  const s = document.createElementNS(NS, 'svg');
  s.setAttribute('viewBox', `0 0 ${w} ${h}`);
  s.setAttribute('width', w);
  s.setAttribute('height', h);
  Object.assign(s.style, style);
  parent.appendChild(s);
  return s;
}

export function node(parent, tag, attrs = {}) {
  const e = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  parent.appendChild(e);
  return e;
}

export const g = (parent, attrs = {}) => node(parent, 'g', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', ...attrs });

/** Rough.js shape appended to parent (an <svg> or <g>). */
export function sketch(parent, kind, args, opts = {}) {
  const root = parent.ownerSVGElement || parent;
  const rc = rough.svg(root);
  const o = { stroke: C.ink, strokeWidth: 4, roughness: 1.25, bowing: 1, seed: seed(), ...opts };
  const el = rc[kind](...args, o);
  parent.appendChild(el);
  return el;
}

export function text(parent, str, { x = 0, y = 0, size = 40, font = 'Caveat', weight = 700, fill = C.ink,
  anchor = 'middle', rot = 0, ls = 0, stroke, sw = 0 } = {}) {
  const t = node(parent, 'text', {
    x, y, 'font-size': size, 'font-family': font, 'font-weight': weight, fill, 'text-anchor': anchor,
    'dominant-baseline': 'middle', 'letter-spacing': ls,
    ...(rot ? { transform: `rotate(${rot} ${x} ${y})` } : {}),
    ...(stroke ? { stroke, 'stroke-width': sw, 'paint-order': 'stroke', 'stroke-linejoin': 'round' } : {}),
  });
  t.textContent = str;
  return t;
}

export function htmlText(parent, str, style = {}) {
  const d = div('', parent, { position: 'absolute', whiteSpace: 'nowrap', ...style });
  d.textContent = str;
  return d;
}

export function tape(parent, { x, y, rot = -8, w = 130, cls = '' }) {
  const t = div('tape ' + cls, parent, { left: `${x - w / 2}px`, top: `${y - 19}px`, width: `${w}px` });
  t.style.transform = `rotate(${rot}deg)`;
  return t;
}

// ------------------------------------------------------------------ doodles
export function sun(p, cx, cy, r, { fill = C.mustard, rays = 10, sw = 3.5 } = {}) {
  const grp = g(p);
  for (let i = 0; i < rays; i++) {
    const a = (i / rays) * Math.PI * 2 + 0.2;
    sketch(grp, 'line', [cx + Math.cos(a) * r * 1.3, cy + Math.sin(a) * r * 1.3,
      cx + Math.cos(a) * r * 1.8, cy + Math.sin(a) * r * 1.8], { strokeWidth: sw });
  }
  sketch(grp, 'circle', [cx, cy, r * 2], { fill, fillStyle: 'solid', strokeWidth: sw });
  return grp;
}

export function openBook(p, cx, cy, w, h, { cover = C.terracotta, lines = 4, sw = 3.5 } = {}) {
  const grp = g(p);
  const hw = w / 2, t = cy - h / 2, b = cy + h / 2;
  sketch(grp, 'polygon', [[[cx - hw - 12, t + 14], [cx, t + 30], [cx + hw + 12, t + 14], [cx + hw + 12, b + 14],
    [cx, b + 28], [cx - hw - 12, b + 14]]], { fill: cover, fillStyle: 'solid', strokeWidth: sw });
  sketch(grp, 'path', [`M${cx - hw},${t} Q${cx - hw / 2},${t - 14} ${cx},${t + 12} L${cx},${b + 12} Q${cx - hw / 2},${b - 4} ${cx - hw},${b} Z`],
    { fill: C.paper, fillStyle: 'solid', strokeWidth: sw });
  sketch(grp, 'path', [`M${cx + hw},${t} Q${cx + hw / 2},${t - 14} ${cx},${t + 12} L${cx},${b + 12} Q${cx + hw / 2},${b - 4} ${cx + hw},${b} Z`],
    { fill: C.paper, fillStyle: 'solid', strokeWidth: sw });
  for (let i = 1; i <= lines; i++) {
    const yy = t + (i * h) / (lines + 1.2) + 8;
    sketch(grp, 'line', [cx - hw + w * 0.07, yy, cx - w * 0.06, yy + 5], { strokeWidth: 2, stroke: C.inkSoft, roughness: 0.8 });
    sketch(grp, 'line', [cx + w * 0.06, yy + 5, cx + hw - w * 0.07, yy], { strokeWidth: 2, stroke: C.inkSoft, roughness: 0.8 });
  }
  return grp;
}

export function scroll(p, x, y, w, h) {
  const grp = g(p);
  sketch(grp, 'path', [`M${x + 12},${y + 18} Q${x + w / 2},${y + 6} ${x + w - 12},${y + 18} L${x + w - 18},${y + h - 18}
    Q${x + w / 2},${y + h - 30} ${x + 18},${y + h - 18} Z`], { fill: C.paper2, fillStyle: 'solid', strokeWidth: 3.5 });
  sketch(grp, 'path', [`M${x + 12},${y + 18} Q${x + w / 2},${y + 6} ${x + w - 12},${y + 18}`], { strokeWidth: 3 });
  sketch(grp, 'ellipse', [x + 12, y + 22, 26, 34], { fill: C.kraft, fillStyle: 'solid', strokeWidth: 3.5 });
  sketch(grp, 'ellipse', [x + w - 12, y + 22, 26, 34], { fill: C.kraft, fillStyle: 'solid', strokeWidth: 3.5 });
  sketch(grp, 'ellipse', [x + 18, y + h - 20, 26, 34], { fill: C.kraft, fillStyle: 'solid', strokeWidth: 3.5 });
  sketch(grp, 'ellipse', [x + w - 18, y + h - 20, 26, 34], { fill: C.kraft, fillStyle: 'solid', strokeWidth: 3.5 });
  for (let i = 0; i < 4; i++) {
    const yy = y + 42 + i * ((h - 80) / 4);
    const x1 = x + 40, x2 = x + w - 40 - (i % 2) * 30;
    sketch(grp, 'path', [`M${x1},${yy} q 12,-8 24,0 t 24,0 t 24,0 t 24,0 L${x2},${yy}`], { strokeWidth: 2.2, stroke: C.inkSoft, roughness: 0.6 });
  }
  return grp;
}

export function mug(p, x, y, s = 1) {
  const grp = g(p);
  sketch(grp, 'path', [`M${x},${y + 30 * s} L${x + 8 * s},${y + 120 * s} Q${x + 50 * s},${y + 134 * s} ${x + 92 * s},${y + 120 * s} L${x + 100 * s},${y + 30 * s} Z`],
    { fill: C.terracotta, fillStyle: 'solid', strokeWidth: 3.5 });
  sketch(grp, 'ellipse', [x + 50 * s, y + 30 * s, 100 * s, 22 * s], { fill: '#6B4A35', fillStyle: 'solid', strokeWidth: 3.5 });
  sketch(grp, 'path', [`M${x + 98 * s},${y + 52 * s} C${x + 140 * s},${y + 50 * s} ${x + 140 * s},${y + 104 * s} ${x + 94 * s},${y + 100 * s}`],
    { strokeWidth: 6 });
  const steam = g(grp);
  for (let i = 0; i < 3; i++) {
    const sx = x + (28 + i * 22) * s;
    sketch(steam, 'path', [`M${sx},${y + 12 * s} q -10,-14 0,-28 t 0,-28`], { strokeWidth: 3, stroke: C.inkSoft });
  }
  return { grp, steam };
}

export function backpack(p, x, y, s = 1) {
  const grp = g(p);
  sketch(grp, 'path', [`M${x + 10 * s},${y + 30 * s} Q${x + 50 * s},${y - 6 * s} ${x + 90 * s},${y + 30 * s} L${x + 96 * s},${y + 130 * s} L${x + 4 * s},${y + 130 * s} Z`],
    { fill: C.sage, fillStyle: 'solid', strokeWidth: 3.5 });
  sketch(grp, 'rectangle', [x + 22 * s, y + 70 * s, 56 * s, 40 * s], { fill: '#B8C29C', fillStyle: 'solid', strokeWidth: 3 });
  sketch(grp, 'path', [`M${x + 34 * s},${y + 14 * s} Q${x + 50 * s},${y - 14 * s} ${x + 66 * s},${y + 14 * s}`], { strokeWidth: 4 });
  return grp;
}

export function heart(p, cx, cy, r, { fill = C.terracotta, sw = 3 } = {}) {
  return sketch(p, 'path', [`M${cx},${cy + r * 0.9} C${cx - r * 1.6},${cy - r * 0.2} ${cx - r * 0.9},${cy - r * 1.4} ${cx},${cy - r * 0.45}
    C${cx + r * 0.9},${cy - r * 1.4} ${cx + r * 1.6},${cy - r * 0.2} ${cx},${cy + r * 0.9} Z`],
  { fill, fillStyle: 'solid', strokeWidth: sw, roughness: 0.9 });
}

export function sparkle(p, cx, cy, r, { fill = C.mustard, sw = 3 } = {}) {
  const k = r * 0.28;
  return sketch(p, 'path', [`M${cx},${cy - r} Q${cx + k * 0.4},${cy - k * 0.4} ${cx + r},${cy} Q${cx + k * 0.4},${cy + k * 0.4} ${cx},${cy + r}
    Q${cx - k * 0.4},${cy + k * 0.4} ${cx - r},${cy} Q${cx - k * 0.4},${cy - k * 0.4} ${cx},${cy - r} Z`],
  { fill, fillStyle: 'solid', strokeWidth: sw, roughness: 0.8 });
}

export function star(p, cx, cy, r, { fill = C.mustard, points = 5, inner = 0.45, sw = 3 } = {}) {
  const pts = [];
  for (let i = 0; i < points * 2; i++) {
    const a = (i / (points * 2)) * Math.PI * 2 - Math.PI / 2;
    const rr = i % 2 ? r * inner : r;
    pts.push([cx + Math.cos(a) * rr, cy + Math.sin(a) * rr]);
  }
  return sketch(p, 'polygon', [pts], { fill, fillStyle: 'solid', strokeWidth: sw, roughness: 1 });
}

export function blob(p, cx, cy, r, { fill = C.terracotta, n = 11, jag = 0.35, sw = 0, drops = 3 } = {}) {
  const grp = g(p);
  const pts = [];
  for (let i = 0; i < n; i++) {
    const a = (i / n) * Math.PI * 2;
    const rr = r * (1 - jag / 2 + rnd() * jag);
    pts.push([cx + Math.cos(a) * rr, cy + Math.sin(a) * rr]);
  }
  sketch(grp, 'curve', [[...pts, pts[0], pts[1]]], { fill, fillStyle: 'solid', stroke: sw ? C.ink : 'none', strokeWidth: sw, roughness: 0.6 });
  for (let i = 0; i < drops; i++) {
    const a = rnd() * Math.PI * 2, d = r * (1.35 + rnd() * 0.5);
    sketch(grp, 'circle', [cx + Math.cos(a) * d, cy + Math.sin(a) * d, r * (0.18 + rnd() * 0.2)], { fill, fillStyle: 'solid', stroke: 'none', roughness: 0.5 });
  }
  return grp;
}

export function checkMark(p, x, y, s = 1, { stroke = C.ink, sw = 7 } = {}) {
  return sketch(p, 'linearPath', [[[x, y], [x + 18 * s, y + 22 * s], [x + 54 * s, y - 26 * s]]], { stroke, strokeWidth: sw, roughness: 1.1 });
}

export function ship(p, ox, oy) {
  const grp = g(p);
  const waves = g(grp);
  for (let k = 0; k < 2; k++) {
    sketch(waves, 'path', [`M${ox - 20},${oy + 196 + k * 18} q 20,-14 40,0 t 40,0 t 40,0 t 40,0 t 40,0 t 40,0 t 40,0 t 40,0`],
      { stroke: C.blue, strokeWidth: 4 });
  }
  sketch(grp, 'path', [`M${ox + 30},${oy + 150} L${ox + 270},${oy + 150} L${ox + 236},${oy + 196} L${ox + 64},${oy + 196} Z`],
    { fill: '#8A5A3B', fillStyle: 'hachure', hachureGap: 6, fillWeight: 3, strokeWidth: 4 });
  sketch(grp, 'line', [ox + 150, oy + 150, ox + 150, oy + 14], { strokeWidth: 5 });
  sketch(grp, 'path', [`M${ox + 156},${oy + 26} Q${ox + 232},${oy + 70} ${ox + 156},${oy + 132} Z`], { fill: C.paper, fillStyle: 'solid', strokeWidth: 3.5 });
  sketch(grp, 'path', [`M${ox + 144},${oy + 40} Q${ox + 84},${oy + 86} ${ox + 144},${oy + 132} Z`], { fill: '#FBF7EE', fillStyle: 'solid', strokeWidth: 3.5 });
  sketch(grp, 'polygon', [[[ox + 150, oy + 14], [ox + 184, oy + 22], [ox + 150, oy + 32]]], { fill: C.terracotta, fillStyle: 'solid', strokeWidth: 3 });
  return { grp, waves };
}

export function castle(p, ox, oy) {
  const grp = g(p);
  const wall = (x, y, w, h) => sketch(grp, 'rectangle', [x, y, w, h], { fill: '#CFC6B4', fillStyle: 'hachure', hachureGap: 7, fillWeight: 2.5, strokeWidth: 4 });
  wall(ox + 60, oy + 90, 180, 110);
  for (let i = 0; i < 5; i++) sketch(grp, 'rectangle', [ox + 66 + i * 36, oy + 74, 22, 18], { fill: '#CFC6B4', fillStyle: 'solid', strokeWidth: 3 });
  wall(ox + 20, oy + 60, 56, 140);
  wall(ox + 224, oy + 60, 56, 140);
  sketch(grp, 'polygon', [[[ox + 14, oy + 62], [ox + 48, oy + 8], [ox + 82, oy + 62]]], { fill: C.terracotta, fillStyle: 'solid', strokeWidth: 3.5 });
  sketch(grp, 'polygon', [[[ox + 218, oy + 62], [ox + 252, oy + 8], [ox + 286, oy + 62]]], { fill: C.terracotta, fillStyle: 'solid', strokeWidth: 3.5 });
  sketch(grp, 'path', [`M${ox + 126},${oy + 200} L${ox + 126},${oy + 150} Q${ox + 150},${oy + 124} ${ox + 174},${oy + 150} L${ox + 174},${oy + 200}`],
    { fill: '#6B4A35', fillStyle: 'solid', strokeWidth: 3.5 });
  sketch(grp, 'line', [ox + 48, oy + 8, ox + 48, oy - 22], { strokeWidth: 3 });
  sketch(grp, 'polygon', [[[ox + 48, oy - 22], [ox + 74, oy - 15], [ox + 48, oy - 8]]], { fill: C.mustard, fillStyle: 'solid', strokeWidth: 2.5 });
  return grp;
}

export function pyramid(p, ox, oy) {
  const grp = g(p);
  sun(grp, ox + 240, oy + 46, 24, { sw: 3 });
  sketch(grp, 'polygon', [[[ox + 150, oy + 200], [ox + 228, oy + 92], [ox + 300, oy + 200]]], { fill: '#E6C27A', fillStyle: 'hachure', hachureGap: 6, fillWeight: 2.5, strokeWidth: 4 });
  sketch(grp, 'polygon', [[[ox + 6, oy + 200], [ox + 110, oy + 40], [ox + 214, oy + 200]]], { fill: C.mustard, fillStyle: 'hachure', hachureGap: 6, fillWeight: 3, strokeWidth: 4 });
  sketch(grp, 'line', [ox + 110, oy + 40, ox + 132, oy + 200], { strokeWidth: 3 });
  sketch(grp, 'path', [`M${ox - 10},${oy + 204} q 40,-10 80,0 t 80,0 t 80,0 t 80,0`], { stroke: C.kraft, strokeWidth: 5 });
  return grp;
}

export function temple(p, ox, oy) {
  const grp = g(p);
  sketch(grp, 'polygon', [[[ox + 30, oy + 70], [ox + 150, oy + 12], [ox + 270, oy + 70]]], { fill: C.paper, fillStyle: 'solid', strokeWidth: 4 });
  sketch(grp, 'rectangle', [ox + 34, oy + 70, 232, 18], { fill: C.paper2, fillStyle: 'solid', strokeWidth: 3.5 });
  for (let i = 0; i < 5; i++) sketch(grp, 'rectangle', [ox + 46 + i * 46, oy + 92, 22, 88], { fill: '#FBF7EE', fillStyle: 'hachure', hachureGap: 5, fillWeight: 1.5, strokeWidth: 3.5 });
  sketch(grp, 'rectangle', [ox + 26, oy + 180, 248, 14], { fill: C.paper2, fillStyle: 'solid', strokeWidth: 3.5 });
  sketch(grp, 'rectangle', [ox + 14, oy + 194, 272, 14], { fill: C.paper2, fillStyle: 'solid', strokeWidth: 3.5 });
  return grp;
}

export function soccerBall(p, cx, cy, r) {
  const grp = g(p);
  sketch(grp, 'circle', [cx, cy, r * 2], { fill: '#FBF7EE', fillStyle: 'solid', strokeWidth: 5 });
  const pent = (x, y, rr, rot = -Math.PI / 2) => {
    const pts = [];
    for (let i = 0; i < 5; i++) { const a = rot + (i / 5) * Math.PI * 2; pts.push([x + Math.cos(a) * rr, y + Math.sin(a) * rr]); }
    return sketch(grp, 'polygon', [pts], { fill: '#2B2420', fillStyle: 'solid', strokeWidth: 3, roughness: 0.8 });
  };
  pent(cx, cy, r * 0.32);
  for (let i = 0; i < 5; i++) {
    const a = -Math.PI / 2 + (i / 5) * Math.PI * 2;
    pent(cx + Math.cos(a) * r * 0.86, cy + Math.sin(a) * r * 0.86, r * 0.2, a + Math.PI / 2);
    sketch(grp, 'line', [cx + Math.cos(a) * r * 0.32, cy + Math.sin(a) * r * 0.32, cx + Math.cos(a) * r * 0.68, cy + Math.sin(a) * r * 0.68], { strokeWidth: 3 });
  }
  return grp;
}

export function waxSeal(p, cx, cy, r, { label = true } = {}) {
  const grp = g(p);
  const pts = [];
  for (let i = 0; i < 16; i++) {
    const a = (i / 16) * Math.PI * 2;
    const rr = r * (0.92 + (i % 3 === 0 ? 0.12 : 0) + rnd() * 0.06);
    pts.push([cx + Math.cos(a) * rr, cy + Math.sin(a) * rr]);
  }
  sketch(grp, 'curve', [[...pts, pts[0], pts[1]]], { fill: '#A63A2A', fillStyle: 'solid', strokeWidth: 3, stroke: '#5E1F16', roughness: 0.7 });
  sketch(grp, 'circle', [cx, cy, r * 1.36], { stroke: 'rgba(255,220,200,.55)', strokeWidth: 4, roughness: 1.3 });
  if (label) {
    text(grp, 'THE', { x: cx, y: cy - r * 0.3, size: r * 0.3, font: 'Kalam', weight: 700, fill: '#F7DCCB', ls: 3 });
    text(grp, 'LESSON', { x: cx, y: cy + r * 0.12, size: r * 0.36, font: 'Kalam', weight: 700, fill: '#F7DCCB', ls: 1 });
    star(grp, cx, cy + r * 0.48, r * 0.12, { fill: '#F7DCCB', sw: 0 });
  } else {
    star(grp, cx, cy, r * 0.36, { fill: '#F7DCCB', sw: 0 });
  }
  return grp;
}

export function scissors(p, cx, cy, s = 1) {
  const root = g(p);
  const top = g(root), bot = g(root);
  sketch(top, 'path', [`M${cx},${cy} L${cx - 120 * s},${cy - 14 * s} L${cx - 118 * s},${cy - 2 * s} Z`], { fill: '#B9C0C6', fillStyle: 'solid', strokeWidth: 3 });
  sketch(top, 'ellipse', [cx + 44 * s, cy - 20 * s, 54 * s, 36 * s], { stroke: C.terracotta, strokeWidth: 8 });
  sketch(bot, 'path', [`M${cx},${cy} L${cx - 120 * s},${cy + 14 * s} L${cx - 118 * s},${cy + 2 * s} Z`], { fill: '#B9C0C6', fillStyle: 'solid', strokeWidth: 3 });
  sketch(bot, 'ellipse', [cx + 44 * s, cy + 20 * s, 54 * s, 36 * s], { stroke: C.terracotta, strokeWidth: 8 });
  sketch(root, 'circle', [cx, cy, 10 * s], { fill: C.ink, fillStyle: 'solid', strokeWidth: 2 });
  return { root, top, bot };
}

export function pencil(p, x, y, len = 150, rot = 0) {
  const grp = g(p, { transform: `rotate(${rot} ${x} ${y})` });
  sketch(grp, 'rectangle', [x, y - 12, len, 24], { fill: C.mustard, fillStyle: 'solid', strokeWidth: 3 });
  sketch(grp, 'polygon', [[[x + len, y - 12], [x + len + 34, y], [x + len, y + 12]]], { fill: '#E8CFA6', fillStyle: 'solid', strokeWidth: 3 });
  sketch(grp, 'polygon', [[[x + len + 22, y - 4], [x + len + 34, y], [x + len + 22, y + 4]]], { fill: C.ink, fillStyle: 'solid', strokeWidth: 2 });
  sketch(grp, 'rectangle', [x - 22, y - 12, 22, 24], { fill: '#E7A1A1', fillStyle: 'solid', strokeWidth: 3 });
  return grp;
}

export function brush(p, x, y, len = 150, rot = 0) {
  const grp = g(p, { transform: `rotate(${rot} ${x} ${y})` });
  sketch(grp, 'rectangle', [x, y - 8, len, 16], { fill: '#8A5A3B', fillStyle: 'solid', strokeWidth: 3 });
  sketch(grp, 'rectangle', [x + len, y - 11, 22, 22], { fill: '#B9C0C6', fillStyle: 'solid', strokeWidth: 3 });
  sketch(grp, 'path', [`M${x + len + 22},${y - 11} Q${x + len + 60},${y} ${x + len + 22},${y + 11} Z`], { fill: C.blue, fillStyle: 'solid', strokeWidth: 3 });
  return grp;
}

export function spiral(p, cx, cy, r, { stroke = C.sage } = {}) {
  let d = `M${cx},${cy}`;
  for (let a = 0; a < Math.PI * 6; a += 0.3) { const rr = (a / (Math.PI * 6)) * r; d += ` L${cx + Math.cos(a) * rr},${cy + Math.sin(a) * rr}`; }
  return sketch(p, 'path', [d], { stroke, strokeWidth: 5, roughness: 0.7 });
}

/** Little Claude: a round coral sun-creature with a face. Returns handles for animation. */
export function littleClaude(p, cx, cy, r) {
  const root = g(p);
  const rays = g(root);
  for (let i = 0; i < 8; i++) {
    const a = (i / 8) * Math.PI * 2 + Math.PI / 8;
    sketch(rays, 'line', [cx + Math.cos(a) * r * 1.05, cy + Math.sin(a) * r * 1.05, cx + Math.cos(a) * r * 1.42, cy + Math.sin(a) * r * 1.42],
      { stroke: C.claude, strokeWidth: r * 0.16, roughness: 0.6 });
  }
  const armL = g(root), armR = g(root);
  sketch(armL, 'path', [`M${cx - r * 0.92},${cy + r * 0.2} Q${cx - r * 1.45},${cy + r * 0.5} ${cx - r * 1.5},${cy + r * 0.95}`], { strokeWidth: 6, roughness: 0.8 });
  sketch(armL, 'circle', [cx - r * 1.5, cy + r * 0.98, r * 0.24], { fill: C.claude, fillStyle: 'solid', strokeWidth: 4 });
  sketch(armR, 'path', [`M${cx + r * 0.92},${cy + r * 0.1} Q${cx + r * 1.45},${cy - r * 0.2} ${cx + r * 1.55},${cy - r * 0.75}`], { strokeWidth: 6, roughness: 0.8 });
  sketch(armR, 'circle', [cx + r * 1.56, cy - r * 0.8, r * 0.24], { fill: C.claude, fillStyle: 'solid', strokeWidth: 4 });
  sketch(root, 'circle', [cx, cy, r * 2], { fill: C.claude, fillStyle: 'solid', strokeWidth: 5, roughness: 1 });
  sketch(root, 'circle', [cx - r * 0.12, cy - r * 0.12, r * 1.5], { fill: 'rgba(255,255,255,.16)', fillStyle: 'hachure', hachureGap: 8, fillWeight: 2, stroke: 'none' });
  const cheeks = g(root);
  node(cheeks, 'ellipse', { cx: cx - r * 0.55, cy: cy + r * 0.28, rx: r * 0.2, ry: r * 0.12, fill: 'rgba(255,170,170,.75)' });
  node(cheeks, 'ellipse', { cx: cx + r * 0.55, cy: cy + r * 0.28, rx: r * 0.2, ry: r * 0.12, fill: 'rgba(255,170,170,.75)' });
  const eyes = g(root);
  for (const sx of [-1, 1]) {
    node(eyes, 'ellipse', { cx: cx + sx * r * 0.34, cy: cy - r * 0.08, rx: r * 0.11, ry: r * 0.16, fill: C.ink });
    node(eyes, 'circle', { cx: cx + sx * r * 0.34 + r * 0.04, cy: cy - r * 0.15, r: r * 0.04, fill: '#fff' });
  }
  const shy = g(root, { opacity: 0 });
  for (const sx of [-1, 1]) {
    node(shy, 'path', { d: `M${cx + sx * r * 0.34 - r * 0.13},${cy - r * 0.04} Q${cx + sx * r * 0.34},${cy - r * 0.24} ${cx + sx * r * 0.34 + r * 0.13},${cy - r * 0.04}`,
      fill: 'none', stroke: C.ink, 'stroke-width': 5, 'stroke-linecap': 'round' });
  }
  const happy = node(root, 'path', { d: `M${cx - r * 0.24},${cy + r * 0.24} Q${cx},${cy + r * 0.5} ${cx + r * 0.24},${cy + r * 0.24}`,
    fill: 'none', stroke: C.ink, 'stroke-width': 5, 'stroke-linecap': 'round' });
  const nervous = node(root, 'path', { d: `M${cx - r * 0.26},${cy + r * 0.34} q ${r * 0.09},-${r * 0.1} ${r * 0.17},0 t ${r * 0.17},0 t ${r * 0.17},0`,
    fill: 'none', stroke: C.ink, 'stroke-width': 5, 'stroke-linecap': 'round', opacity: 0 });
  const sweat = node(root, 'path', { d: `M${cx + r * 0.95},${cy - r * 0.75} q -${r * 0.16},${r * 0.26} 0,${r * 0.34} q ${r * 0.16},-${r * 0.08} 0,-${r * 0.34} Z`,
    fill: '#9FC6E8', stroke: C.ink, 'stroke-width': 3, opacity: 0 });
  return { root, rays, armL, armR, eyes, shy, happy, nervous, sweat, cheeks };
}

/** Hand-drawn speech bubble with a tail pointing at (tx, ty) in local coords. */
export function bubbleShape(p, w, h, tx, ty) {
  const grp = g(p);
  const r = 34;
  const tailX = Math.min(Math.max(tx, r + 20), w - r - 60);
  sketch(grp, 'path', [`M${r},4 L${w - r},4 Q${w - 4},4 ${w - 4},${r} L${w - 4},${h - r} Q${w - 4},${h - 4} ${w - r},${h - 4}
    L${tailX + 52},${h - 4} L${tx},${ty} L${tailX + 10},${h - 4} L${r},${h - 4} Q4,${h - 4} 4,${h - r} L4,${r} Q4,4 ${r},4 Z`],
  { fill: '#FBF7EE', fillStyle: 'solid', strokeWidth: 4.5, roughness: 1 });
  return grp;
}
