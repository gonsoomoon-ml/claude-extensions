#!/usr/bin/env python3
"""Make every text on a slide animatable on its own: ungroup, split name + description boxes, keep animations.

PowerPoint animates a group as one object — the shapes inside cannot get an entrance of their own. A deck
built with one group per reveal step (deck-design 0.4.0 and earlier), or a box holding a bold name and a
regular description, therefore cannot reveal its pieces one by one. On a copy of the deck, this script:

1. Ungroups every group, nested and resized groups included (rotated or flipped groups stay grouped). Each
   former child is renamed "<step> · <child name>" — <step> is the group name up to the first " · "
   ("click1 · options" → "click1 · card A") — so the Selection Pane still lists the reveal order.
2. Carries animations on a group over to its former children: one copy of the effect per child, the first
   keeps the trigger and the rest run "with previous" — one click still reveals the same things.
3. Splits the boxes you name:
   --h  one paragraph, name runs then description runs ("완제품 CLI   명령 한 줄로 부른다") → two boxes side
        by side; the description starts where it started before. A trailing standalone mark on the name
        ("하네스 = ") moves into the description box — LibreOffice widens a Korean/ASCII boundary and would
        wrap the name.
   --v  a name paragraph over description paragraph(s) → two shapes with the same frame; each keeps an empty
        paragraph of the same height where the other's text was, so nothing moves, on any font.
   A filled card keeps its fill and the name; the description goes into a transparent copy on top (pick it
   in the Selection Pane — a click on the slide selects the copy).

Which boxes to split is a judgment call, so the script never guesses: run --list, then name shape ids.
Split a box that holds two texts with different roles shown by styling (a bold name + a regular
description). Leave inline emphasis inside one sentence, and lines of one style, whole. --list marks
structural candidates (H? / V?) — a hint, not a decision — and a size with * when the run has none of its
own (inherited, often 18pt): PowerPoint can drop a run's size while the presenter edits, so check those.
Placeholders inherit their size from the layout by design and are not marked.

    python split_for_animation.py deck.pptx --list
    python split_for_animation.py deck.pptx --h 3:3,11 --h 4:11 --v 5:18,21 -o deck-split.pptx

Slide numbers follow the slide order in the deck. Nothing is written if a named box cannot be split.
--h measures with Noto Sans CJK KR (+ up to 10% for the Latin share — the light profile's width_in) and drops
a smaller description by 0.95 x the size difference to keep one baseline; both are calibrated on Noto in
LibreOffice renders, so check the side-by-side splits on the presenting machine. Needs lxml (Pillow and
fc-match for measuring; without them a per-character estimate is used).
"""
import argparse
import copy
import os
import re
import subprocess
import sys
import tempfile
import zipfile

from lxml import etree

P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS = {"p": P_NS, "a": A_NS}
A = "{%s}" % A_NS
EMU_PER_IN, EMU_PER_PT = 914400, 12700
DEFAULT_SIZE = 18                  # PowerPoint's text box default, when no size is written anywhere
FILLS = {"noFill", "solidFill", "gradFill", "blipFill", "pattFill", "grpFill"}


class Skip(Exception):
    """A named box that cannot be split as asked."""


def local(el):
    return etree.QName(el).localname


# ── width estimate: the light profile's width_in (format_light.py), kept in step with it ──
_fonts = {}   # bold → ImageFont at 1000 units | False (not found)


def _measure_font(bold=True):
    """Noto Sans CJK KR via fc-match + Pillow; None if unavailable (falls back to _em)."""
    if bold not in _fonts:
        _fonts[bold] = False
        try:
            from PIL import ImageFont
            pattern = "Noto Sans CJK KR:bold" if bold else "Noto Sans CJK KR:regular"
            path = subprocess.run(["fc-match", "-f", "%{file}", pattern],
                                  capture_output=True, text=True).stdout.strip()
            for i in range(8):  # find the KR face inside the .ttc
                f = ImageFont.truetype(path, 1000, index=i)
                if "KR" in f.getname()[0]:
                    _fonts[bold] = f
                    break
        except Exception:
            pass
    return _fonts[bold] or None


