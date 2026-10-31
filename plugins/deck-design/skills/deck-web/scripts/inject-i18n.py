#!/usr/bin/env python3
"""Put a language map into the deck's <script id="i18n-en" type="application/json"> block, in place.

usage: python3 inject-i18n.py <index.html> <en.json> [--id i18n-en]

en.json: {"_comment": "...", "text": {"<Korean innerHTML, whitespace-normalized>": "<English innerHTML>", ...}}
The keys come from `capture.py --inventory keys.json`; "_comment" is dropped. Exactly one block must exist.
"""
import json, re, sys


def main():
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(2)
    html_path, json_path = sys.argv[1], sys.argv[2]
    block_id = sys.argv[sys.argv.index('--id') + 1] if '--id' in sys.argv else 'i18n-en'
    html = open(html_path, encoding='utf-8').read()
    data = json.load(open(json_path, encoding='utf-8'))
    data.pop('_comment', None)
    if 'text' not in data or not isinstance(data['text'], dict):
        sys.exit('en.json needs a "text" object')
    blob = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    pat = r'(<script id="%s" type="application/json">)(.*?)(</script>)' % re.escape(block_id)
    new, n = re.subn(pat, lambda m: m.group(1) + blob + m.group(3), html, flags=re.S)
    if n != 1:
        sys.exit(f'expected exactly one <script id="{block_id}"> block, found {n}')
    open(html_path, 'w', encoding='utf-8').write(new)
    print(f'injected {len(blob)} bytes, {len(data["text"])} strings into {html_path}')


if __name__ == '__main__':
    main()
