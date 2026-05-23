"""Deck Agent Team — orchestrator.

Generalized from the M1 module's `agents/orchestrator.py`. The orchestrator
itself does NO LLM calls — it renders PNGs, extracts text, prepares a handoff
bundle for critic dispatch by the parent Claude Code session, and applies
[x]-marked mechanical patches when invoked in --apply mode.

Configuration (in priority order):
  1. CLI flags
  2. Environment variables (DECK_AGENT_*)
  3. Built-in defaults

Required configuration to run:
  --target <pptx>             (or DECK_AGENT_TARGET) — required for review mode
  --build-script <py>         (or DECK_AGENT_BUILD_SCRIPT)
  --mockup <md>               (or DECK_AGENT_MOCKUP_MD)

Optional:
  --reports-dir <dir>         (or DECK_AGENT_REPORTS_DIR; default: ./reports)
  --preview-dir <dir>         (or DECK_AGENT_PREVIEW_DIR; default: /tmp/<stem>_preview)
  --qa-validator <py>         (or DECK_AGENT_QA_VALIDATOR; optional Phase-1 validator)
  --claude-md <md>            (or DECK_AGENT_CLAUDE_MD; project-level CLAUDE.md)
  --extractors-dir <dir>      (or DECK_AGENT_EXTRACTORS_DIR; default: <plugin_dir>/extractors)
  --prompts-dir <dir>         (or DECK_AGENT_PROMPTS_DIR; default: <plugin_dir>/prompts)

See SKILL.md for the full architecture.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


PLUGIN_DIR = Path(__file__).resolve().parent
DEFAULT_EXTRACTORS = PLUGIN_DIR / "extractors"
DEFAULT_PROMPTS = PLUGIN_DIR / "prompts"


def _env_path(name: str, default: Path | None = None) -> Path | None:
    val = os.environ.get(name)
    if val:
        return Path(val).expanduser().resolve()
    return default


# ---------------------------------------------------------------------------
# Stage 1 — render PNGs (idempotent)
# ---------------------------------------------------------------------------

def render_previews(pptx_path: Path, preview_dir: Path,
                    force: bool = False) -> list[Path]:
    """Run libreoffice → PDF → PNG. Returns sorted list of slide-*.png."""
    preview_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = preview_dir / (pptx_path.stem + ".pdf")
    existing = sorted(preview_dir.glob("slide-*.png"))
    if existing and not force:
        return existing

    for old in preview_dir.glob("slide-*.png"):
        old.unlink()
    if pdf_path.exists():
        pdf_path.unlink()

    subprocess.run(
        ["libreoffice", "--headless", "--convert-to", "pdf",
         "--outdir", str(preview_dir), str(pptx_path)],
        check=True, capture_output=True,
    )
    subprocess.run(
        ["pdftoppm", "-r", "110", str(pdf_path), "slide", "-png"],
        check=True, cwd=preview_dir, capture_output=True,
    )
    return sorted(preview_dir.glob("slide-*.png"))


# ---------------------------------------------------------------------------
# Stage 2 — extract slide text (for Critic B)
# ---------------------------------------------------------------------------

def extract_text_per_slide(pptx_path: Path) -> dict[int, list[str]]:
    """Use python-pptx to dump visible text per slide."""
    from pptx import Presentation
    prs = Presentation(str(pptx_path))
    out: dict[int, list[str]] = {}
    for i, slide in enumerate(prs.slides, 1):
        lines: list[str] = []
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            text = shape.text_frame.text.strip()
            if text:
                lines.append(text)
        out[i] = lines
    return out


# ---------------------------------------------------------------------------
# Stage 2.5 — extract canonical mockup text (for Critic B)
# ---------------------------------------------------------------------------

def extract_canonical_mockup(mockup_md: Path,
                             extractors_dir: Path,
                             pptx_slide_count: int) -> dict[int, list[str]]:
    """Parse mockup md and align to PPTX 1-indexed slide IDs.

    Mockup uses 0-indexed `#N` headers (with possible `.5` extras and `★`).
    PPTX is 1-indexed. We pair the first `pptx_slide_count` mockup sections
    in document order to PPTX slides 1..N. Sub-sections (e.g. `#3.5`) and
    later sections are ignored — the deck under review is the source of
    truth for which slides exist.
    """
    sys.path.insert(0, str(extractors_dir))
    from mockup_parser import parse_mockup  # noqa: E402

    raw = parse_mockup(mockup_md)
    ordered_ids = sorted(raw.keys(), key=lambda x: float(x))
    aligned: dict[int, list[str]] = {}
    for pptx_idx in range(1, pptx_slide_count + 1):
        if pptx_idx - 1 < len(ordered_ids):
            mockup_id = ordered_ids[pptx_idx - 1]
            aligned[pptx_idx] = raw[mockup_id]
        else:
            aligned[pptx_idx] = []
    return aligned


# ---------------------------------------------------------------------------
# Stage 3 — run Phase-1 QA (optional)
# ---------------------------------------------------------------------------

def run_qa_phase1(pptx_path: Path, qa_validator: Path | None) -> str:
    if qa_validator is None or not qa_validator.exists():
        return "(qa_validator not configured — skipping Phase-1)"
    res = subprocess.run(
        ["python3", str(qa_validator), str(pptx_path)],
        capture_output=True, text=True,
    )
    return res.stdout + (("\n[stderr]\n" + res.stderr) if res.stderr else "")


# ---------------------------------------------------------------------------
# Stage 4 — write handoff bundle for Agent dispatch
# ---------------------------------------------------------------------------

def write_handoff(target_pptx: Path,
                  mockup: Path,
                  build_script: Path,
                  claude_md: Path | None,
                  prompts_dir: Path,
                  png_paths: list[Path],
                  extracted_text: dict[int, list[str]],
                  canonical_text: dict[int, list[str]],
                  qa_output: str,
                  out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    bundle = {
        "target_pptx": str(target_pptx),
        "mockup_md": str(mockup),
        "build_script": str(build_script),
        "claude_md": str(claude_md) if claude_md else None,
        "slide_pngs": [str(p) for p in png_paths],
        "slide_count": len(png_paths),
        "extracted_text": {str(k): v for k, v in extracted_text.items()},
        "canonical_text": {str(k): v for k, v in canonical_text.items()},
        "qa_phase1_output": qa_output,
        "prompts": {
            "visual": str(prompts_dir / "critic_visual.md"),
            "content": str(prompts_dir / "critic_accuracy.md"),
            "cognitive_on_demand": str(prompts_dir / "critic_cognitive.md"),
            "compliance_on_demand": str(prompts_dir / "critic_compliance.md"),
            "synthesizer": str(prompts_dir / "synthesizer.md"),
        },
    }
    bundle_path = out_dir / "handoff.json"
    bundle_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2))
    return bundle_path


def write_runner_readme(handoff_path: Path, out_dir: Path) -> Path:
    """Human-readable instructions for the in-session dispatcher."""
    readme = out_dir / "RUN.md"
    readme.write_text(f"""# Agent Dispatch Instructions

