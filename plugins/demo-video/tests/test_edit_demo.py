"""edit_demo.py: anchor resolution, speed, reel fades, temp-dir cleanup. Needs ffmpeg/ffprobe on PATH."""
import importlib.util
import json
import re
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


def test_a_mark_anchor_finds_the_mark_with_its_key():
    log = LOG + [{"t": 9.0, "kind": "mark", "key": "wide", "rect": [0, 0, 10, 10]},
                 {"t": 10.5, "kind": "mark", "key": "after", "rect": [5, 5, 10, 10]},
                 {"t": 12.0, "kind": "mark", "key": "after", "rect": [5, 5, 10, 10]}]
    assert edit_demo.script_time("mark:after", log) == 10.5
    assert edit_demo.script_time("mark:after#2", log) == 12.0
    assert edit_demo.script_time("mark:wide", log) == 9.0
    with pytest.raises(SystemExit, match="mark:gone"):
        edit_demo.script_time("mark:gone", log)
    assert edit_demo.script_time("note:play", log) == 4.5 and edit_demo.script_time("play", log) == 4.5


MARK_NOTES = LOG + [{"t": 9.0, "kind": "mark"}, {"t": 11.0, "kind": "mark", "why": "x"}]   # rec.note('mark') of 1.3.0


@pytest.mark.parametrize("at, t", [("mark", 9.0), ("note:mark", 9.0), ("mark#2", 11.0)])
def test_a_mark_anchor_without_a_key_finds_the_notes_of_kind_mark_as_in_1_3_0(at, t):
    """A storyboard of 1.3.0 that wrote rec.note('mark') anchors to those entries by kind: only "mark:<key>" asks for a key."""
    assert edit_demo.script_time(at, MARK_NOTES) == t


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


def test_the_caption_y_of_the_filter_and_of_the_band_come_from_one_constant(monkeypatch):
    assert (edit_demo.caption_y(None), edit_demo.caption_y("bottom"), edit_demo.caption_y("top")) == ("h-150", "h-150", "120")
    monkeypatch.setattr(edit_demo, "BEAT_Y_TOP", 130)
    monkeypatch.setattr(edit_demo, "BEAT_Y_BOTTOM", edit_demo.H - 160)
    assert edit_demo.caption_y("top") == "130" and edit_demo.caption_band("top")[0] == 130 - 18
    assert edit_demo.caption_y(None) == "h-160" and edit_demo.caption_band(None)[0] == edit_demo.H - 160 - 18


def grey_take(tmp_path, camlog, seconds=10, rate=30):
    video = tmp_path / "grey.webm"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"color=c=0x808080:size=1920x1080:rate={rate}:duration={seconds}",
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
def test_a_box_that_starts_as_the_camera_stops_is_drawn(tmp_path, private_tmp, monkeypatch):
    """At 1.25x from 0, a box 1.12 s after its caption on a shot at 4.01 s starts as that shot's move ends (5.41 s), but
    comes back from clip seconds as 5.409999999999999: without a margin it counted as shown during the move."""
    assert 0 + (4.01 / 1.25 + 1.12) * 1.25 < 4.01 + edit_demo.CAMERA_MOVE, "the float rounding this test is about"
    video = grey_take(tmp_path, [{"t": 0.5, "kind": "shot", "key": "hero"}, {"t": 4.01, "kind": "shot", "key": "focus"}])
    script = tmp_path / "story.json"
    script.write_text(json.dumps({"speed": 1.25, "start": 0, "beats": [
        {"at": "shot:focus", "dur": 3, "text": "look", "box": BOX, "box_delay": 1.12}]}))
    seen = _commands(monkeypatch)
    edit_demo.build_clip(video, tmp_path / "grey.mp4", None, None, None, None, True, None, script)
    (cmd,) = seen
    assert "drawbox=x=400:y=300:w=400:h=200" in cmd[cmd.index("-vf") + 1], "the box is drawn"


