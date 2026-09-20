---
name: deck-build
description: Turn locked slide content into a real .pptx in the deck-mindset house style — a token module, build script patterns, and a validate → render → inspect QA loop. Use when the output must be an actual PowerPoint file (dark-background decks, Korean or English), or when an existing build needs restyling.
---

# Deck Build

`deck-mindset` says *what* a good slide is. `deck-agent-team` says *whether* a finished deck holds up.
This skill covers the step between them: **producing the file**.

It exists because the failures in that step are boring, repeatable, and expensive — a box that crosses a
boundary it was supposed to respect, a gradient that silently corrupts the package, a Korean filename that
python-pptx refuses to open, a font that renders fine in QA and overflows on the presenter's laptop.

## The pipeline

Never start at the file. Five steps, in order:

| # | Step | Output | Stop if |
|---|---|---|---|
| 1 | **Lock the content** | Plain-text or ASCII mock per slide, approved one at a time | Wording still moving |
| 2 | **Lock the tokens** | Colors + type scale + canvas, written down once | More than 5 deck colors, or a 4th type size |
| 3 | **Build** | `.pptx` from a script — never hand-placed shapes | Any literal hex with `#`, any shared options object |
| 4 | **File QA** | Schema/relationship validation passes | Validator reports anything |
| 5 | **Visual QA** | Every slide rendered to an image and *looked at* | You are reading the code instead of the render |

Step 1 is not optional. Building before the text is final means every wording change costs a rebuild,
a re-render, and a re-read. A deck whose content is locked builds once.

## Style tokens

Write them at the top of the build script, use them everywhere, never inline a literal color again.

```js
const KR      = "Noto Sans CJK KR";  // Korean-safe face, present in most Linux/QA images
const BG      = "060B1A";            // deep navy — the dark surface deck-mindset assumes
const TEXT    = "EAF0FF";            // primary text
const ACCENT  = "FF40FF";            // the one focal color — subject of the slide
const SECOND  = "2BD9C7";            // structure labels (lanes, axes) only
const MUTED   = "D6DCEA";            // captions, secondary description
const LINE    = "C9D1E3";            // card / box borders
const SURFACE = "141B30";            // card fill (glass, ~8% white over BG)

const TITLE = 30, MID = 18, BODY = 15, CITE = 10;   // max 3 sizes per slide (+ the caption exception)
// canvas: 13.333 x 7.5 in (LAYOUT_WIDE)
```

Rules that survive contact with real decks:

- **One focal color per slide.** If two things are magenta, neither is the subject.
- **15pt floor.** Anything smaller than BODY is a citation, not content.
- **No chrome.** No header bars, no footer bars, no page numbers, no accent stripe under the title.
  A source line at the bottom (CITE, MUTED) is the only furniture.
- **The CITE line is for citations, not claims.** Three kinds of small text get confused with each other,
  and only one of them belongs at 10pt:

| What it is | Where it goes | Size |
|---|---|---|
| A cue the audience must **read** — assumptions, scope, the condition a number depends on | Body area, as a sentence | **14pt or larger** |
| Something the presenter must **say** — "I built this", how a product maps to another cloud | Speaker notes (`addNotes`) | — |
| An actual **citation** — paper, blog, URL | Bottom line | 10pt |

  A claim in 10pt gray is a claim nobody reads. If it is the strongest thing on the slide — that the
  presenter built the system, that every number is an assumption — it is either spoken or it is 14pt.
- **Product names are free.** They do not count toward a slide's text budget — but everything else does.
- Both `scripts/style.js` (pptxgenjs) and the token list above encode the same vocabulary; keep them in sync
  with `../deck-mindset/color_vocabulary.md` if you re-calibrate for a different background.

## Table or cards

Both hold the same content. They differ in **where the eye stops**: a table lets it run down a column
("that whole column is zero"), a card makes it stop inside one container ("zero became forty").

| Use | When |
|---|---|
| **Table** | 5+ rows · 3+ columns · the message lives in a **column** ("all three were rejected") · the list of criteria *is* the point |
| **Cards** | 4 or fewer items · one number per item worth remembering · the presenter walks through them one at a time · items are independent, not a comparison |
| **Neither** | 7+ items — split the slide or cut |

The deciding question is not which looks better. It is **what the audience should carry out of the room**:
a *pattern* (table) or a *number* (cards).

Two traps:

- **A before/after table makes two camps.** Column heads like "current / proposed" get read as "ours
  versus the vendor's", and every number under the second head is discounted. Cards that hold
  `0 → 40` inside one container do not create sides. If you keep the table, name the columns by the
  **mechanism** that causes the difference, not by whose idea it is.
