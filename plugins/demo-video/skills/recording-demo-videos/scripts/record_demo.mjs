#!/usr/bin/env node
/**
 * Record a web UI with Playwright while an in-page "virtual camera" pans and zooms.
 *
 *   node record_demo.mjs --url https://site --storyboard ./storyboard.mjs --name intro [--out raw] [--max-seconds 150] [--layout 1280x720]
 *
 * Output: <out>/<name>.webm (1920x1080, wall-clock video) + <out>/<name>.camlog.json (every shot with
 * its time and label, used by edit_demo.py to place captions). A shot made by focus or region also holds
 * "rect": [x, y, w, h], where its target lies on the 1920x1080 frame once the camera has stopped (integers,
 * clipped to the frame, none when the target lies wholly outside it); rec.mark(key, selector, label) writes a
 * "mark" entry with the same rect for an element, without moving the camera.
 *
 * The camera is a CSS transform on <body> (scale + translate, 1.4 s eased transition) applied while
 * Playwright records the full 1920x1080 viewport. Cropping the recording afterwards is blurry; the
 * in-page transform re-rasterizes text at the new scale so zoomed shots stay crisp.
 *
 * --layout WxH (16:9, e.g. 1280x720): the page is laid out at that CSS size and zoomed to fill 1080p, for a UI
 * that fits one screen and should read large. Done with `html { zoom }`, not a smaller viewport: recordVideo
 * pads a small viewport top-left with grey. The camera math runs in layout px; selectors and pads are unchanged.
 *
 * Playwright is resolved from --playwright-root / $PLAYWRIGHT_ROOT / cwd (a dir with node_modules).
 */
import fs from 'node:fs/promises';
import path from 'node:path';
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';

const argv = process.argv.slice(2);
const option = (name, fallback) => { const i = argv.indexOf(name); return i < 0 ? fallback : argv[i + 1]; };

const siteUrl = option('--url', process.env.DEMO_URL);
const storyboardPath = option('--storyboard');
if (!siteUrl || !storyboardPath) { console.error('usage: record_demo.mjs --url <site> --storyboard <file.mjs> [--name n] [--out dir] [--max-seconds n] [--layout 1280x720]'); process.exit(2); }
const name = option('--name', path.basename(storyboardPath, path.extname(storyboardPath)));
const outDir = path.resolve(option('--out', 'raw'));
const maxSeconds = Number(option('--max-seconds', 150));
const layout = option('--layout', '1920x1080');
const [LW, LH] = layout.split('x').map(Number);
if (!(LW > 0 && LH > 0) || Math.abs(LW / LH - 16 / 9) > 0.01) { console.error(`--layout must be 16:9 (1920x1080 or 1280x720), got ${layout}`); process.exit(2); }
await fs.mkdir(outDir, { recursive: true });

const pwRoot = path.resolve(option('--playwright-root', process.env.PLAYWRIGHT_ROOT || process.cwd()));
const { chromium } = createRequire(path.join(pwRoot, 'package.json'))('playwright');

// Output is always 1920x1080 and the viewport must be exactly that: Playwright's recordVideo captures CSS
// pixels, so a smaller viewport with deviceScaleFactor > 1 lands top-left in the frame with blank margins.
const W = 1920, H = 1080;
const Z = W / LW;  // html zoom; 1 for the default layout
const CAMERA_MOVE = 1.4;  // seconds a camera move takes unless a shot gives its own dur (edit_demo.py CAMERA_MOVE)

