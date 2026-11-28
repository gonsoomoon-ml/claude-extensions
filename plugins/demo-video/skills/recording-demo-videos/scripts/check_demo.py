#!/usr/bin/env python3
"""Check a narrated reel after it is built, and make one page to look at and listen to every narration.

  python3 check_demo.py audit reel.mp4 [--plan reel.voice.json] [--tolerance 0.25] [--loudness -16] --out audit.json
  python3 check_demo.py boxes scripts/take.1.json --raw raw/take.webm --out boxes/take.1.json
  python3 check_demo.py sheet reel.mp4 --plan reel.voice.json --texts texts.json [--boxes boxes/*.json] --out review/
  python3 check_demo.py brief raw/take.webm --out brief/take/ [--script scripts/take.1.json ...] [--speed 1.25]
                        [--voices voice/voice.json] [--rate 7.6] [--every 5]

audit  The reel's own sound against its plan (<reel stem>.voice.json, written by `edit_demo.py reel`). Speech is found
       with ffmpeg's silencedetect (-35 dB; 0.35 s of silence parts two voices), in the reel and in each voice file:
       a voice's sound is expected from its planned start + its file's first sound to its planned start + its file's
       last sound (a file runs on past its sound; its sound is found relative to its own peak; the plan's times are used,
       with a warning, when the file is gone, is not a file here (a URL is never opened) or no longer as long as the
       plan says).
       Problems, one line each: a voice heard more than --tolerance s early or late at either end, a planned voice with
       no sound, sound where no voice is planned, two voices planned to sound closer than 0.35 s (they cannot be told
       apart), video and audio lengths more than 0.1 s apart, an integrated loudness (ffmpeg's ebur128 meter) more than
       1.5 LU from --loudness or none measured, a plan whose voices lack "name", "start" or "end". The report is written
       either way; exit 1 when it holds a problem.
boxes  Each highlight box of a clip script, measured on the raw take, never on the clip (which holds the box and the
       caption): the take's frames at the box's first and last moment, scaled to 1920x1080 as the clip step scales them.
       std: the largest luminance standard deviation (0-255) along the four strips where the border is drawn; redness:
       how close those strips' mean colour is to the border colour (0-1, by CIELAB distance); each the larger of the
       two frames. change: the mean absolute difference (0-255) inside the box between the two frames. Flags: crosses
       (std > 28: the border runs over text or a picture), low_contrast (redness > 0.6), moved (change > 12: the
       screen under the box changed). A flag says "look at this row", not a failure: exit 0 whatever the flags.
sheet  One row per voice of the plan: the finished reel's frames at the voice's start + 0.5 s, its middle and its
       end - 0.2 s; each box (from --boxes reports, matched to a voice by the clip's name) whose time the voice's segment
       shows, with the reel's frame at the middle of that time, an enlarged crop of the box from it and the time (a box
       in no voiced segment's window is named on stderr; a plan without the segments' windows, written before reels
       recorded them, gives each row every box of its clip, cropped from the voice's middle frame, with a line on stderr);
       the caption, the narration, what each box points at, the flags and the times. texts.json: {"<name of a voice in
       the plan>": {"caption": "...", "say": "...", "what": ["..."], "sources": ["..."]}}, every field optional (one text
       is one phrase); what[i] goes with the i-th box of the clip's report; a voice's name is the stem of its segment's
       clip or picture file (copy it from the plan); a texts key or a boxes report that matches no voice and a voice
       with no entry are named on stderr. Writes
       <out>/index.json, one JPEG per row and <out>/review.html: one file with every picture and each voice's sound
       inside it, to send as it is. Its top lists every row and the flagged rows as links to the rows (in-page links
       only); a flagged row's card has a red edge.
brief  What a take shows, for writing its captions and its narration from what was recorded: <out>/brief.json and
       stills (JPEG, the take's frames at 1920x1080). One row per view (a camlog shot to the next one), or with --script
       one row per caption, or for a recording without a camlog one row every --every seconds. A row holds its seconds
       of the take ("raw") and of the finished clip ("seconds"), "budget" (the characters of narration that fit:
       (seconds - 0.3 - the reel's voice gap) x the speech rate; the rate is measured in --voices' voice.json, else
       --rate, else 7.6), "live" (the picture still changes in the row's last second: true, false, or null when a camera
       move or the row's length keeps it from being measured), the frame's text from <take>.frametext.txt (written by
       record_demo.mjs: "text" as the row starts, "text_end" as the camera leaves, "texts" kept by rec.text, each
       mark's text) and the camlog's marks and notes inside it. Reads only; a take without frame text gives rows without
       text, with one line on stderr. A budget is information: nothing stops on it.
Exit codes: 0 done (audit: passed), 1 a problem or input that cannot be read (a box the clip step would refuse stops
`boxes` with that step's message), 2 a usage error.
"""
from __future__ import annotations

import argparse
import base64
import html
import io
import json
import math
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageColor, ImageDraw, ImageFont, ImageStat

if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
import edit_demo  # noqa: E402  the clip step's own rules (box times and delays, the border's look): one rule in one place
from edit_demo import FPS, H, HIGHLIGHT, HIGHLIGHT_THICK, W  # noqa: E402

SPEECH_NOISE_DB = -35.0      # silencedetect: quieter than this is silence
SPEECH_MIN_SILENCE = 0.35    # s; a shorter pause stays inside one voice
MIN_SOUND = 0.05             # s; a shorter burst is left out (rounding at the file's edges, a click)
EDGE_PAD = 1.0               # s (at least) of silence put before and after the decoded sound, so its two ends are found too
OWN_SOUND_RANGE_DB = 33.0    # a voice file's sound is what lies within this many dB of its own peak (the reel's -35 dB
                             # is about this far below the peak of the voice track once the reel has lifted it)
FILE_LENGTH_TOLERANCE = 0.05  # s a voice file may differ from the length the plan records before it counts as changed
VOICE_TOLERANCE = 0.25       # s a voice may start or end away from its plan
LENGTH_TOLERANCE = 0.1       # s between the video's and the audio's length
LOUDNESS_TOLERANCE = edit_demo.VOICE_LOUDNESS_TOLERANCE   # 1.5 LU around the target (edit_demo.VOICE_LOUDNESS, -16 LUFS);
                             # the reel's own step takes one gain that lands within it rather than compress
LOUDNESS_FILTER = "ebur128=peak=true:framelog=verbose"   # EBU R128 meter with true peak; frame lines kept out of the log
CROSSES_STD = 28             # flag "crosses"
LOW_CONTRAST_REDNESS = 0.6   # flag "low_contrast"
MOVED_CHANGE = 12            # flag "moved"
REDNESS_SCALE = 100.0        # CIELAB distance at which redness reaches 0 (black to white is 100)
SHEET_WIDTH = 640            # px of one frame on the page and in a row's JPEG; a crop is at most this wide
CROP_MARGIN = 24             # frame px of screen kept around a box in its crop
CROP_ZOOM = 4                # a crop is enlarged at most this much
JPEG_QUALITY = 70
VOICE_SOUND = ["-ac", "1", "-ar", "24000", "-b:a", "48k"]   # a voice on the page: mono, the speech service's own rate


def _last_line(text: str) -> str:
    return (text.strip().splitlines() or ["no output"])[-1]


def _read_json(path: Path, what: str):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise SystemExit(f"cannot read {what} {path} as JSON: {e}")


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    edit_demo.write_json_atomic(path, data)


# ---------------------------------------------------------------- the frame text a take keeps beside its camlog

FRAMETEXT_KINDS = ("shot", "leave", "mark", "text")
_FRAMETEXT_HEADER = re.compile(r"== (\d+\.\d{2}) (%s) (\S+)" % "|".join(FRAMETEXT_KINDS))


def frametext_key(key) -> str:
    """A camlog key as frametext.mjs writes it into a header: one token, whitespace runs as _, _ for none."""
    return re.sub(r"\s+", "_", str(key if key is not None else "").strip()) or "_"


def read_frametext(path: Path) -> list[dict]:
    """The entries of a take's frame-text file (<name>.frametext.txt, written by record_demo.mjs with frametext.mjs),
    in file order: [{"t": seconds of the take, "kind": shot | leave | mark | text, "key", "text"}]. No file: no entries.
    A line of the screen that looked like a header was written with one more leading space; that space is taken off."""
    if not path.is_file():
        return []
    entries: list[dict] = []
    lines: list[str] = []
    body = path.read_text(encoding="utf-8")
    for line in body.split("\n")[:-1] if body.endswith("\n") else body.split("\n"):
        header = _FRAMETEXT_HEADER.fullmatch(line)
        if header:
            lines = []
            entries.append({"t": float(header.group(1)), "kind": header.group(2), "key": header.group(3), "text": lines})
        elif entries:   # a line before the first header belongs to no capture
            lines.append(line[1:] if re.match(r" +== ", line) else line)
    return [{**e, "text": "\n".join(e["text"])} for e in entries]


