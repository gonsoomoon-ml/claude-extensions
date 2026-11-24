"""edit_demo.py: anchor resolution, speed, reel fades, temp-dir cleanup. Needs ffmpeg/ffprobe on PATH."""
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1]
SCRIPTS = PLUGIN / "skills" / "recording-demo-videos" / "scripts"

spec = importlib.util.spec_from_file_location("edit_demo", SCRIPTS / "edit_demo.py")
edit_demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(edit_demo)

needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")

LOG = [
    {"t": 1.0, "kind": "shot", "key": "hero", "label": "Page overview"},
    {"t": 3.0, "kind": "shot", "key": "stage", "label": "Stage"},
    {"t": 4.5, "kind": "play"},
    {"t": 6.0, "kind": "caption", "text": "System 2에 복구를 요청"},
    {"t": 8.0, "kind": "shot", "key": "stage", "label": "Stage again"},
]


# ---------------------------------------------------------------- script_time

def test_anchor_forms_resolve_to_camlog_seconds():
    assert edit_demo.script_time(41.0, LOG) == 41.0
    assert edit_demo.script_time("shot:stage", LOG) == 3.0
    assert edit_demo.script_time("shot:stage#2", LOG) == 8.0
    assert edit_demo.script_time("caption:System 2", LOG) == 6.0
    assert edit_demo.script_time("note:play", LOG) == 4.5
    assert edit_demo.script_time("play", LOG) == 4.5


def test_missing_anchor_aborts_with_its_name():
    with pytest.raises(SystemExit, match="shot:table"):
        edit_demo.script_time("shot:table", LOG)


# ---------------------------------------------------------------- fixtures

def make_video(path: Path, seconds: float, size: str = "1920x1080") -> Path:
    """Test pattern. .webm = a raw Playwright take (VP8, no audio); .mp4 = a finished clip (H.264 + silent AAC)."""
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"testsrc=size={size}:rate=30:duration={seconds}"]
    if path.suffix == ".webm":
        cmd += ["-c:v", "libvpx", "-pix_fmt", "yuv420p"]
    else:
        cmd += ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000", "-shortest",
                "-pix_fmt", "yuv420p", "-c:a", "aac"]
    subprocess.run(cmd + [str(path)], check=True)
    return path


@pytest.fixture
def raw(tmp_path):
    """A 10 s webm with a camlog beside it, like record_demo.mjs writes (long enough for beats after the 4.2 s title)."""
    video = make_video(tmp_path / "take.webm", 10)
    (tmp_path / "take.camlog.json").write_text(json.dumps({"log": [
        {"t": 0.5, "kind": "shot", "key": "hero", "label": "wide"},
        {"t": 2.0, "kind": "run_clicked"},
        {"t": 4.0, "kind": "shot", "key": "table", "label": "results"},
    ]}))
    return video


@pytest.fixture
def private_tmp(tmp_path, monkeypatch):
    """Point tempfile at an empty dir so leftovers are visible."""
    d = tmp_path / "tmpdir"
    d.mkdir()
    monkeypatch.setenv("TMPDIR", str(d))
    import tempfile
    tempfile.tempdir = None
    yield d
    tempfile.tempdir = None


# ---------------------------------------------------------------- clip

@needs_ffmpeg
def test_clip_removes_its_temp_dir_and_reports_caption_count(raw, tmp_path, private_tmp, capsys):
    script = tmp_path / "story.json"
    script.write_text(json.dumps({"title": "T", "subtitle": "S", "beats": [
        {"at": "shot:hero", "text": "first"},
        {"at": "run_clicked", "text": "second", "style": "insight"},
        {"at": "shot:table", "text": "third", "pos": "top"},
    ]}))
    out = tmp_path / "clips" / "take.mp4"
    edit_demo.build_clip(raw, out, None, None, None, None, True, None, script)
    assert out.exists()
    assert list(private_tmp.iterdir()) == [], "clip must delete its drawtext temp dir"
    report = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert report["captions"] == 3, "count beats, not filter-graph entries"


