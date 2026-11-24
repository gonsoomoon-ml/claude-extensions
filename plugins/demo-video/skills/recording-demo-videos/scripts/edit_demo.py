#!/usr/bin/env python3
"""Turn raw Playwright recordings (webm + camlog.json) into LinkedIn-ready MP4 clips.

  python3 edit_demo.py clip raw/intro.webm --script scripts/intro.json
  python3 edit_demo.py clip raw/intro.webm --title "…" --subtitle "…"      # no story: shot labels as captions
  python3 edit_demo.py reel reel.json --out reel.mp4
  python3 edit_demo.py voice lines.json --out voice/ [--readings readings.json] [--hangul-only]   # Amazon Polly narration

`clip` trims the page-load lead-in, burns a title card and lower-third captions, plays the take at 1.25x
(DEFAULT_SPEED; set "speed" in the script to change it, e.g. 4 for a waiting stretch, 1 for real time) and
encodes H.264 1080p30 + silent AAC. With `--script` the captions are the beats of a script JSON, each anchored
to a camlog event (see script_time). Without a script the captions fall back to the camera shot labels,
which describe where the camera looks, not what the viewer should understand.
`reel` concatenates trimmed windows from several finished clips and re-encodes the join into ONE H.264 stream
(1.3.0: a stream-copied concat carried a two-entry edit list that made QuickTime freeze mid-video; `--copy` keeps
the old behaviour). Default output: High 4.1, CRF 23, 3 Mbit/s cap, keyframe every 2 s, faststart, one file.
A reel segment may carry a narration (1.4.0): "voice": <audio file>, "voice_at": <seconds into the segment>, "group";
a segment may also be a picture, {"image": <png>, "seconds": <n>}. The reel then holds a segment's last frame until
its voice has ended (see schedule), mixes the voices into one track at -16 LUFS ("loudness") and writes
<out stem>.voice.json with the measured times. A manifest with no "voice" and no "image" runs as before.
Nothing about the recorded UI is altered; only overlays are added. Temp files are removed when each command ends.

Look (fixed here so every clip of a set matches; change the constants, re-run every clip):
  title      bold 58 px at x 96, y h-260, 0.2-4.2 s     subtitle  regular 30 px at y h-170, 0.5-4.2 s
  beat       bold 34 px at x 96, y h-150 (y 120 with "pos": "top"), white on a blue box 0x1f6feb@0.82, border 18
             (1.3.0: one look for every caption, visible on dark UIs; DEMO_BEAT_BOX env overrides the box colour;
             "style": "insight" is accepted and looks the same)   tag  mono 22 px top-right (off unless --tag)
  every caption fades 0.35 s in and out; one caption at a time; a beat never starts under the title card
  fonts: DEMO_FONT_BOLD / DEMO_FONT_REGULAR / DEMO_FONT_MONO env, else Nanum, else fc-match (Korean needs a CJK font)

The raw input can also be a screen recording (.mov/.mp4) with no camlog: then every beat "at" is raw seconds
of that file. Crop black bars first with ffmpeg (-vf crop=...) so the frame is the UI only.

Script JSON:
  {"title": "03 판단을 넘깁니다", "subtitle": "…", "start": null, "end": null,   # optional "tag": persistent corner label, off by default
   "speed": 1.25,                             # default 1.25; 4 for waits (agent turns, cloud calls); "at" stays raw seconds
   "beats": [
     {"at": "shot:stage", "text": "Laya가 다음 스킬을 판단합니다", "dur": 5},
     {"at": "caption:System 2에 복구", "offset": 0.5, "text": "확률 0.95인데도 규칙이 이관합니다"},
     {"at": "note:play", "text": "…"},          # any rec.note(kind)
     {"at": "shot:stage#2", "text": "…"},       # 2nd occurrence
     {"at": 41.0, "text": "…", "dur": 5.5},         # raw seconds; dur = end the caption before the next action
     {"at": "shot:table", "text": "…", "pos": "top"}  # caption at the top when the lower third hides the evidence
   ]}
  Highlight boxes (1.4.0): a beat may add "box": [x, y, w, h] | [[x, y, w, h], ...] | "shot:<key>[#n]" | "mark:<key>[#n]"
  (frame pixels; the last two use the camlog entry's rect, grown by the border + 4 px). A red border (8 px, a dark line
  outside it) shows from the caption's start + "box_delay" (default 1.4 / speed + 0.2 s on a "shot:" anchor, else 0) to its end,
  or for "box_dur" seconds of the clip from its start (a number above 0; the box must not outlast its caption).
  "hold": true on the LAST beat keeps its caption and boxes to the clip's last frame with no fade-out ("box_dur" can end
  the boxes sooner). A box under the caption, outside the frame, that can never show (its delay outlasts its caption),
  or that shows while the camera moves stops the clip before ffmpeg starts: a camlog shot moves the camera from its
  time for its "move" seconds (1.4 when the camlog does not say), unless its camera values equal the shot's before.
  For a script that uses a box or a hold, each caption's and box's time in the clip is printed on stderr.
  Beat duration defaults to the gap to the next beat (max 7 s, min 1.5 s). `#n` counts occurrences of that
  same key / substring / kind only. Raw seconds are seconds from launch and are not validated against the
  camlog. A context fact with no event of its own (a batch statistic, a caveat) belongs on a late summary
  shot, e.g. the stats or wide shot, not mid-action.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def _font(env: str, preferred: str, pattern: str) -> str:
    """Font file for drawtext: $env override, else the preferred file if installed, else fc-match."""
    import os
    if os.environ.get(env):
        return os.environ[env]
    if Path(preferred).exists():
        return preferred
    out = subprocess.run(["fc-match", "-f", "%{file}", pattern], capture_output=True, text=True)
    return out.stdout.strip() or preferred

# fallback patterns ask fontconfig for a Korean-capable face: plain "sans" returned DejaVu, which draws Hangul as boxes
FONT_BOLD = _font("DEMO_FONT_BOLD", "/usr/share/fonts/truetype/nanum/NanumSquareB.ttf", "sans:bold:lang=ko")
FONT_REG = _font("DEMO_FONT_REGULAR", "/usr/share/fonts/truetype/nanum/NanumSquareR.ttf", "sans:lang=ko")
FONT_MONO = _font("DEMO_FONT_MONO", "/usr/share/fonts/truetype/nanum/NanumGothicCoding.ttf", "monospace:lang=ko")
W, H, FPS = 1920, 1080, 30
DEFAULT_SPEED = 1.25  # a demo at real time drags; 1.25x reads as a confident pace without looking sped up
# caption box: blue, so it stays visible on dark UIs (the old near-black box vanished on dark pages and terminals)
BEAT_BOX = os.environ.get("DEMO_BEAT_BOX", "0x1f6feb@0.82")
BEAT_SIZE = 34
BEAT_BORDER = 18
BEAT_Y_BOTTOM, BEAT_Y_TOP = H - 150, 120   # caption y; caption_y() writes them as drawtext takes them, "h-150" and "120"
NEW_BEAT_FIELDS = ("box", "box_delay", "box_dur", "hold")   # 1.4.0; a script with none of them prints as in 1.3.0
# highlight boxes (1.4.0): a red border with a thin dark line just outside it, so the box shows on red or orange UIs too
HIGHLIGHT = os.environ.get("DEMO_HIGHLIGHT", "0xff2a2a@0.95")
HIGHLIGHT_THICK = int(os.environ.get("DEMO_HIGHLIGHT_THICK", "8"))
HIGHLIGHT_OUTLINE = 2
CAMERA_MOVE = 1.4  # seconds the recorder's camera takes to arrive on a shot (raw time)
CAMERA_MARGIN = 0.001  # raw seconds: a box's times come back from clip seconds with float rounding (a beat's own shot)
CAMERA_SAME_PX, CAMERA_SAME_ZOOM = 0.01, 1e-4   # camera values this close are one view (a shot that moves nothing)
# the end written into the filter of what stays to the clip's last frame (the tag, a held caption and the boxes that end
# with it): that frame sits on a 1/30 s slot that can lie past the clip's stated end, which the filter writes to 0.01 s
PAST_THE_END = 10_000


def run(cmd: list[str]) -> None:
    print("+", " ".join(shlex.quote(c) for c in cmd), file=sys.stderr)
    subprocess.run(cmd, check=True)


def probe_duration(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         check=True, capture_output=True, text=True).stdout.strip()
    return float(out)


def drawtext(textfile: Path, *, font: str, size: int, x: str, y: str, start: float, end: float,
             color: str = "white", box: bool = True, alpha_fade: bool = True,
             boxcolor: str = BEAT_BOX, fade_out: bool = True) -> str:
    enable = f"between(t\\,{start:.2f}\\,{end:.2f})"
    # expansion=none: the text is literal (a '%' would otherwise start a drawtext expansion sequence)
    parts = [f"drawtext=fontfile={font}", f"textfile={textfile}", "expansion=none", f"fontsize={size}", f"fontcolor={color}",
             f"x={x}", f"y={y}", f"enable='{enable}'"]
    if box:
        parts += ["box=1", f"boxcolor={boxcolor}", f"boxborderw={BEAT_BORDER}"]
    if alpha_fade:
        # fade in/out over 0.35 s inside the enable window (fade_out=False: a held caption stays to the last frame)
        tail = f"if(lt({end:.2f}-t\\,0.35)\\,({end:.2f}-t)/0.35\\,1)" if fade_out else "1"
        fade = f"if(lt(t-{start:.2f}\\,0.35)\\,(t-{start:.2f})/0.35\\,{tail})"
        parts.append(f"alpha='{fade}'")
    return ":".join(parts)


def script_time(at, log: list[dict]) -> float:
    """Resolve a beat anchor to raw seconds. Forms: number | 'shot:<key>[#n]' | 'mark:<key>[#n]' |
    'caption:<substring>[#n]' | 'note:<kind>[#n]' | '<kind>[#n]' (any camlog kind, e.g. 'scene_end', 'play').
    A 'mark' without a key matches every entry of kind mark, as in 1.3.0 (rec.note('mark'))."""
    if isinstance(at, (int, float)):
        return float(at)
    spec, _, nth = str(at).partition("#")
    n = int(nth) if nth else 1
    kind, _, arg = spec.partition(":")
    if kind == "note":
        kind, arg = arg, ""
    if kind == "shot" or (kind == "mark" and arg):
        hits = [e for e in log if e["kind"] == kind and e.get("key") == arg]
    elif kind == "caption":
        hits = [e for e in log if e["kind"] == "caption" and arg in e.get("text", "")]
    else:
        hits = [e for e in log if e["kind"] == kind]
    if len(hits) < n:
        raise SystemExit(f"script anchor not found in camlog: {at!r}")
    return float(hits[n - 1]["t"])


def _bad_box(box, why: str):
    raise SystemExit(f"box {box!r}: {why}")


def _frame_rect(box, grow: int = 0) -> tuple[int, int, int, int]:
    """A rectangle [x, y, w, h] grown by `grow` px on each side and clipped to the frame; aborts when nothing is left."""
    try:
        x, y, w, h = (int(round(float(v))) for v in box)
    except (TypeError, ValueError):
        _bad_box(box, "needs four numbers [x, y, w, h]")
    x0, y0, x1, y1 = x - grow, y - grow, x + w + grow, y + h + grow
    if grow:
        x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
    if w <= 0 or h <= 0 or x0 < 0 or y0 < 0 or x1 > W or y1 > H or x1 <= x0 or y1 <= y0:
        _bad_box(box, f"has no size or lies outside the {W}x{H} frame")
    return x0, y0, x1 - x0, y1 - y0


def beat_boxes(beat: dict, log: list[dict]) -> list[tuple[int, int, int, int]]:
    """The rectangles a beat's "box" asks for, as they will be drawn. Numbers are drawn as given; a camlog rect
    ("shot:<key>[#n]" / "mark:<key>[#n]") is the element's own bounds, so it is grown by the border + 4 px."""
    box = beat.get("box")
    if box is None or box == []:
        return []
    if isinstance(box, str):
        spec, _, nth = box.partition("#")
        kind, _, key = spec.partition(":")
        n = int(nth) if nth else 1
        hits = [e for e in log if e["kind"] == kind and e.get("key") == key] if kind in ("shot", "mark") else []
        if len(hits) < n or not hits[n - 1].get("rect"):
            _bad_box(box, "has no rect in the camlog (use 'shot:<key>' or 'mark:<key>' of an element the recorder measured)")
        return [_frame_rect(hits[n - 1]["rect"], grow=HIGHLIGHT_THICK + 4)]
    if not isinstance(box, (list, tuple)):
        _bad_box(box, "needs [x, y, w, h], a list of them, or 'shot:<key>' / 'mark:<key>'")
    rects = box if isinstance(box[0], (list, tuple)) else [box]
    return [_frame_rect(r) for r in rects]


