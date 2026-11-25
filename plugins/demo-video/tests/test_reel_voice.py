"""edit_demo.py reel with voices: the hold schedule, picture segments, one voice track placed by the encoded parts.

Needs ffmpeg/ffprobe on PATH (the schedule tests do not). Tones made with ffmpeg stand in for narration lines.
"""
import importlib.util
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1]
SCRIPTS = PLUGIN / "skills" / "recording-demo-videos" / "scripts"

spec = importlib.util.spec_from_file_location("edit_demo", SCRIPTS / "edit_demo.py")
edit_demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(edit_demo)

needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")
FPS = 30


# ---------------------------------------------------------------- schedule (no ffmpeg)

def test_schedule_holds_the_range_end_and_the_segment_before_the_next_voice():
    segs = [{"seconds": 3.0, "voice_at": 0.3, "voice_seconds": 6.84},                       # a card
            {"seconds": 6.87, "voice_at": 0.7, "voice_seconds": 10.584, "group": "31"},
            {"seconds": 4.608, "group": "31"},                                              # a wait, no voice
            {"seconds": 4.80, "voice_at": 0.3, "voice_seconds": 7.344, "group": "31"},
            {"seconds": 5.078, "voice_at": 0.6, "voice_seconds": 7.848, "group": "31"}]
    plan = edit_demo.schedule(segs, gap=0.6, tail=1.0)
    assert [p["hold"] for p in plan] == pytest.approx([4.14, 0, 0.106, 2.844, 4.37], abs=1e-3)
    assert plan[1]["voice_start"] == pytest.approx(7.84, abs=1e-3)
    assert plan[1]["voice_end"] == pytest.approx(18.424, abs=1e-3)       # runs on over the wait
    assert plan[3]["voice_start"] == pytest.approx(19.024, abs=1e-3)


def test_a_voice_does_not_run_on_into_another_group():
    segs = [{"seconds": 2.0, "voice_at": 0.0, "voice_seconds": 5.0, "group": "a"}, {"seconds": 4.0, "group": "b"}]
    assert edit_demo.schedule(segs)[0]["hold"] == pytest.approx(3.0)


def test_no_voice_means_no_holds():
    assert [p["hold"] for p in edit_demo.schedule([{"seconds": 2.0}, {"seconds": 3.0}])] == [0, 0]


def test_schedule_gives_every_segment_its_start_with_the_holds_counted():
    segs = [{"seconds": 2.0, "voice_at": 0.5, "voice_seconds": 3.0}, {"seconds": 1.0}, {"seconds": 1.0}]
    plan = edit_demo.schedule(segs)
    assert [p["start"] for p in plan] == pytest.approx([0, 3.5, 4.5])
    assert "voice_start" not in plan[1] and plan[0]["voice_end"] == pytest.approx(3.5)


# ---------------------------------------------------------------- media helpers

@pytest.fixture
def private_tmp(tmp_path, monkeypatch):
    """Point tempfile at an empty dir so leftovers and the reel's temp names are visible."""
    d = tmp_path / "tmpdir"
    d.mkdir()
    monkeypatch.setenv("TMPDIR", str(d))
    import tempfile
    tempfile.tempdir = None
    yield d
    tempfile.tempdir = None


def make_clip(path: Path, seconds: float, colour: str = "red", size: str = "320x180") -> Path:
    """A finished clip of one plain colour (H.264 + silent AAC, as the clip step writes); small so the reel is quick."""
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"color=c={colour}:size={size}:rate={FPS}:duration={seconds}",
                    "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000", "-shortest",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", str(path)], check=True)
    return path


def make_two_colour_clip(path: Path, first: str, seconds: float, then: str, more: float, size: str = "320x180") -> Path:
    """A finished clip that is `first` for `seconds`, then `then` for `more` seconds."""
    colour = lambda c, d: ["-f", "lavfi", "-i", f"color=c={c}:size={size}:rate={FPS}:duration={d}"]  # noqa: E731
    subprocess.run(["ffmpeg", "-y", "-v", "error", *colour(first, seconds), *colour(then, more),
                    "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
                    "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[v]", "-map", "[v]", "-map", "2:a", "-shortest",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", str(path)], check=True)
    return path


def make_tone(path: Path, seconds: float, freq: int = 440, volume_db: float = -6.0) -> Path:
    """A narration line stand-in: a mono 24 kHz tone (mp3 like the speech service, or wav), `volume_db` below full scale."""
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"sine=frequency={freq}:sample_rate=24000:duration={seconds}",
                    "-af", f"volume={volume_db}dB", "-ac", "1", str(path)], check=True)
    return path


