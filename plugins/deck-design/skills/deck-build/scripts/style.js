/**
 * deck-build — style tokens and slide helpers for pptxgenjs.
 *
 *   const pptxgen = require("pptxgenjs");
 *   const S = require("./style.js");
 *   const pres = S.deck(pptxgen);            // sets LAYOUT_WIDE before any slide is added
 *   const s = S.slide(pres);                 // background applied
 *   S.title(s, "경로는 셋, 통제는 하나입니다");
 *
 * Every value here is a token. Build scripts import them; they never inline a hex or a point size.
 */

/* ── tokens ──────────────────────────────────────────────────────────── */

const T = {
  FONT: "Noto Sans CJK KR", // Korean-safe; renders identically in LibreOffice QA
  BG: "060B1A", // deep navy surface
  TEXT: "EAF0FF", // primary text
  ACCENT: "FF40FF", // the one focal color per slide
  SECOND: "2BD9C7", // structure labels only (lanes, axes)
  MUTED: "D6DCEA", // captions, secondary description
  LINE: "C9D1E3", // card / box border
  SURFACE: "141B30", // card fill
  TITLE: 30,
  MID: 18,
  BODY: 15,
  CITE: 10,
  W: 13.333, // canvas width  (LAYOUT_WIDE)
  H: 7.5, // canvas height
  MARGIN: 0.8, // left margin used by every text block
};

/** Background image path — set once by the build script if a gradient PNG is used. */
let BG_IMAGE = null;
function useBackgroundImage(p) {
  BG_IMAGE = p;
}

/* ── deck / slide ────────────────────────────────────────────────────── */

function deck(pptxgen, { author, title } = {}) {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE"; // must precede addSlide()
  if (author) pres.author = author;
  if (title) pres.title = title;
  return pres;
}

function slide(pres) {
  const s = pres.addSlide();
  s.background = BG_IMAGE ? { path: BG_IMAGE } : { color: T.BG };
  return s;
}

/* ── text blocks ─────────────────────────────────────────────────────── */

const textBase = (over = {}) => ({
  isTextBox: true,
  margin: 0,
  fontFace: T.FONT,
  valign: "middle",
  ...over,
});

/** Slide title — top-left, one line. Keep it a claim, not a topic. */
function title(s, text, { y = 0.3 } = {}) {
  s.addText(text, textBase({
    x: T.MARGIN, y, w: T.W - T.MARGIN * 2, h: 0.6,
    fontSize: T.TITLE, bold: true, color: T.TEXT,
  }));
}

/** Small accent line above or under the title (section label, dataset line). */
function eyebrow(s, text, { y = 1.0, color = T.ACCENT, size = T.BODY } = {}) {
  s.addText(text, textBase({
    x: T.MARGIN, y, w: T.W - T.MARGIN * 2, h: 0.35,
    fontSize: size, color,
  }));
}

/** The one sentence the audience should leave with — bottom-left, above the source line. */
function takeaway(s, text, { y = 6.1, color = T.TEXT } = {}) {
  s.addText(text, textBase({
    x: T.MARGIN, y, w: T.W - T.MARGIN * 2, h: 0.6,
    fontSize: 24, bold: true, color,
  }));
}

/** Citation / assumption line — the only chrome allowed at the bottom. */
function source(s, text, { y = 7.02 } = {}) {
  s.addText(text, textBase({
    x: T.MARGIN, y, w: T.W - T.MARGIN * 2, h: 0.3,
    fontSize: T.CITE, color: T.MUTED,
  }));
}

/** Bulleted body inside a card or column. Pass an array of strings. */
function bullets(s, items, { x, y, w, h = 0.4, size = T.BODY, color = T.TEXT, gap = 0.34 } = {}) {
  items.forEach((line, i) => {
    s.addText(line, textBase({
      x, y: y + i * gap, w, h, fontSize: size, color,
    }));
  });
}

/* ── shapes ──────────────────────────────────────────────────────────── */

/** Glass card. Differentiate cards by border color or bold — never by size. */
function card(pres, s, { x, y, w, h, line = T.LINE, transparency = 25 }) {
  s.addShape(pres.ShapeType.roundRect, {
    x, y, w, h, rectRadius: 0.12,
    fill: { color: T.SURFACE, transparency },
    line: { color: line, width: 1 },
  });
}

/** Horizontal or vertical arrow between two points. */
function arrow(pres, s, { x, y, w = 0, h = 0, color = T.ACCENT, width = 1.5 }) {
  s.addShape(pres.ShapeType.line, {
    x, y, w, h,
    line: { color, width, endArrowType: "triangle" },
  });
}

/**
 * A vertical boundary that carries meaning (on-prem | cloud, before | after).
 * Returns the x it was drawn at so callers derive box positions from it instead of guessing.
 */
function boundary(pres, s, { x, y, h, color = T.ACCENT, transparency = 40 }) {
  s.addShape(pres.ShapeType.rect, {
    x, y, w: 0.045, h,
    fill: { color, transparency },
    line: { width: 0 },
  });
  return x;
}

/* ── table ───────────────────────────────────────────────────────────── */

/**
 * Comparison table: header row in ACCENT, hairline under the header, no other borders.
 * rows = [[h1, h2, ...], [c1, c2, ...], ...]
 */
function table(s, rows, { x = T.MARGIN, y, w = T.W - T.MARGIN * 2, colW, rowH = 0.68, firstColBold = true } = {}) {
  const body = rows.map((r, ri) =>
    r.map((cell, ci) => ({
      text: String(cell),
      options: {
        fontFace: T.FONT,
        fontSize: ri === 0 ? T.BODY : 16,
        bold: ri === 0 || (firstColBold && ci === 0),
        color: ri === 0 ? T.ACCENT : T.TEXT,
        valign: "middle",
      },
    })),
  );
  s.addTable(body, {
    x, y, w, colW, rowH,
    border: [
      { type: "none" }, { type: "none" },
      { type: "solid", color: "3D2A66", pt: 1 }, { type: "none" },
    ],
    margin: [6, 10, 6, 0],
  });
}

module.exports = {
  T, useBackgroundImage, deck, slide,
  title, eyebrow, takeaway, source, bullets,
  card, arrow, boundary, table,
};