# ---------------------------------------------------------------- audit: speech, lengths, loudness

def speech_intervals(path: Path, noise_db: float = SPEECH_NOISE_DB,
                     min_silence: float = SPEECH_MIN_SILENCE) -> list[tuple[float, float]]:
    """Where a file's sound is louder than `noise_db`, as (start, end) seconds: what lies between silences of at least
    `min_silence` s (ffmpeg silencedetect on the first audio stream). Silence (EDGE_PAD s, or longer than `min_silence`)
    is put before and after the decoded sound, so a silence at either end of the file counts however short (a first voice 0.3 s into a reel starts
    at 0.3), and the sound ends where it stops, not at the file's stated length (an mp3 states more than it decodes).
    Bursts under MIN_SOUND s are left out."""
    if edit_demo.stream_seconds(path, "a") is None:
        raise SystemExit(f"cannot read an audio stream in {path}")
    edge = max(EDGE_PAD, min_silence + 0.1)   # long enough for the last sound to be followed by a silence that is seen
    pad = f"adelay=delays={edge * 1000:g}:all=1,apad=pad_dur={edge:g}"
    done = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-map", "0:a:0",
                           "-af", f"{pad},silencedetect=n={noise_db:g}dB:d={min_silence:g}", "-f", "null", "-"],
                          capture_output=True, text=True)
    if done.returncode != 0:
        raise SystemExit(f"cannot read the sound of {path}: {_last_line(done.stderr)}")
    silences, opened = [], None
    for kind, value in re.findall(r"silence_(start|end): (-?[\d.]+)", done.stderr):
        if kind == "start":
            opened = float(value) - edge
        else:
            silences.append((-edge if opened is None else opened, float(value) - edge))
            opened = None
    if opened is not None:   # ffmpeg 4.4 closes the last silence at the end of what it reads; an open one runs on
        silences.append((opened, math.inf))
    sound, at = [], 0.0
    for a, b in silences:
        if a - at >= MIN_SOUND:
            sound.append((round(at, 3), round(a, 3)))
        at = max(at, b)
    return sound


def _label(k: int, voice: dict) -> str:
    return voice.get("label") or f"voice {k} ({voice['name']})"


def _heard(planned: list[dict], detected: list[tuple[float, float]], tolerance: float):
    """Each planned voice's heard span (the detected intervals that overlap it most, joined: a pause inside a voice
    splits its sound) and the intervals that overlap no voice (each voice widened by `tolerance`)."""
    spans: list[tuple[float, float] | None] = [None] * len(planned)
    extra = []
    for a, b in detected:
        overlaps = [min(b, v["end"] + tolerance) - max(a, v["start"] - tolerance) for v in planned]
        k = max(range(len(planned)), key=overlaps.__getitem__, default=None)
        if k is None or overlaps[k] <= 0:
            extra.append((a, b))
            continue
        s = spans[k]
        spans[k] = (a, b) if s is None else (min(s[0], a), max(s[1], b))
    return spans, extra


def voice_problems(planned: list[dict], detected: list[tuple[float, float]], tolerance: float = VOICE_TOLERANCE) -> list[str]:
    """One line per voice heard more than `tolerance` s early or late at the start or the end of its sound, per voice
    with no sound, and per sound where no voice is planned. `planned`: the voices in order, each with "name" and the
    "start" and "end" of its sound in the reel. `audit` gives each voice's planned start plus its own file's first and
    last sound, with "placed" (the planned start) and "own" (the file's sound) for the line; plain plan times work too."""
    spans, extra = _heard(planned, detected, tolerance)
    problems = []
    for k, (v, s) in enumerate(zip(planned, spans), 1):
        expected = f"sound expected at {v['start']:.2f}-{v['end']:.2f} s"
        if "own" in v:
            expected += f" (its file placed at {v['placed']:.2f} s sounds {v['own'][0]:.2f}-{v['own'][1]:.2f} s into it)"
        if s is None:
            problems.append(f"{_label(k, v)}: {expected}, no sound there")
        elif abs(s[0] - v["start"]) > tolerance or abs(s[1] - v["end"]) > tolerance:
            problems.append(f"{_label(k, v)}: {expected}, heard {s[0]:.2f}-{s[1]:.2f} s (start {s[0] - v['start']:+.2f} s, "
                            f"end {s[1] - v['end']:+.2f} s; more than {tolerance:g} s off)")
    return problems + [f"sound at {a:.2f}-{b:.2f} s where no voice is planned" for a, b in extra]


def close_voices(planned: list[dict], min_silence: float = SPEECH_MIN_SILENCE) -> tuple[list[dict], list[str]]:
    """The voices as silence detection can tell them apart. Two voices whose sounds are planned less than
    `min_silence` s apart sound as one interval: they are joined into one span, checked as one, and said in a problem
    line (rather than reported as a shifted end and a shifted start)."""
    groups, problems = [], []
    for k, v in enumerate(planned, 1):
        if groups and v["start"] - planned[k - 2]["end"] < min_silence:
            problems.append(f"{_label(k - 1, planned[k - 2])} and {_label(k, v)} are planned to sound "
                            f"{v['start'] - planned[k - 2]['end']:.2f} s apart, less than the {min_silence:g} s of silence "
                            f"that parts two voices: their sound is checked as one")
            g = groups[-1]
            for key in ("own", "placed"):   # the line of a joined span names no single file
                g.pop(key, None)
            g["voices"].append(k)
            g["end"] = max(g["end"], v["end"])
            g["label"] = (f"voices {', '.join(map(str, g['voices']))} "
                          f"({', '.join(planned[j - 1]['name'] for j in g['voices'])})")
        else:
            groups.append({**v, "voices": [k], "label": _label(k, v)})
    return groups, problems


def _peak_db(path: Path) -> float | None:
    """The highest sample level of a file's first audio stream in dB (ffmpeg volumedetect); None when not measured."""
    done = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-map", "0:a:0", "-af", "volumedetect",
                           "-f", "null", "-"], capture_output=True, text=True)
    m = re.search(r"max_volume: (-?[\d.]+) dB", done.stderr) if done.returncode == 0 else None
    return float(m.group(1)) if m else None


def _own_sound(path: Path) -> tuple[float, float] | None:
    """Where a voice file's own sound begins and ends, seconds into the file; None when the file cannot be read or
    holds no sound. The reel lifts its voice track to the loudness target, so the file's sound is found relative to
    the file's own level: OWN_SOUND_RANGE_DB below its peak, never above the reel's own threshold."""
    peak = _peak_db(path)
    noise = SPEECH_NOISE_DB if peak is None else min(SPEECH_NOISE_DB, peak - OWN_SOUND_RANGE_DB)
    try:
        found = speech_intervals(path, noise_db=noise)
    except SystemExit:
        return None
    return (found[0][0], found[-1][1]) if found else None


def _file_changed(file: str, v: dict) -> float | None:
    """The file's length now when it is not the length the plan records for the voice (`end - start`, as the reel step
    measured the file), else None."""
    now = edit_demo.stream_seconds(Path(file), "a") if file else None
    if now is not None and abs(now - (v["end"] - v["start"])) > FILE_LENGTH_TOLERANCE:
        return now
    return None


def _plan_voice_problem(k: int, v) -> str | None:
    if not isinstance(v, dict):
        return f"voice {k} is not an object"
    missing = [key for key in ("name", "start", "end") if key not in v]
    if missing:
        return f"voice {k} has no " + ", ".join(f'"{key}"' for key in missing)
    if not all(isinstance(v[key], (int, float)) and not isinstance(v[key], bool) for key in ("start", "end")):
        return f'voice {k}: "start" and "end" must be numbers of seconds'
    return None


def loudness(path: Path, start: float | None = None, seconds: float | None = None) -> dict:
    """Integrated loudness (LUFS), true peak (dBTP) and loudness range (LU) of a file's first audio stream (from
    `start` for `seconds` when given), read with ffmpeg's EBU R128 meter (LOUDNESS_FILTER). None: no sound at all."""
    window = ([] if start is None else ["-ss", f"{max(0.0, start):.3f}"]) + ([] if seconds is None else ["-t", f"{seconds:.3f}"])
    done = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", *window, "-i", str(path), "-map", "0:a:0",
                           "-af", LOUDNESS_FILTER, "-f", "null", "-"], capture_output=True, text=True)
    summary = done.stderr[done.stderr.rfind("Summary:"):] if done.returncode == 0 and "Summary:" in done.stderr else ""

    def read(label: str) -> float | None:
        m = re.search(rf"^\s*{label}:\s+(-?inf|-?[\d.]+)", summary, re.M)
        if not m:
            raise SystemExit(f"measuring the loudness of {path} failed (ffmpeg ebur128): {_last_line(done.stderr)}")
        return None if m.group(1).endswith("inf") else float(m.group(1))
    return {"integrated": read("I"), "true_peak": read("Peak"), "range": read("LRA")}


