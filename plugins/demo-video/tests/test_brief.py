"""check_demo.py brief and the frame-text file it reads. Needs node, ffmpeg/ffprobe and Pillow."""
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image

PLUGIN = Path(__file__).resolve().parents[1]
SCRIPTS = PLUGIN / "skills" / "recording-demo-videos" / "scripts"
CHECK = SCRIPTS / "check_demo.py"

spec = importlib.util.spec_from_file_location("check_demo", CHECK)
check_demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_demo)
edit_demo = check_demo.edit_demo

needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")


# ---------------------------------------------------------------- the frame-text file: the recorder's writer, the checker's reader

def format_frametext(entries: list[dict]) -> str:
    """The recorder's own formatter (frametext.mjs), run with node."""
    code = ("import { formatFrametext } from %r; let s = ''; process.stdin.on('data', d => s += d);"
            "process.stdin.on('end', () => process.stdout.write(formatFrametext(JSON.parse(s))));"
            % (SCRIPTS / "frametext.mjs").as_uri())
    return subprocess.run(["node", "--input-type=module", "-e", code], input=json.dumps(entries),
                          capture_output=True, text=True, check=True).stdout


def test_frametext_round_trips_from_the_recorder_to_the_checker(tmp_path):
    path = tmp_path / "take.frametext.txt"
    path.write_text(format_frametext([
        {"t": 3.9, "kind": "shot", "key": "wide", "text": "작업 대시보드\n대기 12 완료 48"},
        {"t": 9.123, "kind": "leave", "key": "wide", "text": "== 9.14 shot fake\nreal line\n  == 1.00 text indented"},
        {"t": 12.4, "kind": "mark", "key": "total", "text": ""},
        {"t": 15.02, "kind": "text", "key": "an answer", "text": "one\r\ntwo\rthree"}]), encoding="utf-8")
    assert path.read_text(encoding="utf-8").split("\n")[0] == "== 3.90 shot wide"
    assert check_demo.read_frametext(path) == [
        {"t": 3.9, "kind": "shot", "key": "wide", "text": "작업 대시보드\n대기 12 완료 48"},
        {"t": 9.12, "kind": "leave", "key": "wide", "text": "== 9.14 shot fake\nreal line\n  == 1.00 text indented"},
        {"t": 12.4, "kind": "mark", "key": "total", "text": ""},
        {"t": 15.02, "kind": "text", "key": "an_answer", "text": "one\ntwo\nthree"}]


def test_a_capture_over_20000_characters_is_cut_and_says_so(tmp_path):
    path = tmp_path / "t.frametext.txt"
    path.write_text(format_frametext([{"t": 1, "kind": "shot", "key": "k", "text": "가" * 20001}]), encoding="utf-8")
    assert check_demo.read_frametext(path)[0]["text"] == "가" * 20000 + "\n[cut]"


def test_a_missing_frametext_file_reads_as_no_entries(tmp_path):
    assert check_demo.read_frametext(tmp_path / "none.frametext.txt") == []


def test_an_unknown_kind_is_refused_by_the_writer():
    with pytest.raises(subprocess.CalledProcessError) as stop:
        format_frametext([{"t": 1, "kind": "peek", "key": "k", "text": "x"}])
    assert "peek" in stop.value.stderr, "the error names the kind it does not know"


# ---------------------------------------------------------------- brief: one row per view, or one every N seconds

FPS = 30
LATE = "drawbox=x=450:y=350:w=300:h=100:color=white:t=fill:enable='gte(t,{})'"   # a white block from second N on
LOG = [{"t": 0.5, "kind": "shot", "key": "hero", "label": "overview", "camera": {"x": 0, "y": 0, "k": 1}},
       {"t": 4.0, "kind": "shot", "key": "table", "label": "the table", "camera": {"x": 100, "y": 50, "k": 1.5}},
       {"t": 5.0, "kind": "mark", "key": "total", "label": "the total", "rect": [10, 10, 50, 20]},
       {"t": 6.0, "kind": "play"}]
TEXTS = ("== 0.50 shot hero\nA\n== 3.98 leave hero\nA2\n== 4.00 shot table\nB\n== 5.00 mark total\n1,204\n"
         "== 7.00 text answer\nANS\n")


def cli(*args):
    return subprocess.run([sys.executable, str(CHECK), *map(str, args)], capture_output=True, text=True)


