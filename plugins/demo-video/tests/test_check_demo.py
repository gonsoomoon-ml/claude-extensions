"""check_demo.py: a narrated reel's sound against its plan, highlight boxes measured on the raw take, the review page.

Needs ffmpeg/ffprobe and Pillow. Tones made with ffmpeg stand in for narration lines, plain-colour clips for takes,
pictures drawn with Pillow for frames.
"""
import base64
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

PLUGIN = Path(__file__).resolve().parents[1]
CHECK = PLUGIN / "skills" / "recording-demo-videos" / "scripts" / "check_demo.py"

spec = importlib.util.spec_from_file_location("check_demo", CHECK)
check_demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_demo)
edit_demo = check_demo.edit_demo   # the clip step's rules, as check_demo reads them

needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")
FPS = 30


def cli(*args) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(CHECK), *map(str, args)], capture_output=True, text=True)


def make_clip(path: Path, seconds: float, colour: str = "red", size: str = "320x180") -> Path:
    """A finished clip of one plain colour (H.264 + silent AAC, as the clip step writes); small so the reel is quick."""
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"color=c={colour}:size={size}:rate={FPS}:duration={seconds}",
                    "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000", "-shortest",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", str(path)], check=True)
    return path


def make_tone(path: Path, seconds: float, freq: int = 440) -> Path:
    """A narration line stand-in: a mono 24 kHz tone, as the speech service writes mp3."""
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"sine=frequency={freq}:sample_rate=24000:duration={seconds}",
                    "-af", "volume=-6dB", "-ac", "1", str(path)], check=True)
    return path


def build_reel(tmp_path: Path, segments: list[dict], name: str = "reel") -> tuple[Path, dict]:
    spec_path = tmp_path / f"{name}.json"
    spec_path.write_text(json.dumps({"segments": segments}))
    out = tmp_path / f"{name}.mp4"
    edit_demo.build_reel(spec_path, out)
    return out, json.loads(out.with_suffix(".voice.json").read_text())


def make_take(path: Path, filters: str = "", seconds: float = 10, size: str = "1920x1080") -> Path:
    """A raw take (VP8 webm, like a Playwright recording) of a grey page, with drawbox filters on it, and its camlog."""
    vf = f"color=c=0x808080:size={size}:rate=30:duration={seconds}" + (f",{filters}" if filters else "")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", vf, "-c:v", "libvpx", "-b:v", "4M",
                    "-pix_fmt", "yuv420p", str(path)], check=True)
    path.with_suffix(".camlog.json").write_text(json.dumps({"log": [{"t": 0.5, "kind": "shot", "key": "hero"}]}))
    return path


# ---------------------------------------------------------------- speech against the plan

@needs_ffmpeg
def test_speech_intervals_finds_tone_bursts(tmp_path):
    audio = tmp_path / "tones.wav"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                    "aevalsrc=0.5*sin(2*PI*440*t)*(between(t\\,1\\,2.5)+between(t\\,4\\,6)):s=24000:d=7", str(audio)], check=True)
    found = check_demo.speech_intervals(audio)
    assert len(found) == 2, found
    for (a, b), (x, y) in zip(found, [(1.0, 2.5), (4.0, 6.0)]):
        assert a == pytest.approx(x, abs=0.1) and b == pytest.approx(y, abs=0.1)


def test_a_voice_off_its_plan_is_named():
    plan = [{"segment": 0, "name": "intro", "start": 1.0, "end": 2.5}]
    (problem,) = check_demo.voice_problems(plan, [(1.4, 2.9)])
    assert "voice 1 (intro)" in problem and "1.00-2.50" in problem and "1.40-2.90" in problem
    assert check_demo.voice_problems(plan, [(1.2, 2.3)]) == [], "within 0.25 s"
    assert check_demo.voice_problems(plan, [(1.1, 1.6), (1.9, 2.4)]) == [], "a pause inside one voice"
    two = plan + [{"segment": 1, "name": "next", "start": 4.0, "end": 5.0}]
    problems = check_demo.voice_problems(two, [(1.05, 2.45), (7.0, 8.0)])
    assert len(problems) == 2, problems
    assert any("voice 2 (next)" in p and "4.00-5.00" in p for p in problems), "the missing voice"
    assert any("7.00-8.00" in p and "no voice" in p for p in problems), "the extra sound"