- **Cards on consecutive slides go flat.** If the previous slide is a card grid, the next one needs a
  different shape — a table, a timeline, a hero number — even when cards would work. Check the neighbours
  before choosing, and check that a timeline does not repeat the implementation-plan slide you already have.

## Building with pptxgenjs

These are the mistakes that cost a rebuild, not the API basics:

| Trap | What happens | Fix |
|---|---|---|
| `pres.layout` set after `addSlide()` | Slides silently use the 10" canvas; shapes past 10" vanish | Set layout first, once |
| `color: "#FF40FF"` or 8-digit hex | File corrupts, PowerPoint refuses to open | 6 hex digits, no `#`; use `transparency: 0-100` |
| Reusing one options object across calls | pptxgenjs mutates it to EMU in place; the second call is wrong | Build a fresh object per call |
| Gradient fill | Not supported | Render a gradient PNG (`scripts/gradient_bg.py`) and set it as the slide background |
| `rectRadius` on `rect` | Ignored | Use `roundRect` |
| `addText` without `isTextBox: true` | Screen readers announce a graphic | Always pass it |
| Text aligned to a shape at the same `x` | Looks 6-8px off | `margin: 0` on the text box |
| Notes in a text box | Print as slide content | `slide.addNotes("...")` |

Diagram slides need one extra guard: **compute boundaries, do not eyeball them.** If a wall sits at
`x = 7.3`, an on-premises box must satisfy `x + w ≤ 7.3`. Write the constant once and derive both sides
from it — a box that crosses the line it is supposed to respect is the single most common diagram defect,
and it is invisible in code review because the numbers look plausible.

## Korean decks — the specific gotchas

- **Font:** `Noto Sans CJK KR`. Ships with most Linux images, so the QA render matches what the audience sees.
  Latin-only faces (Calibri, Arial) fall back per-glyph and change line lengths.
- **QA render spacing:** LibreOffice inserts visible gaps in mixed Korean/Latin runs (`AI 를`, `6 개월째`).
  That is the renderer, not the file. Do not "fix" it by editing the text.
- **Korean filenames break python-pptx.** macOS-normalized (NFD) names raise `PackageNotFoundError`
  even though the file exists. Copy it to an ASCII name first with a shell glob:
  `cp 260908-AWS-*.pptx ref.pptx` — then open `ref.pptx`.
- **Line breaks:** Korean wraps mid-word. For a headline that must break in a specific place, use two
  text runs or two text boxes rather than relying on the wrap point.

## QA loop

```bash
node build_deck.js                                  # or python build_deck.py
python scripts/qa.py out/deck.pptx                  # validate + render + list image paths
```

`scripts/qa.py` runs the schema/relationship validation (when the Anthropic `pptx` skill is installed, it
reuses that validator), converts to PDF through LibreOffice, and writes one JPEG per slide. Then **look at
every image**. After staring at the generator you see what you intended, not what rendered.

What actually shows up in this pass, in frequency order:

1. Text overflowing its box or the slide edge
2. A shape crossing a boundary that carries meaning (the wall, a lane, a column)
3. Overlapping elements — a label sitting on top of an arrow it belongs to
4. Uneven gaps: one region cramped, another empty
5. Low-contrast text — MUTED on a light part of a gradient background

Re-render only the slides you changed, then stop. Two QA passes is normal; five means the content was not locked.

## Files

| File | Purpose |
|---|---|
| `scripts/style.js` | Tokens + slide helpers (`slide`, `title`, `eyebrow`, `card`, `bullets`, `takeaway`, `source`, `table`) for pptxgenjs |
| `scripts/gradient_bg.py` | Generates the dark gradient background PNG (Pillow) |
| `scripts/qa.py` | Validate → PDF → per-slide JPEG, prints absolute paths to inspect |
| `examples/example_deck.js` | Three slides — cover, comparison table, boundary diagram — using the helpers |
| `reference/korean-deck-notes.md` | Long-form notes: font stack, render artifacts, NFD filenames, reusing an existing deck's theme |

## Quick start

```bash
npm install pptxgenjs                     # only if require('pptxgenjs') fails
python scripts/gradient_bg.py assets/bg.png
node examples/example_deck.js             # writes out/example.pptx
python scripts/qa.py out/example.pptx
```

Then copy `examples/example_deck.js`, replace the content, and keep the helpers.

## Checklist before shipping

- [ ] Content was approved before the first build
- [ ] Every color and size comes from the token block
- [ ] One focal color per slide; nothing below the 15pt floor except citations
- [ ] Validator passes with no findings
- [ ] Every slide has been viewed as an image, not just built
- [ ] Boundary-carrying shapes verified against the constant, not by eye
- [ ] Speaker notes are in `addNotes`, not on the slide
