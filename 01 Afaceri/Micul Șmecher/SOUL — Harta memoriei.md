---
tip: hub
afacere: Micul Șmecher
actualizat: 2026-10-22
---

# SOUL — Harta memoriei

> Tot ce există despre SOUL, legat într-un singur loc: note, cercetare, cod, planuri, randări, brand, film, finanțare. **Pornește de aici.** Hub-ul afacerii: [[Micul Șmecher]] · decizii: [[Jurnal decizii]] · ce urmează: **[[De continuat — SOUL]]** · finanțare: [[Finanțare — PR BI PoC 1.1 pentru SOUL]] · cereri Anthropic/OpenAI: [[SOUL — Cereri parteneriat Anthropic și OpenAI]] · acasă: [[Acasă]].
> Fișierele proiectului sunt în `micul-smecher/` (căile de mai jos sunt relative la acest folder). Tot ce e marcat **[neverificat]** nu a fost confirmat în repo sau pe hardware.

## Starea pe scurt (2026-10-03; mărimea actualizată 2026-10-22)

> **Decizia din 2026-10-20** ([[Jurnal decizii]]): **produsul final e mărimea S** — MĂRGĂRITAR la scara lui de design, **63 × 70,8 × 23 mm**, sticlă neagră plată **Ø52**, ecran rotund **AMOLED 1,75″ 466×466** (negru adevărat), placa de dezvoltare Waveshare ESP32-S3-Touch-AMOLED-1.75, LiPo 750 mAh, randări `renders/v10/` (CGI). **Mărimea M** (≈ 90 × 101 × 31,5 mm, placa 2.8C, ecran 2,8″, SoulOS 1.9.1) rămâne **prototipul** pentru teste și dovada TRL 3. Cifrele: `micul-smecher/docs/size-s.json`, `docs/12-SIZE-S.md`.

