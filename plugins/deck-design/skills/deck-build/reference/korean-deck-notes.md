# Korean decks — build and QA notes

Notes that only show up when the deck is Korean, the background is dark, and QA runs on Linux.

## Font stack

| Use | Face | Why |
|---|---|---|
| Everything | `Noto Sans CJK KR` | Ships with most Linux images, so the QA render matches the presenter's screen closely |
| Avoid | Latin-only faces (Calibri, Arial, Aptos) | Korean glyphs fall back per-glyph; line lengths change between QA and PowerPoint |
| Avoid | `Malgun Gothic` | Windows-only — LibreOffice substitutes, and the substitute has different widths |

Declare the face explicitly on **every** text run. A missing `fontFace` inherits the theme font, which is
usually Latin-only, and the slide silently renders in a substituted face.

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

Korean wraps mid-word, so a headline that must break in a specific place should be two runs with an
explicit break, or two text boxes. Relying on the wrap point means the break moves when the font substitutes.

## Text budget

Counting characters per slide keeps dark decks readable. A workable budget for 13.333 × 7.5 in:

| Slide type | Budget (characters, product names excluded) |
|---|---|
| Diagram | ~120 |
| Table | ~180 |
| Bridge / question | ~40 |

Product names (`Amazon Bedrock`, `Google Kubernetes Engine`) are excluded because they are unavoidable and
read as one token. Everything else counts, including the title and the takeaway line.
