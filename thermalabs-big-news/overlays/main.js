// Boot: load the timeline, the word timings and the picture pass's per-frame data for this version,
// build every graphic on one paused GSAP timeline in output time, and expose window.__seek(t) for
// the frame-by-frame renderer. ?v=tight|onetake picks the version, ?t=12.3&preview previews a moment.
import { buildScenes } from './scenes.js';
import { buildCaptions } from './captions.js';

gsap.ticker.lagSmoothing(0);

function makeCtx(tl, words, frames, hands, version) {
  const v = tl.versions[version];
  const segs = v.segments;
  const starts = [];
  let acc = 0;
  for (const [a, b] of segs) { starts.push(acc); acc += b - a; }
  const srcLen = acc;
  const fps = tl.meta.fps;
  const duration = srcLen + tl.meta.end_card;
  const out = (src) => {
    for (let i = 0; i < segs.length; i++) {
      const [a, b] = segs[i];
      if (src < a) return starts[i];
      if (src <= b) return starts[i] + (src - a);
    }
    return srcLen + (src - segs[segs.length - 1][1]);
  };
  const kept = (src) => segs.some(([a, b]) => src >= a && src <= b);
  const pick = (val) => (val !== null && typeof val === 'object' && !Array.isArray(val) ? val[version] : val);
  const frameAt = (t) => frames[Math.max(0, Math.min(frames.length - 1, Math.round(t * fps)))];
  const anchor = ([x, y], t) => { const f = frameAt(t); return [(x - f.tx) * f.k, (y - f.ty) * f.k]; };
  return { tl, words, frames, hands, version, segs, starts, srcLen, fps, duration, out, kept, pick, frameAt, anchor,
    W: tl.meta.out_size[0], H: tl.meta.out_size[1], updaters: [] };
}

async function boot() {
  const q = new URLSearchParams(location.search);
  const version = q.get('v') || 'tight';
  const [tl, tr, pf, hands] = await Promise.all([
    fetch('../timeline.json').then((r) => r.json()),
    fetch('../transcript.json').then((r) => r.json()),
    fetch(`../build/${version}/picture_frames.json`).then((r) => r.json()),
    fetch('../build/hands.json').then((r) => r.json()),
  ]);
  await document.fonts.ready;
  const faces = ['500 20px Inter', '600 20px Inter', '700 20px Inter', '800 20px Inter',
    '700 20px Unbounded', '800 20px Unbounded', '900 20px Unbounded'];
  await Promise.all(faces.map((f) => document.fonts.load(f)));
  await Promise.all([...document.images].map((im) => im.decode().catch(() => null)));

  const ctx = makeCtx(tl, tr.words, pf.frames, hands, version);
  const master = gsap.timeline({ paused: true });
  const stage = document.getElementById('stage');
  await buildScenes(master, ctx, stage);
  buildCaptions(master, ctx, stage);
  master.set({}, {}, ctx.duration);

  window.__timeline = master;
  window.__duration = ctx.duration;
  window.__fps = ctx.fps;
  window.__seek = (t) => {
    master.time(t, false);
    for (const u of ctx.updaters) u(t);
  };
  window.__captions = ctx.captionLog;
  if (q.has('preview')) document.body.classList.add('preview');
  window.__seek(parseFloat(q.get('t') || '0'));
  window.__ready = true;
}

boot().catch((e) => { console.error(e); window.__error = String((e && e.stack) || e); });