// ---------------------------------------------------------------- camera (runs inside the page)
const CAMERA_JS = `
(() => {
  if (window.__cam) return;
  const style = document.createElement('style');
  style.textContent = 'html{overflow:hidden!important;background:#0b0f14}body{overflow:visible!important;transform-origin:0 0;transition:transform var(--cam-dur,${CAMERA_MOVE}s) cubic-bezier(.5,0,.15,1);will-change:transform}::-webkit-scrollbar{display:none}';
  document.head.appendChild(style);
  // Layout px: the frame is W x H visual px, but with html zoom Z the page is laid out at W/Z x H/Z and every
  // camera number (rects, translate, pad) lives in that space. getBoundingClientRect returns visual px (already
  // multiplied by Z), so divide before inverting the body transform.
  const Z = ${Z}, W = ${W} / Z, H = ${H} / Z;
  if (Z !== 1) document.documentElement.style.zoom = String(Z);
  const state = { x: 0, y: 0, k: 1 };
  let target = null;  // the last focus/region: where its target truly lies on the page (rect) and the body's box (o)
  let move = ${CAMERA_MOVE};  // seconds the last move takes
  const pageSize = () => ({ w: Math.max(document.body.offsetWidth, W), h: Math.max(document.body.offsetTop + document.body.offsetHeight, H) });
  // A measured place in 1/64 px, the layout's own unit: client rects come in float32 and pass through the inverted
  // transform, and that noise would decide which way an edge that maps to a whole pixel is rounded.
  const lu = v => Math.round(v * 64) / 64;
  // The body transform turns around the body's own box (transform-origin 0 0), which an unstyled page puts 8 px in
  // from the page's corner. The camera aims in a model that takes that box for the corner (kept, so takes frame as
  // they always have); where a rectangle truly lies is worked out around the box itself. Its place: the box's corner
  // as the browser shows it under the transform matrix t, less t's translation (body.offsetLeft/Top are 0 for the body).
  const origin = (t = new DOMMatrix(getComputedStyle(document.body).transform)) => {
    const b = document.body.getBoundingClientRect();
    return { x: lu((b.left + window.scrollX) / Z - t.e), y: lu((b.top + window.scrollY) / Z - t.f) };
  };
  // A client rect (visual px, as getBoundingClientRect gives it) in untransformed page coordinates: invert the current
  // body transform and fold in scroll, otherwise the second shot measures a rect that is already scaled by the first.
  // In the camera's model (what it aims with, as measured); onPage: where the rectangle truly lies on the page.
  const fromClient = (r, onPage = false) => {
    const sx = window.scrollX / Z, sy = window.scrollY / Z, t = new DOMMatrix(getComputedStyle(document.body).transform);
    const m = t.inverse(), o = onPage ? origin(t) : { x: 0, y: 0 };
    const un = (px, py) => { const p = m.transformPoint(new DOMPoint(px / Z + sx - o.x, py / Z + sy - o.y)); return [p.x + o.x, p.y + o.y]; };
    let [x0, y0] = un(r.left, r.top), [x1, y1] = un(r.right, r.bottom);
    if (onPage) [x0, y0, x1, y1] = [x0, y0, x1, y1].map(lu);
    return { x: x0, y: y0, w: x1 - x0, h: y1 - y0 };
  };
  const untransformed = el => fromClient(el.getBoundingClientRect());
  const onPage = el => fromClient(el.getBoundingClientRect(), true);
  const apply = (x, y, k, dur) => {
    target = null;  // a move of its own points at nothing; fitRect names its target once the move is made
    const page = pageSize();
    if (window.scrollX || window.scrollY) window.scrollTo(0, 0);
    k = Math.max(1, Math.min(k, 2.6));
    x = Math.max(0, Math.min(x, page.w - W / k));
    y = Math.max(0, Math.min(y, page.h - H / k));
    move = dur ?? ${CAMERA_MOVE};
    document.body.style.setProperty('--cam-dur', move + 's');
    document.body.style.transform = 'scale(' + k + ') translate(' + (-x) + 'px,' + (-y) + 'px)';
    Object.assign(state, { x, y, k });
    return { x, y, k };
  };
  // A page rectangle (fromClient onPage, or a region's numbers) as the frame shows it with the camera at its current
  // state (the position a move in progress is heading to): scale(k) translate(-x,-y) around the body's box o, then
  // the layout zoom Z; integers (edges rounded outwards), clipped to the frame; null when nothing of it lies on it.
  const frameRect = (r, o = origin()) => {
    const s = Z * state.k;
    const fx = v => Z * o.x + s * (v - o.x - state.x), fy = v => Z * o.y + s * (v - o.y - state.y);
    const x0 = Math.max(0, Math.floor(fx(r.x))), y0 = Math.max(0, Math.floor(fy(r.y)));
    const x1 = Math.min(W * Z, Math.ceil(fx(r.x + r.w))), y1 = Math.min(H * Z, Math.ceil(fy(r.y + r.h)));
    return x1 > x0 && y1 > y0 ? [x0, y0, x1 - x0, y1 - y0] : null;
  };
  // r frames the camera (its model); page is where the target truly lies, for the shot's rect. The body's box is read
  // before the move (apply reads the layout there too): a read after it would start the camera's transition early.
  const fitRect = (r, opts = {}, page = r) => {
    const o = origin();
    const pad = opts.pad ?? 24, kmax = opts.kmax ?? 2.2;
    let k = Math.min(W / (r.w + 2 * pad), H / (r.h + 2 * pad), kmax);
    k = Math.max(1, k);
    const cx = r.x + r.w / 2, cy = (opts.anchorTop ? r.y + H / k / 2 - pad : r.y + r.h / 2);
    const to = apply(cx - W / k / 2, cy - H / k / 2, k, opts.dur);
    target = { rect: page, o };
    return to;
  };
  const focus = (selector, opts = {}) => {
    const els = typeof selector === 'string' ? [...document.querySelectorAll(selector)] : [selector];
    const el = els[opts.index ?? 0];
    if (!el) return null;
    const r = untransformed(el);
    if (r.w < 2 || r.h < 2) return null;
    return fitRect(r, opts, onPage(el));
  };
  const region = (x, y, w, h, opts = {}) => fitRect({ x, y, w, h }, opts);
  const reset = dur => apply(0, 0, 1, dur);
  const targetRect = () => (target ? frameRect(target.rect, target.o) : null);   // reads nothing of the page
  const lastMove = () => move;
  // The element's rect for a mark: { found: false } when nothing matches (or it has no size), else { rect }.
  const mark = (selector, index = 0) => {
    const el = document.querySelectorAll(selector)[index];
    const r = el && onPage(el);
    return !r || r.w < 2 || r.h < 2 ? { found: false } : { found: true, rect: frameRect(r) };
  };
  const rect = selector => { const el = document.querySelector(selector); return el ? untransformed(el) : null; };
  window.__cam = { focus, region, reset, rect, apply, state, pageSize, frameRect, targetRect, lastMove, mark, fromClient };
})();`;