Handoff bundle: `{handoff_path}`

Inside Claude Code, dispatch the 2 active critics **in parallel** (single
message, two Agent tool calls), then run the synthesizer.

The active critics (`visual`, `content`) are both ground-truth-anchored:
visual judges the rendered PNGs, content diffs against canonical mockup
text. The `cognitive` and `compliance` prompt files remain in the plugin's
`prompts/` directory for on-demand invocation when a structural change
warrants a deeper review — they are NOT dispatched by default.

## Step 1 — Parallel critics

For each critic, call the Agent tool with:
- `subagent_type`: `general-purpose`
- `description`: e.g. "Critic A — visual quality"
- `prompt`: contents of the critic's prompt md file +
  the relevant subset of `handoff.json` inlined.

Each agent must return a JSON array (`Issue[]`).

## Step 2 — Synthesizer

After both critics return, call one more Agent with:
- `subagent_type`: `general-purpose`
- `description`: "Synthesizer — consolidate critic reports"
- `prompt`: contents of `synthesizer.md` + the 2 returned arrays under
  `reports.visual`, `reports.content`.

## Step 3 — Save report

Save the synthesizer's markdown output to:
`{out_dir / "report.md"}`

The human marks `[x]` on items to apply, then runs:
```
python3 <plugin>/orchestrator.py --apply {out_dir / "report.md"}
```
""")
    return readme


# ---------------------------------------------------------------------------
# Apply mode — parse report and apply [x] patches
# ---------------------------------------------------------------------------

PATCH_RE = re.compile(
    r"###\s*\[(?P<check>[ xX])\][^\n]*\n\n"
    r"\*\*Why\*\*:[^\n]*\n\n"
    r"\*\*Patch\*\*\s*\(`(?P<file>[^`:]+):(?P<lstart>\d+)-(?P<lend>\d+)`\):\n"
    r"```diff\n(?P<body>.*?)\n```",
    re.DOTALL,
)

MECHANICAL_HEADING_RE = re.compile(
    r"(###\s*\[)( |x|X)(\][^\n]*\n\n"
    r"\*\*Why\*\*:[^\n]*\n\n"
    r"\*\*Patch\*\*\s*\(`[^`]+`\):)",
    re.DOTALL,
)


def parse_report(report_path: Path) -> list[dict[str, Any]]:
    text = report_path.read_text()
    out = []
    for m in PATCH_RE.finditer(text):
        if m["check"].lower() != "x":
            continue
        body = m["body"]
        old_lines = [l[2:] for l in body.splitlines() if l.startswith("- ")]
        new_lines = [l[2:] for l in body.splitlines() if l.startswith("+ ")]
        out.append({
            "file": m["file"].strip(),
            "old": "\n".join(old_lines),
            "new": "\n".join(new_lines),
        })
    return out


def auto_mark_mechanical(report_path: Path) -> int:
    """Flip [ ] → [x] for every issue with a mechanical Patch block."""
    text = report_path.read_text()
    flipped = 0

    def replace(match: re.Match) -> str:
        nonlocal flipped
        prefix, mark, rest = match.group(1), match.group(2), match.group(3)
        if mark == " ":
            flipped += 1
            return f"{prefix}x{rest}"
        return match.group(0)

    new_text = MECHANICAL_HEADING_RE.sub(replace, text)
    if flipped:
        report_path.write_text(new_text)
    return flipped


def apply_patches(patches: list[dict[str, Any]], project_root: Path) -> list[str]:
    """Apply via simple string replace. Returns list of files modified.

    Patch file paths may be relative — resolved against `project_root`.
    """
    modified: list[str] = []
    for p in patches:
        path = Path(p["file"])
        if not path.is_absolute():
            path = project_root / path
        src = path.read_text()
        if p["old"] not in src:
            print(f"  skip {path}: old text not found", file=sys.stderr)
            continue
        if src.count(p["old"]) > 1:
            print(f"  skip {path}: old text matches >1 location, ambiguous",
                  file=sys.stderr)
            continue
        path.write_text(src.replace(p["old"], p["new"], 1))
        modified.append(str(path))
        print(f"  applied {path}")
    return modified


def rebuild(build_script: Path) -> int:
    res = subprocess.run(["python3", str(build_script)], capture_output=False)
    return res.returncode


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(
        description="Deck Agent Team orchestrator — render, extract, "
                    "prepare critic handoff, apply patches.",
    )
    ap.add_argument("--target", type=Path,
                    default=_env_path("DECK_AGENT_TARGET"),
                    help="path to .pptx under review")
    ap.add_argument("--mockup", type=Path,
                    default=_env_path("DECK_AGENT_MOCKUP_MD"),
                    help="path to mockup md")
    ap.add_argument("--build-script", type=Path,
                    default=_env_path("DECK_AGENT_BUILD_SCRIPT"),
                    help="path to build script (used for patch line refs and "
                         "rebuild after --apply)")
    ap.add_argument("--reports-dir", type=Path,
                    default=_env_path("DECK_AGENT_REPORTS_DIR",
                                      Path("./reports").resolve()),
                    help="parent dir for review session subdirs")
    ap.add_argument("--preview-dir", type=Path,
                    default=_env_path("DECK_AGENT_PREVIEW_DIR"),
                    help="dir for rendered PNGs (default: /tmp/<stem>_preview)")
    ap.add_argument("--qa-validator", type=Path,
                    default=_env_path("DECK_AGENT_QA_VALIDATOR"),
                    help="optional Phase-1 validator script (e.g., qa_validate.py)")
    ap.add_argument("--claude-md", type=Path,
                    default=_env_path("DECK_AGENT_CLAUDE_MD"),
                    help="path to project-level CLAUDE.md (passed to Critic D)")
    ap.add_argument("--extractors-dir", type=Path,
                    default=_env_path("DECK_AGENT_EXTRACTORS_DIR",
                                      DEFAULT_EXTRACTORS),
                    help=f"path to extractors dir (default: {DEFAULT_EXTRACTORS})")
    ap.add_argument("--prompts-dir", type=Path,
                    default=_env_path("DECK_AGENT_PROMPTS_DIR",
                                      DEFAULT_PROMPTS),
                    help=f"path to prompts dir (default: {DEFAULT_PROMPTS})")
    ap.add_argument("--project-root", type=Path,
                    default=_env_path("DECK_AGENT_PROJECT_ROOT"),
                    help="project root for resolving relative patch paths "
                         "(default: build-script's parent.parent)")
    ap.add_argument("--apply", type=Path,
                    help="apply [x]-marked patches from a report.md")
    ap.add_argument("--auto-mark-mechanical", type=Path,
                    help="flip [ ] → [x] for every issue with a mechanical "
                         "Patch block (no rebuild)")
    ap.add_argument("--no-rebuild", action="store_true",
                    help="skip rebuild after apply")
    args = ap.parse_args()

    if args.auto_mark_mechanical:
        n = auto_mark_mechanical(args.auto_mark_mechanical)
        print(f"Auto-marked {n} mechanical patch(es) in "
              f"{args.auto_mark_mechanical}")
        return 0

    if args.apply:
        if not args.build_script:
            ap.error("--build-script (or DECK_AGENT_BUILD_SCRIPT) required for --apply")
        project_root = args.project_root or args.build_script.resolve().parent.parent
        patches = parse_report(args.apply)
        if not patches:
            print("No [x]-marked patches found.")
            return 0
        print(f"Applying {len(patches)} patch(es)...")
        modified = apply_patches(patches, project_root)
        if modified and not args.no_rebuild:
            print("Rebuilding...")
            return rebuild(args.build_script)
        return 0

    if not args.target:
        ap.error("--target (or DECK_AGENT_TARGET) is required for review mode")
    if not args.mockup:
        ap.error("--mockup (or DECK_AGENT_MOCKUP_MD) is required for review mode")
    if not args.build_script:
        ap.error("--build-script (or DECK_AGENT_BUILD_SCRIPT) is required for review mode")

    target = args.target.resolve()
    preview_dir = args.preview_dir or Path(f"/tmp/{target.stem}_preview")

    timestamp = dt.datetime.now().strftime("%Y-%m-%d_%H-%M")
    out_dir = args.reports_dir / timestamp
    print(f"Review session: {out_dir}")

    print("→ rendering PNGs")
    pngs = render_previews(target, preview_dir)
    print(f"  {len(pngs)} slides")

    print("→ extracting slide text")
    extracted = extract_text_per_slide(target)

    print("→ extracting canonical mockup text")
    canonical = extract_canonical_mockup(args.mockup, args.extractors_dir, len(pngs))

    print("→ running Phase-1 QA")
    qa_out = run_qa_phase1(target, args.qa_validator)

    print("→ writing handoff bundle")
    bundle = write_handoff(target, args.mockup, args.build_script,
                           args.claude_md, args.prompts_dir,
                           pngs, extracted, canonical, qa_out, out_dir)
    readme = write_runner_readme(bundle, out_dir)
    print(f"\nNext: follow {readme}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
