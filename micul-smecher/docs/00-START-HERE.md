# SOUL: start here

*The complete SOUL package · 25 Sep 2026 · ARTEMIS DIGITAL S.R.L., Bucharest · assembled from the vault `micul-smecher/` + the notes in `01 Afaceri/Micul Șmecher/`.*

## Pe scurt (RO, pentru Andu)
- **SOUL** (mărimea **M**, decizia din 25 sep.) e o pietricică din aluminiu, în picioare, de **90 × 103 × 31,5 mm**, cu ecran rotund de **2,8″ (480 × 480)** sub sticlă neagră și doi ochi vii. Forma e v6 (HOPA), mărită uniform.
  - Funcționează **fără AI**, cu **Claude-ul tău**, cu **ChatGPT-ul tău** sau cu cheia ta API.
  - Are **SoulOS** cu tastatură (scrii lui Claude, notițe, alarme).
  - Doarme în capsula **OU**.
- **Ce e gata:**
  - designul final M (randări **v8**) + logo-ul „The Glass O” (`brand/logo/`);
  - firmware-ul: 61/61 de teste, compilează și pentru placa **Waveshare ESP32-S3-Touch-LCD-2.8C** (`lcd28`);
  - serviciul AI: 49/49 de teste (fără AI / Claude / ChatGPT, cheie proprie criptată, conector MCP);
  - SoulOS pe web (limbajul „Orbit”, 162 de teste), pagina de lansare în engleză;
  - kitul P0 (CAD, STL, STEP), planurile tehnice M, dosarul PR BI PoC 1.1.
- **Ce urmează:** comanzi placa 2.8C + piesele ([`prototip/COMANDA.md`](../prototip/COMANDA.md)), printezi P0, flash-uiești, filmezi (= dovada TRL 3), apoi CNC.
- **Bani:** **PR BI 1.1 Proof of Concept** prin ARTEMIS DIGITAL (€191k, 24 luni) — [`investors/poc-1.1/`](../investors/poc-1.1/).

> Notă: 01-BOM, 02-MANUFACTURING și 05-LAUNCH-PLAN au fost scrise pentru mărimea S (1,75″). Diferențele pentru M sunt în tabelul de mai jos; restul (procese, furnizori, conformitate, calendar) rămâne valabil.

---

## What SOUL is

SOUL is a personal AI object you keep on your desk and hold in your hand. The pitch: "The labs make the brain. We make the body and the soul."

**Final design: v6 "HOPA", size M** (renders: `renders/v8/`)
- An **upright aluminium pebble, 90.0 × 103.1 × 31.5 mm**, black glass Ø74.3 mm.
- **6061-T6**, fine bead-blasted, colour-anodised: Silver, Graphite, Midnight, Ember, Champagne.
- **2.8" round IPS (480 × 480)** behind black glass. **Nothing else on the face.**
- Flat foot, speaker in the side seam, charging from the bottom in **OU**, the egg capsule. No loop: hanging comes from a case accessory.

**What it does**
- **Live eyes**, a round keyboard (≈ 6.7 mm keys), notes, alarms, timers, all **offline**.
- AI modes: **none / your Claude / your ChatGPT / your own API key**; approve Claude Code requests by holding the glass.

**Hardware today:** Waveshare **ESP32-S3-Touch-LCD-2.8C** (ST7701 RGB, GT911 touch, IMU, RTC, charger, buzzer). Voice needs an INMP441 mic + MAX98357 amp (I2S), see `firmware/README.md`.

**First sale: Founders 00** — 25 numbered units at **€349**, only after CE radio tests. Standard from €249 later.