def make_picture(path: Path, rgb=(0, 160, 0), size=(1920, 1080)) -> Path:
    from PIL import Image
    Image.new("RGB", size, rgb).save(path)
    return path


def pixel(video: Path, at: float, tmp: Path, xy=(160, 90)):
    from PIL import Image
    png = tmp / f"frame-{at:.2f}.png"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{at:.3f}", "-i", str(video), "-frames:v", "1", str(png)], check=True)
    return Image.open(png).convert("RGB").getpixel(xy)


def max_volume(video: Path, start: float, seconds: float) -> float:
    """Loudest sample (dBFS) of the audio in [start, start + seconds); -91 is digital silence."""
    err = subprocess.run(["ffmpeg", "-v", "info", "-hide_banner", "-ss", f"{start:.3f}", "-t", f"{seconds:.3f}", "-i", str(video),
                          "-vn", "-af", "volumedetect", "-f", "null", "-"], capture_output=True, text=True).stderr
    return float(re.search(r"max_volume: (-?[\d.]+|-inf) dB", err).group(1))


def speech_starts(video: Path) -> list[float]:
    """Where sound begins after silence (ffmpeg silencedetect), in reel seconds; the silence closed by the file's end is dropped."""
    err = subprocess.run(["ffmpeg", "-v", "info", "-hide_banner", "-i", str(video), "-vn", "-af", "silencedetect=n=-35dB:d=0.2",
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    end = edit_demo.probe_duration(video)
    return [t for t in (float(t) for t in re.findall(r"silence_end: ([\d.]+)", err)) if t < end - 0.05]


def loudness(video: Path) -> dict:
    """Integrated loudness (LUFS) and true peak (dBTP) of a file's audio, read with ffmpeg's loudnorm filter."""
    err = subprocess.run(["ffmpeg", "-v", "info", "-hide_banner", "-i", str(video), "-vn",
                          "-af", "loudnorm=I=-16:TP=-1.5:LRA=20:print_format=json", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    stats = json.loads(err[err.rindex("{"):err.rindex("}") + 1])
    return {"integrated": float(stats["input_i"]), "true_peak": float(stats["input_tp"])}


def is_red(p):
    return p[0] > 200 and p[1] < 60 and p[2] < 60


def build(tmp_path: Path, manifest: dict, name: str = "reel") -> tuple[Path, dict]:
    spec_path = tmp_path / f"{name}.json"
    spec_path.write_text(json.dumps(manifest))
    out = tmp_path / f"{name}.mp4"
    edit_demo.build_reel(spec_path, out)
    return out, json.loads(out.with_suffix(".voice.json").read_text())


# ---------------------------------------------------------------- the old path

# the commands of the 1.3.0 reel step for the manifest below, recorded from that code (paths replaced by <WORK> and <TMP>)
OLD_COMMANDS = [
    ["ffmpeg", "-y", "-v", "error", "-ss", "0.000", "-to", "2.000", "-i", "<WORK>/a.mp4", "-vf", "fade=t=in:st=0:d=0.4",
     "-af", "afade=t=in:st=0:d=0.4", "-c:v", "libx264", "-preset", "slow", "-crf", "19", "-c:a", "aac", "-b:a", "96k",
     "<TMP>/reel-X/part00.mp4"],
    ["ffmpeg", "-y", "-v", "error", "-ss", "0.500", "-to", "2.500", "-i", "<WORK>/b.mp4", "-vf", "fade=t=in:st=0:d=0.4,fade=t=out:st=1.60:d=0.4",
     "-af", "afade=t=in:st=0:d=0.4,afade=t=out:st=1.60:d=0.4", "-c:v", "libx264", "-preset", "slow", "-crf", "19", "-c:a", "aac",
     "-b:a", "96k", "<TMP>/reel-X/part01.mp4"],
    ["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", "<TMP>/reel-X/list.txt", "-c", "copy", "<TMP>/reel-X/joined.mp4"],
    ["ffmpeg", "-y", "-v", "error", "-i", "<TMP>/reel-X/joined.mp4", "-c:v", "libx264", "-preset", "medium", "-crf", "23",
     "-maxrate", "3M", "-bufsize", "3M", "-profile:v", "high", "-level", "4.1", "-refs", "4", "-g", "60", "-keyint_min", "30",
     "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", "<WORK>/reel.mp4"],
]


@needs_ffmpeg
def test_reel_without_voice_runs_the_same_steps_as_before(tmp_path, private_tmp, monkeypatch):
    a, b = make_clip(tmp_path / "a.mp4", 3), make_clip(tmp_path / "b.mp4", 3, "blue")
    seen, real = [], edit_demo.run
    monkeypatch.setattr(edit_demo, "run", lambda cmd: (seen.append(list(cmd)), real(cmd))[1])
    spec_path = tmp_path / "reel.json"
    spec_path.write_text(json.dumps({"fade": 0.4, "segments": [
        {"file": str(a), "start": 0, "end": 2, "fade_out": 0, "group": "x"},   # a group alone does not make a voiced reel
        {"file": str(b), "start": 0.5, "end": 2.5},
    ]}))
    edit_demo.build_reel(spec_path, tmp_path / "reel.mp4")
    text = json.dumps(seen).replace(str(private_tmp), "<TMP>").replace(str(tmp_path), "<WORK>")
    assert json.loads(re.sub(r"reel-[A-Za-z0-9_]+", "reel-X", text)) == OLD_COMMANDS
    assert not (tmp_path / "reel.voice.json").exists()


# ---------------------------------------------------------------- holds and the voice track

@needs_ffmpeg
def test_reel_holds_the_last_frame_and_carries_the_voice(tmp_path, private_tmp):
    """The first clip turns green after the window's end and runs on longer than the hold, so a reel that played on
    would have the same length: only a repeated last frame shows red inside the hold."""
    a = make_two_colour_clip(tmp_path / "a.mp4", "red", 2, "lime", 3)
    b = make_clip(tmp_path / "b.mp4", 3, "blue")
    assert not is_red(pixel(a, 2.5, tmp_path)), "the source plays on in another colour"
    voice = make_tone(tmp_path / "line.mp3", 3.0)
    out, plan = build(tmp_path, {"segments": [
        {"file": str(a), "start": 0, "end": 2, "voice": str(voice), "voice_at": 0.8},
        {"file": str(b), "start": 0, "end": 2},
    ]})
    expected = edit_demo.schedule([{"seconds": 2.0, "voice_at": 0.8, "voice_seconds": edit_demo.probe_duration(voice)},
                                   {"seconds": 2.0}])
    assert expected[0]["hold"] > 1.5
    assert edit_demo.probe_duration(out) == pytest.approx(sum(2.0 + p["hold"] for p in expected), abs=0.1)
    assert is_red(pixel(out, 2.0 + expected[0]["hold"] / 2, tmp_path)), "the hold shows the first clip's last frame"
    assert list(private_tmp.iterdir()) == [], "reel must delete its part files"
    v = plan["voices"][0]
    assert max_volume(out, v["start"] + 0.05, v["end"] - v["start"] - 0.1) > -30, "the voice plays as planned"
    assert max_volume(out, 0, v["start"] - 0.3) < -60, "silence before the voice"


@needs_ffmpeg
def test_reel_places_voices_by_the_measured_part_lengths(tmp_path, private_tmp):
    """Windows of 1.004 / 1.204 / 1.404 s encode to whole frames (31, 37, 43): every part is longer than its nominal
    length, so a plan from the nominal lengths would drift; the plan and the sound follow the encoded parts."""
    segs, nominal = [], []
    for i, (colour, end) in enumerate([("red", 1.004), ("green", 1.204), ("blue", 1.404)]):
        clip = make_clip(tmp_path / f"c{i}.mp4", 2, colour)
        tone = make_tone(tmp_path / f"v{i}.wav", 0.4, freq=440 + 110 * i)
        segs.append({"file": str(clip), "start": 0, "end": end, "voice": str(tone), "voice_at": 0.3})
        nominal.append({"seconds": end, "voice_at": 0.3, "voice_seconds": edit_demo.probe_duration(tone)})
    out, plan = build(tmp_path, {"fade": 0, "segments": segs})
    assert [s["name"] for s in plan["segments"]] == ["c0", "c1", "c2"]
    for s in plan["segments"]:   # an mp4's length is whole frames rounded up to the millisecond (0.03 frame)
        assert s["seconds"] * FPS == pytest.approx(round(s["seconds"] * FPS), abs=0.05), "a measured length is whole frames"
    assert [s["start"] for s in plan["segments"]] == pytest.approx([0, plan["segments"][0]["seconds"],
                                                                     plan["segments"][0]["seconds"] + plan["segments"][1]["seconds"]],
                                                                    abs=1e-3)
    by_rule = edit_demo.schedule(nominal)
    detected = speech_starts(out)
    assert len(detected) == 3
    for v, d in zip(plan["voices"], detected):
        assert d == pytest.approx(v["start"], abs=0.1)
    for i in (1, 2):
        assert plan["voices"][i]["start"] > by_rule[i]["voice_start"] + 0.02, "the measured start, later than the nominal one"
        assert abs(detected[i] - plan["voices"][i]["start"]) < abs(detected[i] - by_rule[i]["voice_start"])


@needs_ffmpeg
def test_a_picture_segment_is_drawn_as_long_as_its_voice(tmp_path, private_tmp):
    card = make_picture(tmp_path / "card.png", (0, 160, 0))
    clip = make_clip(tmp_path / "b.mp4", 3, "blue")
    voice = make_tone(tmp_path / "card.mp3", 3.0)
    out, plan = build(tmp_path, {"segments": [
        {"image": str(card), "seconds": 1.0, "voice": str(voice), "voice_at": 0.2},
        {"file": str(clip), "start": 0, "end": 2},
    ]})
    p = pixel(out, 2.0, tmp_path)                       # 1 s after the picture's nominal end
    assert p[1] > 120 and p[0] < 60 and p[2] < 60, f"the picture, not black: {p}"
    assert plan["segments"][0]["name"] == "card" and plan["segments"][0]["hold"] > 2.0
    assert "window" not in plan["segments"][0] and plan["segments"][1]["window"] == [0, 2], "a picture has no window"
    p = pixel(out, plan["segments"][1]["start"] + 1.0, tmp_path)
    assert p[2] > 200 and p[0] < 60, "the clip follows the picture"


@needs_ffmpeg
@pytest.mark.parametrize("target", [None, -23])
def test_reel_brings_the_voices_to_the_loudness_target(tmp_path, private_tmp, target):
    clip = make_clip(tmp_path / "a.mp4", 3)
    voice = make_tone(tmp_path / "line.mp3", 2.0, volume_db=-20)
    manifest = {"segments": [{"file": str(clip), "start": 0, "end": 3, "voice": str(voice), "voice_at": 0.5}]}
    if target is not None:
        manifest["loudness"] = target
    out, plan = build(tmp_path, manifest)
    level = loudness(out)
    assert level["integrated"] == pytest.approx(-16 if target is None else target, abs=1.0)
    assert level["true_peak"] <= -1.0
    assert not [w for w in plan["warnings"] if "LUFS" in w], "one gain reaches the target: nothing to say"


def make_peaky_tone(path: Path, seconds: float, low: float, high: float, at: float = 1.0) -> Path:
    """A tone of amplitude `low` with 10 ms at amplitude `high` from `at` s: its true peak lies far above its loudness, as
    speech's does."""
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                    f"aevalsrc=({low}+between(t\\,{at}\\,{at + 0.01})*({high}-{low}))*sin(2*PI*440*t):s=24000:d={seconds}",
                    str(path)], check=True)
    return path


@needs_ffmpeg
@pytest.mark.parametrize("seconds, peak", [(5.0, 0.22), (2.5, 0.20)])   # each about 1 LU short (-16.9 and -17.2 LUFS)
def test_reel_takes_the_largest_gain_the_true_peak_allows_when_it_lands_within_the_tolerance(tmp_path, private_tmp,
                                                                                          seconds, peak):
    """A line whose peak leaves too little room for -16 LUFS by about 1 dB (real speech left 6.2 dB of room where 6.9 dB
    were needed): one gain up to the true-peak ceiling, the reel about 1 LU under the target, the levels of the voices
    against each other kept, and the plan says what was reached. A short track (2.5 s) is no different."""
    a, b = make_clip(tmp_path / "a.mp4", seconds + 1, "red"), make_clip(tmp_path / "b.mp4", 3, "blue")
    peaky = make_peaky_tone(tmp_path / "peaky.wav", seconds, 0.05, peak)
    soft = make_peaky_tone(tmp_path / "soft.wav", 2.0, 0.025, 0.025)               # the same tone 6 dB lower, no peak
    out, plan = build(tmp_path, {"segments": [
        {"file": str(a), "start": 0, "end": seconds + 1, "voice": str(peaky), "voice_at": 0.3},
        {"file": str(b), "start": 0, "end": 3, "voice": str(soft), "voice_at": 0.3}]})
    (note,) = [w for w in plan["warnings"] if "LUFS" in w]
    reached = float(re.search(r"brought to (-[0-9.]+) LUFS", note).group(1))
    assert -16 - 1.5 <= reached <= -16 - 0.3, note
    assert "one gain" in note and "true peak" in note and "compress" not in note, note
    level = loudness(out)
    assert level["integrated"] == pytest.approx(reached, abs=0.3)
    assert level["true_peak"] <= edit_demo.VOICE_TRUE_PEAK + 0.3
    v0, v1 = plan["voices"]
    calm = (1.2, seconds - 1.3) if seconds > 3 else (0.0, 0.9)    # the first voice's tone away from its peak
    gap = max_volume(out, v0["start"] + calm[0], calm[1]) - max_volume(out, v1["start"] + 0.2, 1.5)
    assert gap == pytest.approx(6.0, abs=0.5), "one gain: the 6 dB between the two voices stay"


@needs_ffmpeg
def test_reel_warns_when_one_gain_cannot_reach_the_loudness_target(tmp_path, private_tmp):
    """A quiet line with one loud click: the gain to -16 LUFS would push the click past -1.5 dBTP, so loudnorm
    compresses. The track is 5.5 s long because loudnorm compresses over a 3 s window and misses badly on a shorter one."""
    clip = make_clip(tmp_path / "a.mp4", 6)
    voice = tmp_path / "click.wav"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                    "aevalsrc=0.03*sin(2*PI*440*t)+between(t\\,2\\,2.01)*0.9*sin(2*PI*440*t):s=24000:d=5", str(voice)], check=True)
    out, plan = build(tmp_path, {"segments": [{"file": str(clip), "start": 0, "end": 6, "voice": str(voice), "voice_at": 0.5}]})
    assert any("cannot reach -16 LUFS by one gain" in w and "compresses" in w for w in plan["warnings"]), plan["warnings"]
    level = loudness(out)
    # the click reaches the ceiling, so the ceiling is pinned here: loudnorm keeps -1.5 dBTP, and the AAC encode after
    # it may add a few tenths of a dB, hence the 0.3 dB margin
    assert level["true_peak"] <= edit_demo.VOICE_TRUE_PEAK + 0.3
    assert level["integrated"] == pytest.approx(-16, abs=1.5)


