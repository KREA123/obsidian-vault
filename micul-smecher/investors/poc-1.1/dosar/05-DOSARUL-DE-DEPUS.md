---
tip: finanțare
proiect: SOUL-PoC
rol: dosarul practic de depunere în MySMIS2021, fișier cu fișier
actualizat: 2026-10-02
sursa: Ghid 03.06.2026 §7.4 (p. 68–71), §7.5 (p. 71–75); Grila ETF (Anexa 10)
---

# 05 · Dosarul de depus, fișier cu fișier

Tot ce se încarcă în **MySMIS2021**, în ordinea din ghid (§7.4). Fiecare fișier: **PDF semnat electronic de Andu** cu semnătură calificată. Documentele semnate pe hârtie (CV-uri, fișe de post, scrisori) se scanează integral și apoi se semnează electronic.

Legendă: ✅ gata · 📝 draft există, de completat · 🔲 model gata, de semnat de alții · ❌ nu există încă · 🏛 vine de la o instituție.

## Rolul lui Andu în proiect
| Calitate | Ce înseamnă concret | Unde apare |
|---|---|---|
| **Reprezentantul legal al solicitantului** (administratorul ARTEMIS) | semnează electronic tot dosarul; răspunde juridic pentru Declarația unică; semnează Raportul științific ca „solicitant” | toate documentele |
| **Managerul de proiect** (20 h/lună, 18 €/h, activitatea A8) | coordonare, achiziții (Ord. MFE 1284/2016), raportări, relația cu ADR BI, protecția IP, acordurile comerciale (R3, R5) | `draft/Fisa_post_Manager_proiect.docx` |
| **Membru cu experiență CDI** (Grila 3.2b, 2 p.) | creatorul SOUL: firmware, serviciul AI, SoulOS, CAD (dovezile D1–D8) | CV-ul lui Andu + Raportul tehnic CDI |
| **Cedentul drepturilor** | SOUL e creat de Andu ca persoană fizică → cesiune gratuită către ARTEMIS înainte de depunere | `draft/Declaratie_cesiune_drepturi_MODEL.docx` |

Andu **nu** e coordonatorul tehnic/științific și **nu** e expertul care validează raportul.

⚠ Salariul de manager se plătește doar dacă contabilul confirmă că administratorul poate avea CIM cu ARTEMIS. Altfel, managementul rămâne în sarcina lui Andu, dar fără cost în buget.

---

## A. Documentele OBLIGATORII la depunere (§7.4)

