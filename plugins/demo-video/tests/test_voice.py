"""edit_demo.py voice: readings, the Hangul-only check, the cache, and the call form. A stand-in `aws` is the only one on PATH."""
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

STAND_IN = '''#!{python}
"""Stand-in for the AWS CLI: accepts only `polly synthesize-speech ...`, logs its arguments, writes a tone."""
import json, subprocess, sys
args = sys.argv[1:]
LOG = {log!r}
if args[:2] != ["polly", "synthesize-speech"]:
    sys.stderr.write("stand-in aws: unexpected form: %r\\n" % (args,))
    sys.exit(2)
rest = args[2:]
opts, positional, i = {{}}, [], 0
while i < len(rest):
    if rest[i] == "--text":
        sys.stderr.write("stand-in aws: --text must be one argument (--text=<text>)\\n")
        sys.exit(2)
    if rest[i].startswith("--text="):
        opts["--text"] = rest[i][len("--text="):]
        i += 1
    elif rest[i].startswith("--"):
        opts[rest[i]] = rest[i + 1]
        i += 2
    else:
        positional.append(rest[i])
        i += 1
for need in ("--engine", "--language-code", "--voice-id", "--output-format", "--text"):
    if need not in opts:
        sys.stderr.write("stand-in aws: missing " + need + "\\n")
        sys.exit(2)
if len(positional) != 1 or opts["--output-format"] != "mp3":
    sys.stderr.write("stand-in aws: bad output\\n")
    sys.exit(2)
with open(LOG, "a") as f:
    f.write(json.dumps(opts, ensure_ascii=False) + "\\n")
text = opts["--text"]
if "FAIL" in text:
    sys.stderr.write("An error occurred (AccessDeniedException): stand-in refusal\\n")
    sys.exit(1)
seconds = 0.1 * len(text)
subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=%s" % seconds,
                "-ac", "1", positional[0]], check=True)
'''


@pytest.fixture
def aws(tmp_path, monkeypatch):
    """Put the stand-in first on PATH, with only ffmpeg's and python's folders after it (no real aws)."""
    bindir = tmp_path / "bin"
    bindir.mkdir()
    log = tmp_path / "aws.log"
    log.write_text("")
    stand_in = bindir / "aws"
    stand_in.write_text(STAND_IN.format(python=sys.executable, log=str(log)))
    stand_in.chmod(0o755)
    folders = [str(bindir), str(Path(shutil.which("ffmpeg")).parent), str(Path(sys.executable).parent)]
    monkeypatch.setenv("PATH", ":".join(dict.fromkeys(folders)))
    assert shutil.which("aws") == str(stand_in)

    def calls():
        return [json.loads(x) for x in log.read_text().splitlines()]
    return calls


def synth(lines, out, **kw):
    args = dict(voice="Seoyeon", engine="generative", language="ko-KR", region=None, readings={}, hangul_only=False)
    args.update(kw)
    return edit_demo.synthesize(lines, out, **args)


def ffprobe_seconds(path):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                                check=True, capture_output=True, text=True).stdout)


def test_readings_apply_longest_first():
    r = {"release": "릴리스", "release_review": "릴리스 리뷰", "403": "사공삼"}
    assert edit_demo.spoken("release_review가 403을 받습니다", r) == "릴리스 리뷰가 사공삼을 받습니다"


def test_a_reading_is_not_replaced_again_by_a_shorter_key():
    assert edit_demo.spoken("ab", {"ab": "b", "b": "x"}) == "b"


def test_unreadable_names_what_is_left():
    assert edit_demo.unreadable("MCP 서버가 2건을 돌려줍니다") == ["MCP", "2"]
    assert edit_demo.unreadable("엠씨피 서버가 두 건을 돌려줍니다") == []
    assert edit_demo.unreadable("release_review") == ["release", "review"]


@needs_ffmpeg
def test_voice_writes_one_file_per_line_with_its_seconds(tmp_path, aws):
    out = tmp_path / "voice"
    result = synth({"a": "첫째 줄입니다", "b": "둘째 줄은 조금 더 깁니다"}, out)
    assert (out / "a.mp3").exists() and (out / "b.mp3").exists()
    saved = json.loads((out / "voice.json").read_text())
    assert saved == result
    for name in ("a", "b"):
        assert result[name]["file"] == f"{name}.mp3"
        assert abs(result[name]["seconds"] - ffprobe_seconds(out / f"{name}.mp3")) < 0.1
    assert result["b"]["seconds"] > result["a"]["seconds"]
    assert len(result["a"]["key"]) == 64
    assert aws()[0] == {"--engine": "generative", "--language-code": "ko-KR", "--voice-id": "Seoyeon",
                        "--output-format": "mp3", "--text": "첫째 줄입니다"}