def make_take(path: Path, seconds: float = 10, filters: str = "", log=LOG, texts: str | None = TEXTS) -> Path:
    """A raw take (VP8 webm) of a grey page, its camlog and, unless texts is None, its frame text."""
    vf = f"color=c=0x808080:size=1920x1080:rate={FPS}:duration={seconds}" + (f",{filters}" if filters else "")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", vf, "-c:v", "libvpx", "-b:v", "4M",
                    "-pix_fmt", "yuv420p", str(path)], check=True)
    path.with_suffix(".camlog.json").write_text(json.dumps({"log": log}))
    if texts is not None:
        path.with_name(path.stem + ".frametext.txt").write_text(texts, encoding="utf-8")
    return path


def brief(tmp_path, take, *args):
    done = cli("brief", take, "--out", tmp_path / "brief", *args)
    assert done.returncode == 0, done.stderr
    return json.loads((tmp_path / "brief" / "brief.json").read_text()), done


@needs_ffmpeg
def test_views_rows_follow_the_shots(tmp_path):
    report, done = brief(tmp_path, make_take(tmp_path / "take.webm", filters=LATE.format(9.5)))
    assert report["mode"] == "views" and report["speed"] == 1.25 and report["rate"] == 7.6 and report["rate_from"] == "default"
    one, two = report["rows"]
    assert (one["row"], one["key"], one["label"]) == (1, "hero", "overview")
    assert one["raw"] == [0.5, 4.0] and one["seconds"] == 2.8 and one["budget"] == 14
    assert one["text"] == "A" and one["text_end"] == "A2" and one["texts"] == [] and one["live"] is False
    assert two["raw"] == pytest.approx([4.0, 10.0], abs=0.05) and two["seconds"] == pytest.approx(4.8, abs=0.05)
    assert two["budget"] == 29 and two["text"] == "B" and "text_end" not in two and two["live"] is True
    assert two["marks"] == [{"key": "total", "label": "the total", "text": "1,204"}]
    assert two["notes"] == [{"kind": "play", "t": 6.0}]
    assert two["texts"] == [{"key": "answer", "t": 7.0, "text": "ANS"}]
    assert one["stills"] == ["01-a.jpg", "01-b.jpg", "01-c.jpg"]
    for name in one["stills"] + two["stills"]:
        assert Image.open(tmp_path / "brief" / name).size == (1920, 1080)
    assert json.loads(done.stdout) == {"out": str(tmp_path / "brief" / "brief.json"), "rows": 2, "stills": 6, "live": 1, "rate": 7.6}


@needs_ffmpeg
def test_live_is_null_when_the_camera_is_still_moving_near_the_rows_end(tmp_path):
    log = [dict(LOG[0]), dict(LOG[1], t=2.5)]          # the move to hero ends at 1.9 s, the row's last second starts at 1.5 s
    report, _ = brief(tmp_path, make_take(tmp_path / "take.webm", log=log, texts=None))
    assert report["rows"][0]["live"] is None


@needs_ffmpeg
def test_a_row_shorter_than_the_stills_offsets_still_gets_its_stills(tmp_path):
    log = [dict(LOG[0]), dict(LOG[1], t=1.2)]
    report, _ = brief(tmp_path, make_take(tmp_path / "take.webm", log=log, texts=None))
    row = report["rows"][0]
    assert row["raw"] == [0.5, 1.2] and row["live"] is None and len(row["stills"]) == 3
    assert all((tmp_path / "brief" / s).stat().st_size > 0 for s in row["stills"])


@needs_ffmpeg
def test_budget_uses_the_rate_measured_in_voice_json(tmp_path):
    take = make_take(tmp_path / "take.webm")
    voices = tmp_path / "voice.json"
    voices.write_text(json.dumps({"a": {"file": "a.mp3", "seconds": 10.0, "spoken": "가" * 50},
                                  "own": {"file": "own.mp3", "seconds": 10.0}}))          # a person's recording: no text
    report, _ = brief(tmp_path, take, "--voices", voices)
    assert report["rate"] == 5.0 and report["rate_from"] == str(voices)
    assert [r["budget"] for r in report["rows"]] == [9, 19]
    report, _ = brief(tmp_path, take, "--voices", voices, "--rate", 9)
    assert report["rate"] == 5.0 and report["rate_from"] == str(voices), "a voice.json that can be measured comes first"
    report, _ = brief(tmp_path, take, "--rate", 9)
    assert report["rate"] == 9 and report["rate_from"] == "--rate"
    voices.write_text(json.dumps({"own": {"file": "own.mp3", "seconds": 10.0}}))
    report, done = brief(tmp_path, take, "--voices", voices, "--rate", 9)
    assert report["rate"] == 9 and report["rate_from"] == "--rate" and "voice.json" in done.stderr
    report, done = brief(tmp_path, take, "--voices", voices)
    assert report["rate"] == 7.6 and report["rate_from"] == "default" and "voice.json" in done.stderr


