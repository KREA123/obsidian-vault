# SOUL: start here

*The complete SOUL package · 25 Sep 2026, size updated 22 Oct 2026 (S = product, M = prototype) · ARTEMIS DIGITAL S.R.L., Bucharest · assembled from the vault `micul-smecher/` + the notes in `01 Afaceri/Micul Șmecher/`.*

## Pe scurt (RO, pentru Andu)
- **SOUL S = produsul** (decizia din **20.10.2026**, `03 Decizii/Jurnal decizii.md`): o pietricică din aluminiu în forma **MĂRGĂRITAR**, în picioare, de **63 × 70,8 × 23 mm**, cu ecran rotund **AMOLED de 1,75″ (466 × 466)**, negru adevărat, sub sticlă neagră plată **Ø52**, și doi ochi vii. Placa de dezvoltare: **Waveshare ESP32-S3-Touch-AMOLED-1.75** (`pio run -e amoled175`). Baterie LiPo **750 mAh**, ~27 h [estimare]. Cifrele: [`size-s.json`](size-s.json) (sursa unică) și [`12-SIZE-S.md`](12-SIZE-S.md).
  - Funcționează **fără AI**, cu **Claude-ul tău**, cu **ChatGPT-ul tău** sau cu cheia ta API.
  - Are **SoulOS** (designul „Alive”, `os/DESIGN-ALIVE.md`) cu tastatură (scrii lui Claude, notițe, alarme).
  - Doarme în capsula **OU**.
- **SOUL M = prototipul de lucru** (≈ 90 × 101 × 31,5 mm, placa **Waveshare ESP32-S3-Touch-LCD-2.8C**, 2,8″ 480 × 480, firmware 1.9.0, `release/SOUL-2.8C-install.bin`): pentru teste și dovada TRL 3 a dosarului PoC.
- **Ce e gata:**
  - designul final S (randări **v10**, planșa `blueprints/final/soul_s_1_general_arrangement*`) + logo-ul „The Glass O” (`brand/logo/`); M în randările v9;
  - firmware-ul: compilează pentru **AMOLED-1.75** (`amoled175`, SOUL S) și pentru **2.8C** (`lcd28`, SOUL M);
  - serviciul AI, SoulOS pe web, pagina de lansare;
  - kitul S-P0 (`prototip/stl/s/`, `prototip/step/s/`), kitul P0-M, dosarul PR BI PoC 1.1.
- **Ce urmează:** flash pe placa 2.8C și filmare (= dovada TRL 3; testele continuă pe 2.8C), **cumperi o placă Waveshare ESP32-S3-Touch-AMOLED-1.75** (01-BOM P0-01, $29,99–39,99), printezi S-P0, CAD-ul de producție al lui S la 23 mm, apoi CNC.
- **Bani:** **PR BI 1.1 Proof of Concept** prin ARTEMIS DIGITAL (€191k, 24 luni) — [`investors/poc-1.1/`](../investors/poc-1.1/).

> Notă: 01-BOM, 02-MANUFACTURING și 04-COMPLIANCE sunt pe S din 22.10.2026: produsul S (23 mm, PCB propriu), pilotul S-P0 (placa AMOLED-1.75, 25,65 mm) și prototipul M (doar referință). Cost pe bucată S [estimare]: ≈ 144 € la 100, ≈ 74 € la 1.000 (M: 215 / 98 €). Modelul fabricii (`factory/SOUL-fabrica-model.xlsx`) e tot pe S.

---

## What SOUL is

SOUL is a personal AI object you keep on your desk and hold in your hand. The pitch: "The labs make the brain. We make the body and the soul."

**Final design: MĂRGĂRITAR, size S** (decision 20 Oct 2026; renders: `renders/v10/`, CGI)
- An **upright aluminium pebble, 63 × 70.8 × 23 mm** (62.96 × 70.8 incl. the 1.2 mm foot; 23.0 mm target depth), flat black glass **Ø52 mm**.
- **6061-T6**, fine bead-blasted, colour-anodised: Silver, Graphite, Midnight, Ember, Champagne.
- **1.75" round AMOLED (466 × 466)**, true black, behind black glass. **Nothing else on the face.**
- Flat foot, speaker in the side seam, two mic holes, charging from the bottom in **OU**, the egg capsule.
- Battery **750 mAh** (LiPo 603040), about **27 h** on the model day [E]. Numbers: `docs/size-s.json`; method: `docs/12-SIZE-S.md`.