### What changed from S to M
| | S (old) | **M (now)** |
|---|---|---|
| Body | 63 × 72 × 27 mm | **90 × 103 × 31.5 mm** |
| Screen | 1.75" AMOLED 466² | **2.8" IPS 480²** (grey blacks; hidden by black glass + dark UI) |
| Board | ESP32-S3-Touch-AMOLED-1.75 (~€33) | **ESP32-S3-Touch-LCD-2.8C (~€35–40)** + optional mic/amp (~€6) |
| P0 DIY body | 63 × 75 × 29.5 | see `prototip/README.md` (bigger, because the board's glass is glued) |
| CNC shell cost | [E] | ≈ +30–40 % material/time vs S [E] |
| Renders / drawings | `renders/v6`, `blueprints/` rev A | **`renders/v8`, `blueprints/final/`** |

## State of every part

| Part | State | Where | Next step |
|---|---|---|---|
| Industrial design (v6 HOPA, size M) | ✅ **done** (CGI renders, not photos) | `renders/v8/` (+ `renders/v6/README.md` for CMF/hex) | Validate with the P0 in hand |
| Logo „The Glass O” | ✅ done | `brand/logo/` | Trademark search |
| Size study (v7 S/M/L) | ✅ **decided: M** (25 Sep) | `renders/v7/`, `research/12` | – |
| Production CAD of v6 (Ø52 custom glass, 27 mm) | ❌ **to do** | only the Blender mesh `renders/v6/src/` | After P0 rev C; needs the custom PCB |
| DIY prototype P0 (CAD, STL, STEP) | 🟡 **prototype, in progress** (another agent is finishing it) | `prototip/cad/soul_p0.py`, `prototip/stl/`, `prototip/step/` | Plastic variant exported; alu has only the front shell; README/COMANDA not written yet (see gaps) |
| Technical drawings of the final design (M) | ✅ `blueprints/final/` | older: `blueprints/` rev A + `v3` | Update after P0 rev B |
| Older parametric shells (coin/drop/gem/cloud) | ✅ done, legacy | `cad/` | Reference only |
| OU capsule | 🟡 designed (research/09 §4) + rendered; **no CAD** | `renders/v6/soul_v6_ou_night.png`, `renders/v5/` | CAD for the SLA pilot capsule |
| Firmware "Suflet" + SoulOS v1 modules | ✅ **compiles** (lcd28 + amoled143/175/sim), **61/61 tests pass**; ❌ not yet run on hardware | `firmware/` | First flash + calibration |
| SoulOS (the full OS) | 🟡 ~10 % of 1.0; spec + architecture done | `os/SPEC.md`, `os/ARCHITECTURE.md` | Roadmap 0.1 → 1.0 |
| SoulOS web prototype | ✅ done | `os/index.html` (= `site/os.html`) | User tests of the keyboard |
| AI service (companion, 3 modes, BYO key, MCP) | ✅ **49/49 tests pass**; no production deploy, no OAuth | `ai/` | OAuth + EU hosting + voice |
| Phone app | ❌ to do | spec in `os/ARCHITECTURE.md` §5 | SoulOS 0.4 |
| Voice | ❌ to do | plan in `ai/README.md` | SoulOS 0.5 (xiaozhi-esp32) |
| Landing page | ✅ done (SOUL M v8 renders, logo, English default + RO toggle, €349); waitlist in demo mode | `site/` + https://claude.ai/artifact/BUAPPdP1W5xnCvSVcsQXoX | Set `WAITLIST_ENDPOINT`, legal footer |
| Media (simulator clips, keyboard/time-picker frames) | ✅ done | `media/` | Real-device clips after P0 |
| Research (market, hardware, compliance, AI, brand, design, aluminium, competitors, screen) | ✅ done (01–12 + design-max) | `research/` | – |
| Investor pack, funding | ✅ done | `investors/` (DECK, INVESTORS, FINANTARE-ROMANIA, **poc-1.1/** official PR BI PoC 1.1 annexes) | PoC application, Nov 2026 |
| BOM, manufacturing, compliance, launch plan | ✅ this package | `docs/` | Replace [E] prices with real quotes |
| CE / RED / EN 18031 | ❌ to do | [04-COMPLIANCE](04-COMPLIANCE.md) | Lab quotes, week 1 |
| Trademark "SOUL" | ❌ to do (**high conflict risk**) | [04-COMPLIANCE](04-COMPLIANCE.md) | TMview search this week |

## The documents in this package

| # | Document | Read it for |
|---|---|---|
| 01 | [01-BOM.md](01-BOM.md) + [BOM.csv](BOM.csv) | Every part, supplier, URL, price at qty 1/10/25; totals (P0 ≈ €211 plastic / €363 alu; Founders 00 ≈ €190 per unit + ≈ €15k one-off) |
| 02 | [02-MANUFACTURING.md](02-MANUFACTURING.md) | Which file goes to which supplier, CNC/print settings, colours + hex, tolerances, assembly, QC, packaging, OU, base marking, 1k/10k |
| 03 | [03-SOFTWARE.md](03-SOFTWARE.md) | How to build, flash, test and run the firmware, AI service, MCP connector, SoulOS prototype and site (verified today) |
| 04 | [04-COMPLIANCE.md](04-COMPLIANCE.md) | CE/RED, EN 18031, battery, WEEE/ANMAP, GPSR, AI Act, AI policies, trademark, GDPR, with owners, costs and order |
| 05 | [05-LAUNCH-PLAN.md](05-LAUNCH-PLAN.md) | Week-by-week plan to Founders 00, costs, funding in 5 lines, one checklist |
| 06 | [06-SUPPLIERS.md](06-SUPPLIERS.md) | Every supplier and contact link in one table |

## Map of every file (vault folder `micul-smecher/`)

| Folder | Contents |
|---|---|
| `docs/` | This package. `_tools/bom.py` regenerates `BOM.csv` and the BOM tables' numbers. |
| `renders/v8/` | **Final design, size M**: hero, family, side, hand, desk, typing, OU at night, alive gif/mp4, README, `src/` |
| `brand/logo/` | Logo kit „The Glass O”: SVG/PNG, favicon, app icons, mockups |
| `renders/v6/` | Same look at size S: hero, family (5 colours), side, back, bottom, hand, macro, OU at night, `alive.mp4/.gif`; `README.md` (CMF, hex, geometry); `src/` (Blender) |
| `renders/v7/` | Size study S/M/L: `soul_v7_hands.png`, `soul_v7_lineup.png`, `soul_v7_typing.png`, README |
| `renders/v4`, `v5`, root `*.png` | Earlier concepts (shape family, HOPA rocker, glass/pearl), for history |
| `prototip/` | DIY P0: `cad/soul_p0.py` (CadQuery; variants plastic / alu / alu_band), `soul_geom.py`, `render_p0.py`, `blueprints_p0.py`, `report_plastic.json`; `stl/plastic/`, `stl/alu/`, `stl/assembly/`; `step/plastic/`, `step/alu/`, `step/soul_p0_plastic_ASSEMBLY_with_board.step` |
| `cad/` | Older OpenSCAD shells (4 shapes × 2 boards, 33 checked STLs, renders) |
| `blueprints/` | A3 sheets rev A (GA, section, exploded + BOM, 1.75 prototype) + `v3/`; generators in `src/` |
| `firmware/` | PlatformIO project: `src/` (board), `lib/Suflet/src/` (engine + SoulOS modules), `sim/`, `test/`, `tools/` (fonts, word lists, media export) |
| `ai/` | Python `suflet_ai`: companion, actions, providers (rules / Claude / ChatGPT), keystore, MCP server, FastAPI server, tests |
| `os/` | `index.html` (SoulOS prototype), `SPEC.md`, `ARCHITECTURE.md`, `research/01–04`, `lang-mockups/`, `screenshots/` |
| `site/` | `index.html` (landing), `preview.html`, `os.html`, `media/`, `README.md` (config, waitlist, deploy, launch checklist) |
| `media/` | Simulator clips (idle, boop, purr, dizzy, sleep, missed_you, rare, ai_talk, claude_buddy, night) + SoulOS keyboard/time-picker frames |
| `research/` | 01 market · 02 hardware · 03 compliance · 04 AI companions · 05 brand/product dev/funding · 06 design v2 · 07 amulet language · 08 CMF · **09 final design (HOPA)** · **10 aluminium case** · 11 competitors · **12 bigger screen** · `design-max/` (CMF, creatures, dock, icons, trends, render brief) |
| `investors/` | `DECK.md`, `INVESTORS.md`, `FINANTARE-ROMANIA.md`, **`poc-1.1/`** (official PR BI PoC 1.1 annexes: business plan template, ETF grid, scientific report model, TRL levels) |
| `dist/SOUL-package.zip` | This package zipped (~30 MB; see its `README.md` and `SKIPPED.txt`). Rebuild it with `python3 docs/_tools/build_zip.py`. The big plastic shell STEPs and the 113 MB assembly STEP are left out; the plastic parts print from the STLs. |

Vault notes (`01 Afaceri/Micul Șmecher/`):
- „Micul Șmecher" (the hub);
- „De continuat — SOUL" (the to-do list);
- „Design produs v3 — SOUL amuleta" and „Design produs v2 — SUFLET Pebble";
- „Produs și dezvoltare";
- „Conformitate și riscuri";
- „Planul de bani";
- „Brand și lansare";
- „Piață și concurență";
- „Viziunea — momentul iPhone".

## Known gaps (25 Sep 2026)

1. **Nothing has run on real hardware yet.** First job: flash the 2.8C board, film it (TRL 3 evidence for the grant).
2. **No production CAD for the final M body** (custom glass Ø74, custom PCB). P0 is the buildable pilot around the stock board.
3. **No OU capsule CAD** (renders only).
4. Every price is [E] until real quotes arrive; 01-BOM/02-MANUFACTURING numbers are for S, adjust per the S→M table.
5. Trademark "SOUL" is unchecked (**high conflict risk**).
6. PoC 1.1: expert for the scientific report, technical coordinator, 2 letters of intent, ARTEMIS eligibility checks (see `investors/poc-1.1/REVIEW.md`).
