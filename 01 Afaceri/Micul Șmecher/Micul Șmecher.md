---
tip: afacere
afacere: Micul Șmecher
status: activ
actualizat: 2026-09-24
---
# Micul Șmecher — brand de lucru SUFLET

> **Pe scurt:** o amuletă din sticlă mată cu doi ochi vii pe un ecran AMOLED rotund. E **vie și fără internet**, devine **AI-ul tău personal** când ții degetul pe „piatră” (Claude sau ChatGPT în spate) și **se leagă deja de Claude Code / Cowork** pe calculator. „Laboratoarele fac creierul. Noi facem corpul și sufletul.”

Continuarea proiectului [[Gadget WISP]] (sesiunile de concept „Cubul viu” și „Micul șmecher” v0.9.3).

## Ce există deja (construit pe 2026-09-24)
| Piesă | Stare | Unde |
|---|---|---|
| Firmware „Suflet” (ochi, dispoziție, 24 de reacții, personalitate unică din cip, rarități) | ✅ compilează pe ambele plăci, 24/24 teste | `micul-smecher/firmware/` |
| „Works with Claude” (protocolul Bluetooth al Claude Desktop: lucrează / cere aprobare / sărbătorește) | ✅ în firmware, testat pe PC | `firmware/lib/Suflet/src/ClaudeLink.*` |
| Simulator: clipuri din codul real (boop, tors, amețit, somn, „mi-a fost dor”, AI, Claude, noapte) | ✅ | `micul-smecher/media/` |
| Creierul AI în cloud (Claude): naștere de personaj, conversație, memorie, mementouri, notițe, jurnalul zilei | ✅ 9/9 teste, fără cheie API încă | `micul-smecher/ai/` |
| Carcasă 3D (OpenSCAD → STL) | în lucru | `micul-smecher/cad/` |
| Pagina de lansare / pre-comandă (EN/RO) | în lucru | `micul-smecher/site/` |
| Cercetare (piață, hardware, conformitate, AI, brand, finanțare) — cu surse | ✅ | `micul-smecher/research/` |

## Notele proiectului
- [[Viziunea — momentul iPhone]] — ce lansăm, de ce e altceva, scenariul filmului de lansare
- [[Planul de bani Micul Șmecher]] — fazele, cifrele pe bucată, scenarii, finanțare, filtrul celor 5 întrebări
- [[Produs și dezvoltare Micul Șmecher]] — plăci, piese, ce cumperi azi, prototipul în 14 zile, drumul spre producție
- [[Brand și lansare Micul Șmecher]] — nume, carta companionului, mecanica de lansare, conținut
- [[Conformitate și riscuri Micul Șmecher]] — CE, baterie, AI Act, Anthropic, pre-mortem
- [[Piață și concurență Micul Șmecher]] — cine a vândut ce, la ce preț

## Deciziile care îți aparțin (Andu)
- [ ] **Numele**: SUFLET (recomandat) sau altul — apoi verificare EUIPO + domeniu înainte de orice cheltuială pe brand.
- [ ] **Prețul Founders Desk Edition**: €119 (recomandat; la €99 rămân doar ~€33/bucată).
- [ ] **Modelul AI** pentru voce: Claude Opus 5 (implicit) vs Sonnet 5 / Haiku 4.5 (mai ieftine, mai rapide) — după un test real de latență și cost.
- [ ] **Firmă nouă** pentru proiect (SRL separat) — necesară pentru Startup Nation 2026 (250.000 lei) și pentru investitori.
- [ ] Cumperi kitul de prototip (~€120, lista în [[Produs și dezvoltare Micul Șmecher]]).

## Următoarele 7 zile
1. Comanzi plăcile (1.43 pentru Claude Buddy, 1.75 pentru voce) + bateria + comutatorul.
2. Primești → flash firmware (`pio run -e amoled143 -t upload`) → pairing cu Claude Desktop (Developer → Open Hardware Buddy).
3. Filmezi 10 clipuri verticale reale (lista în [[Brand și lansare Micul Șmecher]]).
4. Pagina de așteptare online (domeniu + formular) — fără plăți încă.
5. Postezi clipul „Claude îmi cere aprobarea pe o amuletă” pe X / Reddit r/ClaudeAI / Hacker News.
