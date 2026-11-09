// Terminal scenes: helpers for a storyboard that drives a CLI (Claude Code, any TUI) inside a browser terminal served by
// ttyd, so record_demo.mjs can film it with the same in-page camera. Import from your storyboard:
//   import { openTerminal, run, type, paste, waitFor, waitPrompt, zoomRows } from '<plugin>/scripts/term.mjs';
// Serve the shell on loopback only (a writable shell on 0.0.0.0 is a hole):  ttyd -i lo -p 7681 -W bash
// then record with  node record_demo.mjs --url http://127.0.0.1:7681 --storyboard ./storyboard.mjs
// Notes (1.3.0): ttyd's own -t options may be dropped (its JSON breaks), so the page sets xterm options itself; the DOM
// renderer keeps text crisp under the camera zoom; xterm's fit over-estimates columns for some fonts, so the glyph
// advance is measured and the terminal resized; TUI dialogs render at the bottom, so a narrower terminal (cols) keeps
// them inside the zoom; keyboard.type drops Hangul, so text goes through xterm's paste path.

export const TERM_URL = 'http://127.0.0.1:7681/';

export async function openTerminal(page, siteUrl = TERM_URL, { fontSize = 22, cols: wantCols = 0, font = 'NanumGothicCoding, DejaVu Sans Mono, monospace', background = '#0b0f14' } = {}) {
  await page.goto(siteUrl, { waitUntil: 'load' });
  await page.waitForSelector('.xterm', { timeout: 15000 });
  await page.waitForTimeout(1500);
  await page.evaluate(([fs, ff, bg]) => {
    const t = window.term;
    t.setOption('rendererType', 'dom'); t.setOption('fontSize', fs); t.setOption('lineHeight', 1.1);
    t.setOption('fontFamily', ff); t.setOption('cursorBlink', false);
    t.setOption('theme', { background: bg, foreground: '#e8edf2', cursor: '#e8edf2', selection: '#2a3a55' });
    window.dispatchEvent(new Event('resize'));
  }, [fontSize, font, background]);
  await page.waitForTimeout(600);
  await page.evaluate((wantCols) => {
    const t = window.term; const probe = document.createElement('span');
    probe.style.cssText = 'position:absolute;visibility:hidden;white-space:pre;left:0;top:0';
    probe.style.fontFamily = t.getOption('fontFamily'); probe.style.fontSize = t.getOption('fontSize') + 'px';
    probe.textContent = 'M'.repeat(100); document.body.appendChild(probe);
    const cw = probe.getBoundingClientRect().width / 100; probe.remove();
    let cols = Math.floor((window.innerWidth - 20) / cw);
    if (wantCols > 0) cols = Math.min(cols, wantCols);
    if (cw > 1 && cols < t.cols) t.resize(cols, t.rows);
    window.__termCols = { cw, cols: t.cols, rows: t.rows };
  }, wantCols);
  await page.waitForTimeout(500);
  console.log('terminal', JSON.stringify(await page.evaluate(() => window.__termCols)));
}

/** Visible lines (DOM renderer). */
export const screenText = page => page.evaluate(() => [...document.querySelectorAll('.xterm-rows > div')].map(d => d.textContent.replace(/\s+$/, '')).join('\n'));

/** Send text through xterm's paste path (Hangul and other IME text survive; keyboard.type drops them). */
export const paste = (page, text) => page.evaluate(t => window.term.paste(t), text);

/** One shell line: paste, then Enter. */
export async function run(page, line) { await paste(page, line); await page.waitForTimeout(250); await page.keyboard.press('Enter'); }

/** Type slowly like a person (ASCII only). */
export async function type(page, text, delay = 55) { await page.keyboard.type(text, { delay }); }

/** Wait until text shows on screen; returns true/false. */
export async function waitFor(page, needle, timeoutMs = 60000) {
  const t0 = Date.now();
  while (Date.now() - t0 < timeoutMs) {
    if ((await screenText(page)).includes(needle)) return true;
    await page.waitForTimeout(300);
  }
  console.warn(`waitFor timed out: ${JSON.stringify(needle)}`);
  return false;
}

/** Claude Code's input prompt (❯). */
export const waitPrompt = (page, timeoutMs = 90000) => waitFor(page, '❯', timeoutMs);

/** Rows containing the needles (first..last) as a page rectangle, in untransformed page coordinates. */
export async function rowsRect(page, firstNeedle, lastNeedle) {
  return page.evaluate(([a, b]) => {
    const rows = [...document.querySelectorAll('.xterm-rows > div')];
    const i = rows.findIndex(r => r.textContent.includes(a));
    let j = rows.length - 1;
    for (let k = rows.length - 1; k >= 0; k--) if (rows[k].textContent.includes(b)) { j = k; break; }
    if (i < 0) return null;
    const m = new DOMMatrix(getComputedStyle(document.body).transform).inverse();
    const un = (x, y) => { const p = m.transformPoint(new DOMPoint(x + window.scrollX, y + window.scrollY)); return [p.x, p.y]; };
    const ra = rows[i].getBoundingClientRect(), rb = rows[Math.max(i, j)].getBoundingClientRect();
    const [x0, y0] = un(ra.left, ra.top), [x1, y1] = un(ra.right, rb.bottom);
    return { x: x0, y: y0, w: x1 - x0, h: y1 - y0 };
  }, [firstNeedle, lastNeedle]);
}

/** Zoom the camera onto the rows between two needles; falls back to a wide shot when the text is not on screen. */
export async function zoomRows(rec, page, key, firstNeedle, lastNeedle, opts = {}, label) {
  const r = await rowsRect(page, firstNeedle, lastNeedle);
  if (!r) { console.warn(`zoomRows: ${firstNeedle} not on screen`); return rec.reset(key, label); }
  const w = Math.min(r.w, opts.maxW ?? 1900);  // never crop the right edge of wrapped lines
  return rec.region(key, r.x, r.y, w, r.h, { pad: opts.pad ?? 28, kmax: opts.kmax ?? 1.6, anchorTop: true }, label);
}
