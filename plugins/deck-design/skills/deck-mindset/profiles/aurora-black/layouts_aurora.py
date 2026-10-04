"""Named layout builders for the aurora-black profile (see PROFILE.md §4, §4b).

Every builder: (prs, ...) -> slide.  Text sizes: TITLE 30 / MID 18 / BODY 15 (+CITE 10).
Title guard: ≤ 34 chars; put the rest of a long mock headline into `subline`.
"""
import os
from format_aurora import *

CW = SLIDE_W - 2 * MARGIN_X
TOP0 = Inches(1.0)                 # first content line when there is no subline
SUB_Y = Inches(0.95)               # subline y (below title)
TOP1 = Inches(1.45)                # first content line when a subline exists
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXTRACT = os.environ.get("AURORA_EXTRACT", os.path.join(ROOT, "sources", "extract"))   # original figures (set AURORA_EXTRACT)


def est_lines(text, width, pt):
    """Rough line count for Korean-heavy text: CJK ≈ 0.95·pt/72 in per char, Latin/space ≈ 0.5·pt/72 in."""
    w = 0.0
    for ch in text:
        w += (0.95 if ord(ch) > 0x2E7F else 0.5) * pt / 72.0
    return max(1, int(w / (width / 914400.0)) + 1)


def _slide(prs, name="1_Blank"):
    return prs.slides.add_slide(layout(prs, name))


def _head(s, title, subline=None, cite=None):
    add_chrome(s, cite=cite)
    add_title(s, title)
    if subline:
        sz = MID if est_lines(subline, CW, MID) == 1 else BODY
        add_text(s, MARGIN_X, SUB_Y, CW, Inches(0.4), subline, size=sz, color=MUTED)
    return TOP1 if subline else TOP0




def _takeaway(s, y, parts, aws=None, extra=None):
    """parts: (text, opts) segments for one MID line; aws: BODY muted line below; extra: more BODY lines."""
    add_hairline(s, MARGIN_X, y, CW)
    text = "".join(t for t, _ in parts)
    n = est_lines(text, CW, MID)
    add_text(s, MARGIN_X, y + Inches(0.12), CW, Inches(0.36) * n + Inches(0.1), [parts], line_spacing=1.2)
    yy = y + Inches(0.12) + Inches(0.36) * n + Inches(0.08)
    if aws:
        m = est_lines(aws, CW, BODY)
        add_text(s, MARGIN_X, yy, CW, Inches(0.3) * m + Inches(0.05), aws, size=BODY, color=MUTED, line_spacing=1.2)
        yy += Inches(0.3) * m + Inches(0.1)
    if extra:
        for line in extra:
            m = est_lines(line if isinstance(line, str) else "".join(t for t, _ in line), CW, BODY)
            add_text(s, MARGIN_X, yy, CW, Inches(0.3) * m + Inches(0.05), line, size=BODY, color=TEXT, line_spacing=1.2)
            yy += Inches(0.3) * m + Inches(0.06)
    return yy


def gradient_rule(s, left, top, width=Inches(2.2)):
    bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, width, Pt(4))
    bar.line.fill.background(); bar.fill.gradient(); bar.fill.gradient_angle = 0
    st = bar.fill.gradient_stops
    st[0].color.rgb = RGBColor.from_string(GRAD[0]); st[0].position = 0
    st[1].color.rgb = RGBColor.from_string(GRAD[2]); st[1].position = 1
    return bar


def fit_picture(s, path, left, top, max_w, max_h, border=True):
    """Place an original figure scaled to fit (never cropped); thin BOX_LINE frame so white figures sit on the black ground."""
    from PIL import Image as _I
    iw, ih = _I.open(path).size
    w = max_w; h = int(w * ih / iw)
    if h > max_h:
        h = max_h; w = int(h * iw / ih)
    s.shapes.add_picture(path, left, top, width=int(w), height=int(h))
    if border:
        r = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, int(w), int(h))
        r.fill.background(); r.line.color.rgb = BOX_LINE; r.line.width = Pt(0.75)
    return int(w), int(h)


# ── Cover ─────────────────────────────────────────────────────────────
def cover(prs, kicker, title_lines, date, name, org, sub=None, title_size=48):
    """kicker: small ACCENT line above the title (or None); sub: ACCENT line below the title."""
    s = _slide(prs, "Title Slide")
    for ph in list(s.placeholders):
        ph._element.getparent().remove(ph._element)
    add_chrome(s, cover=True)
    y = Inches(1.05)
    if kicker:
        add_text(s, MARGIN_X, y, CW, Inches(0.5), kicker, size=MID, color=ACCENT); y += Inches(0.6)
    n = len(title_lines)
    add_text(s, MARGIN_X, y, CW, Inches(0.8) * n + Inches(0.2), title_lines, size=title_size, bold=True, line_spacing=1.08)
    y += Inches(0.8) * n + Inches(0.3)
    if sub:
        add_text(s, MARGIN_X, y, CW, Inches(0.5), sub, size=22, color=ACCENT); y += Inches(0.7)
    y = max(y + Inches(0.3), Inches(4.4))
    add_text(s, MARGIN_X, y, CW, Inches(0.4), date, size=MID, color=MUTED)
    add_text(s, MARGIN_X, y + Inches(0.55), CW, Inches(0.45), name, size=MID, bold=True)
    add_text(s, MARGIN_X, y + Inches(1.0), CW, Inches(0.4), org, size=BODY, color=MUTED)
    return s


