# The pointer, presses, and the camera on ordinary web sites

Since 1.6.0 a press shows in the video: a pointer travels to its target and a press mark opens there. The press is made with the real mouse, so a site's links and buttons get what a person's press gives them. This file also holds what the camera does on a site that was not built for it: a long page, an in-page anchor, a link to another page, a new tab, a dialog.

1. [Why the real mouse](#1-why-the-real-mouse)
2. [`rec.tap`, `rec.hover`, `--no-pointer`](#2-rectap-rechover---no-pointer)
3. [What a press does, step by step](#3-what-a-press-does-step-by-step)
4. [What the camlog holds](#4-what-the-camlog-holds)
5. [A link to another page](#5-a-link-to-another-page)
6. [The camera on a long page](#6-the-camera-on-a-long-page)
7. [New tabs and dialogs](#7-new-tabs-and-dialogs)
8. [Captions, boxes and the brief](#8-captions-boxes-and-the-brief)
9. [Recording an older storyboard again](#9-recording-an-older-storyboard-again)
10. [Limits](#10-limits)

## 1. Why the real mouse

Before 1.6.0 `tap(locator)` sent one click event to the element. Measured on 2026-11-28 on a test page, at `1920x1080` and `--layout 1280x720`:

| On the page | The click event | The real mouse |
|---|---|---|
| a button that listens for click | pressed | pressed |
| a button that listens for pointerdown or mousedown (tabs, dropdowns, selects of component libraries) | not pressed, without a word | pressed |
| a menu that opens on hover, a hover colour | nothing | shown |
| a link wrapped over two lines | pressed | its bounding box's centre lies outside it: the first line is pressed |
| a button under another element | the button gets the event | what covers it would be pressed |
| a link far down the page | gets the event | out of reach until the frame shows it |

So a press is the real mouse, and the cases where the mouse cannot reach are handled and written down (section 3). The headless browser draws no pointer of its own; the recorder draws one.

## 2. `rec.tap`, `rec.hover`, `--no-pointer`

| Call | What it does |
|---|---|
| `await rec.tap(locator, { key, label })` | the pointer travels to the locator's first element and presses it; `key` and `label` are optional and go into the camlog |
| `await tap(locator)` | the function a storyboard is handed: the same `rec.tap` |
| `await rec.hover(locator, { key, label })` | the pointer travels there and stays: for a menu that opens on hover, before the `rec.tap` on its item |

`node scripts/record_demo.mjs … --no-pointer` records without the pointer: `tap` sends the click event as before 1.6.0 and writes nothing into the camlog, `rec.hover` does nothing and says so once. The other changes of this file (sections 5 to 7) apply to every take.

The pointer is one element under `<html>`, outside `<body>`: the camera's transform is on `<body>`, so the pointer stays in frame pixels and keeps its size under any zoom. It is a white arrow 28 px high; the press mark is a blue ring (`#1f6feb`) that grows from 28 to 56 px. It first appears at 60 % of the frame's width and height, and stays where it last pressed. It lies in the browser's top layer, so a `showModal()` dialog does not cover it. It carries no text: the frame text never holds it.

A pressed input has real focus, so `page.keyboard.type(…)` types into it.

## 3. What a press does, step by step

1. It waits for the element to be visible (30 s, then the take fails as it always did).
2. It waits for the camera to stop: a box measured while the camera moves is not where it will be. A `rec.tap` right after a shot therefore starts up to 1.4 s later.
3. It brings the element into the frame. A scrolling box around it (a list, a pane) is scrolled by the least that shows it. When the press point lies outside the frame or within 40 px of its edge, or the frame cuts the element's first line (it must lie wholly in the frame, 8 px clear of its edges, unless it is too large for that), the camera moves there at the zoom it has, in 0.8 s, with the point in the middle of the frame as far as the page allows: a `shot` of key `pan` in the camlog, like any shot. The press waits for that move too.
4. It measures the press point live: the centre of the element's first line. When the point is still outside the frame (the camera cannot go there) or the element has no box any more (it was hidden meanwhile), the click is sent as the event, the entry gets `"outside": true`, stderr says `tap <key>: outside the frame, sent as a click event` (or `no longer on the page`), and the pointer does not move.
5. The pointer travels there (0.25 s plus 0.35 s per 1000 px, at most 0.9 s) and the real mouse goes along, so what lies on the way is hovered.
6. The press mark opens. It comes 0.2 s before the press so that it is in the video even when the press leaves the page at once.
7. At the end of those 0.2 s it looks at what is on top of the point now. When that is the element or something inside it, the mouse goes down and 0.08 s later up. When it is not (an overlay, a banner, or the element moved away under the pointer), the click is sent as the event, the entry gets `"covered"`, and stderr says `tap <key>: covered by <tag#id.class>, sent as a click event`. The mark fades over 0.35 s.

A press never stops a take. `rec.hover` does steps 1 to 5, looks at what is on top, and presses nothing.

## 4. What the camlog holds

| Entry | Fields |
|---|---|
| `tap` | `"t"` (the mouse went down), `"key"`, `"label"`, `"rect"` (the element's first line on the frame), `"point"` (`[x, y]`), `"text"` (the element's own text, 80 characters; a password field's value is never read); when they apply `"covered"`, `"outside"`, `"same_tab"` |
| `hover` | the same without `"text"` and `"same_tab"` |
| `shot` | of key pan: the camera's move to a press target, with `"move": 0.8`; of key scroll: a window scroll the camera took (section 6), with `"move": 0` |
| `load` | `"url"` (no query, no fragment); `"soft"` (`true`) when only the `<body>` was swapped |
| `popup` | `"url"` of a tab the page opened |
| `dialog` | `"type"` and `"message"` (200 characters) |

## 5. A link to another page

A link that loads a document throws away everything on the page. After the first `rec.install()` the recorder puts the camera back on every new document by itself (its top frame only), wide, and the pointer back where it last pressed; the camlog gets a `load` entry. `rec.install()` may still be called again; it is harmless.

```js
await Promise.all([page.waitForNavigation({ waitUntil: 'load' }), rec.tap(page.locator('a.docs'), { key: 'docs' })]);
await page.waitForSelector('main');
await rec.reset('docs', 'the docs page');   // a shot of the new page: its own row in the brief, its own frame text
```

A site that swaps its `<body>` without loading a document is treated the same way (`"soft": true`). A site that changes its view without either (most single-page apps) keeps the camera where it is: wait for what you need, then take a shot.

A link, an area or a form that would open another tab (its own `target`, a button's `formtarget`, the page's `<base target>`) is made to open in this one just before the press, because a take records one tab; the entry gets `"same_tab": true`.

## 6. The camera on a long page

- **How far down it goes.** The page's height is the body's content, not the body's own box: a page whose content is positioned absolutely, or whose `<body>` has `height: 100%`, used to stop the camera at the body's height. Its width is the body's own box, as before: a site parks things off the side (a skip link at `left: 100%`), and they are not part of the page.
- **A page without a doctype** (quirks mode) keeps the body's own box as its height, as before: there the body's `scrollHeight` is the viewport's and grows with the camera.
- **A window scroll.** An in-page anchor (`href="#section"`), the page's own code or a focus can scroll the window. When the scroll has ended the camera turns it into its own position and puts the window back at 0, 0: no pixel changes (measured 2026-11-28), and the camera's numbers, the rects it logs and the frame text are true again. The camlog gets a `shot` of key scroll. A window that keeps scrolling (a log that follows its end) is one such shot, not one per scroll: the entry takes the camera's new place and the frame's new text until something else is written. Before 1.6.0 the next shot snapped the window back and the frame jumped.
- **The page's background.** The camera no longer paints `<html>`. Since the fork its style gave `<html>` a dark background (`#0b0f14`); on a light page that sets no background of its own, dark text then stood on dark. `--backdrop <css colour>` paints it as before.
- **A sticky or fixed header** stays at the top of the page, not of the frame, once the camera has moved: the camera moves the `<body>`, and the header is positioned in it. A press on something in the header then begins with a pan back to it.

## 7. New tabs and dialogs

A tab the page opens by itself (`window.open`) is closed and written down as a `popup` entry; stderr names its address and says `a take records one tab, open it with page.goto to show it`. When the storyboard listens for `popup` or `page` itself, the tab is left open and only written down.

A dialog (`alert`, `confirm`, `prompt`, `beforeunload`) is not drawn in the video, and with nobody listening the browser dismisses it: a button that asks "Really?" then does nothing, without a word. The recorder answers it and writes a `dialog` entry: `--dialogs accept` (the default), `--dialogs dismiss`, or `--dialogs leave` (the recorder does not listen, as before 1.6.0). When the storyboard listens for `dialog` itself the recorder only writes it down.

## 8. Captions, boxes and the brief

- A beat is anchored to a press by its key: `"at": "tap:<key>"`, the n-th of that key `"at": "tap:<key>#2"`, or without keys `"at": "tap#2"` (the second press of the take); a hover likewise, `"at": "hover:<key>"`. A press anchor survives a re-record, as a note does.
- A highlight box can point at what was pressed: `"box": "tap:<key>"` (the element's first line, grown like a `mark:` rectangle).
- In `brief` a press is in its row's `"notes"` with its key, label and text: what was pressed, as the screen spelled it.

## 9. Recording an older storyboard again

Switched off with `--no-pointer`:

- every `tap` takes 0.7 to 1.3 s longer (the travel and the press), and one right after a shot waits for the camera;
- the page gets real mouse events: hover effects show, a button that listens for pointerdown is pressed;
- a press on something outside the frame moves the camera there;
- content that the camera slides under a resting pointer is hovered.

In every take, with or without the pointer:

- the camera goes down to the end of a page whose content is longer than its body (section 6);
- a window scroll becomes the camera's position (section 6);
- the camera is back on a new document and on a swapped body (section 5). A storyboard that took a missing `window.__cam` for the sign of a reload therefore never sees one and waits until its own timeout: count the page's `load` events instead (`page.on('load', …)`), which tells of a reload on every version;
- the camera does not paint the page's background; `--backdrop "#0b0f14"` is the look of before;
- a tab the page opens is closed unless the storyboard listens for it (section 7);
- a dialog is accepted; `--dialogs leave` is the behaviour of before;
- the page's Content-Security-Policy is not enforced in the recorder's browser: it would block the camera's style and, with Trusted Types, the pointer.

## 10. Limits

- A press target inside an `iframe` is pressed where the frame shows it, but it is not brought into the frame: frame it with a shot first. Inside an `iframe` of another origin its place comes from the browser's own measure, which can be off under `--layout`; the press is then sent as the event and flagged, not made in the wrong place.
- A camera move after `rec.hover` slides the page from under the pointer and closes the menu: zoom first, then hover.
- What the browser draws in its top layer (a `showModal()` dialog, a popover) is not moved or zoomed by the camera. Its buttons are pressed and the pointer shows over it, but take such shots wide: under a zoom a mark's rectangle and the frame text are off for what is inside it.
- A dialog that opens while the pointer rests covers the pointer until it is used again.
- A tab opened by `window.open` is not followed.
- A sticky or fixed header does not follow the frame (section 6).
- A scrolling box is scrolled to its target at once, not smoothly.
- There is one arrow (no hand over links), and no drag, right click, double click or wheel.

## What was and was not tried

Run on 2026-11-28: the tests of `tests/test_pointer.py` at both layouts (presses on pointerdown, mousedown and click buttons, a hover menu, a wrapped link, a press while the camera moves, a `showModal()` dialog, a covered button, one off the page, one that moves away from the mouse, a row in a scrolling box, a far link on two shapes of long page, an in-page anchor with and without smooth scrolling, a scroll under a 2x camera, a link to another document with and without `target=_blank`, a swapped body, a `confirm` under each `--dialogs` value and with the storyboard listening, `window.open`), with the frames of three presses looked at; and one take of 31.5 s on a public documentation site (a hover menu, a link that loads a document, a link the site routes itself, an in-page anchor, a button, a link at the page's end): no warning, every press in the camlog. That take showed three defects, fixed since: the frame text lost spaces that are text nodes of their own, the camera painted a light page dark, and a pan slid the page sideways.

Also on 2026-11-28, a real web app that sends a Content-Security-Policy, whose buttons are form posts answered with a redirect and whose page reloads itself when a job ends: five takes, four of them from storyboards written for an earlier version. The take without a press had the camera values of its earlier recording at all seven shots, and its earlier caption script cut a clip of the same length. Five presses (three from the older storyboards, two with a key in a new one, one of them on a button outside the frame) were all made with the real mouse, none flagged, each with its `load` entries after it; a caption anchored to a press held, and four of the takes were joined into a reel of 95.7 s and into a narrated one of 143.1 s (twelve voices, the earlier narrated scripts' boxes and held captions; its audit passed at −16.0 LUFS, which is a measurement and not a listening check). Two things came of it. The older storyboards' helper waited for a reload by looking for a missing `window.__cam` and never saw one (section 9): on a local page that reloads once it ended in 3.6 s under 1.5.0 and ran into its timeout under 1.6.0, and counting the page's `load` events ended it on both. And a button whose press point lay 42 px inside the frame was pressed with its top cut off by the frame's edge: since then the camera also goes to a target the frame cuts (section 3).

Not run: a site behind a login, a real site that swaps its body, a press target inside an `iframe` or a shadow root on a real site, a real site at `--layout 1280x720`, and no video has been published with this version yet.