@needs_ffmpeg
def test_region_is_passed_when_given(tmp_path, aws):
    synth({"a": "한 줄"}, tmp_path / "v", region="us-west-2")
    assert aws()[0]["--region"] == "us-west-2"


@needs_ffmpeg
def test_readings_are_what_is_sent_and_recorded(tmp_path, aws):
    result = synth({"a": "MCP 서버"}, tmp_path / "v", readings={"MCP": "엠씨피"}, hangul_only=True)
    assert result["a"]["spoken"] == "엠씨피 서버"
    assert aws()[0]["--text"] == "엠씨피 서버"


@needs_ffmpeg
def test_hangul_only_refuses_a_line_and_names_the_tokens(tmp_path, aws):
    with pytest.raises(SystemExit) as e:
        synth({"first": "좋은 줄입니다", "second": "MCP 서버가 2건"}, tmp_path / "v", hangul_only=True)
    assert "second" in str(e.value) and "MCP" in str(e.value)
    assert aws() == []


@needs_ffmpeg
def test_an_unchanged_line_is_not_synthesized_again(tmp_path, aws):
    lines = {"a": "첫째 줄입니다", "b": "둘째 줄입니다"}
    first = synth(lines, tmp_path / "v")
    assert len(aws()) == 2
    second = synth(lines, tmp_path / "v")
    assert len(aws()) == 2
    assert second == first


@needs_ffmpeg
def test_a_changed_text_or_voice_is_synthesized_again(tmp_path, aws):
    out = tmp_path / "v"
    synth({"a": "첫째 줄입니다", "b": "둘째 줄입니다"}, out)
    synth({"a": "첫째 줄이 바뀝니다", "b": "둘째 줄입니다"}, out)
    assert len(aws()) == 3
    synth({"a": "첫째 줄이 바뀝니다", "b": "둘째 줄입니다"}, out, voice="Jihye")
    assert len(aws()) == 5
    assert aws()[-1]["--voice-id"] == "Jihye"


@needs_ffmpeg
def test_a_missing_audio_file_is_synthesized_again(tmp_path, aws):
    out = tmp_path / "v"
    synth({"a": "첫째 줄입니다"}, out)
    (out / "a.mp3").unlink()
    synth({"a": "첫째 줄입니다"}, out)
    assert len(aws()) == 2 and (out / "a.mp3").exists()


@needs_ffmpeg
def test_a_recorded_file_is_used_as_it_is(tmp_path, aws):
    rec = tmp_path / "mine.mp3"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "sine=duration=1.5", "-ac", "1", str(rec)], check=True)
    result = synth({"a": {"audio": str(rec)}}, tmp_path / "v")
    assert (tmp_path / "v" / result["a"]["file"]).read_bytes() == rec.read_bytes()
    assert abs(result["a"]["seconds"] - 1.5) < 0.1
    assert aws() == []


@needs_ffmpeg
def test_an_empty_line_is_refused(tmp_path, aws):
    with pytest.raises(SystemExit, match="blank"):
        synth({"ok": "좋은 줄입니다", "blank": "   "}, tmp_path / "v")
    assert aws() == []


@needs_ffmpeg
def test_a_line_over_1000_characters_is_refused(tmp_path, aws):
    with pytest.raises(SystemExit, match="long"):
        synth({"long": "가" * 1001}, tmp_path / "v")
    assert aws() == []


@needs_ffmpeg
def test_a_failed_call_stops_with_the_tools_message_and_keeps_what_was_made(tmp_path, aws):
    out = tmp_path / "v"
    with pytest.raises(SystemExit) as e:
        synth({"a": "첫째 줄입니다", "b": "FAIL 줄", "c": "셋째 줄입니다"}, out)
    assert e.value.code not in (0, None)
    assert "AccessDeniedException" in str(e.value)
    saved = json.loads((out / "voice.json").read_text())
    assert list(saved) == ["a"] and (out / "a.mp3").exists()
    assert [c["--text"] for c in aws()] == ["첫째 줄입니다", "FAIL 줄"]  # c was never tried


