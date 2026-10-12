// Frost that creeps in from the screen edges (feathery ice dendrites with 60-degree side branches,
// a cold haze and a few glints) and the ice crack that lands on the fist. Everything is seeded, so
// every render is identical. Frost growth follows the same progress value the picture grade uses
// (picture.py writes it per frame), so the lines and the cold tint advance together.

export function mulberry32(a) {
  return function () {
    a |= 0; a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const DEPTHS = [
  { step: 10, width: 2.0, alpha: 0.85 },
  { step: 7, width: 1.2, alpha: 0.62 },
  { step: 5, width: 0.7, alpha: 0.42 },
];

function buildBranches(W, H, rnd) {
  const segs = [[], [], []];          // per depth: [x1, y1, x2, y2, d0, d1]
  const tips = [];
  let dMax = 0;
  function grow(x, y, ang, L, depth, d) {
    const { step } = DEPTHS[depth];
    let curv = (rnd() - 0.5) * 0.02, side = rnd() < 0.5 ? 1 : -1;
    let next = step * (1.5 + rnd() * 2);
    for (let s = 0; s < L; s += step) {
      curv = Math.max(-0.03, Math.min(0.03, curv + (rnd() - 0.5) * 0.012));
      ang += curv;
      const nx = x + Math.cos(ang) * step, ny = y + Math.sin(ang) * step;
      segs[depth].push([x, y, nx, ny, d + s, d + s + step]);
      dMax = Math.max(dMax, d + s + step);
      if (depth < 2 && s >= next && s < L * 0.9) {
        const remain = L - s;
        const cap = depth === 0 ? 170 : 46;
        const bl = Math.min(cap, remain * (0.3 + rnd() * 0.35) * (0.7 + rnd() * 0.6));
        const off = Math.PI / 3 + (rnd() - 0.5) * 0.22;
        grow(nx, ny, ang + side * off, bl, depth + 1, d + s);
        if (rnd() < (depth === 0 ? 0.45 : 0.2)) grow(nx, ny, ang - side * off, bl * (0.6 + rnd() * 0.3), depth + 1, d + s);
        side = -side;
        next = s + (depth === 0 ? 22 + rnd() * 22 : 12 + rnd() * 12);
      }
      x = nx; y = ny;
    }
    if (depth === 0) tips.push([x, y, d + L]);
  }
  const seeds = [];
  for (let x = -30; x < W + 30; x += 130 + rnd() * 100) { seeds.push([x, -12, Math.PI / 2]); seeds.push([x + 40 * rnd(), H + 12, -Math.PI / 2]); }
  for (let y = 40; y < H - 40; y += 150 + rnd() * 110) { seeds.push([-12, y, 0]); seeds.push([W + 12, y + 40 * rnd(), Math.PI]); }
  for (const [x, y, a] of seeds) {
    const L = 240 + rnd() * 560;
    grow(x, y, a + (rnd() - 0.5) * 1.15, L, 0, rnd() * 60);
  }
  return { segs, tips, dMax };
}

function hazeCanvas(W, H, rnd) {
  const c = document.createElement('canvas');
  c.width = W; c.height = H;
  const g = c.getContext('2d');
  // edge fog
  const fog = g.createRadialGradient(W / 2, H * 0.46, H * 0.18, W / 2, H * 0.46, H * 0.62);
  fog.addColorStop(0, 'rgba(225,245,255,0)');
  fog.addColorStop(0.6, 'rgba(225,245,255,0.10)');
  fog.addColorStop(1, 'rgba(235,250,255,0.30)');
  g.fillStyle = fog;
  g.fillRect(0, 0, W, H);
  // ice grain, denser towards the edges
  for (let i = 0; i < 16000; i++) {
    const x = rnd() * W, y = rnd() * H;
    const e = Math.min(x, W - x, y * 0.7, (H - y) * 0.7) / (W / 2);
    if (rnd() < e * 1.4) continue;
    g.fillStyle = `rgba(240,252,255,${0.10 + rnd() * 0.30})`;
    g.fillRect(x, y, 1 + rnd() * 1.6, 1 + rnd() * 1.6);
  }
  return c;
}

export class Frost {
  constructor(stage, W, H, seed = 11) {
    this.W = W; this.H = H;
    this.canvas = document.createElement('canvas');
    this.canvas.id = 'frost';
    this.canvas.width = W; this.canvas.height = H;
    stage.appendChild(this.canvas);
    this.g = this.canvas.getContext('2d');
    this.lines = document.createElement('canvas');
    this.lines.width = W; this.lines.height = H;
    const rnd = mulberry32(seed);
    Object.assign(this, buildBranches(W, H, rnd));
    this.haze = hazeCanvas(W, H, rnd);
    this.glints = this.tips.filter(() => rnd() < 0.35).map((t) => [...t, rnd() * 6.28, 7 + rnd() * 9]);
    this.count = this.segs.reduce((n, s) => n + s.length, 0);
  }

  // p: 0..1 growth (from the picture pass), t: output time for the twinkle
  draw(p, t, clear = 0) {
    const { g, W, H } = this;
    g.clearRect(0, 0, W, H);
    if (p <= 0) return;
    const front = p * this.dMax * 1.02;
    const lg = this.lines.getContext('2d');
    lg.clearRect(0, 0, W, H);
    lg.lineCap = 'round';
    this.segs.forEach((list, depth) => {
      const { width, alpha } = DEPTHS[depth];
      lg.beginPath();
      for (const [x1, y1, x2, y2, d0, d1] of list) {
        if (d0 >= front) continue;
        const u = d1 <= front ? 1 : (front - d0) / (d1 - d0);
        lg.moveTo(x1, y1);
        lg.lineTo(x1 + (x2 - x1) * u, y1 + (y2 - y1) * u);
      }
      lg.strokeStyle = `rgba(255,255,255,${alpha})`;
      lg.lineWidth = width;
      lg.stroke();
    });
    // haze first, then a soft cyan-white glow of the lines, then the crisp lines
    g.globalAlpha = Math.min(1, p * 1.25) * 0.9;
    g.drawImage(this.haze, 0, 0);
    g.globalAlpha = 0.75;
    g.filter = 'blur(5px)';
    g.drawImage(this.lines, 0, 0);
    g.filter = 'none';
    g.globalAlpha = 1;
    g.drawImage(this.lines, 0, 0);
    // glints on the tips the frost has reached
    for (const [x, y, d, ph, r] of this.glints) {
      if (d > front) continue;
      const a = 0.35 + 0.65 * Math.max(0, Math.sin(t * 5.5 + ph));
      g.strokeStyle = `rgba(255,255,255,${a})`;
      g.lineWidth = 1.6;
      g.beginPath();
      g.moveTo(x - r, y); g.lineTo(x + r, y);
      g.moveTo(x, y - r); g.lineTo(x, y + r);
      g.stroke();
    }
    if (clear > 0) {
      // breath on the glass: a soft clear window where the end card sits
      const r = g.createRadialGradient(W / 2, H * 0.47, 60, W / 2, H * 0.47, 520);
      r.addColorStop(0, `rgba(0,0,0,${0.92 * clear})`);
      r.addColorStop(0.55, `rgba(0,0,0,${0.7 * clear})`);
      r.addColorStop(1, 'rgba(0,0,0,0)');
      g.globalCompositeOperation = 'destination-out';
      g.fillStyle = r;
      g.fillRect(0, 0, W, H);
      g.globalCompositeOperation = 'source-over';
    }
  }
}

// Ice crack: radial cracks from the impact point, a few side cracks and web arcs. Returns an SVG
// element plus the list of animatable paths with their lengths.
export function buildCrack(stage, W, H, cx, cy, seed = 5) {
  const rnd = mulberry32(seed);
  const NS = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(NS, 'svg');
  svg.setAttribute('id', 'crack');
  svg.setAttribute('width', W); svg.setAttribute('height', H);
  svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
  const glow = document.createElementNS(NS, 'g');
  glow.setAttribute('filter', 'url(#crack-glow)');
  glow.setAttribute('stroke', 'rgba(170,240,255,0.9)');
  const crisp = document.createElementNS(NS, 'g');
  crisp.setAttribute('stroke', '#fff');
  for (const grp of [glow, crisp]) {
    grp.setAttribute('fill', 'none');
    grp.setAttribute('stroke-linecap', 'round');
    grp.setAttribute('stroke-linejoin', 'round');
    svg.appendChild(grp);
  }
  const paths = [];
  const addPath = (d, width, delay) => {
    for (const [grp, w] of [[glow, width * 3.2], [crisp, width]]) {
      const p = document.createElementNS(NS, 'path');
      p.setAttribute('d', d);
      p.setAttribute('stroke-width', w);
      grp.appendChild(p);
      paths.push({ el: p, delay });
    }
  };
  const n = 11;
  const ends = [];
  for (let i = 0; i < n; i++) {
    let ang = (i / n) * Math.PI * 2 + (rnd() - 0.5) * 0.45;
    let x = cx + Math.cos(ang) * 24, y = cy + Math.sin(ang) * 24;
    const L = 260 + rnd() * (rnd() < 0.4 ? 900 : 420);
    let d = `M${x.toFixed(1)} ${y.toFixed(1)}`;
    let s = 0;
    const pts = [];
    while (s < L) {
      const step = 18 + rnd() * 26;
      ang += (rnd() - 0.5) * 0.36;
      x += Math.cos(ang) * step; y += Math.sin(ang) * step;
      s += step;
      d += ` L${x.toFixed(1)} ${y.toFixed(1)}`;
      pts.push([x, y, ang, s]);
    }
    addPath(d, 2.6 - (s / 1400), 0);
    ends.push(pts);
    // side cracks
    for (const [bx, by, ba, bs] of pts) {
      if (rnd() > 0.10) continue;
      let a2 = ba + (rnd() < 0.5 ? 1 : -1) * (0.5 + rnd() * 0.4);
      let x2 = bx, y2 = by, d2 = `M${bx.toFixed(1)} ${by.toFixed(1)}`;
      const L2 = 40 + rnd() * 150;
      for (let s2 = 0; s2 < L2;) {
        const st = 14 + rnd() * 18;
        a2 += (rnd() - 0.5) * 0.4;
        x2 += Math.cos(a2) * st; y2 += Math.sin(a2) * st; s2 += st;
        d2 += ` L${x2.toFixed(1)} ${y2.toFixed(1)}`;
      }
      addPath(d2, 1.4, Math.min(0.1, bs / 4000));
    }
  }
  // web arcs between neighbouring cracks
  for (let i = 0; i < n; i++) {
    if (rnd() < 0.45) continue;
    const a = ends[i], b = ends[(i + 1) % n];
    const k = Math.min(a.length, b.length, 2 + Math.floor(rnd() * 2));
    if (k < 2) continue;
    const pa = a[k - 1], pb = b[k - 1];
    const mx = (pa[0] + pb[0]) / 2 + (cx - (pa[0] + pb[0]) / 2) * 0.12;
    const my = (pa[1] + pb[1]) / 2 + (cy - (pa[1] + pb[1]) / 2) * 0.12;
    addPath(`M${pa[0].toFixed(1)} ${pa[1].toFixed(1)} Q${mx.toFixed(1)} ${my.toFixed(1)} ${pb[0].toFixed(1)} ${pb[1].toFixed(1)}`, 1.3, 0.05);
  }
  // impact ring
  const ring = document.createElementNS(NS, 'circle');
  ring.setAttribute('cx', cx); ring.setAttribute('cy', cy); ring.setAttribute('r', 24);
  ring.setAttribute('fill', 'rgba(255,255,255,0.12)'); ring.setAttribute('stroke', '#fff'); ring.setAttribute('stroke-width', 3);
  crisp.appendChild(ring);
  stage.appendChild(svg);
  for (const p of paths) {
    const len = p.el.getTotalLength();
    p.len = len;
    p.el.style.strokeDasharray = `${len} ${len}`;
    p.el.style.strokeDashoffset = `${len}`;
  }
  return { svg, paths, ring };
}
