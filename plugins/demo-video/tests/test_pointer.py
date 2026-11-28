"""record_demo.mjs on ordinary web sites: the camera's reach and its truth after a scroll or a new page, dialogs and
new tabs, and presses made with the real mouse under a visible pointer. Needs PLAYWRIGHT_ROOT and ffmpeg/ffprobe."""
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
from PIL import Image

PLUGIN = Path(__file__).resolve().parents[1]
SCRIPTS = PLUGIN / "skills" / "recording-demo-videos" / "scripts"
PW_ROOT = os.environ.get("PLAYWRIGHT_ROOT")
needs_playwright = pytest.mark.skipif(PW_ROOT is None or shutil.which("ffmpeg") is None, reason="needs PLAYWRIGHT_ROOT and ffmpeg")
LAYOUTS = pytest.mark.parametrize("layout", ["1920x1080", "1280x720"])
HEAD = "<!doctype html><html><head><meta charset='utf-8'><style>html,body{margin:0;background:#202830;color:#fff;font:20px/30px sans-serif}"
FIRED = ("<script>window.fired=[];window.listen=(id,ev)=>document.getElementById(id).addEventListener(ev,"
         "e=>window.fired.push(id+':'+ev+':'+e.isTrusted));</script>")


def take(tmp_path, pages: dict, storyboard: str, *more) -> tuple[subprocess.CompletedProcess, dict]:
    """Record pages["page.html"] (other pages lie beside it) with a storyboard; returns the run and the camlog."""
    for name, html in pages.items():
        (tmp_path / name).write_text(html)
    (tmp_path / "sb.mjs").write_text(storyboard)
    run = subprocess.run(["node", str(SCRIPTS / "record_demo.mjs"), "--url", (tmp_path / "page.html").as_uri(),
                          "--storyboard", str(tmp_path / "sb.mjs"), "--name", "t", "--out", str(tmp_path / "raw"),
                          "--playwright-root", PW_ROOT, *more], capture_output=True, text=True)
    camlog = tmp_path / "raw" / "t.camlog.json"
    return run, json.loads(camlog.read_text()) if camlog.exists() else {}


def entries(camlog: dict, kind: str) -> list[dict]:
    return [e for e in camlog["log"] if e["kind"] == kind]


def frame(tmp_path, t: float) -> Image.Image:
    png = tmp_path / f"f{t:.2f}.png"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{max(0, t):.2f}", "-i", str(tmp_path / "raw" / "t.webm"),
                    "-frames:v", "1", str(png)], check=True)
    return Image.open(png).convert("RGB")


OPEN = """export default async function storyboard({ page, rec, tap, siteUrl, option }) {
  const fired = () => page.evaluate(() => window.fired.splice(0));
  await page.goto(siteUrl); await page.waitForTimeout(300); await rec.install(); await rec.reset('wide', 'overview'); await rec.sleep(300);
"""


# ---------------------------------------------------------------- the camera reaches the whole page

REACH = {  # content longer than the body's own box, two ways
    "absolute": HEAD + "#far{position:absolute;left:60px;top:2000px}</style></head><body><p>TOP</p><a id='far' href='#x'>Far link</a></body></html>",
    "full-height": HEAD.replace("html,body{margin:0;", "html,body{margin:0;height:100%;") + "section{height:900px}</style></head><body>"
                   "<section>ONE</section><section>TWO</section><section>THREE <a id='far' href='#x'>Far link</a></section></body></html>",
}


@needs_playwright
@LAYOUTS
@pytest.mark.parametrize("shape", sorted(REACH))
def test_the_camera_reaches_content_below_a_short_body(tmp_path, layout, shape):
    run, camlog = take(tmp_path, {"page.html": REACH[shape]}, OPEN + """
  await rec.focus('far', '#far', { pad: 20, kmax: 1 }, 'the far link'); await rec.sleep(1700);
}""", "--layout", layout)
    assert run.returncode == 0, run.stderr
    (shot,) = [e for e in entries(camlog, "shot") if e["key"] == "far"]
    assert shot["camera"]["y"] > 500, "the camera went down the page"
    assert "rect" in shot and "missing" not in shot, "and the frame shows the link"


# ---------------------------------------------------------------- a window scroll becomes the camera's position

ANCHOR = HEAD.replace("html,body{margin:0;", "html,body{margin:0;height:100%;SMOOTH") + "section{height:900px}</style></head><body>" \
    "<nav><a id='toc' href='#s3'>Go to section 3</a></nav><section id='s1'>SECTION ONE</section><section id='s2'>SECTION TWO</section>" \
    "<section id='s3'>SECTION THREE <button id='in3'>in three</button></section><section id='s4'>SECTION FOUR</section></body></html>"
PROBE = """
  rec.note('probe', { scroll: await page.evaluate(() => [window.scrollX, window.scrollY]), cam: await page.evaluate(() => ({ ...window.__cam.state })),
                      live: await page.locator('#in3').boundingBox() });
  await rec.mark('in3', '#in3', 'the button');
}"""


