// The frame-text file a take writes beside its camlog (<name>.frametext.txt): the text each frame showed, one entry
// per capture. record_demo.mjs writes it with formatFrametext; check_demo.py reads it back (read_frametext).
//
//   == 3.90 shot wide          header: seconds of the take (two decimals), kind, key
//   작업 대시보드              then the text, line by line
//   대기 12 완료 48
//   == 9.12 leave wide
//   ...
//
// kind: shot (the frame once the camera has stopped on a shot), leave (the same view just before the next shot moves
// the camera, written only when it changed), mark (the marked element's own text), text (rec.text(key): the frame now).

export const FRAMETEXT_KINDS = ['shot', 'leave', 'mark', 'text'];
export const FRAMETEXT_MAX = 20000;   // characters of one capture; a longer one is cut and ends with the line [cut]

/** entries: [{ t: seconds, kind: one of FRAMETEXT_KINDS, key, text }] -> the file's content. */
export function formatFrametext(entries) {
  let out = '';
  for (const { t, kind, key, text } of entries) {
    if (!FRAMETEXT_KINDS.includes(kind)) throw new Error(`frame text: unknown kind ${JSON.stringify(kind)} (one of ${FRAMETEXT_KINDS.join(', ')})`);
    // a key is one token of the header: whitespace runs become _, and a missing or empty key is _ (frametext_key in
    // check_demo.py spells a camlog key the same way before it compares)
    out += `== ${Number(t).toFixed(2)} ${kind} ${String(key ?? '').trim().replace(/\s+/g, '_') || '_'}\n`;
    let body = String(text ?? '').replace(/\r\n?/g, '\n');
    if (body.length > FRAMETEXT_MAX) body = body.slice(0, FRAMETEXT_MAX) + '\n[cut]';
    if (body === '') continue;
    // a line of the screen that looks like a header (a terminal can print anything) gets one leading space; so does
    // one that already has spaces before its "== ", so that the reader takes exactly one space off both
    out += body.split('\n').map(line => (/^ *== /.test(line) ? ' ' + line : line)).join('\n') + '\n';
  }
  return out;
}