| Parte | Stare | Unde |
|---|---|---|
| **Designul final** | **MĂRGĂRITAR, mărimea S** (decizia din 2026-10-20) ≈ 63 × 70,8 × 23 mm, aluminiu 6061 sablat + anodizat, 5 culori (Argint, Grafit, Albastru noapte / Midnight, Jar / Ember, Șampanie); sticlă neagră plată Ø52, ecran AMOLED 1,75″ 466×466, nimic altceva pe față. **Mărimea M** (≈ 90 × 101 × 31,5 mm, sticlă Ø74,3, ecran 2,8″) = prototipul | randări `renders/v10/` (S) și `renders/v9/` (M), CGI, nu poze; `docs/size-s.json`, `docs/12-SIZE-S.md`, planșe `blueprints/final/soul_s_*` |
| **S-P0** (pilotul S, de făcut acasă) | MĂRGĂRITAR S în jurul plăcii Waveshare ESP32-S3-Touch-AMOLED-1.75, **63 × 70,8 × 25,65 mm**, varianta plastic exportată și verificată; baterie LiPo 503030, ~450 mAh [estimare] | `prototip/stl/s/` (+ README RO), `prototip/step/s/`, planșa `blueprints/final/soul_s_2_p0_kit.png` |
| **Prototipul M** (P0-M, teste + TRL 3) | corp printat ≈ 112 × 125 × 31,6 mm (placa 2.8C are sticla Ø95,9 lipită) — **de măsurat pe print** | `prototip/stl/plastic/`, `prototip/COMANDA.md`, planșe `blueprints/final/soul_m_*` |
| **Electronica** | M: Waveshare ESP32-S3-Touch-LCD-2.8C (~140 lei pe Alibaba **[neverificat]**; ~190 lei Waveshare/AliExpress) + LiPo 803450 1500 mAh. S: **o placă** Waveshare ESP32-S3-Touch-AMOLED-1.75 ($29,99–39,99) — de cumpărat | `prototip/COMANDA.md`, `docs/01-BOM.md` |
| **Firmware** | **SoulOS Alive 1.9.1**: M = `lcd28` (imaginea `release/SOUL-2.8C-install.bin`, sha256 `62c2838c…`), S = `amoled175` (profilul de densitate + toate ecranele pe 466 px + difuzorul ES8311; imaginea `release/SOUL-1.75-install.bin`, sha256 `b208fbbb…`); **245 de teste** pe PC; **încă neîncărcat pe o placă** | `firmware/`, `firmware/SOUL-S.md`, `firmware/BRINGUP.md` |
| **Cost și fabrică (S)** | ≈ 144 €/buc. la 100, ≈ 74 € la 1.000 [estimare]; CNC 0,4 kg și ~24 min/set; scenariile A–D | `docs/01-BOM.md`, `docs/12-SIZE-S.md` §3, `docs/factory/SOUL-fabrica-model.xlsx`, [[SOUL — Fabrică și lanț de producție]] |
| **Conectarea AI** | SOUL Cloud (pairing, gateway, conector MCP cu OAuth, `/pair`, `/me`) construit și testat cu falsuri; AI inclus plătit de noi **oprit** (decizia 2026-10-03). SOUL Bridge (Pro/Max prin Claude Code oficial) = prototip, zonă gri | `ai/`, `bridge/`, `docs/07-CONNECT-AI.md`, `docs/08-OWN-CLAUDE.md` |
| **Ochii SOUL v2** | perechea-semnătură aprobată + colecție de **120 de designuri**, **31 de expresii**, comportamente cu giroscopul | `eyes/` · galerie https://claude.ai/artifact/M8CVFPvTN3FCj6fC9UbA3D · semnătura https://claude.ai/artifact/36i5S4iZkq3t48ZqJZwFt5 |
| **SoulOS v4** (prototip web) | ochii ca interfață, Claude real (cu cheie), primul pornit, My SOUL, UX review | `os/index.html` (+ `site/os.html`) · https://claude.ai/artifact/BFboeyYNYTUBrzsiB9uEfA |
| **Pagina de lansare v2** | dispozitivul ca „O” în hero, ochi v2 vii pe fiecare randare, roata celor 120 de ochi, carusel de culori; listă de așteptare în mod demo | `site/` · https://claude.ai/artifact/WZtQ7JpCjpj6M3sfgJugHC (linkul vechi BUAPPdP1W5xnCvSVcsQXoX e versiunea 1) |
| **Brand** | logo „The Glass O”, pachet complet + brand book de 19 pagini | `brand/SOUL-Brand-Package/` + `brand/SOUL-Brand-Package.zip` |
| **Trailer** | **v3**: 47,3 s, 1920×1080 + vertical 1080×1920, muzică de la cadrul 0, tăieturi pe beat, voce neurală Ava; **v4 oprit** de fondator (WIP salvat) | `trailer/soul_trailer.mp4`, `trailer/soul_trailer_vertical.mp4` |
| **Pachetul complet (zip)** | `dist/SOUL-package.zip`, refăcut 2026-10-03 (~90 MB, sub limita de 95 MB) cu `docs/_tools/build_zip.py`: acum include renders v9, eyes, bridge, Brand Package, docs 07/08 | `dist/` |

