"""check_demo.py: a narrated reel's sound against its plan, highlight boxes measured on the raw take, the review page.

Needs ffmpeg/ffprobe and Pillow. Tones made with ffmpeg stand in for narration lines, plain-colour clips for takes,
pictures drawn with Pillow for frames.
"""
import array
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


def make_voice(path: Path, lead: float, tone: float, trail: float, freq: int = 440, gain_db: int = -6, fade: float = 0.0) -> Path:
    """A voice file whose sound starts `lead` s in and stops `trail` s before its end (a tone of `tone` s, which fades
    in and out over `fade` s when given), so a test knows where its sound lies."""
    fades = f",afade=t=in:d={fade},afade=t=out:st={tone - fade}:d={fade}" if fade else ""
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"sine=frequency={freq}:sample_rate=24000:duration={tone}",
                    "-af", f"volume={gain_db}dB{fades},adelay={round(lead * 1000)},apad=pad_dur={trail}", "-ac", "1", str(path)],
                   check=True)
    return path


def build_reel(tmp_path: Path, segments: list[dict], name: str = "reel") -> tuple[Path, dict]:
    spec_path = tmp_path / f"{name}.json"
    spec_path.write_text(json.dumps({"segments": segments}))
    out = tmp_path / f"{name}.mp4"
    edit_demo.build_reel(spec_path, out)
    return out, json.loads(out.with_suffix(".voice.json").read_text())


def audio_seconds(path: Path) -> float:
    return float(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=duration",
                                 "-of", "csv=p=0", str(path)], check=True, capture_output=True, text=True).stdout)


def with_sound_moved(reel: Path, seconds: float, out: Path) -> Path:
    """The reel with all its sound `seconds` later (earlier when negative) and as long as before; the picture copied."""
    length, ms = audio_seconds(reel), round(abs(seconds) * 1000)
    af = (f"adelay={ms}|{ms},atrim=end={length:.4f}" if seconds > 0 else
          f"atrim=start={-seconds:.4f},asetpts=PTS-STARTPTS,apad=whole_dur={length:.4f}")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(reel), "-filter_complex", f"[0:a]{af}[a]", "-map", "0:v", "-map", "[a]",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "96k", str(out)], check=True)
    return out


def _samples(sound: bytes, tmp: Path) -> array.array:
    path = tmp / "row-sound.bin"
    path.write_bytes(sound)
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "s16le", "-ac", "1", "-ar", "48000", "-"],
                         check=True, capture_output=True).stdout
    return array.array("h", pcm)


def loud_span(sound: bytes, tmp: Path) -> tuple[float, float, float]:
    """Where the part of a piece of sound louder than a tenth of its peak starts and ends, and the sound's length (s)."""
    samples = _samples(sound, tmp)
    peak = max(abs(s) for s in samples)
    loud = [i for i, s in enumerate(samples) if abs(s) > peak / 10]
    return loud[0] / 48000, (loud[-1] + 1) / 48000, len(samples) / 48000


def tone_frequency(sound: bytes, tmp: Path) -> float:
    """The frequency of the tone in a piece of sound: zero crossings over the part louder than a tenth of its peak."""
    samples = _samples(sound, tmp)
    peak = max(abs(s) for s in samples)
    loud = [i for i, s in enumerate(samples) if abs(s) > peak / 10]
    a, b = loud[0], loud[-1]
    crossings = sum(1 for i in range(a, b) if (samples[i] < 0) != (samples[i + 1] < 0))
    return crossings / 2 / ((b - a) / 48000)


@pytest.fixture(scope="module")
def tone_reel(tmp_path_factory):
    """Three clips whose voices are mp3 tones: like a speech line, an mp3 runs on past its sound."""
    d = tmp_path_factory.mktemp("tone-reel")
    segments = [{"file": str(make_clip(d / f"c{i}.mp4", 4, colour)), "voice": str(make_tone(d / f"v{i}.mp3", seconds, freq)),
                 "voice_at": at}
                for i, (colour, seconds, freq, at) in enumerate([("red", 1.5, 440, 0.3), ("blue", 1.2, 660, 0.5),
                                                                  ("green", 1.0, 880, 0.3)])]
    return build_reel(d, segments)


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