# ── Statement (question slides) ───────────────────────────────────────
def statement(prs, headline_lines, subline=None, kicker=None, cite=None):
    s = _slide(prs)
    add_chrome(s, cite=cite)
    n = len(headline_lines)
    size = 48 if n <= 2 else 40
    lh = Inches(0.78) if n <= 2 else Inches(0.66)
    top = max(Inches(1.4), (Inches(6.6) - lh * n) / 2)
    if kicker:
        klines = [kicker] if isinstance(kicker, str) else list(kicker)
        kh = Inches(0.38) * len(klines)
        add_text(s, MARGIN_X, top - kh - Inches(0.35), CW, kh, klines, size=MID, color=MUTED, line_spacing=1.2)
    add_text(s, MARGIN_X, top, CW, lh * n + Inches(0.2), headline_lines, size=size, bold=True, color=TEXT, line_spacing=1.1)
    # no underline under question headlines (user decision 2026-09-05)
    if subline:
        add_text(s, MARGIN_X, top + lh * n + Inches(0.35), CW, Inches(0.8), subline, size=MID, color=MUTED, line_spacing=1.25)
    return s


# ── Label rows ────────────────────────────────────────────────────────
def label_rows(prs, title, rows, subline=None, takeaway=None, aws=None, cite=None, label_w=Inches(2.4), row_h=None, arrows=False, width=None):
    """rows: (label, head, sub, focal). head MID bold TEXT; sub BODY MUTED (ACCENT if focal). width: row block width (default CW)."""
    s = _slide(prs)
    y = _head(s, title, subline, cite)
    W = width or CW
    n = len(rows)
    rh = row_h or min(Inches(1.05), (Inches(5.3) - y) / n)
    for i, (label, head, sub, focal) in enumerate(rows):
        add_text(s, MARGIN_X, y + Inches(0.08), label_w, Inches(0.5), label, size=MID, bold=True, color=ACCENT if focal else TEAL)
        add_text(s, MARGIN_X + label_w, y + Inches(0.06), W - label_w, Inches(0.5), head, size=MID, bold=True, color=TEXT)
        if sub:
            add_text(s, MARGIN_X + label_w, y + Inches(0.48), W - label_w, rh - Inches(0.5), sub, size=BODY,
                     color=ACCENT if focal else MUTED, line_spacing=1.2)
        if i < n - 1:
            add_hairline(s, MARGIN_X + label_w, y + rh - Inches(0.06), W - label_w)
            if arrows:
                add_text(s, MARGIN_X, y + rh - Inches(0.3), Inches(0.5), Inches(0.4), "▼", size=BODY, color=MUTED)
        y += rh
    if takeaway:
        _takeaway(s, max(y + Inches(0.1), Inches(5.3)), takeaway, aws)
    return s


# ── Numbered rows ─────────────────────────────────────────────────────
def numbered_rows(prs, title, rows, subline=None, takeaway=None, aws=None, cite=None, cols=1, arrows=False):
    """rows: (badge, head, sub, focal). cols=2 splits rows into two columns."""
    s = _slide(prs)
    y0 = _head(s, title, subline, cite)
    per = (len(rows) + cols - 1) // cols
    colw = (CW - Inches(0.4) * (cols - 1)) / cols
    avail = Inches(5.25) - y0
    rh = min(Inches(1.0), avail / per)
    for c in range(cols):
        x = MARGIN_X + c * (colw + Inches(0.4))
        y = y0
        chunk = rows[c * per:(c + 1) * per]
        for i, (badge, head, sub, focal) in enumerate(chunk):
            add_text(s, x, y + Inches(0.02), Inches(0.55), Inches(0.5), badge, size=MID, bold=True, color=ACCENT if focal else TEAL)
            add_text(s, x + Inches(0.6), y + Inches(0.05), colw - Inches(0.6), Inches(0.5), head, size=MID, bold=focal or not sub, color=TEXT)
            if sub:
                add_text(s, x + Inches(0.6), y + Inches(0.45), colw - Inches(0.6), rh - Inches(0.45), sub, size=BODY,
                         color=ACCENT if focal else MUTED, line_spacing=1.2)
            if i < len(chunk) - 1:
                add_hairline(s, x + Inches(0.6), y + rh - Inches(0.06), colw - Inches(0.6))
                if arrows:
                    add_text(s, x, y + rh - Inches(0.3), Inches(0.5), Inches(0.4), "▼", size=BODY, color=MUTED)
            y += rh
    if takeaway:
        _takeaway(s, Inches(5.3), takeaway, aws)
    return s


