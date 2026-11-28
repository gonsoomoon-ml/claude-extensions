"""record_demo.mjs: the --layout option (one-screen UI laid out at 1280x720, zoomed to fill 1080p).

The smoke test needs Playwright: set PLAYWRIGHT_ROOT to a directory whose node_modules has playwright
(with chromium installed); otherwise it is skipped. Needs ffmpeg/ffprobe.
"""
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1]
SCRIPTS = PLUGIN / "skills" / "recording-demo-videos" / "scripts"
PW_ROOT = os.environ.get("PLAYWRIGHT_ROOT")

PAGE = """<!doctype html><html><head><style>
html,body{margin:0;height:100%;background:#ff0000}
body{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:8px;padding:8px;box-sizing:border-box;font:24px sans-serif}
.card{background:#fff;padding:12px;height:120px}
</style></head><body>
<script>for(let i=0;i<12;i++){document.write('<div class="card" id="c'+i+'">card '+i+'</div>')}</script>
</body></html>"""

STORYBOARD = """export default async function storyboard({ page, rec, siteUrl }) {
  await page.goto(siteUrl);
  await page.waitForTimeout(300);
  await rec.install();
  await rec.reset('wide', 'overview');
  await rec.sleep(1200);
  await rec.focus('card', '#c5', { pad: 12, kmax: 2 }, 'one card');
  await rec.sleep(1800);
  rec.note('done');
}"""


def test_node_scripts_parse():
    for f in ("record_demo.mjs", "storyboard.example.mjs", "frametext.mjs"):
        subprocess.run(["node", "--check", str(SCRIPTS / f)], check=True)


def test_recorder_warns_when_a_selector_matches_nothing():
    src = (SCRIPTS / "record_demo.mjs").read_text()
    assert "missing" in src and "console.warn" in src, "a silent no-op focus cost a whole take; warn and mark the camlog"


def test_recorder_offers_the_layout_option_in_its_usage():
    src = (SCRIPTS / "record_demo.mjs").read_text()
    assert "--layout" in src and "1280x720" in src


def test_layout_must_keep_the_16_9_aspect():
    r = subprocess.run(["node", str(SCRIPTS / "record_demo.mjs"), "--url", "http://x", "--storyboard", "none.mjs",
                        "--layout", "1280x800"], capture_output=True, text=True)
    assert r.returncode == 2 and "16:9" in r.stderr, r.stderr


