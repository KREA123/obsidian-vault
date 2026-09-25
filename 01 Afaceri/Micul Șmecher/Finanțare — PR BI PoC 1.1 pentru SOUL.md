---
tip: finanțare
afacere: Micul Șmecher
program: PR BI P1/1.1/1/2026 — Proof of Concept
actualizat: 2026-09-25
---

# PR BI 1.1 „Proof of Concept” — ne încadrăm cu SOUL?

**Răspuns scurt: da, ne încadrăm pe fond, dar mai sunt câteva condiții de verificat și câteva lucruri de făcut până la depunere (~noiembrie 2026).** Grant **€50.000–200.000, până la 100%, de minimis**, prin **ARTEMIS DIGITAL S.R.L.**

Documentele oficiale primite de la Andu (Anexele 3, 10, 16, 18) sunt salvate în `micul-smecher/investors/poc-1.1/`. Ghidul Solicitantului final nu l-am primit încă; condițiile de eligibilitate de mai jos vin din ghidul în consultare. Cercetarea de fond: `micul-smecher/investors/FINANTARE-ROMANIA.md`.

## De ce se potrivește
- Programul finanțează trecerea unei idei de la **TRL 3 → TRL 4–5**, adică de la „merge pe masă, pe componente” la „merge într-un mediu apropiat de cel real”. Exact asta e SOUL acum.
- Domeniile RIS3 București-Ilfov: SOUL intră în **TIC** + **Sisteme și componente inteligente** (+ eventual **Industrii creative** prin design). Două sau mai multe domenii înseamnă 5 puncte.
- Nu cere o vechime minimă a firmei și nici profit.

## Condiții care ne pot elimina (de verificat în actele ARTEMIS)
| Condiție | De ce contează | Stare |
|---|---|---|
| **Nicio schimbare de asociați/administratori după 04.06.2026** | Altfel e considerată „condiție artificială” și cererea e respinsă | ❓ Andu confirmă |
| **IMM** (ultimele 2 bilanțuri), fără datorii la stat | Condiție de bază | ❓ |
| **De minimis** primit în ultimii 3 ani (ARTEMIS + firmele legate) < €300k minus grantul cerut | Plafonul se socotește pe toate firmele lui Andu la un loc | ❓ verifici în RegAS |
| **Nicio achiziție pentru proiect înainte de depunere** | Efectul stimulativ | ⚠️ Placa de test pentru dovada TRL 3 se poate cumpăra, dar **nu o punem în buget** |
| **Raportul științific (Anexa 16) semnat de un expert** cu ≥ 5 ani experiență în domeniu, ≥ 2 publicații în ultimii 10 ani, acreditări; **nu angajat** (sau expert intern, dacă ghidul permite) | Obligatoriu pentru atestarea TRL 3 | ❌ **trebuie găsit** (UPB — Electronică/Automatică, IMT București, ICI) |
| **Dovezi TRL 3**: minim 2 dovezi experimentale | Obligatoriu | 🟡 Avem firmware testat (55 teste), simulator, serviciu AI (49 teste), prototip SoulOS, CAD. **Ne lipsește testul pe placa fizică**: cumpărăm placa Waveshare, rulăm firmware-ul, filmăm și măsurăm |
| Sediu sau punct de lucru în București/Ilfov | Pentru punctaj | ✅ probabil (ARTEMIS e în București) |

## Punctaj estimat (grila ETF, max 100)
| Criteriu | Max | Ce putem lua | Cum |
|---|---|---|---|
| 1.1 RIS3 (≥ 2 domenii) | 5 | **5** | TIC + Sisteme inteligente |
| 1.2 Problemă relevantă internațional | 15 | **10–15** | Date de piață + competitori (research 01, 04, 11) |
| 1.3 Sediu în BI până la 31.12.2025 | 5 | **5** | ✅ dacă sediul e vechi |
| 1.4 Publicare open-access cu peer-review | 10 | **10** | Articol OA despre randarea ochilor + tastatura rotundă + AI local-first (buget pentru taxa de publicare) |
| 1.5 Economie circulară | 5 | **5** | Baterie înlocuibilă, șuruburi, aluminiu reciclabil, reparabil, update-uri OTA |
| 2.1 Plan de afaceri (piață, etape, competiție, **protecție IP**, riscuri) | 15 | **13–15** | Avem aproape tot; IP = cerere de marcă EUIPO „SOUL” + **desen industrial** pe formă |
| 2.2 Buget (2 oferte pe fiecare linie, plafoane salariale) | 7 | **5–7** | Cerem oferte: CNC, print 3D, laborator, plăci |
| 2.3 Raport științific TRL | 15 | **10–15** | Depinde de expertul semnatar |
| 3.1 Experiența echipei (doctor sau ≥ 5 ani + 1 expert cu ≥ 2 ani) | 5 | **0–5** | ⚠️ Punctul slab: îți trebuie un **coordonator tehnic** cu experiență (angajat sau colaborator) |
| 3.2 Experiență CDI (firma + un membru) | 4 | **2–4** | Istoricul de lucru SOUL (git, teste, rapoarte) + proiecte IT KREA |
| 4.1 Strategia post-PoC pe 5 ani | 5 | **5** | Avem: pilot 25 buc. → CE → Standard |
| 4.2 ≥ 2 scrisori de intenție | 4 | **4** | Ex.: un distribuitor/retailer, clienți KREA, un laborator universitar |
| 4.3 Tânăr ≤ 24 ani student în echipa CD + o măsură de egalitate de șanse | 5 | **5** | Angajezi un student (UPB) part-time |
| **Total realist** | 100 | **~80–95** | Dacă rezolvăm expertul, coordonatorul tehnic și scrisorile |

## Ce ar finanța concret (TRL 3 → 5)
- **Prototipuri de laborator (TRL 4):** plăci, carcase CNC din aluminiu și printate, baterii, capsula OU.
- **Validare în mediu relevant (TRL 5):** ~10–20 unități de test la utilizatori reali, măsurători (autonomie, latență voce, semnal radio prin metal, lizibilitatea tastaturii).
- **Cercetare-dezvoltare:** salarii (coordonator tehnic, inginer firmware, student), un expert extern, pre-testare CE (EMC/radio), protecție IP (marcă, design), publicare open-access, consultanță, audit.
- **Nu intră:** seria de vânzare de 25 de bucăți și certificarea CE finală. Astea sunt TRL 6–7, pentru programul PR BI 1.2 sau altele.

## Pașii următori (în ordine)
1. **Andu verifică** cele 4 condiții „❓” de mai sus (acționariat, IMM, datorii, de minimis) și îmi trimite rezultatele.
2. **Cumpără placa Waveshare 1.75** (fără s-o pună în buget) → rulăm firmware-ul pe ea, filmăm → **dovada TRL 3**.
3. **Găsim expertul** pentru raportul științific (UPB/IMT/ICI) + un **coordonator tehnic** cu ≥ 5 ani experiență în electronică/embedded.
4. **Cerem ofertele** (câte 2 pe linie) și **scrisorile de intenție** (minim 2).
5. **Claude completează** Anexa 3 (plan de afaceri) și draftul pentru Anexa 16 (raport științific) cu toate datele SOUL, corelate între ele.
6. Depunere în **MySMIS2021** când se deschide apelul (~noiembrie 2026).