def close(rect, box, slack=2):
    return rect is not None and all(abs(a - b) <= slack for a, b in zip(rect, (box["x"], box["y"], box["width"], box["height"])))


@needs_playwright
@LAYOUTS
@pytest.mark.parametrize("smooth", ["", "scroll-behavior:smooth;"])
def test_an_in_page_anchor_scroll_is_folded_into_the_camera(tmp_path, layout, smooth):
    run, camlog = take(tmp_path, {"page.html": ANCHOR.replace("SMOOTH", smooth)}, OPEN + """
  const b = await page.locator('#toc').boundingBox(); await page.mouse.click(b.x + 5, b.y + 5); await rec.sleep(1500);""" + PROBE,
                       "--layout", layout)
    assert run.returncode == 0, run.stderr
    (probe,) = entries(camlog, "probe")
    assert probe["scroll"] == [0, 0] and probe["cam"]["y"] > 500
    scrolls = [e for e in entries(camlog, "shot") if e["key"] == "scroll"]
    assert len(scrolls) == 1 and scrolls[0]["move"] == 0, "folded once, after the scroll ended"
    (mark,) = entries(camlog, "mark")
    assert close(mark.get("rect"), probe["live"]), "the camera's model is the frame again"
    from test_record_demo import read_frametext
    texts = {(e["kind"], e["key"]): e["text"] for e in read_frametext(tmp_path / "raw" / "t.frametext.txt")}
    assert "SECTION THREE" in texts[("shot", "scroll")] and "SECTION ONE" not in texts[("shot", "scroll")]


@needs_playwright
@LAYOUTS
def test_a_scroll_under_a_zoomed_camera_is_folded_at_its_true_size(tmp_path, layout):
    run, camlog = take(tmp_path, {"page.html": ANCHOR.replace("SMOOTH", "")}, OPEN + """
  await rec.region('zoom', 0, 1600, 640, 360, { pad: 0, kmax: 2 }); await rec.sleep(1700);    // section 3 starts at about y 1830
  await page.evaluate(() => window.scrollTo(0, 300)); await rec.sleep(500);""" + PROBE, "--layout", layout)
    assert run.returncode == 0, run.stderr
    (probe,) = entries(camlog, "probe")
    assert probe["scroll"] == [0, 0] and probe["cam"]["k"] == 2
    assert close(entries(camlog, "mark")[0].get("rect"), probe["live"])


# ---------------------------------------------------------------- the camera is back on every new page

PAGE2 = HEAD + "</style></head><body><h1 id='p2' style='color:#c8d0d8;display:inline-block'>PAGE TWO</h1><iframe id='inner' srcdoc='<p>inner</p>'></iframe></body></html>"
LINKS = HEAD + "</style></head><body><p id='one'>PAGE ONE</p><a id='go' href='page2.html?token=abc#frag'>Docs</a></body></html>"


@needs_playwright
@LAYOUTS
def test_a_new_document_gets_the_camera_back(tmp_path, layout):
    run, camlog = take(tmp_path, {"page.html": LINKS, "page2.html": PAGE2}, OPEN + """
  await Promise.all([page.waitForNavigation({ waitUntil: 'load' }), tap(page.locator('#go'))]);
  await page.waitForSelector('#p2'); await rec.sleep(300);
  rec.note('probe', { camera: await page.evaluate(() => typeof window.__cam), inner: await page.frames()[1].evaluate(() => typeof window.__cam) });
  await rec.focus('heading', '#p2', { pad: 20, kmax: 2 }, 'page two'); await rec.sleep(1700);
}""", "--layout", layout)
    assert run.returncode == 0, run.stderr
    (probe,) = entries(camlog, "probe")
    assert probe == {**probe, "camera": "object", "inner": "undefined"}, "the top document has the camera, an iframe has none"
    (load,) = entries(camlog, "load")
    assert load["url"].endswith("/page2.html") and "token" not in load["url"] and "soft" not in load
    heading = [e for e in entries(camlog, "shot") if e["key"] == "heading"][0]
    assert heading["camera"]["k"] > 1 and "rect" in heading
    from test_record_demo import read_frametext
    kinds = [(e["kind"], e["key"]) for e in read_frametext(tmp_path / "raw" / "t.frametext.txt")]
    assert kinds == [("shot", "wide"), ("shot", "heading")], "no leave for a view that a new page replaced"


@needs_playwright
def test_a_swapped_body_is_a_new_page(tmp_path):
    run, camlog = take(tmp_path, {"page.html": LINKS}, OPEN + """
  await rec.region('zoom', 0, 0, 640, 360, { pad: 0, kmax: 2 }); await rec.sleep(1700);
  await page.evaluate(() => { const b = document.createElement('body'); b.innerHTML = '<h1 id="p2">SWAPPED</h1>'; document.body.replaceWith(b); });
  await rec.sleep(400);
  rec.note('probe', { cam: await page.evaluate(() => ({ ...window.__cam.state })) });
  await rec.focus('heading', '#p2', { pad: 20, kmax: 2 }); await rec.sleep(1700);
}""")
    assert run.returncode == 0, run.stderr
    assert entries(camlog, "probe")[0]["cam"] == {"x": 0, "y": 0, "k": 1}
    assert [e.get("soft") for e in entries(camlog, "load")] == [True]
    assert "rect" in [e for e in entries(camlog, "shot") if e["key"] == "heading"][0]