def _em(ch):
    """Character width in em when the font is missing — matched to Noto Sans CJK KR Bold."""
    if "가" <= ch <= "힣" or "　" <= ch <= "鿿":
        return 0.92
    if ch == " ":
        return 0.23
    if ch.isdigit():
        return 0.59
    if ch.isascii() and ch.isalpha():
        return 0.66 if ch.isupper() else 0.60
    return 0.60


def width_in(text, size, bold=True):
    """Width of a run of text in inches, +up to 10% for the Latin share (Amazon Ember vs Noto)."""
    f = _measure_font(bold)
    em = f.getlength(text) / 1000 if f else sum(_em(c) for c in text)
    latin = sum(c.isascii() and c.isalpha() for c in text) / max(len(text), 1)
    return em * size / 72 * (1 + 0.10 * latin)


# ── run styles ────────────────────────────────────────────────────────
def run_size(r, body):
    """Point size of a run: its own sz, else the shape's list style, else PowerPoint's default."""
    rpr = r.find("a:rPr", NS)
    if rpr is not None and rpr.get("sz"):
        return int(rpr.get("sz")) / 100
    d = body.find("a:lstStyle/a:lvl1pPr/a:defRPr", NS)
    return int(d.get("sz")) / 100 if d is not None and d.get("sz") else DEFAULT_SIZE


def own_size(r):
    """True if the run writes its own size (not inherited from the list style or PowerPoint's default)."""
    rpr = r.find("a:rPr", NS)
    return rpr is not None and bool(rpr.get("sz"))


def run_bold(r):
    rpr = r.find("a:rPr", NS)
    return rpr is not None and rpr.get("b") in ("1", "true")


def run_style(r, body):
    """(bold, size, color) — what tells a name from a description."""
    clr = r.find("a:rPr/a:solidFill/*", NS)
    return run_bold(r), run_size(r, body), None if clr is None else (local(clr), clr.get("val"))


def run_text(r):
    t = r.find("a:t", NS)
    return (t.text or "") if t is not None else ""


def lines_needed(p, room_in, body):
    """Word-by-word wrap estimate of one paragraph (Korean also wraps at spaces in QA renders)."""
    lines, x = 1, 0.0
    for el in p:
        if local(el) == "br":
            lines, x = lines + 1, 0.0
        elif local(el) in ("r", "fld"):
            size, bold = run_size(el, body), run_bold(el)
            for tok in re.findall(r"\S+|\s+", run_text(el)):
                w = width_in(tok, size, bold)
                if x > 0 and x + w > room_in and not tok.isspace():
                    lines, x = lines + 1, 0.0
                if not (x == 0 and tok.isspace()):
                    x += w
    return lines


# ── shapes ────────────────────────────────────────────────────────────
def cnvpr(el):
    return el.find("./*/p:cNvPr", NS)   # nvSpPr / nvGrpSpPr / nvPicPr / nvCxnSpPr / nvGraphicFramePr


def own_xfrm(el):
    return el.find({"grpSp": "p:grpSpPr/a:xfrm", "graphicFrame": "p:xfrm"}.get(local(el), "p:spPr/a:xfrm"), NS)


def frame(sp):
    off, ext = own_xfrm(sp).find("a:off", NS), own_xfrm(sp).find("a:ext", NS)
    return off, ext, int(off.get("x")), int(off.get("y")), int(ext.get("cx")), int(ext.get("cy"))


def paints(sp):
    """True if the shape draws a fill, a border or an effect of its own (explicitly or through its style)."""
    sppr, style = sp.find("p:spPr", NS), sp.find("p:style", NS)

    def by_style(ref):
        el = style.find(f"a:{ref}", NS) if style is not None else None
        return el is not None and el.get("idx", "0") != "0"

    fill = next((c for c in sppr if local(c) in FILLS), None)
    ln = sppr.find("a:ln", NS)
    line_off = ln is not None and ln.find("a:noFill", NS) is not None
    line_on = ln is not None and any(ln.find(f"a:{t}", NS) is not None for t in ("solidFill", "gradFill", "pattFill"))
    return ((fill is not None and local(fill) != "noFill") or (fill is None and by_style("fillRef"))
            or line_on or (not line_off and by_style("lnRef")))


