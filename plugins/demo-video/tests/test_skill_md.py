import json
import re
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
SKILL = PLUGIN / "skills" / "recording-demo-videos"
SKILL_MD = SKILL / "SKILL.md"
SCRIPT_MD = SKILL / "references" / "script.md"


def frontmatter() -> str:
    fm = re.match(r"^---\n(.*?)\n---\n", SKILL_MD.read_text(), re.S)
    assert fm, "missing frontmatter"
    return fm.group(1)


def test_frontmatter_names_the_skill_and_fits_the_spec_limit():
    fm = frontmatter()
    assert "name: recording-demo-videos" in fm
    assert len(fm) <= 1024, f"frontmatter is {len(fm)} chars; the Agent Skills spec caps it at 1024"
    assert re.search(r"description: Use when", fm), "description must start with the triggering condition"
    assert "데모 영상" in fm, "Korean triggers (kept from upstream hi-aws-skills)"


def test_manifest_and_marketplace_agree_on_name():
    """루트 plugin.json 중복본은 두지 않는다(저장소 관례). 마켓플레이스 항목과 이름·경로가 맞아야 한다.

    No root plugin.json duplicate (repo convention). The marketplace entry must match the name and source.
    """
    a = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text())
    assert a["name"] == "demo-video"
    assert not (PLUGIN / "plugin.json").exists()
    market = json.loads((PLUGIN.parents[1] / ".claude-plugin" / "marketplace.json").read_text())
    entry = next(p for p in market["plugins"] if p["name"] == a["name"])
    assert entry["source"] == "./plugins/demo-video"


def test_every_linked_reference_exists_and_the_old_split_is_gone():
    text = SKILL_MD.read_text()
    links = set(re.findall(r"\]\((references/[^)#]+|scripts/[^)#]+)\)", text))
    assert {"references/script.md", "references/reel-manifest.md"} <= links
    missing = sorted(l for l in links if not (SKILL / l).exists())
    assert missing == []
    # 1.2.0 merged story.md + caption-style.md into script.md; a stale file would be read by mistake
    assert not (SKILL / "references" / "story.md").exists()
    assert not (SKILL / "references" / "caption-style.md").exists()


def test_scripts_are_invoked_through_their_interpreter():
    text = SKILL_MD.read_text()
    assert "node scripts/record_demo.mjs" in text and "python3 scripts/edit_demo.py" in text
    assert "python3 scripts/make_cards.py" in text
    assert not re.search(r"(?<![\w/])scripts/edit_demo\.py clip", text.replace("python3 scripts/edit_demo.py", "")), \
        "never call a bundled script by bare path; plugin packagers strip executable bits"


def test_skill_states_the_recording_and_tempo_defaults():
    """1.2.0: output is 1080p; a UI that fits one screen is laid out at 1280x720 and zoomed; clips play at 1.25x."""
    text = SKILL_MD.read_text()
    assert "--layout 1280x720" in text, "the one-screen layout option must be in the record step"
    assert "1.25" in text, "default clip tempo"
    for must in ("speed", "fade_in", ".mov", "re-record"):
        assert must in text, f"SKILL.md lost the lesson keyed by {must!r}"


def test_skill_is_lean():
    """User request 2026-09-26: only what is necessary; over-constraints removed (1.3.0: terminal scenes added, cap raised to 1400)."""
    text = SKILL_MD.read_text()
    words = len(text.split())
    assert words <= 1400, f"SKILL.md is {words} words; 1.1.0 was 2037 and was judged too constrained"
    for residue in ("Laya", "Bedrock", "AgentCore", "Radix", "Settings 탭", "settings tab", "Argument video", "argument video"):
        assert residue not in text, f"project-specific residue {residue!r} in SKILL.md"
    for residue in ("Laya", "Bedrock", "AgentCore", "Registry", "argument video", "Argument video"):
        assert residue not in SCRIPT_MD.read_text(), f"project-specific residue {residue!r} in script.md"