def test_voices_closer_than_the_silence_detection_can_part_are_checked_as_one():
    """Two voices planned 0.2 s apart sound as one interval to a 0.35 s silence detection: the audit says so in a
    problem line instead of reporting the first voice's end and the second's start as shifted."""
    plan = [{"segment": 0, "name": "a", "start": 1.0, "end": 2.0}, {"segment": 1, "name": "b", "start": 2.2, "end": 3.0},
            {"segment": 2, "name": "c", "start": 4.0, "end": 5.0}]
    groups, problems = check_demo.close_voices(plan, 0.35)
    (problem,) = problems
    assert "voice 1 (a)" in problem and "voice 2 (b)" in problem and "0.20 s apart" in problem
    assert [(g["start"], g["end"]) for g in groups] == [(1.0, 3.0), (4.0, 5.0)]
    assert check_demo.voice_problems(groups, [(1.1, 2.95), (4.1, 4.95)]) == []


# ---------------------------------------------------------------- the border of a box on a picture

def text_like_picture() -> Image.Image:
    """A flat light page with lines of 'text': black rows 4 px high every 12 px over x 500-900, y 300-500."""
    image = Image.new("RGB", (1920, 1080), (230, 230, 230))
    draw = ImageDraw.Draw(image)
    for y in range(300, 500, 12):
        draw.rectangle([500, y, 900, y + 3], fill=(0, 0, 0))
    return image


def test_border_stats_tell_a_clean_border_from_one_that_crosses_text():
    image = text_like_picture()
    clean = check_demo.border_stats(image, (480, 280, 440, 240))      # the border runs on the page around the text
    across = check_demo.border_stats(image, (600, 350, 200, 100))     # the border runs over the lines
    assert clean["std"] < 5
    assert across["std"] > 28


def test_redness_is_high_on_a_red_background():
    assert edit_demo.HIGHLIGHT.startswith("0xff2a2a")
    for red in [(255, 0, 0), (211, 47, 47), (229, 57, 53)]:
        assert check_demo.border_stats(Image.new("RGB", (400, 300), red), (50, 50, 200, 100))["redness"] > 0.6, red
    for other in [(255, 255, 255), (128, 128, 128), (30, 30, 30), (31, 111, 235), (255, 152, 0)]:   # mid grey too
        assert check_demo.border_stats(Image.new("RGB", (400, 300), other), (50, 50, 200, 100))["redness"] < 0.5, other


def test_region_change_is_zero_for_the_same_frame_and_large_when_the_content_moved():
    a = text_like_picture()
    b = Image.new("RGB", a.size, (230, 230, 230))
    b.paste(a.crop((0, 0, 1920, 1074)), (0, 6))                        # the same page, scrolled down by 6 px
    rect = (520, 320, 300, 150)
    assert check_demo.region_change(a, a.copy(), rect) == 0
    assert check_demo.region_change(a, b, rect) > 12
    assert check_demo.region_change(a, b, (1200, 600, 300, 150)) == 0, "outside the lines nothing moved"


# ---------------------------------------------------------------- audit

