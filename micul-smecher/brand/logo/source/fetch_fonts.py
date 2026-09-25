"""Download the two OFL variable fonts and cut the static instances the scripts use into ./fonts.
Needs: pip install fonttools skia-pathops playwright pillow numpy && python -m playwright install chromium
Then, from this folder: python fetch_fonts.py && python build.py && python sheets.py && python mock_*.py"""
import os, urllib.request
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont, OverlapMode
os.makedirs("fonts", exist_ok=True)
GF = "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/"
src = {"Bric": GF + "bricolagegrotesque/BricolageGrotesque%5Bopsz,wdth,wght%5D.ttf",
       "Mart": GF + "martianmono/MartianMono%5Bwdth,wght%5D.ttf",
       "Fredoka": GF + "fredoka/Fredoka%5Bwdth,wght%5D.ttf"}
for k, u in src.items():
    urllib.request.urlretrieve(u, f"fonts/{k}-VF.ttf")
os.replace("fonts/Fredoka-VF.ttf", "fonts/Fredoka.ttf")
for w in (500, 600, 700, 800):
    t = TTFont("fonts/Bric-VF.ttf")
    instantiateVariableFont(t, {"opsz": 96, "wdth": 100, "wght": w}, inplace=True, overlap=OverlapMode.REMOVE)
    t.save(f"fonts/Bric-{w}.ttf")
for w in (400, 500, 700):
    t = TTFont("fonts/Mart-VF.ttf")
    instantiateVariableFont(t, {"wdth": 100, "wght": w}, inplace=True, overlap=OverlapMode.REMOVE)
    t.save(f"fonts/Mart-{w}.ttf")