# ---------------------------------------------------------------- dialogs are answered, new tabs closed, both written down

DIALOG = HEAD + "</style></head><body><button id='ask' onclick=\"document.getElementById('out').textContent=confirm('Really?')?'CONFIRMED':'CANCELLED'\">Delete</button>" \
    "<button id='pop' onclick=\"window.open('page2.html?x=1')\">Open</button><p id='out'></p></body></html>"
ASK = OPEN + """
  LISTEN
  await tap(page.locator('#ask')); await rec.sleep(300);
  rec.note('probe', { out: await page.locator('#out').textContent() });
}"""


@needs_playwright
@pytest.mark.parametrize("option, listen, out, logged", [
    ((), "", "CONFIRMED", True), (("--dialogs", "dismiss"), "", "CANCELLED", True), (("--dialogs", "leave"), "", "CANCELLED", False),
    ((), "page.on('dialog', d => d.dismiss());", "CANCELLED", True)])
def test_a_dialog_is_answered_and_written_down(tmp_path, option, listen, out, logged):
    run, camlog = take(tmp_path, {"page.html": DIALOG}, ASK.replace("LISTEN", listen), *option)
    assert run.returncode == 0 and camlog["ok"] is True and camlog["errors"] == [], run.stderr
    assert entries(camlog, "probe")[0]["out"] == out
    assert [(e["type"], e["message"]) for e in entries(camlog, "dialog")] == ([("confirm", "Really?")] if logged else [])
    assert ("dialog (confirm)" in run.stderr) is logged


@needs_playwright
@pytest.mark.parametrize("listen, tabs", [("", 1), ("page.on('popup', () => {});", 2)])
def test_a_new_tab_is_closed_unless_the_storyboard_wants_it(tmp_path, listen, tabs):
    run, camlog = take(tmp_path, {"page.html": DIALOG, "page2.html": PAGE2}, OPEN + listen + """
  await tap(page.locator('#pop')); await rec.sleep(800);
  rec.note('probe', { tabs: page.context().pages().length });
}""")
    assert run.returncode == 0, run.stderr
    assert entries(camlog, "probe")[0]["tabs"] == tabs
    (popup,) = entries(camlog, "popup")
    assert popup["url"].endswith("/page2.html") and "x=1" not in popup["url"]
    assert ("a take records one tab" in run.stderr) is (tabs == 1)


# ---------------------------------------------------------------- the pointer, and a press with the real mouse

CLICK = HEAD + """body{color:#c8d0d8}button,a{font:inherit;padding:8px 16px;background:#30404f;color:#c8d0d8;border:0}
#panel{position:absolute;left:60px;top:60px;width:700px;height:260px;background:#283440;padding:20px}
.menu{position:relative;display:inline-block}.menu .items{display:none;position:absolute;left:0;top:30px;background:#30404f}.menu:hover .items{display:block}
dialog{background:#d0d0d0;color:#000;border:0;padding:40px}</style></head><body>
<div id="panel"><button id="pd">pointerdown only</button> <button id="md">mousedown only</button> <button id="ck">click only</button> <button id="open">Open dialog</button>
<div class="menu" id="menu">Hover menu<div class="items"><a id="item" href="#i">Menu item</a></div></div>
<a id="wrap" href="#w">A long link text that is meant to wrap over two lines when its container is narrow enough for that to happen here and there</a></div>
<dialog id="dlg"><p>Really?</p><button id="yes">Yes</button></dialog>""" + FIRED + """<script>
listen('pd','pointerdown');listen('md','mousedown');listen('ck','click');listen('item','click');listen('wrap','click');listen('yes','pointerdown');
document.getElementById('open').addEventListener('click',()=>document.getElementById('dlg').showModal());</script></body></html>"""
BLUE = lambda p: p[2] > 180 and p[0] < 90 and 60 < p[1] < 160           # the ring, #1f6feb  # noqa: E731
WHITE = lambda p: min(p) > 235                                          # the pointer; no page of these tests has text this white  # noqa: E731


def near(image, point, hit, radius):
    x0, y0 = int(point[0]), int(point[1])
    return sum(1 for y in range(max(0, y0 - radius), min(image.height, y0 + radius)) for x in range(max(0, x0 - radius), min(image.width, x0 + radius))
               if hit(image.getpixel((x, y))))