@needs_ffmpeg
def test_reel_keeps_the_voices_levels_against_each_other(tmp_path, private_tmp):
    a, b = make_clip(tmp_path / "a.mp4", 2, "red"), make_clip(tmp_path / "b.mp4", 2, "blue")
    loud, soft = make_tone(tmp_path / "loud.wav", 1.0, volume_db=-6), make_tone(tmp_path / "soft.wav", 1.0, volume_db=-12)
    out, plan = build(tmp_path, {"segments": [
        {"file": str(a), "start": 0, "end": 2, "voice": str(loud), "voice_at": 0.3},
        {"file": str(b), "start": 0, "end": 2, "voice": str(soft), "voice_at": 0.3},
    ]})
    v0, v1 = plan["voices"]
    level0 = max_volume(out, v0["start"] + 0.1, 0.8)
    level1 = max_volume(out, v1["start"] + 0.1, 0.8)
    assert level0 - level1 == pytest.approx(6.0, abs=0.7)


@needs_ffmpeg
def test_reel_takes_the_gap_and_the_tail_from_the_manifest(tmp_path, private_tmp):
    a, b = make_clip(tmp_path / "a.mp4", 2, "red"), make_clip(tmp_path / "b.mp4", 2, "blue")
    one, two = make_tone(tmp_path / "one.wav", 1.5), make_tone(tmp_path / "two.wav", 1.0)
    out, plan = build(tmp_path, {"voice_gap": 1.5, "voice_tail": 2.0, "segments": [
        {"file": str(a), "start": 0, "end": 2, "voice": str(one), "voice_at": 0.3},
        {"file": str(b), "start": 0, "end": 2, "voice": str(two), "voice_at": 0.1},
    ]})
    v0, v1 = plan["voices"]
    assert v1["start"] - v0["end"] == pytest.approx(1.5, abs=0.05)
    assert edit_demo.probe_duration(out) - v1["end"] == pytest.approx(2.0, abs=0.05)


