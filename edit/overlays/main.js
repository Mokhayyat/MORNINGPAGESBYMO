// Boot: load the timeline data, build every scene + captions on one paused GSAP timeline,
// and expose window.__seek(t) for the frame-by-frame renderer.
import { setPalette } from './draw.js';
import { buildScenes } from './scenes.js';
import { buildCaptions } from './captions.js';

gsap.registerPlugin(DrawSVGPlugin);
gsap.ticker.lagSmoothing(0);

async function boot() {
  const [beats, transcript] = await Promise.all([
    fetch('../beats.json').then((r) => r.json()),
    fetch('../transcript.json').then((r) => r.json()),
  ]);
  await document.fonts.ready;
  await Promise.all([...document.fonts].map((f) => f.load().catch(() => null)));

  setPalette(beats.palette);
  const tl = gsap.timeline({ paused: true });
  buildScenes(tl, beats);
  buildCaptions(tl, beats, transcript);
  tl.set({}, {}, beats.meta.duration);

  window.__timeline = tl;
  window.__duration = beats.meta.duration;
  window.__fps = beats.meta.fps;
  window.__seek = (t) => {
    tl.time(t, false);
    const n = Math.floor(t * 12 + 1e-6);                 // line boil + film dust at 12 fps ("on twos")
    const b = document.body.classList;
    b.remove('b0', 'b1', 'b2', 'd0', 'd1');
    b.add(`b${n % 3}`, `d${n % 2}`);
  };

  const q = new URLSearchParams(location.search);
  if (q.has('preview')) document.body.classList.add('preview');
  window.__seek(parseFloat(q.get('t') || '0'));
  window.__ready = true;
}

boot().catch((e) => { console.error(e); window.__error = String(e && e.stack || e); });