def box_delay(beat: dict, speed: float) -> float:
    """Seconds after the caption starts that its box appears: the camera needs CAMERA_MOVE (raw) to arrive on a shot."""
    if "box_delay" in beat:
        return float(beat["box_delay"])
    return CAMERA_MOVE / speed + 0.2 if str(beat.get("at", "")).startswith("shot:") else 0.0


def box_dur(beat: dict) -> float | None:
    """Seconds of the clip a beat's boxes show, counted from their start ("box_dur"); None without it: they show until
    the caption ends. Stops unless it is a number above 0."""
    if "box_dur" not in beat:
        return None
    value = beat["box_dur"]
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not value > 0:
        raise SystemExit(f"box_dur on beat {beat['text']!r} must be a number of seconds above 0, not {value!r}")
    return float(value)


def same_view(a, b) -> bool:
    """Two camlog camera values {x, y, k} that frame the same view: focusing one element again gives its numbers back
    with float noise (1e-4 px seen), which no frame shows."""
    try:
        return (abs(a["x"] - b["x"]) <= CAMERA_SAME_PX and abs(a["y"] - b["y"]) <= CAMERA_SAME_PX
                and abs(a["k"] - b["k"]) <= CAMERA_SAME_ZOOM)
    except (TypeError, KeyError):
        return False


def camera_moves(log: list[dict]) -> list[tuple[dict, float, float]]:
    """The camera's moves in a camlog, as (shot, from, to) in the take's seconds. A shot moves the camera from its time
    for its "move" seconds (the recorder writes them for a shot of its own length), else CAMERA_MOVE; a shot whose
    selector matched nothing ("missing") or whose camera values equal the previous shot's (same_view) moves nothing."""
    moves, before = [], None
    for e in log:
        if e["kind"] != "shot" or e.get("missing"):
            continue
        camera = e.get("camera")
        if not same_view(camera, before):
            t = float(e["t"])
            moves.append((e, t, t + float(e.get("move", CAMERA_MOVE))))
        before = camera
    return moves


def caption_y(pos: str | None) -> str:
    """The beat caption's y as the drawtext filter takes it: BEAT_Y_TOP with "pos": "top", else BEAT_Y_BOTTOM counted
    from the frame's bottom ("120", "h-150")."""
    return str(BEAT_Y_TOP) if pos == "top" else f"h-{H - BEAT_Y_BOTTOM}"


