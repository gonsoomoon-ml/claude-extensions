/**
 * deck-build example — three slides that cover the three shapes most decks need:
 *   1. cover            2. comparison table            3. boundary diagram
 *
 *   npm install pptxgenjs                       # only if require() fails
 *   python ../scripts/gradient_bg.py assets/bg.png
 *   node example_deck.js                        # → out/example.pptx
 *   python ../scripts/qa.py out/example.pptx
 */
const path = require("path");
const pptxgen = require("pptxgenjs");
const S = require("../scripts/style.js");

const HERE = __dirname;
const BG = path.join(HERE, "assets", "bg.png");
if (require("fs").existsSync(BG)) S.useBackgroundImage(BG); // falls back to a flat dark fill

const pres = S.deck(pptxgen, { author: "deck-build", title: "example" });
const { T } = S;

/* ── 1. cover ─────────────────────────────────────────────────────────── */
{
  const s = S.slide(pres);
  S.eyebrow(s, "Section label — what this deck is about", { y: 1.05, size: T.MID });
  s.addText("The claim the deck argues", {
    isTextBox: true, margin: 0, x: T.MARGIN, y: 1.55, w: 11.7, h: 0.75,
    fontFace: T.FONT, fontSize: 40, bold: true, color: T.TEXT,
  });
  S.eyebrow(s, "The one sentence a listener repeats afterwards", { y: 2.45, color: T.MUTED, size: 24 });
  S.eyebrow(s, "2026-09-30", { y: 4.5, color: T.MUTED, size: T.MID });
  s.addText("Presenter Name", {
    isTextBox: true, margin: 0, x: T.MARGIN, y: 4.95, w: 6, h: 0.4,
    fontFace: T.FONT, fontSize: T.MID, bold: true, color: T.TEXT,
  });
  S.eyebrow(s, "name@example.com", { y: 5.4, color: T.MUTED });
  s.addNotes("Cover: say the claim, then the takeaway line. Do not read the deck title.");
}

/* ── 2. comparison table ──────────────────────────────────────────────── */
{
  const s = S.slide(pres);
  S.title(s, "Two ways to do it — what actually differs");
  S.eyebrow(s, "Assumptions · replace with the customer's numbers in the first workshop", { y: 1.0, color: T.SECOND });
  S.table(
    s,
    [
      ["", "Today", "Proposed"],
      ["Can start now", "0 — everything blocked", "40 — where data has no constraint"],
      ["On-prem hardware", "all 100 cases", "25 — only data that cannot leave"],
      ["Keys handed out", "one per system and person", "none"],
    ],
    { y: 1.6, colW: [3.2, 3.6, 4.9] },
  );
  S.takeaway(s, "A quarter of the hardware, and it starts this quarter", { y: 5.4 });
  S.source(s, "Numbers are assumptions until the first workshop replaces them.");
  s.addNotes("Read the table row by row. The last row is the one to pause on.");
}

/* ── 3. boundary diagram ──────────────────────────────────────────────── */
{
  const s = S.slide(pres);
  S.title(s, "Three paths, one set of controls");

  // The boundary is a constant — every box position derives from it, so nothing can cross by accident.
  const WALL = 7.3;
  const CLEAR = 0.3; // breathing room so the box never touches the boundary
  const LEFT_BOX = { x: 4.0, w: WALL - 4.0 - CLEAR }; // stays left of the wall by construction
  const RIGHT_BOX = { x: WALL + 0.5, w: 3.9 };

  S.boundary(pres, s, { x: WALL, y: 1.35, h: 4.3 });
  S.eyebrow(s, "On premises", { y: 1.0, color: T.MUTED });
  s.addText("Cloud", {
    isTextBox: true, margin: 0, x: WALL + 0.5, y: 1.0, w: 3, h: 0.35,
    fontFace: T.FONT, fontSize: T.BODY, color: T.MUTED,
  });

  const rows = [
    { n: "1", label: "Design team", box: LEFT_BOX, model: "Model inside the building", note: "nothing crosses" },
    { n: "2", label: "Quality team", box: RIGHT_BOX, model: "Managed model service", note: "direct call" },
    { n: "3", label: "App team", box: RIGHT_BOX, model: "Managed model service", note: "through the gateway" },
  ];

  rows.forEach((r, i) => {
    const y = 1.75 + i * 1.4;
    s.addText(`${r.n}  ${r.label}`, {
      isTextBox: true, margin: 0, x: T.MARGIN, y: y + 0.08, w: 2.8, h: 0.4,
      fontFace: T.FONT, fontSize: 16, bold: true, color: T.TEXT,
    });
    const x0 = 3.6;
    S.arrow(pres, s, { x: x0, y: y + 0.28, w: r.box.x - x0 - 0.05, color: i === 0 ? T.SECOND : T.ACCENT });
    S.card(pres, s, { x: r.box.x, y: y - 0.05, w: r.box.w, h: 0.72 });
    s.addText(r.model, {
      isTextBox: true, margin: 0, x: r.box.x + 0.18, y: y - 0.02, w: r.box.w - 0.3, h: 0.35,
      fontFace: T.FONT, fontSize: 14, bold: true, color: T.TEXT,
    });
    s.addText(r.note, {
      isTextBox: true, margin: 0, x: r.box.x + 0.18, y: y + 0.3, w: r.box.w - 0.3, h: 0.32,
      fontFace: T.FONT, fontSize: 11, color: T.MUTED,
    });
  });

  S.takeaway(s, "Where the model runs changes; how it is governed does not", { y: 6.2 });
  s.addNotes("Read all three rows the same way: team on the left, model on the right.");
}

pres
  .writeFile({ fileName: path.join(HERE, "out", "example.pptx") })
  .then((f) => console.log("written", f));