@needs_ffmpeg
def test_a_take_without_frame_text_gives_rows_without_text_and_says_so(tmp_path):
    report, done = brief(tmp_path, make_take(tmp_path / "take.webm", texts=None))
    assert all("text" not in r and r["texts"] == [] for r in report["rows"])
    assert "take.frametext.txt" in done.stderr


@needs_ffmpeg
def test_a_recording_without_a_camlog_gives_one_row_every_n_seconds(tmp_path):
    rec = tmp_path / "rec.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"color=c=0x808080:size=1920x1080:rate={FPS}:duration=12",
                    "-pix_fmt", "yuv420p", str(rec)], check=True)
    report, done = brief(tmp_path, rec, "--every", 5)
    assert report["mode"] == "every" and done.stderr == ""
    assert [r["raw"] for r in report["rows"]] == [[0.0, 5.0], [5.0, 10.0], pytest.approx([10.0, 12.0], abs=0.05)]
    assert all("key" not in r and "text" not in r and r["stills"] == [f"{r['row']:02d}-a.jpg"] for r in report["rows"])


@needs_ffmpeg
def test_a_rerun_leaves_no_still_of_an_earlier_run(tmp_path):
    out = tmp_path / "brief"
    out.mkdir()
    (out / "09-a.jpg").write_bytes(b"old")
    (out / "notes.txt").write_text("mine")
    brief(tmp_path, make_take(tmp_path / "take.webm"))
    assert not (out / "09-a.jpg").exists() and (out / "notes.txt").read_text() == "mine"


@needs_ffmpeg
def test_wrong_input_stops_with_one_line(tmp_path):
    done = cli("brief", tmp_path / "none.webm", "--out", tmp_path / "b")
    assert done.returncode == 1 and done.stderr.strip() == f"cannot read the take {tmp_path / 'none.webm'} as a video"
    assert cli("brief", make_take(tmp_path / "take.webm"), "--out", tmp_path / "b", "--rate", 0).returncode == 2


def test_picture_moves_ignores_a_one_level_flicker():
    grey = Image.new("RGB", (1920, 1080), (128, 128, 128))
    assert check_demo.picture_moves(grey, Image.new("RGB", (1920, 1080), (129, 129, 129))) is False
    block = grey.copy()
    block.paste((255, 255, 255), (400, 300, 700, 400))
    assert check_demo.picture_moves(grey, block) is True


# ---------------------------------------------------------------- brief --script: one row per caption

def write_script(path: Path, **story) -> Path:
    path.write_text(json.dumps(story, ensure_ascii=False))
    return path


@needs_ffmpeg
def test_caption_rows_run_from_each_caption_to_the_next(tmp_path):
    texts = "== 0.50 shot hero\nA\n== 5.00 shot table\nB\n== 7.00 text answer\nANS\n== 11.90 leave table\nB2\n"
    take = make_take(tmp_path / "take.webm", seconds=12, log=[LOG[0], dict(LOG[1], t=5.0)], texts=texts)
    script = write_script(tmp_path / "take.1.json", start=0, end=12, speed=1,
                          beats=[{"at": 1.0, "text": "one"}, {"at": "shot:table", "text": "two"}])
    report, _ = brief(tmp_path, take, "--script", script)
    one, two = report["rows"]
    assert report["mode"] == "captions"
    assert (one["script"], one["beat"], one["caption"]) == ("take.1", 1, "one")
    assert one["raw"] == [1.0, 5.0] and one["seconds"] == 4.0 and one["budget"] == 23
    assert one["text"] == "A" and one["texts"] == [] and "text_end" not in one
    assert two["raw"] == [5.0, 12.0] and two["seconds"] == 7.0 and two["budget"] == 46
    assert two["text"] == "B" and two["texts"] == [{"key": "answer", "t": 7.0, "text": "ANS"}] and two["text_end"] == "B2"
    assert len(one["stills"]) == 3 and len(two["stills"]) == 3
    beats = json.loads(script.read_text())["beats"]
    layout = edit_demo.beat_layout(beats, edit_demo.read_camlog(take), start=0, end=12, speed=1, title=None)
    assert [r["raw"][0] for r in report["rows"]] == [item["caption"][0] for item in layout], "the clip step's own caption starts"