## Start și pachetul complet
- [[micul-smecher/docs/00-START-HERE|SOUL: start here]] — `docs/00-START-HERE.md`
- [[micul-smecher/docs/01-BOM|01 · Bill of materials: SOUL S, S-P0, M]] — `docs/01-BOM.md` + `BOM.csv` (S la 100 / 1.000, pilotul S-P0, un prim lot S de 25 = fostul Founders 00, piesele prototipului M)
- [[micul-smecher/docs/02-MANUFACTURING|02 · Manufacturing dossier]] — `docs/02-MANUFACTURING.md`
- [[micul-smecher/docs/03-SOFTWARE|03 · Software]] — `docs/03-SOFTWARE.md`
- [[micul-smecher/docs/04-COMPLIANCE|04 · Compliance (EU / Romania)]] — `docs/04-COMPLIANCE.md`
- [[micul-smecher/docs/05-LAUNCH-PLAN|05 · Launch plan]] — `docs/05-LAUNCH-PLAN.md`
- [[micul-smecher/docs/06-SUPPLIERS|06 · Suppliers and contacts (one table)]] — `docs/06-SUPPLIERS.md`
- [[micul-smecher/docs/07-CONNECT-AI|07 · Connect AI: SOUL Cloud, pairing, conectorul Claude/ChatGPT]] — `docs/07-CONNECT-AI.md`
- [[micul-smecher/docs/08-OWN-CLAUDE|08 · Claude-ul tău pe SOUL (Pro/Max prin SOUL Bridge)]] — `docs/08-OWN-CLAUDE.md`
- [[micul-smecher/docs/12-SIZE-S|12 · SOUL S: specificația hardware]] — `docs/12-SIZE-S.md` + `docs/size-s.json` (**sursa unică pentru mărimea S**: placa, stiva internă, bateria de 750 mAh, autonomia, costul și CNC față de M)
- Arhiva: `dist/SOUL-package.zip` (generată de `docs/_tools/build_zip.py`; fișierele prea mari sunt listate în `SKIPPED.txt` din zip)

## Notele proiectului (vault)
- [[Micul Șmecher]] — hub-ul afacerii, starea
- [[De continuat — SOUL]] — **lista de pași următori** (fondator + Claude)
- [[Design produs v3 — SOUL amuleta]] — istoria designului până la forma finală MĂRGĂRITAR
- [[Design produs v2 — SUFLET Pebble]] — (abandonat) piatra de buzunar
- [[Viziunea — momentul iPhone]] — gestul-semnătură, „one more thing”, filmul de lansare
- [[SOUL — Cereri parteneriat Anthropic și OpenAI]] — emailurile către Anthropic și OpenAI (Sign in with ChatGPT)
- [[Finanțare — PR BI PoC 1.1 pentru SOUL]] — grantul PoC 1.1
- [[SOUL — Fabrică și lanț de producție]] — **fabrică mică vs lanț de producție: variantele A–D, costuri, parteneri RO, autorizații, bani, plan 2026–2028** (2026-10-15); model `docs/factory/SOUL-fabrica-model.xlsx`
- [[Planul de bani Micul Șmecher]] · [[Produs și dezvoltare Micul Șmecher]] · [[Brand și lansare Micul Șmecher]] · [[Conformitate și riscuri Micul Șmecher]] · [[Piață și concurență Micul Șmecher]]
- [[Jurnal decizii]] — toate deciziile SOUL, datate

## Planul de construcție (S-P0 și prototipul M)
- [[micul-smecher/prototip/stl/s/README|SOUL S-P0: kitul de printat pentru mărimea S (placa AMOLED-1.75)]] — `prototip/stl/s/README.md` · STEP `prototip/step/s/` · CAD `prototip/cad/soul_p0_s.py` · verificări `prototip/cad/report_s_plastic.json`
- [[micul-smecher/prototip/COMANDA|Ce comanzi azi: SOUL-P0 mărimea M]] — `prototip/COMANDA.md` (prototipul de teste / TRL 3)
- [[micul-smecher/prototip/README|SOUL-P0 mărimea M: kitul de prototip făcut acasă]] — `prototip/README.md` · print `prototip/stl/plastic/`, `prototip/stl/alu/` · STEP `prototip/step/{plastic,alu}/`
- Foaia la scară reală S / S+ / M: `prototip/SOUL-marimi-scara-reala.pdf`
- [[micul-smecher/prototip/legacy-S/README|SOUL-P0 S vechi (HOPA, 1,75″), înlocuit de S-P0]] — `prototip/legacy-S/README.md`