def make_transparent(sp):
    """Text only: no fill, no border, no shadow — explicit in spPr and in the style references (LibreOffice
    draws a style's shadow even under an empty effectLst)."""
    sppr = sp.find("p:spPr", NS)
    for c in list(sppr):
        if local(c) in FILLS or local(c) in ("effectLst", "effectDag"):
            sppr.remove(c)
    before = [c for c in sppr if local(c) in ("xfrm", "custGeom", "prstGeom")]
    nofill = etree.Element(A + "noFill")
    if before:
        before[-1].addnext(nofill)
    else:
        sppr.insert(0, nofill)
    ln = sppr.find("a:ln", NS)
    if ln is None:
        ln = etree.Element(A + "ln")
    nofill.addnext(ln)
    for c in list(ln):
        ln.remove(c)
    etree.SubElement(ln, A + "noFill")
    ln.addnext(etree.Element(A + "effectLst"))
    style = sp.find("p:style", NS)
    if style is not None:
        for ref in ("lnRef", "fillRef", "effectRef"):
            if style.find(f"a:{ref}", NS) is not None:
                style.find(f"a:{ref}", NS).set("idx", "0")


# ── 1 · ungroup ───────────────────────────────────────────────────────
def children(grp):
    return [c for c in grp if local(c) not in ("nvGrpSpPr", "grpSpPr", "extLst")]


def keep_reason(grp):
    """Why a group has to stay grouped, or None."""
    x = grp.find("p:grpSpPr/a:xfrm", NS)
    if x is None or x.find("a:chExt", NS) is None:
        return "no transform"
    if x.get("rot", "0") != "0" or x.get("flipH") in ("1", "true") or x.get("flipV") in ("1", "true"):
        return "rotated or flipped"
    for c in children(grp):
        if local(c) == "grpSp":
            why = keep_reason(c)
            if why:
                return why
        elif own_xfrm(c) is None:
            return f"child '{cnvpr(c).get('name')}' has no position"
    return None


def flatten(grp):
    """The group's leaf shapes, with positions mapped into the group's parent space."""
    x = grp.find("p:grpSpPr/a:xfrm", NS)
    off, ext, choff, chext = (x.find(f"a:{t}", NS) for t in ("off", "ext", "chOff", "chExt"))
    sx = int(ext.get("cx")) / int(chext.get("cx")) if int(chext.get("cx")) else 1.0
    sy = int(ext.get("cy")) / int(chext.get("cy")) if int(chext.get("cy")) else 1.0
    leaves = []
    for c in children(grp):
        for leaf in flatten(c) if local(c) == "grpSp" else [c]:
            lo, le = own_xfrm(leaf).find("a:off", NS), own_xfrm(leaf).find("a:ext", NS)
            lo.set("x", str(round(int(off.get("x")) + (int(lo.get("x")) - int(choff.get("x"))) * sx)))
            lo.set("y", str(round(int(off.get("y")) + (int(lo.get("y")) - int(choff.get("y"))) * sy)))
            le.set("cx", str(round(int(le.get("cx")) * sx)))
            le.set("cy", str(round(int(le.get("cy")) * sy)))
            leaves.append(leaf)
    return leaves


def effect_par(tgt):
    """The effect node (<p:par> whose cTn has a presetClass) a target belongs to, or None."""
    for par in tgt.iterancestors(f"{{{P_NS}}}par"):
        ctn = par.find("p:cTn", NS)
        if ctn is not None and ctn.get("presetClass") is not None:
            return par
    return None


def timing_block(timing, gid):
    """Why the animations on a group cannot be carried to its children (a trigger, a build entry), or None."""
    if timing is None:
        return None
    for el in timing.iter():
        if el.get("spid") == gid and (local(el) != "spTgt" or effect_par(el) is None):
            return f"{local(el)} on the group"
    return None