@needs_ffmpeg
def test_clip_default_tempo_is_1_25x(raw, tmp_path, private_tmp):
    """1.2.0: every clip plays at 1.25x unless the script says otherwise; 10 s of raw footage becomes 8 s."""
    script = tmp_path / "story.json"
    script.write_text(json.dumps({"start": 0, "beats": [{"at": 4.0, "text": "late"}]}))
    out = tmp_path / "default.mp4"
    edit_demo.build_clip(raw, out, None, None, None, None, True, None, script)
    assert abs(edit_demo.probe_duration(out) - 8.0) < 0.3
    assert edit_demo.DEFAULT_SPEED == 1.25


@needs_ffmpeg
def test_clip_speed_shortens_the_output_and_keeps_raw_second_anchors(raw, tmp_path, private_tmp):
    script = tmp_path / "story.json"
    script.write_text(json.dumps({"speed": 2, "start": 0, "beats": [{"at": 4.0, "text": "late"}]}))
    out = tmp_path / "fast.mp4"
    edit_demo.build_clip(raw, out, None, None, None, None, True, None, script)
    assert abs(edit_demo.probe_duration(out) - 5.0) < 0.3


@needs_ffmpeg
def test_clip_without_script_uses_shot_labels_and_default_clips_dir(raw, tmp_path, private_tmp, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["edit_demo.py", "clip", str(raw), "--title", "T"])
    edit_demo.main()
    assert (tmp_path / "clips" / "take.mp4").exists(), "default output is ./clips/<stem>.mp4, not a project path"


# ---------------------------------------------------------------- reel

@needs_ffmpeg
def test_reel_honours_per_segment_fades_and_cleans_up(tmp_path, private_tmp):
    a = make_video(tmp_path / "a.mp4", 3)
    b = make_video(tmp_path / "b.mp4", 3)
    spec_path = tmp_path / "reel.json"
    spec_path.write_text(json.dumps({"fade": 0.4, "segments": [
        {"file": str(a), "start": 0, "end": 2, "fade_out": 0},
        {"file": str(b), "start": 1, "end": 3, "fade_in": 0},
    ]}))
    out = tmp_path / "reel.mp4"
    edit_demo.build_reel(spec_path, out)
    assert abs(edit_demo.probe_duration(out) - 4.0) < 0.3
    assert list(private_tmp.iterdir()) == [], "reel must delete its part files"


@needs_ffmpeg
def test_reel_refuses_mixed_resolutions_before_encoding(tmp_path, private_tmp):
    a = make_video(tmp_path / "a.mp4", 2)
    b = make_video(tmp_path / "b.mp4", 2, size="1080x1080")
    spec_path = tmp_path / "reel.json"
    spec_path.write_text(json.dumps({"segments": [{"file": str(a)}, {"file": str(b)}]}))
    with pytest.raises(SystemExit, match="1080x1080"):
        edit_demo.build_reel(spec_path, tmp_path / "reel.mp4")


# ---------------------------------------------------------------- highlight boxes and held captions

def test_box_forms_resolve_to_frame_rectangles():
    """Numbers are drawn as given; a camlog rect is grown by border + 4 px (12 px) and clipped to the frame."""
    log = LOG + [{"t": 9.0, "kind": "shot", "key": "row", "rect": [100, 200, 300, 40]},
                 {"t": 9.5, "kind": "mark", "key": "cell", "rect": [10, 20, 30, 40]}]
    assert edit_demo.beat_boxes({"box": [1, 2, 3, 4]}, log) == [(1, 2, 3, 4)]
    assert edit_demo.beat_boxes({"box": [[1, 2, 3, 4], [5, 6, 7, 8]]}, log) == [(1, 2, 3, 4), (5, 6, 7, 8)]
    assert edit_demo.beat_boxes({"box": "shot:row"}, log) == [(88, 188, 324, 64)]
    assert edit_demo.beat_boxes({"box": "mark:cell"}, log) == [(0, 8, 52, 64)]
    assert edit_demo.beat_boxes({}, log) == []


@pytest.mark.parametrize("box", [[0, 0, 0, 10], [1900, 10, 40, 10], [10, 1075, 10, 10], [-1, 0, 5, 5], "shot:hero"])
def test_a_box_outside_the_frame_without_size_or_without_a_rect_aborts(box):
    with pytest.raises(SystemExit) as stop:
        edit_demo.beat_boxes({"box": box, "text": "x"}, LOG)      # shot:hero has no rect in LOG
    assert "box" in str(stop.value)