## Planuri tehnice (blueprint)
- [[micul-smecher/blueprints/README|SOUL · planșe tehnice (blueprint), rev A]] — `blueprints/README.md` (planșele vechi)
- **Planșele SOUL S**: `blueprints/final/soul_s_1_general_arrangement.png` (produsul, 63 × 70,8 × 23, sticlă Ø52; + SVG, + varianta albă) și `soul_s_2_p0_kit.png` (kitul S-P0 cotat)
- **Planșele SOUL-P0 M în forma MĂRGĂRITAR** (prototipul; 4 foi: GA, secțiunea A-A, explodat + BOM, variante): `blueprints/final/soul_m_1_general_arrangement.png` … `soul_m_4_variants.png` (+ SVG, + varianta albă de printat)

## CAD
- [[micul-smecher/cad/README|Carcasa SUFLET / Micul Șmecher: CAD parametric (OpenSCAD)]] — `cad/README.md` (istoric)

## Randări (istoric design → final)
- [[micul-smecher/renders/v10/README|SOUL v10: MĂRGĂRITAR, mărimea S — PRODUSUL FINAL (2026-10-20)]] — `renders/v10/README.md` (hero, family, side, hand, desk)
- [[micul-smecher/renders/v9/README|SOUL v9: MĂRGĂRITAR, mărimea M — prototipul (a fost designul final până la 2026-10-20)]] — `renders/v9/README.md` (hero, family, side, hand, desk, typing, ou_night, vs v8, alive gif/mp4)
- [[micul-smecher/renders/v8/README|SOUL v8: HOPA mărimea M (înlocuit de v9)]] — `renders/v8/README.md`
- [[micul-smecher/renders/README|Randări produs — SUFLET („Micul Șmecher”)]] — `renders/README.md`
- [[micul-smecher/renders/v2/README|v2 („piatra de buzunar”)]] · [[micul-smecher/renders/v3/README|v3]] · [[micul-smecher/renders/v4/README|v4 familia]] · [[micul-smecher/renders/v5/README|v5 HOPA + ALT A/B (MĂRGĂRITAR vine de aici)]] · [[micul-smecher/renders/v6/README|v6 aluminiu + culori]] · [[micul-smecher/renders/v7/README|v7 studiu de mărime]]

## Brand și logo
- [[micul-smecher/brand/SOUL-Brand-Package/README|SOUL Brand Package v1.0 (The Glass O)]] — `brand/SOUL-Brand-Package/README.md`; brand book: `brand/SOUL-Brand-Package/Brand-Book/SOUL-Brand-Book.pdf` (19 pagini); arhiva: `brand/SOUL-Brand-Package.zip`
- [[micul-smecher/brand/SOUL-Brand-Package/Fonts/README|Fonturile brandului (Bricolage Grotesque, Martian Mono)]] — `brand/SOUL-Brand-Package/Fonts/README.md`
- [[micul-smecher/brand/logo/README|SOUL: logo and mini brand kit (v1.0, sursele)]] — `brand/logo/README.md`

## Trailer și film
- Trailer **v3** (47,3 s): `trailer/soul_trailer.mp4` (16:9) + `trailer/soul_trailer_vertical.mp4` (9:16), sursa `trailer/soul_trailer.html`, randare `trailer/render.py`
- [[micul-smecher/trailer/voiceover_script|Scenariul vocii (cronometrat pe beat)]] — `trailer/voiceover_script.md` (titlul spune v4; timeline-ul e cel din MP4)
- [[micul-smecher/trailer/MUSIC-LICENSE|Licența muzicii]] — `trailer/MUSIC-LICENSE.md`
- Trailer v4: oprit de fondator (commit `cfe5104`, WIP salvat). Filmul CGI de lansare v9: vezi `renders/v9/README.md`