**What it does**
- **Live eyes**, a round keyboard (S: 5.1 mm keys, alphabetical, `os/DESIGN-ALIVE.md`; M: ≈ 6.7 mm QWERTY), notes, alarms, timers, all **offline**.
- AI modes: **none / your Claude / your ChatGPT / your own API key**; approve Claude Code requests by holding the glass.

**Hardware:** the product dev board is the Waveshare **ESP32-S3-Touch-AMOLED-1.75** (CO5300 QSPI, CST9217 touch, QMI8658, PCF85063, AXP2101, 2 mics + ES7210/ES8311 + speaker); the product itself gets a custom round PCB [E]. The working prototype is the Waveshare **ESP32-S3-Touch-LCD-2.8C** (ST7701 RGB, GT911, IMU, RTC, buzzer; voice needs an INMP441 + MAX98357). See `firmware/README.md`.

**Sale:** pre-launch waitlist only, **from €249**, no Founders edition, nothing charged before CE (`site/README.md`). The Founders 00 plan in 05-LAUNCH-PLAN is history; 01-BOM keeps its costs as "a first S batch of 25".

### M → S: prototype vs product (refreshed 22 Oct 2026)
Values from [`size-s.json`](size-s.json) (decision 20 Oct 2026); costs from `01-BOM.md` (c). [E] = estimate.

| | M (prototype) | **S (product, now)** |
|---|---|---|
| Body | 90 × 101 × 31.5 mm (MĂRGĂRITAR v9) | **63 × 70.8 × 23.0 mm** (MĂRGĂRITAR at its design scale, back compressed s_back 0.807) |
| Glass | black Ø74.3 | **flat black Ø52**, 0.7 mm [E] |
| Screen | 2.8" IPS 480² (grey blacks) | **1.75" AMOLED 466²**, true black, CO5300 / QSPI |
| Board | ESP32-S3-Touch-LCD-2.8C + optional mic/amp | **ESP32-S3-Touch-AMOLED-1.75** (dev, $29.99–39.99, mics + codec + speaker on board); product: custom PCB [E] |
| Battery | 1500 mAh (803450), ≈ 32 h [E] | **750 mAh (603040), ≈ 27 h [E]** |
| DIY prototype body | P0-M kit 112.1 × 125.1 × 31.6 mm (stock 2.8C glass Ø95.86) | **S-P0 63 × 70.8 × 25.65 mm** (stock AMOLED-1.75 glass; 500 mAh 503035 planned, the exported CAD fits a 503030 ≈ 450 mAh [E]) |
| CNC shell | billet 1.0 kg, ~45 min/set [E] | **billet 0.4 kg, ~24 min/set** [E] |
| Firmware | `pio run -e lcd28`, SoulOS Alive 1.9.0, image `firmware/release/SOUL-2.8C-install.bin` | `pio run -e amoled175`: S density profile + every Alive screen on 466 px (`firmware/SOUL-S.md`; 237 native tests on both); ES8311/ES7210 audio and light sleep still to do |
| Weight [E] | – | ≈ 85 g (75–95) |
| Hardware per unit [E] | ≈ €215 @100 · ≈ €98 @1000 | **≈ €144 @100 · ≈ €74 @1000** (`01-BOM.md` (c), `12-SIZE-S.md` §3.1) |
| Role | tests + PoC TRL 3 proof (firmware 1.9.0) | the product, from €249 |
| Renders / drawings | `renders/v9/`, `blueprints/final/soul_m_*` | **`renders/v10/`, `blueprints/final/soul_s_*`**, `prototip/stl/s/`, `prototip/step/s/` |

## State of every part