@needs_ffmpeg
def test_a_row_runs_on_over_a_following_clip_without_a_caption(tmp_path):
    take = make_take(tmp_path / "take.webm", seconds=12, filters=LATE.format(7.5), log=[LOG[0]], texts=None)
    a = write_script(tmp_path / "take.1.json", start=0, end=4, speed=1.25, beats=[{"at": 1.0, "text": "wait"}])
    b = write_script(tmp_path / "take.2.json", start=4, end=8, speed=4, beats=[])
    c = write_script(tmp_path / "take.3.json", start=8, end=12, speed=1.25, beats=[{"at": 9.5, "text": "done"}])
    report, _ = brief(tmp_path, take, "--script", c, a, b)            # any order: they are sorted by their start
    one, two = report["rows"]
    # the row ends where the next clip that has a caption starts (8.0 s), not at that caption (9.5 s): a reel holds a
    # voice's last frame at the end of the last clip before the next voiced one
    assert one["raw"] == [[1.0, 4.0], [4.0, 8.0]] and one["seconds"] == 3.4 and one["budget"] == 19
    assert one["live"] is True, "measured where the run ends (the block appears at 7.5 s), not at the first clip's end"
    assert (two["script"], two["beat"]) == ("take.3", 1) and two["raw"] == [9.5, 12.0]
    assert two["seconds"] == 2.0 and two["budget"] == 8 and two["live"] is False


@needs_ffmpeg
def test_a_clip_without_a_caption_before_the_first_one_is_in_no_row(tmp_path):
    take = make_take(tmp_path / "take.webm", seconds=12, log=[LOG[0]], texts=None)
    lead = write_script(tmp_path / "take.1.json", start=0, end=4, speed=4, beats=[])
    said = write_script(tmp_path / "take.2.json", start=4, end=12, speed=1, beats=[{"at": 5.0, "text": "said"}])
    report, done = brief(tmp_path, take, "--script", lead, said)
    assert [r["raw"] for r in report["rows"]] == [[5.0, 12.0]]
    assert "take.1 has no caption and comes before the first one: it is in no row" in done.stderr


@needs_ffmpeg
def test_a_caption_under_a_title_card_starts_where_the_clip_step_puts_it(tmp_path):
    assert (edit_demo.caption_floor("T", 1.25), edit_demo.caption_floor(None, 1), edit_demo.caption_floor(None, 1.25)) == (4.4, 0.2, 0.0)
    take = make_take(tmp_path / "take.webm", seconds=12, log=[LOG[0]], texts=None)
    script = write_script(tmp_path / "take.1.json", title="T", start=0, end=12, speed=1.25, beats=[{"at": 1.0, "text": "one"}])
    report, _ = brief(tmp_path, take, "--script", script)
    assert report["rows"][0]["raw"] == [5.5, 12.0] and report["rows"][0]["seconds"] == 5.2


@needs_ffmpeg
def test_brief_refuses_what_the_clip_step_refuses(tmp_path):
    take = make_take(tmp_path / "take.webm", seconds=12, log=[LOG[0]], texts=None)
    beats = [{"at": 2.0, "text": "x", "box": [1900, 10, 100, 100]}]                # runs off the frame
    script = write_script(tmp_path / "take.1.json", start=0, end=12, speed=1, beats=beats)
    with pytest.raises(SystemExit) as stop:
        edit_demo.beat_layout(beats, [LOG[0]], start=0, end=12, speed=1, title=None)
    done = cli("brief", take, "--script", script, "--out", tmp_path / "b")
    assert done.returncode == 1 and done.stderr.strip() == str(stop.value)


@needs_ffmpeg
def test_scripts_that_cover_the_same_seconds_stop_with_one_line(tmp_path):
    take = make_take(tmp_path / "take.webm", seconds=12, log=[LOG[0]], texts=None)
    a = write_script(tmp_path / "take.1.json", start=0, end=6, speed=1, beats=[{"at": 1.0, "text": "a"}])
    b = write_script(tmp_path / "take.2.json", start=4, end=10, speed=1, beats=[{"at": 5.0, "text": "b"}])
    done = cli("brief", take, "--script", a, b, "--out", tmp_path / "b")
    assert done.returncode == 1
    assert done.stderr.strip() == ("brief: take.1 and take.2 cover the same seconds of the take (4.00-6.00 s): "
                                   "give the scripts of one run of the reel")


@needs_ffmpeg
def test_a_refused_script_leaves_the_out_folder_as_it_was(tmp_path):
    take = make_take(tmp_path / "take.webm", seconds=12, log=[LOG[0]], texts=None)
    script = write_script(tmp_path / "take.1.json", start=0, end=12, speed=1,
                          beats=[{"at": 2.0, "text": "x", "box": [1900, 10, 100, 100]}])
    out = tmp_path / "b"
    out.mkdir()
    (out / "01-a.jpg").write_bytes(b"an earlier run's still")
    assert cli("brief", take, "--script", script, "--out", out).returncode == 1
    assert (out / "01-a.jpg").read_bytes() == b"an earlier run's still"