@needs_ffmpeg
def test_reel_writes_its_plan_and_warns(tmp_path, private_tmp, capsys):
    a, b = make_clip(tmp_path / "a.mp4", 3, "red"), make_clip(tmp_path / "b.mp4", 3, "blue")
    long_voice = make_tone(tmp_path / "long.mp3", 15.0)
    out, plan = build(tmp_path, {"segments": [
        {"file": str(a), "start": 0, "end": 2, "voice": str(long_voice), "voice_at": 0.5},
        {"file": str(b), "start": 0, "end": 2},
    ]})
    assert [(s["name"], s["hold"] > 6) for s in plan["segments"]] == [("a", True), ("b", False)]
    for s in plan["segments"]:
        assert set(s) == {"name", "start", "seconds", "hold", "window"}
    assert [s["window"] for s in plan["segments"]] == [[0, 2], [0, 2]], "the seconds of its clip each segment shows"
    assert plan["segments"][1]["start"] == pytest.approx(plan["segments"][0]["seconds"])
    assert sum(s["seconds"] for s in plan["segments"]) == pytest.approx(edit_demo.probe_duration(out), abs=0.05)
    (v,) = plan["voices"]
    assert set(v) == {"segment", "name", "file", "start", "end"}
    assert (v["segment"], v["name"], v["file"]) == (0, "a", str(long_voice.resolve()))
    assert v["start"] == pytest.approx(0.5, abs=0.01) and v["end"] - v["start"] == pytest.approx(15.0, abs=0.1)
    text = "\n".join(plan["warnings"])
    assert len(plan["warnings"]) == 3, text
    assert re.search(r"segment 1 \(a\).*hold.*over 6 s", text), "a hold over 6 s, naming its segment"
    assert re.search(r"holds.*over 30 %", text), "the holds' share of the reel"
    assert re.search(r"segment 1 \(a\).*voice.*over 14 s", text), "a voice over 14 s, naming its segment"
    summary = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert summary["out"] == str(out) and summary["voices"] == 1 and summary["plan"] == str(out.with_suffix(".voice.json"))


