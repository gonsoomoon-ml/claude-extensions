---
name: infographic-mindset
description: Rules for a single feed-post infographic (LinkedIn or similar) that survives blurring and reposting — one message, one structure drawn as shapes, a body-text budget, a 16 px floor at feed width, one accent — plus three design schemes taken from shipped images (two-panel concept/system map, question + measured cards + bars, tension headline + structure compare + case). Use when deciding whether a post needs an image, what goes in it, or why a draft image reads as a wall of text; pair with infographic-build to produce the PNG.
---

# Infographic Mindset

An infographic is the part of the post that survives when the text is cut. The feed shows three lines, a repost shows fewer, the image shows all of it. So the image carries **one message, one structure, one example**; the post body carries the rest.

## The three tests (on the ASCII mockup, before any HTML)

1. **Three-second test** — one line is dominant (`--fs-headline`) and it is the message, not a title. Everything else is clearly smaller.
2. **Blur test** — cover the text. The shapes must still differ: one blob vs a tree, a long bar vs a short bar, two mirrored panels. Boxes that each hold a sentence are a list, not a diagram. Label shapes with two words.
3. **Budget test** — body text inside the scheme's budget (A 400 / B 450 / C 650 characters, sources excluded). When content does not fit, cut content. Never grow the canvas, never shrink the type.

## Canvas and type are fixed by the feed, not by the content

- Portrait **1080 × 1350** (4:5) by default. Landscape only **1200 × 800** (3:2), for the two-panel scheme. Taller than 4:5 is cropped in the feed; wider than 3:2 shows tiny on a phone. Do not copy a reference image's ratio, and do not reason from LinkedIn's maximum limits.
- Type floor **16 px at 1080-width equivalent**: an 1800-wide canvas needs 27 px for the same legibility. `lint.py` normalizes.
- All text near-black. Hierarchy comes from size and weight, never from gray.
- One accent family for stroke, fill, key number and headline. Neutrals do everything else. No second shade typed by hand.

## Pick a scheme, then mock it up

| The message is made of | Scheme |
|---|---|
| numbers you measured | **B · data cards** |
| an architecture that mixed readers must recognize | **A · two-panel** |
| a position comparing two approaches, with a case | **C · structure compare** |

Band order, budgets and rules per scheme: `reference/schemes.md`. Rendered examples: `../infographic-build/examples/out/`.

Write the mockup as bands with the exact words. Get it approved. Then hand it to **infographic-build**.

## What stays in the post body

Dates, quotes, the full argument, the honest footnote, the second example. If a reader needs it to act, it goes in the body. If a reader needs it to recognize the message, it goes in the image.

## Red flags (each one came from a real draft)

- "I kept the type size and absorbed the density with a taller canvas" → cut content.
- "The reference is 1:1.375, so I used 1:1.375" → 4:5.
- "Body text 13.5 px, titles 17 px" on a canvas wider than 1080 → normalize to 1080 first.
- Every box carries a sentence → draw the difference, label with two words.
- Eight components per panel plus numbered arrows plus a legend plus a banner → seven boxes, one-word arrow labels, one caption.

Dated baseline-vs-skill comparisons: `lessons.md`.
