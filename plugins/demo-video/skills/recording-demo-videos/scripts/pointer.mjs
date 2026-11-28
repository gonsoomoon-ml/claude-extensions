// The pointer a take shows and the numbers of a press (1.6.0). record_demo.mjs moves this drawn pointer and the real
// mouse together, so the video shows where a press lands and the page gets the events a person's press gives it.
//
// The pointer is one element under <html>, outside <body>: the camera's transform is on <body>, so the pointer stays in
// frame (viewport) pixels and keeps its size under any zoom. It lives in the browser's top layer (popover="manual"),
// because a showModal() dialog is drawn above every z-index; a top-layer element opened later covers an earlier one,
// so the pointer is raised again each time it is used. It carries no text, so the frame text never holds it.

export const POINTER = {
  id: '__demo_pointer',
  size: 28,                 // px, the arrow's height on the frame
  ring: '#1f6feb',          // the press mark: a ring in the caption box's blue,
  ringFrom: 28, ringTo: 56, ringWidth: 4,   // growing from 28 to 56 px across, 4 px line
  appear: 0.2,              // s the pointer takes to fade in where it first shows,
  start: [0.6, 0.6],        // at this share of the frame's width and height
  pressLead: 0.2,           // s the press mark shows before the mouse goes down (a link may leave the page at once)
  pressHold: 0.08,          // s the mouse stays down
  ringFade: 0.35,           // s the mark takes to fade after that
  pan: 0.8,                 // s a camera move to a target outside the frame takes
  edge: 40,                 // px from the frame's edge within which a press point still counts as outside
  clear: 8,                 // px the pressed element's first line keeps from the frame's edge, or the camera goes to it
  text: 80,                 // characters of the pressed element's own text kept in the camlog
};

/** Seconds the pointer travels over `px` of the frame: 0.25 s plus 0.35 s per 1000 px, at most 0.9 s. */
export const travelSeconds = px => Math.min(0.9, Math.round((0.25 + 0.35 * px / 1000) * 1000) / 1000);

/** The page code that defines window.__demoPointer once per document. All its coordinates are frame pixels; `zoom` is
 *  the recorder's --layout zoom (html { zoom }), which the element's own CSS pixels are divided by.
 *    place(x, y)          put the pointer at a point (creating it; it fades in when it was not showing)
 *    move(x, y, seconds)  travel there
 *    ring(x, y)           start a press mark there
 *    raise()              take the pointer to the top of the top layer
 *    at()                 where it is, [x, y], or null before it was placed */
export const pointerJs = zoom => `
(() => {
  if (window.__demoPointer) return;
  const P = ${JSON.stringify(POINTER)}, Z = ${Number(zoom)};
  const px = v => (v / Z) + 'px';
  const tip = P.size / 28;   // the arrow's tip lies one unit of its 20 x 28 drawing in from its corner
  let host = null, arrow = null, at = null;
  const raise = () => { try { if (host.matches(':popover-open')) host.hidePopover(); host.showPopover(); } catch (e) { /* no popover API: stays in the page's own layer */ } };
  const ensure = () => {
    if (host && host.isConnected) return;
    host = document.createElement('div');
    host.id = P.id;
    host.setAttribute('popover', 'manual');
    host.setAttribute('aria-hidden', 'true');
    host.style.cssText = 'position:fixed;inset:0;margin:0;border:0;padding:0;width:100%;height:100%;background:transparent;overflow:visible;pointer-events:none;z-index:2147483647';
    arrow = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    arrow.setAttribute('viewBox', '0 0 20 28');
    arrow.style.cssText = 'position:absolute;left:0;top:0;width:' + px(P.size * 20 / 28) + ';height:' + px(P.size) + ';overflow:visible;opacity:0;filter:drop-shadow(0 1px 2px rgba(0,0,0,.55))';
    const shape = document.createElementNS('http://www.w3.org/2000/svg', 'path');   // built node by node: a page with Trusted Types refuses innerHTML
    for (const [k, v] of [['d', 'M1 1 L1 22 L6.5 17 L10.5 26 L14 24.5 L10 15.5 L18 15.5 Z'], ['fill', '#fff'], ['stroke', '#0b0f14'], ['stroke-width', '1.5'], ['stroke-linejoin', 'round']]) shape.setAttribute(k, v);
    arrow.appendChild(shape);
    host.appendChild(arrow);
    document.documentElement.appendChild(host);
    raise();
  };
  const set = (x, y, seconds) => {
    arrow.style.transition = 'transform ' + seconds + 's cubic-bezier(.4,0,.2,1), opacity ' + P.appear + 's linear';
    arrow.style.transform = 'translate(' + px(x - tip) + ',' + px(y - tip) + ')';
    at = [x, y];
  };
  const place = (x, y) => { ensure(); set(x, y, 0); void arrow.getBoundingClientRect(); arrow.style.opacity = '1'; };
  const move = (x, y, seconds) => { ensure(); set(x, y, seconds); arrow.style.opacity = '1'; };
  const ring = (x, y) => {
    ensure();
    const mark = document.createElement('div');
    mark.style.cssText = 'position:absolute;box-sizing:border-box;border-radius:50%;border:' + px(P.ringWidth) + ' solid ' + P.ring
      + ';left:' + px(x) + ';top:' + px(y) + ';transform:translate(-50%,-50%)';
    host.insertBefore(mark, arrow);
    const shown = P.pressLead + P.pressHold, all = shown + P.ringFade;
    mark.animate([{ width: px(P.ringFrom), height: px(P.ringFrom), opacity: 1 },
                  { width: px(P.ringTo), height: px(P.ringTo), opacity: 1, offset: shown / all },
                  { width: px(P.ringTo), height: px(P.ringTo), opacity: 0 }], { duration: all * 1000, fill: 'forwards' }).onfinish = () => mark.remove();
  };
  window.__demoPointer = { place, move, ring, raise: () => { ensure(); raise(); }, at: () => at };
})();`;
