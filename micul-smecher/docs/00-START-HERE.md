# SOUL: start here

*The complete SOUL package · 25 Sep 2026 · ARTEMIS DIGITAL S.R.L., Bucharest · assembled from the vault `micul-smecher/` + the notes in `01 Afaceri/Micul Șmecher/`.*

## Pe scurt (RO, pentru Andu)
- **SOUL** e o pietricică din aluminiu, în picioare, de **≈ 63 × 72 × 27 mm**, cu ecran AMOLED rotund de **1,75″** și doi ochi vii.
  - Funcționează **fără AI**, cu **Claude-ul tău** sau cu **ChatGPT-ul tău**.
  - Se leagă de Claude Desktop ca să aprobi cererile lui Claude Code.
  - Doarme în capsula **OU**.
- **Ce e gata:**
  - designul final (randări v6);
  - firmware-ul: 55/55 de teste trec și compilează pentru placa 1.75;
  - serviciul AI: 49/49 de teste, cu conector MCP pentru Claude și ChatGPT și cheie proprie criptată;
  - prototipul SoulOS pe web, pagina de lansare, cercetarea, costurile și planul de finanțare.
- **Ce e în lucru:** kitul DIY **P0**. CAD-ul și fișierele pentru print sunt aproape gata. Carcasa din aluminiu are deocamdată doar partea din față.
- **Ce urmează:**
  - comanzi piesele (vezi [01-BOM](01-BOM.md), ≈ €211 pentru un prototip din plastic);
  - printezi, flash-uiești și filmezi;
  - trimiți STEP-ul la 5–7 ateliere CNC;
  - testele CE (€5–12k);
  - Founders 00: 25 de bucăți la €349, în primăvara 2027 ([05-LAUNCH-PLAN](05-LAUNCH-PLAN.md)).
- **Decizie deschisă:** ecran mai mare? Vezi [`research/12`](../research/12-ecran-mai-mare.md) și `renders/v7/`. Recomandarea e să rămână 1,75″ ca produs principal, iar varianta de 2,8″ să fie un prototip paralel.
- **Bani:** apelul **PR BI 1.1 Proof of Concept** (€50–200k, nov. 2026). Anexele oficiale sunt în [`investors/poc-1.1/`](../investors/poc-1.1/).

---

## What SOUL is

SOUL is a small AI companion object. The pitch: "The labs make the brain. We make the body and the soul."

**Final design: v6 (design code HOPA)**
- An **upright aluminium pebble, ≈ 63 × 72.2 × 27 mm**.
- **6061-T6**, fine bead-blasted, colour-anodised in five colours: Natural silver, Graphite, Night blue, Ember and Champagne.
- **1.75" round AMOLED (466 × 466)** behind black glass. **Nothing else on the face.**
- A flat oval foot (no rocker).
- A polymer base plate that doubles as the antenna window, with 5 gold charging contacts.
- The speaker slot sits in the side seam.

It sleeps and charges in **OU**, an egg-shaped capsule (77 × 88 × 42 mm).

**What it does**
- **Live eyes** with 24 reactions and a unique personality born from the chip.
- A round keyboard, notes, reminders, alarms and timers, all **offline**.
- **Works with Claude:** approve Claude Code / Cowork requests by holding the glass.
- AI modes: **none / Claude / ChatGPT**. These run through the user's own API key or through the SOUL connector/app inside their Claude or ChatGPT.

**Hardware today:** the Waveshare **ESP32-S3-Touch-AMOLED-1.75** board, which has 2 mics, a speaker, an IMU, an RTC and a PMU.

**First sale: Founders 00**
- 25 numbered units at **€349**.
- Only after CE radio tests; spring 2027.

**Pending decision: a bigger screen**
- The founder said: "too small, how do you type on it?"
- [`research/12-ecran-mai-mare.md`](../research/12-ecran-mai-mare.md) finds **no round AMOLED larger than 1.75" at small quantities**. Bigger means IPS, which has grey blacks.
- Options:
  - **S** 1.75": 63 × 72 × 27 mm (today);
  - **M** 2.8" IPS: ≈ 93 × 106 × 31 mm, 6.7 mm keys;
  - **L** 3.4" IPS on an ESP32-P4: ≈ 113 × 129 × 34 mm.