## Ochii SOUL (eyes v2)
- [[micul-smecher/eyes/README|SOUL eyes: motorul, API-ul, colecția]] — `eyes/README.md`
- `eyes/eyes.js` (motorul, `SoulEyes.createEyes`), `eyes/designs.json` (cele 120 de designuri), `eyes/one.html` (perechea-semnătură, 31 de expresii, Motion), `eyes/index.html` (galeria + „Birth a SOUL”), clipuri `eyes/soul_eye_v2.mp4`, `soul_eyes_collection.mp4`, `soul_eye_motion.mp4`
- Online: galeria https://claude.ai/artifact/M8CVFPvTN3FCj6fC9UbA3D · semnătura https://claude.ai/artifact/36i5S4iZkq3t48ZqJZwFt5
- Comportamente cu giroscopul (și pe dispozitiv): ochii rămân la nivel, pupile ca bile, rotire → amețit → „ufff”, orientare (pe spate / cu fața în jos / invers / calm în mână), dublu-tap pe carcasă, da/nu din cap

## SoulOS — sistemul de operare
- Prototipul web **v4**: `os/index.html` (copie în `site/os.html`), teste `os/tests/soulos.test.mjs` · online https://claude.ai/artifact/BFboeyYNYTUBrzsiB9uEfA
- [[micul-smecher/os/UX-REVIEW|SoulOS UX review (v3 → v4)]] — `os/UX-REVIEW.md`
- [[micul-smecher/os/ARCHITECTURE|SoulOS: arhitectura sistemului de operare]] — `os/ARCHITECTURE.md` (tabelul de moduri AI e înlocuit de docs/07 unde diferă)
- [[micul-smecher/os/SPEC|SoulOS — specificație v0.1]] — `os/SPEC.md`
- [[micul-smecher/os/research/01-text-input|SoulOS: text input (01)]] · [[micul-smecher/os/research/02-os-architecture|OS architecture research (02)]] · [[micul-smecher/os/research/03-code-map|code map (03)]] · [[micul-smecher/os/research/04-keyboard-design-familiar|Round QWERTY + Rim-Dial (04)]]

## Firmware (programul plăcii)
- [[micul-smecher/firmware/README|Firmware: SoulOS pe ESP32-S3 (SOUL M = mediul lcd28)]] — `firmware/README.md`
- [[micul-smecher/firmware/BRINGUP|BRINGUP: primele 15 minute pe o placă 2.8C reală]] — `firmware/BRINGUP.md`
- [[micul-smecher/firmware/SOUL-S|SoulOS Alive pe S (AMOLED 1,75″, 466 px)]] — `firmware/SOUL-S.md` (`pio run -e amoled175`)
- [[micul-smecher/firmware/release/README|Imaginile de instalare 1.9.1 pentru M și S (flash la 0x0 din browser)]] — `firmware/release/README.md` → `firmware/release/SOUL-2.8C-install.bin` (M) și `firmware/release/SOUL-1.75-install.bin` (S); pașii: `1-INSTALEAZA-RO.md` (M), `1-INSTALEAZA-S-RO.md` (S)
- [[micul-smecher/firmware/LICENSE-THIRD-PARTY|Third-party code]] · [[micul-smecher/firmware/tools/words/README|Keyboard word lists (EN + RO)]]

## Conectarea AI (SOUL Cloud, conector, Bridge)
- [[micul-smecher/docs/07-CONNECT-AI|07 · Connect AI]] — modurile (B cheia ta, C conectorul, D Hardware Buddy, E offline; A = AI inclus, oprit), protocolul device ↔ cloud, statusul real, acțiunile fondatorului
- [[micul-smecher/docs/08-OWN-CLAUDE|08 · Claude-ul tău (Pro/Max)]] — SOUL Bridge ca *channel* al Claude Code oficial, pe calculatorul omului; **zonă gri** până la acordul scris al Anthropic
- [[micul-smecher/ai/README|SOUL AI / SOUL Cloud (serverul)]] — `ai/README.md` (gateway, pairing, OAuth + MCP, `/pair`, `/me`, deploy `ai/fly.toml`)
- SOUL Bridge (Node): `bridge/` (`bridge/bin/soul-bridge.js`, `bridge/src/channel.js`, teste în `bridge/test/`)
- Fapte cheie: abonamentul **Claude Pro/Max nu poate fi folosit de dispozitive terțe** (regula Anthropic, verificată în docs/08 §1); „**Sign in with ChatGPT**” lansat de OpenAI pe 2026-09-29, pentru aplicații plătite/găzduite e listă de așteptare: https://openai.com/form/sign-in-with-chatgpt-interest/

