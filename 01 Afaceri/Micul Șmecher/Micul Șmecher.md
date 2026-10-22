---
tip: afacere
afacere: Micul Șmecher
status: activ
actualizat: 2026-10-22
---

![[suflet_hero.png]]

# Micul Șmecher — produsul SOUL

> **Decizia din 2026-10-20** ([[Jurnal decizii]]): **produsul final e mărimea S** — MĂRGĂRITAR la scara lui de design, **63 × 70,8 × 23 mm**, sticlă neagră plată **Ø52**, ecran rotund **AMOLED 1,75″ 466×466** (negru adevărat), placa de dezvoltare Waveshare ESP32-S3-Touch-AMOLED-1.75, LiPo 750 mAh, randări `renders/v10/` (CGI). **Mărimea M** (≈ 90 × 101 × 31,5 mm, placa 2.8C, ecran 2,8″, SoulOS 1.9.1) rămâne **prototipul** pentru teste și dovada TRL 3. Cifrele: `micul-smecher/docs/size-s.json`, `docs/12-SIZE-S.md`.
>
> **Starea la 2026-10-03** (mărimea corectată la 2026-10-22): SOUL = obiect din **aluminiu** în forma **MĂRGĂRITAR**, mărimea **S** (≈ 63 × 70,8 × 23 mm, ecran rotund AMOLED 1,75″, 5 culori; prototipul de lucru e mărimea M, ≈ 90 × 101 × 31,5 mm, ecran 2,8″), cu doi ochi vii (eyes v2) și **SoulOS**. Fiecare om își conectează **propriul AI** (nu plătim noi AI); merge și offline. Harta completă: **[[SOUL — Harta memoriei]]** · pașii următori: **[[De continuat — SOUL]]**.
>
> *Paragraful de mai jos e descrierea inițială (2026-09-24), păstrată ca istoric.*
> **Pe scurt (24 sep.):** o amuletă din sticlă mată cu doi ochi vii pe un ecran AMOLED rotund. E **vie și fără internet**, devine **AI-ul tău personal** când ții degetul pe „piatră” (Claude sau ChatGPT în spate) și **se leagă deja de Claude Code / Cowork** pe calculator. „Laboratoarele fac creierul. Noi facem corpul și sufletul.”

Continuarea proiectului [[Gadget WISP]] (sesiunile de concept „Cubul viu” și „Micul șmecher” v0.9.3).

## Ce există acum (2026-10-03)
| Piesă | Stare | Unde |
|---|---|---|
| Designul final MĂRGĂRITAR, **mărimea S** (din 2026-10-20), aluminiu, 5 culori | ✅ randări v10 (CGI, nu poze); M = prototipul, randări v9 | `micul-smecher/renders/v10/`, `renders/v9/`, `docs/size-s.json` |
| **S-P0**, pilotul lui S (placa Waveshare AMOLED-1.75, 63 × 70,8 × 25,65 mm) | ✅ STL/STEP plastic + notă de asamblare + planșă; ⏳ placa de cumpărat | `prototip/stl/s/`, `prototip/step/s/`, `blueprints/final/soul_s_2_p0_kit.png` |
| Prototipul M (P0-M printat, ≈ 112 × 125 × 31,6 mm), pentru teste și TRL 3 | ✅ STL-uri + planșe; ⏳ de comandat și printat | `prototip/stl/plastic/`, `prototip/COMANDA.md`, `blueprints/final/soul_m_*` |
| Electronica: M = Waveshare 2.8C + LiPo 803450; S = Waveshare AMOLED-1.75 + LiPo 503030 (~450 mAh [estimare]) | ⏳ de cumpărat (câte o placă) | `prototip/COMANDA.md`, `docs/01-BOM.md` |
| Firmware **SoulOS Alive 1.9.1** (M: `lcd28`, imaginea `release/SOUL-2.8C-install.bin`; S: `amoled175`, toate ecranele pe 466 px + difuzorul ES8311, imaginea `release/SOUL-1.75-install.bin`) | ✅ 245 de teste pe PC/simulator; ⏳ neîncărcat pe placă | `firmware/`, `firmware/SOUL-S.md`, `firmware/BRINGUP.md` |
| Cost S pe bucată [estimare] | ≈ 144 € la 100, ≈ 74 € la 1.000 (M: 215 / 98 €) | `docs/01-BOM.md`, `docs/factory/SOUL-fabrica-model.xlsx` |
| SOUL Cloud (pairing, gateway, conector OAuth MCP, `/pair`, `/me`); AI inclus oprit | ✅ testat cu falsuri; ⏳ nedeployat, netestat cu claude.ai real | `ai/`, `docs/07-CONNECT-AI.md` |
| SOUL Bridge (Claude Pro/Max prin Claude Code oficial) | 🧪 prototip, zonă gri de politică | `bridge/`, `docs/08-OWN-CLAUDE.md` |
| Ochii v2: 120 de designuri, 31 de expresii, giroscop | ✅ | `eyes/` · https://claude.ai/artifact/M8CVFPvTN3FCj6fC9UbA3D |
| SoulOS v4 (prototip web) | ✅ | `os/` · https://claude.ai/artifact/BFboeyYNYTUBrzsiB9uEfA |
| Pagina de lansare v2 (listă de așteptare, demo) | ✅ | `site/` · https://claude.ai/artifact/WZtQ7JpCjpj6M3sfgJugHC |
| Brand Package v1.0 + brand book | ✅ | `brand/SOUL-Brand-Package/` (+ `.zip`) |
| Trailer v3 (47 s, 16:9 + 9:16); v4 oprit | ✅ | `trailer/` |
| Pachetul complet | ✅ refăcut 2026-10-03 (~90 MB) | `dist/SOUL-package.zip` |

