---
name: deck-web
description: Build a slide deck as one HTML file in the deck-mindset house style — aurora-black tokens on a 1280×720 canvas, click builds, speaker notes, keys, an optional 한|EN toggle driven by one JSON map — then check every slide for overflow with a Chromium capture and publish it as a link on S3 + CloudFront. Use when the deck must be a URL (a LinkedIn post, a page to send) or when a web deck needs an English side; the pptx twin is deck-build.
---

# Deck Web

`deck-mindset` says *what* a good slide is. `deck-build` makes the .pptx. This skill makes the same deck as
**one HTML file** that opens from a link: the thumbnail is the cover, clicks build each slide, notes sit under
it, and one button flips the whole deck to English.

Born from a 13-slide deck shipped 2026-10-30/31 — Korean with an English toggle, public on CloudFront, with a
pptx twin built from the same coordinates.

## The pipeline

| # | Step | Output | Stop if |
|---|---|---|---|
| 1 | **Lock the content** | a mockup md — words, build order and notes per slide, approved one slide at a time | wording still moving |
| 2 | **Copy the template** | `templates/deck.html` → `web/index.html` | you start from a blank page |
| 3 | **Fill the slides** | one `<section class="slide">` per slide, layout classes from the template, `data-step` for click order, notes in `<template class="notes-src">` | a literal size or hex outside `:root`; a new layout when a template one fits |
| 4 | **Capture and look** | `python3 scripts/capture.py web/index.html out/` → `out/sNN.png` + issues | any issue — or you are reading code instead of the render |
| 5 | **Cover image** | `cp out/s01.png web/cover.png` — the og:image, the preview card on LinkedIn | the question is not readable at thumbnail size |
| 6 | **English (optional)** | `capture.py --inventory keys.json` → write `en.json` → `inject-i18n.py` → `capture.py --lang en --noember` | any issue in the Noto-only render |
| 7 | **Publish** | `bash scripts/deploy-s3-cloudfront.sh <name> web` — the first run creates a public surface, so the person runs it | — |

## The file

- **Canvas** 1280×720 px = 13.333×7.5 in at 96 px/in, scaled to the window. Every coordinate is a canvas px,
  so the pptx build can reuse it as is.
- **Tokens** in `:root`: the aurora-black colors (coral = pillar 1, blue = pillar 2, gray = everything else) and
  the type scale 53 / 40 / 32 / 24 / 20 / 13.3 px (= 40 / 30 / 24 / 18 / 15 / 10 pt). Three sizes per slide at
  most, 20 px floor, 13.3 px for sources only.
- **Color on terms, not sentences**: in the title and the takeaway, the one to three terms that carry the
  slide take the pillar color (`<span class="p1">` coral, `<span class="p2">` blue); box titles take their
  pillar's color; everything else stays white or gray. A whole sentence in color reads as decoration.
- **Layouts in the template**: question cover · rail + title + takeaway · pillar cards (question ▼ answer) and
  option cards (badge · lines · verdict) · bridge chip · flow diagram (absolute nodes + one SVG of connectors) ·
  step grid · glossary rows · figure with overlays. Each is one CSS block — delete the ones the deck does not use.
- **Builds**: `data-step="n"` shows at click n. The hash is `#slide.step`; keys ←/→, PageUp/Down, Space, Home/End.
- **Notes and footnotes**: `<template class="notes-src">` / `refs-src` inside each slide; N shows them under it.
- **Controls row** under the slide: ← 이전 · 다음 → · 한|EN · 노트 (N) · 전체 화면 (F) · count. Fullscreen hides
  the row, so every control also has a key (E for language).
- **No chrome**: no page numbers, no logo, no footer. The rail (문제 · 접근 · 해법 · 적용, current step in coral)
  is the only furniture.

## English side

One file, two languages. The key is the Korean `innerHTML` of each leaf element (whitespace-normalized); the
value is the English `innerHTML` with the same tags. `<title>`, `alt`, `aria-label` and `data-title` use the
same map. The engine swaps text in place and re-applies the build step; layout stays. `?lang=en` beats the
remembered choice, and the button hides itself when the map is empty.

- English runs 10–20% longer. The `html[lang=en]` block steps the dense blocks down one size (never under
  18 px); shorten the English before touching sizes.
- Check with `--noember`: a visitor's browser has no Amazon Ember, so Latin renders in Noto Sans KR, which is wider.
- The og:image and the thumbnail stay Korean — one image.

## What capture.py checks

Each slide is rendered with every step on (`#N.99`) at scale 1. Issues: `past-right` / `past-bottom` (off the
canvas, 22 px bottom margin), `nowrap-clip` (a one-line label clipped), `past-box-right` / `past-box-bottom`
(text outside its nearest bordered or filled box). Exit 1 on any issue. It cannot see a detached arrowhead or
two boxes overlapping — look at the PNGs.

## Publish

`deploy-s3-cloudfront.sh <name> [web-dir] [region]`: bucket `<name>-<account>` with public access blocked, an
Origin Access Control named `<name>`, a CloudFront distribution with `index.html` as root. Later runs upload and
invalidate only. It rewrites `og:image` to the absolute URL on every run, so the source keeps `cover.png`.

## Environment

`python3` with `playwright` and its Chromium (`python3 -m playwright install chromium`); Noto Sans KR or Noto
Sans CJK KR installed; the `aws` CLI with S3 + CloudFront rights for publishing. No Pillow, no Node.

`reference/lessons.md` holds what the first deck taught; `examples/` has the template rendered in both languages
and the `en.json` that drives the English side.