@needs_playwright
@LAYOUTS
def test_a_tap_is_a_real_press_under_a_pointer_the_video_shows(tmp_path, layout):
    run, camlog = take(tmp_path, {"page.html": CLICK}, OPEN + """
  await rec.tap(page.locator('#pd'), { key: 'pd', label: 'the first button' });
  await tap(page.locator('#md'));
  await rec.hover(page.locator('#menu'), { key: 'menu' });
  rec.note('menu', { shown: await page.evaluate(() => getComputedStyle(document.querySelector('.menu .items')).display) });
  await rec.tap(page.locator('#item'), { key: 'item' });
  await rec.tap(page.locator('#wrap'), { key: 'wrap' });
  await rec.focus('panel', '#panel', { pad: 20, kmax: 2 }, 'the panel');
  await rec.tap(page.locator('#ck'), { key: 'ck' });                     // called while the camera moves
  await rec.reset('wide2'); await rec.sleep(1700);
  await rec.tap(page.locator('#open')); await rec.sleep(300);
  await rec.tap(page.locator('#yes'), { key: 'yes' });
  rec.note('fired', { fired: await fired(), pointer: await page.evaluate(() => document.getElementById('__demo_pointer')?.textContent) });
  await rec.sleep(600);
}""", "--layout", layout)
    assert run.returncode == 0, run.stderr
    (end,) = entries(camlog, "fired")
    assert end["pointer"] == "", "the pointer is on the page and adds no text to it"
    assert end["fired"] == ["pd:pointerdown:true", "md:mousedown:true", "item:click:true", "wrap:click:true", "ck:click:true", "yes:pointerdown:true"]
    assert entries(camlog, "menu")[0]["shown"] == "block", "the real mouse opened the hover menu"
    taps = entries(camlog, "tap")
    assert [t.get("key") for t in taps] == ["pd", None, "item", "wrap", "ck", None, "yes"]
    for t in taps:
        x, y, w, h = t["rect"]
        assert all(isinstance(v, int) for v in t["rect"]) and x <= t["point"][0] <= x + w and y <= t["point"][1] <= y + h
    assert taps[0]["label"] == "the first button" and taps[0]["text"] == "pointerdown only"
    assert [(e["key"], "rect" in e) for e in entries(camlog, "hover")] == [("menu", True)]
    panel = [e for e in entries(camlog, "shot") if e["key"] == "panel"][0]
    assert taps[4]["t"] >= panel["t"] + 1.4, "the press waited for the camera to stop"
    # the video: the ring and the pointer are at the press, also over the modal dialog; the pointer keeps its size under the zoom
    for t in (taps[0], taps[4], taps[6]):
        shown = frame(tmp_path, t["t"] - 0.05)
        assert near(shown, t["point"], BLUE, 40) > 20, f"no press mark at {t.get('key')}"
        assert near(shown, t["point"], WHITE, 40) > 40, f"no pointer at {t.get('key')}"
    wide, zoomed = (near(frame(tmp_path, t["t"] - 0.05), t["point"], WHITE, 45) for t in (taps[0], taps[4]))
    assert 0.6 < zoomed / wide < 1.6, "the pointer is as large under a 2x camera"


@needs_playwright
def test_no_pointer_keeps_the_old_press(tmp_path):
    run, camlog = take(tmp_path, {"page.html": CLICK}, OPEN + """
  await tap(page.locator('#pd')); await tap(page.locator('#ck')); await rec.hover(page.locator('#menu'));
  rec.note('fired', { fired: await fired(), pointer: await page.evaluate(() => !!document.getElementById('__demo_pointer')) });
}""", "--no-pointer")
    assert run.returncode == 0, run.stderr
    assert entries(camlog, "fired")[0] == {**entries(camlog, "fired")[0], "fired": ["ck:click:false"], "pointer": False}
    assert entries(camlog, "tap") == [] and entries(camlog, "hover") == []
    assert "hover does nothing without the pointer" in run.stderr


@needs_playwright
def test_a_tap_before_the_camera_is_installed_still_presses(tmp_path):
    run, camlog = take(tmp_path, {"page.html": CLICK}, """export default async function storyboard({ page, rec, siteUrl }) {
  await page.goto(siteUrl); await page.waitForTimeout(300);
  await rec.tap(page.locator('#pd'), { key: 'early' });
  rec.note('fired', { fired: await page.evaluate(() => window.fired.splice(0)) });
}""")
    assert run.returncode == 0, run.stderr
    assert entries(camlog, "fired")[0]["fired"] == ["pd:pointerdown:true"] and entries(camlog, "tap")[0]["key"] == "early"


# ---------------------------------------------------------------- targets the frame does not show, or that something covers