@needs_ffmpeg
def test_audit_fails_on_a_shifted_voice_and_passes_on_the_planned_one(tmp_path):
    a, b = make_clip(tmp_path / "a.mp4", 3), make_clip(tmp_path / "b.mp4", 3, "blue")
    reel, plan = build_reel(tmp_path, [
        {"file": str(a), "voice": str(make_tone(tmp_path / "one.mp3", 1.5)), "voice_at": 0.3},
        {"file": str(b), "voice": str(make_tone(tmp_path / "two.mp3", 1.0, freq=660)), "voice_at": 0.5}])
    done = cli("audit", reel, "--out", tmp_path / "audit.json")
    assert done.returncode == 0, done.stderr
    report = json.loads((tmp_path / "audit.json").read_text())
    assert report["ok"] is True and report["problems"] == []
    assert [v["name"] for v in report["voices"]] == ["a", "b"]
    for v, planned in zip(report["voices"], plan["voices"]):
        assert v["planned"] == [planned["start"], planned["end"]]
        assert abs(v["heard"][0] - planned["start"]) <= 0.25 and abs(v["heard"][1] - planned["end"]) <= 0.25
    assert report["loudness"]["filter"].startswith("ebur128")
    assert report["loudness"]["integrated"] == pytest.approx(-16, abs=1.5)
    assert abs(report["length"]["video"] - report["length"]["audio"]) <= 0.1

    # the same reel with its sound 0.5 s late (and as long as before)
    shifted = tmp_path / "shifted.mp4"
    seconds = report["length"]["audio"]
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(reel), "-filter_complex",
                    f"[0:a]adelay=500|500,atrim=end={seconds:.4f}[a]", "-map", "0:v", "-map", "[a]", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "96k", str(shifted)], check=True)
    done = cli("audit", shifted, "--plan", reel.with_suffix(".voice.json"), "--out", tmp_path / "shifted.json")
    assert done.returncode == 1
    report = json.loads((tmp_path / "shifted.json").read_text())
    assert report["ok"] is False
    assert len(report["problems"]) == 2, report["problems"]
    assert "voice 1 (a)" in report["problems"][0] and "voice 2 (b)" in report["problems"][1]
    for line in report["problems"]:
        assert line in done.stderr, "one line per problem"


@needs_ffmpeg
def test_audit_fails_on_a_reel_off_the_loudness_target(tmp_path):
    a = make_clip(tmp_path / "a.mp4", 3)
    reel, _ = build_reel(tmp_path, [{"file": str(a), "voice": str(make_tone(tmp_path / "one.mp3", 2.0)), "voice_at": 0.3}])
    done = cli("audit", reel, "--loudness", -23, "--out", tmp_path / "audit.json")
    assert done.returncode == 1
    (problem,) = json.loads((tmp_path / "audit.json").read_text())["problems"]
    assert "LUFS" in problem and "-23" in problem


# ---------------------------------------------------------------- boxes

BOX = [400, 300, 400, 200]
STRIPE = "drawbox=x=560:y=0:w=80:h=1080:color=black:t=fill"                       # crosses the box's top and bottom
LATE_BLOCK = "drawbox=x=450:y=350:w=300:h=100:color=white:t=fill:enable='gte(t,6)'"  # appears inside the box at 6 s


def box_script(tmp_path: Path, name: str = "a") -> Path:
    script = tmp_path / f"{name}.json"
    script.write_text(json.dumps({"speed": 1, "start": 0, "beats": [
        {"at": 2.0, "dur": 6, "text": "look", "box": BOX, "box_delay": 1.0}]}))   # the box shows 3.0-8.0 s of the take
    return script


@needs_ffmpeg
def test_boxes_measures_on_the_raw_take(tmp_path):
    """The clip holds the red border and the caption; `boxes` reads the take, so cutting the clip changes nothing."""
    take = make_take(tmp_path / "take.webm", f"{STRIPE},{LATE_BLOCK}")
    script = box_script(tmp_path)
    done = cli("boxes", script, "--raw", take, "--out", tmp_path / "before.json")
    assert done.returncode == 0, done.stderr
    before = json.loads((tmp_path / "before.json").read_text())
    (box,) = before["boxes"]
    assert box["rect"] == BOX and box["raw"] == pytest.approx([3.0, 8.0], abs=0.01)
    assert box["std"] > 28 and box["redness"] < 0.6 and box["change"] > 12
    assert box["flags"] == ["crosses", "moved"]

    clip = tmp_path / "a.mp4"
    edit_demo.build_clip(take, clip, None, None, None, None, True, None, script)
    frame = tmp_path / "clip-frame.png"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "5", "-i", str(clip), "-frames:v", "1", str(frame)], check=True)
    assert check_demo.border_stats(Image.open(frame), tuple(BOX))["redness"] > 0.6, "the clip's frame holds the red border"

    assert cli("boxes", script, "--raw", take, "--out", tmp_path / "after.json").returncode == 0
    after = json.loads((tmp_path / "after.json").read_text())
    assert after["boxes"] == before["boxes"]