def caption_band(pos: str | None) -> tuple[int, int]:
    """Top and bottom y of the beat caption's box ("top" or the lower third), one line of text."""
    y = BEAT_Y_TOP if pos == "top" else BEAT_Y_BOTTOM
    return y - BEAT_BORDER, y + round(BEAT_SIZE * 1.3) + BEAT_BORDER


def drawbox(rect, *, start: float, end: float) -> list[str]:
    """ffmpeg filters for one highlight box: the dark outline just outside the red border, then the border
    (drawbox draws inside the rectangle it is given)."""
    enable = f"enable='between(t\\,{start:.2f}\\,{end:.2f})'"
    x, y, w, h = rect
    o = HIGHLIGHT_OUTLINE
    ox, oy = max(0, x - o), max(0, y - o)
    ow, oh = min(W, x + w + o) - ox, min(H, y + h + o) - oy
    return [f"drawbox=x={ox}:y={oy}:w={ow}:h={oh}:color=0x101010@0.9:t={o}:{enable}",
            f"drawbox=x={x}:y={y}:w={w}:h={h}:color={HIGHLIGHT}:t={HIGHLIGHT_THICK}:{enable}"]


def beat_layout(beats: list[dict], log: list[dict], *, start: float, end: float, speed: float, title) -> list[dict]:
    """When and where each beat of a script shows in its clip, checked before ffmpeg starts.

    The beats in time order, each {"beat": the beat, "caption": (start, end) in clip seconds, or None when the caption
    has under 1 s of room and is left out, "boxes": [(x, y, w, h), ...], "box": (start, end) in clip seconds while the
    boxes show (from the caption's start + box_delay to the caption's end, or for box_dur seconds), "box_raw": the
    same in the take's seconds (start + t * speed); both None without boxes}. Stops on a box outside the frame, a
    box_dur that is not a number above 0 or has no box, a hold on a beat that is not the last, a box that can never
    show, a box_dur that runs past its caption's end, a box under its caption's band, and a box that shows while the
    camera moves (camera_moves: from a shot's time until the camera stops), whatever the beat is anchored to.
    """
    rel = lambda t: (t - start) / speed  # noqa: E731
    timed = sorted(((rel(script_time(b["at"], log) + float(b.get("offset", 0))), b) for b in beats), key=lambda x: x[0])
    boxes = [beat_boxes(b, log) for _, b in timed]  # every box's frame check comes first
    for (_, b), rects in zip(timed, boxes):
        if "box_dur" in b and not rects:
            raise SystemExit(f"box_dur on beat {b['text']!r} has no box to end: give the beat a \"box\" or leave "
                             f"\"box_dur\" out")
    lengths = [box_dur(b) for _, b in timed]
    for _, b in timed[:-1]:
        if b.get("hold"):
            raise SystemExit(f"hold on beat {b['text']!r} is not allowed: only the clip's last beat can be held")
    moves = camera_moves(log)
    layout = []
    for i, (t0, b) in enumerate(timed):
        t0 = max(t0, 4.4 if title else 0.2 if speed == 1 else 0.0)  # never under the title card
        nxt = timed[i + 1][0] if i + 1 < len(timed) else rel(end)
        dur = float(b.get("dur", min(7.0, nxt - t0 - 0.3)))
        t1 = rel(end) if b.get("hold") else min(t0 + max(dur, 1.5), rel(end) - 0.1)
        item = {"beat": b, "caption": (t0, t1) if t1 - t0 >= 1.0 else None, "boxes": boxes[i], "box": None, "box_raw": None}
        layout.append(item)
        if not boxes[i]:
            continue
        # a box that can never show is a mistake in the script, not something to skip with a note
        if item["caption"] is None:
            raise SystemExit(f"box of {b['text']!r} can never show: its caption has no room ({t1 - t0:.2f} s, "
                             f"under 1 s) and is left out")
        b0 = t0 + box_delay(b, speed)
        if b0 >= t1:
            raise SystemExit(f"box of {b['text']!r} can never show: it waits {b0 - t0:.2f} s (box_delay) and its caption "
                             f"lasts {t1 - t0:.2f} s; shorten \"box_delay\" or lengthen the caption")
        b1 = t1 if lengths[i] is None else b0 + lengths[i]
        if round(b1 - t1, 6) > 0:  # compared to the microsecond: a box_dur written to the caption's end is that end
            ends = "its held caption ends with the clip at" if b.get("hold") else "its caption ends at"
            raise SystemExit(f"box_dur on beat {b['text']!r} runs past its caption: the box shows from {b0:.2f} s and "
                             f"would end at {b1:.2f} s of the clip, {ends} {t1:.2f} s; shorten \"box_dur\" to "
                             f"{t1 - b0:.2f} s or less")
        b1 = min(b1, t1)
        band = caption_band(b.get("pos"))
        for r in boxes[i]:
            if r[1] < band[1] and r[1] + r[3] > band[0]:
                raise SystemExit(f"box {list(r)} crosses the caption band y {band[0]}-{band[1]} (pos={b.get('pos') or 'bottom'}): "
                                 f"move the box or set \"pos\" to the other edge")
        lo, hi = start + b0 * speed, start + b1 * speed  # the box's time in the take's seconds
        if lengths[i] is not None:
            advice = 'shorten "box_dur" or move the box'
        elif b.get("hold"):
            advice = 'give the box a "box_dur" or move the box'  # a held caption cannot be shortened
        else:
            advice = "shorten the caption or move the box"
        for e, moved, stops in moves:
            if moved < hi - CAMERA_MARGIN and stops > lo + CAMERA_MARGIN:
                # the box_delay that starts the box as the camera stops, rounded up to 0.01 s
                wait = math.ceil(((stops - start) / speed - t0) * 100 - 1e-6) / 100
                fits = t0 + wait < t1
                if moved <= lo + CAMERA_MARGIN:   # the box would start while the camera is still on its way
                    raise SystemExit(
                        f"the camera is still moving to shot {e.get('key')!r} (from {moved:.2f} s, it stops at "
                        f"{stops:.2f} s) when the box of {b['text']!r} starts (it shows {lo:.2f}-{hi:.2f} s): "
                        + (f'start the box after the camera stops with "box_delay": {wait:.2f}' if fits else
                           "its caption ends before the camera stops: anchor the beat later or lengthen its caption"))
                raise SystemExit(f"the camera moves to shot {e.get('key')!r} at {moved:.2f} s (it stops at {stops:.2f} s) "
                                 f"while the box of {b['text']!r} shows ({lo:.2f}-{hi:.2f} s): {advice}"
                                 + (f', or start the box after the camera stops with "box_delay": {wait:.2f}'
                                    if fits else ""))
        item.update(box=(b0, b1), box_raw=(lo, hi))
    return layout


def read_camlog(raw: Path) -> list[dict]:
    """The camlog entries of a Playwright take (<name>.camlog.json beside <name>.webm); none for a screen recording."""
    camlog = raw.with_suffix("").with_suffix(".camlog.json") if raw.suffix == ".webm" else None
    return json.loads(camlog.read_text())["log"] if camlog and camlog.exists() else []


def clip_span(raw: Path, log: list[dict], start: float | None, end: float | None) -> tuple[float, float]:
    """The take's seconds a clip covers: `start` defaults to 0.4 s before the first camera shot (the page-load lead-in
    is cut), `end` to the take's end."""
    shots = [e for e in log if e["kind"] == "shot"]
    if start is None:
        start = max(0.0, (shots[0]["t"] - 0.4) if shots else 0.0)
    return start, probe_duration(raw) if end is None else end