# ── Glass cards ───────────────────────────────────────────────────────
def glass_cards(prs, title, cards, subline=None, intro=None, takeaway=None, aws=None, cite=None, focal=None, card_h=None):
    """cards: (label, body, result). focal: index of the card outlined in ACCENT."""
    s = _slide(prs)
    y = _head(s, title, subline, cite)
    if intro:
        add_text(s, MARGIN_X, y, CW, Inches(0.4), intro, size=BODY, color=MUTED)
        y += Inches(0.42)
    n = len(cards); gap = Inches(0.25); cw = (CW - gap * (n - 1)) / n
    ch = card_h or (Inches(3.35) if takeaway else Inches(4.0))
    for i, (label, body, result) in enumerate(cards):
        left = MARGIN_X + i * (cw + gap)
        add_box(s, left, y, cw, ch, [""], fill=SURFACE_FILL, line=ACCENT if focal == i else BOX_LINE)
        add_text(s, left + Inches(0.2), y + Inches(0.18), cw - Inches(0.4), Inches(0.45), label, size=MID, bold=True, color=ACCENT)
        add_text(s, left + Inches(0.2), y + Inches(0.7), cw - Inches(0.4), ch * 0.5, body, size=BODY, color=TEXT, line_spacing=1.25)
        if result:
            add_text(s, left + Inches(0.2), y + ch - Inches(1.05), cw - Inches(0.4), Inches(0.95), result, size=BODY, color=MUTED, line_spacing=1.25)
    if takeaway:
        _takeaway(s, y + ch + Inches(0.2), takeaway, aws)
    return s


# ── Two-column comparison ─────────────────────────────────────────────
def two_column(prs, title, left, right, subline=None, takeaway=None, aws=None, cite=None, focal="right", col_h=None):
    """left/right: (heading, [lines]) — lines are str or [(text, opts)] segments."""
    s = _slide(prs)
    y = _head(s, title, subline, cite)
    gap = Inches(0.3); cw = (CW - gap) / 2
    ch = col_h or (Inches(3.6) if takeaway else Inches(4.4))
    for i, (heading, lines) in enumerate([left, right]):
        x = MARGIN_X + i * (cw + gap)
        is_focal = (focal == ("left" if i == 0 else "right"))
        add_box(s, x, y, cw, ch, [""], fill=SURFACE_FILL, line=ACCENT if is_focal else BOX_LINE)
        add_text(s, x + Inches(0.22), y + Inches(0.18), cw - Inches(0.44), Inches(0.45), heading, size=MID, bold=True, color=ACCENT if is_focal else TEXT)
        add_text(s, x + Inches(0.22), y + Inches(0.72), cw - Inches(0.44), ch - Inches(0.9), lines, size=BODY, color=TEXT, line_spacing=1.3, space_after=4)
    if takeaway:
        _takeaway(s, y + ch + Inches(0.2), takeaway, aws)
    return s


# ── Hairline table ────────────────────────────────────────────────────
def hairline_table(prs, title, headers, rows, col_w, subline=None, focal_row=None, takeaway=None, aws=None, cite=None,
                   first_col_big=False, row_h=None, body_size=BODY):
    """rows: list of cell lists (str). col_w: list of Inches summing ≤ CW."""
    s = _slide(prs)
    y = _head(s, title, subline, cite)
    xs = [MARGIN_X]
    for w in col_w[:-1]:
        xs.append(xs[-1] + w)
    if headers:
        for x, w, h in zip(xs, col_w, headers):
            add_text(s, x, y, w, Inches(0.35), h, size=BODY, color=MUTED)
        add_hairline(s, MARGIN_X, y + Inches(0.4), CW)
        y += Inches(0.52)
    avail = (Inches(5.35) if takeaway else Inches(6.5)) - y
    rh = row_h or min(Inches(0.85), avail / len(rows))
    for r, cells in enumerate(rows):
        focal = (r == focal_row)
        for c, (x, w, cell) in enumerate(zip(xs, col_w, cells)):
            if c == 0 and first_col_big:
                add_text(s, x, y + Inches(0.02), w, Inches(0.6), cell, size=TITLE, bold=True, color=ACCENT if focal else TEAL)
            else:
                add_text(s, x, y + Inches(0.06), w - Inches(0.15), rh, cell, size=body_size,
                         color=ACCENT if focal else (TEXT if c <= 1 else MUTED), bold=focal, line_spacing=1.2)
        y += rh
        add_hairline(s, MARGIN_X, y - Inches(0.06), CW)
    if takeaway:
        _takeaway(s, y + Inches(0.15), takeaway, aws)
    return s