def audit(reel: Path, plan_path: Path, *, tolerance: float = VOICE_TOLERANCE,
          target: float = edit_demo.VOICE_LOUDNESS) -> dict:
    """The audit report of a reel against its plan (see the module docstring); empty "problems" means it passes."""
    report = {"reel": str(reel), "plan": str(plan_path), "ok": False, "problems": [], "warnings": []}
    problems = report["problems"]
    plan = _read_json(plan_path, "the plan")
    voices = plan.get("voices") if isinstance(plan, dict) else None
    if not isinstance(voices, list):
        raise SystemExit(f"the plan {plan_path} has no list of voices")
    if shape := [p for k, v in enumerate(voices, 1) if (p := _plan_voice_problem(k, v))]:
        raise SystemExit(f"the plan {plan_path} does not describe its voices: " + "; ".join(shape))
    video, audio = edit_demo.stream_seconds(reel, "v"), edit_demo.stream_seconds(reel, "a")
    if video is None or audio is None:
        raise SystemExit(f"cannot read {'a video' if video is None else 'an audio'} stream in {reel}")
    report["length"] = {"video": video, "audio": audio, "limit": LENGTH_TOLERANCE}
    if abs(video - audio) > LENGTH_TOLERANCE:
        problems.append(f"the video is {video:.3f} s and the audio {audio:.3f} s long, {abs(video - audio):.3f} s apart "
                        f"(more than {LENGTH_TOLERANCE:g} s)")
    # a voice file runs on past its sound (an mp3's last frame) and a speech line begins after its file does: the
    # reel's sound is held against each file's own first and last sound, so the tolerance holds both ways
    own: dict[str, tuple[float, float] | None] = {}
    expected = []
    for k, v in enumerate(voices, 1):
        file = str(v.get("file") or "")
        usable = file if file and Path(file).is_file() else ""   # never a URL or a device: only a file is read
        if usable not in own:
            own[usable] = _own_sound(Path(usable)) if usable else None
        if (now := _file_changed(usable, v)) is not None:
            report["warnings"].append(f"{_label(k, v)}: its file {file} is {now:.2f} s long, the plan says "
                                      f"{v['end'] - v['start']:.2f} s (changed since the reel was built): held against the "
                                      f"plan's times")
            expected.append({"name": v["name"], "start": v["start"], "end": v["end"]})
        elif (sound := own[usable]) is None:
            report["warnings"].append(f"{_label(k, v)}: found no sound in its file {file or '(none named)'} (missing, not "
                                      f"a file, unreadable or silent): held against the plan's times")
            expected.append({"name": v["name"], "start": v["start"], "end": v["end"]})
        else:
            expected.append({"name": v["name"], "start": round(v["start"] + sound[0], 4), "end": round(v["start"] + sound[1], 4),
                             "placed": v["start"], "own": sound})
    detected = speech_intervals(reel)
    groups, close = close_voices(expected)
    problems += close + voice_problems(groups, detected, tolerance)
    report["speech"] = {"filter": f"silencedetect=n={SPEECH_NOISE_DB:g}dB:d={SPEECH_MIN_SILENCE:g}", "tolerance": tolerance,
                        "intervals": [list(i) for i in detected]}
    spans, _ = _heard(groups, detected, tolerance)
    report["voices"] = []
    for g, s in zip(groups, spans):
        for k in g["voices"]:
            v, e = voices[k - 1], expected[k - 1]
            entry = {"voice": k, "segment": v.get("segment"), "name": v["name"], "file": v.get("file"),
                     "planned": [v["start"], v["end"]], "file_sound": list(e["own"]) if "own" in e else None,
                     "expected": [e["start"], e["end"]], "heard": None if s is None else list(s)}
            if len(g["voices"]) > 1:
                entry["checked_with"] = [j for j in g["voices"] if j != k]
            elif s is not None:
                entry.update(start_off=round(s[0] - e["start"], 3), end_off=round(s[1] - e["end"], 3))
            entry["loudness"] = loudness(reel, v["start"], v["end"] - v["start"])["integrated"]
            report["voices"].append(entry)
    level = loudness(reel)
    report["loudness"] = {"filter": LOUDNESS_FILTER, **level, "target": target, "tolerance": LOUDNESS_TOLERANCE,
                          "true_peak_ceiling": edit_demo.VOICE_TRUE_PEAK}
    levels = [v["loudness"] for v in report["voices"] if v["loudness"] is not None]
    if levels:
        report["loudness"]["voices"] = {"lowest": min(levels), "highest": max(levels), "spread": round(max(levels) - min(levels), 1)}
    if not voices:
        report["warnings"].append("the plan has no voices: the loudness is not checked")
    elif level["integrated"] is None:
        problems.append(f"the integrated loudness could not be measured (ffmpeg ebur128 gave no value); the target is "
                        f"{target:g} LUFS")
    elif abs(level["integrated"] - target) > LOUDNESS_TOLERANCE:
        problems.append(f"the integrated loudness is {level['integrated']:.1f} LUFS, more than {LOUDNESS_TOLERANCE:g} LU "
                        f"from the target of {target:g} LUFS")
    if level["true_peak"] is not None and level["true_peak"] > edit_demo.VOICE_TRUE_PEAK:
        report["warnings"].append(f"the true peak is {level['true_peak']:.1f} dBTP, above {edit_demo.VOICE_TRUE_PEAK:g} dBTP")
    report["ok"] = not problems
    return report


# ---------------------------------------------------------------- boxes: what lies under each border on the raw take

def _colour(value: str) -> tuple[int, int, int]:
    """An ffmpeg colour as HIGHLIGHT holds it (0xRRGGBB or a name, then the opacity after an at sign) as RGB."""
    name = value.split("@")[0]
    try:
        return ImageColor.getrgb("#" + name[2:] if name.lower().startswith("0x") else name)[:3]
    except ValueError:
        raise SystemExit(f"cannot read the highlight colour {value!r} (DEMO_HIGHLIGHT)")