def ungroup(sptree, timing, log):
    """Flatten every top-level group in place; returns {group id: [leaf ids]}."""
    flattened = {}
    for grp in sptree.findall("p:grpSp", NS):
        gnv = cnvpr(grp)
        why = keep_reason(grp) or timing_block(timing, gnv.get("id"))
        if why:
            log.append(f"  kept group {gnv.get('name')!r}: {why}")
            continue
        name = gnv.get("name")
        step = name.split(" · ")[0] if " · " in name else None   # "click1" / "start" / "클릭1" / "처음"
        idx = sptree.index(grp)
        leaves = flatten(grp)
        sptree.remove(grp)
        for k, leaf in enumerate(leaves):
            nv = cnvpr(leaf)
            if step and not nv.get("name").startswith(f"{step} · "):
                nv.set("name", f"{step} · {nv.get('name')}")
            sptree.insert(idx + k, leaf)
        flattened[gnv.get("id")] = [cnvpr(leaf).get("id") for leaf in leaves]
        log.append(f"  ungrouped {name!r}: {len(leaves)} shapes")
    return flattened


# ── 2 · animations that pointed at a group ────────────────────────────
def retarget(timing, flattened, log):
    if timing is None:
        return
    changed = False
    for gid, kids in flattened.items():
        for tgt in timing.xpath(f".//p:spTgt[@spid='{gid}']", namespaces=NS):
            par = effect_par(tgt)
            if par.getparent() is None:
                continue  # already replaced through another target of the same effect
            for k, kid in enumerate(kids):
                clone = copy.deepcopy(par)
                for t in clone.xpath(f".//p:spTgt[@spid='{gid}']", namespaces=NS):
                    t.set("spid", kid)
                if k:  # one click still reveals everything at once
                    clone.find("p:cTn", NS).set("nodeType", "withEffect")
                par.addprevious(clone)
            par.getparent().remove(par)
            changed = True
            log.append(f"  animation on group {gid} → {len(kids)} shapes")
    if changed:
        for n, ctn in enumerate(timing.iter(f"{{{P_NS}}}cTn"), 1):  # ids must stay unique
            ctn.set("id", str(n))


