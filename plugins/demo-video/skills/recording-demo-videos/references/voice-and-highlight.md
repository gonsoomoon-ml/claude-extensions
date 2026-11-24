# Highlight boxes, held captions and narrated reels

What each part does, in the order you use it. The commands and fields were run on synthetic clips and one real recording of a small page; speech synthesis was never run for this document (see "What was and was not tried").

1. [Say where things are (recorder)](#1-say-where-things-are-recorder)
2. [Boxes and held captions in a clip script](#2-boxes-and-held-captions-in-a-clip-script)
3. [Narration lines and `voice`](#3-narration-lines-and-voice)
4. [A narrated reel](#4-a-narrated-reel)
5. [The checks](#5-the-checks)
6. [What the checks cannot see, and other limits](#6-what-the-checks-cannot-see-and-other-limits)

Workflow in one line: lines (text) → `voice` → clips with `hold` → reel manifest with `voice`, `voice_at`, `group` and picture segments → `reel` → `check_demo.py audit`, `boxes`, `sheet` → listen on `review.html`.

## 1. Say where things are (recorder)

Every `focus` and `region` shot now writes `"rect": [x, y, w, h]` into the camlog: where its target lies on the 1920×1080 frame once the camera has stopped (integers, clipped to the frame; no `rect` when the target lies wholly outside it). Two more ways to log a place without moving the camera:

- `await rec.mark('cell', '#total', 'the total')` writes a `"mark"` entry with the element's `rect`. A selector that matches nothing writes `missing: true` and prints a warning, as `focus` does; grep the camlog for it.
- `await markRows(rec, page, 'rows', 'first text', 'last text', 'three rows')` from `term.mjs` does the same for the terminal rows between two texts.

A beat then points at a place by name (`"box": "shot:<key>"`, `"box": "mark:<key>"`) and can be anchored to one (`"at": "mark:<key>"`, with `#n` for the n-th entry of that key).

Limits of the numbers, with the remedy:

- The camera turns the page around the corner of the `<body>` box. On a page whose body starts at the page's corner (`body { margin: 0 }`, as most apps and the ttyd page have) everything is exact. On a page whose body box is offset (an unstyled page's 8 px margin, a centred body) two things are off:
  - the camera frames its target off-centre (measured: 552 px on a centred 1000 px body at 1920×1080). This is older than the rectangles; a page with `body { margin: 0 }` is not affected;
  - a region whose numbers were measured by the camera (`window.__cam.rect(…)`, `rowsRect`) while it was zoomed logs a rectangle 9 to 17 px off on an 8 px margin, and far more on a centred body. Numbers typed as page coordinates, `rec.focus` and `rec.mark` are exact (within 2 px). Measure after `rec.reset`, or use `focus` / `mark`.
- `rowsRect`, `zoomRows` and `markRows` need `rec.install()` first; without it they stop with a TypeError.
- A rectangle from the camlog was measured at `1920x1080` and `--layout 1280x720` within 2 px of the frame's pixels.

## 2. Boxes and held captions in a clip script

Fields of a beat (the rest of the beat is in [script.md](script.md)):

| Field | Meaning |
|---|---|
| `"box"` | `[x, y, w, h]` in frame pixels, a list of such rectangles, `"shot:<key>[#n]"` or `"mark:<key>[#n]"`. Numbers are drawn as given. A camlog rectangle is the element's own bounds and is grown by 12 px (the border plus 4). |
| `"box_delay"` | Seconds after the caption starts that the box appears. Default: `1.4 / speed + 0.2` when the beat's `at` is a `shot:` anchor (the box waits for the camera to stop: 1.32 s at 1.25×), else 0. |
| `"box_dur"` | Seconds of the finished clip the box shows, counted from its start. A number above 0. Without it the box shows until its caption ends (a held caption: until the clip's last frame). |
| `"hold": true` | On the last beat only. Its caption (and its boxes) stay to the clip's last frame, with no fade-out. |

A red border 8 px wide with a 2 px dark line outside it, drawn over the real frame; nothing under it is changed. All boxes of one beat share one time, so one caption cannot point at two things one after the other: use two beats.

The clip step stops before ffmpeg starts, with a message that names the fix, when:

- a box lies outside the frame, or a `shot:` / `mark:` entry has no `rect`;
- a box lies under its caption: the lower third is y 912 to 992, `"pos": "top"` is y 102 to 182. This check assumes a one-line caption and compares the vertical range only;
- the box could never show (its caption has under 1 s of room, or `box_delay` outlasts the caption);
- the camera moves to a new shot while a box shows. The message reads `the camera moves to shot 'log' at 7.33 s while the box of '<text>' shows (5.83-8.96 s): shorten the caption or move the box`. For a held caption without `box_dur` it advises giving the box a `"box_dur"` instead, because a held caption cannot be shortened;
- `hold` is on a beat that is not the last;
- `box_dur` is not a number above 0 (`box_dur on beat '<text>' must be a number of seconds above 0, not '2'`), has no box to end, or runs past its caption (`… the box shows from 3.18 s and would end at 4.68 s of the clip, its caption ends at 4.36 s; shorten "box_dur" to 1.18 s or less`; for a held caption the middle reads `its held caption ends with the clip at <t> s`). The limits are exact to 1 ms although the lines print two decimals. The smallest useful `box_dur` is about one frame (0.04 s); a smaller one passes and draws nothing.

### A `box_dur` that ends before the next camera move

A held caption stays to the clip's end, a box may not show while the camera moves, so on a clip whose camera moves on the box must end first. Work in the clip's seconds:

1. Read `start` and `speed` from the script. `start` defaults to the first camlog shot minus 0.4 s (not below 0); `speed` defaults to 1.25.
2. `a` is the camlog time of the beat's `"at"` plus its `"offset"`.
3. The caption starts at `c0 = max((a - start) / speed, F)`, where `F` is 4.4 with a title card, 0.2 at `speed` 1 without one, else 0.
4. The box starts at `b0 = c0 + d`, with `d` the `box_delay`, else `1.4 / speed + 0.2` on a `shot:` anchor, else 0. In the take's seconds that is `lo = start + b0 * speed`.
5. The next camera move is the first camlog entry of kind `shot` with `t > lo`. A `mark` is not a move.
6. `box_dur <= (t - lo) / speed`, and `box_dur <= c1 - b0`, where for a held caption `c1 = (end - start) / speed` (`end` from the script, else the take's length).
7. Round down to 0.01 s and leave about one frame (0.04 s): the filter writes the box's end to 0.01 s.

Worked example, stand-in names: the script has `start` 3.5 and no title, `speed` 1.25; the beat is `{"at": "shot:wide", "hold": true, "box": [96, 160, 900, 300], …}` with `shot:wide` at 3.90 s. So `c0` = 0.32, `d` = 1.32, `b0` = 1.64, `lo` = 5.55. The next shot, `counts`, is at 9.91 s, so `box_dur <= (9.91 - 5.55) / 1.25 = 3.488`. Write `"box_dur": 3.45`: the box ends at 5.09 s of the clip and the caption stays to the end.

## 3. Narration lines and `voice`

```
python3 scripts/edit_demo.py voice lines.json --out voice/ [--readings readings.json] [--hangul-only]
          [--voice Seoyeon] [--engine generative] [--language ko-KR] [--region <region>]
```

`lines.json` is `{"<name>": "<text>" | {"audio": "<file>"}}`. One mp3 per line goes to `voice/<name>.mp3`, and `voice/voice.json` lists each file with its length in seconds, the text as spoken and a cache key. A line of the form `{"audio": "<file>"}` is a recording you made yourself: it is copied in as it is.

- Synthesis calls `aws polly synthesize-speech`, so it needs the AWS CLI with permission for `polly:SynthesizeSpeech`. Nothing else in the plugin calls AWS. The defaults are voice `Seoyeon`, engine `generative`, language `ko-KR`; `--region` or the CLI's own environment picks the region. These are the values chosen on 2026-11-24 for the first Korean narration; other voices and engines were not tried for this document, so choose by ear.
- `--readings` is `{"<written>": "<spoken>"}`, plain substrings applied longest key first, once per position (`"S3": "에스삼"`). `--hangul-only` refuses a line that still holds a Latin letter or a digit after the readings; use both so that a name is never read in a way you did not choose.
- A line whose spoken text, voice, engine and language are unchanged is not synthesized again (`voice: <name>: unchanged`), so a re-run costs only the lines you edited.
- It refuses, before any call, a blank line, a name that is not a plain file name, a line over 1000 characters, and a line that begins with `file://`, `fileb://`, `http://` or `https://` (the CLI would load it instead of speak it). The text is passed as `--text=<text>`, so a line that begins with a dash is spoken, not read as an option.
- A failed call stops the run, removes that line's file and leaves `voice.json` with the lines done so far.

Write each line to be heard together with the frames it plays over: it says only what those frames show. Keep a line under about 14 s (the reel warns above that).

## 4. A narrated reel

End a clip whose last frame the reel will hold with a held caption (`"hold": true` on its last beat), so the held frame keeps its caption, then give the reel manifest ([reel-manifest.md](reel-manifest.md) has the full field list):

```json
{"fade": 0.4, "voice_gap": 0.6, "voice_tail": 1.0, "loudness": -16, "segments": [
 {"image": "clips/card-intro.png", "seconds": 3, "voice": "voice/intro.mp3", "voice_at": 0.3},
 {"file": "clips/take.1.mp4", "start": 0, "end": 4.5, "voice": "voice/log.mp3", "voice_at": 0.3, "group": "a"},
 {"file": "clips/take.1.mp4", "start": 4.5, "end": 9.9, "group": "a"}
]}
```

- **A card under narration is a picture segment** (`image`, `seconds`). A card clip made by `make_cards.py` has its fade baked in, so holding its last frame gives black. Use the card's `.png`; it is drawn for as long as the voice needs.
- **The schedule.** A voice starts `voice_at` seconds into its segment. The reel holds the last frame of a segment so that the picture never runs ahead of a voice and no two voices overlap: (1) a voice that ends after the last segment of its run-on range is held by the difference; (2) the next voice starts at least `voice_gap` (0.6 s) after this one ends, the segment just before it being held by the missing time; (3) the reel runs `voice_tail` (1.0 s) past the last voice. `group` lets a voice run on over the following segments with an equal, non-empty group (a long wait that the voice talks across); without it a voice's range is its own segment.
- **Voices are placed by measured lengths.** Each part is encoded and measured, and a voice goes at the measured start of its part plus `voice_at`, not at the lengths the manifest states: a clip a few frames longer than stated would otherwise shift every later voice.
- **The sound.** The clips' own audio is dropped: the voice track is the reel's only sound. The voices are mixed and brought to `loudness` (−16 LUFS integrated, true peak at most −1.5 dBTP) with one gain, so their levels against each other stay as synthesized.
- **Output.** `reel.mp4` as before and `reel.voice.json` beside it: each segment's measured start, length and hold, each voice's measured start and end, and `warnings`. Warnings do not stop the reel: a hold over 6 s, holds over 30 % of the reel, a voice over 14 s, and a voice track that one gain cannot bring to the target. stdout is one line with the reel's length, the number of parts and voices and the seconds held.
- **Refused before encoding:** a missing file, `start` or `end` outside the clip, two voices on one segment, a `voice_at` outside the segment, a picture without `seconds`, and `--copy` on a manifest with `voice` or `image` (`reel: --copy cannot carry voices or picture segments; leave it out`). A manifest with neither field runs exactly as before.

## 5. The checks

`check_demo.py` reads finished files and never changes them. Each command prints one JSON line.

**`audit reel.mp4 --out audit.json`** compares the reel's sound with its plan (`reel.voice.json` beside it, or `--plan`). It finds speech with ffmpeg's `silencedetect` and expects each voice from its planned start plus its file's first sound to its planned start plus its file's last sound: a speech file begins and ends with a little silence, so the audit reads each voice file's own first and last sound instead of its length. It reports, one line each: a voice heard more than `--tolerance` (0.25 s) early or late at either end, a planned voice with no sound, sound where no voice is planned, two voices planned closer than 0.35 s, video and audio lengths more than 0.1 s apart, an integrated loudness more than 1.5 LU from `--loudness`, and a plan without `name`, `start` or `end`. The report is written either way. Exit 0 when it passes, 1 on a problem.

**`boxes scripts/take.1.json --raw raw/take.webm --out boxes/take.1.json`** measures each box on the raw take (never on the clip, which holds the box itself) at the box's first and last moment, and writes its rectangle, its time in the take and in the clip, and three numbers: `std` (how busy the strips under the border are), `redness` and `change` (how much the picture inside the box changes). Flags:

- `crosses`: the border runs over text or a picture;
- `low_contrast`: the strips under the border are already near the border's red;
- `moved`: the screen under the box changed while it showed.

A flag says "look at this row", not a failure: exit 0 whatever the flags. Exit 1 only when the script cannot be read or the clip step would refuse it (its own message). The script's stem must equal its clip's stem, and a script's `title` must be in the script, not only on `clip`'s command line.

**`sheet reel.mp4 --plan reel.voice.json --texts texts.json [--boxes boxes/*.json] --out review/`** writes `index.json`, one JPEG per voice and `review.html`: one file to send as it is. Per voice it shows the reel's frames at start + 0.5 s, the middle and end − 0.2 s, an enlarged crop of each box, the caption, the narration, what each box points at, the flags and the times, and a play control with the reel's own sound for that voice's window. The page has no script and its only links are the in-page ones from its top list of rows and flagged rows; a flagged row has a red edge. `texts.json` is `{"<voice name>": {"caption": "…", "say": "…", "what": ["…"], "sources": ["…"]}}`, every field optional (`what[i]` goes with the i-th box).

## 6. What the checks cannot see, and other limits

- **They cannot hear.** They find where sound is and how loud, not whether a word is pronounced well. A person listens with the review page.
- A sound placed inside a voice's own pause is joined into that voice by the audit and passes.
- The box-under-caption check assumes a one-line caption and compares the vertical range only.
- A boxes report attaches to every row whose clip carries that name: a clip used twice in one reel shows its boxes on both rows.
- A voice track shorter than about 3 s cannot be brought to the loudness target in one step and comes out quieter, with a warning.
- One caption has one time for its boxes.
- The audio options of the reel were run with ffmpeg 4.4 only.
- A reel whose voice is one quiet line among loud ones keeps that line quiet: the gain is one for the whole track.

## What was and was not tried

Run on 2026-11-24 on synthetic clips and one real take of a small page: `clip` with `box` in three forms, `box_dur` and `hold`; `voice` (its refusals and its cache) with a stand-in `aws` that writes a tone; `reel` with a picture segment, voices and a group; `audit`, `boxes` and `sheet` on that reel. Speech synthesis itself, the AWS permission and `markRows` on a live terminal were not run for this document; they are described from the code and its tests.