def _lab(rgb) -> tuple[float, float, float]:
    """sRGB (0-255) as CIELAB (D65)."""
    def linear(c: float) -> float:
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (linear(float(c)) for c in rgb)
    xyz = ((0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047, 0.2126 * r + 0.7152 * g + 0.0722 * b,
           (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883)
    fx, fy, fz = (t ** (1 / 3) if t > (6 / 29) ** 3 else t / (3 * (6 / 29) ** 2) + 4 / 29 for t in xyz)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def border_stats(image, rect: tuple[int, int, int, int], thick: int = HIGHLIGHT_THICK) -> dict:
    """What lies under a box's border on a frame without the box: "std", the largest luminance standard deviation
    (0-255) of the four strips where the border is drawn (`thick` px inside the rectangle); "redness", how close the
    strips' mean colour is to the highlight colour, 1 - CIELAB distance / REDNESS_SCALE, 0 (far) to 1 (the same)."""
    x, y, w, h = (int(v) for v in rect)
    t = max(1, min(thick, w // 2, h // 2))
    rgb = image.convert("RGB")
    strips = [rgb.crop(s) for s in ((x, y, x + w, y + t), (x, y + h - t, x + w, y + h),
                                    (x, y, x + t, y + h), (x + w - t, y, x + w, y + h))]
    std = max(ImageStat.Stat(s.convert("L")).stddev[0] for s in strips)
    areas = [s.width * s.height for s in strips]
    mean = [sum(ImageStat.Stat(s).mean[c] * a for s, a in zip(strips, areas)) / sum(areas) for c in range(3)]
    redness = max(0.0, 1 - math.dist(_lab(mean), _lab(_colour(HIGHLIGHT))) / REDNESS_SCALE)
    return {"std": std, "redness": redness}


def region_change(a, b, rect: tuple[int, int, int, int]) -> float:
    """Mean absolute difference (0-255, over the three colour channels) between two frames inside a rectangle."""
    x, y, w, h = (int(v) for v in rect)
    box = (x, y, x + w, y + h)
    return sum(ImageStat.Stat(ImageChops.difference(a.convert("RGB").crop(box), b.convert("RGB").crop(box))).mean) / 3


def _frame(video: Path, t: float, vf: str | None = None) -> Image.Image:
    done = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(0.0, t):.3f}", "-i", str(video), "-frames:v", "1",
                           *(["-vf", vf] if vf else []), "-f", "image2pipe", "-c:v", "ppm", "-"], capture_output=True)
    if done.returncode != 0 or not done.stdout:
        raise SystemExit(f"cannot read a frame of {video} at {t:.2f} s: {_last_line(done.stderr.decode(errors='replace'))}")
    return Image.open(io.BytesIO(done.stdout)).convert("RGB")


def take_frame(raw: Path, t: float) -> Image.Image:
    """The raw take's frame at `t` s, scaled to the clip's frame as the clip step scales it (lanczos, then 4:2:0)."""
    return _frame(raw, t, f"scale={W}:{H}:flags=lanczos,format=yuv420p")


def _clip_script(script: Path) -> tuple[dict, list[dict]]:
    """A clip script and its beats, or one line that says it is not one."""
    story = _read_json(script, "the clip script")
    beats = (story.get("beats") or []) if isinstance(story, dict) else None
    if not isinstance(beats, list) or not all(isinstance(b, dict) and "at" in b for b in beats):
        raise SystemExit(f"{script} is not a clip script (one JSON object whose \"beats\" each have an \"at\")")
    return story, beats


def measure_boxes(script: Path, raw: Path) -> dict:
    """The `boxes` report of one clip script: per box its rectangle (frame px), its time (raw and clip seconds), what
    lies under its border and the flags. Both frames are read from the raw take; the clip is never opened."""
    story, beats = _clip_script(script)
    take_end = edit_demo.stream_seconds(raw, "v")
    if not take_end:
        raise SystemExit(f"cannot read the take {raw} as a video")
    log = edit_demo.read_camlog(raw)
    start, end = edit_demo.clip_span(raw, log, story.get("start"), story.get("end"))
    speed = float(story.get("speed", edit_demo.DEFAULT_SPEED))
    layout = edit_demo.beat_layout(beats, log, start=start, end=end, speed=speed, title=story.get("title"))
    found = []
    for item in layout:
        if not item["box_raw"]:
            continue
        lo, hi = item["box_raw"]
        # the box's first frame, and its last one: a clip frame before it goes (a held box goes with the clip's end)
        frames = take_frame(raw, lo), take_frame(raw, max(lo, min(hi, take_end) - speed / FPS))
        beat = next(n for n, b in enumerate(beats, 1) if b is item["beat"])
        for k, rect in enumerate(item["boxes"], 1):
            stats = [border_stats(f, rect) for f in frames]
            std, redness = max(s["std"] for s in stats), max(s["redness"] for s in stats)
            change = region_change(*frames, rect)
            flags = [name for name, on in (("crosses", std > CROSSES_STD), ("low_contrast", redness > LOW_CONTRAST_REDNESS),
                                           ("moved", change > MOVED_CHANGE)) if on]
            found.append({"beat": beat, "text": item["beat"].get("text", ""), "box": k, "rect": list(rect),
                          "raw": [round(lo, 3), round(hi, 3)], "clip": [round(item["box"][0], 3), round(item["box"][1], 3)],
                          "std": round(std, 1), "redness": round(redness, 3), "change": round(change, 1), "flags": flags})
    return {"name": script.stem, "script": str(script), "raw": str(raw), "frame": [W, H],
            "thresholds": {"crosses": CROSSES_STD, "low_contrast": LOW_CONTRAST_REDNESS, "moved": MOVED_CHANGE},
            "boxes": found}


# ---------------------------------------------------------------- sheet: one row per voice, and the page

PAGE_STYLE = """
:root{color-scheme:light dark;--bg:#f6f7f9;--card:#fff;--ink:#1d2127;--dim:#5d6670;--line:#d9dde3;--flag:#b3261e}
@media (prefers-color-scheme:dark){:root{--bg:#121417;--card:#1b1e22;--ink:#e8eaed;--dim:#9aa3ad;--line:#2e3339;--flag:#ff8a80}}
body{margin:0;padding:16px;background:var(--bg);color:var(--ink);
 font:16px/1.6 system-ui,-apple-system,"Apple SD Gothic Neo","Malgun Gothic","Noto Sans KR",sans-serif}
main{max-width:2000px;margin:0 auto}
h1{font-size:22px;margin:0 0 4px}
section{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px 16px;margin:16px 0}
section.flagged{border:2px solid var(--flag);border-left-width:8px}
h2{font-size:18px;margin:0}
a{color:inherit}
h2 a.back{font-size:13px;font-weight:400;color:var(--dim);margin-left:8px}
.dim{color:var(--dim);font-size:14px;margin:2px 0 8px}
.flags{color:var(--flag);font-weight:600}
.index{display:flex;flex-wrap:wrap;gap:2px 14px;list-style:none;padding:0;margin:8px 0;font-size:14px}
.index a{text-decoration:none;border-bottom:1px solid var(--line)}
.index a.flagged{color:var(--flag);font-weight:600}
.frames{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:8px;max-width:1940px}
.frames img{width:100%}
.crops{display:flex;flex-wrap:wrap;gap:8px;margin-top:8px}
figure{margin:0;max-width:100%}
img{display:block;max-width:100%;height:auto;border:1px solid var(--line)}
figcaption{color:var(--dim);font-size:13px}
audio{width:100%;max-width:640px;margin:8px 0}
dl{display:grid;grid-template-columns:max-content 1fr;gap:2px 12px;margin:8px 0}
dt{color:var(--dim)}
dd{margin:0}
ol,ul{margin:0;padding-left:20px}
"""


def _font(path: str, size: int):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def _wrap(text: str, font, width: float) -> list[str]:
    lines = []
    for paragraph in text.splitlines() or [""]:
        line = ""
        for word in paragraph.split(" "):
            candidate = f"{line} {word}" if line else word
            if line and font.getlength(candidate) > width:
                lines.append(line)
                line = word
            else:
                line = candidate
        lines.append(line)
    return lines


def _fit(text: str, font, width: float) -> str:
    if font.getlength(text) <= width:
        return text
    while text and font.getlength(text + "…") > width:
        text = text[:-1]
    return text + "…"


def _jpeg(image: Image.Image, width: int | None = None) -> bytes:
    if width and image.width != width:
        image = image.resize((width, max(1, round(image.height * width / image.width))), Image.LANCZOS)
    buf = io.BytesIO()
    image.save(buf, "JPEG", quality=JPEG_QUALITY)
    return buf.getvalue()


def _data_uri(mime: str, data: bytes) -> str:
    return f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"


def _voice_sound(reel: Path, start: float, end: float) -> tuple[str, bytes]:
    """The reel's own sound while a voice plays, small enough to put in the page (mp3, else AAC)."""
    for codec, fmt, mime in (("libmp3lame", "mp3", "audio/mpeg"), ("aac", "adts", "audio/aac")):
        done = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(0.0, start):.3f}", "-t", f"{max(0.1, end - start):.3f}",
                               "-i", str(reel), "-vn", *VOICE_SOUND, "-c:a", codec, "-f", fmt, "-"], capture_output=True)
        if done.returncode == 0 and done.stdout:
            return mime, done.stdout
    raise SystemExit(f"cannot cut the sound of {reel} at {start:.2f}-{end:.2f} s: {_last_line(done.stderr.decode(errors='replace'))}")


def _crop(frame: Image.Image, rect, scale: float) -> Image.Image:
    """A box's rectangle (frame px) and CROP_MARGIN px around it, cut from a reel frame and enlarged to fit
    SHEET_WIDTH x SHEET_WIDTH * 9/16 (CROP_ZOOM at most)."""
    x, y, w, h = rect
    region = [round(c * scale) for c in (max(0, x - CROP_MARGIN), max(0, y - CROP_MARGIN),
                                         min(W, x + w + CROP_MARGIN), min(H, y + h + CROP_MARGIN))]
    crop = frame.crop(region)
    zoom = min(SHEET_WIDTH / crop.width, SHEET_WIDTH * 9 / 16 / crop.height, CROP_ZOOM)
    return crop.resize((max(1, round(crop.width * zoom)), max(1, round(crop.height * zoom))), Image.LANCZOS)