@needs_ffmpeg
def test_boxes_reads_a_smaller_take_as_the_clip_scales_it(tmp_path):
    """A 1280x720 take is scaled to 1920x1080 like the clip step does, so a box is measured where it is drawn."""
    take = make_take(tmp_path / "take.webm", "drawbox=x=373:y=0:w=54:h=720:color=black:t=fill", size="1280x720")
    script = tmp_path / "a.json"
    script.write_text(json.dumps({"speed": 1, "start": 0, "beats": [
        {"at": 2.0, "dur": 3, "text": "on", "box": [[400, 300, 400, 200], [1200, 300, 400, 200]]}]}))
    assert cli("boxes", script, "--raw", take, "--out", tmp_path / "boxes.json").returncode == 0
    on_stripe, beside = json.loads((tmp_path / "boxes.json").read_text())["boxes"]
    assert "crosses" in on_stripe["flags"] and beside["flags"] == []


# ---------------------------------------------------------------- sheet

@needs_ffmpeg
def test_sheet_writes_one_row_per_voice_in_one_html_file(tmp_path):
    a, b, c = make_clip(tmp_path / "a.mp4", 3), make_clip(tmp_path / "b.mp4", 3, "blue"), make_clip(tmp_path / "c.mp4", 2, "green")
    reel, plan = build_reel(tmp_path, [
        {"file": str(a), "voice": str(make_tone(tmp_path / "one.mp3", 1.5)), "voice_at": 0.3},
        {"file": str(b), "voice": str(make_tone(tmp_path / "two.mp3", 1.0, freq=550)), "voice_at": 0.5},
        {"file": str(c), "voice": str(make_tone(tmp_path / "three.mp3", 1.0, freq=660)), "voice_at": 0.2}])
    take = make_take(tmp_path / "take.webm", STRIPE, seconds=6)
    assert cli("boxes", box_script(tmp_path), "--raw", take, "--out", tmp_path / "a.boxes.json").returncode == 0
    texts = tmp_path / "texts.json"
    texts.write_text(json.dumps({
        "a": {"caption": "정책 세 개가 걸려 있습니다", "say": "에이전트 게이트웨이에 정책 세 개가 걸려 있습니다.",
              "what": ["기록 모드로 걸린 정책 세 줄"], "sources": ["화면"]},
        "b": {"say": "버튼 한 번으로 정책이 붙었습니다."}}, ensure_ascii=False), encoding="utf-8")   # "c" has no entry
    out = tmp_path / "review"
    done = cli("sheet", reel, "--plan", reel.with_suffix(".voice.json"), "--texts", texts,
               "--boxes", tmp_path / "a.boxes.json", "--out", out)
    assert done.returncode == 0, done.stderr

    index = json.loads((out / "index.json").read_text())
    assert [r["name"] for r in index["rows"]] == ["a", "b", "c"] == [v["name"] for v in plan["voices"]]
    for row, voice in zip(index["rows"], plan["voices"]):
        assert Image.open(out / row["picture"]).format == "JPEG"
        assert [f["at"] for f in row["frames"]] == pytest.approx(
            [voice["start"] + 0.5, (voice["start"] + voice["end"]) / 2, voice["end"] - 0.2], abs=1e-3)
    first = index["rows"][0]
    assert [x["what"] for x in first["boxes"]] == ["기록 모드로 걸린 정책 세 줄"] and first["flags"] == ["crosses"]
    assert index["rows"][2]["say"] == "" and index["rows"][2]["boxes"] == []

    page = (out / "review.html").read_text(encoding="utf-8")
    assert page.count("<audio") == len(plan["voices"])
    sources = re.findall(r'\bsrc="([^"]*)"', page)
    assert sources and all(s.startswith("data:") for s in sources), "every picture and sound is inside the file"
    assert not re.search(r"\bhref=|url\(|<link|<script|<iframe", page), "no reference to another file"
    assert '<meta charset="utf-8">' in page and "에이전트 게이트웨이에 정책 세 개가 걸려 있습니다." in page
    assert "기록 모드로 걸린 정책 세 줄" in page and "crosses" in page
    pictures = [s for s in sources if s.startswith("data:image/jpeg;base64,")]
    assert len(pictures) == 3 * 3 + 1, "three frames a row and one crop for the one box"
    sound = next(s for s in sources if s.startswith("data:audio/"))
    assert len(base64.b64decode(sound.split(",", 1)[1])) > 1000