| Part | State | Where | Next step |
|---|---|---|---|
| Industrial design (MĂRGĂRITAR, size S; M = prototype) | ✅ **done** (CGI renders, not photos) | `renders/v10/` (S), `renders/v9/` (M) (+ `renders/v6/README.md` for CMF/hex) | Validate with the S-P0 in hand |
| Logo „The Glass O” | ✅ done | `brand/logo/` | Trademark search |
| Size study (v7 S/M/L) | ✅ **decided: S is the product** (20 Oct; M on 25 Sep, now the prototype) | `renders/v7/`, `research/12`, `docs/12-SIZE-S.md` | – |
| Production CAD of S (Ø52 custom glass, 23.0 mm) | ❌ **to do** | `renders/v9/src/marg_geo.py` (MargaritarV9, s_back 0.807); S-P0 shells in `prototip/step/s/` | Needs the custom PCB (docs/12 §4) |
| S-P0, the DIY pilot of S (CAD, STL, STEP) | ✅ plastic variant exported + checked (60 pairs) + assembly note (RO); ❌ alu variant not exported | `prototip/cad/soul_p0_s.py`, `prototip/stl/s/`, `prototip/step/s/`, `blueprints/final/soul_s_2_p0_kit.*` | Buy the AMOLED-1.75 board, print, measure the UNVERIFIED items |
| M prototype kit P0-M (CAD, STL, STEP) | ✅ plastic + alu exported, `COMANDA.md` written | `prototip/cad/soul_p0.py`, `prototip/stl/{plastic,alu}/`, `prototip/step/{plastic,alu}/`, `prototip/COMANDA.md` | Print + flash 1.9.0 for TRL 3 |
| Technical drawings | ✅ S: GA + S-P0 kit (`blueprints/final/soul_s_*`); M: 4 sheets (`soul_m_*`) | older: `blueprints/` rev A + `v3` | S production drawing after the 23 mm CAD |
| Older parametric shells (coin/drop/gem/cloud) | ✅ done, legacy | `cad/` | Reference only |
| OU capsule | 🟡 designed (research/09 §4) + rendered; **no CAD** | `renders/v6/soul_v6_ou_night.png`, `renders/v5/` | CAD for the SLA pilot capsule |
| Firmware SoulOS Alive (1.9.0) | ✅ **compiles** (`lcd28` = M, `amoled175` = S, `sim`), **237/237 native tests**; S layout done (`firmware/SOUL-S.md`); ❌ not yet run on hardware | `firmware/` | First flash on the 2.8C (TRL 3), then on the AMOLED-1.75 |
| SoulOS (the full OS) | 🟡 ~10 % of 1.0; spec + architecture done | `os/SPEC.md`, `os/ARCHITECTURE.md` | Roadmap 0.1 → 1.0 |
| SoulOS web prototype | ✅ done | `os/index.html` (= `site/os.html`) | User tests of the keyboard |
| AI service (companion, 3 modes, BYO key, MCP) | ✅ **49/49 tests pass**; no production deploy, no OAuth | `ai/` | OAuth + EU hosting + voice |
| Phone app | ❌ to do | spec in `os/ARCHITECTURE.md` §5 | SoulOS 0.4 |
| Voice | ❌ to do | plan in `ai/README.md` | SoulOS 0.5 (xiaozhi-esp32) |
| Landing page | ✅ done (landing v3, size S, MĂRGĂRITAR renders, logo, English default + RO toggle, from €249); waitlist in demo mode | `site/` + https://claude.ai/artifact/WZtQ7JpCjpj6M3sfgJugHC | Set `WAITLIST_ENDPOINT`, legal footer |
| Media (simulator clips, keyboard/time-picker frames) | ✅ done | `media/` | Real-device clips after P0 |
| Research (market, hardware, compliance, AI, brand, design, aluminium, competitors, screen) | ✅ done (01–12 + design-max) | `research/` | – |
| Investor pack, funding | ✅ done | `investors/` (DECK, INVESTORS, FINANTARE-ROMANIA, **poc-1.1/** official PR BI PoC 1.1 annexes) | PoC application, Nov 2026 |
| BOM, manufacturing, compliance, launch plan | ✅ this package | `docs/` | Replace [E] prices with real quotes |
| CE / RED / EN 18031 | ❌ to do | [04-COMPLIANCE](04-COMPLIANCE.md) | Lab quotes, week 1 |
| Trademark "SOUL" | ❌ to do (**high conflict risk**) | [04-COMPLIANCE](04-COMPLIANCE.md) | TMview search this week |

## The documents in this package

| # | Document | Read it for |
|---|---|---|
| 01 | [01-BOM.md](01-BOM.md) + [BOM.csv](BOM.csv) | SOUL S per unit at 100 / 1,000 (≈ €144 / €74 [E]); S-P0 parts at qty 1/10/25 (≈ €211 plastic / €363 alu); a first S batch of 25 (≈ €190 per unit + ≈ €15k one-off); the M prototype parts (reference) |
| 02 | [02-MANUFACTURING.md](02-MANUFACTURING.md) | Which file goes to which supplier, CNC/print settings, colours + hex, tolerances, assembly, QC, packaging, OU, base marking, 1k/10k |
| 03 | [03-SOFTWARE.md](03-SOFTWARE.md) | How to build, flash, test and run the firmware, AI service, MCP connector, SoulOS prototype and site (verified today) |
| 04 | [04-COMPLIANCE.md](04-COMPLIANCE.md) | CE/RED, EN 18031, battery, WEEE/ANMAP, GPSR, AI Act, AI policies, trademark, GDPR, with owners, costs and order |
| 05 | [05-LAUNCH-PLAN.md](05-LAUNCH-PLAN.md) | Week-by-week launch plan, costs, funding in 5 lines, one checklist (written for Founders 00, now history: the site is a waitlist) |
| 06 | [06-SUPPLIERS.md](06-SUPPLIERS.md) | Every supplier and contact link in one table |
| 07 | [07-CONNECT-AI.md](07-CONNECT-AI.md) | How SOUL gets Claude/ChatGPT (SOUL Cloud, your API key, the SOUL connector for your own Claude/ChatGPT app, Hardware Buddy, offline), what is not possible, the device↔cloud protocol and the firmware contract |
| 12 | [12-SIZE-S.md](12-SIZE-S.md) + [size-s.json](size-s.json) | **The S spec (single source of truth):** board and panel checks, internal stack-up, the 750 mAh battery, battery life, cost and CNC delta vs M |
| – | [factory/](factory/) | Small factory vs production chain on S: `SOUL-fabrica-model.xlsx` (scenarios A–D at 100 / 1k / 5k / 20k), `SOUL-fabrica.pdf` |

## Map of every file (vault folder `micul-smecher/`)

| Folder | Contents |
|---|---|
| `docs/` | This package. `_tools/bom.py` regenerates `BOM.csv` and the BOM tables' numbers. |
| `renders/v10/` | **Final design, MĂRGĂRITAR size S** (20 Oct 2026): hero, family, side, hand, desk, README, `src/` |
| `renders/v9/` | MĂRGĂRITAR **size M, the prototype**: hero, family, side, hand, desk, typing, OU at night, alive gif/mp4 |
| `renders/v8/` | HOPA size M (replaced by v9) |
| `brand/logo/` | Logo kit „The Glass O”: SVG/PNG, favicon, app icons, mockups |
| `renders/v6/` | Same look at size S: hero, family (5 colours), side, back, bottom, hand, macro, OU at night, `alive.mp4/.gif`; `README.md` (CMF, hex, geometry); `src/` (Blender) |
| `renders/v7/` | Size study S/M/L: `soul_v7_hands.png`, `soul_v7_lineup.png`, `soul_v7_typing.png`, README |
| `renders/v4`, `v5`, root `*.png` | Earlier concepts (shape family, HOPA rocker, glass/pearl), for history |
| `prototip/` | **S-P0** (S pilot): `cad/soul_p0_s.py`, `cad/blueprints_s.py`, `cad/report_s_plastic.json`, `stl/s/` (+ `assembly/`, README RO), `step/s/*.step.gz`; **P0-M** (M prototype kit): `cad/soul_p0.py`, `stl/plastic/`, `stl/alu/`, `step/plastic/`, `step/alu/`, `COMANDA.md`, `README.md`; `SOUL-marimi-scara-reala.pdf` (true-scale sheet); `legacy-S/` (old HOPA S) |
| `cad/` | Older OpenSCAD shells (4 shapes × 2 boards, 33 checked STLs, renders) |
| `blueprints/` | A3 sheets rev A (GA, section, exploded + BOM, 1.75 prototype) + `v3/`; generators in `src/` |
| `firmware/` | PlatformIO project: `src/` (board), `lib/Suflet/src/` (engine + SoulOS modules), `sim/`, `test/`, `tools/` (fonts, word lists, media export) |
| `ai/` | Python `suflet_ai`: companion, actions, providers (rules / Claude / ChatGPT), keystore, MCP server, FastAPI server, tests |
| `os/` | `index.html` (SoulOS prototype), `SPEC.md`, `ARCHITECTURE.md`, `research/01–04`, `lang-mockups/`, `screenshots/` |
| `site/` | `index.html` (landing v3), `legal.html`, `os.html`, `media/`, `README.md` (config, waitlist, deploy, launch checklist) |
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

## Known gaps (updated 22 Oct 2026)

1. **Nothing has run on real hardware yet.** First job: flash the 2.8C board, film it (TRL 3 evidence for the grant).
2. **No production CAD for the final S body** (23.0 mm, custom glass Ø52, custom PCB). S-P0 (25.65 mm) and P0-M are the buildable pilots around the stock boards.
3. **No OU capsule CAD** (renders only).
4. Every price is [E] until real quotes arrive; the S cost delta vs M is in `12-SIZE-S.md` §3.
5. Trademark "SOUL" is unchecked (**high conflict risk**).
6. PoC 1.1: expert for the scientific report, technical coordinator, 2 letters of intent, ARTEMIS eligibility checks (see `investors/poc-1.1/REVIEW.md`).