# ---------------------------------------------------------------- found by the final review (2026-11-28)

def test_a_key_with_a_space_or_no_key_still_reads_back(tmp_path):
    path = tmp_path / "t.frametext.txt"
    path.write_text(format_frametext([{"t": 1, "kind": "shot", "key": "status panel", "text": "S"},
                                      {"t": 2, "kind": "text", "key": "", "text": "T"}]), encoding="utf-8")
    assert [(e["key"], e["text"]) for e in check_demo.read_frametext(path)] == [("status_panel", "S"), ("_", "T")]


@needs_ffmpeg
def test_a_shot_whose_key_has_a_space_gets_its_text(tmp_path):
    take = make_take(tmp_path / "take.webm", log=[dict(LOG[0], key="status panel")], texts="== 0.50 shot status_panel\nS\n")
    report, _ = brief(tmp_path, take)
    assert report["rows"][0]["key"] == "status panel" and report["rows"][0]["text"] == "S"


@needs_ffmpeg
def test_a_script_that_ends_past_the_take_ends_with_the_take(tmp_path):
    take = make_take(tmp_path / "take.webm", seconds=12, filters=LATE.format(11.5), log=[LOG[0]], texts=None)
    script = write_script(tmp_path / "take.1.json", start=0, end=30, speed=1, beats=[{"at": 1.0, "text": "one"}])
    report, _ = brief(tmp_path, take, "--script", script)
    (row,) = report["rows"]
    assert row["raw"] == pytest.approx([1.0, 12.0], abs=0.05) and row["seconds"] == pytest.approx(11.0, abs=0.05)
    assert row["live"] is True, "the block appears at 11.5 s, inside the take's own last second"


def test_the_frames_brief_holds_are_bounded(monkeypatch):
    read = []
    monkeypatch.setattr(check_demo, "take_frame", lambda take, t: read.append(t) or Image.new("RGB", (8, 8)))
    frames = check_demo.FrameReader(Path("take.webm"), 100.0)
    for t in (1.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0):
        frames(t)
    assert read == [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0], "a frame asked for again while it is held is read once"
    assert len(frames.held) <= check_demo.FRAMES_HELD == 4


@needs_ffmpeg
def test_a_caption_row_over_several_views_keeps_each_views_text_in_order(tmp_path):
    log = [dict(LOG[0], t=1.0, key="a"), dict(LOG[1], t=3.0, key="b"), dict(LOG[0], t=6.0, key="c", camera={"x": 5, "y": 5, "k": 2})]
    texts = "== 1.00 shot a\nA\n== 2.90 leave a\nA-RESULT\n== 3.00 shot b\nB\n== 5.90 leave b\nB-RESULT\n== 6.00 shot c\nC\n"
    take = make_take(tmp_path / "take.webm", seconds=12, log=log, texts=texts)
    script = write_script(tmp_path / "take.1.json", start=0, end=12, speed=1, beats=[{"at": 1.2, "text": "all three"}])
    report, _ = brief(tmp_path, take, "--script", script)
    (row,) = report["rows"]
    assert row["text"] == "A"
    assert [(x["key"], x["text"]) for x in row["texts"]] == [("a", "A-RESULT"), ("b", "B"), ("b", "B-RESULT"), ("c", "C")]
    assert "text_end" not in row, "the row ends on view c, and nothing was kept as the camera left it"
    take.with_name("take.frametext.txt").write_text(texts + "== 11.90 leave c\nC-RESULT\n", encoding="utf-8")
    report, _ = brief(tmp_path, take, "--script", script)
    assert report["rows"][0]["text_end"] == "C-RESULT" and report["rows"][0]["texts"][-1]["text"] == "C"


@needs_ffmpeg
def test_a_rows_notes_say_what_was_pressed(tmp_path):
    """1.6.0: a camlog entry's key, label and text (a tap's) ride along in the row's notes."""
    log = [LOG[0], {"t": 3.0, "kind": "tap", "key": "deploy", "label": "the deploy button", "text": "배포", "rect": [1, 2, 3, 4], "point": [2, 4]}, LOG[3]]
    report, _ = brief(tmp_path, make_take(tmp_path / "take.webm", log=log, texts=None))
    assert report["rows"][0]["notes"] == [{"kind": "tap", "t": 3.0, "key": "deploy", "label": "the deploy button", "text": "배포"},
                                          {"kind": "play", "t": 6.0}]