def _row_picture(row: dict, frames: list[Image.Image], crops: list[Image.Image]) -> Image.Image:
    """One row as one picture: a header line, the frames with their times (the voice's three, then one per box moment;
    three to a line), the crops with what each box points at and its time, then the caption and the narration."""
    pad, gap = 16, 16
    width = 3 * SHEET_WIDTH + 2 * gap + 2 * pad
    bold, small = _font(edit_demo.FONT_BOLD, 24), _font(edit_demo.FONT_REG, 20)
    shown = [f.resize((SHEET_WIDTH, max(1, round(f.height * SHEET_WIDTH / f.width))), Image.LANCZOS) for f in frames]
    cells, x, y_crops, line_h = [], pad, 0, 0
    for crop, box in zip(crops, row["boxes"]):
        cell = max(crop.width, 300)
        if x > pad and x + cell > width - pad:
            x, y_crops, line_h = pad, y_crops + line_h + gap, 0
        cells.append((x, y_crops, crop, box))
        x, line_h = x + cell + gap, max(line_h, crop.height + 30)
    text_lines = [(f"caption: {row['caption'] or '-'}", small)] + [
        (line, small) for line in _wrap(f"narration: {row['say'] or '-'}", small, width - 2 * pad)]
    frame_h, frame_lines = max(f.height for f in shown), math.ceil(len(shown) / 3)
    crops_h = (y_crops + line_h + gap) if cells else 0
    height = pad + 36 + frame_lines * (frame_h + 34) + crops_h + 28 * len(text_lines) + pad
    image = Image.new("RGB", (width, height), (24, 27, 31))
    draw = ImageDraw.Draw(image)
    head = (f"#{row['row']}  {row['name']}   voice {row['start']:.2f}-{row['end']:.2f} s ({row['seconds']:.2f} s)"
            + (f"   hold {row['hold']:.2f} s" if row.get("hold") is not None else "")
            + f"   flags: {', '.join(row['flags']) or 'none'}")
    draw.text((pad, pad), _fit(head, bold, width - 2 * pad), font=bold, fill=(255, 138, 128) if row["flags"] else (232, 234, 237))
    y = pad + 36
    for i, (f, spec) in enumerate(zip(shown, row["frames"] + row["box_frames"])):
        fx, fy = pad + i % 3 * (SHEET_WIDTH + gap), y + i // 3 * (frame_h + 34)
        image.paste(f, (fx, fy))
        draw.text((fx, fy + f.height + 4), f"{spec['at']:.2f} s  ({spec['when']})", font=small, fill=(170, 178, 187))
    y += frame_lines * (frame_h + 34)
    for cx, cy, crop, box in cells:
        image.paste(crop, (cx, y + cy))
        label = (f"box {box['number']}: {box['what'] or '-'}  {box['at']:.2f} s"
                 + (f"  [{', '.join(box['flags'])}]" if box["flags"] else ""))
        draw.text((cx, y + cy + crop.height + 4), _fit(label, small, max(crop.width, 300)), font=small, fill=(232, 234, 237))
    y += crops_h
    for line, font in text_lines:
        draw.text((pad, y), line, font=font, fill=(232, 234, 237))
        y += 28
    return image


def _row_section(row: dict, frames: list[bytes], crops: list[bytes], sound: tuple[str, bytes], unmeasured: list[str]) -> str:
    """One row of the page. Every text is escaped; the boxes' numbers were made numbers when their report was read."""
    e = lambda s: html.escape(str(s), quote=True)  # noqa: E731
    times = (f"voice {row['start']:.2f}-{row['end']:.2f} s ({row['seconds']:.2f} s)"
             + (f" · hold {row['hold']:.2f} s" if row.get("hold") is not None else ""))
    figures = "".join(f'<figure><img src="{_data_uri("image/jpeg", data)}" alt="frame at {spec["at"]:.2f} s">'
                      f'<figcaption>{spec["at"]:.2f} s · {e(spec["when"])}</figcaption></figure>'
                      for data, spec in zip(frames, row["frames"] + row["box_frames"]))
    crop_figures = "".join(f'<figure><img src="{_data_uri("image/jpeg", data)}" alt="box {box["number"]}">'
                           f'<figcaption>box {box["number"]}: {e(box["what"] or "-")} · {box["at"]:.2f} s</figcaption></figure>'
                           for data, box in zip(crops, row["boxes"]))
    boxes = "".join(f'<li>{e(box["what"] or "-")}' + (f' <span class="flags">{e(", ".join(box["flags"]))}</span>' if box["flags"] else "")
                    + f' <span class="dim">std {box["std"]}, redness {box["redness"]}, change {box["change"]}</span></li>'
                    for box in row["boxes"])
    boxes += "".join(f'<li>{e(w)} <span class="dim">(no box measured)</span></li>' for w in unmeasured)
    parts = [f'<section id="r{row["row"]}"' + (' class="flagged"' if row["flags"] else "") + '>'
             f'<h2>#{row["row"]} {e(row["name"])} <a class="back" href="#top">index</a></h2>',
             f'<p class="dim">{e(times)}</p>',
             f'<p class="flags">{e(", ".join(row["flags"]))}</p>' if row["flags"] else "",
             f'<audio controls preload="none" src="{_data_uri(*sound)}"></audio>',
             f'<dl><dt>Caption</dt><dd>{e(row["caption"] or "-")}</dd><dt>Narration</dt><dd>{e(row["say"] or "-")}</dd>',
             f'<dt>Boxes</dt><dd><ol>{boxes}</ol></dd>' if boxes else "",
             f'<dt>Sources</dt><dd><ul>{"".join(f"<li>{e(s)}</li>" for s in row["sources"])}</ul></dd>' if row["sources"] else "",
             "</dl>",
             f'<div class="frames">{figures}</div>',
             f'<div class="crops">{crop_figures}</div>' if crop_figures else "",
             "</section>"]
    return "\n".join(p for p in parts if p)


def _report_boxes(path: Path, report: dict) -> list[dict]:
    """The boxes of a `boxes` report, with the fields the page shows made numbers (a report is a file that anyone can
    write, and the page is made to be sent): one line when one is missing or is not a number."""
    found = []
    for n, box in enumerate(report["boxes"], 1):
        try:
            rect, clip = [int(round(float(v))) for v in box["rect"]], [float(v) for v in box["clip"]]
            if len(rect) != 4 or len(clip) != 2 or not isinstance(box["flags"], list):
                raise ValueError
            found.append({**box, "box": int(box["box"]), "rect": rect, "clip": clip, "std": float(box["std"]),
                          "redness": float(box["redness"]), "change": float(box["change"]),
                          "flags": [str(f) for f in box["flags"]]})
        except (KeyError, TypeError, ValueError):
            raise SystemExit(f"{path}: box {n} is not as `check_demo.py boxes` writes it (it needs \"box\", \"rect\", "
                             f"\"clip\", \"std\", \"redness\", \"change\" and \"flags\")")
    return found


def _phrases(value) -> list[str]:
    """A texts entry's "what" or "sources": a list of phrases; one text is one phrase."""
    if value is None or value == "":
        return []
    return [str(v) for v in value] if isinstance(value, list) else [str(value)]


def _box_moment(box: dict, segment) -> float | None:
    """Where in the reel a box shows in a clip segment: the middle of the part of its time (its "clip" seconds) that the
    segment's window shows, as reel seconds; None when the window shows none of it (or the segment has no window)."""
    try:
        (w0, w1), (b0, b1) = [float(v) for v in segment["window"]], box["clip"]
        start = float(segment["start"])
    except (KeyError, TypeError, ValueError):
        return None
    a, b = max(b0, w0), min(b1, w1)
    return start + (a + b) / 2 - w0 if b > a else None


