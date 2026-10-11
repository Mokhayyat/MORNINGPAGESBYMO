// Frame-accurate overlay renderer: seeks the paused GSAP timeline one frame at a time and screenshots
// with a transparent background. Never screen-records.
//
//   node scripts/render_overlays.mjs --out overlays.mov [--from 0] [--to 64.95]    ProRes 4444 + alpha
//   node scripts/render_overlays.mjs --stills 1.0,9.3,48.5 --outdir stills/        transparent PNGs
//   node scripts/render_overlays.mjs --check                                        load + report only
import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import fs from 'node:fs';
import http from 'node:http';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const args = Object.fromEntries(process.argv.slice(2).reduce((acc, a, i, arr) => {
  if (a.startsWith('--')) acc.push([a.slice(2), arr[i + 1] && !arr[i + 1].startsWith('--') ? arr[i + 1] : true]);
  return acc;
}, []));

const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.css': 'text/css',
  '.json': 'application/json', '.png': 'image/png', '.ttf': 'font/ttf', '.svg': 'image/svg+xml' };
const server = http.createServer((req, res) => {
  const p = path.join(root, decodeURIComponent(new URL(req.url, 'http://x').pathname));
  if (!p.startsWith(root) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); res.end(); return; }
  res.writeHead(200, { 'content-type': TYPES[path.extname(p)] || 'application/octet-stream' });
  fs.createReadStream(p).pipe(res);
});
await new Promise((r) => server.listen(0, '127.0.0.1', r));
const url = `http://127.0.0.1:${server.address().port}/overlays/index.html`;

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
const problems = [];
page.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warning') problems.push(`[${m.type()}] ${m.text()}`); });
page.on('pageerror', (e) => problems.push(`[pageerror] ${e.message}`));
page.on('requestfailed', (r) => problems.push(`[requestfailed] ${r.url()}`));
await page.goto(url, { waitUntil: 'networkidle' });
await page.waitForFunction(() => window.__ready === true || window.__error, null, { timeout: 60000 });
const err = await page.evaluate(() => window.__error);
if (err) { console.error(err); process.exit(1); }
const { duration, fps } = await page.evaluate(() => ({ duration: window.__duration, fps: window.__fps }));
const seek = (t) => page.evaluate((tt) => window.__seek(tt), t);
const shot = (opts = {}) => page.screenshot({ omitBackground: true, type: 'png', animations: 'disabled', ...opts });

if (args.check) {
  console.log(JSON.stringify(await page.evaluate(() => window.__captions), null, 0));
} else if (args.stills) {
  const outdir = args.outdir || 'stills';
  fs.mkdirSync(outdir, { recursive: true });
  for (const t of String(args.stills).split(',').map(Number)) {
    await seek(t);
    await shot({ path: path.join(outdir, `ov_${t.toFixed(2)}.png`) });
  }
  console.log(`stills -> ${outdir}`);
} else {
  const out = args.out || 'overlays.mov';
  const from = Number(args.from ?? 0), to = Math.min(Number(args.to ?? duration), duration);
  const i0 = Math.round(from * fps), i1 = Math.ceil(to * fps - 1e-6);
  const ff = spawn('ffmpeg', ['-v', 'error', '-y', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'png', '-i', '-',
    '-vf', 'scale=out_color_matrix=bt709:out_range=tv,format=yuva444p10le',
    '-c:v', 'prores_ks', '-profile:v', '4444', '-pix_fmt', 'yuva444p10le', '-vendor', 'apl0', '-qscale:v', '6',
    '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv', out], { stdio: ['pipe', 'inherit', 'inherit'] });
  const t0 = Date.now();
  for (let i = i0; i < i1; i++) {
    await seek(i / fps);
    const buf = await shot();
    if (!ff.stdin.write(buf)) await once(ff.stdin, 'drain');
    if ((i - i0) % 150 === 0) console.log(`frame ${i}/${i1} (${((Date.now() - t0) / 1000).toFixed(0)}s)`);
  }
  ff.stdin.end();
  await once(ff, 'close');
  console.log(`${i1 - i0} frames ${from}-${to}s -> ${out} in ${((Date.now() - t0) / 1000).toFixed(0)}s`);
}
if (problems.length) console.log('PAGE PROBLEMS:\n' + [...new Set(problems)].slice(0, 30).join('\n'));
await browser.close();
server.close();
