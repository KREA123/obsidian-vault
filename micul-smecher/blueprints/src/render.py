"""Rasterise SVG sheets to PNG with the preinstalled Playwright Chromium (no downloads)."""
import sys, os
from playwright.sync_api import sync_playwright

WIDTH = 2400


def render(pairs):
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path='/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
        pg = b.new_page(viewport={'width': WIDTH, 'height': int(WIDTH * 297 / 420)}, device_scale_factor=1)
        for svg, png in pairs:
            data = open(svg, encoding='utf-8').read()
            data = data.replace('width="420mm" height="297mm"', 'width="%d" height="%d"' % (WIDTH, int(WIDTH * 297 / 420)))
            pg.set_content('<html><body style="margin:0;background:#fff">%s</body></html>' % data)
            pg.wait_for_timeout(150)
            pg.locator('svg').screenshot(path=png)
            print('png', png)
        b.close()


if __name__ == '__main__':
    args = sys.argv[1:]
    render([(a, os.path.splitext(a)[0] + '.png') for a in args])