def build_sheet(reel: Path, plan_path: Path, texts_path: Path, boxes_paths: list[Path], out: Path) -> dict:
    """index.json, one JPEG per voice and review.html in `out` (see the module docstring); returns index.json's data."""
    plan = _read_json(plan_path, "the plan")
    texts = _read_json(texts_path, "the texts")
    if not isinstance(plan, dict) or not isinstance(plan.get("voices"), list):
        raise SystemExit(f"the plan {plan_path} has no list of voices")
    if not isinstance(texts, dict) or not all(isinstance(t, dict) for t in texts.values()):
        raise SystemExit(f'{texts_path} must hold {{"<name of a voice in the plan>": {{"caption", "say", "what", "sources"}}, ...}}')
    boxes_by_name: dict[str, list[dict]] = {}
    report_of: dict[str, list[Path]] = {}
    for path in boxes_paths:
        report = _read_json(path, "the boxes report")
        if not isinstance(report, dict) or "name" not in report or not isinstance(report.get("boxes"), list):
            raise SystemExit(f"{path} is not a report of `check_demo.py boxes` (no name or no list of boxes)")
        boxes_by_name.setdefault(str(report["name"]), []).extend(_report_boxes(path, report))
        report_of.setdefault(str(report["name"]), []).append(path)
    length = edit_demo.stream_seconds(reel, "v")
    if not length:
        raise SystemExit(f"cannot read a video stream in {reel}")
    scale = int(edit_demo.probe_size(reel).split("x")[0]) / W
    segments = plan.get("segments", [])
    # a plan written before the segments' windows were recorded cannot say when a box shows in the reel
    windows = any(isinstance(s, dict) and "window" in s for s in segments)
    out.mkdir(parents=True, exist_ok=True)
    names = [v["name"] for v in plan.get("voices", [])]
    for key in texts:  # a texts file keyed by other names gives an empty page: say so, still write the page
        if key not in names:
            print(f"sheet: texts key {key!r} matches no voice of the plan (voices: {', '.join(dict.fromkeys(names))})", file=sys.stderr)
    for k, name in enumerate(names, 1):
        if name not in texts:
            print(f"sheet: voice {k} ({name}) has no entry in the texts file", file=sys.stderr)
    for name, paths in report_of.items():
        if name not in names:
            print(f"sheet: boxes report {', '.join(p.name for p in paths)} (name {name!r}) matches no voice of the plan "
                  f"(voices: {', '.join(dict.fromkeys(names))})", file=sys.stderr)
    if boxes_by_name and not windows:
        print("sheet: the plan has no segment windows (its reel was built before they were recorded): each box's crop "
              "is taken from the frame at its voice's middle, whatever the box's time; build the reel again for crops at "
              "each box's own time", file=sys.stderr)
    rows, sections, placed = [], [], set()
    clamp = lambda t: round(min(max(t, 0.0), length - 0.05), 3)  # noqa: E731
    for k, v in enumerate(plan.get("voices", []), 1):
        text = texts.get(v["name"]) or {}
        what = _phrases(text.get("what"))
        at = [(when, clamp(t)) for when, t in
              (("start + 0.5 s", v["start"] + 0.5), ("middle", (v["start"] + v["end"]) / 2), ("end - 0.2 s", v["end"] - 0.2))]
        segment = v.get("segment")
        seg = segments[segment] if isinstance(segment, int) and 0 <= segment < len(segments) else {}
        # what[i] goes with the i-th box of the clip's report, on whichever row that box shows
        clip_boxes = [{**box, "number": i, "what": what[i - 1] if i <= len(what) else ""}
                      for i, box in enumerate(boxes_by_name.get(v["name"], []), 1)]
        if windows:   # each box at the middle of its own time, on the row whose window shows it
            boxes = [{**box, "at": clamp(t)} for box in clip_boxes if (t := _box_moment(box, seg)) is not None]
            placed.update((v["name"], box["number"]) for box in boxes)
        else:
            boxes = [{**box, "at": at[1][1]} for box in clip_boxes]
        moments = list(dict.fromkeys(box["at"] for box in boxes)) if windows else []
        box_frames = [{"at": t, "when": ("box " if len(ns) == 1 else "boxes ") + ", ".join(ns)}
                      for t in moments for ns in [[str(b["number"]) for b in boxes if b["at"] == t]]]
        frames = [_frame(reel, t) for _, t in at]
        moment_frames = {spec["at"]: _frame(reel, spec["at"]) for spec in box_frames}
        crops = [_crop(moment_frames[box["at"]] if windows else frames[1], box["rect"], scale) for box in boxes]
        row = {"row": k, "segment": segment, "name": v["name"], "start": v["start"], "end": v["end"],
               "seconds": round(v["end"] - v["start"], 3),
               "hold": seg.get("hold") if isinstance(seg, dict) else None,
               "frames": [{"at": t, "when": when} for when, t in at], "box_frames": box_frames,
               "caption": str(text.get("caption") or ""), "say": str(text.get("say") or ""), "what": what,
               "sources": _phrases(text.get("sources")), "boxes": boxes,
               "flags": list(dict.fromkeys(f for box in boxes for f in box["flags"])),
               "picture": f"{k:02d}-{re.sub(r'[^A-Za-z0-9._-]+', '_', v['name'])}.jpg"}
        shown = frames + [moment_frames[spec["at"]] for spec in box_frames]
        _row_picture(row, shown, crops).save(out / row["picture"], "JPEG", quality=JPEG_QUALITY)
        sections.append(_row_section(row, [_jpeg(f, SHEET_WIDTH) for f in shown], [_jpeg(c) for c in crops],
                                     _voice_sound(reel, v["start"], v["end"]), what[len(clip_boxes):]))
        rows.append(row)
        print(f"sheet: row {k} ({v['name']})", file=sys.stderr)
    for name, found in boxes_by_name.items():
        if windows and name in names:
            for i, box in enumerate(found, 1):
                if (name, i) not in placed:
                    print(f"sheet: box {i} of {name} (beat {box.get('beat', '?')}, {box['clip'][0]:.2f}-{box['clip'][1]:.2f} "
                          f"s of the clip) lies in no voiced segment's window: it is on no row", file=sys.stderr)
    e = lambda s: html.escape(str(s), quote=True)  # noqa: E731
    # links stay inside the page (href="#rN"): the page refers to no other file
    flagged = "; ".join(f'<a href="#r{r["row"]}">{r["row"]}</a> ({e(", ".join(r["flags"]))})' for r in rows if r["flags"])
    every_row = "".join(f'<li><a href="#r{r["row"]}"' + (' class="flagged"' if r["flags"] else "") + f'>{r["row"]} {e(r["name"])}</a>'
                        + (f' <span class="flags">{e(", ".join(r["flags"]))}</span>' if r["flags"] else "") + "</li>" for r in rows)
    head = ['<nav id="top">', f'<h1>{e(reel.name)}</h1>',
            f'<p class="dim">{len(rows)} narrations · reel {length:.1f} s · plan {e(plan_path.name)}. '
            f'Each row: frames at the voice\'s start + 0.5 s, middle and end - 0.2 s, its sound, the texts and the boxes'
            + (", each box with the frame at the middle of its own time and its crop from that frame. " if windows else
               ", each box's crop from the frame at the voice's middle. ") +
            f'Name a row by its number to have it changed.</p>',
            f'<p class="flags">Rows with flags: {flagged}</p>' if flagged else '<p class="dim">No flags.</p>',
            f'<ol class="index">{every_row}</ol>' if rows else ""]
    if plan.get("warnings"):
        head.append("<ul>" + "".join(f'<li class="dim">{e(w)}</li>' for w in plan["warnings"]) + "</ul>")
    head.append("</nav>")
    page = out / "review.html"
    page.write_text('<!doctype html>\n<html lang="ko">\n<head>\n<meta charset="utf-8">\n'
                    '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
                    f'<title>Review: {e(reel.stem)}</title>\n<style>{PAGE_STYLE}</style>\n</head>\n<body>\n<main>\n'
                    + "\n".join(head + sections) + "\n</main>\n</body>\n</html>\n", encoding="utf-8")
    index = {"reel": str(reel), "plan": str(plan_path), "page": page.name, "seconds": round(length, 3),
             "warnings": plan.get("warnings", []), "rows": rows}
    _write_json(out / "index.json", index)
    return index


# ---------------------------------------------------------------- command line

# ---------------------------------------------------------------- brief: what a take shows, to write from

BRIEF_LEAD = 0.3              # s from a caption's start to its voice (the lead the reference gives for "voice_at")
BRIEF_RATE = 7.6              # spoken characters a second, spaces counted (70 narration lines, 2026-11-24: 7.63)
BRIEF_EVERY = 5.0             # s a row of a recording without a camlog lasts
LIVE_BEFORE_END = (1.0, 0.2)  # "live" compares the take's frames this long before a row's end
LIVE_SIZE = (480, 270)        # both frames scaled to this, in grey
LIVE_LEVELS = 24              # a pixel has changed when it differs by more than this (an encoder flickers by 1 or 2)
LIVE_PIXELS = 8               # this many changed pixels: the picture moves
STILL_NAME = re.compile(r"\d{2,}-[abc]\.jpg")   # the stills brief writes, and the only files it removes from --out
STILL_QUALITY = 85
STILL_AFTER_MOVE = 0.1        # s after the camera stops that a row's first still is taken
NEAR = 0.05                   # s within which a frame-text entry and a camlog entry are the same moment
FRAMES_HELD = 4               # frames of the take held at once (a row's last still is also the later "live" frame)


def frametext_path(take: Path) -> Path:
    """<name>.frametext.txt beside the take (the recorder writes it under the take's own name)."""
    return take.with_name(take.stem + ".frametext.txt")


def speech_rate(voices: Path | None, rate: float | None) -> tuple[float, str]:
    """The spoken characters a second a budget is counted with, and where the number came from: measured in a
    voice.json when it holds lines to measure (their "spoken" characters over their "seconds"; a line without both,
    such as a person's own recording, is left out), else --rate, else BRIEF_RATE."""
    fallback = (rate, "--rate") if rate is not None else (BRIEF_RATE, "default")
    if voices is None:
        return fallback
    lines = _read_json(voices, "the voice list")
    spoken = [(len(v["spoken"]), float(v["seconds"])) for v in (lines.values() if isinstance(lines, dict) else [])
              if isinstance(v, dict) and isinstance(v.get("spoken"), str) and v["spoken"]
              and isinstance(v.get("seconds"), (int, float)) and v["seconds"] > 0]
    if not spoken:
        used = f"--rate {rate:g}" if rate is not None else f"the default rate {BRIEF_RATE:g}"
        print(f'brief: no line of {voices} has "spoken" text and "seconds": {used} is used', file=sys.stderr)
        return fallback
    return round(sum(chars for chars, _ in spoken) / sum(seconds for _, seconds in spoken), 2), str(voices)