def test_a_box_waits_for_the_camera_on_a_shot_anchor():
    assert edit_demo.box_delay({"at": "shot:stage"}, 1.25) == pytest.approx(1.4 / 1.25 + 0.2)
    assert edit_demo.box_delay({"at": "shot:stage"}, 4) == pytest.approx(1.4 / 4 + 0.2)
    assert edit_demo.box_delay({"at": "play"}, 1.25) == 0
    assert edit_demo.box_delay({"at": "shot:stage", "box_delay": 0.5}, 1.25) == 0.5


def test_caption_band_follows_the_caption_constants():
    bottom, top = edit_demo.caption_band(None), edit_demo.caption_band("top")
    assert edit_demo.caption_band("bottom") == bottom
    assert top[0] < top[1] < bottom[0] < bottom[1] <= edit_demo.H
    assert bottom[0] == edit_demo.H - 150 - 18 and top[0] == 120 - 18


def grey_take(tmp_path, camlog, seconds=10):
    video = tmp_path / "grey.webm"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"color=c=0x808080:size=1920x1080:rate=30:duration={seconds}",
                    "-c:v", "libvpx", "-pix_fmt", "yuv420p", str(video)], check=True)
    (tmp_path / "grey.camlog.json").write_text(json.dumps({"log": camlog}))
    return video


def clip_of(tmp_path, video, beats):
    script = tmp_path / "story.json"
    script.write_text(json.dumps({"speed": 1, "start": 0, "beats": beats}))
    out = tmp_path / "grey.mp4"
    edit_demo.build_clip(video, out, None, None, None, None, True, None, script)
    return out


def pixel(video, x, y, *, at=None, from_end=None, tmp):
    from PIL import Image
    png = tmp / f"p{at}{from_end}.png"
    seek = ["-ss", str(at)] if from_end is None else ["-sseof", str(-from_end)]
    subprocess.run(["ffmpeg", "-v", "error", "-y", *seek, "-i", str(video), "-frames:v", "1", str(png)], check=True)
    return Image.open(png).convert("RGB").getpixel((x, y))


def is_red(p):
    return p[0] > 200 and p[1] < 100 and p[2] < 100


BOX = [400, 300, 400, 200]
BORDER, MIDDLE = (404, 400), (600, 400)   # inside the 8 px left border; inside the box


@needs_ffmpeg
def test_clip_draws_the_box_after_its_delay_and_until_its_caption_ends(tmp_path, private_tmp):
    video = grey_take(tmp_path, [{"t": 0.5, "kind": "shot", "key": "hero"}])
    out = clip_of(tmp_path, video, [{"at": 2.0, "dur": 4, "text": "look", "box": BOX, "box_delay": 1.0}])
    assert not is_red(pixel(out, *BORDER, at=2.5, tmp=tmp_path)), "before the delay"
    assert is_red(pixel(out, *BORDER, at=4.0, tmp=tmp_path)), "inside the caption's time"
    assert not is_red(pixel(out, *BORDER, at=7.0, tmp=tmp_path)), "after the caption"
    mid = pixel(out, *MIDDLE, at=4.0, tmp=tmp_path)
    assert all(abs(c - 128) < 6 for c in mid), "the middle keeps the take's colour"


@needs_ffmpeg
@pytest.mark.parametrize("hold, red", [(True, True), (False, False)])
def test_a_held_caption_and_its_box_are_on_the_last_frame(tmp_path, private_tmp, hold, red):
    video = grey_take(tmp_path, [{"t": 0.5, "kind": "shot", "key": "hero"}])
    beat = {"at": 6.0, "dur": 1.5, "text": "stay", "box": BOX}
    if hold:
        beat["hold"] = True
    out = clip_of(tmp_path, video, [beat])
    assert is_red(pixel(out, *BORDER, from_end=0.1, tmp=tmp_path)) is red