# ── 3a · side by side: "완제품 CLI   명령 한 줄로 부른다" ─────────────────
def h_split(sp, new_id, names, log):
    body = sp.find("p:txBody", NS)
    paras = body.findall("a:p", NS) if body is not None else []
    if len(paras) != 1:
        raise Skip(f"--h needs one paragraph, found {len(paras)}")
    p = paras[0]
    if p.find("a:br", NS) is not None or p.find("a:fld", NS) is not None:
        raise Skip("--h paragraph has a line break or field")
    algn = p.find("a:pPr", NS).get("algn", "l") if p.find("a:pPr", NS) is not None else "l"
    if algn != "l":
        raise Skip(f"--h needs a left-aligned paragraph (algn={algn}) — the halves move when either changes")
    runs = p.findall("a:r", NS)
    first = next((run_style(r, body) for r in runs if run_text(r).strip()), None)
    k = next((i for i, r in enumerate(runs) if run_text(r).strip() and run_style(r, body) != first), None)
    if k is None:
        raise Skip("--h found one style only — nothing tells the name from the description")
    li = max(i for i in range(k) if run_text(runs[i]).strip())                    # last name run with text
    di = next(i for i in range(k, len(runs)) if run_text(runs[i]).strip())        # first description run with text
    ws = lambda i, s: width_in(s, run_size(runs[i], body), run_bold(runs[i]))      # measured in that run's style
    lab_sz = max(run_size(runs[i], body) for i in range(li + 1))
    desc_sz = max(run_size(r, body) for r in runs[di:])

    # gap = the whitespace between name and description, as it was
    gap_in = sum(ws(i, run_text(runs[i])) for i in range(li + 1, di))
    raw = run_text(runs[li])
    text, carry = raw.rstrip(), ""
    m = re.search(r"\s(\S+)$", text)
    if m and not re.search(r"\w", m.group(1)):                  # "하네스 = " → "하네스" | "= " to the description
        carry, text = raw[m.start(1):], text[:m.start()].rstrip()
        gap_in += ws(li, raw[len(text):m.start(1)])
    else:
        gap_in += ws(li, raw[len(text):])
    lead = run_text(runs[di])
    gap_in += ws(di, lead[: len(lead) - len(lead.lstrip())])
    label_in = sum(ws(i, run_text(runs[i])) for i in range(li)) + ws(li, text)
    desc_text = carry + "".join(map(run_text, runs[di:])).lstrip()

    off, ext, x, y, cx, cy = frame(sp)
    bpr = body.find("a:bodyPr", NS)
    room = cx / EMU_PER_IN - int(bpr.get("lIns", 91440)) / EMU_PER_IN - int(bpr.get("rIns", 91440)) / EMU_PER_IN
    if lines_needed(p, room, body) > 1:
        log.append(f"  note: '{desc_text[:20]}…' wrapped under the name — it now wraps under itself")
    shift = round(label_in * EMU_PER_IN) + round(gap_in * EMU_PER_IN)
    drop = round((lab_sz - desc_sz) * 0.95 * EMU_PER_PT)        # the smaller run sat on the name's baseline
    anchor = bpr.get("anchor", "t")
    if drop and anchor != "t":
        log.append(f"  note: anchor={anchor} with two sizes — baseline not adjusted, check the render")
        drop = 0

    d = copy.deepcopy(sp)                                       # the description box, copied before any change
    d_runs = d.findall("p:txBody/a:p/a:r", NS)
    for i, dup in enumerate(d_runs[:di]):
        if i == li and carry:
            dup.find("a:t", NS).text = carry
        else:
            dup.getparent().remove(dup)
    d_runs[di].find("a:t", NS).text = lead.lstrip()
    nv, d_nv = cnvpr(sp), cnvpr(d)
    base = nv.get("name")
    d_nv.set("id", new_id)
    d_nv.set("name", f"{base} · {names[1]}")

    for r in runs[li + 1:]:                                     # the name box keeps the name runs only
        p.remove(r)
    runs[li].find("a:t", NS).text = text
    nv.set("name", f"{base} · {names[0]}")
    if paints(sp):
        # a card keeps its frame and fill; the description is a transparent copy, its text pushed past the name
        make_transparent(d)
        d_bpr = d.find("p:txBody/a:bodyPr", NS)
        d_bpr.set("lIns", str(int(bpr.get("lIns", 91440)) + shift))
        d_bpr.set("tIns", str(int(bpr.get("tIns", 45720)) + drop))
        kind = "card + overlay"
    else:
        # two boxes side by side; the name box never wraps and runs up to where the description starts —
        # LibreOffice wraps at the box edge despite wrap="none" and widens Korean/Latin boundaries
        d_off, d_ext = own_xfrm(d).find("a:off", NS), own_xfrm(d).find("a:ext", NS)
        d_off.set("x", str(x + shift))
        d_off.set("y", str(y + drop))
        d_ext.set("cx", str(cx - shift))
        d_ext.set("cy", str(round(cy * desc_sz / lab_sz)))
        bpr.set("wrap", "none")
        ext.set("cx", str(shift))
        kind = "side by side"
    sp.addnext(d)
    log.append(f"  h-split {base!r}: {text!r} | {desc_text!r}  ({kind})")


# ── 3b · stacked: name paragraph over description paragraph(s) ────────
def spacer_for(p, n_lines):
    """Empty paragraph as tall as `p`: same pPr, same size and faces, no text."""
    rpr = p.find("a:r/a:rPr", NS)
    if rpr is None:
        return copy.deepcopy(p)
    sp = etree.Element(A + "p")
    ppr = p.find("a:pPr", NS)
    if ppr is not None:
        sp.append(copy.deepcopy(ppr))
    for _ in range(n_lines - 1):
        etree.SubElement(sp, A + "br").append(copy.deepcopy(rpr))
    end = copy.deepcopy(rpr)
    end.tag = A + "endParaRPr"
    sp.append(end)
    return sp