# ── Hero stat ─────────────────────────────────────────────────────────
def hero_stat(prs, title, stats, lines=None, subline=None, takeaway=None, aws=None, cite=None, image=None, image_w=Inches(6.5), caption=None):
    """stats: (number, label). With image: stats stacked right of the image; without: stats in a row."""
    s = _slide(prs)
    y = _head(s, title, subline, cite)
    if image:
        s.shapes.add_picture(image, MARGIN_X, y, width=image_w)
        from PIL import Image as _I
        iw, ih = _I.open(image).size
        img_h = image_w * ih / iw
        if caption:
            add_text(s, MARGIN_X, y + img_h + Inches(0.08), image_w, Inches(0.3), caption, size=BODY, color=MUTED)
        sx = MARGIN_X + image_w + Inches(0.45); sw = SLIDE_W - sx - MARGIN_X
        yy = y
        for num, label in stats:
            add_text(s, sx, yy, sw, Inches(0.9), num, size=54, bold=True, color=ACCENT, line_spacing=1.0)
            add_text(s, sx, yy + Inches(0.85), sw, Inches(0.35), label, size=BODY, color=MUTED)
            yy += Inches(1.15)
        body_y = max(y + img_h + Inches(0.5), yy + Inches(0.1))
    else:
        n = len(stats); cw = CW / n
        for i, (num, label) in enumerate(stats):
            x = MARGIN_X + i * cw
            add_text(s, x, y + Inches(0.3), cw, Inches(1.3), num, size=72, bold=True, color=ACCENT, line_spacing=1.0)
            add_text(s, x, y + Inches(1.65), cw - Inches(0.3), Inches(0.7), label, size=MID, color=MUTED, line_spacing=1.2)
        body_y = y + Inches(2.6)
    if lines:
        add_hairline(s, MARGIN_X, body_y, CW)
        add_text(s, MARGIN_X, body_y + Inches(0.12), CW, Inches(1.2), lines, size=BODY, color=TEXT, line_spacing=1.3)
        body_y += Inches(0.12) + Inches(0.32) * len(lines)
    if takeaway:
        _takeaway(s, body_y + Inches(0.2), takeaway, aws)
    return s


# ── Image + cite ──────────────────────────────────────────────────────
def image_cite(prs, title, image, caption=None, side=None, subline=None, takeaway=None, aws=None, cite=None, image_w=None, max_h=Inches(4.6)):
    """side: (heading, [lines]) drawn to the right of the image."""
    s = _slide(prs)
    y = _head(s, title, subline, cite)
    from PIL import Image as _I
    iw, ih = _I.open(image).size
    w = image_w or (Inches(7.6) if side else CW)
    h = w * ih / iw
    if h > max_h:
        h = max_h; w = h * iw / ih
    s.shapes.add_picture(image, MARGIN_X, y, width=w, height=h)
    if caption:
        add_text(s, MARGIN_X, y + h + Inches(0.08), w, Inches(0.3), caption, size=BODY, color=MUTED)
    if side:
        sx = MARGIN_X + w + Inches(0.4); sw = SLIDE_W - sx - MARGIN_X
        heading, lines = side
        add_text(s, sx, y, sw, Inches(0.45), heading, size=MID, bold=True, color=ACCENT)
        add_text(s, sx, y + Inches(0.55), sw, h - Inches(0.5), lines, size=BODY, color=TEXT, line_spacing=1.3, space_after=4)
    if takeaway:
        _takeaway(s, max(y + h + Inches(0.5), Inches(5.3)), takeaway, aws)
    return s