def build_clip(raw: Path, out: Path, title: str | None, subtitle: str | None, start: float | None,
               end: float | None, captions: bool, tag: str | None, script: Path | None = None) -> None:
    log = read_camlog(raw)
    story = json.loads(script.read_text()) if script else None
    if story:
        title = title or story.get("title")
        subtitle = subtitle or story.get("subtitle")
        tag = tag or story.get("tag")
        start = start if start is not None else story.get("start")
        end = end if end is not None else story.get("end")
    shots = [e for e in log if e["kind"] == "shot"]
    start, end = clip_span(raw, log, start, end)
    speed = float(story.get("speed", DEFAULT_SPEED)) if story else DEFAULT_SPEED  # beat "at" stays raw seconds
    with tempfile.TemporaryDirectory(prefix="edit-") as tmp_name:  # drawtext files; removed when the encode is done
        tmp = Path(tmp_name)
        _encode_clip(raw, out, title, subtitle, tag, start, end, captions, story, log, shots, speed, tmp)


def _encode_clip(raw: Path, out: Path, title, subtitle, tag, start: float, end: float, captions: bool,
                 story, log: list[dict], shots: list[dict], speed: float, tmp: Path) -> None:
    filters = ([f"setpts=PTS/{speed}"] if speed != 1 else []) + [f"fps={FPS}", f"scale={W}:{H}:flags=lanczos", "format=yuv420p"]
    rel = lambda t: (t - start) / speed  # noqa: E731
    placed = 0
    if title:
        (tmp / "title.txt").write_text(title)
        filters.append(drawtext(tmp / "title.txt", font=FONT_BOLD, size=58, x="96", y="h-260", start=0.2, end=4.2))
        if subtitle:
            (tmp / "subtitle.txt").write_text(subtitle)
            filters.append(drawtext(tmp / "subtitle.txt", font=FONT_REG, size=30, x="96", y="h-170", start=0.5, end=4.2))
    if tag:
        (tmp / "tag.txt").write_text(tag)
        filters.append(drawtext(tmp / "tag.txt", font=FONT_MONO, size=22, x="w-tw-40", y="h-58", start=0, end=PAST_THE_END,
                                color="0xcfd8dc", alpha_fade=False))
    if story and story.get("beats"):
        # the times in the finished clip, for a reel's voice_at; printed for a script that uses a 1.4.0 field only
        times = any(k in b for b in story["beats"] for k in NEW_BEAT_FIELDS)
        for i, item in enumerate(beat_layout(story["beats"], log, start=start, end=end, speed=speed, title=title)):
            b = item["beat"]
            if item["caption"] is None:
                print(f"skip beat (no room): {b['text']!r}", file=sys.stderr)
                continue
            t0, t1 = item["caption"]
            if times:
                n = next(n for n, x in enumerate(story["beats"], 1) if x is b)
                where = f", box {item['box'][0]:.2f}-{item['box'][1]:.2f} s" if item["box"] else ""
                print(f"clip: beat {n}: caption {t0:.2f}-{t1:.2f} s{where}: {b['text']!r}", file=sys.stderr)
            f = tmp / f"beat{i}.txt"
            f.write_text(b["text"])
            y = caption_y(b.get("pos"))  # pos=top when the lower third would cover the evidence
            held = bool(b.get("hold"))  # its caption, and the boxes that end with it, stay to the clip's very last frame
            # one look for every beat ("style": "insight" is accepted for old scripts and renders the same)
            filters.append(drawtext(f, font=FONT_BOLD, size=BEAT_SIZE, x="96", y=y, start=t0,
                                    end=PAST_THE_END if held else t1, color="0xffffff", fade_out=not held))
            placed += 1
            if item["boxes"]:
                b0, b1 = item["box"]
                b1 = PAST_THE_END if held and round(t1 - b1, 6) == 0 else b1
                for r in item["boxes"]:
                    filters += drawbox(r, start=b0, end=b1)
    elif captions:
        labelled = [s for s in shots if s.get("label") and rel(s["t"]) > 4.6]
        for i, shot in enumerate(labelled):
            t0 = rel(shot["t"]) + 0.9  # let the camera settle first
            nxt = labelled[i + 1]["t"] if i + 1 < len(labelled) else end
            t1 = min(t0 + 4.5, rel(nxt) + 0.4, rel(end) - 0.1)
            if t1 - t0 < 1.2:
                continue
            f = tmp / f"cap{i}.txt"
            f.write_text(shot["label"])
            filters.append(drawtext(f, font=FONT_BOLD, size=BEAT_SIZE, x="96", y=caption_y(None), start=t0, end=t1,
                                    color="0xffffff"))
            placed += 1
    vf = ",".join(filters)
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-y", "-v", "error", "-stats", "-ss", f"{start:.3f}", "-to", f"{end:.3f}", "-i", str(raw),
           "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
           "-vf", vf, "-c:v", "libx264", "-preset", "slow", "-crf", "19", "-profile:v", "high", "-level", "4.1",
           "-c:a", "aac", "-b:a", "96k", "-shortest", "-movflags", "+faststart", str(out)]
    run(cmd)
    print(json.dumps({"out": str(out), "seconds": round(rel(end), 2), "captions": placed}))


def probe_size(path: Path) -> str:
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                          "-of", "csv=s=x:p=0", str(path)], check=True, capture_output=True, text=True).stdout.strip()
    return out.rstrip("x")


# final reel encode: one uniform stream that QuickTime, browsers and LinkedIn all take; the cap keeps zoom transitions
# from spiking past what a remote download or a phone can stream
REEL_ENCODE = ["-c:v", "libx264", "-preset", "medium", "-crf", "23", "-maxrate", "3M", "-bufsize", "3M", "-profile:v", "high",
               "-level", "4.1", "-refs", "4", "-g", "60", "-keyint_min", "30", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k"]


def build_reel(spec: Path, out: Path, copy: bool = False) -> None:
    """spec: {"segments": [{"file": "...mp4", "start": 0, "end": 25, "fade_in": 0}, ...], "fade": 0.4}
    copy=True keeps the 1.2.0 behaviour (stream-copy concat, two-entry edit list) instead of the final re-encode.
    A manifest with a "voice" or an "image" on any segment is a narrated reel (build_narrated_reel); the rest of this
    function is the 1.3.0 reel, unchanged."""
    cfg = json.loads(spec.read_text())
    if any("voice" in seg or "image" in seg for seg in cfg["segments"]):
        if copy:
            raise SystemExit("reel: --copy cannot carry voices or picture segments; leave it out")
        build_narrated_reel(spec, out)
        return
    fade = float(cfg.get("fade", 0.4))
    # concat with stream copy needs identical streams; a mixed-size reel fails late with a cryptic error, so check first
    sizes = {seg["file"]: probe_size(Path(seg["file"])) for seg in cfg["segments"]}
    if len(set(sizes.values())) > 1:
        raise SystemExit("reel segments differ in resolution: " + ", ".join(f"{f} {s}" for f, s in sizes.items()))
    with tempfile.TemporaryDirectory(prefix="reel-") as tmp_name:  # re-encoded parts; removed after the concat
        tmp = Path(tmp_name)
        parts = []
        for i, seg in enumerate(cfg["segments"]):
            src = Path(seg["file"])
            s, e = float(seg.get("start", 0)), float(seg.get("end") or probe_duration(src))
            d = e - s
            part = tmp / f"part{i:02d}.mp4"
            # per-segment "fade_in"/"fade_out" (0 = hard cut) join pieces of one scene without a dip to black
            fi, fo = float(seg.get("fade_in", fade)), float(seg.get("fade_out", fade))
            vf = ",".join([f"fade=t=in:st=0:d={fi}"] * (fi > 0) + [f"fade=t=out:st={max(0, d - fo):.2f}:d={fo}"] * (fo > 0)) or "null"
            af = ",".join([f"afade=t=in:st=0:d={fi}"] * (fi > 0) + [f"afade=t=out:st={max(0, d - fo):.2f}:d={fo}"] * (fo > 0)) or "anull"
            run(["ffmpeg", "-y", "-v", "error", "-ss", f"{s:.3f}", "-to", f"{e:.3f}", "-i", str(src), "-vf", vf, "-af", af,
                 "-c:v", "libx264", "-preset", "slow", "-crf", "19", "-c:a", "aac", "-b:a", "96k", str(part)])
            parts.append(part)
        lst = tmp / "list.txt"
        lst.write_text("".join(f"file '{p}'\n" for p in parts))
        out.parent.mkdir(parents=True, exist_ok=True)
        if copy:
            run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", "-movflags", "+faststart", str(out)])
        else:
            joined = tmp / "joined.mp4"
            run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(joined)])
            run(["ffmpeg", "-y", "-v", "error", "-i", str(joined), *REEL_ENCODE, "-movflags", "+faststart", str(out)])
    print(json.dumps({"out": str(out), "seconds": round(probe_duration(out), 1), "parts": len(parts)}))