def v_split(sp, new_id, names, log):
    body = sp.find("p:txBody", NS)
    paras = [p for p in body.findall("a:p", NS)] if body is not None else []
    if len(paras) < 2:
        raise Skip(f"--v needs a name paragraph and a description paragraph, found {len(paras)}")
    bpr = body.find("a:bodyPr", NS)
    _, _, _, _, cx, _ = frame(sp)
    room = cx / EMU_PER_IN - int(bpr.get("lIns", 91440)) / EMU_PER_IN - int(bpr.get("rIns", 91440)) / EMU_PER_IN
    n = [lines_needed(p, room, body) for p in paras]

    over = copy.deepcopy(sp)                                    # carries the description; same frame, on top
    o_paras = over.findall("p:txBody/a:p", NS)
    o_paras[0].addprevious(spacer_for(paras[0], n[0]))
    o_paras[0].getparent().remove(o_paras[0])
    o_nv = cnvpr(over)
    base = cnvpr(sp).get("name")
    o_nv.set("id", new_id)
    o_nv.set("name", f"{base} · {names[1]}")
    card = paints(over)
    if card:  # the card stays underneath; the overlay is text only
        make_transparent(over)

    for p, k in zip(paras[1:], n[1:]):
        p.addprevious(spacer_for(p, k))
        body.remove(p)
    cnvpr(sp).set("name", f"{base} · {names[0]}")
    sp.addnext(over)
    texts = ["".join(t.text or "" for t in p.iter(A + "t")) for p in paras]
    log.append(f"  v-split {base!r}: {texts[0]!r} / {' / '.join(texts[1:])!r}  lines={n}"
               f"{'  (card + overlay)' if card else ''}")


# ── listing ───────────────────────────────────────────────────────────
def describe(sp):
    """Runs per paragraph (B/R + size) and a structural hint: H? one paragraph whose weight or size changes
    once, V? a first paragraph in another weight or size than the next. Color is left out — a colored phrase
    inside a sentence is emphasis far more often than a name."""
    body = sp.find("p:txBody", NS)
    paras = [p for p in body.findall("a:p", NS) if "".join(map(run_text, p.findall("a:r", NS))).strip()]
    placeholder = sp.find("p:nvSpPr/p:nvPr/p:ph", NS) is not None
    shown, styles = [], []
    for p in paras:
        runs = [r for r in p.findall("a:r", NS) if run_text(r).strip()]
        styles.append([run_style(r, body)[:2] for r in runs])
        shown.append(" ".join(f"[{'B' if run_bold(r) else 'R'}{run_size(r, body):g}{'' if placeholder or own_size(r) else '*'} "
                              f"{run_text(r).strip()[:22]!r}]" for r in runs))
    hint = ""
    if len(paras) == 1 and len(styles[0]) >= 2:
        changes = sum(a != b for a, b in zip(styles[0], styles[0][1:]))
        hint = "H?" if changes == 1 else ""
    elif len(paras) >= 2 and styles[0] and styles[1] and styles[0][0] != styles[1][0]:
        hint = "V?"
    return hint, " / ".join(shown)


def list_slide(n, sptree, timing):
    print(f"slide {n}")
    animated = set(timing.xpath(".//p:spTgt/@spid", namespaces=NS)) if timing is not None else set()

    def walk(container, depth):
        for el in container:
            if local(el) == "grpSp":
                nv = cnvpr(el)
                tag = ", animated" if nv.get("id") in animated else ""
                print(f"{'  ' * depth}group {nv.get('id')} {nv.get('name')!r} ({len(children(el))} shapes{tag})")
                walk(el, depth + 1)
            elif local(el) == "sp" and el.find("p:txBody", NS) is not None:
                hint, shown = describe(el)
                if shown:
                    nv = cnvpr(el)
                    print(f"{'  ' * depth}{hint:3} {nv.get('id'):>4} {nv.get('name')!r}  {shown}")

    walk(sptree, 1)


# ── main ──────────────────────────────────────────────────────────────
def slide_parts(z):
    """Slide part names in presentation order — slide N is the Nth sldId, not necessarily slideN.xml."""
    pres = etree.fromstring(z.read("ppt/presentation.xml"))
    rels = etree.fromstring(z.read("ppt/_rels/presentation.xml.rels"))
    target = {r.get("Id"): r.get("Target") for r in rels}
    parts = []
    for sid in pres.iterfind("p:sldIdLst/p:sldId", NS):
        t = target[sid.get(f"{{{R_NS}}}id")]
        parts.append(t.lstrip("/") if t.startswith("/") else os.path.normpath(os.path.join("ppt", t)).replace(os.sep, "/"))
    return parts