// Playwright's click()/fill() scroll the target into view, which fights the camera transform. Dispatch instead.
const tap = async locator => { await locator.first().waitFor({ state: 'visible' }); await locator.first().dispatchEvent('click'); };

class Recorder {
  constructor(page, name) { this.page = page; this.name = name; this.log = []; this.t0 = Date.now(); this.lastShot = 0; this.lastKey = ''; }
  now() { return (Date.now() - this.t0) / 1000; }
  note(kind, data = {}, t = this.now()) { this.log.push({ t: +t.toFixed(2), kind, ...data }); }
  async install() { await this.page.evaluate(CAMERA_JS); }
  async shot(key, fn, label) {
    const result = await this.page.evaluate(fn).catch(error => ({ error: String(error) }));
    const t = this.lastShot = this.now(); this.lastKey = key;
    // null = selector matched nothing (or a 0-size element): the camera did not move. Say so loudly; a silent
    // no-op here means a whole take with the wrong framing.
    const missing = result === null;
    // where the target lies once the camera stops, and how long the move takes: written only when not the default,
    // so the clip step's camera check knows when this camera stops
    const [rect, move] = result && result.k !== undefined
      ? await this.page.evaluate('[window.__cam.targetRect(), window.__cam.lastMove()]').catch(() => [null, CAMERA_MOVE])
      : [null, CAMERA_MOVE];
    this.note('shot', { key, label, camera: result, ...(rect ? { rect } : {}), ...(move !== CAMERA_MOVE ? { move } : {}),
                        ...(missing ? { missing: true } : {}) }, t);
    if (missing) console.warn(`[${this.now().toFixed(1)}s] shot ${key}: selector matched nothing, camera unchanged`);
    else console.log(`[${this.now().toFixed(1)}s] shot ${key}${label ? ' — ' + label : ''}`);
    return result;
  }
  /** Zoom to fit an element. opts: pad (px), kmax (zoom cap), index, anchorTop, dur (s). label → caption. */
  async focus(key, selector, opts = {}, label) { return this.shot(key, `window.__cam.focus(${JSON.stringify(selector)}, ${JSON.stringify(opts)})`, label); }
  /** Zoom to fit a page-coordinate rectangle. */
  async region(key, x, y, w, h, opts = {}, label) { return this.shot(key, `window.__cam.region(${x},${y},${w},${h},${JSON.stringify(opts)})`, label); }
  /** Say where an element is on the frame as the camera shows it (or will: a move under way counts as made), moving
   *  nothing. Writes a "mark" entry with "rect"; no match → missing: true, a warning, and null (a selector that is not
   *  CSS: the same, with the browser's error in the entry's "error" and in the warning). The label comes third (focus
   *  takes its options there), the index among several matches fourth. */
  async mark(key, selector, label, index = 0) {
    const found = await this.page.evaluate(`window.__cam.mark(${JSON.stringify(selector)}, ${Number(index)})`)
      .catch(error => ({ error: String(error).split('\n')[0] }));
    if (found?.error) return this.markRect(key, null, label, `selector ${selector}: ${found.error}`, found.error);
    return this.markRect(key, found?.found ? found.rect ?? undefined : null, label, `selector ${selector} matched nothing`);
  }
  /** The same for a rectangle already in frame pixels (term.mjs markRows). rect null: nothing to mark; error: the
   *  browser's words, kept in the entry. */
  async markRect(key, rect, label, whyMissing = 'nothing to mark', error) {
    const missing = rect === null;
    this.note('mark', { key, label, ...(rect ? { rect } : {}), ...(missing ? { missing: true } : {}), ...(error ? { error } : {}) });
    if (missing) console.warn(`[${this.now().toFixed(1)}s] mark ${key}: ${whyMissing}`);
    else console.log(`[${this.now().toFixed(1)}s] mark ${key}${label ? ' — ' + label : ''}`);
    return missing ? null : rect;
  }
  async reset(key = 'wide', label) { return this.shot(key, 'window.__cam.reset()', label); }
  since() { return this.now() - this.lastShot; }
  async sleep(ms) { await this.page.waitForTimeout(ms); }
}