# ---------------------------------------------------------------- refusals (before anything is encoded)

def _refused(tmp_path, monkeypatch, manifest_text: str, copy: bool = False) -> str:
    seen = []
    monkeypatch.setattr(edit_demo, "run", lambda cmd: seen.append(cmd))
    spec_path = tmp_path / "reel.json"
    spec_path.write_text(manifest_text)
    with pytest.raises(SystemExit) as stop:
        edit_demo.build_reel(spec_path, tmp_path / "reel.mp4", copy=copy)
    assert seen == [], "nothing is encoded"
    assert not (tmp_path / "reel.mp4").exists()
    return str(stop.value)


@needs_ffmpeg
@pytest.mark.parametrize("case", ["voice twice", "voice list", "voice missing"])
def test_two_voices_on_one_segment_or_a_voice_without_its_file_stop_the_reel(tmp_path, monkeypatch, case):
    clip = make_clip(tmp_path / "a.mp4", 2)
    one, two = make_tone(tmp_path / "one.mp3", 0.5), make_tone(tmp_path / "two.mp3", 0.5)
    segment = {
        "voice twice": f'{{"file": "{clip}", "voice": "{one}", "voice": "{two}"}}',
        "voice list": json.dumps({"file": str(clip), "voice": [str(one), str(two)]}),
        "voice missing": json.dumps({"file": str(clip), "voice": str(tmp_path / "gone.mp3")}),
    }[case]
    message = _refused(tmp_path, monkeypatch, f'{{"segments": [{segment}]}}')
    assert ("gone.mp3" if case == "voice missing" else "one voice") in message
    assert "segment 1" in message