## Pagina de lansare
- [[micul-smecher/site/README|Pagina de lansare SOUL]] — `site/README.md` · v2 online: https://claude.ai/artifact/WZtQ7JpCjpj6M3sfgJugHC

## Unelte și repo separat
- `tools/sync-soul-repo.sh` — oglindește `micul-smecher/` + notele SOUL din vault (și doar deciziile SOUL din jurnal) în repo-ul separat `krea123/soul`; rulează după ce fondatorul creează repo-ul pe GitHub
- `docs/_tools/build_zip.py` (pachetul zip) · `docs/_tools/bom.py` (BOM)

## Cercetare
- [[micul-smecher/research/01-market-2026-09-24|Market research — "living companion" charm gadget (raw report, 2026-09-24)]] — `research/01-market-2026-09-24.md`
- [[micul-smecher/research/02-hardware-2026-09-24|Hardware research — Waveshare ESP32-S3-Touch-AMOLED-1.43 and alternatives (raw, 2026-09-24]] — `research/02-hardware-2026-09-24.md`
- [[micul-smecher/research/03-compliance-2026-09-24|EU / Romania compliance brief (raw, 2026-09-24) — not legal advice]] — `research/03-compliance-2026-09-24.md`
- [[micul-smecher/research/04-ai-companions-2026-09-24|AI companion gadgets — market, tech, cost, regulation (raw, 2026-09-24)]] — `research/04-ai-companions-2026-09-24.md`
- [[micul-smecher/research/05-brand-productdev-funding-2026-09-24|Brand, product development, funding, Claude policy (raw, 2026-09-24)]] — `research/05-brand-productdev-funding-2026-09-24.md`
- [[micul-smecher/research/06-product-design-v2-2026-09-24|Product design v2 — "SUFLET Pebble" (raw, 2026-09-24)]] — `research/06-product-design-v2-2026-09-24.md`
- [[micul-smecher/research/07-amulet-design-language-2026-09-24|SOUL v3 — "the amulet": design language (raw, 2026-09-24)]] — `research/07-amulet-design-language-2026-09-24.md`
- [[micul-smecher/research/08-wow-design-cmf-2026-09-24|SOUL — "wow" design, CMF and the three render concepts (raw, 2026-09-24)]] — `research/08-wow-design-cmf-2026-09-24.md`
- [[micul-smecher/research/09-product-design-max-2026-09-24|SOUL: final design (design-max synthesis, 2026-09-24)]] — `research/09-product-design-max-2026-09-24.md`
- [[micul-smecher/research/10-carcasa-aluminiu|SOUL: carcasa din aluminiu (HOPA), de la primele 10–25 de bucăți la 10k (2026-09-25)]] — `research/10-carcasa-aluminiu.md`
- [[micul-smecher/research/11-competitori|11 · Competitori SOUL: analiză aprofundată (2026-09-25)]] — `research/11-competitori.md`
- [[micul-smecher/research/12-ecran-mai-mare|12 · Ecran mai mare pentru SOUL: ce panouri există, ce tastatură iese, ce corp rezultă (20]] — `research/12-ecran-mai-mare.md`
- [[micul-smecher/research/design-max/r-cmf|Cheap-but-premium CMF & manufacturing for SOUL (2026-09-24)]] — `research/design-max/r-cmf.md`
- [[micul-smecher/research/design-max/r-creatures|Creature form language: alive, not a toy → 10 form rules for SOUL (2026-09-24)]] — `research/design-max/r-creatures.md`
- [[micul-smecher/research/design-max/r-dock|SOUL: the dock and the charging capsule as design objects and rituals (2026-09-24)]] — `research/design-max/r-dock.md`
- [[micul-smecher/research/design-max/r-icons|Icons & desire drivers → 12 laws of "want it on sight" for SOUL (2026-09-24)]] — `research/design-max/r-icons.md`
- [[micul-smecher/research/design-max/r-trends|Design and consumer trends 2025–2026: what makes SOUL feel new in 2027 (2026-09-24)]] — `research/design-max/r-trends.md`
- [[micul-smecher/research/design-max/render-brief|Render brief v5: SOUL final + OU capsule + ALT A (PIATRA) + ALT B (MĂRGĂRITAR) (2026-09-24]] — `research/design-max/render-brief.md`

## Investitori și finanțare
- [[Finanțare — toate sursele pentru SOUL]] — **toate programele de bani (UE, România, credite AI, acceleratoare, investitori), top 5 și calendarul oct. 2026 → dec. 2027** (2026-10-12)
- [[Finanțare — expertul științific pentru PoC 1.1]] — **cine semnează Anexa 16: cerințele (Decizia CM 54), lista scurtă UPB, costul, coordonatorul tehnic, emailul gata de trimis** (2026-10-12)
- [[Finanțare — Start-Up Nation 2026 pentru SOUL]] — **Start-Up Nation sesiunea 2: nu se potrivește pentru SOUL/ARTEMIS; eligibilitate, buget teoretic, conflictul cu PoC 1.1** (2026-10-12)
- [[Finanțare — oferte de preț pentru PoC 1.1]] — **ofertele de preț: regula de 2 surse pe fiecare linie, furnizorii găsiți pe fiecare linie, bugetul estimat ≈ 189k €, emailuri de cerere de ofertă RO/EN** (2026-10-12)
- [[Finanțare — crowdfunding și alte surse pentru SOUL]] — **crowdfunding (Indiegogo da, Kickstarter nu pentru RO), precomenzi Shopify, investitori și regula PoC 1.1 despre asociați, credite, checklist înainte de bani, plan 2026–2028** (2026-10-20)
- [[micul-smecher/investors/DECK|SOUL: pitch deck content (v1, 2026-09-25)]] — `investors/DECK.md`
- [[micul-smecher/investors/FINANTARE-ROMANIA|Finanțare nerambursabilă și publică pentru SOUL — prin ARTEMIS DIGITAL S.R.L.]] — `investors/FINANTARE-ROMANIA.md`
- [[micul-smecher/investors/INVESTORS|SOUL: investor research, target list, 90-day raise plan (2026-09-25)]] — `investors/INVESTORS.md`
- [[micul-smecher/investors/poc-1.1/dosar/00-ELIGIBILITATE|00 · Matricea de eligibilitate — SOUL-PoC / ARTEMIS DIGITAL S.R.L.]] — `investors/poc-1.1/dosar/00-ELIGIBILITATE.md`
- [[micul-smecher/investors/poc-1.1/dosar/01-DOCUMENTE|01 · Documentele pentru MySMIS2021 — cine le face, cum se semnează, cât sunt valabile]] — `investors/poc-1.1/dosar/01-DOCUMENTE.md`
- [[micul-smecher/investors/poc-1.1/dosar/02-PUNCTAJ|02 · Punctajul ETF — cum luăm maximul și cât e realist]] — `investors/poc-1.1/dosar/02-PUNCTAJ.md`
- [[micul-smecher/investors/poc-1.1/dosar/03-NUCLEU-PROIECT|03 · Nucleul proiectului SOUL-PoC]] — `investors/poc-1.1/dosar/03-NUCLEU-PROIECT.md`
- [[micul-smecher/investors/poc-1.1/dosar/04-CE-TREBUIE-SA-FACA-ANDU|04 · Ce trebuie să faci tu, Andu (în ordine)]] — `investors/poc-1.1/dosar/04-CE-TREBUIE-SA-FACA-ANDU.md`