@needs_ffmpeg
@pytest.mark.parametrize("shift, passes", [(-0.3, False), (-0.2, True), (0.2, True), (0.3, False)])
def test_audit_holds_a_shift_to_its_tolerance_in_both_directions(tmp_path, tone_reel, shift, passes):
    """A voice file runs on past its sound (an mp3's last frame, a speech line's lead-in): the reel's sound is held
    against each file's own first and last sound, so 0.25 s means 0.25 s early or late, at both ends."""
    reel, _ = tone_reel
    moved = with_sound_moved(reel, shift, tmp_path / "moved.mp4")
    done = cli("audit", moved, "--plan", reel.with_suffix(".voice.json"), "--out", tmp_path / "audit.json")
    report = json.loads((tmp_path / "audit.json").read_text())
    assert (done.returncode == 0) is passes, report["problems"]
    for v in report["voices"]:
        start, (onset, end) = v["planned"][0], v["file_sound"]
        assert onset < 0.05 and end < v["planned"][1] - start, "a tone sounds from its file's start to before its end"
        assert v["expected"] == pytest.approx([start + onset, start + end], abs=1e-3)
        assert v["start_off"] == pytest.approx(shift, abs=0.03) and v["end_off"] == pytest.approx(shift, abs=0.03)


@needs_ffmpeg
def test_audit_holds_a_voice_whose_file_is_gone_against_the_plan(tmp_path, tone_reel):
    reel, _ = tone_reel
    plan = json.loads(reel.with_suffix(".voice.json").read_text())
    plan["voices"][1]["file"] = str(tmp_path / "gone.mp3")
    (tmp_path / "plan.json").write_text(json.dumps(plan))
    done = cli("audit", reel, "--plan", tmp_path / "plan.json", "--out", tmp_path / "audit.json")
    assert done.returncode == 0, done.stderr
    report = json.loads((tmp_path / "audit.json").read_text())
    (warning,) = report["warnings"]
    assert "voice 2" in warning and "gone.mp3" in warning and "plan" in warning
    v = report["voices"][1]
    assert v["file_sound"] is None and v["expected"] == v["planned"]


@needs_ffmpeg
def test_audit_names_a_video_and_audio_of_different_lengths(tmp_path, tone_reel):
    reel, _ = tone_reel
    longer = tmp_path / "longer.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(reel), "-filter_complex", "[0:a]apad=pad_dur=0.3[a]",
                    "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "96k", str(longer)], check=True)
    done = cli("audit", longer, "--plan", reel.with_suffix(".voice.json"), "--out", tmp_path / "audit.json")
    assert done.returncode == 1
    (problem,) = json.loads((tmp_path / "audit.json").read_text())["problems"]
    assert problem.startswith("the video is") and "more than 0.1 s" in problem


@needs_ffmpeg
def test_audit_passes_a_first_voice_at_the_reel_start(tmp_path):
    a = make_clip(tmp_path / "a.mp4", 3)
    reel, plan = build_reel(tmp_path, [{"file": str(a), "voice": str(make_tone(tmp_path / "one.mp3", 1.5)), "voice_at": 0}])
    assert plan["voices"][0]["start"] == 0
    done = cli("audit", reel, "--out", tmp_path / "audit.json")
    assert done.returncode == 0, done.stderr
    (v,) = json.loads((tmp_path / "audit.json").read_text())["voices"]
    assert v["heard"][0] == pytest.approx(0, abs=0.03)


@needs_ffmpeg
def test_a_loudness_that_cannot_be_measured_is_said_so(tone_reel, monkeypatch):
    reel, _ = tone_reel
    monkeypatch.setattr(check_demo, "loudness", lambda *args, **kw: {"integrated": None, "true_peak": None, "range": None})
    report = check_demo.audit(reel, reel.with_suffix(".voice.json"))
    (problem,) = [p for p in report["problems"] if "loudness" in p]
    assert "could not be measured" in problem and "None" not in problem


@needs_ffmpeg
@pytest.mark.parametrize("case", ["plan voice without end", "missing take", "take that is not a video", "script that is a list"])
def test_wrongly_shaped_input_stops_with_one_line(tmp_path, tone_reel, case):
    if case == "plan voice without end":
        reel, _ = tone_reel
        plan = json.loads(reel.with_suffix(".voice.json").read_text())
        del plan["voices"][1]["end"]
        (tmp_path / "plan.json").write_text(json.dumps(plan))
        done = cli("audit", reel, "--plan", tmp_path / "plan.json", "--out", tmp_path / "audit.json")
        (problem,) = json.loads((tmp_path / "audit.json").read_text())["problems"]
        assert "voice 2" in problem and '"end"' in problem
    else:
        script, take = box_script(tmp_path), tmp_path / "take.webm"
        if case == "take that is not a video":
            take.write_text("not a video")
        if case == "script that is a list":
            script.write_text("[1, 2]")
        done = cli("boxes", script, "--raw", take, "--out", tmp_path / "boxes.json")
        assert len(done.stderr.strip().splitlines()) == 1, done.stderr
        assert ("take.webm" if "take" in case else "a.json") in done.stderr
    assert done.returncode == 1 and "Traceback" not in done.stderr


