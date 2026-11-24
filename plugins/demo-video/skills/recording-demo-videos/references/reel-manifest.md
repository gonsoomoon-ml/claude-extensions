# Reel manifest (`edit_demo.py reel`)

```json
{"fade": 0.4, "segments": [
 {"file": "clips/replay-normal.mp4",   "start": 0,  "end": 16},
 {"file": "clips/replay-escalation.mp4", "start": 0, "end": 46},
 {"file": "clips/live-move_object.mp4", "start": 0,  "end": 42},
 {"file": "clips/live-move_object.mp4", "start": 76, "end": 90},
 {"file": "clips/lab-slippery.mp4",     "start": 343, "end": 372},
 {"file": "clips/replay-results.mp4",   "start": 0,  "end": 30}
]}
```

- `file`: a finished clip (already has title card and captions). Paths relative to the cwd where `edit_demo.py` runs.
- `start`/`end`: seconds inside that clip; `end` null or omitted = to the end. The same clip may appear several times (intro window, then the payoff later).
- `fade`: video and audio fade in/out per segment, seconds. 0.4 reads as a clean cut with no flash.
- Each segment is re-encoded with the same x264 settings and concatenated; the join is then re-encoded once more into one uniform stream (High 4.1, CRF 23, 3 Mbit/s cap, keyframe every 2 s, faststart). 1.2.0 stopped at the stream-copied concat, whose two-entry edit list made QuickTime freeze on a mid-video frame while the time kept running; `--copy` restores that output if you need it.
- Deliver that one file. If a viewer reports a freeze, compare their copy's byte size and md5 with yours: a download cut short plays up to the missing bytes and then sticks.

Choosing windows: open `raw/<stem>.camlog.json` and take `t` of the shots you want; clip time = camlog `t` minus the clip's trimmed lead-in (`edit_demo.py clip` prints `seconds` and starts 0.4 s before the first shot unless `--start` was given). Keep the title card (first 4 s of a clip) only for the first appearance of that clip.

Two reels usually cover a post: a **short** (3–6 min, one window per scene, ends on the results scene) and a **full** (every clip whole, with the slowest scene's dead time cut out).

Per-segment `fade_in` / `fade_out` (seconds, `0` = hard cut) override `fade` for that segment. Use them when one scene was cut into several clips at different `speed` values; only the outer edges of the scene fade:

```json
{"fade": 0.4, "segments": [
 {"file": "clips/04a-lab-start.mp4",  "fade_out": 0},
 {"file": "clips/04b-lab-agent.mp4",  "fade_in": 0, "fade_out": 0},
 {"file": "clips/04c-lab-result.mp4", "fade_in": 0}
]}
```

`04b` was clipped with `"speed": 4`, so its 17.5 s of agent turns play in 4.4 s; the viewer sees one continuous scene. Every segment must have the same resolution; the tool aborts before encoding if two files differ.

## Narrated reel: voices and picture segments

A segment may carry a voice, and a segment may be a picture instead of a clip. A manifest with a `voice` or an `image` anywhere is a narrated reel; one with neither runs exactly as described above.

```json
{"fade": 0.4, "voice_gap": 0.6, "voice_tail": 1.0, "loudness": -16, "segments": [
 {"image": "clips/card-intro.png", "seconds": 3, "voice": "voice/intro.mp3", "voice_at": 0.3},
 {"file": "clips/take.1.mp4", "start": 0, "end": 4.5, "voice": "voice/log.mp3", "voice_at": 0.3, "group": "a"},
 {"file": "clips/take.1.mp4", "start": 4.5, "end": 9.9, "group": "a"}
]}
```

| Field | Where | Meaning |
|---|---|---|
| `image`, `seconds` | segment | a picture drawn for `seconds` (above 0; longer when its voice needs it), scaled to fit the clips' frame and letterboxed; `start` and `end` are ignored. Use it for a card under narration: a card clip has its fade baked in and would hold black. |
| `voice` | segment | one audio file (any format ffmpeg reads) per segment |
| `voice_at` | segment | seconds into the segment where the voice starts; default 0, must lie inside the segment |
| `group` | segment | a voice runs on over the following segments with an equal, non-empty `group`; without it a voice's range is its own segment |
| `voice_gap` | top level | least silence between two voices; default 0.6 s |
| `voice_tail` | top level | how long the reel runs after the last voice; default 1.0 s |
| `loudness` | top level | integrated loudness of the voice track in LUFS; default -16, true peak at most -1.5 dBTP |

- The reel holds a segment's last frame until its voice has ended, mixes the voices into the reel's only sound (the clips' own audio is dropped) and places each voice by the measured length of the parts before it, not by the lengths the manifest states.
- It writes `<reel stem>.voice.json` beside the reel: each segment's measured `start`, `seconds` and `hold`, each voice's measured `start` and `end`, and `warnings` (a hold over 6 s, holds over 30 % of the reel, a voice over 14 s, a voice track that one gain cannot bring to the target; none of them stops the reel). `check_demo.py audit` and `sheet` read that file.
- `--copy` is refused for a narrated reel.
- A voice track shorter than about 3 s comes out quieter than the target, with a warning.

The schedule's rules, the checks and their limits are in [voice-and-highlight.md](voice-and-highlight.md).