# ── Flow (4-lane sequence) ────────────────────────────────────────────
def flow(prs, title, lanes, steps, rows, takeaway=None, aws=None, cite=None, subline=None, dim_steps=None, note=None):
    """lanes: [(name, sub)] up to 4; steps: (from, to, badge, focal); rows: (badge, text, focal) list at right.
    dim_steps: set of badges to draw dimmed (for 'grown' pictures)."""
    s = _slide(prs)
    y0 = _head(s, title, subline, cite)
    n = len(lanes)
    lane_w = Inches(1.85); pitch = Inches(1.95)
    lane_x = [Inches(1.55) + i * pitch for i in range(n)]
    for (name, sub), cx in zip(lanes, lane_x):
        lines = [[(name, {"size": MID, "bold": True, "color": TEXT})]]
        if sub:
            lines.append([(sub, {"size": BODY, "color": MUTED})])
        add_box(s, cx - lane_w / 2, y0, lane_w, Inches(0.9), lines)
    n_steps = len(steps)
    step0 = y0 + Inches(1.2); pitch_y = Inches(0.43)
    life_h = pitch_y * (n_steps - 1) + Inches(0.6)
    for cx in lane_x:
        add_vline(s, cx, y0 + Inches(0.9), life_h, dash=True)
    dim_steps = dim_steps or set()
    for i, (a, b, badge, focal) in enumerate(steps):
        yy = step0 + i * pitch_y
        x1, x2 = lane_x[a], lane_x[b]
        dim = badge in dim_steps
        add_arrow(s, x1, yy, x2, yy, color=ACCENT if focal else (SURFACE_LINE if dim else MUTED), weight=1.75 if focal else 1.0)
        mid = (x1 + x2) / 2
        add_box(s, mid - Inches(0.19), yy - Inches(0.19), Inches(0.38), Inches(0.38),
                [[(badge, {"size": BODY, "bold": True, "color": ACCENT if focal else (SURFACE_LINE if dim else TEXT)})]],
                fill=BG, line=ACCENT if focal else SURFACE_LINE)
    rx = Inches(1.55) + (n - 1) * pitch + lane_w / 2 + Inches(0.4); rw = SLIDE_W - rx - MARGIN_X
    yy = y0 + Inches(0.05)
    for badge, text, focal in rows:
        m = est_lines(text, rw - Inches(0.42), BODY)
        add_text(s, rx, yy, Inches(0.4), Inches(0.45), badge, size=MID, bold=True, color=ACCENT if focal else MUTED)
        add_text(s, rx + Inches(0.42), yy + Inches(0.03), rw - Inches(0.42), Inches(0.28) * m + Inches(0.1), text, size=BODY, color=TEXT if focal else MUTED, bold=focal, line_spacing=1.15)
        yy += Inches(0.28) * m + Inches(0.2)
    last = step0 + (n_steps - 1) * pitch_y
    if note:
        add_text(s, MARGIN_X, last + Inches(0.3), Inches(7.6), Inches(0.35), note, size=BODY, color=ACCENT)
    if takeaway:
        _takeaway(s, max(Inches(5.3), last + Inches(0.35)), takeaway, aws)
    return s


# ── Code ──────────────────────────────────────────────────────────────
def code_slide(prs, title, code_lines, note=None, subline=None, takeaway=None, aws=None, cite=None):
    s = _slide(prs)
    y = _head(s, title, subline, cite)
    h = Inches(0.3) * len(code_lines) + Inches(0.4)
    add_box(s, MARGIN_X, y, CW, h, [""], fill=SURFACE_FILL, line=BOX_LINE, radius=False)
    add_text(s, MARGIN_X + Inches(0.25), y + Inches(0.2), CW - Inches(0.5), h - Inches(0.3), code_lines, size=BODY, color=TEXT, mono=True, line_spacing=1.15)
    if note:
        add_text(s, MARGIN_X, y + h + Inches(0.2), CW, Inches(0.5), note, size=MID, color=ACCENT, bold=True)
    if takeaway:
        _takeaway(s, Inches(5.3), takeaway, aws)
    return s


# ── Thanks ────────────────────────────────────────────────────────────
def thanks(prs, big, name, org):
    s = _slide(prs)
    add_chrome(s)
    add_text(s, MARGIN_X, Inches(2.5), CW, Inches(1.2), big, size=54, bold=True, color=TEXT, align=PP_ALIGN.CENTER)
    add_text(s, MARGIN_X, Inches(4.0), CW, Inches(0.45), name, size=MID, bold=True, align=PP_ALIGN.CENTER)
    add_text(s, MARGIN_X, Inches(4.45), CW, Inches(0.4), org, size=BODY, color=MUTED, align=PP_ALIGN.CENTER)
    return s


# ══════════════════════════════════════════════════════════════════════
# v6 additions (2026-09-06) — layouts that survived the user's editing rounds
# ══════════════════════════════════════════════════════════════════════
def seg(text, **o):
    """(text, opts) segment for mixed-style lines."""
    return (text, o)


def cap(s, x, y, w, text):
    """one-line caption under an original figure (BODY, MUTED). Keep ≤ 25 chars when the figure is narrow."""
    add_text(s, x, y, w, Inches(0.3), text, size=BODY, color=MUTED)


def card(s, x, y, w, h, head, lines, focal=False, head_color=None, dim=False):
    """Rounded card: head (MID bold) + body (BODY). dim=True → SURFACE_LINE border + MUTED text = deferred item ("○ … 심화에서")."""
    add_box(s, x, y, w, h, [""], fill=SURFACE_FILL, line=SURFACE_LINE if dim else (ACCENT if focal else BOX_LINE))
    hc = MUTED if dim else (head_color or (ACCENT if focal else TEXT))
    add_text(s, x + Inches(0.22), y + Inches(0.15), w - Inches(0.44), Inches(0.42), head, size=MID, bold=True, color=hc)
    add_text(s, x + Inches(0.22), y + Inches(0.62), w - Inches(0.44), h - Inches(0.7), lines, size=BODY,
             color=MUTED if dim else TEXT, line_spacing=1.3, space_after=3)