# ---------------------------------------------------------------- narrated reel (voices, held frames, picture segments)

VOICE_GAP = 0.6          # seconds of silence at least between two voices (manifest "voice_gap")
VOICE_TAIL = 1.0         # seconds the reel runs on after the last voice (manifest "voice_tail")
VOICE_LOUDNESS = -16.0   # integrated loudness of the voice track, LUFS (manifest "loudness")
VOICE_TRUE_PEAK = -1.5   # dBTP
VOICE_LOUDNESS_TOLERANCE = 1.5   # LU a reel may stay under "loudness" with one gain (check_demo.py audit's tolerance)
VOICE_RATE = 48000
# ffmpeg 4.4's loudnorm applies one gain only when the track's loudness range fits its target range; with a narrower
# target it compresses instead, which changes the voices' levels against each other and can miss the target by over 1 LU
LOUDNORM_LRA = 20        # the widest range ffmpeg 4.4 accepts
WARN_HOLD, WARN_HOLD_SHARE, WARN_VOICE = 6.0, 0.30, 14.0   # reported in <out>.voice.json, not fatal


def schedule(segments: list[dict], gap: float = VOICE_GAP, tail: float = VOICE_TAIL) -> list[dict]:
    """How long each segment's last frame is held so that voices never overlap and the screen never runs ahead of a voice.

    In, per segment: "seconds"; for a voiced one "voice_seconds" and "voice_at" (seconds into the segment, default 0);
    optional "group". Out, per segment: "hold" and "start" (in the reel, holds counted); "voice_start" and "voice_end"
    for a voiced one. A voice may run on over the following segments that share its non-empty group (and so have no
    voice: they end at the next voiced segment). For each voiced segment a, in order, with b the next voiced segment
    and c the last segment of a's run-on range (a itself when the range is empty):
      1. if the voice ends after c ends, c is held by the difference;
      2. if b's voice would start less than `gap` after this voice ends, the segment just before b is held by the
         missing time;
      3. after the last voice the reel runs at least `tail` longer: its last segment is held by the missing time.
    Every start is counted with the holds already given.
    """
    n = len(segments)
    hold = [0.0] * n
    voiced = [i for i, s in enumerate(segments) if "voice_seconds" in s]

    def start(i: int) -> float:
        return sum(float(segments[j]["seconds"]) + hold[j] for j in range(i))

    def voice(i: int) -> tuple[float, float]:
        t0 = start(i) + float(segments[i].get("voice_at", 0))
        return t0, t0 + float(segments[i]["voice_seconds"])

    for k, a in enumerate(voiced):
        b = voiced[k + 1] if k + 1 < len(voiced) else None
        group, c = segments[a].get("group"), a
        while group not in (None, "") and c + 1 < (n if b is None else b) and segments[c + 1].get("group") == group:
            c += 1
        _, end = voice(a)
        c_end = start(c + 1)
        if end > c_end:
            hold[c] += end - c_end
        if b is not None:
            next_start, _ = voice(b)
            if next_start < end + gap:
                hold[b - 1] += end + gap - next_start
        elif start(n) < end + tail:
            hold[n - 1] += end + tail - start(n)
    plan = []
    for i in range(n):
        p = {"hold": hold[i], "start": start(i)}
        if i in voiced:
            p["voice_start"], p["voice_end"] = voice(i)
        plan.append(p)
    return plan


def _manifest_object(pairs: list) -> dict:
    """json object hook: a "voice" given twice in one segment keeps both values (as a list, which the checks refuse);
    plain json.loads would keep the last one without a word."""
    obj = {}
    for key, value in pairs:
        if key == "voice" and key in obj:
            obj[key] = (obj[key] if isinstance(obj[key], list) else [obj[key]]) + [value]
        else:
            obj[key] = value
    return obj