def budget(seconds: float, rate: float) -> int:
    """The characters of narration that fit `seconds` of a finished clip: the voice starts BRIEF_LEAD after the caption
    and the reel keeps its voice gap before the next one."""
    return math.floor(max(0.0, seconds - BRIEF_LEAD - edit_demo.VOICE_GAP) * rate + 1e-9)


def picture_moves(a: Image.Image, b: Image.Image) -> bool:
    """Two frames differ by more than an encoder's flicker: LIVE_PIXELS or more pixels (at LIVE_SIZE, grey) changed by
    more than LIVE_LEVELS."""
    small = [image.convert("L").resize(LIVE_SIZE, Image.BILINEAR) for image in (a, b)]
    return ImageChops.difference(*small).point(lambda v: 255 if v > LIVE_LEVELS else 0).histogram()[255] >= LIVE_PIXELS


def _moves_in(moves, lo: float, hi: float) -> bool:
    return any(start < hi and stop > lo for _, start, stop in moves)


def _live(frame, start: float, end: float, moves) -> bool | None:
    """Whether the picture still changes as the stretch [start, end] of the take ends: the frames LIVE_BEFORE_END before
    its end, compared. None when that span begins before the stretch or a camera move lies in it."""
    a, b = end - LIVE_BEFORE_END[0], end - LIVE_BEFORE_END[1]
    if a < start - 1e-6 or _moves_in(moves, a, b):
        return None
    return picture_moves(frame(a), frame(b))


def _inside(t: float, lo: float, hi: float, last: bool) -> bool:
    """A time on a boundary belongs to the row that starts there; the last row also holds its own end."""
    return lo <= t < hi or (last and t == hi)


def _marks_and_notes(log: list[dict], texts: list[dict], holds) -> tuple[list[dict], list[dict]]:
    marks, notes = [], []
    for e in log:
        if e["kind"] == "shot" or not holds(float(e["t"])):
            continue
        if e["kind"] == "mark":
            text = next((x["text"] for x in texts if x["kind"] == "mark" and x["key"] == frametext_key(e.get("key"))
                         and abs(x["t"] - float(e["t"])) <= NEAR), None)
            marks.append({k: v for k, v in (("key", e.get("key")), ("label", e.get("label")), ("text", text)) if v is not None})
        else:
            # what a press pressed rides along: a tap's key, label and the element's own text
            notes.append({"kind": e["kind"], "t": float(e["t"]), **{k: e[k] for k in ("key", "label", "text") if e.get(k) is not None}})
    return marks, notes


def _view_rows(log: list[dict], texts: list[dict], end: float, speed: float, rate: float, frame, still) -> list[dict]:
    shots = [e for e in log if e["kind"] == "shot"]
    moves = edit_demo.camera_moves(log)
    stops = {id(e): stop for e, _, stop in moves}
    rows = []
    for n, shot in enumerate(shots, 1):
        last = n == len(shots)
        t0 = float(shot["t"])
        t1 = max(t0, end if last else float(shots[n]["t"]))
        seconds = round((t1 - t0) / speed, 3)
        row = {"row": n, **{k: shot[k] for k in ("key", "label") if shot.get(k) is not None},
               "raw": [round(t0, 3), round(t1, 3)], "seconds": seconds, "budget": budget(seconds, rate),
               "live": _live(frame, t0, t1, moves)}
        key = frametext_key(shot.get("key"))
        own = next((x for x in texts if x["kind"] == "shot" and x["key"] == key and abs(x["t"] - t0) <= NEAR), None)
        if own:
            row["text"] = own["text"]
        left = [x for x in texts if x["kind"] == "leave" and x["key"] == key and t0 < x["t"] <= t1]
        if left and left[-1]["text"] != row.get("text"):
            row["text_end"] = left[-1]["text"]
        row["texts"] = [{"key": x["key"], "t": x["t"], "text": x["text"]} for x in texts
                        if x["kind"] == "text" and _inside(x["t"], t0, t1, last)]
        row["marks"], row["notes"] = _marks_and_notes(log, texts, lambda t: _inside(t, t0, t1, last))
        first = stops[id(shot)] + STILL_AFTER_MOVE if id(shot) in stops else t0 + STILL_AFTER_MOVE
        row["stills"] = [still(f"{n:02d}-{name}.jpg", min(max(t, t0), max(t0, t1 - NEAR)))
                         for name, t in (("a", first), ("b", (t0 + t1) / 2), ("c", t1 - LIVE_BEFORE_END[1]))]
        rows.append(row)
    return rows


def _every_rows(end: float, every: float, speed: float, rate: float, frame, still) -> list[dict]:
    rows, t0 = [], 0.0
    while t0 < end - 0.01:
        t1 = min(t0 + every, end)
        n, seconds = len(rows) + 1, round((t1 - t0) / speed, 3)
        rows.append({"row": n, "raw": [round(t0, 3), round(t1, 3)], "seconds": seconds, "budget": budget(seconds, rate),
                     "live": _live(frame, t0, t1, []), "stills": [still(f"{n:02d}-a.jpg", t0)]})
        t0 = t1
    return rows


def _script_pieces(take: Path, scripts: list[Path], log: list[dict], take_end: float) -> list[dict]:
    """The scripts as pieces of the take, in the take's order, each with its captions' starts in the take's seconds.
    Stops, before anything is written, on a script the clip step would refuse and on two scripts that overlap."""
    pieces = []
    for path in scripts:
        story, beats = _clip_script(path)
        start, end = edit_demo.clip_span(take, log, story.get("start"), story.get("end"))
        speed = float(story.get("speed", edit_demo.DEFAULT_SPEED))
        edit_demo.beat_layout(beats, log, start=start, end=end, speed=speed, title=story.get("title"))   # the clip step's refusals
        end = min(end, take_end)   # a script may name an end past the take: its clip ends with the take
        start = min(start, end)
        floor = edit_demo.caption_floor(story.get("title"), speed)
        starts = [(min(end, start + max((edit_demo.script_time(b["at"], log) + float(b.get("offset", 0)) - start) / speed, floor) * speed), n, b)
                  for n, b in enumerate(beats, 1)]
        pieces.append({"stem": path.stem, "start": start, "end": end, "speed": speed, "beats": sorted(starts, key=lambda x: x[0])})
    pieces.sort(key=lambda p: p["start"])
    for a, b in zip(pieces, pieces[1:]):
        if a["end"] - b["start"] > 0.001:
            raise SystemExit(f"brief: {a['stem']} and {b['stem']} cover the same seconds of the take "
                             f"({b['start']:.2f}-{min(a['end'], b['end']):.2f} s): give the scripts of one run of the reel")
    return pieces


def _caption_rows(pieces: list[dict], log: list[dict], texts: list[dict], rate: float, frame, still) -> list[dict]:
    """One row per caption of the scripts cut from this take, in the take's order. A row runs from its caption's start
    over the rest of its clip and every following clip without a caption (it is narrated across, as a voice runs on
    over the reel's later segments of its group). It ends where the reel would hold its last frame: at the next
    caption when that is in the same script, else where the next script with a caption starts (not at that caption:
    the head of a captioned clip is that clip's own); the last row runs to the last script's end."""
    captions = [(t, p, n, b) for p in pieces for t, n, b in p["beats"]]
    for p in pieces:
        if not p["beats"] and (not captions or p["start"] < captions[0][0]):
            print(f"brief: {p['stem']} has no caption and comes before the first one: it is in no row", file=sys.stderr)
    moves = edit_demo.camera_moves(log)
    frame_texts = sorted((x for x in texts if x["kind"] != "mark"), key=lambda x: x["t"])
    rows = []
    for k, (t0, piece, n, beat) in enumerate(captions):
        last = k + 1 == len(captions)
        t1 = pieces[-1]["end"] if last else captions[k + 1][0] if captions[k + 1][1] is piece else captions[k + 1][1]["start"]
        spans = [(max(t0, p["start"]), min(t1, p["end"]), p["speed"]) for p in pieces
                 if min(t1, p["end"]) - max(t0, p["start"]) > 1e-6] or [(t0, t0, piece["speed"])]
        seconds = round(sum((hi - lo) / speed for lo, hi, speed in spans), 3)

        def holds(t: float, closed_end: bool = False) -> bool:   # a time on a boundary belongs to the row that starts there
            return any((lo < t <= hi) if closed_end else (lo <= t < hi or (last and t == hi)) for lo, hi, _ in spans)

        raw = [[round(lo, 3), round(hi, 3)] for lo, hi, _ in spans]
        row = {"row": k + 1, "script": piece["stem"], "beat": n, "caption": beat.get("text", ""),
               "raw": raw[0] if len(raw) == 1 else raw, "seconds": seconds, "budget": budget(seconds, rate),
               "live": _live(frame, spans[-1][0], spans[-1][1], moves)}
        before = [x for x in frame_texts if x["t"] <= t0 + NEAR]
        if before:
            row["text"] = before[-1]["text"]
        # what was kept later inside the row, in the take's order: each view's text as the camera arrives and as it
        # leaves, and what rec.text kept. The row's end is a leave that is the last of them.
        later = [x for x in frame_texts if x["t"] > t0 + NEAR and holds(x["t"], closed_end=x["kind"] == "leave")]
        if later and later[-1]["kind"] == "leave":
            if later[-1]["text"] != (later[-2]["text"] if len(later) > 1 else row.get("text")):
                row["text_end"] = later[-1]["text"]
            later = later[:-1]
        row["texts"] = [{"key": x["key"], "t": x["t"], "text": x["text"]} for x in later]
        row["marks"], row["notes"] = _marks_and_notes(log, texts, holds)
        # the stills: half a clip second after the caption (after a camera move under way then), the second of the
        # take at half the row's clip seconds, and just before the row's last piece ends
        lo, hi, speed = spans[0]
        first = lo + 0.5 * speed
        first = next((stop + STILL_AFTER_MOVE for _, start, stop in moves if start <= first < stop), first)
        half, middle = seconds / 2, spans[-1][1]
        for a, b, v in spans:
            if half <= (b - a) / v:
                middle = a + half * v
                break
            half -= (b - a) / v
        row["stills"] = [still(f"{k + 1:02d}-a.jpg", min(max(first, lo), max(lo, hi - NEAR))),
                         still(f"{k + 1:02d}-b.jpg", middle),
                         still(f"{k + 1:02d}-c.jpg", max(spans[-1][0], spans[-1][1] - LIVE_BEFORE_END[1]))]
        rows.append(row)
    return rows