@needs_ffmpeg
def test_speech_intervals_closes_the_last_sound_whatever_the_silence_asked_for(tmp_path):
    """min_silence above the silence put around the sound must not drop the last sound."""
    tone = make_tone(tmp_path / "t.mp3", 1.5)
    for silence in (0.35, 0.9, 1.2, 2.0):
        (a, b), = check_demo.speech_intervals(tone, min_silence=silence)
        assert a == pytest.approx(0.0, abs=0.05) and b == pytest.approx(1.5, abs=0.05), silence
    bursts = tmp_path / "b.wav"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                    "aevalsrc=0.5*sin(2*PI*440*t)*(between(t\\,0.2\\,1.2)+between(t\\,2.3\\,3.3)):s=24000:d=4", str(bursts)], check=True)
    assert len(check_demo.speech_intervals(bursts, min_silence=0.9)) == 2
    (a, b), = check_demo.speech_intervals(bursts, min_silence=2.0)
    assert a == pytest.approx(0.2, abs=0.05) and b == pytest.approx(3.3, abs=0.05)


@needs_ffmpeg
def test_audit_names_a_voice_file_changed_since_the_reel_was_built(tmp_path, tone_reel):
    """A file of another length than the plan says is held against the plan's times, with a warning, instead of being
    trusted to say where its sound is."""
    reel, _ = tone_reel
    intact = cli("audit", reel, "--plan", reel.with_suffix(".voice.json"), "--out", tmp_path / "ok.json")
    ok = json.loads((tmp_path / "ok.json").read_text())
    assert intact.returncode == 0 and not ok["warnings"]
    # only voice 2's sound is damaged: its last 0.35 s (more than the tolerance) is silenced in the reel
    end = ok["voices"][1]["heard"][1]
    cut = tmp_path / "cut.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(reel), "-af", f"volume=0:enable='between(t,{end - 0.35:.3f},{end + 0.1:.3f})'",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "96k", str(cut)], check=True)
    plan = json.loads(reel.with_suffix(".voice.json").read_text())
    swapped = plan["voices"][1]["end"] - plan["voices"][1]["start"] - 0.35
    plan["voices"][1]["file"] = str(make_tone(tmp_path / "two.mp3", swapped, 660))   # a file that now matches the damaged reel
    (tmp_path / "plan.json").write_text(json.dumps(plan))
    done = cli("audit", cut, "--plan", tmp_path / "plan.json", "--out", tmp_path / "audit.json")
    report = json.loads((tmp_path / "audit.json").read_text())
    assert done.returncode == 1, "the plan's times show the cut the swapped file would hide"
    (problem,) = report["problems"]
    assert problem.startswith("voice 2 (") and "end -" in problem, problem
    (warning,) = [w for w in report["warnings"] if "changed since the reel was built" in w]
    assert "voice 2" in warning and "two.mp3" in warning
    assert report["voices"][1]["file_sound"] is None and report["voices"][1]["expected"] == report["voices"][1]["planned"]


@needs_ffmpeg
def test_audit_passes_a_correct_reel_whose_voice_files_are_much_quieter(tmp_path):
    """The reel lifts its voice track to the loudness target: files 20 dB quieter than usual, with soft edges, have
    their own sound found relative to their own level, so its onset and end are the moments the lifted reel has them."""
    clips = [make_clip(tmp_path / f"c{i}.mp4", 6, c) for i, c in enumerate(["red", "blue"])]
    voices = [make_voice(tmp_path / "one.mp3", 0.2, 3.0, 0.4, 440, -26, fade=1.0),
              make_voice(tmp_path / "two.mp3", 0.5, 2.5, 0.4, 550, -26, fade=1.0)]
    reel, _ = build_reel(tmp_path, [{"file": str(c), "voice": str(v), "voice_at": 0.3} for c, v in zip(clips, voices)])
    done = cli("audit", reel, "--out", tmp_path / "audit.json")
    report = json.loads((tmp_path / "audit.json").read_text())
    assert done.returncode == 0, report["problems"]
    for v in report["voices"]:
        assert abs(v["start_off"]) < 0.2 and abs(v["end_off"]) < 0.2


def test_the_clip_steps_helpers_are_used_by_their_public_names():
    assert not re.findall(r"edit_demo\._\w+", CHECK.read_text())
    assert callable(edit_demo.stream_seconds) and callable(edit_demo.write_json_atomic)


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


