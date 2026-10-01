# SOUL Brand Package v1.0 (October 2026)

The approved logo is **The Glass O**. In the wordmark SOUL, the O is the device's face: a black glass disc with two cream eyes. ARTEMIS DIGITAL S.R.L., Bucharest.

## What's where
| Folder | Contents |
|---|---|
| `Brand-Book/SOUL-Brand-Book.pdf` | The 19-page brand guidelines (A4 landscape). Read this first. |
| `Logo/<Asset>/<Format>/` | Assets: `Wordmark`, `Symbol`, `Lockup-Horizontal`, `Lockup-Stacked`, `Lockup-Stacked-Tagline`. Formats: `SVG`, `PDF`, `EPS`, `AI`, `PNG` (512 / 1024 / 2048 / 4096 px wide). |
| `Logo/All-Variants/` | `SOUL-Logo-AllVariants` (.svg/.pdf/.ai/.eps + PNG preview): every asset in every variant on one artboard. |
| `App-Icon/` | 1024 px icons in the 5 finishes (`PNG-1024`, `SVG`), `iOS/` (20–1024 px, full-bleed, no transparency), `Android/` (mipmap-*dpi launcher icons, Play Store 512 px, adaptive-icon foreground). |
| `Favicon/` | `favicon.svg` (adds a silver bezel in dark mode), `favicon-16.svg` (pixel-fitted master), `favicon.ico`, PNGs from 16 to 128 px, `apple-touch-icon.png`, `icon-192/512.png`. |
| `Colours/` | `SOUL-Colours.ase` (Adobe Swatch Exchange: sRGB group + approximate CMYK group), `SOUL-Colours-RGB.ase`, `colours.json`, `colours.css`. |
| `Fonts/` | Bricolage Grotesque and Martian Mono (variable TTF, SIL OFL 1.1) plus their licences. See `Fonts/README.md`. |

**Variants** (file suffix): `Primary` (ink letters on light grounds), `Black` and `White` (true one colour, eyes knocked out, transparent background), `On-Dark` (warm-white letters, silver bezel, for dark grounds), and `On-Silver`, `On-Graphite`, `On-Midnight`, `On-Ember`, `On-Champagne` (artwork on the aluminium colour, background included). Only the colour-background variants have a background; all others are transparent.

## Which file to use
| Use | Use this |
|---|---|
| Web, apps, UI, email | **SVG**, or **PNG** where SVG isn't supported |
| Word, PowerPoint, Keynote, Google Docs | **PNG** at 1024 or 2048 px |
| Print, signage, packaging (sent to a printer) | **PDF** or **AI**; **EPS** for older workflows |
| Laser etch, deboss, foil, embroidery | `Black` or `White` vector (PDF/AI/EPS/SVG) |
| Social media avatar | `Logo/Symbol/PNG/SOUL-Symbol-Primary_1024px.png` (or `On-<colour>`) |
| App stores | `App-Icon/iOS/AppIcon-1024.png`, `App-Icon/Android/play-store-512.png` |
| Website favicon | `Favicon/` (snippet below) |

```html
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="icon" href="/favicon.ico" sizes="48x48">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
```

## Technical notes
- **All text is outlined.** No file contains `<text>`, fonts or external references. SVGs have a clean `0 0 w h` viewBox and use sRGB hex colours only. The tagline is a solid colour, not transparent.
- **.ai files** are PDF-based: PDF 1.7 vector, saved with the `.ai` extension. Adobe Illustrator opens them natively and keeps full vector editability, as do Affinity and Inkscape. They are not native Illustrator-private-data files.
- **PDF and EPS** are pure vector, generated with cairo from the same SVG. The EPS files are EPSF-3.0 with a tight bounding box.
- **Colour:** sRGB is the master. The CMYK values (in the ASE, JSON and CSS files and the brand book) are approximate starting points, so proof before print. The vector files are RGB, and your printer converts them.
- **Geometry** is identical to the approved kit (`brand/logo/source/kit.py`) and the wordmark in the site header.
- The brand book's product images are **renders / concept (CGI)** of the final MĂRGĂRITAR shape (renders v9).

## Rules in one breath
One face per layout. Keep clear space of ½ Ø on every side. The minimum widths are 72 px or 18 mm for the wordmark and 16 px or 5 mm for the symbol. The eyes are always cream, or knocked out. Never stretch, rotate, recolour, add effects to or retype the logo.