@needs_ffmpeg
@pytest.mark.parametrize("segment, words", [
    ({"voice_at": -0.1}, "voice_at"),
    ({"voice_at": 2.5}, "voice_at"),
    ({"image": "IMG"}, "not both"),
    ({"file": None}, "neither"),
    ({"file": None, "image": "IMG"}, "seconds"),
])
def test_a_bad_segment_stops_the_reel_before_anything_is_encoded(tmp_path, monkeypatch, segment, words):
    clip = make_clip(tmp_path / "a.mp4", 2)
    picture = make_picture(tmp_path / "card.png")
    voice = make_tone(tmp_path / "one.mp3", 0.5)
    seg = {"file": str(clip), "voice": str(voice)}
    for k, v in segment.items():
        if v is None:
            seg.pop(k)
        else:
            seg[k] = str(picture) if v == "IMG" else v
    message = _refused(tmp_path, monkeypatch, json.dumps({"segments": [seg]}))
    assert words in message and "segment 1" in message


@needs_ffmpeg
@pytest.mark.parametrize("window, words", [
    ({"start": 0, "end": 3}, '"end" 3 s lies beyond the clip'),
    ({"start": 1, "end": 1}, '"end" 1 s is not after "start" 1 s'),
    ({"start": 1.5, "end": 0.5}, '"end" 0.5 s is not after "start" 1.5 s'),
    ({"start": 2.5}, '"start" 2.5 s lies beyond the clip'),
])
def test_a_window_that_leaves_its_clip_or_is_empty_stops_the_reel(tmp_path, monkeypatch, window, words):
    clip = make_clip(tmp_path / "a.mp4", 2)
    voice = make_tone(tmp_path / "one.mp3", 0.5)
    message = _refused(tmp_path, monkeypatch, json.dumps({"segments": [{"file": str(clip), "voice": str(voice), **window}]}))
    assert words in message and "segment 1 (a.mp4)" in message


@needs_ffmpeg
def test_an_end_past_the_clip_cannot_make_two_voices_overlap(tmp_path, monkeypatch):
    """A 2 s clip with "end": 3 and a 2.5 s voice, then a voiced clip: planned on 3 s but encoded as 2 s, the two voices
    would overlap by 0.4 s. The window is refused before anything is encoded."""
    a, b = make_clip(tmp_path / "a.mp4", 2), make_clip(tmp_path / "b.mp4", 2, "blue")
    long_voice, short_voice = make_tone(tmp_path / "long.wav", 2.5), make_tone(tmp_path / "short.wav", 0.5)
    message = _refused(tmp_path, monkeypatch, json.dumps({"segments": [
        {"file": str(a), "start": 0, "end": 3, "voice": str(long_voice), "voice_at": 0},
        {"file": str(b), "voice": str(short_voice), "voice_at": 0.1}]}))
    assert 'segment 1 (a.mp4): "end" 3 s lies beyond the clip' in message