| # MySMIS | Fișierul de încărcat | Ce e / cine îl face | Stare | Sursa / modelul |
|---|---|---|---|---|
| 1 | **Cererea de finanțare** | se completează direct în formularul MySMIS; textele le redactează Claude din `03-NUCLEU` | 📝 | `03-NUCLEU-PROIECT.md` |
| 2 | `02_Declaratia_unica.pdf` | **generată de MySMIS** (Anexa 2); Andu verifică fiecare punct și o semnează | ❌ (apare la deschiderea apelului) | MySMIS |
| 3 | `03_Declaratie_IMM_Anexa7.pdf` | contabilul completează cifrele 2024 + 2025, inclusiv pentru firmele legate | ❌ | Anexa 7 din ghidul final |
| 4 | `04_Plan_de_afaceri_Anexa3.pdf` | ⚠ **fără el: respingere fără clarificări** | 📝 61 de câmpuri galbene | `draft/Anexa_3_Plan_Afaceri_SOUL_DRAFT.docx` |
| 5a | `05a_CV_Andu.pdf` | CV Europass + diplome | ❌ | [europass.europa.eu](https://europass.europa.eu) |
| 5b | `05b_CV_Coordonator_tehnic.pdf` | CV Europass semnat + diplome + publicații + **declarație de disponibilitate** | ❌ de găsit | `draft/Declaratie_disponibilitate_MODEL.docx` |
| 5c | `05c_CV_Inginer_embedded.pdf` | la fel | ❌ de găsit | idem |
| 5d | `05d_CV_Student.pdf` | CV + **adeverință de student 2026–2027** + copie CI (vârsta ≤ 24) | 🔲 studentul există | – |
| 5e | `05e_Fise_de_post.pdf` | **4 fișe de post**, fiecare semnată de titular (ghidul cere fișe pentru *toate* pozițiile) | 🔲 | `draft/Fisa_post_*.docx` (4) |
| 6 | `06_Raport_stiintific_Anexa16.pdf` | ⚠ **fără el: respingere fără clarificări**; semnat de Andu **și** de expert | 📝 69 de câmpuri galbene | `draft/Anexa_16_Raport_Stiintific_SOUL_DRAFT.docx` |
| 6.1 | `06.1_Dovezi_TRL3.pdf` | raportul de laborator pe placa 2.8C (X1–X8) + loguri + linkuri video + hash git | ❌ placa necomandată | protocolul îl scrie Claude |
| 6.2 | `06.2_Cesiune_drepturi.pdf` | contractul Andu → ARTEMIS + lista componentelor open-source, **datat înainte de depunere** | 🔲 de văzut de avocat | `draft/Declaratie_cesiune_drepturi_MODEL.docx` |
| 7 | `07_Expert_CV_si_dovezi.pdf` | CV-ul expertului + dovezi: ≥ 5 ani în domeniu, ≥ 2 publicații în ultimii 10 ani (cu DOI), certificări din ultimii 10 ani | ❌ de găsit | e-mailul din `draft/Email_UPB_expert_si_echipa.md` |
| 8 | `08_Centralizator_costuri_Anexa19.pdf` + `08.x_Oferte_*.pdf` | **2 surse pe fiecare linie de buget** (oferte fără comandă sau capturi datate de pe site-uri) | ❌ | `01-DOCUMENTE.md` §C (lista liniilor); Anexa 19 din ghidul final |
| 9 | `09_Certificat_constatator.pdf` | de la ONRC, emis **cu cel mult 30 de zile înainte de depunere** | 🏛 se cere în ultima lună | portal ONRC |
| 10 | `10_Situatii_financiare_2025.pdf` | F10 + F20 + F30 + F40 + recipisa | 🏛 contabilul | – |
| 11 | `11_CI_Andu.pdf` | actul de identitate al reprezentantului legal | ✅ | – |

## B. Documente pentru PUNCTAJ (se depun tot atunci; clarificările nu mai pot crește punctajul)

| Fișier | Pentru | Puncte | Stare | Model |
|---|---|---|---|---|
| `12a_Scrisori_intentie.pdf` (≥ 2, ideal 3–4, de la entități diferite, datate cu ≤ 6 luni înainte) | 4.2 | 4 | 🔲 | `draft/Scrisoare_de_intentie_MODEL.docx` |
| `12b_Politica_egalitate_sanse.pdf` (decizia administratorului, datată înainte de depunere) | 4.3b | 2 | 🔲 Andu semnează | `draft/Politica_egalitate_sanse_DECIZIE.docx` |
| `12c_Raport_activitate_CDI_SOUL_2026.pdf` (git, teste, simulator, prototip; „simplele declarații nu sunt suficiente”) | 3.2a | 2 | ❌ Claude îl redactează | – |
| `12d_Scrisoare_laborator.pdf` (acces la laborator EMC/RF, cameră anecoică) | 2.3d | până la 3 | ❌ | varianta B din modelul de scrisoare |
| `12e_Cautare_TMview_DesignView.pdf` | 2.1d | – | ❌ Claude | – |
| `12f_Captura_APC_revista_OA.pdf` | 1.4 | – | ❌ Claude | – |

## C. NU se depun acum, dar trebuie să existe la contractare (15 zile lucrătoare)
Contractul de comodat/închiriere pentru spațiu (până în ~2032) · certificatele de atestare fiscală (stat + local) · cazierul fiscal · actul constitutiv consolidat · decizia asociatului de aprobare a proiectului · Anexele 5 (de minimis), 13 (plan de monitorizare), 14 · CIM-urile echipei. Detalii: `01-DOCUMENTE.md` §D.

---

## Ce lipsește din documentele oficiale
Ghidul final nu e publicat. Apar odată cu el: **Anexa 2** (Declarația unică, generată în MySMIS), **Anexa 7** (IMM), **Anexa 19** (Centralizatorul costurilor), **Anexa 20** (plafoanele de cheltuieli), **Anexa 15** (schema de minimis). Draft-urile se reverifică pe ele în ziua publicării.

## Calendar
- **Data-limită de depunere: nu există încă.** Ghidul din 03.06.2026 e versiunea de consultare, cu datele de deschidere și închidere lăsate goale (§4.3, p. 34). Până la 27.09.2026 cel final nu fusese publicat.
- **Regula din draft:** după publicarea ghidului final urmează **30 de zile de pregătire**, apoi **90 de zile de depunere** (§3.1, p. 21).
- Calendarul ADR BI anunța deschidere **și** închidere în **noiembrie 2026**, deci fereastra reală poate fi mult mai scurtă decât 90 de zile.
- Evaluarea se face în ordinea depunerii, iar la punctaj egal câștigă cine a depus primul (§8.4). **Ținta: dosarul complet înainte de deschidere, depunere în prima săptămână.**
- Limita absolută a proiectului: implementarea, inclusiv plățile, se termină până la **31.12.2029**.