HARD = HEAD + """button,a{font:inherit;padding:8px 16px;background:#30404f;color:#fff;border:0}
#far{position:absolute;left:60px;top:2000px}
#pane{position:absolute;left:60px;top:80px;width:400px;height:120px;overflow:auto}#pane div{height:40px}
#overlay{position:absolute;left:560px;top:80px;width:400px;height:80px;background:rgba(255,0,0,.05)}
#covered{position:absolute;left:580px;top:100px}
#off{position:absolute;left:-600px;top:300px}
#dodge{position:absolute;left:60px;top:300px}</style></head><body>
<a id="far" href="#far">Far link</a>
<div id="pane"></div><button id="covered">Covered</button><div id="overlay"></div><button id="off">Off the page</button><button id="dodge">Dodge</button>""" + FIRED + """<script>
const pane=document.getElementById('pane');for(let i=0;i<30;i++){const d=document.createElement('div');d.innerHTML=i===25?'<button id="row25">Row 25</button>':'row '+i;pane.appendChild(d)}
for(const id of ['far','row25','covered','overlay','off','dodge'])listen(id,'click');
document.getElementById('dodge').addEventListener('mouseenter',e=>{e.target.style.left='700px'});</script></body></html>"""


@needs_playwright
@LAYOUTS
def test_a_target_the_frame_does_not_show_is_brought_in_or_pressed_as_an_event(tmp_path, layout):
    run, camlog = take(tmp_path, {"page.html": HARD}, OPEN + """
  await rec.tap(page.locator('#row25'), { key: 'row' });
  await rec.tap(page.locator('#covered'), { key: 'covered' });
  await rec.tap(page.locator('#off'), { key: 'off' });
  await rec.tap(page.locator('#dodge'), { key: 'dodge' });
  await rec.tap(page.locator('#far'), { key: 'far', label: 'the far link' });
  rec.note('fired', { fired: await fired(), pane: await page.evaluate(() => document.getElementById('pane').scrollTop) });
}""", "--layout", layout)
    assert run.returncode == 0 and camlog["ok"] is True, run.stderr
    (end,) = entries(camlog, "fired")
    assert end["fired"] == ["row25:click:true", "covered:click:false", "off:click:false", "dodge:click:false", "far:click:true"]
    assert end["pane"] > 0, "the pane was scrolled to its row"
    taps = {t["key"]: t for t in entries(camlog, "tap")}
    assert "overlay" in taps["covered"]["covered"] and "covered" in taps["dodge"] and taps["off"]["outside"] is True
    assert all(flag not in taps[k] for k in ("row", "far") for flag in ("covered", "outside"))
    for words in ("tap covered: covered by", "tap off: outside the frame", "tap dodge: covered by"):
        assert words in run.stderr, words
    (pan,) = [e for e in entries(camlog, "shot") if e["key"] == "pan"]
    assert pan["move"] == 0.8 and pan["label"] == "the far link" and pan["t"] < taps["far"]["t"] - 0.8
    assert taps["far"]["point"][1] < 1080, "pressed inside the frame, after the camera went there"


CUT = HEAD + """button{font:inherit;background:#30404f;color:#fff;border:0}
#big{position:absolute;left:300px;top:600px;width:300px;height:120px}#end{position:absolute;left:0;top:2990px}</style></head><body>
<button id="big">A tall button</button><p id="end">END</p>""" + FIRED + "<script>listen('big','click')</script></body></html>"


@needs_playwright
def test_a_button_the_frame_cuts_is_brought_in_whole_before_it_is_pressed(tmp_path):
    """Found on a real app (2026-11-28): the press point lay 42 px inside the frame, so no camera move came, and the
    button was pressed with its top cut off by the frame's edge."""
    run, camlog = take(tmp_path, {"page.html": CUT}, OPEN + """
  await rec.region('cut', 0, 610, 1920, 1080, { pad: 0, kmax: 1 }, 'the frame cuts the button: its top 10 px are above it');
  await rec.sleep(1700);
  rec.note('before', { rect: await page.evaluate(() => window.__cam.rect('#big')) });
  await rec.tap(page.locator('#big'), { key: 'big' });
  rec.note('fired', { fired: await fired() });
}""")
    assert run.returncode == 0 and camlog["ok"] is True, run.stderr
    (cut,) = [e for e in entries(camlog, "shot") if e["key"] == "cut"]
    assert cut["camera"] == {"x": 0, "y": 610, "k": 1}, "the test's own premise: the button's centre is 50 px inside the frame"
    (tap,) = entries(camlog, "tap")
    assert entries(camlog, "fired")[0]["fired"] == ["big:click:true"] and "covered" not in tap and "outside" not in tap
    x, y, w, h = tap["rect"]
    assert (w, h) == (300, 120), "the frame shows the whole button when it is pressed"
    assert y >= 8 and y + h <= 1080 - 8, "clear of the frame's edges"
    assert [e["key"] for e in entries(camlog, "shot")] == ["wide", "cut", "pan"], "the camera went to it"


