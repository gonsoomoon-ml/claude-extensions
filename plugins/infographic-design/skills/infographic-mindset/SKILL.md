---
name: infographic-mindset
description: Rules for a single feed-post infographic (LinkedIn or similar) that survives blurring and reposting — one message, one structure drawn as shapes, a body-text budget, a 16 px floor at feed width, one accent, and a line-by-line wording read (every name defined before it is used, titles and verdicts as sentences with a subject, positive wording, evidence beside each verdict) — plus four design schemes taken from finished post images (two-panel concept/system map, question + measured cards + bars, tension headline + structure compare + case, two definition panels + one framework mapped onto the other) and how the image and the post body divide the work. Use when deciding whether a post needs an image, what goes in it, why a draft image reads as a wall of text, or why readers stumble over its words; pair with infographic-build to produce the PNG.
---

# Infographic Mindset

An infographic is the part of the post that survives when the text is cut. The feed shows three lines, a repost shows fewer, the image shows all of it. So the image carries **one message, one structure, one example**; the post body carries the rest.

## The three tests (on the ASCII mockup, before any HTML)

1. **Three-second test** — one line is dominant (`--fs-headline`) and it is the message, not a title. Everything else is clearly smaller.
2. **Blur test** — cover the text. The shapes must still differ: one blob vs a tree, a long bar vs a short bar, two mirrored panels. Boxes that each hold a sentence are a list, not a diagram. Label shapes with two words.
3. **Budget test** — body text inside the scheme's budget (A 400 / B 450 / C 650 / D 950 characters, sources excluded). When content does not fit, cut content. Never grow the canvas, never shrink the type.

The tests catch a wall of text. They do not catch a word nobody can place: that is the read below.

## Canvas and type are fixed by the feed, not by the content

- Portrait **1080 × 1350** (4:5) by default. Landscape only **1200 × 800** (3:2), for the two-panel scheme. Taller than 4:5 is cropped in the feed; wider than 3:2 shows tiny on a phone. Do not copy a reference image's ratio, and do not reason from LinkedIn's maximum limits.
- Type floor **16 px at 1080-width equivalent**: an 1800-wide canvas needs 27 px for the same legibility. `lint.py` normalizes.
- All text near-black. Hierarchy comes from size and weight, never from gray.
- One accent family for stroke, fill, key number and headline. Neutrals do everything else. No second shade typed by hand.

## Pick a scheme, then mock it up

| The message is made of | Scheme |
|---|---|
| numbers you measured | **B · data cards** |
| an architecture that mixed readers must recognize | **A · two-panel** |
| a position comparing two approaches, with a case | **C · structure compare** |
| your framework mapped onto someone else's, when the reader knows neither | **D · define + map** |

Band order, budgets and rules per scheme: `reference/schemes.md`. Rendered examples: `../infographic-build/examples/out/`.

Write the mockup as bands with the exact words. Get it approved. Then hand it to **infographic-build**.

## Read every line before the first render

Render and lint catch overflow, small type and a second accent; they do not catch a word the reader cannot place. On the first post built with scheme D, lint passed on every render except the budget, and most of the review rounds were wording that only reading found. Read the mockup, then every render (`render.py --outline` prints the words in reading order), as someone who has seen neither source:

- **Define every name before you use it.** "7월 지침", "새 규칙" and "4층" meant nothing until a line above said what each one was. The fix was a context line naming both sources and a "…란" panel for each side.
- **Titles, questions and verdicts are sentences with a subject; a comparison names both sides.** A chip that says "그대로" or "남는다" does not say what stays. "새 규칙에 대입한 결과" became "Deep Insight 4계층을 Anthropic 새 규칙에 대입하면".
- **Use the word the reader already knows and the word the source uses; gloss a technical term once.** 지시문 became 프롬프트. 층 and Layer became 계층, the source's own term and shorter than Layer. 컨텍스트 is glossed as "AI의 작업 기억" the first time only.
- **Choose verbs that cannot be read two ways.** 빼기 reads as subtraction or deletion; 옮기기 says what happens to the data.
- **Inside the image, write positively and assert only what the image shows.** 줄이고 read as "this part was wrong", 재점검 and 어긋나지 않고 read as doubt. Caveats, limits and next steps go to the post body.
- **Every verdict shows its evidence, and none claims a direction nobody measured.** Put the rule number or the number on the arrow into the verdict. "가볍게 하면 된다" became "더 다듬을 수 있다".
- **When two numbers sit together, each says what it measures.** "20K → 500" (always loaded) and "3K" (loaded on demand) read as one claim until each had its label. Gloss the unit once ("자·토큰 = AI에 넣는 글의 양").
- **The answer takes the question's verb; the takeaway generalizes the answer as one idea.** 유효할까? → 유효하고. A takeaway that listed three items with three verbs was the line readers found hardest.
- **In a series, reuse the previous post's thesis words and never contradict them.** "일 나누기" read as "always split the work", against the previous post's "split the context only when needed".

## What stays in the post body

Dates, quotes, the full argument, the honest footnote, the second example. If a reader needs it to act, it goes in the body. If a reader needs it to recognize the message, it goes in the image.

How the two divide the work (the posts this plugin came from both did it this way):

- The image is complete and leads. Most readers see the first two or three lines of the body and the image, nothing more.
- The body follows the image's order: the question, the answer, then the reasons.
- Only the question, the answer and the takeaway appear in both, word for word. The image owns the lists, numbers and verdicts; the body owns the why and the how, the examples, the link back to the previous post, and the links.
- The first lines of the body are the feed preview. Put the surprising fact there, never a pointer such as "see the left of the image".
- An image cannot hold a link. One line in the image sends the reader to the body for it ("코드와 수치는 블로그에 · 링크는 본문").

## Red flags (each one came from a real draft)

- "I kept the type size and absorbed the density with a taller canvas" → cut content.
- "The reference is 1:1.375, so I used 1:1.375" → 4:5.
- "Body text 13.5 px, titles 17 px" on a canvas wider than 1080 → normalize to 1080 first.
- Every box carries a sentence → draw the difference, label with two words.
- Eight components per panel plus numbered arrows plus a legend plus a banner → seven boxes, one-word arrow labels, one caption.
- The first line uses a name that nothing above it defines → define it there, or drop it.
- A verdict chip with no subject ("그대로", "남는다") → write the sentence.
- A caveat line inside the image ("판정은 저자 해석", "재측정은 다음 과제") → the post body.

Dated baseline-vs-skill comparisons and the first real post review: `lessons.md`.
