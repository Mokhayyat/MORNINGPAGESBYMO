// Captions: house style (Inter Bold, white, sentence chunks, key words lit cyan as they are said),
// on a dark glass pill because Mo is in a white T-shirt in this one. A chunk shows from its first
// word until the next chunk (or shortly after its last word); chunks whose words were cut are skipped.

export function buildCaptions(master, ctx, stage) {
  const C = ctx.tl.captions;
  const words = ctx.words;
  const shown = C.chunks.filter((c) => words.slice(c.w[0], c.w[1] + 1).every((w) => ctx.kept(w.start)));
  ctx.captionLog = [];
  shown.forEach((c, i) => {
    const text = ctx.pick(c.text);
    const el = document.createElement('div');
    el.className = 'cap abs';
    // map display tokens onto the chunk's words so highlights follow the spoken word
    const tokens = text.split(' ');
    const ws = words.slice(c.w[0], c.w[1] + 1);
    tokens.forEach((tok, j) => {
      const s = document.createElement('span');
      s.className = 'w';
      s.textContent = tok;
      el.appendChild(s);
      if (j < tokens.length - 1) el.appendChild(document.createTextNode(' '));
      const wi = c.w[0] + Math.min(j, ws.length - 1);
      if ((c.hl || []).includes(wi)) {
        const t = ctx.out(words[wi].start);
        master.fromTo(s, { color: '#FFFFFF' }, { color: '#00E0FF', duration: 0.08, ease: 'none', immediateRender: false }, t - 0.02);
      }
    });
    stage.appendChild(el);
    if (el.offsetWidth > 780) el.style.fontSize = `${(C.size * 780) / el.offsetWidth}px`;   // keep clear of the app's right-hand buttons
    const w = el.offsetWidth, h = el.offsetHeight;
    gsap.set(el, { x: (ctx.W - w) / 2, y: C.y - h / 2, opacity: 0 });
    const t0 = ctx.out(ws[0].start) - 0.06;
    const next = shown[i + 1];
    const tNext = next ? ctx.out(words[next.w[0]].start) - 0.06 : Infinity;
    const lastEnd = ctx.out(ws[ws.length - 1].end);
    const t1 = next ? Math.min(tNext, lastEnd + 0.45) : Math.min(lastEnd + 0.9, ctx.srcLen + 0.1);
    master.fromTo(el, { scale: 0.94, y: C.y - h / 2 + 10 },
      { scale: 1, y: C.y - h / 2, duration: 0.12, ease: 'power2.out', immediateRender: false }, t0);
    master.set(el, { opacity: 1 }, t0);
    const tOff = Math.max(t0 + 0.2, t1);
    if (next && tOff >= tNext - 1e-3) master.set(el, { opacity: 0 }, tNext);
    else master.to(el, { opacity: 0, duration: 0.08, ease: 'none' }, tOff);
    ctx.captionLog.push({ text, from: +t0.toFixed(3), to: +Math.max(t0 + 0.2, t1).toFixed(3), width: w });
  });
}
