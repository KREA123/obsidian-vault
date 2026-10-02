#!/usr/bin/env python3
"""build_manifest.py -- writes assets/manifest.js for soul_trailer.html (v4):
  * every product cut-out in assets/ (soul_*.webp) with its size and the projected glass outline that post_cut.py wrote
    next to it (renders/v9/src/post_cut.py), so the page can map the live eyes / UI exactly onto the glass;
  * the official SOUL logo SVGs (brand/SOUL-Brand-Package/Logo), embedded as strings so the page can split the
    wordmark into its glyphs for the entrance animation without re-drawing or re-colouring anything.
The page loads it with a <script> tag (no fetch, so it also works from file://).
    python3 build_manifest.py [assets_dir]
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
A = pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else HERE / 'assets'
LOGO = HERE.parent / 'brand' / 'SOUL-Brand-Package' / 'Logo'


def main():
    prods = {}
    for j in sorted(A.glob('soul_*.json')):
        d = json.loads(j.read_text())
        prods[j.stem] = d
    logos = {
        'wordmark': (LOGO / 'Wordmark' / 'SVG' / 'SOUL-Wordmark-Primary.svg').read_text(),
        'wordmark_dark': (LOGO / 'Wordmark' / 'SVG' / 'SOUL-Wordmark-On-Dark.svg').read_text(),
        'stacked': (LOGO / 'Lockup-Stacked' / 'SVG' / 'SOUL-Lockup-Stacked-Primary.svg').read_text(),
        'symbol': (LOGO / 'Symbol' / 'SVG' / 'SOUL-Symbol-Primary.svg').read_text(),
    }
    ui = sorted(p.stem for p in A.glob('ui_*.webp'))
    js = 'window.ASSETS = ' + json.dumps(dict(prods=prods, logos=logos, ui=ui), separators=(',', ':')) + ';\n'
    (A / 'manifest.js').write_text(js)
    print('manifest:', list(prods), ui, len(js) // 1024, 'KB')


if __name__ == '__main__':
    main()