## Ce exista pe 2026-09-24 (istoric)
| Piesă | Stare | Unde |
|---|---|---|
| Firmware „Suflet” (ochi, dispoziție, 24 de reacții, personalitate unică din cip, rarități) | ✅ compilează pe ambele plăci, 24/24 teste | `micul-smecher/firmware/` |
| „Works with Claude” (protocolul Bluetooth al Claude Desktop: lucrează / cere aprobare / sărbătorește) | ✅ în firmware, testat pe PC | `firmware/lib/Suflet/src/ClaudeLink.*` |
| Simulator: clipuri din codul real (boop, tors, amețit, somn, „mi-a fost dor”, AI, Claude, noapte) | ✅ | `micul-smecher/media/` |
| Creierul AI în cloud (Claude): naștere de personaj, conversație, memorie, mementouri, notițe, jurnalul zilei | ✅ 9/9 teste, fără cheie API încă | `micul-smecher/ai/` |
| **Randări fotorealiste** ale produsului (Blender): erou, 4 forme, noapte, pe geantă, pe birou, vertical social, turntable | ✅ (randări de concept, nu poze) | `micul-smecher/renders/` |
| Carcasă 3D parametrică (OpenSCAD): 4 forme × 2 plăci, față/spate/capac/lentilă + suport de birou, 33 STL verificate | ✅ de printat după măsurători cu șublerul | `micul-smecher/cad/` |
| Pagina de lansare / pre-comandă (EN/RO, ochi vii în browser, demo Claude, rezervări) | ✅ previzualizare: https://claude.ai/artifact/BUAPPdP1W5xnCvSVcsQXoX | `micul-smecher/site/` |
| Cercetare (piață, hardware, conformitate, AI, brand, finanțare) — cu surse | ✅ | `micul-smecher/research/` |

## Notele proiectului
- **[[SOUL — Harta memoriei]]** — harta completă: fiecare document, cercetare, cod, plan, randare și dosar de finanțare
- [[Finanțare — PR BI PoC 1.1 pentru SOUL]] — grantul PoC 1.1 (dosarul complet în `micul-smecher/investors/poc-1.1/dosar/`)
- **Pachetul complet SOUL (EN):** `micul-smecher/docs/00-START-HERE.md` (BOM, fabricație, software, conformitate, plan de lansare, furnizori) · arhivă: `micul-smecher/dist/SOUL-package.zip`
- [[Viziunea — momentul iPhone]] — ce lansăm, de ce e altceva, scenariul filmului de lansare
- [[Planul de bani Micul Șmecher]] — fazele, cifrele pe bucată, scenarii, finanțare, filtrul celor 5 întrebări
- [[Produs și dezvoltare Micul Șmecher]] — plăci, piese, ce cumperi azi, prototipul în 14 zile, drumul spre producție
- [[De continuat — SOUL]] — **pașii următori** (fondator + Claude)
- [[SOUL — Cereri parteneriat Anthropic și OpenAI]] — emailul către Anthropic și formularul „Sign in with ChatGPT”
- [[Design produs v3 — SOUL amuleta]] — istoria designului (Ø64 → v4 → HOPA → **MĂRGĂRITAR**, final)
- [[Design produs v2 — SUFLET Pebble]] — (abandonat) piatra de buzunar; funcțiile și bateria rămân utile
- [[Brand și lansare Micul Șmecher]] — nume, carta companionului, mecanica de lansare, conținut
- [[Conformitate și riscuri Micul Șmecher]] — CE, baterie, AI Act, Anthropic, pre-mortem
- [[Piață și concurență Micul Șmecher]] — cine a vândut ce, la ce preț

## Deciziile care îți aparțin (Andu)
- [x] **Numele**: **SOUL** (ales de Andu, 2026-09-24) — urmează verificare EUIPO + domeniu înainte de orice cheltuială pe brand.
- [x] **Forma**: MĂRGĂRITAR (2026-09-26). **Fără Founders 00** (2026-09-26). **Fără AI inclus plătit de noi** (2026-10-03). **Firmă**: ARTEMIS DIGITAL S.R.L., fără firmă nouă (2026-09-25).
- [ ] ~~Prețul Founders Desk Edition~~ — scos odată cu Founders 00; pe site „de la €249”, doar listă de așteptare.
- [ ] Cumperi placa 2.8C + bateria și printezi P0-M (teste, TRL 3) și **o placă Waveshare ESP32-S3-Touch-AMOLED-1.75** pentru S — vezi [[De continuat — SOUL]].

## Următoarele 7 zile (lista din 24 sep., depășită — valabilă e [[De continuat — SOUL]])
1. Comanzi plăcile (1.43 pentru Claude Buddy, 1.75 pentru voce) + bateria + comutatorul.
2. Primești → flash firmware (`pio run -e amoled143 -t upload`) → pairing cu Claude Desktop (Developer → Open Hardware Buddy).
3. Filmezi 10 clipuri verticale reale (lista în [[Brand și lansare Micul Șmecher]]).
4. Pagina de așteptare online (domeniu + formular) — fără plăți încă.
5. Postezi clipul „Claude îmi cere aprobarea pe o amuletă” pe X / Reddit r/ClaudeAI / Hacker News.
