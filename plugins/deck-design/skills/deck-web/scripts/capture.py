#!/usr/bin/env python3
"""Deck QA: capture every slide with all build steps shown, check for overflow, and dump the translatable strings.

usage: python3 capture.py <index.html | url> <outdir> [--lang en] [--noember] [--inventory keys.json]

  --lang en     render the English side (?lang=en)
  --noember     force "Noto Sans KR" for Latin too — what a visitor without Amazon Ember sees; use it for every English check
  --inventory   write every translatable string (slide, tag, class, key) to a JSON file — the keys of en.json

Writes <outdir>/sNN.png per slide and <outdir>/report.json; prints one line per slide plus its issues.
Issue kinds: past-right / past-bottom (off the 1280×720 canvas), nowrap-clip (a one-line label clipped),
past-box-right / past-box-bottom (text outside its nearest bordered or filled box).
Needs: python3 with playwright and its Chromium; Noto Sans KR or Noto Sans CJK KR installed.
"""
import json, os, sys
from playwright.sync_api import sync_playwright

W, H = 1280, 720

# Fallback when the page does not expose window.deck.keys (an older deck): leaf elements whose children are only inline tags.
LEAF_JS = r"""
() => {
  if (window.deck && window.deck.keys) return window.deck.keys();
  const INLINE = {SPAN:1,B:1,BR:1,A:1,I:1,EM:1,STRONG:1,SUP:1,SUB:1};
  const norm = h => h.replace(/\s+/g,' ').trim();
  const out = [];
  function walk(root, slide) {
    if (!root || root.id === 'notes' || root.id === 'refs' || root.id === 'lang') return;
    if (root.tagName === 'TEMPLATE') { walk(root.content, slide); return; }
    const kids = root.children || [];
    let allInline = true;
    for (const k of kids) if (!INLINE[k.tagName]) { allInline = false; break; }
    if (allInline && (root.textContent || '').trim()) { out.push({slide, tag: root.tagName, cls: String(root.className || ''), key: norm(root.innerHTML)}); return; }
    for (const k of kids) walk(k, slide);
  }
  document.querySelectorAll('.slide').forEach((s, i) => walk(s, i));
  walk(document.querySelector('.below'), -1);
  return out;
}
"""

CHECK_JS = r"""
() => {
  const W = 1280, H = 720;
  const s = document.querySelector('.slide.active');
  const st = document.getElementById('stage').getBoundingClientRect();
  const cs = e => getComputedStyle(e);
  const isBox = e => { const c = cs(e); return parseFloat(c.borderTopWidth) > 0 || parseFloat(c.borderLeftWidth) > 0 || (c.backgroundColor !== 'rgba(0, 0, 0, 0)' && !e.classList.contains('slide')); };
  const rel = r => ({l: r.left - st.left, t: r.top - st.top, r: r.right - st.left, b: r.bottom - st.top});
  const out = [];
  for (const e of s.querySelectorAll('*')) {
    if (e.tagName === 'svg' || e.closest('svg') || e.tagName === 'TEMPLATE') continue;
    if (!(e.textContent || '').trim()) continue;
    const c = cs(e); if (c.visibility === 'hidden' || c.display === 'none') continue;
    const r = rel(e.getBoundingClientRect());
    const label = e.tagName + (e.className ? '.' + String(e.className).split(' ').join('.') : '') + ' "' + (e.textContent || '').trim().slice(0, 40) + '"';
    if (r.r > W + 1) out.push({kind: 'past-right', el: label, by: Math.round(r.r - W)});
    if (r.b > H - 21) out.push({kind: 'past-bottom', el: label, by: Math.round(r.b - (H - 22))});
    if (c.whiteSpace === 'nowrap' && e.scrollWidth > e.clientWidth + 1 && c.overflow !== 'visible') out.push({kind: 'nowrap-clip', el: label, by: e.scrollWidth - e.clientWidth});
    let a = e.parentElement;
    while (a && a !== s && !isBox(a)) a = a.parentElement;
    if (a && a !== s) {
      const ar = rel(a.getBoundingClientRect()); const ac = cs(a);
      const padB = parseFloat(ac.paddingBottom), padR = parseFloat(ac.paddingRight);
      const box = a.tagName + '.' + String(a.className).split(' ').join('.');
      if (r.b > ar.b - padB + 2) out.push({kind: 'past-box-bottom', el: label, box, by: Math.round(r.b - (ar.b - padB))});
      if (r.r > ar.r - padR + 2) out.push({kind: 'past-box-right', el: label, box, by: Math.round(r.r - (ar.r - padR))});
    }
  }
  return out;
}
"""

HEIGHTS_JS = r"""
() => {
  const s = document.querySelector('.slide.active');
  const st = document.getElementById('stage').getBoundingClientRect();
  const out = [];
  s.querySelectorAll('*').forEach(e => {
    if (e.closest('svg') || e.tagName === 'TEMPLATE') return;
    if (!(e.textContent || '').trim()) return;
    const r = e.getBoundingClientRect();
    out.push([e.tagName + '.' + String(e.className).split(' ').join('.'), Math.round(r.top - st.top), Math.round(r.bottom - st.top), Math.round(r.right - st.left)]);
  });
  return out;
}
"""


def main():
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(2)
    url, outdir = sys.argv[1], sys.argv[2]
    lang = 'en' if '--lang' in sys.argv and sys.argv[sys.argv.index('--lang') + 1] == 'en' else 'ko'
    noember = '--noember' in sys.argv
    inv = sys.argv[sys.argv.index('--inventory') + 1] if '--inventory' in sys.argv else None
    os.makedirs(outdir, exist_ok=True)
    if not url.startswith('http'):
        url = 'file://' + os.path.abspath(url)
    if lang == 'en':
        url += ('&' if '?' in url else '?') + 'lang=en'
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': W, 'height': H + 90}, device_scale_factor=1)   # scale = 1 → canvas px = screen px
        pg.goto(url); pg.wait_for_load_state('networkidle')
        if noember:
            pg.add_style_tag(content='body{font-family:"Noto Sans KR","Noto Sans CJK KR",sans-serif !important}')
        pg.evaluate('document.fonts.ready')
        n = pg.evaluate('document.querySelectorAll(".slide").length')
        if inv:
            json.dump(pg.evaluate(LEAF_JS), open(inv, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        report = {}
        for i in range(n):
            pg.evaluate(f'location.hash = "#{i + 1}.99"')        # .99 = every build step on
            pg.wait_for_timeout(120)
            pg.evaluate('document.fonts.ready')
            title = pg.evaluate('document.querySelector(".slide.active").dataset.title')
            pg.locator('#frame').screenshot(path=f'{outdir}/s{i + 1:02d}.png')
            report[i + 1] = {'title': title, 'lang': pg.evaluate('document.documentElement.lang'),
                             'issues': pg.evaluate(CHECK_JS), 'heights': pg.evaluate(HEIGHTS_JS),
                             'steps': pg.evaluate('document.querySelectorAll(".slide.active [data-step]").length')}
        json.dump(report, open(f'{outdir}/report.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        b.close()
    bad = 0
    for k, v in report.items():
        bad += len(v['issues'])
        print(f"s{k:02d} {v['lang']} steps={v['steps']} issues={len(v['issues'])} {v['title']}")
        for x in v['issues'][:12]:
            print('   ', x)
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