# ---------------------------------------------------------------- the camera check: no box while the camera moves

def layout(beats, log, speed=1.25):
    return edit_demo.beat_layout(beats, log, start=0.0, end=20.0, speed=speed, title=None)


CAM_WIDE, CAM_TABLE = {"x": 0, "y": 0, "k": 1}, {"x": 300, "y": 200, "k": 1.8}
TABLE = [{"t": 1.0, "kind": "shot", "key": "wide", "camera": CAM_WIDE},
         {"t": 5.0, "kind": "shot", "key": "table", "camera": CAM_TABLE, "rect": [300, 200, 900, 500]},   # moves to 6.4 s
         {"t": 5.05, "kind": "mark", "key": "row", "rect": [400, 300, 400, 40]},
         {"t": 5.3, "kind": "clicked"}]
STILL_MOVING = [
    {"at": "mark:row", "box": "mark:row", "dur": 4},              # a mark made just after a focus
    {"at": "clicked", "box": BOX, "dur": 4},                       # a note 0.3 s after a shot
    {"at": 5.2, "box": BOX, "dur": 4},                             # raw seconds 0.2 s after a shot
    {"at": "shot:table", "offset": -1.0, "box": BOX, "dur": 5},    # a shot anchor whose caption starts 1 s early
]


@pytest.mark.parametrize("beat", STILL_MOVING)
def test_a_box_that_starts_while_the_camera_still_moves_is_refused_with_the_box_delay_that_waits(beat):
    """Whatever the beat is anchored to, a box may not start before the camera has stopped; the refusal says when it
    stops and names a box_delay that starts the box after it, and that box_delay passes."""
    with pytest.raises(SystemExit) as stop:
        layout([{**beat, "text": "x"}], TABLE)
    message = str(stop.value)
    assert message.startswith("the camera is still moving to shot 'table' (from 5.00 s, it stops at 6.40 s)"), message
    delay = float(re.search(r'"box_delay": ([0-9.]+)$', message).group(1))
    (item,) = layout([{**beat, "text": "x", "box_delay": delay}], TABLE)
    assert 6.4 - edit_demo.CAMERA_MARGIN <= item["box_raw"][0] < 6.4 + 0.0125, "the box starts as the camera stops"


def test_the_refusal_of_a_box_during_a_move_reads_in_one_line():
    with pytest.raises(SystemExit) as stop:
        layout([{"at": "clicked", "box": BOX, "dur": 4, "text": "x"}], TABLE)
    assert str(stop.value) == ("the camera is still moving to shot 'table' (from 5.00 s, it stops at 6.40 s) when the box "
                               "of 'x' starts (it shows 5.30-10.30 s): start the box after the camera stops with "
                               "\"box_delay\": 0.88")


def test_a_box_whose_caption_ends_before_the_camera_stops_is_told_to_anchor_later():
    log = [{"t": 1.0, "kind": "shot", "key": "wide", "camera": CAM_WIDE},
           {"t": 5.0, "kind": "shot", "key": "slow", "camera": CAM_TABLE, "move": 3.0}]     # moves to 8.0 s
    with pytest.raises(SystemExit) as stop:
        layout([{"at": 5.2, "box": BOX, "dur": 1.5, "text": "x"}], log)                     # caption to 7.075 s
    assert str(stop.value).endswith("its caption ends before the camera stops: anchor the beat later or lengthen its caption")


def test_a_shot_anchored_box_with_the_default_delay_waits_for_the_move():
    (item,) = layout([{"at": "shot:table", "box": BOX, "dur": 5, "text": "x"}], TABLE)
    assert item["box_raw"][0] == pytest.approx(5.0 + 1.4 + 0.2 * 1.25)


