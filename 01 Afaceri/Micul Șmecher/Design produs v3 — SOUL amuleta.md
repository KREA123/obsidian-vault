---
tip: afacere
afacere: Micul Șmecher
status: direcție în lucru (concept E)
actualizat: 2026-10-03
---

# Design produs v3 — SOUL (familia de forme, fără toartă)

> **Actualizare 2026-10-03 — designul FINAL e MĂRGĂRITAR** (decizia lui Andu din 2026-09-26, după HOPA): mărimea **M ≈ 90 × 101 × 31,5 mm** (89,9 × 101,1 × 31,5), **aluminiu 6061** sablat + anodizat în **5 culori** (Argint, Grafit, Albastru noapte, Jar, Șampanie), sticlă neagră Ø74,3 cu teșitură de 45°, nimic altceva pe față, bază plată cu picior oval, difuzor în cusătura laterală, încărcare jos în capsula OU. Randări: `micul-smecher/renders/v9/` (CGI). Prototipul P0 printat e mai mare (≈ 112 × 125 × 31,6 mm după STL), pentru că placa Waveshare 2.8C are sticla Ø95,9 lipită: `micul-smecher/prototip/`, planșe `micul-smecher/blueprints/final/`. **Tot ce urmează mai jos (Ø64, plastic PC, concept E) e istoric.** Harta: [[SOUL — Harta memoriei]] · pași: [[De continuat — SOUL]].

> **Actualizare 2026-09-24 seara:** cercul simplu Ø64 (concept E) a fost respins — „cerc mic și urat”. Mergem înapoi la **formele cu caracter**: piatra ovală în picioare (ca în prototipul SoulOS), norul, lacrima, amuleta — **mai mari**, **fără toartă**, corp lucios perlat (ieftin, injectat). Randări: `micul-smecher/renders/v4/`. Restul notei (strategia AirTag, husa, costurile) rămâne valabil.

> **Ce a spus Andu (2026-09-24), în ordine:**
> 1. Prima variantă (rotundă, fereastra neagră, ochii vii) are suflet; piatra culcată v2 părea plastic ieftin.
> 2. „Amuletă” = **forma**, nu purtat la gât.
> 3. Trebuie să fie **ieftin de făcut**, **mai mare**, **bun de ținut în mână**, și **fără toartă** — toarta de agățat arată ieftin. Agățatul vine dintr-o **husă** separată.

Cercetări: `micul-smecher/research/07-amulet-design-language-2026-09-24.md`, `08-wow-design-cmf-2026-09-24.md`. Randări: `micul-smecher/renders/v3/concepts/`.

## Strategia AirTag
AirTag e plastic lucios + oțel, și totuși arată scump. Secretul: **un obiect curat, fără nimic agățat de el**, materiale ieftine dar lucioase și precise, și **accesoriile se vând separat** (husă, breloc, curea). Facem la fel.

## Cum arată
| | |
|---|---|
| Formă | piatră-lentilă rotundă **Ø64 mm**, 18 mm la centru, ~9 mm la margine; spatele bombat, se așază în palmă ca o piatră de râu |
| Față | sticlă neagră ușor bombată **Ø56** — marginea vopsită negru-adevărat, deci toată sticla pare ecran; ochii plutesc în negru (≥85% din față e sticlă) |
| Ramă | inel subțire de aluminiu sablat, **o singură muchie lustruită** care prinde lumina |
| Spate | plastic (PC) injectat, **lucios**, colorat: alb, grafit, salvie, nisip, lila |
| Nimic sus | fără toartă, fără șuruburi vizibile |
| Greutate | ~75 g (cu o plăcuță de oțel înăuntru → se simte dens și ține de suportul magnetic) |
| Ecran | 1,75" AMOLED rotund (cel mai mare rotund cu negru adevărat pentru placa noastră) |

## Accesorii (bani în plus, ca la AirTag)
- Husă din silicon cu buclă (breloc / geantă) — preț țintă €19
- Husă din piele cu șnur scurt — €39
- Suport magnetic de birou, înclinat ~15° — €29

## Cât costă carcasa [estimări, de confirmat cu oferte reale]
| Piesă | 1.000 buc. | 10.000 buc. |
|---|---|---|
| Sticlă față cu margine neagră | $2,5–4 | $1,5–2,5 |
| Inel aluminiu (CNC / extrudat + sablat) | $4–7 | $2–4 |
| Spate PC lucios | $1,5–3 | $0,5–1,5 |
| Plăcuță oțel, garnituri, adeziv | $1–2 | $0,5–1 |
| **Carcasă total** | **~$9–16** | **~$5–9** |
| Matriță spate (o singură dată) | $15–30k | — |
| Husă silicon (cost) | $1–2 | $0,6–1,2 |

Față de titan ($30–100/buc.) sau ceramică (matriță $40–120k), e de ~5–10× mai ieftin. Prețul la client poate rămâne în zona €149–179 cu marjă sănătoasă.

## Semnătura
- **„Apasă ochiul. Te ascultă.”** — toată fața e butonul.
- **Inel de lumină** subțire între sticlă și ramă (albastru = ascultă, chihlimbar = Claude cere voie).
- Merge **fără AI**, cu **Claude-ul tău** sau cu **ChatGPT-ul tău**.

## Pașii următori
1. Andu alege din randările concept E (culoare, mărime Ø60 / 64).
2. Trei machete printate 3D la Ø60 / 62 / 64, ținute în mână câteva zile.
3. Oferte reale: sticlă (furnizori de sticlă pentru ceasuri), inel de aluminiu, matriță PC.
4. Refacem planurile tehnice pentru concept E.
