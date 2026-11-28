#!/usr/bin/env node
/**
 * Record a web UI with Playwright while an in-page "virtual camera" pans and zooms.
 *
 *   node record_demo.mjs --url https://site --storyboard ./storyboard.mjs --name intro [--out raw] [--max-seconds 150] [--layout 1280x720]
 *                        [--dialogs accept|dismiss|leave] [--no-pointer] [--backdrop <css colour>]
 *
 * Output: <out>/<name>.webm (1920x1080, wall-clock video) + <out>/<name>.camlog.json (every shot with
 * its time and label, used by edit_demo.py to place captions). A shot made by focus or region also holds
 * "rect": [x, y, w, h], where its target lies on the 1920x1080 frame once the camera has stopped (integers,
 * clipped to the frame, none when the target lies wholly outside it); rec.mark(key, selector, label) writes a
 * "mark" entry with the same rect for an element, without moving the camera.
 * Also <out>/<name>.frametext.txt (1.5.0): the text each frame showed, in the format of frametext.mjs. One entry per
 * shot (the frame once the camera has stopped), one for the view a shot leaves when it changed since ("leave": results
 * arrive after a shot, not with it), one per mark (the element's own text) and one per `await rec.text(key)` (the frame
 * now: for a screen that changes while the camera stays). check_demo.py brief reads it. Only what the frame shows is
 * kept: not text scrolled out of an overflow box, not hidden elements, never a password field's value.
 *
 * Presses (1.6.0, references/pointer.md): rec.tap(locator, {key, label}) moves a drawn pointer and the real mouse to
 * the element and presses it; rec.hover(locator) stops there. Camlog entries: "tap" with "t", "key", "label", "rect",
 * "point", "text" and, when they apply, "covered", "outside", "same_tab"; "hover" likewise; a "shot" of key "pan" (the
 * camera went to a press target) or "scroll" (it took a window scroll into its own position); "load" with "url" and,
 * for a swapped <body>, "soft"; "popup" with "url"; "dialog" with "type" and "message".
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
import { formatFrametext } from './frametext.mjs';
import { POINTER, travelSeconds, pointerJs } from './pointer.mjs';

const argv = process.argv.slice(2);
const option = (name, fallback) => { const i = argv.indexOf(name); return i < 0 ? fallback : argv[i + 1]; };

const siteUrl = option('--url', process.env.DEMO_URL);
const storyboardPath = option('--storyboard');
if (!siteUrl || !storyboardPath) { console.error('usage: record_demo.mjs --url <site> --storyboard <file.mjs> [--name n] [--out dir] [--max-seconds n] [--layout 1280x720] [--dialogs accept|dismiss|leave] [--no-pointer] [--backdrop <css colour>]'); process.exit(2); }
// --backdrop <css colour>: paint <html> with it, as the camera always did before 1.6.0 (#0b0f14). The camera no longer
// does by itself: a light page that sets no background of its own (the browser's white) showed dark text on dark.
const BACKDROP = option('--backdrop', '');
if (!/^[#\w(),.% -]*$/.test(BACKDROP)) { console.error(`--backdrop must be a CSS colour, got ${BACKDROP}`); process.exit(2); }
const pointerOn = !argv.includes('--no-pointer');   // --no-pointer: no pointer, tap() sends the click event as before 1.6.0
const dialogs = option('--dialogs', 'accept');
if (!['accept', 'dismiss', 'leave'].includes(dialogs)) { console.error(`--dialogs must be accept, dismiss or leave, got ${dialogs}`); process.exit(2); }
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
  style.textContent = 'html{overflow:hidden!important${BACKDROP ? ';background:' + BACKDROP : ''}}body{overflow:visible!important;transform-origin:0 0;transition:transform var(--cam-dur,${CAMERA_MOVE}s) cubic-bezier(.5,0,.15,1);will-change:transform}::-webkit-scrollbar{display:none}';
  document.head.appendChild(style);
  // Layout px: the frame is W x H visual px, but with html zoom Z the page is laid out at W/Z x H/Z and every
  // camera number (rects, translate, pad) lives in that space. getBoundingClientRect returns visual px (already
  // multiplied by Z), so divide before inverting the body transform.
  const Z = ${Z}, W = ${W} / Z, H = ${H} / Z;
  if (Z !== 1) document.documentElement.style.zoom = String(Z);
  const state = { x: 0, y: 0, k: 1 };
  let target = null;  // the last focus/region: where its target truly lies on the page (rect) and the body's box (o)
  let move = ${CAMERA_MOVE};  // seconds the last move takes
  // How far down the camera can travel is the body's content, not only the body's own box: a body shorter than what
  // it holds (content positioned absolutely, a body of height 100 %) says the content's height in scrollHeight, and
  // that does not change under the camera's transform (documentElement.scrollHeight doubles under a 2x camera).
  // The body's own box may start below the page's corner (a first paragraph's margin pushes it down, and offsetTop
  // of <body> is always 0): its true corner is origin(), and the page ends that much further down.
  // Sideways the page is the body's own box, as before 1.6.0: scrollWidth also counts what a site parks off the side
  // (a skip link at left: 100 %, a closed drawer), and a camera that went there slid the whole page out of place.
  // A page without a doctype (quirks mode) is the exception: there the body's scrollHeight is the viewport's, which
  // grows with the camera's own zoom. Its height is the body's own box, as before 1.6.0.
  const pageSize = () => {
    const b = document.body, o = origin();
    const tall = document.compatMode === 'BackCompat' ? b.offsetHeight : Math.max(b.offsetHeight, b.scrollHeight);
    return { w: Math.max(o.x + b.offsetWidth, W), h: Math.max(o.y + tall, H) };
  };
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
  const fromClient = (r, onPage = false, t = new DOMMatrix(getComputedStyle(document.body).transform)) => {
    const sx = window.scrollX / Z, sy = window.scrollY / Z;
    const m = t.inverse(), o = onPage ? origin(t) : { x: 0, y: 0 };
    const un = (px, py) => { const p = m.transformPoint(new DOMPoint(px / Z + sx - o.x, py / Z + sy - o.y)); return [p.x + o.x, p.y + o.y]; };
    let [x0, y0] = un(r.left, r.top), [x1, y1] = un(r.right, r.bottom);
    if (onPage) [x0, y0, x1, y1] = [x0, y0, x1, y1].map(lu);
    return { x: x0, y: y0, w: x1 - x0, h: y1 - y0 };
  };
  const untransformed = el => fromClient(el.getBoundingClientRect());
  const onPage = el => fromClient(el.getBoundingClientRect(), true);
  // Put the camera at x, y (layout px of the page, clamped to it) and zoom k, over seconds.
  const place = (x, y, k, seconds) => {
    const page = pageSize();
    k = Math.max(1, Math.min(k, 2.6));
    x = Math.max(0, Math.min(x, page.w - W / k));
    y = Math.max(0, Math.min(y, page.h - H / k));
    document.body.style.setProperty('--cam-dur', seconds + 's');
    document.body.style.transform = 'scale(' + k + ') translate(' + (-x) + 'px,' + (-y) + 'px)';
    Object.assign(state, { x, y, k });
    return { x, y, k };
  };
  // A window scroll (an in-page anchor, the page's own code, a focus) moves the frame without the camera knowing: its
  // numbers, every rect it logs and the frame text would be those of another part of the page. fold() turns the scroll
  // into the camera's own position, at once, and puts the window back at 0, 0. No pixel changes (measured 2026-11-28).
  // The scroll is in zoomed pixels: one layout px of the page is Z * k of them. The style is read back so that the
  // next move starts from the folded position, not from the one before it.
  const fold = () => {
    const sx = window.scrollX, sy = window.scrollY;
    if (!sx && !sy) return false;
    place(state.x + sx / (Z * state.k), state.y + sy / (Z * state.k), state.k, 0);
    window.scrollTo({ left: 0, top: 0, behavior: 'instant' });
    void getComputedStyle(document.body).transform;
    return true;
  };
  // When a scroll has ended the camera takes it and tells the recorder (a "shot" of key scroll in the camlog).
  let scrolled = 0;
  const settle = () => { clearTimeout(scrolled); if (fold() && window.__demoEvent) window.__demoEvent({ kind: 'scroll', camera: { ...state } }); };
  if ('onscrollend' in window) window.addEventListener('scrollend', settle);
  else window.addEventListener('scroll', () => { clearTimeout(scrolled); scrolled = setTimeout(settle, 120); });
  const apply = (x, y, k, dur) => {
    fold();         // a scroll still in the window would make this move start with a jump
    target = null;  // a move of its own points at nothing; fitRect names its target once the move is made
    move = dur ?? ${CAMERA_MOVE};
    return place(x, y, k, move);
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
  // ---- the text the frame shows (1.5.0)
  const collapse = s => s.replace(/\\s+/g, ' ');
  const NO_VALUE = ['password', 'hidden', 'checkbox', 'radio', 'file', 'button', 'submit', 'reset', 'image', 'color', 'range'];
  // What a form field shows: its value (a select: the chosen option's text). A password field's value is never read.
  const fieldValue = el => {
    if (el.tagName === 'SELECT') return el.selectedOptions[0] ? el.selectedOptions[0].textContent : '';
    if (el.tagName === 'INPUT' && NO_VALUE.includes((el.getAttribute('type') || 'text').toLowerCase())) return '';
    return el.value || '';
  };
  // The text of what lies in the frame once the camera has stopped, in reading order, one line per row of the screen.
  // A piece is a text node (or a form field's value) with the place of its first line box that the frame shows; a box
  // cut away by an overflow ancestor is not shown. <html> and <body> are no such ancestors: the camera's own style
  // hides <html>'s overflow, and the frame is what the camera brings into it. An overflow box cuts only what is laid
  // out in it: an absolutely or fixedly positioned element (a popover, a dropdown, a dialog) is laid out in the
  // ancestor it is positioned against, and shows outside an overflow parent that lies between the two.
  const frameText = () => {
    const t = new DOMMatrix(getComputedStyle(document.body).transform), o = origin(t);
    const shown = new Map(), clips = new Map();
    const visible = el => {
      let v = shown.get(el);
      if (v === undefined) shown.set(el, v = el.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true, opacityProperty: true, visibilityProperty: true }));
      return v;
    };
    const positions = (a, fixed) => {   // a is what an absolutely (fixed: fixedly) positioned descendant is positioned against
      const cs = getComputedStyle(a);
      return (!fixed && cs.position !== 'static') || cs.transform !== 'none' || cs.perspective !== 'none' || cs.filter !== 'none'
        || /transform|perspective|filter/.test(cs.willChange) || /paint|layout|strict|content/.test(cs.contain);
    };
    const laidOutIn = (el, position) => {   // the element whose overflow cuts el: its parent, or what it is positioned against
      if (position !== 'absolute' && position !== 'fixed') return el.parentElement;
      for (let a = el.parentElement; a && a !== document.body && a !== document.documentElement; a = a.parentElement) {
        if (positions(a, position === 'fixed')) return a;
      }
      return null;   // the page itself
    };
    const clipOf = el => {   // the client box everything inside el is cut to; null: not cut
      if (!el || el === document.body || el === document.documentElement) return null;
      if (clips.has(el)) return clips.get(el);
      const cs = getComputedStyle(el);
      let box = clipOf(laidOutIn(el, cs.position));
      if (cs.overflowX !== 'visible' || cs.overflowY !== 'visible') {
        const r = el.getBoundingClientRect();
        box = box ? { left: Math.max(box.left, r.left), top: Math.max(box.top, r.top), right: Math.min(box.right, r.right), bottom: Math.min(box.bottom, r.bottom) }
                  : { left: r.left, top: r.top, right: r.right, bottom: r.bottom };
      }
      clips.set(el, box);
      return box;
    };
    const place = (r, box) => {   // a client rect, cut to box, as the frame at rest shows it: [x, y, w, h] or null
      const c = box ? { left: Math.max(r.left, box.left), top: Math.max(r.top, box.top), right: Math.min(r.right, box.right), bottom: Math.min(r.bottom, box.bottom) } : r;
      return c.right - c.left < 0.5 || c.bottom - c.top < 0.5 ? null : frameRect(fromClient(c, true, t), o);
    };
    const pieces = [];
    const add = (f, s) => pieces.push({ x: f[0], y: f[1], w: f[2], h: f[3], s });
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT), range = document.createRange();
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
      const el = node.parentElement;
      // a node of nothing but whitespace counts when it is drawn (a framework's ',<!-- --> <a>' keeps the space of
      // "TypeScript, Python" in a node of its own); between blocks it has no box and falls out below
      if (!el || !node.data || el.closest('script,style,noscript,template,textarea,select') || !visible(el)) continue;
      const box = clipOf(el);
      range.selectNodeContents(node);
      for (const r of range.getClientRects()) {
        const f = place(r, box);
        if (f) { add(f, collapse(node.data)); break; }
      }
    }
    for (const el of document.querySelectorAll('input, textarea, select')) {
      const value = collapse(fieldValue(el)).trim();
      if (!value || !visible(el)) continue;
      const f = place(el.getBoundingClientRect(), clipOf(el.parentElement));
      if (f) add(f, value);
    }
    pieces.sort((a, b) => a.y - b.y || a.x - b.x);
    const rows = [];
    for (const p of pieces) {   // one row: pieces that share more than half the lower one's height (a big number between small labels)
      const row = rows[rows.length - 1];
      if (row && Math.min(row.y + row.h, p.y + p.h) - Math.max(row.y, p.y) > Math.min(p.h, row.h) / 2) row.items.push(p);
      else rows.push({ y: p.y, h: p.h, items: [p] });
    }
    // within a row, pieces that touch are one run of text (a terminal row is many spans); pieces apart get a space
    return rows.map(row => collapse(row.items.sort((a, b) => a.x - b.x).reduce((line, p, i, all) =>
      i ? line + (p.x - (all[i - 1].x + all[i - 1].w) < 0.3 * Math.min(p.h, all[i - 1].h) ? '' : ' ') + p.s : p.s, '')).trim())
      .filter(Boolean).join('\\n');
  };
  // An element's own text (a form field: its value), each line trimmed, empty lines dropped; null when nothing matches.
  const elementText = (selector, index = 0) => {
    const el = document.querySelectorAll(selector)[index];
    if (!el) return null;
    const own = ['INPUT', 'TEXTAREA', 'SELECT'].includes(el.tagName) ? fieldValue(el) : (el.innerText ?? el.textContent ?? '');
    return own.split('\\n').map(line => collapse(line).trim()).filter(Boolean).join('\\n');
  };
  // A page that swaps its <body> without loading a document is a new page to the camera: its transform was on the
  // old body. It starts over on the new one, wide, and tells the recorder (a "load" entry with soft: true).
  let body = document.body;
  new MutationObserver(() => {
    if (!document.body || document.body === body) return;
    body = document.body;
    if (!style.isConnected) document.head.appendChild(style);
    target = null;
    Object.assign(state, { x: 0, y: 0, k: 1 });
    if (window.__demoEvent) window.__demoEvent({ kind: 'load', soft: true });
  }).observe(document.documentElement, { childList: true });
  // ---- what a press needs to find its target on the frame (1.6.0)
  const firstBox = el => [...el.getClientRects()].find(r => r.width >= 1 && r.height >= 1) ?? el.getBoundingClientRect();
  // Scroll the element's scrolling ancestors (below <body>) by the least that shows its first line, then say where
  // that line's centre lies on the page and whether the frame at rest shows it: the centre clear of the frame's edges
  // by edge frame px, and the whole line by clear frame px (a button whose top the frame cuts off is pressed in the
  // viewer's sight, but reads as a mistake). A line too large for the frame is held to its centre only.
  const reveal = (el, edge, clear = 0) => {
    const whole = el.getBoundingClientRect();
    if (whole.width < 1 && whole.height < 1) return null;   // hidden or gone: nothing to bring in
    for (let a = el.parentElement; a && a !== document.body && a !== document.documentElement; a = a.parentElement) {
      const cs = getComputedStyle(a);
      if (!/auto|scroll|hidden/.test(cs.overflowX + ' ' + cs.overflowY)) continue;
      const r = firstBox(el), box = a.getBoundingClientRect(), s = Z * state.k;   // client px per px of the element's own scroll
      if (r.top < box.top) a.scrollTop -= (box.top - r.top) / s; else if (r.bottom > box.bottom) a.scrollTop += (r.bottom - box.bottom) / s;
      if (r.left < box.left) a.scrollLeft -= (box.left - r.left) / s; else if (r.right > box.right) a.scrollLeft += (r.right - box.right) / s;
    }
    const r = firstBox(el), cx = (r.left + r.right) / 2, cy = (r.top + r.bottom) / 2;
    const p = fromClient({ left: cx, top: cy, right: cx, bottom: cy }, true);
    const f = frameRect({ x: p.x - 0.5, y: p.y - 0.5, w: 1, h: 1 });
    const b = fromClient(r, true), o = origin(), s = Z * state.k, FW = W * Z, FH = H * Z;
    const x0 = Z * o.x + s * (b.x - o.x - state.x), y0 = Z * o.y + s * (b.y - o.y - state.y), x1 = x0 + s * b.w, y1 = y0 + s * b.h;   // the line on the frame, not clipped to it
    const fits = x1 - x0 <= FW - 2 * clear && y1 - y0 <= FH - 2 * clear;
    const shown = !fits || (x0 >= clear && y0 >= clear && x1 <= FW - clear && y1 <= FH - clear);
    return { x: p.x, y: p.y, inside: !!f && f[0] >= edge && f[1] >= edge && f[0] <= FW - edge && f[1] <= FH - edge && shown };
  };
  // Where the camera would stand with a page point in the middle of the frame, at the zoom it has (clamped to the page).
  const around = (x, y) => {
    const page = pageSize(), k = state.k;
    return { x: Math.max(0, Math.min(x - W / k / 2, page.w - W / k)), y: Math.max(0, Math.min(y - H / k / 2, page.h - H / k)), k };
  };
  const nearer = (x, y) => { const to = around(x, y); return Math.abs(to.x - state.x) >= 0.5 || Math.abs(to.y - state.y) >= 0.5; };
  const centre = (x, y, seconds) => { const to = around(x, y); return apply(to.x, to.y, to.k, seconds); };
  window.__cam = { focus, region, reset, rect, apply, state, pageSize, frameRect, targetRect, lastMove, mark, fromClient, frameText, elementText, fold, reveal, nearer, centre };
})();`;

// Playwright's click()/fill() scroll the target into view, which fights the camera transform. Dispatch instead.
// What a storyboard gets as tap: Recorder.tap (below). Since 1.6.0 that is a press with the real mouse under a
// pointer the video shows; with --no-pointer it is the click event, sent to the element, of the versions before.
const tap = (locator, opts) => rec.tap(locator, opts);

// A box of frame pixels as the camlog keeps it: integers, edges rounded outwards, cut to the frame; null when none of it is on the frame.
const frameBox = (x, y, w, h) => {
  const x0 = Math.max(0, Math.floor(x)), y0 = Math.max(0, Math.floor(y)), x1 = Math.min(W, Math.ceil(x + w)), y1 = Math.min(H, Math.ceil(y + h));
  return x1 > x0 && y1 > y0 ? [x0, y0, x1 - x0, y1 - y0] : null;
};

// An address as the camlog keeps it: no query and no fragment (they can carry tokens).
const plainUrl = address => {
  try { const u = new URL(address); return (u.origin === 'null' ? u.protocol + '//' : u.origin) + u.pathname; } catch { return String(address).split(/[?#]/)[0]; }
};

class Recorder {
  constructor(page, name) { this.page = page; this.name = name; this.log = []; this.t0 = Date.now(); this.lastShot = 0; this.lastKey = ''; this.texts = []; this.lastText = null;
    this.pointerOn = pointerOn; this.pointerAt = null; this.cameraStops = 0; }
  /** The text the frame shows (window.__cam.frameText); null when the page has no camera (before install, after a
   *  reload) or cannot be read now. A capture that fails adds nothing and stops nothing. */
  async frameText() { return this.page.evaluate('window.__cam.frameText()').then(v => (typeof v === 'string' ? v : null), () => null); }
  keep(kind, key, text, t = this.now()) { this.texts.push({ t: +t.toFixed(2), kind, key, text }); }
  /** Keep the text the frame shows now, under `key` (a "text" entry of <name>.frametext.txt). For a screen that
   *  changes while the camera stays: a result that arrived, a terminal that printed. Returns the text, or null. */
  async text(key) {
    const text = await this.frameText();
    if (text !== null) { this.keep('text', key, text); this.lastText = text; }
    return text;
  }
  now() { return (Date.now() - this.t0) / 1000; }
  note(kind, data = {}, t = this.now()) { this.log.push({ t: +t.toFixed(2), kind, ...data }); }
  /** Put the camera into the page. From the first call on, every later document of this tab gets it by itself (its
   *  top frame only, once the document's <head> is there), so a link that loads a page does not lose the camera; each
   *  such load is a "load" entry in the camlog. Calling it again is harmless. */
  async install() {
    if (!this.installed) {
      this.installed = true;
      await this.page.addInitScript(`if (window.top === window) { const install = () => { ${CAMERA_JS} }; `
        + `if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install); else install(); }`);
      // at DOMContentLoaded, when the init script has put the camera in: a storyboard that waits for a selector and
      // takes its shot may be done long before the page's last picture has loaded
      this.page.on('domcontentloaded', () => { this.onPageEvent({ kind: 'load' }).catch(() => {}); });
    }
    await this.page.evaluate(CAMERA_JS);
  }
  async shot(key, fn, label) {
    // the view this shot leaves, as it is just before the camera moves on: results arrive after a shot, not with it
    if (this.lastKey !== '' && !this.viewGone) {   // a view that a new page replaced has nothing left to keep
      const left = await this.frameText();
      if (left !== null && left !== this.lastText) { this.keep('leave', this.lastKey, left); this.lastText = left; }
    }
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
    this.cameraStops = missing || result?.error ? t : t + move;   // a press waits for the camera to stop (tap, hover)
    this.note('shot', { key, label, camera: result, ...(rect ? { rect } : {}), ...(move !== CAMERA_MOVE ? { move } : {}),
                        ...(missing ? { missing: true } : {}) }, t);
    if (missing) console.warn(`[${this.now().toFixed(1)}s] shot ${key}: selector matched nothing, camera unchanged`);
    else console.log(`[${this.now().toFixed(1)}s] shot ${key}${label ? ' — ' + label : ''}`);
    const text = await this.frameText();   // what the frame shows once the camera has stopped, under the shot's own time
    if (text !== null) { this.keep('shot', key, text, t); this.lastText = text; }
    this.viewGone = false;
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
    const text = found?.found
      ? await this.page.evaluate(`window.__cam.elementText(${JSON.stringify(selector)}, ${Number(index)})`).catch(() => null) : null;
    return this.markRect(key, found?.found ? found.rect ?? undefined : null, label, `selector ${selector} matched nothing`, undefined, text);
  }
  /** The same for a rectangle already in frame pixels (term.mjs markRows). rect null: nothing to mark; error: the
   *  browser's words, kept in the entry; text: the marked thing's own text, kept as a "mark" entry of the frame text. */
  async markRect(key, rect, label, whyMissing = 'nothing to mark', error, text) {
    const missing = rect === null, t = this.now();
    this.note('mark', { key, label, ...(rect ? { rect } : {}), ...(missing ? { missing: true } : {}), ...(error ? { error } : {}) }, t);
    if (!missing && typeof text === 'string') this.keep('mark', key, text, t);
    if (missing) console.warn(`[${this.now().toFixed(1)}s] mark ${key}: ${whyMissing}`);
    else console.log(`[${this.now().toFixed(1)}s] mark ${key}${label ? ' — ' + label : ''}`);
    return missing ? null : rect;
  }
  async reset(key = 'wide', label) { return this.shot(key, 'window.__cam.reset()', label); }
  since() { return this.now() - this.lastShot; }

  // ---- presses (1.6.0; references/pointer.md)
  /** Where a press on the locator's first element lands, measured now, live: the centre of its first line box (a link
   *  wrapped over two lines has its bounding box's centre outside itself), that box on the frame, and the element's own
   *  text. The frame's pixels are worked out in the page, climbing from the element's own document through every
   *  iframe that holds it (each drawn at its own scale: the layout zoom, the camera's zoom); Playwright's boundingBox()
   *  serves only for a frame of another origin, which cannot be climbed. null: the element has no box (hidden, gone). */
  async pressSpot(locator) {
    const el = locator.first();
    const own = await el.evaluate((node, max) => {
      const all = node.getBoundingClientRect();
      if (all.width < 1 && all.height < 1) return null;
      const first = [...node.getClientRects()].find(r => r.width >= 1 && r.height >= 1) ?? all;
      const field = ['INPUT', 'TEXTAREA', 'SELECT'].includes(node.tagName);
      const said = field ? (node.type === 'password' ? '' : node.value ?? '') : (node.innerText ?? node.textContent ?? '');
      let x = first.left, y = first.top, w = first.width, h = first.height, climbed = true;
      try {
        for (let win = window; win !== win.parent; win = win.parent) {
          const frame = win.frameElement, r = frame.getBoundingClientRect();
          const sx = r.width / (frame.offsetWidth || r.width), sy = r.height / (frame.offsetHeight || r.height);
          x = r.left + (frame.clientLeft + x) * sx; y = r.top + (frame.clientTop + y) * sy; w *= sx; h *= sy;
        }
      } catch (e) { climbed = false; }
      return { x, y, w, h, climbed, framed: window.top !== window, dx: first.left - all.left, dy: first.top - all.top, fw: first.width, fh: first.height,
               aw: all.width, cx: first.left + first.width / 2, cy: first.top + first.height / 2, text: String(said).replace(/\s+/g, ' ').trim().slice(0, max) };
    }, POINTER.text).catch(() => null);
    if (!own) return null;
    let { x, y, w, h } = own;
    if (!own.climbed) {   // a frame of another origin: Playwright's box of the element, with the first line's place inside it
      const box = await el.boundingBox().catch(() => null);
      if (!box) return null;
      const scale = box.width / (own.aw || box.width);
      x = box.x + own.dx * scale; y = box.y + own.dy * scale; w = own.fw * scale; h = own.fh * scale;
    }
    const point = [Math.round((x + w / 2) * 10) / 10, Math.round((y + h / 2) * 10) / 10];
    // within: the same point in the element's own document, for the covered check there; framed: it is inside an iframe
    return { point, within: [own.cx, own.cy], framed: own.framed, rect: frameBox(x, y, w, h), text: own.text,
             outside: !(point[0] >= 0 && point[0] <= W && point[1] >= 0 && point[1] <= H) };
  }
  /** Bring a press target into the frame and measure it. The camera comes to rest first (a box measured while it
   *  moves is not where it will be); then the element's scrolling ancestors are scrolled to it and, when the frame
   *  would not show it whole and clear of its edges, the camera pans (a "shot" of key pan; none when the camera cannot get
   *  nearer) and comes to rest again; then the spot is measured. Revealing and panning happen only in the top frame
   *  and with the camera on the page. null: the element has no box by then. */
  async approach(locator, opts) {
    await this.cameraAtRest();
    const seen = await locator.first().evaluate((node, [edge, clear]) => (window.top === window && window.__cam ? window.__cam.reveal(node, edge, clear) : null), [POINTER.edge, POINTER.clear])
      .catch(() => null);
    if (seen && !seen.inside && await this.page.evaluate(([x, y]) => window.__cam.nearer(x, y), [seen.x, seen.y]).catch(() => false)) {
      await this.shot('pan', `window.__cam.centre(${seen.x}, ${seen.y}, ${POINTER.pan})`, opts.label ?? opts.key);
      await this.cameraAtRest();
    }
    return this.pressSpot(locator);
  }
  /** What lies on top of the spot now, when it is not the element or something inside it: 'tag#id.class', else null.
   *  Asked at the last moment before the mouse goes down: a page can move under the pointer while it travels and
   *  while the press mark opens. For an element inside an iframe the top document is asked too: the point must lie
   *  on an iframe there, or the press would go to whatever of the outer page is drawn at it. */
  async coveredBy(locator, spot) {
    const name = `top => top.tagName.toLowerCase() + (top.id ? '#' + top.id : '') + (typeof top.className === 'string' ? top.className.trim().split(/\\s+/).filter(Boolean).map(c => '.' + c).join('') : '')`;
    if (spot.framed) {
      const outer = await this.page.evaluate(`(() => { const top = document.elementFromPoint(${spot.point[0]}, ${spot.point[1]}); return !top ? 'nothing' : /^I?FRAME$/.test(top.tagName) ? null : (${name})(top); })()`)
        .catch(() => null);
      if (outer) return outer;
    }
    return locator.first().evaluate((node, [x, y, describe]) => {
      let top = document.elementFromPoint(x, y);
      for (;;) {
        if (!top) return 'nothing';
        if (top === node || node.contains(top)) return null;
        const deeper = top.shadowRoot && top.shadowRoot.elementFromPoint(x, y);
        if (!deeper || deeper === top) break;
        top = deeper;
      }
      return (0, eval)(describe)(top);
    }, [...spot.within, name]).catch(() => null);
  }
  /** Take the drawn pointer and the real mouse to a frame point, together: the pointer by its own transition, the mouse
   *  in steps of about 40 ms along the same line, so that what lies on the way is hovered as a person's mouse would. */
  async pointerTo([x, y]) {
    const page = this.page;
    await page.evaluate(pointerJs(Z));
    let from = this.pointerAt;
    if (from) {
      await page.evaluate(([a, b]) => { if (!window.__demoPointer.at()) window.__demoPointer.place(a, b); window.__demoPointer.raise(); }, from);
    } else {
      from = [Math.round(W * POINTER.start[0]), Math.round(H * POINTER.start[1])];
      await page.evaluate(([a, b]) => window.__demoPointer.place(a, b), from);
      await page.mouse.move(from[0], from[1]);
      await this.sleep(POINTER.appear * 1000);
    }
    const seconds = travelSeconds(Math.hypot(x - from[0], y - from[1]));
    await page.evaluate(([a, b, s]) => window.__demoPointer.move(a, b, s), [x, y, seconds]);
    const steps = Math.max(2, Math.round(seconds / 0.04));
    for (let i = 1; i <= steps; i++) {
      await page.mouse.move(from[0] + (x - from[0]) * i / steps, from[1] + (y - from[1]) * i / steps);
      await this.sleep(seconds * 1000 / steps);
    }
    this.pointerAt = [x, y];
  }
  /** Until the camera has stopped: a press is measured in the frame as it is, not as it will be. */
  async cameraAtRest() { const wait = this.cameraStops - this.now(); if (wait > 0) await this.sleep(wait * 1000 + 60); }
  /** Press the locator's first element: the pointer travels to it, a press mark shows, the real mouse goes down and
   *  up. opts: key, label (kept in the camlog's "tap" entry; anchor a beat with "tap:<key>"). A press never stops a
   *  take: what the mouse cannot press gets the click as an event, a warning and a flag in its entry. */
  async tap(locator, opts = {}) {
    const el = locator.first();
    await el.waitFor({ state: 'visible' });
    if (!this.pointerOn) { await el.dispatchEvent('click'); return; }
    const spot = await this.approach(locator, opts);
    const name = opts.key ?? spot?.text ?? '';
    if (!spot || spot.outside) {   // no box any more, or the camera cannot show it: no pointer goes there
      await el.dispatchEvent('click').catch(() => {});
      this.note('tap', { ...this.named(opts), ...(spot?.rect ? { rect: spot.rect } : {}), ...(spot ? { point: spot.point, text: spot.text } : {}), outside: true });
      console.warn(`[${this.now().toFixed(1)}s] tap ${name}: ${spot ? 'outside the frame' : 'no longer on the page'}, sent as a click event`);
      return;
    }
    await this.pointerTo(spot.point);
    const sameTab = await this.keepInTab(locator);
    await this.page.evaluate(([a, b]) => window.__demoPointer.ring(a, b), spot.point).catch(() => {});
    await this.sleep(POINTER.pressLead * 1000);
    const covered = await this.coveredBy(locator, spot);   // now, not when the pointer arrived: the page had 0.2 s more to move
    const t = this.now();
    if (covered) {        // a real press here would press what covers it: the click goes to the element as the event
      await el.dispatchEvent('click').catch(() => {});
    } else {
      await this.page.mouse.down();
      await this.sleep(POINTER.pressHold * 1000);
      await this.page.mouse.up();
    }
    this.note('tap', { ...this.named(opts), rect: spot.rect, point: spot.point, text: spot.text, ...(covered ? { covered } : {}),
                       ...(sameTab ? { same_tab: true } : {}) }, t);
    if (covered) console.warn(`[${t.toFixed(1)}s] tap ${name}: covered by ${covered}, sent as a click event`);
    else console.log(`[${t.toFixed(1)}s] tap ${name}`);
  }
  /** Take the pointer to the locator's first element and leave it there (a menu that opens on hover). */
  async hover(locator, opts = {}) {
    if (!this.pointerOn) {
      if (!this.hoverSaid) console.warn('hover does nothing without the pointer (--no-pointer)');
      this.hoverSaid = true;
      return;
    }
    await locator.first().waitFor({ state: 'visible' });
    const spot = await this.approach(locator, opts);
    const name = opts.key ?? spot?.text ?? '';
    if (!spot || spot.outside) {
      this.note('hover', { ...this.named(opts), ...(spot?.rect ? { rect: spot.rect } : {}), ...(spot ? { point: spot.point } : {}), outside: true });
      console.warn(`[${this.now().toFixed(1)}s] hover ${name}: ${spot ? 'outside the frame' : 'no longer on the page'}, the pointer did not go there`);
      return;
    }
    await this.pointerTo(spot.point);
    const covered = await this.coveredBy(locator, spot);
    this.note('hover', { ...this.named(opts), rect: spot.rect, point: spot.point, ...(covered ? { covered } : {}) });
    if (covered) console.warn(`[${this.now().toFixed(1)}s] hover ${name}: covered by ${covered}`);
    else console.log(`[${this.now().toFixed(1)}s] hover ${name}`);
  }
  /** A take records one tab: a link, an area or a form that would open another (its own "target", a button's
   *  "formtarget", or the page's <base target>) is made to open in this one, just before the press. True when it was. */
  async keepInTab(locator) {
    return locator.first().evaluate(node => {
      const elsewhere = v => !!v && !['_self', '_top', '_parent'].includes(v.toLowerCase());
      const owner = node.closest('a, area, form');
      let changed = false;
      if (owner && elsewhere(owner.getAttribute('target'))) { owner.removeAttribute('target'); changed = true; }
      if (elsewhere(node.getAttribute('formtarget'))) { node.removeAttribute('formtarget'); changed = true; }
      if (owner && !owner.hasAttribute('target') && elsewhere(document.querySelector('base[target]')?.getAttribute('target'))) { owner.setAttribute('target', '_self'); changed = true; }
      return changed;
    }).catch(() => false);
  }
  /** After a new document (or a swapped body): the pointer again where it last was, once it has been shown. */
  async pointerBack() {
    if (!this.pointerOn || !this.pointerAt) return;
    await this.page.evaluate(pointerJs(Z)).catch(() => {});
    await this.page.evaluate(([a, b]) => { if (!window.__demoPointer.at()) window.__demoPointer.place(a, b); }, this.pointerAt).catch(() => {});
  }
  named({ key, label } = {}) { return { ...(key !== undefined ? { key } : {}), ...(label !== undefined ? { label } : {}) }; }
  /** What the page says about itself, through the __demoEvent binding. scroll: the camera has taken a window scroll
   *  into its own position (fold). The frame is where the window scrolled to: a view of its own from here on, written
   *  as a shot of key "scroll" that takes no time, with its frame text like any shot's. load: see install(). */
  async onPageEvent(event) {
    if (event?.kind === 'load') {   // a new document in the tab, or (soft) a swapped <body>: the camera is back, wide
      this.note('load', { url: plainUrl(this.page.url()), ...(event.soft ? { soft: true } : {}) });
      this.viewGone = true;
      console.log(`[${this.now().toFixed(1)}s] load ${plainUrl(this.page.url())}${event.soft ? ' (the body was swapped)' : ''}`);
      await this.pointerBack();
      return;
    }
    if (event?.kind !== 'scroll') return;
    // a window that keeps scrolling (a log that follows its end, a carousel) is one view, not one per scroll: while
    // nothing else was written since the last scroll shot, that entry takes the camera's new place and the new text
    const last = this.log[this.log.length - 1];
    if (last && last === this.scrolled?.shot) {
      last.camera = event.camera;
      this.cameraStops = this.now();
      const again = await this.frameText();
      if (again !== null) { if (this.scrolled.text) this.scrolled.text.text = again; this.lastText = again; }
      return;
    }
    const t = this.lastShot = this.now();
    this.lastKey = 'scroll';
    this.cameraStops = t;
    this.note('shot', { key: 'scroll', camera: event.camera, move: 0 }, t);
    this.scrolled = { shot: this.log[this.log.length - 1], text: null };
    console.log(`[${t.toFixed(1)}s] shot scroll — the window scrolled and the camera took it`);
    const text = await this.frameText();
    if (text !== null) { this.keep('shot', 'scroll', text, t); this.scrolled.text = this.texts[this.texts.length - 1]; this.lastText = text; }
  }
  async sleep(ms) { await this.page.waitForTimeout(ms); }
}