@needs_ffmpeg
def test_a_window_is_measured_inside_the_probed_clip(tmp_path):
    """The schedule gets the window inside the clip's video: an end within one frame past it is the clip's end, and a
    missing end is the video's length (the file's length is a few ms longer: the audio's last packet)."""
    clip = make_clip(tmp_path / "a.mp4", 2)
    assert edit_demo.probe_duration(clip) > 2.0
    segs, _ = edit_demo._narrated_segments({"segments": [{"file": str(clip), "start": 0.5, "end": 2.02},
                                                         {"file": str(clip)}]})
    assert [s["seconds"] for s in segs] == pytest.approx([1.5, 2.0], abs=1e-3)


def _without_holds(monkeypatch):
    """A schedule with its holds taken away: the plan then lets voices overlap, which only the second net can catch."""
    real = edit_demo.schedule
    monkeypatch.setattr(edit_demo, "schedule", lambda segs, gap, tail: [{**p, "hold": 0.0} for p in real(segs, gap=gap, tail=tail)])


@needs_ffmpeg
def test_reel_stops_when_two_measured_voices_come_closer_than_the_gap(tmp_path, private_tmp, monkeypatch):
    _without_holds(monkeypatch)
    a, b = make_clip(tmp_path / "a.mp4", 2), make_clip(tmp_path / "b.mp4", 2, "blue")
    one, two = make_tone(tmp_path / "one.wav", 2.5), make_tone(tmp_path / "two.wav", 0.5)
    spec_path, out = tmp_path / "reel.json", tmp_path / "reel.mp4"
    spec_path.write_text(json.dumps({"segments": [{"file": str(a), "voice": str(one), "voice_at": 0.3},
                                                  {"file": str(b), "voice": str(two), "voice_at": 0.1}]}))
    with pytest.raises(SystemExit) as stop:
        edit_demo.build_reel(spec_path, out)
    assert "segment 1 (a)" in str(stop.value) and "segment 2 (b)" in str(stop.value) and "gap" in str(stop.value)
    assert not out.exists() and not out.with_suffix(".voice.json").exists()
    assert list(private_tmp.iterdir()) == []


@needs_ffmpeg
def test_reel_stops_when_the_last_voice_would_end_after_the_reel(tmp_path, private_tmp, monkeypatch):
    _without_holds(monkeypatch)
    clip, voice = make_clip(tmp_path / "a.mp4", 2), make_tone(tmp_path / "one.wav", 3.0)
    spec_path, out = tmp_path / "reel.json", tmp_path / "reel.mp4"
    spec_path.write_text(json.dumps({"segments": [{"file": str(clip), "voice": str(voice), "voice_at": 0.3}]}))
    with pytest.raises(SystemExit) as stop:
        edit_demo.build_reel(spec_path, out)
    assert "segment 1 (a)" in str(stop.value) and "after the reel's end" in str(stop.value)
    assert not out.exists() and not out.with_suffix(".voice.json").exists()


def _voices(*spans):
    """Voices for _voices_off_plan: (segment, start, end) each."""
    return [{"segment": s, "name": f"v{s}", "start": a, "end": b} for s, a, b in spans]


@pytest.mark.parametrize("voices, lengths, gap", [
    (_voices((0, 0.0, 1.05), (21, 1.0, 1.5)), [0.05] * 20 + [1.0, 2.0], 0.6),   # 21 parts between them: no allowance left
    (_voices((0, 0.0, 1.02), (1, 1.0, 1.5)), [1.0, 2.0], 0.0),                  # no gap asked, but still an overlap
])
def test_two_voices_that_overlap_always_stop_the_reel(voices, lengths, gap):
    problem = edit_demo._voices_off_plan(voices, lengths, gap, 0.0)
    assert problem and "less than the gap" in problem and "segment 1 (v0)" in problem


def test_the_gap_check_still_allows_one_frame_per_part():
    """A part can come out up to one frame shorter than its window, so two voices half a frame closer than the gap pass."""
    voices = _voices((0, 0.3, 1.5), (1, 1.5 + 0.6 - 0.5 / FPS, 2.5))
    assert edit_demo._voices_off_plan(voices, [2.0, 3.5], 0.6, 1.0) is None