@needs_ffmpeg
def test_cli_prints_only_the_json_on_stdout(tmp_path, aws):
    lines = tmp_path / "lines.json"
    lines.write_text(json.dumps({"a": "MCP 줄"}, ensure_ascii=False))
    readings = tmp_path / "readings.json"
    readings.write_text(json.dumps({"MCP": "엠씨피"}, ensure_ascii=False))
    proc = subprocess.run([sys.executable, str(SCRIPTS / "edit_demo.py"), "voice", str(lines), "--out", str(tmp_path / "v"),
                           "--readings", str(readings), "--hangul-only", "--region", "us-west-2"],
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)["a"]["spoken"] == "엠씨피 줄"


@needs_ffmpeg
def test_a_text_that_begins_with_a_dash_reaches_the_cli_whole(tmp_path, aws):
    synth({"a": "- 첫째 항목입니다"}, tmp_path / "v")
    assert aws()[0]["--text"] == "- 첫째 항목입니다"


@needs_ffmpeg
def test_quotes_and_a_line_break_are_passed_whole(tmp_path, aws):
    text = '그는 "안녕"이라고 \'말했습니다\'\n다음 줄입니다'
    synth({"a": text}, tmp_path / "v")
    assert aws()[0]["--text"] == text


@needs_ffmpeg
@pytest.mark.parametrize("text", ["file:///etc/hostname", "  fileb://x", "https://example.com/a", "http://example.com"])
def test_a_text_the_cli_would_load_is_refused_before_any_call(tmp_path, aws, text):
    with pytest.raises(SystemExit, match="bad"):
        synth({"ok": "좋은 줄입니다", "bad": text}, tmp_path / "v")
    assert aws() == []


@needs_ffmpeg
def test_a_reading_that_empties_a_line_is_refused(tmp_path, aws):
    with pytest.raises(SystemExit, match="blank"):
        synth({"a": "MCP"}, tmp_path / "v", readings={"MCP": ""})
    assert aws() == []


@needs_ffmpeg
def test_a_value_that_is_not_a_text_or_audio_object_is_refused_with_its_own_message(tmp_path, aws):
    with pytest.raises(SystemExit, match="neither"):
        synth({"a": 5}, tmp_path / "v")
    assert aws() == []


@needs_ffmpeg
@pytest.mark.parametrize("name", ["../x", "a/b", ".hidden", ""])
def test_a_name_that_is_not_a_plain_file_name_is_refused(tmp_path, aws, name):
    with pytest.raises(SystemExit, match="name"):
        synth({name: "한 줄입니다"}, tmp_path / "v")
    assert aws() == []
    assert not (tmp_path / "x.mp3").exists()


@needs_ffmpeg
def test_an_entry_of_a_changed_line_is_dropped_at_once(tmp_path, aws):
    out = tmp_path / "v"
    synth({"a": "첫째 줄입니다", "b": "둘째 줄입니다"}, out)
    with pytest.raises(SystemExit):  # x fails first, so a (changed) is never reached: its old entry must still be gone
        synth({"x": "FAIL 줄", "a": "첫째 줄이 바뀝니다", "b": "둘째 줄입니다"}, out)
    assert list(json.loads((out / "voice.json").read_text())) == ["b"]


@needs_ffmpeg
def test_a_failed_call_on_a_line_with_an_older_file_leaves_neither_file_nor_entry(tmp_path, aws):
    out = tmp_path / "v"
    synth({"a": "첫째 줄입니다"}, out)
    assert (out / "a.mp3").exists()
    with pytest.raises(SystemExit):
        synth({"a": "FAIL 바뀐 줄"}, out)
    assert not (out / "a.mp3").exists()
    assert json.loads((out / "voice.json").read_text()) == {}


@needs_ffmpeg
def test_cli_says_in_one_line_when_a_json_file_is_not_an_object(tmp_path, aws):
    lines = tmp_path / "lines.json"
    lines.write_text('["a"]')
    proc = subprocess.run([sys.executable, str(SCRIPTS / "edit_demo.py"), "voice", str(lines), "--out", str(tmp_path / "v")],
                          capture_output=True, text=True)
    assert proc.returncode != 0 and "JSON object" in proc.stderr and "Traceback" not in proc.stderr