@needs_ffmpeg
def test_boxes_ends_a_box_where_its_box_dur_ends(tmp_path):
    """A held box at 2x: without "box_dur" it lasts to the clip's end and its last frame holds the block that appears
    at 6 s of the take; with "box_dur" 1 its times end 1 s of the clip after its start and its last frame is read there."""
    take = make_take(tmp_path / "take.webm", LATE_BLOCK)
    beat = {"at": 2.0, "text": "look", "box": BOX, "box_delay": 0.5, "hold": True}   # the box starts at 1.5 s of the clip
    found = {}
    for name, extra in (("held", {}), ("ended", {"box_dur": 1.0})):
        script = tmp_path / f"{name}.json"
        script.write_text(json.dumps({"speed": 2, "start": 0, "beats": [{**beat, **extra}]}))
        done = cli("boxes", script, "--raw", take, "--out", tmp_path / f"{name}.boxes.json")
        assert done.returncode == 0, done.stderr
        (found[name],) = json.loads((tmp_path / f"{name}.boxes.json").read_text())["boxes"]
    held, ended = found["held"], found["ended"]
    assert held["clip"] == pytest.approx([1.5, 5.0], abs=0.01) and held["raw"] == pytest.approx([3.0, 10.0], abs=0.01)
    assert "moved" in held["flags"]
    assert ended["clip"] == pytest.approx([1.5, 1.5 + 1.0], abs=1e-3) and ended["raw"] == pytest.approx([3.0, 5.0], abs=1e-3)
    assert ended["change"] < 1 and "moved" not in ended["flags"], "the last frame is the box's last moment, before 6 s"


# ---------------------------------------------------------------- sheet

@needs_ffmpeg
def test_sheet_writes_one_row_per_voice_in_one_html_file(tmp_path):
    a, b, c = make_clip(tmp_path / "a.mp4", 3), make_clip(tmp_path / "b.mp4", 3, "blue"), make_clip(tmp_path / "c.mp4", 2, "green")
    reel, plan = build_reel(tmp_path, [
        {"file": str(a), "voice": str(make_voice(tmp_path / "one.mp3", 0.4, 1.0, 0.3, 440)), "voice_at": 0.3},
        {"file": str(b), "voice": str(make_voice(tmp_path / "two.mp3", 0.3, 0.8, 0.4, 550)), "voice_at": 0.5},
        {"file": str(c), "voice": str(make_voice(tmp_path / "three.mp3", 0.5, 0.6, 0.3, 660)), "voice_at": 0.2}])
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
    assert not re.search(r"url\(|<link|<script|<iframe|<object|<embed|srcset=|poster=", page), "no reference to another file"
    links = re.findall(r'\bhref="([^"]*)"', page)
    assert links and all(h.startswith("#") for h in links), "links stay inside the page"
    assert {h[1:] for h in links} <= set(re.findall(r'\bid="([^"]+)"', page)), "every link has its target"
    assert {"#r1", "#r2", "#r3"} <= set(links), "the index at the top links every row"
    assert re.search(r'<a href="#r1"[^>]*>[^<]*1[^<]*</a>[^<]*crosses', page.split('<section id="r1"')[0]), \
        "the list of flagged rows links the flagged row"
    assert re.search(r'<section id="r1" class="[^"]*flagged', page) and '<section id="r2">' in page, "a flagged card stands out"
    assert '<meta charset="utf-8">' in page and "에이전트 게이트웨이에 정책 세 개가 걸려 있습니다." in page
    assert "기록 모드로 걸린 정책 세 줄" in page and "crosses" in page
    pictures = [s for s in sources if s.startswith("data:image/jpeg;base64,")]
    assert len(pictures) == 3 * 3 + 1, "three frames a row and one crop for the one box"
    sounds = [base64.b64decode(s.split(",", 1)[1]) for s in sources if s.startswith("data:audio/")]
    for sound, freq, (lead, tone, trail) in zip(sounds, [440, 550, 660], [(0.4, 1.0, 0.3), (0.3, 0.8, 0.4), (0.5, 0.6, 0.3)], strict=True):
        assert tone_frequency(sound, tmp_path) == pytest.approx(freq, rel=0.05), "each row plays its own voice"
        first, last, length = loud_span(sound, tmp_path)   # the window is the voice's own: its silences at both ends, no more
        assert first == pytest.approx(lead, abs=0.15) and length - last == pytest.approx(trail, abs=0.15)
        assert length == pytest.approx(lead + tone + trail, abs=0.15)