@needs_playwright
@LAYOUTS
@pytest.mark.parametrize("shape", sorted(REACH))
def test_a_far_link_is_pressed_on_both_shapes_of_a_long_page(tmp_path, layout, shape):
    run, camlog = take(tmp_path, {"page.html": REACH[shape]}, OPEN + """
  await rec.tap(page.locator('#far'), { key: 'far' });
}""", "--layout", layout)
    assert run.returncode == 0, run.stderr
    (tap,) = entries(camlog, "tap")
    assert "covered" not in tap and "outside" not in tap and 0 <= tap["point"][1] <= 1080
    assert [e["move"] for e in entries(camlog, "shot") if e["key"] == "pan"] == [0.8]


# ---------------------------------------------------------------- links: the same tab, and the pointer on the next page

TABS = HEAD + "a{padding:8px 16px;background:#30404f;color:#fff}</style></head><body><p>PAGE ONE</p>" \
    "<a id='blank' href='page2.html' target='_blank'>New tab link</a> <a id='go' href='page2.html'>Same tab link</a></body></html>"


@needs_playwright
@pytest.mark.parametrize("link, same_tab", [("#blank", True), ("#go", False)])
def test_a_link_opens_in_the_same_tab_and_the_pointer_comes_back(tmp_path, link, same_tab):
    run, camlog = take(tmp_path, {"page.html": TABS, "page2.html": PAGE2}, OPEN + f"""
  await Promise.all([page.waitForNavigation({{ waitUntil: 'load' }}), rec.tap(page.locator('{link}'), {{ key: 'link' }})]);
  await page.waitForSelector('#p2'); await rec.sleep(400);
  rec.note('probe', {{ url: page.url(), tabs: page.context().pages().length, at: await page.evaluate(() => window.__demoPointer.at()) }});
  await rec.reset('two', 'page two'); await rec.sleep(600);
}}""")
    assert run.returncode == 0 and camlog["ok"] is True and camlog["errors"] == [], run.stderr
    (probe,) = entries(camlog, "probe")
    (tap,) = entries(camlog, "tap")
    assert probe["url"].endswith("/page2.html") and probe["tabs"] == 1
    assert tap.get("same_tab", False) is same_tab and entries(camlog, "popup") == []
    assert probe["at"] is not None and all(abs(a - b) <= 2 for a, b in zip(probe["at"], tap["point"])), "the pointer is where it pressed"
    assert len(entries(camlog, "load")) == 1
    assert near(frame(tmp_path, [e for e in entries(camlog, "shot") if e["key"] == "two"][0]["t"] + 0.3), tap["point"], WHITE, 40) > 40


# ---------------------------------------------------------------- the camera leaves the page's own background alone

LIGHT = "<!doctype html><html><head><meta charset='utf-8'><style>html,body{margin:0}p{margin:40px;color:#1c1e21;font:20px/30px sans-serif}</style></head>" \
        "<body><p>Dark text on the browser's own white: the page sets no background at all</p></body></html>"


@needs_playwright
@pytest.mark.parametrize("option, light", [((), True), (("--backdrop", "#0b0f14"), False)])
def test_the_camera_does_not_repaint_the_pages_background(tmp_path, option, light):
    """Found on a real site, 2026-11-28: the camera gave <html> a dark background (#0b0f14, since the fork), and a light
    page that sets none of its own showed dark text on dark. --backdrop <colour> paints it as before."""
    run, camlog = take(tmp_path, {"page.html": LIGHT}, OPEN + """
  await rec.sleep(700);
  rec.note('probe', { html: await page.evaluate(() => getComputedStyle(document.documentElement).backgroundColor) });
}""", *option)
    assert run.returncode == 0, run.stderr
    assert entries(camlog, "probe")[0]["html"] == ("rgba(0, 0, 0, 0)" if light else "rgb(11, 15, 20)")
    corner = frame(tmp_path, entries(camlog, "probe")[0]["t"]).getpixel((1800, 1000))
    assert (min(corner) > 240) if light else (max(corner) < 40), corner


# ---------------------------------------------------------------- content parked off the side is not part of the page

PARKED = HEAD + "#skip{position:absolute;left:100%;top:16px;width:200px}#far{position:absolute;left:1500px;top:2000px}#right{position:absolute;left:1600px;top:20px}</style></head>" \
    "<body><a id='skip' href='#main'>Skip to main content</a><button id='right'>Theme</button><p id='main'>TOP</p><a id='far' href='#x'>Far link</a></body></html>"


@needs_playwright
@LAYOUTS
def test_content_parked_off_the_side_does_not_let_the_camera_slide_sideways(tmp_path, layout):
    """Found on a real site, 2026-11-28: a skip link parked at left: 100% made the page 'wider' than the frame, and a pan
    to a button near the right edge slid the whole page left, cutting its sidebar and showing the parked link."""
    run, camlog = take(tmp_path, {"page.html": PARKED}, OPEN + """
  await rec.tap(page.locator('#far'), { key: 'far' });
  await rec.tap(page.locator('#right'), { key: 'right' });
  await rec.focus('right', '#right', { pad: 20, kmax: 1 }, 'the button on the right'); await rec.sleep(1500);
}""", "--layout", layout)
    assert run.returncode == 0, run.stderr
    shots = [e for e in entries(camlog, "shot") if e["key"] in ("pan", "right")]
    assert len(shots) == 3 and all(e["camera"]["x"] == 0 for e in shots), [e["camera"] for e in shots]
    assert shots[0]["camera"]["y"] > 500, "the pan still goes down the page"