class FrameReader:
    """The take's frames by their second, read once while a row needs them. The last FRAMES_HELD are held and no more:
    a 1080p frame is about 8 MB and a long recording has hundreds of rows."""

    def __init__(self, take: Path, end: float):
        self.take, self.end, self.held = take, end, {}

    def __call__(self, t: float) -> Image.Image:
        t = round(min(max(t, 0.0), max(0.0, self.end - NEAR)), 3)
        if t not in self.held:
            if len(self.held) >= FRAMES_HELD:
                del self.held[next(iter(self.held))]   # the oldest
            self.held[t] = take_frame(self.take, t)
        return self.held[t]


def build_brief(take: Path, out: Path, *, scripts: list[Path] = (), speed: float = edit_demo.DEFAULT_SPEED,
                rate: float = BRIEF_RATE, rate_from: str = "default", every: float = BRIEF_EVERY) -> dict:
    """The `brief` report of a take, written to <out>/brief.json with its stills; the take and its files are only read."""
    end = edit_demo.stream_seconds(take, "v")
    if not end:
        raise SystemExit(f"cannot read the take {take} as a video")
    log = edit_demo.read_camlog(take)
    texts = read_frametext(frametext_path(take))
    mode = "captions" if scripts else "views" if any(e["kind"] == "shot" for e in log) else "every"
    pieces = _script_pieces(take, list(scripts), log, end) if scripts else []   # refused here, before --out is touched
    out.mkdir(parents=True, exist_ok=True)
    for old in out.iterdir():   # an earlier run's stills, and nothing else of the folder
        if old.is_file() and STILL_NAME.fullmatch(old.name):
            old.unlink()
    frame = FrameReader(take, end)

    def still(name: str, t: float) -> str:
        frame(t).save(out / name, "JPEG", quality=STILL_QUALITY)
        return name

    if mode == "captions":   # each script has its own speed: the report carries none
        report = {"take": str(take), "mode": mode, "rate": rate, "rate_from": rate_from,
                  "rows": _caption_rows(pieces, log, texts, rate, frame, still)}
    else:
        rows = (_view_rows(log, texts, end, speed, rate, frame, still) if mode == "views"
                else _every_rows(end, every, speed, rate, frame, still))
        report = {"take": str(take), "mode": mode, "speed": speed, "rate": rate, "rate_from": rate_from, "rows": rows}
    if log and mode != "every" and not frametext_path(take).is_file():   # said once the rows stand: a refusal is one line
        print(f"brief: no {frametext_path(take).name} beside the take: rows carry no text", file=sys.stderr)
    _write_json(out / "brief.json", report)
    return report


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("audit", help="the reel's sound against its plan, its lengths and its loudness")
    a.add_argument("reel", type=Path)
    a.add_argument("--plan", type=Path, help="default: <reel stem>.voice.json beside the reel")
    a.add_argument("--tolerance", type=float, default=VOICE_TOLERANCE, help="seconds a voice may start or end off its plan")
    a.add_argument("--loudness", type=float, default=edit_demo.VOICE_LOUDNESS, help="target integrated loudness, LUFS")
    a.add_argument("--out", type=Path, required=True, help="the report (JSON), written either way")
    b = sub.add_parser("boxes", help="what lies under each highlight box of a clip script, on the raw take")
    b.add_argument("script", type=Path)
    b.add_argument("--raw", type=Path, required=True, help="the take the clip is cut from (its camlog beside it)")
    b.add_argument("--out", type=Path, required=True)
    s = sub.add_parser("sheet", help="one row per voice and review.html, one file to send")
    s.add_argument("reel", type=Path)
    s.add_argument("--plan", type=Path, required=True)
    s.add_argument("--texts", type=Path, required=True, help='JSON: {"<name of a voice in the plan>": {"caption", "say", "what", "sources"}}')
    s.add_argument("--boxes", type=Path, nargs="+", action="extend", default=[], help="reports of `boxes`")
    s.add_argument("--out", type=Path, required=True, help="folder for index.json, the JPEGs and review.html")
    f = sub.add_parser("brief", help="what a take shows, row by row, to write its captions and narration from")
    f.add_argument("take", type=Path, help="the raw take (its camlog and frame text beside it), or any recording")
    f.add_argument("--out", type=Path, required=True, help="folder for brief.json and the stills")
    f.add_argument("--script", type=Path, nargs="+", action="extend", default=[],
                   help="clip scripts cut from this take, those of one run of the reel: one row per caption")
    f.add_argument("--speed", type=float, default=edit_demo.DEFAULT_SPEED, help="the clip's speed, without --script")
    f.add_argument("--voices", type=Path, help="a voice.json: the speech rate is measured in it")
    f.add_argument("--rate", type=float, help=f"spoken characters a second (default {BRIEF_RATE:g})")
    f.add_argument("--every", type=float, default=BRIEF_EVERY, help="seconds a row lasts for a recording without a camlog")
    args = ap.parse_args()
    if args.cmd == "audit":
        plan = args.plan or args.reel.with_suffix(".voice.json")
        try:
            report = audit(args.reel, plan, tolerance=args.tolerance, target=args.loudness)
        except SystemExit as stop:   # input that cannot be read is a problem too, and the report still says so
            report = {"reel": str(args.reel), "plan": str(plan), "ok": False, "problems": [str(stop)], "warnings": []}
        _write_json(args.out, report)
        print(json.dumps({"out": str(args.out), "ok": report["ok"], "problems": len(report["problems"]),
                          "voices": len(report.get("voices", [])), "integrated": report.get("loudness", {}).get("integrated")}))
        for w in report["warnings"]:
            print(f"audit: warning: {w}", file=sys.stderr)
        if report["problems"]:
            raise SystemExit(f"audit: {args.reel.name}: {len(report['problems'])} problem(s)\n  " + "\n  ".join(report["problems"]))
    elif args.cmd == "boxes":
        report = measure_boxes(args.script, args.raw)
        _write_json(args.out, report)
        print(json.dumps({"out": str(args.out), "boxes": len(report["boxes"]),
                          "flagged": sum(1 for box in report["boxes"] if box["flags"])}))
    elif args.cmd == "brief":
        for name in ("rate", "every", "speed"):
            if getattr(args, name) is not None and getattr(args, name) <= 0:
                ap.error(f"--{name} must be above 0")
        rate, rate_from = speech_rate(args.voices, args.rate)
        report = build_brief(args.take, args.out, scripts=args.script, speed=args.speed, rate=rate, rate_from=rate_from,
                             every=args.every)
        print(json.dumps({"out": str(args.out / "brief.json"), "rows": len(report["rows"]),
                          "stills": sum(len(row["stills"]) for row in report["rows"]),
                          "live": sum(1 for row in report["rows"] if row["live"] is True), "rate": rate}))
    else:
        index = build_sheet(args.reel, args.plan, args.texts, args.boxes, args.out)
        page = args.out / index["page"]
        print(json.dumps({"out": str(args.out), "rows": len(index["rows"]), "page": str(page), "bytes": page.stat().st_size}))


if __name__ == "__main__":
    main()