@pytest.mark.parametrize("shot, passes", [
    ({"camera": CAM_TABLE}, True),                        # the same camera values as the shot before: nothing moves
    # the same element focused again: its numbers come back with float noise (seen on a real take: 1e-4 px)
    ({"camera": {"x": 300.0001, "y": 199.9998, "k": 1.8}}, True),
    ({"camera": {"x": 300.5, "y": 200, "k": 1.8}}, False),   # half a pixel off: a move
    ({"camera": {"x": 300, "y": 200, "k": 1.801}}, False),   # a zoom 0.001 apart: a move (about 1 px at the frame's edge)
    ({"camera": CAM_WIDE}, False),                        # back to wide: a move
    ({"camera": None, "missing": True}, True),            # its selector matched nothing: the camera did not move
    ({}, False),                                          # a camlog without camera values: counted as a move
    ({"camera": CAM_WIDE, "move": 0.5}, True),            # a move of its own length, over before the box
    ({"camera": CAM_WIDE, "move": 0.7}, False),
])
def test_a_shot_moves_the_camera_for_its_own_length_unless_its_camera_values_stay(shot, passes):
    log = TABLE + [{"t": 9.0, "kind": "shot", "key": "again", **shot}]
    beat = {"at": 9.6, "box": BOX, "dur": 3, "text": "after"}       # the box starts 0.6 s after the shot
    if passes:
        (item,) = layout([beat], log)
        assert item["box_raw"][0] == pytest.approx(9.6)
    else:
        with pytest.raises(SystemExit, match="'again'"):
            layout([beat], log)


def test_a_shot_with_a_longer_move_than_the_default_delay_covers_is_refused():
    """The default delay of a shot-anchored beat stays 1.4 / speed + 0.2; a recorded move of 2.5 s outlasts it."""
    log = [{"t": 1.0, "kind": "shot", "key": "wide", "camera": CAM_WIDE},
           {"t": 5.0, "kind": "shot", "key": "slow", "camera": CAM_TABLE, "move": 2.5}]
    with pytest.raises(SystemExit) as stop:
        layout([{"at": "shot:slow", "box": BOX, "dur": 5, "text": "x"}], log)
    assert "it stops at 7.50 s" in str(stop.value) and '"box_delay": 2.00' in str(stop.value)


@needs_ffmpeg
def test_clip_prints_each_captions_and_boxs_time_for_a_script_with_boxes_or_a_hold(tmp_path, private_tmp, monkeypatch,
                                                                                  capsys):
    """So that a reel's voice_at can be read off: each beat's caption and box times in the finished clip, on stderr,
    for a script that uses a box or a hold; a script without them prints what it printed before."""
    video = grey_take(tmp_path, [{"t": 0.5, "kind": "shot", "key": "hero"}])
    _commands(monkeypatch)
    beats = [{"at": 2.0, "dur": 2, "text": "plain"}, {"at": 6.0, "text": "held", "box": BOX, "box_delay": 0.5, "hold": True}]
    clip_of(tmp_path, video, beats)
    err = capsys.readouterr().err
    assert "clip: beat 1: caption 2.00-4.00 s: 'plain'" in err.splitlines()
    assert "clip: beat 2: caption 6.00-10.00 s, box 6.50-10.00 s: 'held'" in err.splitlines()
    clip_of(tmp_path, video, [{"at": 2.0, "dur": 2, "text": "plain"}, {"at": 6.0, "text": "last"}])
    assert "clip: beat" not in capsys.readouterr().err


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


# ---------------------------------------------------------------- a box with a length of its own ("box_dur")

LATER_SHOT = [{"t": 0.5, "kind": "shot", "key": "hero"}, {"t": 6.0, "kind": "shot", "key": "later"}]
HELD = {"at": 2.0, "text": "stay", "box": BOX, "box_delay": 0.5, "hold": True}   # caption 2 s to the clip's end (10 s)
CAPTION_EDGE = (86, 918)   # inside the caption's blue box, left of its text


def is_caption_blue(p):
    return p[2] > 170 and p[0] < 100