def test_script_reference_defines_cards_and_voice():
    """Intro card = the message and what the demo shows; summary card = take home messages; chapter cards between."""
    ref = SCRIPT_MD.read_text()
    low = ref.lower()
    assert "intro card" in low and "the message" in low and "what the demo shows" in low, "intro card: message + what the demo shows"
    assert "take home" in low or "take-home" in low, "summary card = take home messages"
    assert "chapter card" in low or "간지" in ref, "chapter (간지) cards between chapters"
    for must in ("합니다체", "U+2014", "U+00B7", "U+2192", "45"):
        assert must in ref, f"script.md must state the voice rule keyed by {must!r}"
    assert "describe" in low or "묘사" in ref, "a beat says what the feature does, not what the frame shows"


def test_korean_examples_obey_the_voice_rules():
    """Every Korean example line (outside ✗ bad examples) must itself follow the rules, or the next reel copies it."""
    hangul = re.compile(r"[가-힣]")
    for path in (SCRIPT_MD, SKILL_MD, PLUGIN / "README.md"):
        for n, line in enumerate(path.read_text().splitlines(), 1):
            if not hangul.search(line) or "✗" in line:
                continue
            for ch in ("—", "·", "→"):
                assert ch not in line, f"{path.name}:{n} Korean line uses {ch!r}: {line.strip()}"
            assert "배속)" not in line, f"{path.name}:{n} example carries a speed label: {line.strip()}"


def test_edit_demo_docstring_carries_the_look_constants():
    """caption-style.md is gone; the drawing constants must be readable from `edit_demo.py --help`."""
    code = (SKILL / "scripts" / "edit_demo.py").read_text()
    doc = code.split('"""')[1]
    for token in ("1.25", "58", "34", "h-150", "0x1f6feb"):
        assert token in doc, f"edit_demo.py docstring does not state {token}"
    for token in ("size=58", "BEAT_SIZE = 34", "0x1f6feb", "h-150", "REEL_ENCODE"):
        assert token in code, f"style constant {token} moved out of edit_demo.py"


def test_terminal_helpers_ship_and_reel_is_single_pass():
    """1.3.0: terminal scenes need term.mjs beside the example; the reel default is a one-pass re-encode (QuickTime)."""
    assert (SKILL / "scripts" / "term.mjs").exists() and (SKILL / "scripts" / "terminal.example.mjs").exists()
    code = (SKILL / "scripts" / "edit_demo.py").read_text()
    assert "REEL_ENCODE" in code and '"--copy"' in code, "reel must re-encode by default and keep --copy for the old join"
    assert "lang=ko" in code and "lang=ko" in (SKILL / "scripts" / "make_cards.py").read_text(), "font fallback must ask fontconfig for Korean"


REFERENCE_MD = SKILL / "references" / "voice-and-highlight.md"
MANIFEST_MD = SKILL / "references" / "reel-manifest.md"
README_MD = PLUGIN / "README.md"
POINTER_MD = SKILL / "references" / "pointer.md"


def test_skill_points_to_the_voice_and_highlight_reference():
    """SKILL.md links the reference and has a quick-reference row for each new thing; no project name in either."""
    text = SKILL_MD.read_text()
    assert "](references/voice-and-highlight.md)" in text
    assert REFERENCE_MD.exists()
    for row in ("rec.mark", "\"hold\": true", "python3 scripts/edit_demo.py voice", "python3 scripts/check_demo.py audit"):
        assert row in text, f"SKILL.md has no quick-reference row for {row!r}"
    for name in ("Bedrock", "AgentCore", "hosting hub", "Hosting Hub", "agent-hosting"):
        assert name not in REFERENCE_MD.read_text() and name not in text, f"project name {name!r} in a skill document"


def _script_sources() -> str:
    return "".join((SKILL / "scripts" / f).read_text()
                   for f in ("edit_demo.py", "check_demo.py", "record_demo.mjs", "term.mjs", "pointer.mjs", "frametext.mjs"))