def num_list(s, x, y, w, items, pitch=Inches(0.95)):
    """items: (badge, head, sub, focal) — badge MID accent · head MID bold · sub BODY muted."""
    for badge, head, sub, focal in items:
        add_text(s, x, y, Inches(0.5), Inches(0.45), badge, size=MID, bold=True, color=ACCENT if focal else TEAL)
        add_text(s, x + Inches(0.5), y + Inches(0.02), w - Inches(0.5), Inches(0.45), head, size=MID, bold=True)
        if sub:
            add_text(s, x + Inches(0.5), y + Inches(0.42), w - Inches(0.5), pitch - Inches(0.45), sub, size=BODY,
                     color=ACCENT if focal else MUTED, line_spacing=1.2)
        y += pitch
    return y


def gauge(s, y, segments, height=Inches(0.7), groups=None):
    """Segmented bar. segments: (label, weight, focal). groups: [(label, first_idx, last_idx, color)] drawn 0.34in above the bar
    so the axis is named ("모델이 읽는 것 (입력)" / "모델이 쓰는 것 (출력)"). Returns the bar's bottom y."""
    total = sum(w for _, w, _ in segments); x = MARGIN_X; xs = []
    for label, w, focal in segments:
        bw = CW * w / total; xs.append((x, bw))
        add_box(s, x, y, bw - Inches(0.05), height, [[seg(label, size=BODY, bold=focal, color=ACCENT if focal else TEXT)]],
                fill=SURFACE_FILL, line=ACCENT if focal else BOX_LINE, radius=False)
        x += bw
    for label, a, b, color in (groups or []):
        gx = xs[a][0]; gw = xs[b][0] + xs[b][1] - gx
        add_text(s, gx - Inches(0.2), y - Inches(0.34), gw + Inches(0.4), Inches(0.3), label, size=BODY, color=color, align=PP_ALIGN.CENTER)
    return y + height


def statement_named(prs, headline_lines, name_line, cite=None):
    """Statement headline + one ACCENT "name" line under it (P11: "→ 이 설계의 이름: 하네스 엔지니어링").
    The name line takes the largest of 30/28/26/24pt that still fits one line."""
    s = statement(prs, headline_lines, cite=cite)
    n = len(headline_lines); lh = Inches(0.78) if n <= 2 else Inches(0.66)
    top = max(Inches(1.4), (Inches(6.6) - lh * n) / 2)
    sz = next((z for z in (30, 28, 26, 24) if est_lines(name_line, CW, z) == 1), 24)
    add_text(s, MARGIN_X, top + lh * n + Inches(0.5), CW, Inches(0.6), name_line, size=sz, bold=True, color=ACCENT)
    return s


def definition_box(prs, title, subline, box_label, groups, focal_box, focal_caption=None, takeaway=None, cite=None, box_h=Inches(3.05)):
    """One big box = the definition's scope, holding column groups of verbatim items, plus a small ACCENT box (P12 "하네스는?").
    groups: [(group_label, [item, ...])]. takeaway: segment list for the line under the box ("하는 일 — …")."""
    s = _slide(prs); y0 = _head(s, title, subline, cite)
    add_box(s, MARGIN_X, y0, CW, box_h, [""], fill=SURFACE_FILL, line=BOX_LINE)
    add_text(s, MARGIN_X + Inches(0.25), y0 + Inches(0.14), Inches(5), Inches(0.4), box_label, size=MID, bold=True, color=TEAL)
    gx = MARGIN_X + Inches(0.3); gw = (CW - Inches(0.6)) / len(groups)
    for i, (label, items) in enumerate(groups):
        x = gx + i * gw
        add_text(s, x, y0 + Inches(0.62), gw - Inches(0.2), Inches(0.4), label, size=MID, bold=True)
        add_text(s, x, y0 + Inches(1.05), gw - Inches(0.2), Inches(1.0), items, size=BODY, line_spacing=1.35)
    mw, mh = Inches(2.4), Inches(0.55); mx = MARGIN_X + (CW - mw) / 2 - Inches(1.6); my = y0 + box_h - mh - Inches(0.25)
    add_box(s, mx, my, mw, mh, [[seg(focal_box, size=MID, bold=True)]], fill=SURFACE_FILL, line=ACCENT)
    if focal_caption:
        add_text(s, mx + mw + Inches(0.3), my + Inches(0.12), Inches(5.5), Inches(0.35), focal_caption, size=BODY, color=MUTED)
    if takeaway:
        _takeaway(s, y0 + box_h + Inches(0.22), takeaway)
    return s