def _number(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def stream_seconds(path: Path, kind: str, picture: bool = False) -> float | None:
    """Length of the first video ("v") or audio ("a") stream of a media file: the stream's own duration (an mp4's file
    length runs a few ms past its video, to the last audio packet), else the file's, else 0. None when ffprobe cannot
    read the file or it has no such stream; a picture is decoded too (its reader goes by the file name alone).
    check_demo.py uses it too."""
    done = subprocess.run(["ffprobe", "-v", "error", "-select_streams", f"{kind}:0", *(["-count_frames"] if picture else []),
                           "-show_entries", "stream=duration,nb_read_frames:format=duration", "-of", "json", str(path)],
                          capture_output=True, text=True)
    try:
        info = json.loads(done.stdout) if done.returncode == 0 else {}
    except ValueError:
        info = {}
    if not info.get("streams"):
        return None
    if picture and (_number(info["streams"][0].get("nb_read_frames")) or 0) < 1:
        return None
    for value in (info["streams"][0].get("duration"), info.get("format", {}).get("duration")):
        if (seconds := _number(value)) is not None and seconds > 0:
            return seconds
    return 0.0


def _narrated_segments(cfg: dict) -> tuple[list[dict], tuple[int, int]]:
    """Every segment of a narrated reel, checked and measured (clip windows, voice lengths) before anything is encoded,
    and the reel's frame size (the clips' size; W x H when there are only pictures, which are scaled to fit it)."""
    fade = float(cfg.get("fade", 0.4))
    problems, segs = [], []
    for n, seg in enumerate(cfg["segments"], 1):
        if ("file" in seg) == ("image" in seg):
            problems.append(f'segment {n}: has both "file" and "image" (give one, not both)' if "file" in seg
                            else f'segment {n}: has neither "file" nor "image"')
            continue
        is_image = "image" in seg
        src = Path(str(seg["image"] if is_image else seg["file"]))
        label = f"segment {n} ({src.name})"
        if not src.is_file():
            problems.append(f"{label}: file not found: {src}")
            continue
        length = stream_seconds(src, "v", picture=is_image)
        if length is None:
            problems.append(f"{label}: cannot read {src} as {'a picture' if is_image else 'a video'}")
            continue
        if is_image:
            start, seconds = 0.0, _number(seg.get("seconds"))
            if seconds is None or seconds <= 0:
                problems.append(f'{label}: an "image" needs "seconds" (a number above 0)')
                continue
        else:
            # the window must lie inside the clip: planned on a longer window than the one encoded, voices could overlap
            start, end = _number(seg.get("start", 0)), (length if seg.get("end") is None else _number(seg["end"]))
            if start is None or end is None:
                problems.append(f'{label}: "start" and "end" must be numbers of seconds')
                continue
            if not 0 <= start < length:
                where = "before" if start < 0 else "beyond"
                problems.append(f'{label}: "start" {start:g} s lies {where} the clip (0 to {length:.3f} s)')
                continue
            if end <= start:
                problems.append(f'{label}: "end" {end:g} s is not after "start" {start:g} s')
                continue
            if end > length + 1 / FPS:  # one frame of slack: an end written as the clip's rounded length
                problems.append(f'{label}: "end" {end:g} s lies beyond the clip (its video is {length:.3f} s long)')
                continue
            seconds = min(end, length) - start
            if seconds < 1 / FPS:  # a window that holds no frame encodes to nothing, and ffmpeg then fails
                problems.append(f'{label}: the window {start:g} to {min(end, length):g} s is shorter than one frame '
                                f'(1/{FPS} s)')
                continue
        item = {"name": src.stem, "src": src, "image": is_image, "start": start, "seconds": seconds,
                "fade_in": float(seg.get("fade_in", fade)), "fade_out": float(seg.get("fade_out", fade)),
                "group": seg.get("group")}
        if seg.get("voice") is not None:
            if not isinstance(seg["voice"], str):
                problems.append(f'{label}: one voice per segment ("voice" holds {len(seg["voice"])} values)'
                                if isinstance(seg["voice"], list) else f'{label}: "voice" is not a file name')
                continue
            voice = Path(seg["voice"])
            if not voice.is_file():
                problems.append(f"{label}: voice file not found: {voice}")
                continue
            voice_seconds = stream_seconds(voice, "a")
            if voice_seconds is None:
                problems.append(f"{label}: cannot read the voice file {voice} as audio")
                continue
            at = _number(seg.get("voice_at", 0))
            if at is None or not 0 <= at <= seconds:
                problems.append(f'{label}: "voice_at" {seg.get("voice_at", 0)!r} lies outside the segment (0 to {seconds:.2f} s)')
                continue
            item.update(voice=voice, voice_at=at, voice_seconds=voice_seconds)
        segs.append(item)
    if problems:
        raise SystemExit("reel: refused before encoding:\n  " + "\n  ".join(problems))
    sizes = {str(s["src"]): probe_size(s["src"]) for s in segs if not s["image"]}
    if len(set(sizes.values())) > 1:
        raise SystemExit("reel segments differ in resolution: " + ", ".join(f"{f} {s}" for f, s in sizes.items()))
    size = next(iter(sizes.values()), f"{W}x{H}")
    return segs, tuple(int(v) for v in size.split("x"))


def _encode_narrated_part(seg: dict, hold: float, size: tuple[int, int], part: Path) -> None:
    """One part of a narrated reel, video only: a clip window with its last frame held, or a picture drawn for its
    whole length; then the segment's fades (the hold comes before the fade-out)."""
    w, h = size
    total = seg["seconds"] + hold
    fi, fo = seg["fade_in"], seg["fade_out"]
    fades = [f"fade=t=in:st=0:d={fi}"] * (fi > 0) + [f"fade=t=out:st={max(0, total - fo):.3f}:d={fo}"] * (fo > 0)
    if seg["image"]:
        # drawn, never frozen: a card clip fades to black at its own end, so holding its last frame shows black
        src = ["-loop", "1", "-framerate", str(FPS), "-i", str(seg["src"])]
        vf = [f"scale={w}:{h}:force_original_aspect_ratio=decrease", f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2",
              "setsar=1", f"fps={FPS}", "format=yuv420p"]
        length = ["-frames:v", str(math.ceil(total * FPS - 1e-6))]
    else:
        src = ["-ss", f"{seg['start']:.3f}", "-to", f"{seg['start'] + seg['seconds']:.3f}", "-i", str(seg["src"])]
        vf = ["setsar=1", f"fps={FPS}", "format=yuv420p"]
        if hold > 0:
            vf.append(f"tpad=stop_mode=clone:stop={math.ceil(hold * FPS - 1e-6)}")
        length = []
    run(["ffmpeg", "-y", "-v", "error", *src, "-vf", ",".join(vf + fades), "-an", *length,
         "-c:v", "libx264", "-preset", "slow", "-crf", "19", str(part)])


def _mix_voices(voices: list[dict], track: Path) -> None:
    """Every voice at its start on the reel's timeline, in one 48 kHz stereo track; levels as recorded (no normalize)."""
    cmd, chains = ["ffmpeg", "-y", "-v", "error"], []
    for k, v in enumerate(voices):
        cmd += ["-i", v["file"]]
        delay = round(v["start"] * VOICE_RATE)  # in samples
        chains.append(f"[{k}:a]aresample={VOICE_RATE},aformat=sample_fmts=fltp:channel_layouts=stereo,"
                      f"adelay={delay}S|{delay}S[v{k}]")
    mix = "".join(f"[v{k}]" for k in range(len(voices))) + f"amix=inputs={len(voices)}:normalize=0[m]"
    run(cmd + ["-filter_complex", ";".join(chains + [mix]), "-map", "[m]", "-c:a", "pcm_f32le", str(track)])


def _loudness_filter(track: Path, target: float) -> tuple[str, str | None]:
    """The filter that brings `track` towards `target` LUFS integrated with its true peak at most VOICE_TRUE_PEAK, and a
    note for the plan's warnings. Measured with loudnorm's first pass, then:
      1. one gain reaches the target under the ceiling: loudnorm's second pass in linear mode (one gain), no note;
      2. it does not, but the largest gain the ceiling allows (or a plain gain where the loudness range is too wide for
         loudnorm's linear mode) lands within VOICE_LOUDNESS_TOLERANCE of the target: that one gain ("volume"), and a
         note that says the level reached when it is under the target;
      3. else loudnorm compresses (its dynamic mode), which changes the voices' levels against each other: a note."""
    base = f"loudnorm=I={target:g}:TP={VOICE_TRUE_PEAK:g}:LRA={LOUDNORM_LRA}"
    cmd = ["ffmpeg", "-hide_banner", "-nostats", "-i", str(track), "-af", base + ":print_format=json", "-f", "null", "-"]
    print("+", " ".join(shlex.quote(c) for c in cmd), file=sys.stderr)
    done = subprocess.run(cmd, capture_output=True, text=True)
    try:
        if done.returncode != 0:
            raise ValueError(done.returncode)
        m = json.loads(done.stderr[done.stderr.rindex("{"):done.stderr.rindex("}") + 1])
        level, peak, lra, thresh, offset = (float(m[k]) for k in ("input_i", "input_tp", "input_lra", "input_thresh",
                                                                  "target_offset"))
    except (ValueError, KeyError, TypeError):
        last = (done.stderr.strip().splitlines() or ["no output"])[-1]
        raise SystemExit(f"reel: measuring the loudness of the voice track failed (ffmpeg loudnorm): {last}")
    if not level > -70:
        return "anull", "the voices are silent: the voice track is left as it is"
    second_pass = (base + f":measured_I={level}:measured_TP={peak}:measured_LRA={lra}:measured_thresh={thresh}"
                   f":offset={offset}:linear=true")
    need, room = target - level, VOICE_TRUE_PEAK - peak   # the gain the target asks for, the most the ceiling allows
    if need <= room and lra <= LOUDNORM_LRA:
        return second_pass, None
    gain = min(need, room)
    if level + gain >= target - VOICE_LOUDNESS_TOLERANCE:
        note = None if gain == need else (
            f"the voice track is brought to {level + gain:.1f} LUFS, not {target:g} LUFS: one gain of {gain:+.1f} dB is the "
            f"most its true peak ({peak:.1f} dBTP at {level:.1f} LUFS) allows under {VOICE_TRUE_PEAK:g} dBTP, so the voices "
            f"keep their levels against each other")
        return f"volume={gain:.2f}dB", note
    return second_pass, (
        f"the voice track cannot reach {target:g} LUFS by one gain (true peak {peak:.1f} dBTP at {level:.1f} LUFS, loudness "
        f"range {lra:.1f} LU; the most one gain allows is {level + gain:.1f} LUFS, more than {VOICE_LOUDNESS_TOLERANCE:g} LU "
        f"short): loudnorm compresses instead, so the voices' levels against each other change")


def _voices_off_plan(voices: list[dict], lengths: list[float], gap: float, tail: float) -> str | None:
    """On the encoded parts: two consecutive voices closer than `gap` (or overlapping), or a last voice that ends after
    the reel or less than `tail` before its end. Unreachable while schedule() gets the true window lengths
    (_narrated_segments refuses a window outside its clip); this guards the reel against a plan made on lengths the
    encoded parts do not have. A part is whole frames and can come out up to one frame shorter than its window, so
    one frame per part from the first voice to the second (or to the reel's end) is allowed, never below zero: an
    overlap, or a voice past the end, always stops the reel. Distances are compared to the microsecond (float sums)."""
    for v0, v1 in zip(voices, voices[1:]):
        apart = v1["start"] - v0["end"]
        if round(apart, 6) < max(0.0, gap - (v1["segment"] - v0["segment"]) / FPS):
            return (f"the voices of segment {v0['segment'] + 1} ({v0['name']}) and segment {v1['segment'] + 1} "
                    f"({v1['name']}) are {apart:.3f} s apart, less than the gap of {gap:g} s")
    if voices:
        v, reel_end = voices[-1], sum(lengths)
        left = reel_end - v["end"]
        if round(left, 6) < max(0.0, tail - (len(lengths) - v["segment"]) / FPS):
            where = (f"after the reel's end at {reel_end:.3f} s" if left < 0 else
                     f"{left:.3f} s before the reel's end, less than the tail of {tail:g} s")
            return f"the voice of segment {v['segment'] + 1} ({v['name']}) ends at {v['end']:.3f} s, {where}"
    return None


def build_narrated_reel(spec: Path, out: Path) -> None:
    """A reel whose segments may carry a voice and may be pictures; writes <out> and <out stem>.voice.json.

    spec: {"segments": [{"file": "clip.mp4", "start": 0, "end": 9, "voice": "line.mp3", "voice_at": 0.3, "group": "take"},
                        {"image": "card.png", "seconds": 3, "voice": "card.mp3"}, ...],
           "fade": 0.4, "voice_gap": 0.6, "voice_tail": 1.0, "loudness": -16}
    Holds come from schedule() on the probed lengths. Each part is encoded and measured; a voice is placed at the measured
    start of its part plus voice_at, so the sound cannot drift from the picture over a long reel. The plan gives each
    segment its measured start, length and hold, and a clip segment its "window" (the seconds of the clip it shows).
    """
    cfg = json.loads(spec.read_text(), object_pairs_hook=_manifest_object)
    segs, size = _narrated_segments(cfg)
    gap, tail = float(cfg.get("voice_gap", VOICE_GAP)), float(cfg.get("voice_tail", VOICE_TAIL))
    target = float(cfg.get("loudness", VOICE_LOUDNESS))
    plan = schedule(segs, gap=gap, tail=tail)
    with tempfile.TemporaryDirectory(prefix="reel-") as tmp_name:  # parts, join and voice track; removed at the end
        tmp = Path(tmp_name)
        parts, lengths = [], []
        for i, (seg, p) in enumerate(zip(segs, plan)):
            part = tmp / f"part{i:02d}.mp4"
            _encode_narrated_part(seg, p["hold"], size, part)
            parts.append(part)
            lengths.append(probe_duration(part))
        starts = [sum(lengths[:i]) for i in range(len(lengths))]
        voices = [{"segment": i, "name": s["name"], "file": str(s["voice"].resolve()), "start": starts[i] + s["voice_at"],
                   "end": starts[i] + s["voice_at"] + s["voice_seconds"]} for i, s in enumerate(segs) if "voice" in s]
        if problem := _voices_off_plan(voices, lengths, gap, tail):
            raise SystemExit(f"reel: stopped before writing the reel: {problem}")
        lst = tmp / "list.txt"
        lst.write_text("".join(f"file '{p}'\n" for p in parts))
        joined = tmp / "joined.mp4"
        run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(joined)])
        seconds = probe_duration(joined)
        note = None
        if voices:
            track = tmp / "voices.wav"
            _mix_voices(voices, track)
            gain, note = _loudness_filter(track, target)
            audio = ["-i", str(track)]
            sound = f"{gain},aresample={VOICE_RATE},aformat=sample_fmts=fltp:channel_layouts=stereo,"
        else:
            audio = ["-f", "lavfi", "-i", f"anullsrc=channel_layout=stereo:sample_rate={VOICE_RATE}"]
            sound = ""
        out.parent.mkdir(parents=True, exist_ok=True)
        run(["ffmpeg", "-y", "-v", "error", "-i", str(joined), *audio,
             "-filter_complex", f"[1:a]{sound}apad=whole_dur={seconds:.4f},atrim=end={seconds:.4f}[a]",
             "-map", "0:v", "-map", "[a]", *REEL_ENCODE, "-movflags", "+faststart", str(out)])
    holds = [p["hold"] for p in plan]
    warnings = [f"segment {n} ({s['name']}): a hold of {h:.1f} s, over {WARN_HOLD:g} s"
                for n, (s, h) in enumerate(zip(segs, holds), 1) if h > WARN_HOLD]
    if sum(holds) > WARN_HOLD_SHARE * seconds:
        warnings.append(f"holds are {100 * sum(holds) / seconds:.0f} % of the reel ({sum(holds):.1f} of {seconds:.1f} s), "
                        f"over {100 * WARN_HOLD_SHARE:.0f} %")
    warnings += [f"segment {v['segment'] + 1} ({v['name']}): a voice of {v['end'] - v['start']:.1f} s, over {WARN_VOICE:g} s"
                 for v in voices if v["end"] - v["start"] > WARN_VOICE]
    warnings += [note] if note else []
    r4 = lambda t: round(t, 4)  # noqa: E731
    plan_path = out.with_suffix(".voice.json")
    write_json_atomic(plan_path, {
        # a clip segment's window (seconds of its clip) turns a time in the clip into reel time: start + (t - window[0])
        "segments": [{"name": s["name"], "start": r4(starts[i]), "seconds": r4(lengths[i]), "hold": r4(holds[i]),
                      **({} if s["image"] else {"window": [r4(s["start"]), r4(s["start"] + s["seconds"])]})}
                     for i, s in enumerate(segs)],
        "voices": [{**v, "start": r4(v["start"]), "end": r4(v["end"])} for v in voices],
        "warnings": warnings})
    for w in warnings:
        print(f"reel: warning: {w}", file=sys.stderr)
    print(json.dumps({"out": str(out), "seconds": round(probe_duration(out), 1), "parts": len(parts), "voices": len(voices),
                      "held": round(sum(holds), 1), "plan": str(plan_path), "warnings": len(warnings)}, ensure_ascii=False))

