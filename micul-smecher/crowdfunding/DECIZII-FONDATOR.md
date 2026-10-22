---
tip: decizii
afacere: Micul Șmecher
actualizat: 2026-10-22
---

# SOUL pe Indiegogo: ce decizi tu (după review-ul din 22.10.2026)

Kitul e făcut **sigur din oficiu**: unde trebuia o decizie de-a ta, textul folosește varianta prudentă și o marchează. Tu confirmi sau schimbi; scrii decizia în `03 Decizii/Jurnal decizii.md`, apoi eu schimb `facts.json` și refac textele, imaginile și video-ul.

## Decizii (o linie fiecare, cu recomandarea mea)

| # | Ce decizi | Până când | Ce e în kit acum | Recomand |
|---|---|---|---|---|
| **D1** | Campania după CE (regula ta: nicio plată de la clienți înainte de grant și CE) sau înainte de CE | acum | după CE (lansare 05.10.2027) | **Păstrezi regula.** Lansezi doar după decizia PoC 1.1 și după declarația UE de conformitate. |
| **D4** | Vârsta pe pagină: 16+ sau 18+ | înainte de pagina Upcoming (mar. 2027) | **18+** peste tot | **18+**: funcțiile AI cer cont API propriu, care e 18+. |
| **D9** | Data promisă | 07.09.2027 | **mai 2028** (lotul 1), **august 2028** (lotul 2), ~10 săpt. rezervă | **Păstrezi mai 2028.** Aprilie lasă doar 6 săptămâni de rezervă. |
| **D12** | Câte bucăți are lotul 1 | 07.09.2027 | **270** = First Light 150 + Campaign 100 + Two Souls 10 × 2; restul e „Campaign Price · batch 2” | **270**; crești limitele doar cu capacitate scrisă de la CNC, anodizare și asamblare. |
| **D13** | Marea Britanie în campania 1 | 01.06.2027 | **scoasă** | **Afară.** O deschizi în Late Pledge după poarta UK: declarația PSTI, DEEE/baterii în UK, TVA la import (~€320 la ușă pentru €249). |
| **D14** | SUA/Canada (FCC + ISED, ~€15k în plus înainte de campanie) | 31.01.2027 | afară; nu mai e stretch goal | **Afară.** Nu avem banii înainte de prima plată; revii după campanie. |
| **D15** | Rambursări: integral până la livrare sau până la comenzile pentru lot; mărimea rezervei | 07.09.2027, cu avocatul | integral până la livrare, rezervă 5 %, marcat „ciornă pentru avocat” | **Avocatul confirmă.** Probabil e obligatoriu oricum pentru consumatori; atunci mărim rezerva, nu tăiem promisiunea. |
| **D2** | Înregistrarea în scopuri de TVA + OSS | 07.09.2027, cu contabilul | „ne așteptăm să datorăm TVA”, plătit din banii strânși | **Te înregistrezi înainte de lansare**, cu OSS. La €70k campania singură nu trece sigur pragul de 395.000 lei; vânzările în alte țări UE peste €10k îl declanșează. |
| **D11** | Cine plătește CE + marketing (€59.500) înainte de campanie | 31.01.2027 | bani proprii și împrumuturi; pagina nu numește niciun grant | **Bani proprii, KREA, împrumuturi, Patria Credit.** Nimic din asta nu se cere și în PoC 1.1. |
| **D3** | Scara de prețuri | acum | B: €249 / €269 / Two Souls **€498** (€249 bucata) / Late €299, First Light cu numărul gravat pe picior | **B**, așa cum e acum. Obiectivul a scăzut la **€70.000**. |
| **D7** | Culorile la lansare | acum | Argint, Grafit, Jar | **Trei.** Mai puține mostre de referință și băi de anodizare. |
| **D8** | Placa din lotul 1 (A proprie / B Waveshare) | 15.01.2027 | B | **B** pentru lotul 1; A pentru un lot următor. |
| **D10** | Stable Pledge (ireversibil) | 21.09.2027 | nedecis | **Pornit doar dacă** toate ofertele (lot + curierat) sunt scrise la G3. |
| **D6** | Bani de marketing riscați | acum | până la €17.500 | **Da**, cu oprire la CPL > €3. |
| Titlu | Numele și sloganul campaniei | în draft | „SOUL: Living Eyes for Your Own AI” | **Varianta 1.** Promisiunea „se uită în sus când AI-ul are nevoie de tine” rămâne doar dacă G1 arată conectorul Claude mergând pe placa S. |

## Ce doar tu poți face (fără ele nu lansăm)

| # | Ce | Când | Recomand |
|---|---|---|---|
| **F1** | Filmarea reală: SOUL S din aluminiu, o singură dublă (G2), primul în galerie și la 0:00 în video | 12.02.2027 | Obligatoriu. Fără ea nu publici nici pagina Upcoming. |
| **F2** | Până la F1: fotografii și video reale cu prototipul M, etichetate „Prototype shown at a larger size (M)…” | cât mai repede (pentru lista de așteptare) | Filmezi M-ul care merge acum; altfel ștergi `{{img:prototype-m}}`. |
| **F3** | O mână reală care ține o machetă S printată 3D (etichetată „size model”), în locul mâinii CGI | dec. 2026 | Machetă din `prototip/stl/s/`, poză pe fundal deschis. |
| **F4** | Echipa: numele tău complet, o fotografie reală, 60–80 de cuvinte despre tine și 10–15 s la cameră (F09, la 0:15 în video) | înainte de Upcoming (mar. 2027) | Obligatoriu: azi pagina n-are nicio față și niciun nume. |

Cerințe de pe pagină care rămân deschise până trec porțile: `[[CE: …]]` (laboratorul și data declarației UE), `[[G1/G2/G3: …]]`, `[de completat: …]`, `{{URL:…}}`. `tools/check_copy.py --strict` le listează pe toate.
