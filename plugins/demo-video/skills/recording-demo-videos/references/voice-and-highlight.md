# Highlight boxes, held captions and narrated reels

What each part does, in the order you use it. The commands and fields were run on synthetic clips and one real recording of a small page; speech synthesis was never run for this document (see "What was and was not tried").

1. [Say where things are (recorder)](#1-say-where-things-are-recorder)
2. [Boxes and held captions in a clip script](#2-boxes-and-held-captions-in-a-clip-script)
3. [Write from the take: frame text and `brief`](#3-write-from-the-take-frame-text-and-brief)
4. [Narration lines and `voice`](#4-narration-lines-and-voice)
5. [A narrated reel](#5-a-narrated-reel)
6. [The checks](#6-the-checks)
7. [What the checks cannot see, and other limits](#7-what-the-checks-cannot-see-and-other-limits)

Workflow in one line: take → `brief` → lines (text) → `voice` → clips with `hold` → reel manifest with `voice`, `voice_at`, `group` and picture segments → `reel` → `check_demo.py audit`, `boxes`, `sheet` → listen on `review.html`.

## 1. Say where things are (recorder)

Every `focus` and `region` shot now writes `"rect": [x, y, w, h]` into the camlog: where its target lies on the 1920×1080 frame once the camera has stopped (integers, clipped to the frame; no `rect` when the target lies wholly outside it). Two more ways to log a place without moving the camera:

- `await rec.mark('cell', '#total', 'the total')` (the label comes third, where `focus` takes its options; a fourth argument, the index among several matches, defaults to 0) writes a `"mark"` entry with the element's `rect`. A selector that matches nothing writes `missing: true` and prints a warning, as `focus` does; grep the camlog for it.
- `await markRows(rec, page, 'rows', 'first text', 'last text', 'three rows')` from `term.mjs` does the same for the terminal rows between two texts.

A shot given a move length of its own (`{ dur: 0.6 }` on `focus` or `region`, or `window.__cam.apply(x, y, k, dur)` inside `rec.shot`) also writes `"move": 0.6`, the seconds the camera takes to arrive; a shot of the default 1.4 s writes none. The clip step's camera check reads it (section 2). A camlog recorded before the recorder wrote `"move"` is checked with 1.4 s for every shot.

A beat then points at a place by name (`"box": "shot:<key>"`, `"box": "mark:<key>"`) and can be anchored to one (`"at": "mark:<key>"`, with `#n` for the n-th entry of that key).

Limits of the numbers, with the remedy:

- The camera turns the page around the corner of the `<body>` box. On a page whose body starts at the page's corner (`body { margin: 0 }`, as most apps and the ttyd page have) everything is exact. On a page whose body box is offset (an unstyled page's 8 px margin, a centred body) two things are off:
  - the camera frames its target off-centre (measured 2026-11-24: 552 px on a centred 1000 px body at 1920×1080). This is older than the rectangles; a page with `body { margin: 0 }` is not affected;
  - a region whose numbers were measured by the camera (`window.__cam.rect(…)`, `rowsRect`) while it was zoomed logs a rectangle 9 to 17 px off on an 8 px margin (measured 2026-11-24), and far more on a centred body. Numbers typed as page coordinates, `rec.focus` and `rec.mark` are exact (within 2 px). Measure after `rec.reset`, or use `focus` / `mark`.
- `rowsRect`, `zoomRows` and `markRows` need `rec.install()` first; without it they stop with a TypeError.
- A rectangle from the camlog was measured on 2026-11-24 at `1920x1080` and `--layout 1280x720` within 2 px of the frame's pixels.

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

- typed numbers lie outside the frame, or a `shot:` / `mark:` entry has no `rect` (a camlog rectangle is grown and then clipped to the frame, so a `shot:` box at the edge is drawn, not refused);
- a box lies under its caption: the lower third is y 912 to 992, `"pos": "top"` is y 102 to 182. This check assumes a one-line caption and compares the vertical range only;
- the box could never show (its caption has under 1 s of room, or `box_delay` outlasts the caption);
- a box shows while the camera moves. A move lasts from a shot's time until the camera stops: 1.4 s, or the shot's own `"move"` from the camlog (section 1). A shot whose camera values equal the previous shot's (to 0.01 px; the same element focused again) moves nothing, and so does a shot whose selector matched nothing. The check holds whatever the beat is anchored to (a shot, a mark, a note, seconds); only a `shot:` anchor gets a default delay, and it waits for a move of the default 1.4 s (a shot recorded with a longer `"move"` of its own is refused until you give a longer `"box_delay"`). Both lines say when the camera stops and name the `"box_delay"` that starts the box after it (rounded up to 0.01 s) when a delay can pass before the caption ends; without such a delay each line ends in its own advice, given below:
  - a box that would start during a move: `the camera is still moving to shot 'table' (from 5.00 s, it stops at 6.40 s) when the box of 'x' starts (it shows 5.30-10.30 s): start the box after the camera stops with "box_delay": 0.88`; when no delay leaves the box room before its caption ends, the line ends `its caption ends before the camera stops: anchor the beat later or lengthen its caption`;
  - a move that starts while the box shows: `the camera moves to shot 'later' at 6.00 s (it stops at 7.40 s) while the box of 'stay' shows (2.50-8.00 s): shorten the caption or move the box, or start the box after the camera stops with "box_delay": 5.40`; where no delay fits, the line ends at `shorten the caption or move the box`. For a held caption without `box_dur` the advice is to give the box a `"box_dur"`, because a held caption cannot be shortened; with a `box_dur` it is to shorten it;
- `hold` is on a beat that is not the last;
- `box_dur` is not a number above 0 (`box_dur on beat '<text>' must be a number of seconds above 0, not '2'`), has no box to end, or runs past its caption (`… the box shows from 3.18 s and would end at 4.68 s of the clip, its caption ends at 4.36 s; shorten "box_dur" to 1.18 s or less`; for a held caption the middle reads `its held caption ends with the clip at <t> s`). The limits are exact to 1 ms although the lines print two decimals. The smallest useful `box_dur` is about one frame (0.04 s); a smaller one passes and draws nothing.

### A `box_dur` that ends before the next camera move

A held caption stays to the clip's end, a box may not show while the camera moves, so on a clip whose camera moves on the box must end first. Work in the clip's seconds:

1. Read `start` and `speed` from the script. `start` defaults to the first camlog shot minus 0.4 s (not below 0); `speed` defaults to 1.25.
2. `a` is the camlog time of the beat's `"at"` plus its `"offset"`.
3. The caption starts at `c0 = max((a - start) / speed, F)`, where `F` is 4.4 with a title card, 0.2 at `speed` 1 without one, else 0.
4. The box starts at `b0 = c0 + d`, with `d` the `box_delay`, else `1.4 / speed + 0.2` on a `shot:` anchor, else 0. In the take's seconds that is `lo = start + b0 * speed`.
5. The next camera move is the first camlog entry of kind `shot` with `t > lo`. A `mark` is not a move, nor is a shot whose camera values equal the shot's before it.
6. `box_dur <= (t - lo) / speed`, and `box_dur <= c1 - b0`, where for a held caption `c1 = (end - start) / speed` (`end` from the script, else the take's length).
7. Round down to 0.01 s and leave about one frame (0.04 s): the filter writes the box's end to 0.01 s.

Worked example, stand-in names: the script has `start` 3.5 and no title, `speed` 1.25; the beat is `{"at": "shot:wide", "hold": true, "box": [96, 160, 900, 300], …}` with `shot:wide` at 3.90 s. So `c0` = 0.32, `d` = 1.32, `b0` = 1.64, `lo` = 5.55 (the move to `wide` stops at 5.30). The next shot, `counts`, is at 9.91 s, so `box_dur <= (9.91 - 5.55) / 1.25 = 3.488`. Write `"box_dur": 3.45`: the box ends at 5.09 s of the clip and the caption stays to the end.

A script that uses a box or a hold makes `clip` print, on stderr, each caption's and box's time in the finished clip, one line per beat: `clip: beat 2: caption 6.00-10.00 s, box 6.50-10.00 s: 'held'`. A script without them prints what it printed before.

## 3. Write from the take: frame text and `brief`

Captions and narration lines are written after the take, from what it recorded. What the video says (cards, chapter titles) is still decided before recording ([script.md](script.md)); the take supplies the facts.

### What the recorder keeps

Beside the camlog, `record_demo.mjs` writes `<name>.frametext.txt`: the text the frame showed, one entry per capture. An entry is a header line, `== <seconds of the take> <kind> <key>`, and the text's lines.

| When | Kind | Text |
|---|---|---|
| a shot (`rec.focus`, `rec.region`, `rec.reset`, `rec.shot`) | `shot`, under the shot's key and time | what the frame shows once the camera has stopped |
| the next shot, just before it moves the camera | `leave`, under the key of the view it leaves | that view as it is then; written only when it differs from the last capture, because a result arrives after a shot, not with it |
| `rec.mark`, `markRows` | `mark`, under the mark's key and time | the marked element's (or rows') own text |
| `await rec.text('<key>')` | `text` | what the frame shows now, for a screen that changes while the camera stays (an event-probe loop, a terminal session) |

"What the frame shows" is the text of the visible elements that have a line inside the frame at rest, plus the values of form fields, in reading order: rows top to bottom, pieces that touch joined, pieces apart given a space. Each line is first cut to the `overflow` boxes around it, so a row scrolled out of a panel is not kept. A capture holds at most 20,000 characters and then ends with the line `[cut]`. One capture took 14 ms on a page of 3,000 text nodes (measured 2026-11-28); the `leave` capture runs before the camera moves, the shot's camlog time is still taken after the camera call.

Limits:

- a paragraph that is only partly in the frame is kept whole;
- text covered by another element (a page behind a dialog) is kept;
- text inside a picture, a `canvas`, an `iframe` or a shadow root is not read: write such rows from the stills;
- the value of a `type="password"` field is never read;
- text that arrives after a capture is missing until the next `leave` or `rec.text`;
- a capture needs the camera on the page: before the first `rec.install()` nothing is kept and nothing stops. After it the recorder puts the camera back on every new page by itself ([pointer.md](pointer.md)).

The file is the take's content as text: keep it where the take is kept. The recorder never writes a `<name>.texts.txt`; a storyboard that keeps such a file of its own keeps it.

### `brief`: the take as rows

```
python3 scripts/check_demo.py brief raw/<stem>.webm --out brief/<stem>/ [--script scripts/<stem>.1.json …]
          [--speed 1.25] [--voices voice/voice.json] [--rate 7.6] [--every 5]
```

It writes `<out>/brief.json` and stills (JPEG, 1920×1080), reads its inputs only, and prints one JSON line (the number of rows, of stills and of live rows, and the rate). A run removes its own earlier stills from `--out` and nothing else.

| Called | One row | Use |
|---|---|---|
| on a take, without `--script` | per view: a camlog shot to the next one | write the beats |
| with `--script`: one or more scripts cut from this take, those of one run of the reel | per caption | write one narration line per caption |
| on a recording without a camlog (a `.mov`), without `--script` | every `--every` seconds (5) | find where the screen changes |

With `--script` a row starts where its caption starts (the clip step's own times; a script the clip step refuses stops `brief` with the same line, before `--out` is touched). The row runs over the rest of its clip and over every following clip that has no caption, as a voice runs on over the later segments of its `group`. It ends where the reel would hold its last frame: at the next caption when that is in the same script, else where the next script with a caption starts. A script without a caption that comes before the first caption is in no row (stderr names it). Two scripts that cover the same seconds of the take stop the command.

| Field | Meaning |
|---|---|
| `"row"` | 1, 2, … |
| `"key"`, `"label"` | per view: the shot's |
| `"script"`, `"beat"`, `"caption"` | per caption: the script's stem, the beat's number in it, the caption |
| `"raw"` | the take's seconds, `[start, end]`; one pair per clip, `[[start, end], …]`, when the row runs over several |
| `"seconds"` | seconds of the finished clip: each piece at its script's speed, or at `--speed` without scripts |
| `"budget"` | the characters of narration that fit: `(seconds − 0.3 − voice_gap) × rate`, rounded down |
| `"live"` | `true`: the picture still changes in the row's last second (the take's frames 1.0 s and 0.2 s before its end differ); `false`: it stands still; `null`: not measured, because the camera moves in that second or the row's last piece is shorter than 1.0 s |
| `"text"` | the frame's text as the row starts |
| `"text_end"` | the frame's text as the camera leaves the row's last view (`leave`), when it differs |
| `"texts"` | what `rec.text` kept inside the row; per caption everything kept later in the row, in the take's order: each following view's text as the camera arrives and as it leaves |
| `"marks"`, `"notes"` | the camlog's marks, with their text, and its other entries inside the row; a press (`tap`) comes with its key, label and the pressed element's text |
| `"stills"` | three file names: after the camera stops (per caption: half a clip second after the caption), the middle, 0.2 s before the end; one per row with `--every` |

The budget: 0.3 s is the lead from a caption to its voice, `voice_gap` (0.6 s) the reel's silence between two voices. The rate is the spoken characters a second, spaces counted: measured in the `voice.json` that `--voices` names when it has lines, else `--rate`, else 7.6 (7.63 on the 70 Korean lines of a narration synthesized on 2026-11-24). The report says which. A take recorded before the recorder kept frame text gives rows without text, with one line on stderr.

**What `"live"` is for.** A reel holds a row's last frame when its voice outlasts the row. On a `"live": false` row that frame was standing still already: a line over the budget costs nothing a viewer sees. On a `"live": true` row the reel stops a picture that was moving. The budget is information, no command stops on it.

### Writing from the rows

Beats come from the view rows, narration lines from the caption rows:

1. What to say comes from the script (the cards, the chapter titles). The facts come from the row's text and stills.
2. Names and numbers are spelled as the row's text spells them. One that needs a reading goes into the `--readings` file.
3. Say what the feature did in this take, usually the result in `"text_end"`, not that a screen opened.
4. On a `"live": true` row keep the line within `"budget"`. On any other row the limit is the reel's own (section 4).

## 4. Narration lines and `voice`

```
python3 scripts/edit_demo.py voice lines.json --out voice/ [--readings readings.json] [--hangul-only]
          [--voice Seoyeon] [--engine generative] [--language ko-KR] [--region <region>]
```

`lines.json` is `{"<name>": "<text>" | {"audio": "<file>"}}`. One mp3 per line goes to `voice/<name>.mp3`, and `voice/voice.json` lists each file with its length in seconds, the text as spoken and a cache key. A line of the form `{"audio": "<file>"}` is a recording you made yourself: it is copied in as it is.

- Synthesis calls `aws polly synthesize-speech`, so it needs the AWS CLI with permission for `polly:SynthesizeSpeech`. Nothing else in the plugin calls AWS. The defaults are voice `Seoyeon`, engine `generative`, language `ko-KR`; `--region` or the CLI's own environment picks the region. These are the values chosen on 2026-11-24 for the first Korean narration; other voices and engines were not tried for this document, so choose by ear.
- `--readings` is `{"<written>": "<spoken>"}`, plain substrings applied longest key first, once per position (`"S3": "에스삼"`). `--hangul-only` refuses a line that still holds a Latin letter or a digit after the readings; use both so that a name is never read in a way you did not choose.
- A line whose spoken text, voice, engine and language are unchanged is not synthesized again (`voice: <name>: unchanged`), so a re-run costs only the lines you edited.
- It refuses, before any call, a blank line, a line that is neither text nor `{"audio": …}`, an `{"audio": …}` file that does not exist, is not audio or would be copied in as `voice.json`, a reading whose spoken form is not a text, a name that is not a plain file name, a line over 1000 characters, and a line that begins with `file://`, `fileb://`, `http://` or `https://` (the CLI would load it instead of speak it). The text is passed as `--text=<text>`, so a line that begins with a dash is spoken, not read as an option.
- The cache also needs the mp3 to exist. `voice` prints the `voice.json` it wrote on stdout.
- A failed call stops the run, removes that line's file and leaves `voice.json` with the lines done so far.

Write each line to be heard together with the frames it plays over: it says only what those frames show. Keep a line under about 14 s (the reel warns above that).

## 5. A narrated reel

End a clip whose last frame the reel will hold with a held caption (`"hold": true` on its last beat), so the held frame keeps its caption, then give the reel manifest ([reel-manifest.md](reel-manifest.md) has the full field list):

```json
{"fade": 0.4, "voice_gap": 0.6, "voice_tail": 1.0, "loudness": -16, "segments": [
 {"image": "clips/card-intro.png", "seconds": 3, "voice": "voice/intro.mp3", "voice_at": 0.3},
 {"file": "clips/take.1.mp4", "start": 0, "end": 4.5, "voice": "voice/log.mp3", "voice_at": 0.3, "group": "a", "fade_out": 0},
 {"file": "clips/take.1.mp4", "start": 4.5, "end": 9.9, "group": "a", "fade_in": 0}
]}
```

- **A card under narration is a picture segment** (`image`, `seconds`). A card clip made by `make_cards.py` has its fade baked in, so holding its last frame gives black. Use the card's `.png`; it is drawn for as long as the voice needs.
- **The schedule.** A voice starts `voice_at` seconds into its segment. The reel holds the last frame of a segment so that the picture never runs ahead of a voice and no two voices overlap: (1) a voice that ends after the last segment of its run-on range is held by the difference; (2) the next voice starts at least `voice_gap` (0.6 s) after this one ends, the segment just before it being held by the missing time; (3) the reel runs `voice_tail` (1.0 s) past the last voice. `group` lets a voice run on over the following segments with an equal, non-empty group (a long wait that the voice talks across); without it a voice's range is its own segment.
- **Choosing `voice_at`.** So that a voice never starts before its caption, set `voice_at` to the caption's start in the clip minus the window's `start`, plus a lead (0.3 s for the first narrated reels). `clip` prints each caption's start for a script with a box or a hold (section 2); for another script work it out as `c0` in section 2.
- **Voices are placed by measured lengths.** Each part is encoded and measured, and a voice goes at the measured start of its part plus `voice_at`, not at the lengths the manifest states: a clip a few frames longer than stated would otherwise shift every later voice.
- **Fades.** `fade`, `fade_in` and `fade_out` apply to a narrated reel as to any other (the hold comes before the fade-out). Pieces of one `group` are pieces of one scene: join them with `fade_out: 0` on the earlier and `fade_in: 0` on the later, or the picture dips to black while the voice runs on.
- **The sound.** The clips' own audio is dropped: the voice track is the reel's only sound. The voices are mixed and brought towards `loudness` (−16 LUFS integrated) with the true peak at most −1.5 dBTP, measured with ffmpeg's loudnorm, in one of three ways:
  1. one gain reaches the target under that ceiling: that gain, and the voices' levels against each other stay as synthesized;
  2. it does not, but the largest gain the ceiling allows lands within 1.5 LU of the target (the audit's tolerance): that one gain, the levels stay, and the plan's `warnings` say the level reached (`the voice track is brought to -16.9 LUFS, not -16 LUFS: one gain of +14.6 dB is the most its true peak (-16.1 dBTP at -31.6 LUFS) allows under -1.5 dBTP, so the voices keep their levels against each other`);
  3. even that lands more than 1.5 LU short: loudnorm compresses the track, which changes the voices' levels against each other, with a warning.

  Speech peaks high for its loudness (synthesized lines about 15 dB above it, measured 2026-11-24), so expect the second way with the default voice and target. One gain works the same on a short track; a voice track shorter than about 3 s that has to be compressed comes out quieter than the target (a 2.5 s tone track: −18.5 LUFS, measured 2026-11-24). The audio options were run with ffmpeg 4.4 only.
- **Output.** `reel.mp4` as before and `reel.voice.json` beside it (it holds the absolute paths of the voice files; keep that in mind before sending the plan file to someone, the review page holds no paths): each segment's measured start, length and hold, each clip segment's `"window"` (the seconds of its clip it shows, from which `sheet` places each box), each voice's measured start and end, and `warnings`. Warnings do not stop the reel: a hold over 6 s, holds over 30 % of the reel, a voice over 14 s, a voice track that one gain brings only near the target (the level reached), and a voice track that has to be compressed. stdout is one line with the reel's length, the number of parts and voices and the seconds held.
- **Refused before encoding:** a missing file, `start` or `end` outside the clip, two voices on one segment, a `voice_at` outside the segment, a picture without `seconds`, and `--copy` on a manifest with `voice` or `image` (`reel: --copy cannot carry voices or picture segments; leave it out`). A manifest with neither field runs exactly as before.

## 6. The checks

`check_demo.py` reads finished files and never changes them. Each command prints one JSON line.

**`python3 scripts/check_demo.py audit reel.mp4 --out audit.json`** compares the reel's sound with its plan (`reel.voice.json` beside it, or `--plan`). It finds speech with ffmpeg's `silencedetect` and expects each voice from its planned start plus its file's first sound to its planned start plus its file's last sound: a speech file begins and ends with a little silence, so the audit reads each voice file's own first and last sound instead of its length. It reports, one line each: a voice heard more than `--tolerance` (0.25 s) early or late at either end, a planned voice with no sound, sound where no voice is planned, two voices planned closer than 0.35 s, video and audio lengths more than 0.1 s apart, an integrated loudness more than 1.5 LU from `--loudness`, and a plan without `name`, `start` or `end`. The report is written either way (it also holds the voice files' absolute paths). Exit 0 when it passes, 1 on a problem. A voice whose `file` is not a file here (gone, or a URL) is held against the plan's times with a warning; the value is never handed to ffmpeg. A sound placed inside a voice's own pause is joined into that voice by the audit and passes.

**`python3 scripts/check_demo.py boxes scripts/take.1.json --raw raw/take.webm --out boxes/take.1.json`** measures each box on the raw take (never on the clip, which holds the box itself) at the box's first and last moment, and writes its rectangle, its time in the take and in the clip, and three numbers: `std` (how busy the strips under the border are), `redness` and `change` (how much the picture inside the box changes). Flags:

- `crosses`: the border runs over text or a picture;
- `low_contrast`: the strips under the border are already near the border's red;
- `moved`: the screen under the box changed while it showed.

A flag says "look at this row", not a failure: exit 0 whatever the flags. Exit 1 only when the script cannot be read or the clip step would refuse it (its own message). The script's stem must equal its clip's stem, and a script's `title`, `start` and `end` must be in the script, not only on `clip`'s command line: they set the boxes' times.

**`python3 scripts/check_demo.py sheet reel.mp4 --plan reel.voice.json --texts texts.json [--boxes boxes/*.json] --out review/`** writes `index.json`, one JPEG per voice and `review.html`: one file to send as it is. Per voice it shows the reel's frames at start + 0.5 s, the middle and end − 0.2 s, the caption, the narration, the flags and the times, and a play control with the reel's own sound for that voice's window. Each box of the voice's clip (from a boxes report of the same name) whose time that voice's segment shows comes with the reel's frame at the middle of the box's time (of the part the segment shows), an enlarged crop of the box from that frame, what it points at and that time (`box 2: <what> · 2.00 s`): the plan's `"window"` turns the box's time in the clip into reel time. A box whose time a row's segment does not show is left out of that row, so a clip used twice shows a box on each row whose window holds part of the box's time (a box that spans both windows is on both rows); a box on no row is named on stderr (`sheet: box 1 of take.1 (beat 1, 1.40-2.40 s of the clip) lies in no voiced segment's window: it is on no row`). This also happens to a box in a later segment of a narrated group that is cut from the same clip and has no voice of its own: the page does not show it, and the voice plays over it. A plan written before reels recorded the windows still gives a page: every box of a clip on each of its rows, cropped from the voice's middle frame, with one line on stderr that says so; build the reel again to see the boxes at their own times. The page has no script and its only links are the in-page ones from its top list of rows and flagged rows; a flagged row has a red edge. `texts.json` is `{"<name>": {"caption": "…", "say": "…", "what": ["…"], "sources": ["…"]}}`, every field optional (one text in `what` or `sources` is one phrase; `what[i]` goes with the i-th box of the clip's boxes report, the box's number on the page). **The key is the `name` of a voice in the plan file** (`reel.voice.json`), which is the stem of the segment's clip or picture file (`take.1`, `card-intro`), not the name of the line in `lines.json`: copy the keys from the plan. Two voiced segments cut from one clip share a key and so share their texts. A texts key or a boxes report that matches no voice and a voice with no entry are named on stderr, one line each (`sheet: texts key 'intro' matches no voice of the plan (voices: card-intro, take.1)`); the page is still written and the exit code stays 0, with those rows empty. A boxes report whose `box`, `rect`, `clip`, `std`, `redness`, `change` or `flags` is missing or not what `boxes` writes stops the page with one line.

## 7. What the checks cannot see, and other limits

Each limit stands where its subject is described; this is the list in one place.

- **They cannot hear.** They find where sound is and how loud, not whether a word is pronounced well. A person listens with the review page.
- A sound placed inside a voice's own pause is joined into that voice by the audit and passes.
- The box-under-caption check assumes a one-line caption and compares the vertical range only.
- With a plan written before reels recorded the segments' windows, `sheet` puts every box of a clip on each of its rows, cropped from the voice's middle frame whatever the box's time (it says so on stderr).
- Two voiced segments cut from one clip share their texts entry.
- A box that shows in a later segment of a narrated group, cut from the same clip and without a voice of its own, is on no row of the page, though the voice plays over it; `sheet` names it on stderr.
- The camera check knows a shot's own move length only from the camlog's `"move"`: a camlog recorded before the recorder wrote it is checked with 1.4 s for every shot.
- A voice track shorter than about 3 s that has to be compressed comes out quieter than the loudness target (a 2.5 s tone track: −18.5 LUFS), and the audit then fails it.
- One caption has one time for its boxes.
- The audio options of the reel were run with ffmpeg 4.4 only.
- A reel whose voice is one quiet line among loud ones keeps that line quiet: one gain lifts the whole track (when the track has to be compressed, the levels shift instead).

## What was and was not tried

Frame text and `brief` (2026-11-28). Run: the frame text of a test page at `1920x1080` and `--layout 1280x720` (text inside and outside the zoom, a list cut by `overflow`, hidden elements, a text and a password field, terminal rows split into spans, a reload, a storyboard that throws); `brief` on synthetic takes in its three modes; and `brief --script` on 24 real takes with their 78 caption scripts, against the narrated reel made from them. On those takes a line over its budget and a frame held for that line went together for 57 of 60 lines (the other three were within 2 characters of the budget), the budget was on the safe side by a median 0.7 s, and the two rows where the reel had stopped a moving screen were `"live": true`, with six more. Not run: frame text on those real takes (they were recorded before the recorder kept it), a page with an `iframe` or a shadow root, and no video has been made with these rows yet.

Run on 2026-11-24 on synthetic clips and one real take of a small page: `clip` with `box` in three forms, `box_dur` and `hold`; `voice` (its refusals and its cache) with a stand-in `aws` that writes a tone; `reel` with a picture segment, voices and a group; `audit`, `boxes` and `sheet` on that reel. Speech synthesis itself, the AWS permission and `markRows` on a live terminal were not run for this document; they are described from the code and its tests. Also run on 2026-11-24: the held caption and its box on the counted last frame of 84 synthetic clips (25 and 30 fps, three speeds), the camera check on boxes anchored to a shot, a mark, a note and seconds, `sheet` placing each box at its own time on a synthetic reel and on a copy of a real 70-row plan given its windows, and the three ways of the loudness step on tone tracks.