// ---------------------------------------------------------------- main
const browser = await chromium.launch({ headless: true, args: ['--disable-dev-shm-usage', '--autoplay-policy=no-user-gesture-required'] });
// bypassCSP: a site's Content-Security-Policy would block the camera's <style> (a style-src without inline styles: the
// transform then turns around the wrong corner) and, with Trusted Types, the pointer. The recorder is not the page.
const context = await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: 1, acceptDownloads: true, bypassCSP: true, recordVideo: { dir: outDir, size: { width: W, height: H } } });
const page = await context.newPage();
page.setDefaultTimeout(30000);
const errors = [];
page.on('pageerror', e => errors.push(e.message));
const rec = new Recorder(page, name);
// the page reports to the recorder through one binding; only its top frame is listened to
// A dialog (alert, confirm, prompt, beforeunload) is not drawn in the video, and with nobody listening the browser
// dismisses it: a button that asks "Really?" then does nothing, without a word. The recorder answers it (--dialogs
// accept, the default, or dismiss) and writes a "dialog" entry; --dialogs leave: the recorder does not listen. When
// the storyboard listens itself the recorder only writes it down: a second answer to one dialog is an error.
if (dialogs !== 'leave') {
  page.on('dialog', async dialog => {
    const own = page.listenerCount('dialog') > 1;
    const message = dialog.message().slice(0, 200);
    rec.note('dialog', { type: dialog.type(), message });
    console.warn(`[${rec.now().toFixed(1)}s] dialog (${dialog.type()}) ${own ? 'left to the storyboard' : dialogs === 'accept' ? 'accepted' : 'dismissed'}: ${message}`);
    if (!own) await (dialogs === 'accept' ? dialog.accept() : dialog.dismiss()).catch(() => {});
  });
}
// A take records one tab. Another tab the page opens is closed (with the video file Playwright started for it) and
// written down as a "popup" entry, unless the storyboard listens for it itself: then it is only written down.
context.on('page', async other => {
  if (other === page || !(await other.opener().catch(() => null))) return;   // only a tab the page opened; the storyboard's own stay
  const kept = page.listenerCount('popup') > 0 || context.listenerCount('page') > 1;
  await other.waitForLoadState('domcontentloaded', { timeout: 5000 }).catch(() => {});
  const url = plainUrl(other.url());
  rec.note('popup', { url });
  if (kept) return;
  console.warn(`[${rec.now().toFixed(1)}s] the page opened another tab (${url}): a take records one tab, open it with page.goto to show it`);
  const film = other.video();
  await other.close().catch(() => {});
  if (film) await film.delete().catch(() => {});
});
await page.exposeBinding('__demoEvent', (source, event) => (source.frame === page.mainFrame() ? rec.onPageEvent(event).catch(() => {}) : undefined));
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
  await fs.writeFile(path.join(outDir, `${name}.frametext.txt`), formatFrametext(rec.texts));
  await fs.writeFile(path.join(outDir, `${name}.camlog.json`), JSON.stringify({ name, url: siteUrl, layout, ok, errors, duration_s: rec.now(), log: rec.log }, null, 2));
  await browser.close();
  console.log(JSON.stringify({ video: target, ok, seconds: rec.now(), errors: errors.length }));
}
process.exit(ok ? 0 : 1);