@needs_ffmpeg
def test_box_dur_ends_a_held_box_before_a_later_camera_shot(tmp_path, private_tmp):
    """The box shows 2.5-4.5 s ("box_delay" 0.5, "box_dur" 2), the camera moves at 6 s, the caption stays to the end."""
    video = grey_take(tmp_path, LATER_SHOT)
    out = clip_of(tmp_path, video, [{**HELD, "box_dur": 2.0}])
    assert is_red(pixel(out, *BORDER, at=3.5, tmp=tmp_path)), "inside the box's time"
    assert not is_red(pixel(out, *BORDER, at=5.0, tmp=tmp_path)), "after box_dur"
    assert not is_red(pixel(out, *BORDER, from_end=0.1, tmp=tmp_path)), "the box is gone on the last frame"
    assert is_caption_blue(pixel(out, *CAPTION_EDGE, from_end=0.1, tmp=tmp_path)), "the held caption is on the last frame"


def last_frame(video, tmp):
    """The clip's truly last frame: its frames counted and the last one decoded (a seek near the end can land on an
    earlier frame)."""
    from PIL import Image
    n = int(subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
                            "stream=nb_read_frames", "-of", "csv=p=0", str(video)], check=True, capture_output=True,
                           text=True).stdout)
    png = tmp / "last.png"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-vf", f"select=eq(n\\,{n - 1})", "-frames:v", "1",
                    str(png)], check=True)
    return Image.open(png).convert("RGB")


@needs_ffmpeg
@pytest.mark.parametrize("end", [5.085, 5.125])
def test_a_held_caption_and_its_box_are_on_the_truly_last_frame_of_a_25_fps_take(tmp_path, private_tmp, end):
    """A 25 fps take cut from 0.2 s to 5.085 (5.125) s at speed 1: the clip's last frame lies on a 1/30 s slot past the
    clip's stated end of 4.885 (4.925) s, which the filters write to 0.01 s. The frame a reel repeats during a hold
    must still carry the held caption and its box."""
    video = grey_take(tmp_path, [{"t": 0.5, "kind": "shot", "key": "hero"}], seconds=8, rate=25)
    script = tmp_path / "story.json"
    script.write_text(json.dumps({"speed": 1, "start": 0.2, "end": end, "beats": [
        {"at": 2.0, "text": "stay", "box": BOX, "hold": True}]}))
    out = tmp_path / "grey.mp4"
    edit_demo.build_clip(video, out, None, None, None, None, True, None, script)
    frame = last_frame(out, tmp_path)
    assert is_caption_blue(frame.getpixel(CAPTION_EDGE)), "the held caption is on the last frame"
    assert is_red(frame.getpixel(BORDER)), "the held box is on the last frame"


@needs_ffmpeg
def test_a_held_box_with_a_box_dur_to_the_clips_end_is_on_the_truly_last_frame(tmp_path, private_tmp):
    """A box_dur written to the held caption's end ends with it: it is held to the last frame too."""
    video = grey_take(tmp_path, [{"t": 0.5, "kind": "shot", "key": "hero"}], seconds=8, rate=25)
    script = tmp_path / "story.json"
    script.write_text(json.dumps({"speed": 1, "start": 0.2, "end": 5.085, "beats": [
        {"at": 2.0, "text": "stay", "box": BOX, "box_delay": 0.5, "box_dur": 4.885 - 1.8 - 0.5, "hold": True}]}))
    out = tmp_path / "grey.mp4"
    edit_demo.build_clip(video, out, None, None, None, None, True, None, script)
    assert is_red(last_frame(out, tmp_path).getpixel(BORDER))


