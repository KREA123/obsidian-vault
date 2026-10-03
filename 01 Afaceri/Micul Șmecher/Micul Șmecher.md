---
tip: afacere
afacere: Micul Șmecher
status: activ
actualizat: 2026-10-03
---

![[suflet_hero.png]]

# Micul Șmecher — produsul SOUL

> **Starea la 2026-10-03:** SOUL = obiect din **aluminiu** în forma **MĂRGĂRITAR**, mărimea **M** (≈ 90 × 101 × 31,5 mm, ecran rotund 2,8″, 5 culori), cu doi ochi vii (eyes v2) și **SoulOS**. Fiecare om își conectează **propriul AI** (nu plătim noi AI); merge și offline. Harta completă: **[[SOUL — Harta memoriei]]** · pașii următori: **[[De continuat — SOUL]]**.
>
> *Paragraful de mai jos e descrierea inițială (2026-09-24), păstrată ca istoric.*
> **Pe scurt (24 sep.):** o amuletă din sticlă mată cu doi ochi vii pe un ecran AMOLED rotund. E **vie și fără internet**, devine **AI-ul tău personal** când ții degetul pe „piatră” (Claude sau ChatGPT în spate) și **se leagă deja de Claude Code / Cowork** pe calculator. „Laboratoarele fac creierul. Noi facem corpul și sufletul.”

Continuarea proiectului [[Gadget WISP]] (sesiunile de concept „Cubul viu” și „Micul șmecher” v0.9.3).

## Ce există acum (2026-10-03)
| Piesă | Stare | Unde |
|---|---|---|
| Designul final MĂRGĂRITAR, mărimea M, aluminiu, 5 culori | ✅ randări v9 (CGI, nu poze) | `micul-smecher/renders/v9/` |
| Prototipul P0 (printat 3D, ≈ 112 × 125 × 31,6 mm după STL [de măsurat]) | ✅ STL-uri de print + planșe; ⏳ de comandat și printat | `prototip/stl/plastic/`, `prototip/COMANDA.md`, `blueprints/final/` |
| Electronica P0: Waveshare 2.8C (Alibaba ~140 lei [neverificat]) + LiPo 803450 (eMAG) | ⏳ de cumpărat | `prototip/COMANDA.md` |
| Firmware **SoulOS 1.2.0** (ochii, IMU, portal Wi-Fi, Claude/OpenAI cu cheia omului, SOUL Cloud, BLE Hardware Buddy) | ✅ compilat + testat pe PC/simulator; ⏳ neîncărcat pe placă | `firmware/`, `firmware/BRINGUP.md`, `firmware/release/` |
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
- [ ] Cumperi placa 2.8C + bateria și printezi P0 — vezi [[De continuat — SOUL]].

## Următoarele 7 zile (lista din 24 sep., depășită — valabilă e [[De continuat — SOUL]])
1. Comanzi plăcile (1.43 pentru Claude Buddy, 1.75 pentru voce) + bateria + comutatorul.
2. Primești → flash firmware (`pio run -e amoled143 -t upload`) → pairing cu Claude Desktop (Developer → Open Hardware Buddy).
3. Filmezi 10 clipuri verticale reale (lista în [[Brand și lansare Micul Șmecher]]).
4. Pagina de așteptare online (domeniu + formular) — fără plăți încă.
5. Postezi clipul „Claude îmi cere aprobarea pe o amuletă” pe X / Reddit r/ClaudeAI / Hacker News.