# ---------------------------------------------------------------- found by the final review (2026-11-28)

MOVES = HEAD + "button{position:absolute;left:100px;top:100px;width:220px;height:60px;font:inherit}</style></head><body>" \
    "<button id='under'>Delete everything</button><button id='item'>Menu item</button>" + FIRED + \
    "<script>listen('under','click');listen('item','click');" \
    "document.getElementById('item').addEventListener('mouseenter',e=>setTimeout(()=>{e.target.style.left='600px'},120),{once:true});</script></body></html>"


@needs_playwright
def test_a_target_that_moves_away_after_the_pointer_arrived_is_not_pressed_through(tmp_path):
    """The element left 120 ms after the mouse came; what lay beneath it must not get the press."""
    run, camlog = take(tmp_path, {"page.html": MOVES}, OPEN + """
  await rec.tap(page.locator('#item'), { key: 'item' }); await rec.sleep(300);
  rec.note('fired', { fired: await fired() });
}""")
    assert run.returncode == 0, run.stderr
    assert entries(camlog, "fired")[0]["fired"] == ["item:click:false"], "the click went to the target, as the event"
    assert "under" in entries(camlog, "tap")[0]["covered"]


FRAMED = HEAD + "iframe{position:absolute;left:200px;top:150px;width:400px;height:200px;border:0;background:#30404f}</style></head><body>" \
    "<iframe id='f' srcdoc=\"<button id='in' style='position:absolute;left:100px;top:60px;font:20px sans-serif'>Inside</button>" \
    "<script>document.getElementById('in').addEventListener('pointerdown',e=>parent.fired.push('in:pointerdown:'+e.isTrusted))</script>\"></iframe>" \
    + FIRED + "</body></html>"


@needs_playwright
@LAYOUTS
def test_a_button_inside_an_iframe_is_pressed_where_the_frame_shows_it(tmp_path, layout):
    run, camlog = take(tmp_path, {"page.html": FRAMED}, OPEN + """
  await rec.tap(page.frameLocator('#f').locator('#in'), { key: 'wide' });
  await rec.focus('frame', '#f', { pad: 20, kmax: 2 }, 'the embedded page');
  await rec.tap(page.frameLocator('#f').locator('#in'), { key: 'zoomed' });
  rec.note('fired', { fired: await fired() });
}""", "--layout", layout)
    assert run.returncode == 0, run.stderr
    assert entries(camlog, "fired")[0]["fired"] == ["in:pointerdown:true", "in:pointerdown:true"]
    wide, zoomed = entries(camlog, "tap")
    assert all(flag not in t for t in (wide, zoomed) for flag in ("covered", "outside"))
    k = [e for e in entries(camlog, "shot") if e["key"] == "frame"][0]["camera"]["k"]
    assert zoomed["rect"][2] == pytest.approx(wide["rect"][2] * k, rel=0.15), "the rect is the button as the frame shows it"


@needs_playwright
def test_a_tap_right_after_a_zooming_shot_scrolls_its_row_in_by_the_right_amount(tmp_path):
    run, camlog = take(tmp_path, {"page.html": HARD}, OPEN + """
  await rec.focus('pane', '#pane', { pad: 20, kmax: 2 }, 'the list');
  await rec.tap(page.locator('#row25'), { key: 'row' });
  rec.note('fired', { fired: await fired() });
}""")
    assert run.returncode == 0, run.stderr
    assert entries(camlog, "fired")[0]["fired"] == ["row25:click:true"]
    assert "covered" not in entries(camlog, "tap")[0] and [e for e in entries(camlog, "shot") if e["key"] == "pan"] == []


@needs_playwright
def test_a_target_that_hides_before_the_press_does_not_stop_the_take(tmp_path):
    run, camlog = take(tmp_path, {"page.html": CLICK}, OPEN + """
  await rec.focus('panel', '#panel', { pad: 20, kmax: 2 }, 'the panel');
  await page.evaluate(() => { setTimeout(() => { document.getElementById('ck').style.display = 'none'; }, 300); });
  await rec.tap(page.locator('#ck'), { key: 'gone' });
  rec.note('fired', { fired: await fired() });
}""")
    assert run.returncode == 0 and camlog["ok"] is True, run.stderr
    assert entries(camlog, "fired")[0]["fired"] == ["ck:click:false"]
    assert entries(camlog, "tap")[0]["outside"] is True and "tap gone:" in run.stderr


@needs_playwright
def test_a_tab_the_storyboard_opens_itself_is_left_alone(tmp_path):
    run, camlog = take(tmp_path, {"page.html": LINKS}, OPEN + """
  const other = await page.context().newPage();
  await other.goto(siteUrl); await other.waitForTimeout(400);
  rec.note('probe', { url: other.url() });
  await other.close();
}""")
    assert run.returncode == 0, run.stderr
    assert entries(camlog, "probe")[0]["url"].endswith("/page.html") and entries(camlog, "popup") == []