def test_every_option_and_field_the_documents_name_exists_in_the_scripts():
    """The documents pin no wording: each --option and each "field" they name in backticks must exist in the scripts."""
    code = _script_sources()
    docs = REFERENCE_MD.read_text() + MANIFEST_MD.read_text() + SCRIPT_MD.read_text() + POINTER_MD.read_text()
    options = set(re.findall(r"(?<![\w-])(--[a-z][a-z-]+)", docs))
    assert {"--readings", "--hangul-only", "--tolerance", "--plan", "--texts", "--boxes", "--raw", "--copy"} <= options
    assert sorted(o for o in options if o not in code and o != "--help") == [], "an option the documents name is not in the scripts"
    quoted = set(re.findall(r"`\"([a-z_]+)\"", docs))
    # every field the documents list in the first cell of a table row (`image`, `seconds` | ...), quoted or bare
    listed = {n for row in re.findall(r"^\| ([^|]+) \|", docs, re.M) for n in re.findall(r"`\"?([a-z_]+)\"?`", row)}
    names = quoted | listed
    assert {"box", "box_dur", "box_delay", "hold", "voice", "voice_at", "group", "image", "seconds", "voice_gap", "voice_tail", "loudness"} <= names
    assert sorted(n for n in names if f'"{n}"' not in code) == [], "a field the documents name is not in the scripts"


def test_the_default_numbers_the_documents_give_are_the_scripts_constants():
    import importlib.util
    spec = importlib.util.spec_from_file_location("edit_demo", SKILL / "scripts" / "edit_demo.py")
    edit_demo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(edit_demo)
    manifest, ref = MANIFEST_MD.read_text(), REFERENCE_MD.read_text()
    assert float(re.search(r"`voice_gap`[^\n]*default ([0-9.]+)", manifest).group(1)) == edit_demo.VOICE_GAP
    assert float(re.search(r"`voice_tail`[^\n]*default ([0-9.]+)", manifest).group(1)) == edit_demo.VOICE_TAIL
    assert float(re.search(r"`loudness`[^\n]*default (-?[0-9.]+)", manifest).group(1)) == edit_demo.VOICE_LOUDNESS
    assert float(re.search(r"`voice_gap` \(([0-9.]+) s\)", ref).group(1)) == edit_demo.VOICE_GAP
    assert float(re.search(r"`voice_tail` \(([0-9.]+) s\)", ref).group(1)) == edit_demo.VOICE_TAIL
    assert float(re.search(r"[−-]([0-9.]+) LUFS", ref).group(1)) == -edit_demo.VOICE_LOUDNESS
    assert float(re.search(r"a hold over ([0-9.]+) s", ref).group(1)) == edit_demo.WARN_HOLD


def test_the_reference_documents_name_the_new_fields():
    """script.md carries the beat fields, reel-manifest.md the segment and top-level fields."""
    script = SCRIPT_MD.read_text()
    for must in ("box", "box_delay", "box_dur", "hold"):
        assert f"`\"{must}\"" in script or f"`{must}`" in script, f"script.md does not document {must!r}"
    manifest = MANIFEST_MD.read_text()
    for must in ("image", "seconds", "voice", "voice_at", "group", "voice_gap", "voice_tail", "loudness", ".voice.json", "--copy"):
        assert must in manifest, f"reel-manifest.md does not document {must!r}"


def test_the_description_names_the_new_features_in_all_four_places():
    """plugin.json, the marketplace entry, the README and the SKILL.md frontmatter change together."""
    plugin = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text())["description"]
    market = json.loads((PLUGIN.parents[1] / ".claude-plugin" / "marketplace.json").read_text())
    entry = next(p for p in market["plugins"] if p["name"] == "demo-video")["description"]
    places = {"plugin.json": plugin, "marketplace.json": entry, "SKILL.md": frontmatter(), "README.md": README_MD.read_text()}
    for where, text in places.items():
        low = text.lower()
        assert "highlight box" in low or "강조 상자" in text, f"{where} does not name the highlight boxes"
        assert "narrat" in low or "내레이션" in text, f"{where} does not name the narrated reels"