// ---------------------------------------------------------------- main
const browser = await chromium.launch({ headless: true, args: ['--disable-dev-shm-usage', '--autoplay-policy=no-user-gesture-required'] });
const context = await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: 1, acceptDownloads: true, recordVideo: { dir: outDir, size: { width: W, height: H } } });
const page = await context.newPage();
page.setDefaultTimeout(30000);
const errors = [];
page.on('pageerror', e => errors.push(e.message));
const rec = new Recorder(page, name);
let ok = false;
try {
  const { default: storyboard } = await import(pathToFileURL(path.resolve(storyboardPath)).href);
  await storyboard({ page, rec, tap, siteUrl, maxSeconds, option });
  ok = true;
} catch (error) {
  rec.note('error', { message: String(error) });
  console.error(error);
  await page.screenshot({ path: path.join(outDir, `${name}.error.png`) }).catch(() => {});
} finally {
  await rec.sleep(1200);
  const video = page.video();
  await context.close();
  const recorded = await video.path();
  const target = path.join(outDir, `${name}.webm`);
  await fs.copyFile(recorded, target);
  await fs.unlink(recorded).catch(() => {});
  await fs.writeFile(path.join(outDir, `${name}.camlog.json`), JSON.stringify({ name, url: siteUrl, layout, ok, errors, duration_s: rec.now(), log: rec.log }, null, 2));
  await browser.close();
  console.log(JSON.stringify({ video: target, ok, seconds: rec.now(), errors: errors.length }));
}
process.exit(ok ? 0 : 1);