def container_strip(prs, title, outer_label, inner_focal, inner_items, items_label, owned, cards=None, cite=None,
                    user_label="사용자", owned_label="이미 가진 것 ▶", card_h=Inches(2.7)):
    """Outer box (the harness) containing a focal box (the model) ⇄ N inner boxes (tools · skills · surfaces · memory);
    captions under each inner box name what the company already has; optional cards below (P18).
    outer_label may be a segment list. cards: [(head, lines)]."""
    s = _slide(prs); y0 = _head(s, title, cite=cite)
    add_box(s, MARGIN_X, y0 + Inches(0.45), Inches(1.0), Inches(0.55), [[seg(user_label, size=BODY, bold=True)]], fill=SURFACE_FILL, line=BOX_LINE)
    add_text(s, MARGIN_X + Inches(1.05), y0 + Inches(0.5), Inches(0.4), Inches(0.45), "⇄", size=MID, color=MUTED, align=PP_ALIGN.CENTER)
    hx = MARGIN_X + Inches(1.5); hw = CW - Inches(1.5); hh = Inches(1.45)
    add_box(s, hx, y0, hw, hh, [""], fill=SURFACE_FILL, line=BOX_LINE)
    add_text(s, hx + Inches(0.25), y0 + Inches(0.1), hw - Inches(0.5), Inches(0.35), outer_label, size=MID)
    bw = Inches(1.6); gap = Inches(0.15); by = y0 + Inches(0.8); bh = Inches(0.5)
    add_box(s, hx + Inches(0.25), by, Inches(1.4), bh, [[seg(inner_focal, size=BODY, bold=True)]], fill=SURFACE_FILL, line=ACCENT)
    add_text(s, hx + Inches(1.7), by + Inches(0.06), Inches(0.5), Inches(0.4), "⇄", size=MID, color=MUTED, align=PP_ALIGN.CENTER)
    bx0 = hx + Inches(2.3)
    add_text(s, bx0, y0 + Inches(0.5), Inches(6.9), Inches(0.3), items_label, size=BODY, color=MUTED)
    for i, nm in enumerate(inner_items):
        add_box(s, bx0 + i * (bw + gap), by, bw, bh, [[seg(nm, size=BODY, bold=True)]], fill=SURFACE_FILL, line=BOX_LINE)
    cy = y0 + hh + Inches(0.08)
    add_text(s, hx + Inches(0.25), cy, Inches(1.95), Inches(0.3), owned_label, size=BODY, bold=True, color=ACCENT, align=PP_ALIGN.RIGHT)
    for i, ow in enumerate(owned):
        add_text(s, bx0 + i * (bw + gap), cy, bw, Inches(0.3), ow, size=BODY, color=MUTED, align=PP_ALIGN.CENTER)
    if cards:
        cy2 = y0 + hh + Inches(0.5); cg = Inches(0.2); cw4 = (CW - cg * (len(cards) - 1)) / len(cards)
        for i, (head, lines) in enumerate(cards):
            card(s, MARGIN_X + i * (cw4 + cg), cy2, cw4, card_h, head, lines)
    return s


def figure_with_steps(prs, title, image, steps, subline=None, caption=None, steps_head=None, takeaway=None, cite=None,
                      image_w=Inches(7.0), image_h=Inches(3.4)):
    """Original figure (bordered, uncropped) on the left + a numbered reading order on the right (P23).
    steps: list of lines (str or segment list); the figure's own title stays in the figure, the caption names the source."""
    s = _slide(prs); y0 = _head(s, title, subline, cite)
    iw, ih = fit_picture(s, image, MARGIN_X, y0, image_w, image_h, border=True)
    if caption:
        cap(s, MARGIN_X, y0 + ih + Inches(0.08), iw, caption)
    sx = MARGIN_X + iw + Inches(0.4); sw = SLIDE_W - sx - MARGIN_X
    if steps_head:
        add_text(s, sx, y0, sw, Inches(0.4), steps_head, size=MID, bold=True, color=ACCENT)
    add_text(s, sx, y0 + (Inches(0.5) if steps_head else 0), sw, ih - Inches(0.4), steps, size=BODY, line_spacing=1.3, space_after=5)
    if takeaway:
        _takeaway(s, y0 + ih + Inches(0.5), takeaway)
    return s


def procedure_flow(prs, title, steps, subline=None, takeaway=None, aws=None, cite=None, card_h=Inches(3.05), focal_last=True):
    """N equal cards joined by ▶, each = head (MID bold) + sub (BODY muted) + body lines; the last card is the focal one (P47).
    steps: [(head, sub, lines)]."""
    s = _slide(prs); y0 = _head(s, title, subline, cite)
    n = len(steps); gap = Inches(0.25); cw = (CW - gap * (n - 1)) / n
    for i, (head, sub, lines) in enumerate(steps):
        focal = focal_last and i == n - 1
        x = MARGIN_X + i * (cw + gap); ix = x + Inches(0.2); iw = cw - Inches(0.4)
        add_box(s, x, y0, cw, card_h, [""], fill=SURFACE_FILL, line=ACCENT if focal else BOX_LINE)
        add_text(s, ix, y0 + Inches(0.15), iw, Inches(0.4), head, size=MID, bold=True, color=ACCENT if focal else TEXT)
        if sub:
            add_text(s, ix, y0 + Inches(0.5), iw, Inches(0.55), sub, size=BODY, color=MUTED, line_spacing=1.15)
        add_text(s, ix, y0 + Inches(1.08), iw, card_h - Inches(1.15), lines, size=BODY, line_spacing=1.3, space_after=5)
        if i < n - 1:
            add_text(s, x + cw, y0 + card_h / 2 - Inches(0.2), gap, Inches(0.4), "▶", size=MID, color=MUTED, align=PP_ALIGN.CENTER)
    if takeaway:
        _takeaway(s, y0 + card_h + Inches(0.15), takeaway, aws)
    return s