@needs_ffmpeg
@pytest.mark.parametrize("beat, shows, advice", [
    # a held caption without box_dur: shortening the caption cannot help, a box_dur can
    (HELD, "2.50-10.00 s", 'give the box a "box_dur" or move the box'),
    ({**HELD, "box_dur": 4.0}, "2.50-6.50 s", 'shorten "box_dur" or move the box'),   # a box_dur that still reaches the shot
    # a caption that is not held: the advice stays as it was
    ({"at": 2.0, "text": "stay", "box": BOX, "box_delay": 0.5, "dur": 6.0}, "2.50-8.00 s",
     "shorten the caption or move the box"),
])
def test_a_box_that_reaches_the_later_shot_stops_the_clip(tmp_path, private_tmp, monkeypatch, beat, shows, advice):
    video = grey_take(tmp_path, LATER_SHOT)
    seen = _commands(monkeypatch)
    with pytest.raises(SystemExit) as stop:
        clip_of(tmp_path, video, [beat])
    assert seen == [], "ffmpeg never starts"
    assert str(stop.value) == (f"the camera moves to shot 'later' at 6.00 s (it stops at 7.40 s) while the box of 'stay' "
                               f"shows ({shows}): {advice}, or start the box after the camera stops with "
                               f"\"box_delay\": 5.40")


@needs_ffmpeg
def test_a_box_dur_that_ends_with_its_caption_draws_what_no_box_dur_draws(tmp_path, private_tmp, monkeypatch):
    """At 1.25x the box's end (start + box_dur) comes out a little after the caption's end: it is that end, not past it."""
    assert 2.0 / 1.25 + 0.3 + 2.7 > 2.0 / 1.25 + 3, "the float rounding this test is about"
    video = grey_take(tmp_path, [{"t": 0.5, "kind": "shot", "key": "hero"}])
    seen = _commands(monkeypatch)
    beat = {"at": 2.0, "dur": 3, "text": "to the end", "box": BOX, "box_delay": 0.3}   # caption 1.6-4.6 s, box from 1.9 s
    for extra in ({}, {"box_dur": 2.7}):
        script = tmp_path / "story.json"
        script.write_text(json.dumps({"speed": 1.25, "start": 0, "beats": [{**beat, **extra}]}))
        edit_demo.build_clip(video, tmp_path / "grey.mp4", None, None, None, None, True, None, script)
    without, with_dur = (cmd[cmd.index("-vf") + 1] for cmd in seen)
    assert "between(t\\,1.90\\,4.60)" in without
    assert re.sub(r"edit-\w+", "", with_dur) == re.sub(r"edit-\w+", "", without)


@needs_ffmpeg
@pytest.mark.parametrize("beat, words", [
    ({"at": 2.0, "dur": 3, "box": BOX, "box_delay": 1.0, "box_dur": 2.5}, ["5.50 s", "5.00 s"]),  # box 3.0-5.5, caption to 5.0
    ({"at": 6.0, "box": BOX, "hold": True, "box_dur": 5}, ["11.00 s", "10.00 s"]),            # held: the clip ends at 10 s
    ({"at": 2.0, "box": BOX, "box_dur": 0}, ["above 0"]),
    ({"at": 2.0, "box": BOX, "box_dur": -1}, ["above 0"]),
    ({"at": 2.0, "box": BOX, "box_dur": "2"}, ["above 0", "'2'"]),
    ({"at": 2.0, "box": BOX, "box_dur": True}, ["above 0"]),
    ({"at": 2.0, "box_dur": 2}, ["no box"]),
])
def test_a_wrong_box_dur_stops_the_clip_before_ffmpeg_with_one_line(tmp_path, private_tmp, monkeypatch, beat, words):
    video = grey_take(tmp_path, [{"t": 0.5, "kind": "shot", "key": "hero"}])
    seen = _commands(monkeypatch)
    with pytest.raises(SystemExit) as stop:
        clip_of(tmp_path, video, [{**beat, "text": "late"}])
    message = str(stop.value)
    assert seen == [], "ffmpeg never starts"
    assert "\n" not in message and "box_dur" in message and "'late'" in message, message
    assert all(w in message for w in words), message