def test_the_readme_states_the_one_new_requirement_and_the_origin():
    readme = README_MD.read_text()
    assert "polly:SynthesizeSpeech" in readme, "the only new requirement: the AWS CLI, for synthesis only"
    assert "2026-11-24" in readme and "check_demo.py" in readme


def test_the_version_is_1_6_0_wherever_it_is_written():
    """The version lives in plugin.json only; CHANGELOG.md, the marketplace entry and the README's origin section name the release."""
    plugin = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text())
    assert plugin["version"] == "1.6.0"
    assert "CHANGELOG.md" in plugin["description"] and " adds " not in plugin["description"], "the history lives in CHANGELOG.md, not the description"
    changelog = (PLUGIN / "CHANGELOG.md").read_text()
    for release in ("1.6.0 (2026-11-28)", "1.5.0 (2026-11-28)", "1.4.0 (2026-11-24)", "1.3.0 (2026-11-09)", "1.2.0 (2026-11-09)"):
        assert f"## {release}" in changelog, f"CHANGELOG.md has no section for {release}"
    market = json.loads((PLUGIN.parents[1] / ".claude-plugin" / "marketplace.json").read_text())
    entry = next(p for p in market["plugins"] if p["name"] == "demo-video")
    assert "version" not in entry and entry["description"].rstrip().endswith("1.6.0.")
    assert market["metadata"]["version"] == "1.0.0", "the marketplace's own version stays"
    assert all(old not in entry["description"] for old in ("1.3.0.", "1.4.0.", "1.5.0."))
    readme = README_MD.read_text()
    for line in (r"^- 1\.6\.0 \(2026-11-28", r"^- 1\.5\.0 \(2026-11-28", r"^- 1\.4\.0 \(2026-11-24"):
        assert re.search(line, readme, re.M), "the README's origin section names each release"
    assert "version" not in frontmatter(), "the skill's frontmatter carries no version"


def test_the_documents_teach_writing_from_the_take():
    """1.5.0: the recorder keeps each frame's text and `brief` turns a take into rows to write from."""
    skill, ref, script = SKILL_MD.read_text(), REFERENCE_MD.read_text(), SCRIPT_MD.read_text()
    assert "python3 scripts/check_demo.py brief" in skill and "--every" in skill and "rec.text" in skill
    for must in ("python3 scripts/check_demo.py brief", "--script", "--every", "--voices", "--rate", "--speed",
                 ".frametext.txt", "rec.text", '`"budget"`', '`"live"`', '`"text_end"`', '`"texts"`', '`"stills"`',
                 "iframe", "canvas", "password"):
        assert must in ref, f"voice-and-highlight.md does not name {must!r}"
    assert "check_demo.py brief" in script, "script.md's working order writes the beats from the brief"
    readme = README_MD.read_text()
    assert "check_demo.py brief" in readme and "frametext" in readme


def test_the_documents_teach_pressing_with_the_pointer():
    """1.6.0: a press is the real mouse under a pointer the video shows; references/pointer.md says how."""
    skill, ref = SKILL_MD.read_text(), POINTER_MD.read_text()
    assert "](references/pointer.md)" in skill and "rec.tap" in skill and "--no-pointer" in skill
    for must in ("rec.tap", "rec.hover", "--no-pointer", "--dialogs", "--backdrop", '`"covered"`', '`"outside"`', '`"same_tab"`',
                 '`"point"`', '`"soft"`', "tap:<key>", "pan", "scroll", "load", "popup", "dialog", "showModal", "iframe", "sticky"):
        assert must in ref, f"pointer.md does not name {must!r}"
    for name in ("Bedrock", "AgentCore", "hosting hub", "Hosting Hub", "agent-hosting"):
        assert name not in ref
    readme = README_MD.read_text()
    assert "--no-pointer" in readme and "rec.tap" in readme
    assert "rec.tap(" in (SKILL / "scripts" / "storyboard.example.mjs").read_text()
    assert "installed again" not in REFERENCE_MD.read_text(), "1.6.0 puts the camera back after a reload by itself"