def frame_pixels(video: Path, t: float, tmp: Path) -> "list[tuple[int, int, int]]":
    from PIL import Image
    png = tmp / f"f{t}.png"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", str(video), "-frames:v", "1", str(png)], check=True)
    im = Image.open(png).convert("RGB")
    w, h = im.size
    assert (w, h) == (1920, 1080)
    return [im.getpixel((w - 3, h - 3)), im.getpixel((w - 3, 3)), im.getpixel((w // 2, h // 2))]


@pytest.mark.skipif(PW_ROOT is None or shutil.which("ffmpeg") is None, reason="needs PLAYWRIGHT_ROOT and ffmpeg")
def test_layout_1280x720_fills_the_1080p_frame_and_the_camera_still_lands(tmp_path):
    (tmp_path / "page.html").write_text(PAGE)
    (tmp_path / "sb.mjs").write_text(STORYBOARD)
    r = subprocess.run(["node", str(SCRIPTS / "record_demo.mjs"), "--url", (tmp_path / "page.html").as_uri(),
                        "--storyboard", str(tmp_path / "sb.mjs"), "--name", "t", "--out", str(tmp_path / "raw"),
                        "--playwright-root", PW_ROOT, "--layout", "1280x720"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    log = json.loads((tmp_path / "raw" / "t.camlog.json").read_text())
    shots = [e for e in log["log"] if e["kind"] == "shot"]
    assert [s["key"] for s in shots] == ["wide", "card"] and not any(s.get("missing") for s in shots)
    assert log["layout"] == "1280x720"
    # wide shot: the page background reaches the bottom-right corner (no grey pad from a small viewport)
    wide_t = shots[0]["t"] + 0.8
    corner, top_right, _ = frame_pixels(tmp_path / "raw" / "t.webm", wide_t, tmp_path)
    for px in (corner, top_right):
        assert px[0] > 180 and px[1] < 80 and px[2] < 80, f"frame edge is not the page background: {px}"
    # focus shot: the camera zoomed in (k > 1) and the frame centre is the white card, not red background
    cam = shots[1]["camera"]
    assert cam and cam["k"] > 1.5, cam
    _, _, centre = frame_pixels(tmp_path / "raw" / "t.webm", shots[1]["t"] + 1.6, tmp_path)
    assert min(centre) > 200, f"centre of the focus shot is not the card: {centre}"


def test_recorder_offers_mark_and_logs_rects():
    """A shot's camlog entry says where its target is on the frame, and a mark says it without moving the camera."""
    recorder, term = (SCRIPTS / "record_demo.mjs").read_text(), (SCRIPTS / "term.mjs").read_text()
    assert "mark(" in recorder and "rect" in recorder
    assert "markRows" in term
    for f in ("record_demo.mjs", "term.mjs"):
        subprocess.run(["node", "--check", str(SCRIPTS / f)], check=True)


MARK_PAGE = """<!doctype html><html><head><style>
html,body{margin:0;height:100%;background:#202830}
.block{position:absolute}
</style></head><body>
<div id="red" class="block" style="left:300px;top:200px;width:240px;height:120px;background:#ff0000"></div>
<div id="green" class="block" style="left:560px;top:250px;width:100px;height:80px;background:#00ff00"></div>
<div id="far" class="block" style="left:1100px;top:600px;width:60px;height:60px;background:#0000ff"></div>
</body></html>"""

MARK_STORYBOARD = """export default async function storyboard({ page, rec, siteUrl }) {
  await page.goto(siteUrl);
  await page.waitForTimeout(300);
  await rec.install();
  await rec.reset('wide', 'overview');
  await rec.sleep(1000);
  const cam = () => page.evaluate(() => ({ ...window.__cam.state }));
  await rec.focus('red', '#red', { pad: 24 }, 'the red block');
  rec.note('probe', { when: 'after focus', cam: await cam() });
  await rec.mark('during', '#green', 'green while the camera moves');   // less than 1.4 s after the shot
  rec.note('probe', { when: 'after mark', cam: await cam() });
  await rec.sleep(2200);
  await rec.mark('after', '#green', 'green once the camera has stopped');
  await rec.mark('absent', '#nothing-here', 'matches nothing');
  await rec.mark('outside', '#far', 'a block the camera does not show');
  await rec.mark('swapped', '#green', {}, 'options where the label goes');   // mark takes its label third
  await rec.region('area', 300, 200, 360, 130, { pad: 20, dur: 0.6 }, 'a region');
  await rec.sleep(2200);
  rec.note('done');
}"""


def bounds(video: Path, t: float, tmp: Path, colour: str) -> "tuple[int, int, int, int]":
    """The box (x0, y0, x1, y1) of the pixels of a pure red or green block in the video frame at t."""
    from PIL import Image
    png = tmp / f"b{colour}{t}.png"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", str(video), "-frames:v", "1", str(png)], check=True)
    im = Image.open(png).convert("RGB")
    hit = (lambda p: p[0] > 200 and p[1] < 70 and p[2] < 70) if colour == "red" else (lambda p: p[1] > 200 and p[0] < 70 and p[2] < 70)
    xs, ys = zip(*[(x, y) for y in range(0, im.height, 2) for x in range(0, im.width, 2) if hit(im.getpixel((x, y)))])
    return min(xs), min(ys), max(xs) + 2, max(ys) + 2


def assert_encloses(rect, box, slack=4):
    assert rect is not None and len(rect) == 4 and all(isinstance(v, int) for v in rect), rect
    x, y, w, h = rect
    assert (x, y, x + w, y + h) == pytest.approx(box, abs=slack), (rect, box)


@pytest.mark.skipif(PW_ROOT is None or shutil.which("ffmpeg") is None, reason="needs PLAYWRIGHT_ROOT and ffmpeg")
@pytest.mark.parametrize("layout", ["1920x1080", "1280x720"])
def test_camlog_rects_enclose_what_the_frame_shows(tmp_path, layout):
    (tmp_path / "page.html").write_text(MARK_PAGE)
    (tmp_path / "sb.mjs").write_text(MARK_STORYBOARD)
    r = subprocess.run(["node", str(SCRIPTS / "record_demo.mjs"), "--url", (tmp_path / "page.html").as_uri(),
                        "--storyboard", str(tmp_path / "sb.mjs"), "--name", "m", "--out", str(tmp_path / "raw"),
                        "--playwright-root", PW_ROOT, "--layout", layout], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    log = json.loads((tmp_path / "raw" / "m.camlog.json").read_text())["log"]
    video = tmp_path / "raw" / "m.webm"
    by_key = {e["key"]: e for e in log if "key" in e}
    assert "rect" not in by_key["wide"], "a reset points at nothing"
    # the camera at rest after the focus: the red block is where the shot's rect says
    red = by_key["red"]
    assert red["kind"] == "shot" and red["camera"]["k"] > 1.5
    assert_encloses(red["rect"], bounds(video, red["t"] + 2.0, tmp_path, "red"))
    # a mark made while the camera is still moving points at where the block will be, and moves nothing
    during, after = by_key["during"], by_key["after"]
    assert during["kind"] == "mark" and during["label"] == "green while the camera moves"
    assert_encloses(during["rect"], bounds(video, red["t"] + 2.0, tmp_path, "green"))
    assert after["rect"] == during["rect"], "the same block once the move is over"
    before_mark, after_mark = [e["cam"] for e in log if e["kind"] == "probe"]
    assert before_mark == after_mark == red["camera"], "a mark leaves the camera where the shot put it"
    # a selector that matches nothing is said so; a block outside the frame has no rect; a region maps its rectangle
    assert by_key["absent"]["missing"] is True and "rect" not in by_key["absent"]
    assert by_key["outside"]["kind"] == "mark" and "rect" not in by_key["outside"] and "missing" not in by_key["outside"]
    assert "matched nothing" in r.stderr
    area = by_key["area"]
    assert area["kind"] == "shot"
    r0, g0 = bounds(video, area["t"] + 2.0, tmp_path, "red"), bounds(video, area["t"] + 2.0, tmp_path, "green")
    assert_encloses(area["rect"], (r0[0], r0[1], g0[2], g0[3]))   # the region's rectangle holds both blocks, edge to edge
    # an index in the label's place is a number, not page code: the mark is missing, with no browser error
    swapped = by_key["swapped"]
    assert swapped["kind"] == "mark" and swapped["missing"] is True and "error" not in swapped, swapped
    # a shot of its own move length says so, for the clip step's camera check; one of the default length does not
    assert area["move"] == 0.6 and "move" not in red and "move" not in by_key["wide"]


ROWS_PAGE = """<!doctype html><html><head><style>
html,body{margin:0;height:100%;background:#202830}
.xterm-rows{position:absolute;left:100px;top:80px;width:600px;font:20px/30px monospace}
.xterm-rows > div{height:30px;white-space:pre}
.xterm-rows > div.hot{background:#00ff00;color:#00ff00}
</style></head><body><div class="xterm-rows">
<div>one</div><div class="hot">first</div><div class="hot">second</div><div class="hot">last</div><div>five</div>
</div></body></html>"""

ROWS_STORYBOARD = """import { markRows, zoomRows } from %r;
export default async function storyboard({ page, rec, siteUrl }) {
  await page.goto(siteUrl);
  await page.waitForTimeout(300);
  await rec.install();
  await rec.reset('wide', 'overview');
  await rec.sleep(800);
  await markRows(rec, page, 'rows', 'first', 'last', 'three rows');
  await markRows(rec, page, 'nowhere', 'not on screen', 'x', 'absent');
  await rec.sleep(800);
  await zoomRows(rec, page, 'zoom', 'first', 'last', { pad: 40 }, 'the rows, zoomed');
  await rec.sleep(2000);
  await markRows(rec, page, 'zoomed', 'first', 'last', 'three rows, zoomed');
  await rec.sleep(1200);
}"""


@pytest.mark.skipif(PW_ROOT is None or shutil.which("ffmpeg") is None, reason="needs PLAYWRIGHT_ROOT and ffmpeg")
@pytest.mark.parametrize("layout, wide", [("1920x1080", [100, 110, 600, 90]), ("1280x720", [150, 165, 900, 135])])
def test_mark_rows_logs_the_rows_rectangle(tmp_path, layout, wide):
    """markRows says where the rows are on the frame as exactly as rec.mark does, wide and after zoomRows, at both
    layouts; zoomRows frames those rows."""
    (tmp_path / "page.html").write_text(ROWS_PAGE)
    (tmp_path / "sb.mjs").write_text(ROWS_STORYBOARD % (SCRIPTS / "term.mjs").as_uri())
    r = subprocess.run(["node", str(SCRIPTS / "record_demo.mjs"), "--url", (tmp_path / "page.html").as_uri(),
                        "--storyboard", str(tmp_path / "sb.mjs"), "--name", "r", "--out", str(tmp_path / "raw"),
                        "--playwright-root", PW_ROOT, "--layout", layout], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    log = json.loads((tmp_path / "raw" / "r.camlog.json").read_text())["log"]
    video = tmp_path / "raw" / "r.webm"
    by_key = {e["key"]: e for e in log if "key" in e}
    rows, nowhere, zoom, zoomed = by_key["rows"], by_key["nowhere"], by_key["zoom"], by_key["zoomed"]
    assert rows["kind"] == "mark" and rows["rect"] == wide, "rows 2 to 4 of the block at 100,80 (30 px rows), times the zoom"
    assert_encloses(rows["rect"], bounds(video, rows["t"] + 0.3, tmp_path, "green"))
    assert nowhere["kind"] == "mark" and nowhere["missing"] is True and "rect" not in nowhere
    # zoomRows aims at the rows, and its shot's rect and a mark after the move are where the frame shows them
    assert zoom["kind"] == "shot" and zoom["camera"]["k"] > 1.2
    at_rest = bounds(video, zoom["t"] + 2.0, tmp_path, "green")
    assert_encloses(zoom["rect"], at_rest)
    assert_encloses(zoomed["rect"], at_rest)
    assert_encloses(zoomed["rect"], bounds(video, zoomed["t"] + 0.3, tmp_path, "green"))
    # a mark of rows keeps the rows' own text; rows that are not on the screen keep none
    texts = {(e["kind"], e["key"]): e["text"] for e in read_frametext(tmp_path / "raw" / "r.frametext.txt")}
    assert texts[("mark", "rows")] == "first\nsecond\nlast"
    assert ("mark", "nowhere") not in texts


MARGIN_PAGE = """<!doctype html><html><head><style>
html,body{background:#202830}
</style></head><body>
<div style="height:180px"></div>
<div id="red" style="margin-left:280px;width:240px;height:120px;background:#ff0000"></div>
</body></html>"""

MARGIN_STORYBOARD = """export default async function storyboard({ page, rec, siteUrl }) {
  await page.goto(siteUrl);
  await page.waitForTimeout(300);
  await rec.install();
  await rec.reset('wide', 'overview');
  await rec.sleep(1000);
  await rec.focus('red', '#red', { pad: 24 }, 'the red block');
  await rec.sleep(2200);
  await rec.mark('after', '#red', 'the red block once the camera has stopped');
  await rec.mark('bad', '#red[', 'a selector that is not CSS');
  await rec.sleep(800);
  await rec.reset('back', 'overview again');
  await rec.sleep(1600);
  await rec.region('area', 288, 188, 240, 120, { pad: 24 }, 'the red block by its page coordinates');
  await rec.sleep(2200);
  // a camera move of the storyboard's own, with every page call answered 0.3 s late
  const evaluate = page.evaluate;
  page.evaluate = async (...args) => { const v = await evaluate.apply(page, args); await new Promise(r => setTimeout(r, 300)); return v; };
  await rec.shot('pan', 'window.__cam.apply(0, 0, 1.2, 0.8)', 'a camera move of its own');
  delete page.evaluate;
  rec.note('probe', { lastShot: rec.lastShot });
  await rec.sleep(1600);
}"""


@pytest.mark.skipif(PW_ROOT is None or shutil.which("ffmpeg") is None, reason="needs PLAYWRIGHT_ROOT and ffmpeg")
@pytest.mark.parametrize("layout", ["1920x1080", "1280x720"])
def test_rects_hold_on_a_page_whose_body_has_the_default_margin(tmp_path, layout):
    """The body's transform turns around the body's own box, 8 px in from the page's corner on an unstyled page: a
    shot's rect and a mark's rect are still where the frame shows the block."""
    (tmp_path / "page.html").write_text(MARGIN_PAGE)
    (tmp_path / "sb.mjs").write_text(MARGIN_STORYBOARD)
    r = subprocess.run(["node", str(SCRIPTS / "record_demo.mjs"), "--url", (tmp_path / "page.html").as_uri(),
                        "--storyboard", str(tmp_path / "sb.mjs"), "--name", "g", "--out", str(tmp_path / "raw"),
                        "--playwright-root", PW_ROOT, "--layout", layout], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    log = json.loads((tmp_path / "raw" / "g.camlog.json").read_text())["log"]
    video = tmp_path / "raw" / "g.webm"
    by_key = {e["key"]: e for e in log if "key" in e}
    red, after, area = by_key["red"], by_key["after"], by_key["area"]
    assert red["kind"] == "shot" and red["camera"]["k"] > 1.5
    assert_encloses(red["rect"], bounds(video, red["t"] + 2.0, tmp_path, "red"))
    assert after["kind"] == "mark"
    assert_encloses(after["rect"], bounds(video, after["t"] + 0.3, tmp_path, "red"))
    x, y, w, h = after["rect"]
    assert_encloses(red["rect"], (x, y, x + w, y + h))   # the shot and the mark agree on the same block
    # a region's numbers are page coordinates: the block's own (the body's 8 px margin, then the block's offsets)
    assert area["kind"] == "shot" and area["camera"] == red["camera"]
    assert_encloses(area["rect"], bounds(video, area["t"] + 2.0, tmp_path, "red"))
    # a selector that is not CSS: the mark is missing, and the camlog and the warning keep the browser's words
    bad = by_key["bad"]
    assert bad["kind"] == "mark" and bad["missing"] is True and "rect" not in bad
    assert "not a valid selector" in bad["error"] and "not a valid selector" in r.stderr
    # a move the storyboard makes itself points at nothing, and its time is the moment the move was made
    pan, (probe,) = by_key["pan"], [e for e in log if e["kind"] == "probe"]
    assert pan["camera"]["k"] == 1.2 and "rect" not in pan, "only focus and region shots carry a rect"
    assert pan["t"] == pytest.approx(probe["lastShot"], abs=0.006)
    assert pan["move"] == 0.8, "a move of its own length, made with the camera's apply"


# ---------------------------------------------------------------- the text each frame shows (1.5.0)

def test_recorder_keeps_the_frame_text():
    recorder = (SCRIPTS / "record_demo.mjs").read_text()
    for must in ("frameText", "elementText", "async text(", ".frametext.txt", "./frametext.mjs"):
        assert must in recorder, must
    assert ".texts.txt" not in recorder, "a storyboard's own text file is not the recorder's"
    assert "rec.text(" in (SCRIPTS / "storyboard.example.mjs").read_text()


def read_frametext(path):
    """The checker's own reader, so the test reads the file as `brief` will."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("check_demo", SCRIPTS / "check_demo.py")
    check_demo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(check_demo)
    return check_demo.read_frametext(path)


def record(tmp_path, page: str, storyboard: str, *more) -> subprocess.CompletedProcess:
    (tmp_path / "page.html").write_text(page)
    (tmp_path / "sb.mjs").write_text(storyboard)
    return subprocess.run(["node", str(SCRIPTS / "record_demo.mjs"), "--url", (tmp_path / "page.html").as_uri(),
                           "--storyboard", str(tmp_path / "sb.mjs"), "--name", "t", "--out", str(tmp_path / "raw"),
                           "--playwright-root", PW_ROOT, *more], capture_output=True, text=True)


TEXT_PAGE = """<!doctype html><html><head><style>
html,body{margin:0;height:100%;background:#202830;color:#fff;font:20px/30px sans-serif}
.abs{position:absolute}
#panel{left:60px;top:60px;width:420px;height:300px;background:#30404f}
#scroller,#big{height:30px;overflow:hidden}
.xterm-rows{left:60px;top:400px;width:500px;font:20px/30px monospace;white-space:pre}
#outside{left:1000px;top:600px;width:200px;height:40px}
</style></head><body>
<div id="panel" class="abs">
<div id="title">INSIDE-ALPHA</div>
<div id="scroller"><div>VISIBLE-ROW</div><div>CLIPPED-ROW</div></div>
<div><input id="q" value="typed-query"><input type="password" value="secret-pw"></div>
<div style="display:none">HIDDEN-TEXT</div><div style="visibility:hidden">INVISIBLE-TEXT</div>
<div id="late"></div><div id="big"></div>
</div>
<div class="abs xterm-rows"><div><span>foo</span><span style="font-weight:bold">bar</span><span> baz</span></div></div>
<div id="outside" class="abs">OUTSIDE-OMEGA</div>
<script>const big=document.getElementById('big');for(let i=0;i<3000;i++){const d=document.createElement('div');d.textContent='ROW-'+i;big.appendChild(d)}</script>
</body></html>"""

TEXT_STORYBOARD = """import fs from 'node:fs'; import path from 'node:path';
export default async function storyboard({ page, rec, siteUrl, option }) {
  fs.writeFileSync(path.join(option('--out', 'raw'), 't.texts.txt'), 'OWN\\n');
  await page.goto(siteUrl); await page.waitForTimeout(300);
  await rec.text('early');                      // no camera yet: no entry, no error
  await rec.install();
  await rec.reset('wide', 'overview');
  await rec.sleep(600);
  await rec.focus('panel', '#panel', { pad: 20, kmax: 2 }, 'the panel');
  await rec.mark('title', '#title', 'the title');
  await rec.sleep(1800);
  await page.evaluate(() => { document.querySelector('#late').textContent = 'LATE-RESULT'; });
  await rec.text('now');
  await page.evaluate(() => { document.querySelector('#late').textContent = 'LATER-RESULT'; });
  const ms = await page.evaluate(() => { const t = performance.now(); window.__cam.frameText(); return performance.now() - t; });
  rec.note('timing', { ms });
  await rec.reset('wide2', 'overview again');
  await rec.sleep(1600);
  await page.goto(siteUrl); await page.waitForTimeout(300);   // a reload takes the camera away
  await rec.text('gone');                                     // no camera: no entry, the take goes on
}"""


@pytest.mark.skipif(PW_ROOT is None or shutil.which("ffmpeg") is None, reason="needs PLAYWRIGHT_ROOT and ffmpeg")
@pytest.mark.parametrize("layout", ["1920x1080", "1280x720"])
def test_frame_text_holds_what_the_frame_shows_and_nothing_else(tmp_path, layout):
    r = record(tmp_path, TEXT_PAGE, TEXT_STORYBOARD, "--layout", layout)
    assert r.returncode == 0, r.stderr
    raw = tmp_path / "raw"
    e = read_frametext(raw / "t.frametext.txt")
    assert [(x["kind"], x["key"]) for x in e] == [("shot", "wide"), ("shot", "panel"), ("mark", "title"),
                                                  ("text", "now"), ("leave", "panel"), ("shot", "wide2")]
    wide, panel, title, now, leave, wide2 = (x["text"] for x in e)
    for s in ("INSIDE-ALPHA", "OUTSIDE-OMEGA", "VISIBLE-ROW", "typed-query", "foobar baz", "ROW-0"):
        assert s in wide, s
    for s in ("CLIPPED-ROW", "HIDDEN-TEXT", "INVISIBLE-TEXT", "secret-pw", "ROW-2999"):
        assert s not in wide, s
    assert "INSIDE-ALPHA" in panel and "typed-query" in panel
    assert "OUTSIDE-OMEGA" not in panel and "LATE-RESULT" not in panel and "secret-pw" not in panel
    assert title == "INSIDE-ALPHA"
    assert "LATE-RESULT" in now and "LATER-RESULT" in leave
    assert "LATER-RESULT" in wide2 and "OUTSIDE-OMEGA" in wide2
    assert (raw / "t.texts.txt").read_text() == "OWN\n", "the storyboard's own file is untouched"
    camlog = json.loads((raw / "t.camlog.json").read_text())
    assert camlog["ok"] is True
    shots = {x["key"]: x["t"] for x in camlog["log"] if x["kind"] == "shot"}
    assert e[1]["t"] == shots["panel"], "a shot's text carries the shot's own time"
    (timing,) = [x for x in camlog["log"] if x["kind"] == "timing"]
    assert timing["ms"] < 300, "one capture on a page of 3,000 text nodes"


@pytest.mark.skipif(PW_ROOT is None or shutil.which("ffmpeg") is None, reason="needs PLAYWRIGHT_ROOT and ffmpeg")
def test_a_take_that_fails_still_writes_its_frame_text(tmp_path):
    r = record(tmp_path, TEXT_PAGE, """export default async function storyboard({ page, rec, siteUrl }) {
  await page.goto(siteUrl); await page.waitForTimeout(300); await rec.install();
  await rec.reset('wide', 'overview');
  throw new Error('the storyboard stops here');
}""")
    assert r.returncode == 1
    assert [(x["kind"], x["key"]) for x in read_frametext(tmp_path / "raw" / "t.frametext.txt")] == [("shot", "wide")]


POPOVER_PAGE = """<!doctype html><html><head><style>
html,body{margin:0;height:100%;background:#202830;color:#fff;font:20px/30px sans-serif}
#shell{height:60px;overflow:hidden}
#fixed{position:fixed;left:100px;top:200px}
#abs{position:absolute;left:100px;top:300px}
#box{position:relative;height:40px;overflow:hidden}
#inner{position:absolute;left:0;top:80px}
#mixed{position:absolute;left:100px;top:500px;line-height:60px}
</style></head><body>
<div id="shell">SHELL-ROW
<div id="fixed">FIXED-POPOVER</div>
<div id="abs">ABS-POPOVER</div>
<div id="box"><div id="inner">ABS-CLIPPED</div></div>
</div>
<div id="mixed"><span style="font-size:14px">Queued</span> <span style="font-size:40px">1,204</span> <span style="font-size:14px">Done</span></div>
</body></html>"""


@pytest.mark.skipif(PW_ROOT is None or shutil.which("ffmpeg") is None, reason="needs PLAYWRIGHT_ROOT and ffmpeg")
def test_frame_text_keeps_a_popover_outside_its_overflow_parent_and_a_line_of_mixed_sizes(tmp_path):
    """Final review 2026-11-28: an overflow box cuts only what is laid out in it; a big number between small labels is one row."""
    r = record(tmp_path, POPOVER_PAGE, """export default async function storyboard({ page, rec, siteUrl }) {
  await page.goto(siteUrl); await page.waitForTimeout(300); await rec.install();
  await rec.reset('status panel', 'overview');
  await rec.sleep(500);
}""")
    assert r.returncode == 0, r.stderr
    (shot,) = read_frametext(tmp_path / "raw" / "t.frametext.txt")
    assert shot["key"] == "status_panel"
    for s in ("SHELL-ROW", "FIXED-POPOVER", "ABS-POPOVER", "Queued 1,204 Done"):
        assert s in shot["text"], (s, shot["text"])
    assert "ABS-CLIPPED" not in shot["text"], "cut by the box it is positioned in"