def take_home(prs, title, kicker, items, closing=None):
    """3 (max 4) numbered lines + one MUTED explanation each; sizes 32/24/16 are this layout's exception (P48).
    items: [(num, key, rest, explanation)]."""
    s = _slide(prs); add_chrome(s); add_title(s, title)
    add_text(s, MARGIN_X, SUB_Y, CW, Inches(0.4), kicker, size=MID, bold=True, color=ACCENT)
    y = Inches(1.55); pitch = Inches(1.4); tx = MARGIN_X + Inches(0.75); tw = CW - Inches(0.75)
    for num, key, rest, expl in items:
        add_text(s, MARGIN_X, y - Inches(0.08), Inches(0.7), Inches(0.6), num, size=32, bold=True, color=ACCENT)
        add_text(s, tx, y, tw, Inches(0.5), [[seg(key, size=24, bold=True), seg(rest, size=24)]], line_spacing=1.1)
        add_text(s, tx, y + Inches(0.55), tw, Inches(0.5), expl, size=16, color=MUTED, line_spacing=1.2)
        y += pitch
    if closing:
        add_hairline(s, MARGIN_X, Inches(5.85), CW)
        add_text(s, MARGIN_X, Inches(6.0), CW, Inches(0.45), closing, size=MID, bold=True)
    return s


def checkpoint(prs, title, headers, rows, col_w, focal_row, cards_head, cards, takeaway=None, aws=None,
               row_h=Inches(0.66), card_h=Inches(1.75), cards_y=None):
    """Progress table (sections done so far) + N cards; a card's mode is 'check' (ACCENT head), 'focal' (ACCENT border) or
    'dim' (deferred: SURFACE_LINE border, MUTED text, "○" instead of "✓"). Never cite a number the deck no longer shows (P28/P45).
    cards: [(head, lines, mode)]."""
    s = hairline_table(prs, title, headers, rows, col_w, focal_row=focal_row, row_h=row_h)
    yy = cards_y or (TOP0 + Inches(0.52) + row_h * len(rows) + Inches(0.2))
    add_text(s, MARGIN_X, yy, CW, Inches(0.35), cards_head, size=MID)
    n = len(cards); gap = Inches(0.25); cw = (CW - gap * (n - 1)) / n; cy = yy + Inches(0.45)
    for i, (head, lines, mode) in enumerate(cards):
        card(s, MARGIN_X + i * (cw + gap), cy, cw, card_h, head, lines,
             focal=(mode == "focal"), head_color=None if mode == "dim" else ACCENT, dim=(mode == "dim"))
    if takeaway:
        _takeaway(s, cy + card_h + Inches(0.2), takeaway, aws)
    return s


def finalize_notes(prs, last="→ 다음 장"):
    """Replace "→ S16"-style record pointers in speaker notes with "→ 다음 장 「<next slide title>」".
    Run this as the LAST step of every build, including one-slide builds — record IDs go stale when slides move."""
    import re as _re
    slides = list(prs.slides)

    def title_of(sl):
        best = ("", 0)
        for sh in sl.shapes:
            if sh.has_text_frame and len(sh.text_frame.text.strip()) >= 4 and "https://" not in sh.text_frame.text:   # skip badges like "①"
                for para in sh.text_frame.paragraphs:
                    for r in para.runs:
                        if r.font.size and r.font.size.pt > best[1]:
                            best = (sh.text_frame.text.strip().split("\n")[0], r.font.size.pt)
        return best[0]

    for i, sl in enumerate(slides):
        if not sl.has_notes_slide:
            continue
        tf = sl.notes_slide.notes_text_frame; n = tf.text
        nxt = title_of(slides[i + 1]) if i + 1 < len(slides) else ""
        n2 = _re.sub(r"→ S\d+\b[:.]?", (f"→ 다음 장 「{nxt[:28]}」" if nxt else last), n)
        if n2 != n:
            tf.text = n2


def run_part(path, allowed, namespace):
    """One-slide builds: exec a part file whose slides sit behind `if want(n):` gates, with want() limited to `allowed`.
    namespace = globals() of the caller (must hold prs, seg, blog, REF, …)."""
    namespace["want"] = lambda n: n in allowed
    exec(compile(open(path, encoding="utf-8").read(), path, "exec"), namespace)