@pytest.mark.parametrize("voices, lengths, tail, words", [
    (_voices((0, 0.3, 2.5)), [0.1] * 20, 1.0, "after the reel's end"),       # 0.5 s past a 20-part reel, on the first part
    (_voices((0, 0.0, 1.01)), [1.0], 0.0, "after the reel's end"),           # no tail asked: 0.01 s past the end
    (_voices((0, 0.3, 1.5)), [2.0], 1.0, "less than the tail"),             # 0.5 s left of a 1 s tail
])
def test_a_last_voice_past_the_end_or_into_the_tail_stops_the_reel(voices, lengths, tail, words):
    problem = edit_demo._voices_off_plan(voices, lengths, 0.6, tail)
    assert problem and words in problem and "segment 1 (v0)" in problem


def test_the_tail_check_allows_one_frame_per_part():
    assert edit_demo._voices_off_plan(_voices((0, 0.3, 1.5)), [2.5 - 0.5 / FPS], 0.6, 1.0) is None


@needs_ffmpeg
@pytest.mark.parametrize("case", ["gap", "tail"])
def test_a_window_that_encodes_a_frame_short_cannot_make_voices_overlap_or_outrun_the_reel(tmp_path, private_tmp, case):
    """The window 1.99-3.0 s of a 3 s clip holds 30 frames and encodes to 1.000 s, not 1.01 s. With "voice_gap" and
    "voice_tail" 0 the schedule plans no hold, so a 1.01 s voice on it would overlap the next voice (or run past the
    reel's end) by 0.01 s."""
    a, b = make_clip(tmp_path / "a.mp4", 3), make_clip(tmp_path / "b.mp4", 2, "blue")
    long_voice, short_voice = make_tone(tmp_path / "long.wav", 1.01), make_tone(tmp_path / "short.wav", 0.5)
    segments = [{"file": str(a), "start": 1.99, "voice": str(long_voice), "voice_at": 0}]
    if case == "gap":
        segments.append({"file": str(b), "voice": str(short_voice), "voice_at": 0})
    spec_path, out = tmp_path / "reel.json", tmp_path / "reel.mp4"
    spec_path.write_text(json.dumps({"voice_gap": 0, "voice_tail": 0, "fade": 0, "segments": segments}))
    with pytest.raises(SystemExit) as stop:
        edit_demo.build_reel(spec_path, out)
    assert ("less than the gap" if case == "gap" else "after the reel's end") in str(stop.value)
    assert not out.exists() and not out.with_suffix(".voice.json").exists()


@needs_ffmpeg
@pytest.mark.parametrize("window", [{"start": 1.99}, {"start": 1.0, "end": 1.02}])
def test_a_window_shorter_than_one_frame_stops_the_reel(tmp_path, monkeypatch, window):
    clip = make_clip(tmp_path / "a.mp4", 2)
    voice = make_tone(tmp_path / "one.mp3", 0.5)
    message = _refused(tmp_path, monkeypatch, json.dumps({"segments": [{"file": str(clip), "voice": str(voice), **window}]}))
    assert "segment 1 (a.mp4)" in message and "shorter than one frame" in message


@needs_ffmpeg
@pytest.mark.parametrize("bad", ["file", "image", "voice"])
def test_a_file_that_is_not_media_stops_the_reel_with_one_line(tmp_path, monkeypatch, bad):
    clip, voice = make_clip(tmp_path / "a.mp4", 2), make_tone(tmp_path / "one.mp3", 0.5)
    junk = tmp_path / ("junk." + {"file": "mp4", "image": "png", "voice": "mp3"}[bad])
    junk.write_text("not media")
    seg = {"file": str(clip), "voice": str(voice)}
    if bad == "image":
        seg = {"image": str(junk), "seconds": 1, "voice": str(voice)}
    else:
        seg[bad] = str(junk)
    message = _refused(tmp_path, monkeypatch, json.dumps({"segments": [seg]}))
    assert "segment 1" in message and "cannot read" in message and junk.name in message


@needs_ffmpeg
def test_a_failed_loudness_measurement_stops_with_one_line(tmp_path):
    junk = tmp_path / "voices.wav"
    junk.write_text("not audio")
    with pytest.raises(SystemExit, match="measuring the loudness of the voice track failed"):
        edit_demo._loudness_filter(junk, -16)


@needs_ffmpeg
def test_a_voiced_reel_refuses_the_stream_copy(tmp_path, monkeypatch):
    clip, voice = make_clip(tmp_path / "a.mp4", 2), make_tone(tmp_path / "one.mp3", 0.5)
    message = _refused(tmp_path, monkeypatch, json.dumps({"segments": [{"file": str(clip), "voice": str(voice)}]}), copy=True)
    assert "--copy" in message
