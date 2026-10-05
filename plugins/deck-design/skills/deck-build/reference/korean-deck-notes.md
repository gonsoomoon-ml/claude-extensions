# Korean decks — build and QA notes

Notes that only show up when the deck is Korean and QA runs on Linux.

## Font stack

| Use | Face | Why |
|---|---|---|
| Latin text | `Amazon Ember` | The AWS brand face — the `latin` slot of every run |
| Korean text | `Noto Sans CJK KR` | Korean-safe, ships with most Linux images — the `ea` and `cs` slots of every run |
| Korean text, Mac presenter PC | `Apple SD Gothic Neo` | The macOS system face (listed for Sequoia and Tahoe); Noto Sans CJK KR is not, so a stock Mac substitutes it unless installed. Mac-only — keep Noto when the presenting machine is unknown or not a Mac. QA still renders in Noto (`RENDER_CHECK=1`) |
| QA renders | `Noto Sans CJK KR` for Latin too (`RENDER_CHECK=1`) | Amazon Ember is not installed on Linux; LibreOffice would substitute a face with other widths |
| Avoid | Calibri, Arial, Aptos as the body face | Latin-only and off-brand; Korean glyphs fall back per character |
| Avoid | `Malgun Gothic` | Windows-only — LibreOffice substitutes, and the substitute has different widths |

Declare **both** faces on **every** text run. A missing face inherits the theme font, which is usually
Latin-only, and the slide silently renders in a substituted face.

- **python-pptx** — set the Latin face on `run.font.name` and write `<a:ea>`/`<a:cs>` with the Korean face
  into the run properties (the aurora-black profile's `format_aurora.py`, `_set_fonts`, does exactly this).
- **pptxgenjs** — `fontFace` is written into `latin`, `ea` and `cs` alike (checked in pptxgenjs 4.0.1), so a
  build with `fontFace: "Amazon Ember"` asks for Korean glyphs Amazon Ember does not have. Run
  `python scripts/set_ea_font.py deck.pptx` after `writeFile()` — it rewrites only `ea`/`cs`.

Latin widths in a Noto QA render differ slightly from Amazon Ember in PowerPoint — leave ~10% slack in boxes
whose text is mostly Latin.

## Rendering artifacts that are not defects

LibreOffice adds a visible space at Korean/Latin and Korean/digit boundaries:

```
AI 를 쓸 수 없던         (file says: AI를 쓸 수 없던)
6 개월째 0 건            (file says: 6개월째 0건)
```

The same artifact appears when rendering decks made in PowerPoint, so it is the renderer, not the file.
Do not "fix" it by deleting characters — the deck will then be wrong in PowerPoint.

What *is* a real defect in the render: text touching or crossing its box edge, and any line that wraps
where the author did not intend.

## Korean filenames break python-pptx

A macOS-created file whose name contains Korean is usually NFD-normalized. Linux tools list it fine, but
`Presentation("한글이름.pptx")` raises `PackageNotFoundError: Package not found` — the path the library
receives never matches the directory entry.

```bash
cp 260908-AWS-*.pptx ref.pptx     # shell glob sidesteps the normalization
python -c "from pptx import Presentation; Presentation('ref.pptx')"
```

Same rule for `soffice`, `markitdown`, and the thumbnail script: copy to an ASCII name first.

## Reusing an existing deck's look

To match a deck you already have, read its theme rather than eyeballing the colors:

```bash
python3 - <<'PY'
import zipfile, re
z = zipfile.ZipFile("ref.pptx")
t = z.read("ppt/theme/theme1.xml").decode()
print(re.findall(r'<a:(dk1|lt1|dk2|lt2|accent[1-6])>.*?val="([0-9A-Fa-f]{6})"', t)[:10])
print(re.findall(r'<a:(?:latin|ea) typeface="([^"]+)"', t)[:6])
PY
```

Then render two or three representative slides (cover, a table slide, a diagram slide) and read the
positions from `python-pptx`: `shape.left/top/width` in inches tells you the real margin and type scale.
A deck's tone lives in four numbers — left margin, title size, body size, and the accent hex.

## Line breaks in Korean headlines

In LibreOffice QA renders Korean wraps at spaces (between words), not mid-word — measured 2026-10-04 on four
card texts whose rendered line counts matched a word-by-word estimate; PowerPoint was not measured. Either way,
a headline that must break in a specific place should be two runs with an explicit break, or two text boxes.
Relying on the wrap point means the break moves when the font substitutes.

## Text budget

Counting characters per slide keeps slides readable. A workable budget for 13.333 × 7.5 in:

| Slide type | Budget (characters, product names excluded) |
|---|---|
| Diagram | ~120 |
| Table | ~180 |
| Bridge / question | ~40 |

Product names (`Amazon Bedrock`, `Google Kubernetes Engine`) are excluded because they are unavoidable and
read as one token. Everything else counts, including the title and the takeaway line.