# ---------------------------------------------------------------- voice (Amazon Polly through the AWS CLI)

CLI_LOADS = ("file://", "fileb://", "http://", "https://")  # the AWS CLI reads a parameter value with these prefixes
MAX_LINE_CHARS = 1000  # one call per line; the service limits a call's text and this tool does not split lines


def spoken(text: str, readings: dict[str, str]) -> str:
    """Apply the readings table: plain substrings, longest key first, each position replaced at most once."""
    if not readings:
        return text
    keys = sorted((k for k in readings if k), key=len, reverse=True)
    pattern = re.compile("|".join(re.escape(k) for k in keys))
    return pattern.sub(lambda m: readings[m.group(0)], text)


def unreadable(text: str) -> list[str]:
    """Runs of Latin letters or digits left in a text, in order (a synthesizer reads them in its own way)."""
    return re.findall(r"[A-Za-z]+|[0-9]+", text)


def write_json_atomic(path: Path, data: dict) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def _voice_key(text: str, voice: str, engine: str, language: str) -> str:
    return hashlib.sha256("\0".join([text, voice, engine, language]).encode("utf-8")).hexdigest()


def synthesize(lines: dict, out: Path, *, voice: str, engine: str, language: str, region: str | None,
               readings: dict[str, str], hangul_only: bool) -> dict:
    """One mp3 per narration line in `out`, plus voice.json (rewritten after every synthesized line).

    A line is a text or {"audio": file} (a recorded file, copied as it is). Every check runs before the first call;
    a line whose spoken text, voice, engine and language are unchanged (and whose file exists) is not synthesized again.
    """
    problems, texts = [], {}
    for name, line in lines.items():
        if not name or "/" in name or "\\" in name or name.startswith("."):
            problems.append(f"{name!r}: name is not a plain file name (no path separator, not empty, no leading dot)")
            continue
        if isinstance(line, dict):
            if not Path(str(line.get("audio", ""))).is_file():
                problems.append(f"{name}: audio file not found: {line.get('audio')}")
            continue
        if not isinstance(line, str):
            problems.append(f"{name}: neither a text nor an {{\"audio\": file}} object")
            continue
        texts[name] = spoken(line, readings)
        if not texts[name].strip():
            problems.append(f"{name}: blank line")
        elif texts[name].lstrip().lower().startswith(CLI_LOADS):
            problems.append(f"{name}: text begins with a prefix the AWS CLI would load instead of speak ({', '.join(CLI_LOADS)})")
        elif len(texts[name]) > MAX_LINE_CHARS:
            problems.append(f"{name}: line too long ({len(texts[name])} characters, at most {MAX_LINE_CHARS})")
        elif hangul_only and unreadable(texts[name]):
            problems.append(f"{name}: not Hangul only, left: {', '.join(unreadable(texts[name]))}")
    if problems:
        raise SystemExit("voice: refused before any call:\n  " + "\n  ".join(problems))

    out.mkdir(parents=True, exist_ok=True)
    index = out / "voice.json"
    try:
        old = json.loads(index.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        old = {}
    entries = {n: old[n] for n in lines if isinstance(old.get(n), dict)
               and (n not in texts or old[n].get("key") == _voice_key(texts[n], voice, engine, language))}
    for name, line in lines.items():
        if isinstance(line, dict):
            src = Path(line["audio"])
            target = out / (name + src.suffix)
            if src.resolve() != target.resolve():
                shutil.copyfile(src, target)
            entries[name] = {"file": target.name, "seconds": round(probe_duration(target), 2), "spoken": "",
                             "key": hashlib.sha256(target.read_bytes()).hexdigest()}
            continue
        text = texts[name]
        key = _voice_key(text, voice, engine, language)
        have = entries.get(name)
        target = out / f"{name}.mp3"
        if have and have.get("key") == key and (out / have.get("file", "")).is_file():
            print(f"voice: {name}: unchanged", file=sys.stderr)
            continue
        cmd = ["aws", "polly", "synthesize-speech"] + (["--region", region] if region else []) + [
            "--engine", engine, "--language-code", language, "--voice-id", voice,
            "--output-format", "mp3", f"--text={text}", str(target)]
        print(f"voice: {name}: synthesizing {len(text)} characters", file=sys.stderr)
        try:
            done = subprocess.run(cmd, capture_output=True, text=True)
        except FileNotFoundError:
            raise SystemExit("voice: the AWS CLI (aws) is not installed or not on PATH")
        if done.returncode != 0:
            target.unlink(missing_ok=True)
            entries.pop(name, None)
            write_json_atomic(index, entries)
            raise SystemExit(f"voice: {name}: aws polly synthesize-speech failed ({done.returncode}): "
                             f"{(done.stderr or done.stdout).strip()}")
        if not target.is_file():
            raise SystemExit(f"voice: {name}: aws polly synthesize-speech exited 0 but wrote no audio file")
        entries[name] = {"file": target.name, "seconds": round(probe_duration(target), 2), "spoken": text, "key": key}
        write_json_atomic(index, entries)
    result = {n: entries[n] for n in lines}
    write_json_atomic(index, result)
    return result


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("clip")
    c.add_argument("raw", type=Path)
    c.add_argument("--out", type=Path)
    c.add_argument("--title")
    c.add_argument("--subtitle")
    c.add_argument("--tag", help="small persistent top-right label, e.g. the site URL")
    c.add_argument("--start", type=float)
    c.add_argument("--end", type=float)
    c.add_argument("--no-captions", action="store_true")
    c.add_argument("--script", type=Path, help="story script JSON: title/subtitle/tag + beats anchored to camlog events")
    r = sub.add_parser("reel")
    r.add_argument("spec", type=Path)
    r.add_argument("--out", type=Path, required=True)
    r.add_argument("--copy", action="store_true", help="1.2.0 behaviour: stream-copy concat (QuickTime may stall mid-video)")
    v = sub.add_parser("voice", help="narration lines -> one mp3 each with Amazon Polly (AWS CLI), plus voice.json")
    v.add_argument("lines", type=Path, help='JSON: {"<name>": "<text>" | {"audio": "<file>"}}')
    v.add_argument("--out", type=Path, required=True)
    v.add_argument("--voice", default="Seoyeon")
    v.add_argument("--engine", default="generative")
    v.add_argument("--language", default="ko-KR")
    v.add_argument("--region")
    v.add_argument("--readings", type=Path, help='JSON: {"<written>": "<spoken>"}, applied longest key first')
    v.add_argument("--hangul-only", action="store_true", help="refuse a line that still holds Latin letters or digits")
    a = ap.parse_args()
    if a.cmd == "voice":
        def load_object(path: Path) -> dict:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as e:
                raise SystemExit(f"voice: cannot read {path} as JSON: {e}")
            if not isinstance(data, dict):
                raise SystemExit(f"voice: {path} must hold one JSON object")
            return data
        readings = load_object(a.readings) if a.readings else {}
        result = synthesize(load_object(a.lines), a.out, voice=a.voice, engine=a.engine,
                            language=a.language, region=a.region, readings=readings, hangul_only=a.hangul_only)
        print(json.dumps(result, ensure_ascii=False))
        return
    if a.cmd == "clip":
        out = a.out or Path("clips") / (a.raw.stem + ".mp4")
        build_clip(a.raw, out, a.title, a.subtitle, a.start, a.end, not a.no_captions, a.tag, a.script)
    else:
        build_reel(a.spec, a.out, copy=a.copy)


if __name__ == "__main__":
    main()
