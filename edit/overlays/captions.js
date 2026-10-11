// Burned-in handwritten captions on torn paper strips, built from transcript.json word timings.
import { div } from './draw.js';

export function chunkWords(words, cfg, duration) {
  const groups = [];
  let cur = [];
  const len = (ws) => ws.map((w) => w.caption).join(' ').length;
  for (const w of words) {
    const prev = cur[cur.length - 1];
    if (prev) {
      const gap = w.start - prev.end;
      const would = len([...cur, w]);
      const tooLong = cur.length >= cfg.max_words || would > cfg.max_chars;
      // let a sentence's last word ride along instead of sitting alone on screen ("…daily / life")
      const orphanOk = /[.?!]$/.test(w.caption) && would <= cfg.max_chars + 9 && cur.length <= cfg.max_words;
      const sentenceEnd = /[.?!]$/.test(prev.caption);
      const comma = /,$/.test(prev.caption) && cur.length >= 2;
      if (gap >= cfg.gap_break || sentenceEnd || comma || (tooLong && !orphanOk)) { groups.push(cur); cur = []; }
    }
    cur.push(w);
  }
  if (cur.length) groups.push(cur);
  return groups.map((ws, i) => {
    const tin = Math.max(0, ws[0].start - 0.04);
    const next = groups[i + 1];
    const natural = Math.max(ws[ws.length - 1].end + cfg.hold_after, tin + 0.5);
    const tout = Math.min(natural, next ? next[0].start - 0.04 : duration);
    return { words: ws, tin, tout };
  });
}

const clean = (s) => s.replace(/[.,]+$/, '');

export function buildCaptions(tl, beats, transcript) {
  const cfg = beats.captions;
  const chunks = chunkWords(transcript.words, cfg, beats.meta.duration);
  const stage = document.getElementById('stage');
  chunks.forEach((ch, i) => {
    const wrap = div('capwrap', stage, { top: `${cfg.y}px` });
    const cap = div('cap paper torn', wrap);
    ch.words.forEach((w, j) => {
      const key = w.caption.toLowerCase().replace(/[^a-z']/g, '');
      const color = cfg.highlight[key];
      const span = document.createElement('span');
      span.className = 'w' + (color ? ` hl ${color}` : '');
      span.textContent = clean(w.caption);
      cap.appendChild(span);
      if (j < ch.words.length - 1) cap.appendChild(document.createTextNode(' '));
    });
    gsap.set(wrap, { autoAlpha: 0, rotation: i % 2 ? 1.1 : -1.3 });
    tl.fromTo(wrap, { autoAlpha: 0, scale: 0.9, y: 14 },
      { autoAlpha: 1, scale: 1, y: 0, duration: 0.14, ease: 'back.out(2)', immediateRender: false }, ch.tin);
    tl.to(wrap, { autoAlpha: 0, duration: 0.08, ease: 'none' }, ch.tout - 0.08);
  });
  window.__captions = chunks.map((c) => ({ tin: +c.tin.toFixed(2), tout: +c.tout.toFixed(2), text: c.words.map((w) => clean(w.caption)).join(' ') }));
}
