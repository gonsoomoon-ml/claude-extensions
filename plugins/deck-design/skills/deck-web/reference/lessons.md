# Lessons — from the first web deck (13 slides, Korean + English, 2026-10-30/31)

Each one came from a render, the live page or the author's remark, not from theory. Font-stack and Korean-render
lessons live in `../../deck-build/reference/korean-deck-notes.md` and apply here unchanged.

- **The deck is one file.** Fonts (Google Fonts link), the English map and the engine are inline; only images
  sit beside it. A deploy uploads index.html plus the images; the link is the deliverable.
- **Public visitors do not have Amazon Ember.** The font stack starts with Ember, so the author's machine renders
  narrow Latin; a visitor gets Noto Sans KR, which is wider. The first English render overflowed on 10 of 13
  slides, worst in the Noto-only render — every English check runs with `--noember`.
- **English runs 10–20% longer than Korean.** Fix in this order: shorter English, then the `html[lang=en]` size
  step (one size down, never under 18 px), then wider columns (glossary name column 180 → 200 px). Keep the rules
  under `html[lang=en]` and diff the Korean captures against the pre-change set — they stayed pixel-identical.
- **Translate by element, not by page.** Keying the map on each leaf's Korean innerHTML lets one JSON cover
  slides, notes templates, title, alt and aria text; the markup stays Korean-only, and a missing key leaves
  Korean on screen where the inventory diff catches it.
- **A fixed pill in the corner is invisible.** The first 한|EN toggle was pinned bottom-right; the author said it
  was not easily visible. It moved into the controls row beside ← 이전 / 다음 → with the same button look (current
  language bold).
- **Color the key terms, not the sentence.** The author's rule on the first deck: the title and the takeaway
  carry one to three pillar-colored terms per slide (`.p1` / `.p2`), box titles take their pillar's color and
  only the focus box doubles its border. Everything else stays white or gray, so the colored term is the
  thing the eye lands on.
- **The strange words were found by reading, not by rendering.** The first deck's wording changed in a box-by-box
  read (등록부 → Agent Registry, 넷 → 네 가지, 토큰 → 호출자 검증, 거름망 → 막는 곳은 유형마다 하나 …) after the
  slides already rendered clean. The rules are in SKILL.md, "Korean wording"; do that read before the first capture.
- **Fullscreen hides the controls row.** Every control needs a key: N notes, F fullscreen, E language.
- **og:image must be absolute.** The preview card ignores a relative `cover.png`; the deploy script rewrites it to
  `https://<distribution>/cover.png` on every run, so the source file keeps the relative path.
- **The thumbnail is the cover slide.** One question in three lines and nothing else; the preview card shows those
  lines at thumbnail size. Capture s01.png and ship it as cover.png.
- **One canvas, two outputs.** The 1280×720 px coordinates double as the pptx coordinates (python-pptx at
  96 px/in) and `data-step` numbers double as click-animation steps. Build the HTML first, derive the pptx.
- **A one-line label needs slack.** `white-space: nowrap` labels (chips, sub-boxes, diagram labels) clip without
  a visible wrap; capture.py flags `nowrap-clip`. Mixed Korean/Latin labels run wider than they measure.
- **3–7 px past-box reports on two-line sub-boxes are the Korean descender, not text loss — fix the box anyway.**
  The first deck accepted them; the template's sub-box height went 58 → 62 px so a fresh deck starts at zero issues.
- **No page numbers, no measured numbers on slides** — the author's rule for this deck; numbers live in the notes
  with their source.
- **The first deploy creates a public surface, and a tool-approval classifier blocked it from the session.**
  Bucket + distribution were created by the author's hand; re-deploys (upload + invalidate) ran from the session
  afterward with an explicit go. Keep the script idempotent so the second run is routine.