SLOW2 = HEAD + "</style></head><body><h1 id='p2' style='color:#c8d0d8;display:inline-block'>PAGE TWO</h1><img src='slow.png'></body></html>"


@needs_playwright
def test_a_new_page_is_known_before_its_last_picture_has_loaded(tmp_path):
    """The camera is back when the document is ready; the camlog and the frame text must know the page by then too."""
    run, camlog = take(tmp_path, {"page.html": LINKS.replace("page2.html?token=abc#frag", "page2.html"), "page2.html": SLOW2}, OPEN + """
  await page.route('**/slow.png', route => { setTimeout(() => route.abort().catch(() => {}), 2500); });
  await rec.tap(page.locator('#go'), { key: 'go' });
  await page.waitForSelector('#p2');
  await rec.reset('two', 'page two'); await rec.sleep(3000);
}""")
    assert run.returncode == 0, run.stderr
    two = [e for e in entries(camlog, "shot") if e["key"] == "two"][0]
    assert [e["t"] < two["t"] for e in entries(camlog, "load")] == [True]
    from test_record_demo import read_frametext
    assert [(e["kind"], e["key"]) for e in read_frametext(tmp_path / "raw" / "t.frametext.txt")] == [("shot", "wide"), ("shot", "two")]


@needs_playwright
def test_a_window_that_keeps_scrolling_is_one_view_not_one_per_scroll(tmp_path):
    run, camlog = take(tmp_path, {"page.html": ANCHOR.replace("SMOOTH", "")}, OPEN + """
  await page.evaluate(() => { let n = 0; const id = setInterval(() => { window.scrollBy(0, 60); if (++n >= 20) clearInterval(id); }, 100); });
  await rec.sleep(3200);
  rec.note('probe', { cam: await page.evaluate(() => ({ ...window.__cam.state })) });
}""")
    assert run.returncode == 0, run.stderr
    scrolls = [e for e in entries(camlog, "shot") if e["key"] == "scroll"]
    assert len(scrolls) == 1 and scrolls[0]["camera"]["y"] == entries(camlog, "probe")[0]["cam"]["y"] == 1200
    from test_record_demo import read_frametext
    kept = [e for e in read_frametext(tmp_path / "raw" / "t.frametext.txt") if e["key"] == "scroll"]
    # 1200 px down the frame shows the end of section 2 (its heading is above the frame) and the top of section 3
    assert len(kept) == 1 and "SECTION THREE" in kept[0]["text"] and "Go to section 3" not in kept[0]["text"], "the text of where the scrolling ended"


STRICT = HEAD.replace("<meta charset='utf-8'>", "<meta charset='utf-8'><meta http-equiv='Content-Security-Policy' content=\"require-trusted-types-for 'script'; style-src 'none'\">") \
    + "</style></head><body><button id='b' style='position:absolute;left:300px;top:200px'>Press</button>" + FIRED + "<script>listen('b','pointerdown')</script></body></html>"


@needs_playwright
def test_a_site_with_a_strict_content_policy_still_gets_the_camera_and_the_pointer(tmp_path):
    run, camlog = take(tmp_path, {"page.html": STRICT}, OPEN + """
  await rec.tap(page.locator('#b'), { key: 'b' });
  rec.note('probe', { fired: await fired(), origin: await page.evaluate(() => getComputedStyle(document.body).transformOrigin),
                      pointer: await page.evaluate(() => !!document.querySelector('#__demo_pointer path')) });
}""")
    assert run.returncode == 0 and camlog["ok"] is True, run.stderr
    probe = entries(camlog, "probe")[0]
    assert probe["fired"] == ["b:pointerdown:true"] and probe["origin"] == "0px 0px" and probe["pointer"] is True


QUIRKS = "<html><head><meta charset='utf-8'><style>body{margin:0;background:#202830;color:#fff}section{height:1010px}</style></head>" \
         "<body><section>ONE</section><section>TWO</section><section id='three'>THREE</section></body></html>"


@needs_playwright
def test_a_page_without_a_doctype_keeps_its_size_under_the_camera(tmp_path):
    run, camlog = take(tmp_path, {"page.html": QUIRKS}, OPEN + """
  const h = () => page.evaluate(() => window.__cam.pageSize().h);
  const wide = await h();
  await rec.region('zoom', 0, 0, 640, 360, { pad: 0, kmax: 2 }); await rec.sleep(1700);
  rec.note('probe', { wide, zoomed: await h(), mode: await page.evaluate(() => document.compatMode) });
}""")
    assert run.returncode == 0, run.stderr
    probe = entries(camlog, "probe")[0]
    assert probe["mode"] == "BackCompat" and probe["wide"] == probe["zoomed"] == 3030