@needs_ffmpeg
@pytest.mark.parametrize("pos, box", [(None, [400, 920, 400, 40]), ("top", [400, 110, 400, 40])])
def test_a_box_under_its_caption_stops_the_clip(tmp_path, private_tmp, pos, box):
    video = grey_take(tmp_path, [{"t": 0.5, "kind": "shot", "key": "hero"}])
    beat = {"at": 2.0, "text": "x", "box": box}
    if pos:
        beat["pos"] = pos
    with pytest.raises(SystemExit, match="pos"):
        clip_of(tmp_path, video, [beat])


@needs_ffmpeg
def test_a_camera_move_while_a_box_shows_stops_the_clip(tmp_path, private_tmp):
    video = grey_take(tmp_path, [{"t": 0.5, "kind": "shot", "key": "hero"}, {"t": 4.0, "kind": "shot", "key": "late"}])
    with pytest.raises(SystemExit, match="late"):
        clip_of(tmp_path, video, [{"at": 2.0, "dur": 4, "text": "x", "box": BOX, "box_delay": 1.0}])


@needs_ffmpeg
def test_hold_is_refused_on_a_beat_that_is_not_the_last(tmp_path, private_tmp):
    video = grey_take(tmp_path, [{"t": 0.5, "kind": "shot", "key": "hero"}])
    with pytest.raises(SystemExit, match="hold"):
        clip_of(tmp_path, video, [{"at": 2.0, "text": "a", "hold": True}, {"at": 6.0, "text": "b"}])


def _commands(monkeypatch) -> list:
    """Record the ffmpeg commands instead of running them (the checks before ffmpeg still run)."""
    seen = []
    monkeypatch.setattr(edit_demo, "run", lambda cmd: seen.append(cmd))
    return seen


@needs_ffmpeg
def test_a_box_on_its_own_anchor_shot_is_not_a_camera_move(tmp_path, private_tmp, monkeypatch):
    """At 1.25x from 0, a shot at 3.28 s comes back from clip seconds as 3.2799999999999998: without a margin the beat's
    own anchor shot fell inside the box's time when "box_delay" is 0 and stopped the clip."""
    assert 0 + (3.28 - 0) / 1.25 * 1.25 < 3.28, "the float rounding this test is about"
    video = grey_take(tmp_path, [{"t": 0.5, "kind": "shot", "key": "hero"}, {"t": 3.28, "kind": "shot", "key": "focus"}])
    script = tmp_path / "story.json"
    script.write_text(json.dumps({"speed": 1.25, "start": 0, "beats": [
        {"at": "shot:focus", "dur": 3, "text": "look", "box": BOX, "box_delay": 0}]}))
    seen = _commands(monkeypatch)
    edit_demo.build_clip(video, tmp_path / "grey.mp4", None, None, None, None, True, None, script)
    (cmd,) = seen
    assert "drawbox=x=400:y=300:w=400:h=200" in cmd[cmd.index("-vf") + 1], "the box is drawn"


@pytest.mark.parametrize("box", [5, 1.5, True, {"x": 1}])
def test_a_box_that_is_neither_a_list_nor_a_string_aborts_with_one_line(box):
    with pytest.raises(SystemExit) as stop:
        edit_demo.beat_boxes({"box": box, "text": "x"}, LOG)
    assert str(stop.value).startswith("box ")


@needs_ffmpeg
@pytest.mark.parametrize("beat, words", [
    ({"at": 2.0, "dur": 2, "box_delay": 2.5}, "box_delay"),        # the box would appear after its caption has gone
    ({"at": 2.0, "dur": 2, "box_delay": 2.0}, "box_delay"),        # ... or just as it goes
    ({"at": 9.5}, "no room"),                                       # the caption itself is left out
])
def test_a_box_that_can_never_show_stops_the_clip_before_ffmpeg(tmp_path, private_tmp, monkeypatch, beat, words):
    video = grey_take(tmp_path, [{"t": 0.5, "kind": "shot", "key": "hero"}])
    seen = _commands(monkeypatch)
    with pytest.raises(SystemExit) as stop:
        clip_of(tmp_path, video, [{**beat, "text": "late", "box": BOX}])
    assert seen == [], "ffmpeg never starts"
    assert str(stop.value).startswith("box ") and words in str(stop.value) and "'late'" in str(stop.value)