- Recommendation: **keep S as the hero** (type on the phone, by voice or with a BT keyboard), and **prototype M in parallel**. Renders are in `renders/v7/`.
- This package assumes S.

## State of every part

| Part | State | Where | Next step |
|---|---|---|---|
| Industrial design (v6 aluminium) | ✅ **done** (CGI renders, not photos) | `renders/v6/` (+ README with CMF and hex colours) | Validate with the P0 in hand |
| Size study (v7 S/M/L) | ✅ renders + research done; **decision open** | `renders/v7/`, `research/12` | Founder decides S vs M |
| Production CAD of v6 (Ø52 custom glass, 27 mm) | ❌ **to do** | only the Blender mesh `renders/v6/src/` | After P0 rev C; needs the custom PCB |
| DIY prototype P0 (CAD, STL, STEP) | 🟡 **prototype, in progress** (another agent is finishing it) | `prototip/cad/soul_p0.py`, `prototip/stl/`, `prototip/step/` | Plastic variant exported; alu has only the front shell; README/COMANDA not written yet (see gaps) |
| Technical drawings of the final design | ❌ to do (`blueprints/final/` missing; `prototip/cad/blueprints_p0.py` in progress) | `blueprints/` rev A + `v3` = older concepts | Generate the P0/v6 sheets |
| Older parametric shells (coin/drop/gem/cloud) | ✅ done, legacy | `cad/` | Reference only |
| OU capsule | 🟡 designed (research/09 §4) + rendered; **no CAD** | `renders/v6/soul_v6_ou_night.png`, `renders/v5/` | CAD for the SLA pilot capsule |
| Firmware "Suflet" + SoulOS v1 modules | ✅ **compiles** (amoled143/175/sim), **55/55 tests pass**; ❌ not yet run on hardware | `firmware/` | First flash + calibration |
| SoulOS (the full OS) | 🟡 ~10 % of 1.0; spec + architecture done | `os/SPEC.md`, `os/ARCHITECTURE.md` | Roadmap 0.1 → 1.0 |
| SoulOS web prototype | ✅ done | `os/index.html` (= `site/os.html`) | User tests of the keyboard |
| AI service (companion, 3 modes, BYO key, MCP) | ✅ **49/49 tests pass**; no production deploy, no OAuth | `ai/` | OAuth + EU hosting + voice |
| Phone app | ❌ to do | spec in `os/ARCHITECTURE.md` §5 | SoulOS 0.4 |
| Voice | ❌ to do | plan in `ai/README.md` | SoulOS 0.5 (xiaozhi-esp32) |
| Landing page | ✅ done (v6 renders, €349, EN/RO); waitlist in demo mode | `site/` + https://claude.ai/artifact/BUAPPdP1W5xnCvSVcsQXoX | Set `WAITLIST_ENDPOINT`, legal footer |
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
| `renders/v6/` | **Final design** CGI: hero, family (5 colours), side, back, bottom, hand, macro, OU at night, `alive.mp4/.gif`; `README.md` (CMF, hex, geometry); `src/` (Blender) |
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
| `dist/SOUL-package.zip` | This package zipped (see its `README.md` and `SKIPPED.txt`) |

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

1. **P0 kit not finished** (another agent is working on it). Missing today:
   - `prototip/README.md` (assembly guide) and `prototip/COMANDA.md` (order list);
   - the alu **back shell** and all of the `alu_band` files;
   - `prototip/CHECKS.txt` and the check images;
   - the P0 drawings.
   - Use [01-BOM](01-BOM.md) and [02-MANUFACTURING](02-MANUFACTURING.md) §6 until they exist.
2. **No production CAD for v6** (27 mm deep, Ø52 glass). It needs the custom PCB.
3. **No OU capsule CAD.**
4. **No `blueprints/final/`.**
5. **Nothing has run on real hardware yet.** Every price is [E] until real quotes arrive.
6. `site/README.md` still describes older renders and €119 (the page itself is correct). The vault note „Micul Șmecher" still describes the glass amulet. Its state table predates v6.
7. Trademark "SOUL" is unchecked.