def parse_targets(specs, kind, targets):
    for spec in specs:
        m = re.fullmatch(r"(\d+):(\d+(?:,\d+)*)", spec.strip())
        if not m:
            raise SystemExit(f"--{kind} {spec!r}: expected N:ID[,ID...] (slide number : shape ids)")
        targets.setdefault(int(m.group(1)), []).extend((kind, sid) for sid in m.group(2).split(","))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pptx")
    ap.add_argument("--list", action="store_true", help="print groups and text boxes per slide, then stop")
    ap.add_argument("--h", action="append", default=[], metavar="N:ID,ID", help="side-by-side splits on slide N")
    ap.add_argument("--v", action="append", default=[], metavar="N:ID,ID", help="stacked splits on slide N")
    ap.add_argument("--names", default="이름,설명", help="name suffixes for the two halves (default: 이름,설명)")
    ap.add_argument("-o", "--output", help="default: <input>-split.pptx next to the input")
    a = ap.parse_args()

    if not os.path.exists(a.pptx):
        print(f"not found: {a.pptx}", file=sys.stderr)
        return 1
    names = [s.strip() for s in a.names.split(",")]
    if len(names) != 2 or not all(names):
        raise SystemExit("--names takes two suffixes, e.g. 이름,설명")
    targets = {}
    parse_targets(a.h, "h", targets)
    parse_targets(a.v, "v", targets)

    with zipfile.ZipFile(a.pptx) as z:
        parts = slide_parts(z)
        if a.list:
            for n, part in enumerate(parts, 1):
                sld = etree.fromstring(z.read(part))
                list_slide(n, sld.find("p:cSld/p:spTree", NS), sld.find("p:timing", NS))
            return 0
        bad = [n for n in targets if not 1 <= n <= len(parts)]
        if bad:
            raise SystemExit(f"slide {bad[0]} does not exist — the deck has {len(parts)} slides")
        out = a.output or re.sub(r"\.pptx$", "", a.pptx, flags=re.I) + "-split.pptx"
        if os.path.abspath(out) == os.path.abspath(a.pptx):
            raise SystemExit("refusing to write over the input — pass another -o")

        new_parts, problems = {}, []
        for n, part in enumerate(parts, 1):
            sld = etree.fromstring(z.read(part))
            sptree, timing = sld.find("p:cSld/p:spTree", NS), sld.find("p:timing", NS)
            if sptree.find("p:grpSp", NS) is None and n not in targets:
                continue
            log = []
            flattened = ungroup(sptree, timing, log)
            retarget(timing, flattened, log)
            next_id = max(int(e.get("id")) for e in sld.iter(f"{{{P_NS}}}cNvPr")) + 1
            for kind in ("h", "v"):
                for k, sid in targets.get(n, []):
                    if k != kind:
                        continue
                    found = sptree.xpath(f"p:sp[p:nvSpPr/p:cNvPr/@id='{sid}']", namespaces=NS)
                    try:
                        if not found:
                            raise Skip("no such shape at the top level (after ungrouping)")
                        (h_split if kind == "h" else v_split)(found[0], str(next_id), names, log)
                        next_id += 1
                    except Skip as e:
                        problems.append(f"slide {n} shape {sid}: {e}")
            ids = [e.get("id") for e in sld.iter(f"{{{P_NS}}}cNvPr")]
            if len(ids) != len(set(ids)):
                problems.append(f"slide {n}: duplicate shape ids")
            if log:
                print(f"slide {n}", *log, sep="\n")
                new_parts[part] = etree.tostring(sld, xml_declaration=True, encoding="UTF-8", standalone=True)
        if problems:
            print("nothing written:", *problems, sep="\n  ", file=sys.stderr)
            return 1

        fd, tmp = tempfile.mkstemp(suffix=".pptx", dir=os.path.dirname(os.path.abspath(out)))
        os.close(fd)
        with zipfile.ZipFile(tmp, "w") as dst:
            for info in z.infolist():
                dst.writestr(info, new_parts.get(info.filename, z.read(info.filename)), compress_type=info.compress_type)
    os.replace(tmp, out)
    print(f"{len(new_parts)} slide(s) changed → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
