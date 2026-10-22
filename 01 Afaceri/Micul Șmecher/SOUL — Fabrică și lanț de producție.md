---
tip: plan
afacere: Micul Șmecher
actualizat: 2026-10-22
---

# SOUL — Fabrică și lanț de producție

> Întrebarea lui Andu: „ce ar însemna să facem efectiv o fabrică? mică, pentru asta, sau un lanț de producție măcar”.
> Hub: [[Micul Șmecher]] · harta: [[SOUL — Harta memoriei]] · bani: [[Finanțare — toate sursele pentru SOUL]] · pași: [[De continuat — SOUL]].
> Modelul de calcul: `micul-smecher/docs/factory/SOUL-fabrica-model.xlsx` (foi: Rezultate, Ipoteze, Scenarii, Break-even, Capacitate). PDF de printat: `micul-smecher/docs/factory/SOUL-fabrica.pdf`.
> **[estimare]** = calculul meu, fără ofertă. **[neverificat]** = o singură sursă sau o sursă pe care n-am putut-o redeschide. Toate cifrele sunt în EUR fără TVA, **mărimea S**, dacă nu scrie altfel.
> **Actualizare 2026-10-22:** modelul e refăcut pe **mărimea S**, produsul final din decizia de pe 20.10.2026 (AMOLED 1,75″ 466×466, 63 × 70,8 × 23 mm, LiPo 603040 de 750 mAh, placa Waveshare ESP32-S3-Touch-AMOLED-1.75 la volume mici; `micul-smecher/docs/size-s.json`, `docs/12-SIZE-S.md` §3). CNC: semifabricat **0,4 kg/set** și ciclu **24 min/set** [estimare], față de 1,0 kg și 45 min la M. Carcasa externă, sablarea și anodizarea pe set = M × 0,65 [estimare] (`size-s.json` `cnc.external_shell_factor_vs_M`; același factor e în `01-BOM` SV-07 și în modelul de obiectiv al campaniei). **M** (placa 2.8C) rămâne prototipul și apare doar ca termen de comparație în foaia Break-even. Varianta veche pe M (121 €/buc. la 1.000) e înlocuită. Constructorul modelului: `micul-smecher/docs/factory/_tools/build_model.py`.

## 1. Răspunsul pe scurt

**O „fabrică mică” SOUL înseamnă 3 trepte. Fiecare se adaugă peste cea dinainte:**
- **T0 – atelier de asamblare și test.** Primești piese gata făcute. Tu montezi, încarci firmware-ul, calibrezi, testezi, gravezi seria și ambalezi. Costă ~€23k (configurat pentru 1.000/an) până la ~€39k (pentru 20.000/an) [estimare din model]. Îți trebuie 40–60 m² și 1–4 oameni.
- **T1 – plus celulă CNC proprie (carcasele).** Prima mașină cu tot ce trebuie pe lângă costă ~€104k [estimare]. Fiecare mașină în plus costă ~€92k. O mașină face ~17 seturi S pe schimb (la M erau ~9).
- **T2 – plus linie SMT proprie (plăcile).** O linie costă ~€36k [estimare]. Dar PCB-ul custom nici nu există încă.
- **Anodizarea rămâne externă în orice variantă.** Chimicale periculoase, ape uzate, autorizații. Iar culoarea pe 5 nuanțe e greu de ținut constantă.

**Când merită (după model):**
- Sub ~5.000 de unități/an, cel mai ieftin e **lanțul externalizat (A)**.
- Atelierul T0 costă cam cât box build-ul la un EMS. Îl faci pentru **control** (flash, calibrare, test, QC, serie), nu pentru bani.
- CNC-ul propriu iese **la egalitate** pe la ~3.800–5.000 de seturi S/an (la M: ~5.000). Câștigă clar doar la ~10–20k/an.
- SMT-ul propriu **nu câștigă clar niciodată**. Iese egal cu un EMS din România pe la 20.000 de plăci/an și pierde în fața JLCPCB la orice volum calculat.

**Recomandarea:**
- **25 de bucăți (pilot):** fără fabrică. Asamblezi tu, la birou. Carcasele și anodizarea le comanzi afară. Placa rămâne Waveshare. Faci un jig de test simplu. Investiție ~€2k [estimare din model].
- **1.000/an:** **lanț de producție**, nu fabrică. Alegi între un atelier T0 de 40–60 m² cu 1 operator part-time și box build la Felix EMS sau EMS-Electra. Decide oferta: dacă EMS-ul cere peste ~16,5 €/buc. pentru box build, atelierul tău e mai ieftin.
- **10.000/an:** atelier T0 cu 3–4 oameni pe ~150–200 m². Plăcile le face un EMS sau JLCPCB, carcasele un atelier extern. CNC propriu doar dacă ofertele pentru carcasa S trec de ~22 €/set la 5.000/an (ipoteza: ~23,5 €) și simularea CAM confirmă ≤ 24 min/set.

## 2. Cele 4 variante

| | **A – totul extern** | **B – atelier T0** | **C – T0 + CNC** | **D – T0 + CNC + SMT** |
|---|---|---|---|---|
| **Ce faci tu** | Design, firmware, comenzi, QC la recepție, vânzare | + asamblare, flash, calibrare, test, laser, ambalare | + frezezi carcasele, sablare, șanfren | + plantezi plăcile (SMT, reflow, AOI) |
| **Ce fac partenerii** | Tot: CNC, anodizare, PCBA, box build, ambalare | CNC, anodizare, PCBA, cutia | Anodizare, PCBA, cutia | Anodizare, cutia |
| **Investiție** | ~€2–7k (jig de test dat la EMS + mostre-etalon) | ~€23–39k | ~€128k la 1.000/an; ~€131k la 5.000/an (o singură mașină ajunge) | ~€164k la 1.000/an; ~€167k la 5.000/an |
| **Oameni** | Fondatorul | + 0,5–3,5 operatori + QC | + 1 programator CNC + operatori CNC | + 1 tehnician SMT |
| **Spațiu** | Biroul | 40–60 m² (T0), până la ~200 m² | + 60–100 m², curent trifazat 25–40 kVA, pardoseală pentru 2–3,5 t | + 40–60 m² |
| **Cost/buc. la 1.000** | **97 €** | 104 € | 138 € | 163 € |
| **Cost/buc. la 10.000** [interpolat] | ~64 € | ~64 € | ~61 € | ~63 € |
| **Când merită** | Acum, până la ~5k/an | De la pilot, pentru control | Clar abia la ~10–20k seturi/an | Practic niciodată |

- Cifrele de cost nu includ NRE-ul produsului (PCB, sticlă, matrițe pentru OU). Cu NRE, A costă 109 € la 1.000 (la M: 132 €).
- Modelul a calculat 100 / 1.000 / 5.000 / 20.000. Pentru 10.000 am luat media între 5.000 și 20.000 [estimare]. Diferențele de 2–3 € sunt sub eroarea estimărilor.
- Valorile exacte din model:

| €/buc. | 100 | 1.000 | 5.000 | 20.000 |
|---|---|---|---|---|
| A | 224,83 | **97,46** | **70,79** | 57,95 |
| B | 255,90 | 104,01 | 73,19 | 55,17 |
| C | 804,89 | 137,87 | 71,80 | 51,10 |
| D | 1.123,42 | 163,39 | 75,41 | **51,01** |

- Pentru comparație, aceleași scenarii pe M (modelul din 15.10.2026): A 311,68 / 121,09 / 87,77 / 71,23 €. S e cu ~24 €/buc. mai ieftin la 1.000 (−20 %), mai ales din carcasă (31,84 € vs 47,46 € livrată) și din placă.

- La 100 de bucăți marja (cu NRE) e negativă în toate variantele, la prețul de €249: A ajunge la −4,83 €/buc. La 100 de bucăți placa e Waveshare AMOLED-1.75, deci corpul e S-P0 (25,65 mm, LiPo 503030 ~450 mAh [estimare]), nu produsul de 23 mm. Cifrele de la 100 includ TVA-ul de 21%, pe care ARTEMIS nu-l poate recupera cât e sub plafonul de 395.000 lei.
- **Corecții după verificare:**
  - Timpul de 24 min/set S e scalat din cele 45 min ale lui M (× 0,53, docs/12 §3.2), iar 45 min era deja optimist pentru un Haas VF-2 cu axul de 8.100 rpm: acolo calcula 60–90 min/set M, adică ~32–48 min/set S [estimare]. Cele 24 min se potrivesc unei mașini rapide BT30 (Brother Speedio), care costă ~$100–150k [estimare MachineToolIndex]. Verifică prin simulare CAM pe STEP-ul S de 23 mm, care încă nu există.
  - Consumul de curent al atelierului T0 (1.000 kWh/lună la 1.000 buc.) pare mare. Cu 300–500 kWh, atelierul T0 bate box build-ul mai devreme de 1.554 buc./an.

## 3. Pașii fabricii, de la piesă la cutie

1. **Componente din Asia:** display rotund AMOLED 1,75″, modul ESP32-S3, celulă LiPo 603040 certificată, sticlă 2.5D Ø52. *(extern)*
2. **CNC carcasă**, cele 2 jumătăți, din aluminiu 6061. *(extern; T1 = tu)*
3. **Debavurare + degresare** în baie cu ultrasunete. *(extern; T1 = tu)*
4. **Sablare cu bile de sticlă** pentru textura mată. *(extern; T1 = tu)*
5. **Re-tăierea șanfrenului de 45°** după sablare, ca să lucească. *(extern; T1 = tu)*
6. **Anodizare în 5 culori.** *(mereu extern)*
7. **Recepție:** compari culoarea cu mostra-etalon (golden sample) și verifici cotele. *(tu)*
8. **Placa (PCBA):** la început Waveshare ESP32-S3-Touch-AMOLED-1.75, mai târziu PCB-ul propriu rotund (~Ø46 mm). *(EMS / JLCPCB; T2 = tu)*
9. **Flash firmware** pe 4–8 porturi în paralel. *(tu)*
10. **Lipești sticla și display-ul** cu inel de adeziv PSA decupat. *(tu)*
11. **Montaj:** placa, bateria, microfonul, difuzorul, șuruburile, închiderea. *(tu)*
12. **Test funcțional pe jig:** încărcare, IMU, touch, microfon, difuzor, BLE. Calibrare. *(tu)*
13. **Rodaj** de ~10 min (burn-in), fără om lângă. *(tu)*
14. **Laser:** seria și marcajele CE/WEEE pe bază. *(tu)*
15. **QC final + cântărire.** *(tu)*
16. **Bateria adusă la ≤30%**, apoi ambalare cu OU-ul în cutie. *(tu)*
17. **Depozitare** în dulap pentru Li-ion, apoi livrare (tu sau un 3PL). *(tu / 3PL)*

Manoperă: ~15–25 min/buc. cu fixturi [estimare]. Modelul folosește 25 min, adică ~16 buc. pe operator într-un schimb. Gâtuirea în T0 sunt oamenii. În C și D e mașina CNC: ~17 seturi S pe schimb (M: ~9).

## 4. Echipamente cu prețuri

| Echipament | Nou | Second-hand / alternativă | Sursă |
|---|---|---|---|
| Banc ESD (Treston) | €1.595–3.395 / stație | Kit ESD 386–702 lei | [wrepair](https://www.wrepair.com/product/esd-workstation-180x75cm/) |
| Jig de test cu pogo pin | Fixturfab $999 / $1.799 / $7.399 | DIY $500–2.000 + 1 săpt. lucru | [fixturfab](https://fixturfab.com/fixtures) |
| Stație de flash | Gratis (Espressif Flash Download Tool, mod Factory) + hub USB <€300 [estimare] | – | [Espressif](https://docs.espressif.com/projects/esp-test-tools/en/latest/esp8266/production_stage/tools/flash_download_tool.html) |
| Laser fibră MOPA | Gweike G6 €4.469 [neverificat, 429]; OMTech 60 W $4.199,99 | FabLab Jilava 0,20 €/cm² | [Gweike](https://shop.gweikecloud.com/products/g6-mopa-30w-60w-100w-fiber-laser-marking-engraving-machine) |
| Dulap Li-ion tip 90 | Düperthal XL €4.660; asecos €5.515 | – | [lion-care](https://www.lion-care.com/en/Dueperthal-BATTERY-standard-line-XL-storage-cabinet/DUPSHSBLSXL1) |
| Dozator adeziv (doar cu adeziv lichid) | Nordson Ultimus I €3.089,95 | Ultimus Plus $1.650; inel PSA = aproape gratis | [esd.equipment](https://esd.equipment/en/wl21683.html) |
| CNC Haas VF-2 | $70.995 listă SUA (prețul UE se cere de la HFO) | VF-2 2003 €14.000 + TVA; VF-2SSYT 2012 €32.500 + TVA | [MTI](https://machinetoolindex.com/machines/haas-vf-2) · [machineseeker](https://www.machineseeker.com/mss/haas+vf+2) |
| CNC Haas Mini Mill | $47.995 listă SUA | – | [MTI](https://machinetoolindex.com/machines/haas-mini-mill) |
| CNC Brother Speedio S500Xd2 | ~$100–150k [estimare MTI] | S500X2 2021: $67k cerut | [MTI](https://machinetoolindex.com/machines/brother-speedio-s500xd2) |
| CNC Hurco / Doosan | – | Hurco VMX24 la licitație în RO de la €7.500; Doosan DNM 4500 (2016) €42.000 | [Surplex](https://www.surplex.com/ro/m/centru-de-prelucrare-vertical-hurco-vmx24-782504.html) |
| CNC Tormach 1100MX (pilot) | $29.594 | – | [tormach](https://tormach.com/machines/mills/1100mx.html) |
| Scule, menghine, palpator | ~€10–25k [estimare] | – | – |
| CAM Fusion | $680/an | – | [vagon](https://vagon.io/blog/fusion-360-pricing) |
| Cabină de sablare 350 L | 3.872–6.539 lei cu TVA | – | [mtools](https://www.mtools.ro/scule-hidraulice/echipamente-de-sablare/echipamente-de-sablare/big-red-jack/dulap-de-sablare-cu-cabina-350-litri-si-aspirator-big-red-jack) |
| Compresor cu șurub 7,5 kW | 21.901 lei (Fiac); Fini €4.424 | Boge C9 €5.799 | [dedeman](https://www.dedeman.ro/ro/compresor-aer-cu-surub-cu-ulei-fiac-new-silver-10-7-5-kw-10-cp/p/1066403) |
| Baie cu ultrasunete 30 L | 2.859 lei – €2.320 | – | [multilab](https://www.multilab.ro/bai/baie_curatare_ultrasunete.html) |
| Pick-and-place | NeoDen YY1 €3.499; NeoDen4 ~€10,9–12k [neverificat, 503] | Juki RS-1R €46.437 | [esdshop](https://www.esdshop.eu/Neoden-YY1/) |
| Imprimantă pastă | NeoDen FP2636 €1.028,50 [neverificat, 503] | – | [neodentech](https://neodentech.eu/contents/en-uk/p55129_NEODEN-FP2636-Stencil-Printer-for-frameless-stencils.html) |
| Cuptor reflow NeoDen IN6 | $2.399–5.499 | – | [neoden-solution](https://neoden-solution.com/collections/reflow-ovens/products/neoden-in6-reflow-oven) |
| AOI | $1.800–15.999 [estimare: listări Alibaba; pagina oficială n-are preț] | – | [neodensmt](https://www.neodensmt.com/automatic-inspection-machine/nd880-offline-aoi-machine.html) |

Lipsesc prețuri pentru dulap de uscare MSL și X-ray.

## 5. Parteneri concreți (lanțul de producție)

**Din România:**

| Rol | Partener | De ce | Contact |
|---|---|---|---|
| PCBA + box build, pilot → sute | **Felix Electronic Services** (București, sector 2) | Toate pașii la un loc: SMT, AOI, CNC mic, carcase printate, standuri de test, ambalare | office@felix-ems.ro · [site](https://www.felix-ems.ro/index_ro.html) |
| PCBA + box build, 100 → 1.000+ | **EMS-Electra** (Iași) | Programare MCU, test funcțional, ambalare pentru retail | office@ems-electra.ro · [site](https://www.ems-electra.ro/en/services/electronic-manufacturing) |
| 1.000 → 10.000 | **ICCO EMT** (Brașov, Timișoara) | NPI, X-ray, ICT/FCT, box build, ISO 9001 | emt@icco.ro · [site](https://iccoemt.ro/en/) |
| PCBA, volum | **Epsicom** | 3 linii SMT, până la 100k buc./an, test RF | office@epsicom.com · [site](https://epsicom.ro/) |
| Peste 10.000 | Cicor Arad, HELBAKO Timișoara, Elemaster, EC Electronics Petroșani | Firme mari; un client mic e prioritate mică | vezi Surse |
| CNC | **ARSAT** (Pecica) ~100 mașini; **Alvi Technik** (Cluj) | Serii de zeci–mii de piese | [arsat](https://www.arsat.ro/ro/industrie-prelucrare-metalica-cnc) · [alvi](https://www.alvi-technik.com/) |
| Anodizare | **Anorom** (Hunedoara) | Anodizare colorată; cere mostre-etalon pe cele 5 culori | office@anorom.ro · [site](https://anorom.ro/) |
| Oul OU (25–500 buc.) | **Capib.ro** (Bistrița), SLS PA12 | Ofertă online, serii în 1–2 săpt. | [capib](https://capib.ro/3dprint/printare-3d-sls-mjf/) |
| Oul OU (peste ~1.500 buc.) | Protolabs EU; Arna Mould, Matplast | Matrițe de injecție | [protolabs](https://www.protolabs.com/en-gb/services/injection-moulding/production/) |
| Cutia rigidă | **Web2Print** (București) | De la 25 buc., 7–20 zile lucrătoare | vanzari@web2print.ro |
| Livrare (3PL) | Fulfillment Romania | €0,29 pick & pack + livrare de la €2,29 | [clubantreprenor](https://www.clubantreprenor.ro/2026/10/11/fulfillment-pentru-magazine-online-cat-costa-si-cum-alegi-furnizorul/) |

**Atenție:** pcbpret.com e în română, dar producția e la WellPCB în Shenzhen. Se plătesc vamă și TVA la import.

**Din Asia (nu există alternativă la preț bun în RO/UE):**
- Display rotund AMOLED 1,75″ 466×466 (CO5300, QSPI): $9–17 la eșantion la Tailor-Pixels; NoseDisplay și Lianxun doar la cerere (`docs/12` §1.2). Modelul folosește $10 la 1.000 [estimare].
- ESP32-S3-WROOM-1-N16R8: ~$3,46 la 650+ buc. ([LCSC](https://www.lcsc.com/product-detail/WiFi-Modules_Espressif-Systems-ESP32-S3-WROOM-1-N16R8_C2913202.html)).
- LiPo 603040 750 mAh: ~$1,5 la 1.000 buc. [estimare]; listare A&S Power (HKTDC) [neverificat]. Cere certificatul UN38.3 și IEC 62133.
- Sticlă 2.5D: $0,20–8/buc. la MOQ 100 [listări vechi]. Alternativă UE: Mirit Glas (Danemarca), fără preț public.
- Benchmark: JLCPCB PCBA = setup $8–51 + $0,0016/punct de lipire ([jlcpcb](https://jlcpcb.com/help/article/pcb-assembly-price)). PCBWay face și box build complet.

Niciun furnizor din RO sau UE nu publică prețuri pentru CNC, PCBA sau box build. Trebuie cerere de ofertă (RFQ) cu STEP, Gerber, BOM și cantități.

## 6. Spațiu, oameni, autorizații

**Spațiu:**
- Hale mici în Ilfov (publi24, 10–15.10.2026): 3,5–8,5 €/m²/lună. Exemple: Clinceni 200 m² €1.700, Bragadiru 350 m² €2.000, Popești-Leordeni 300 m² €2.420, Pantelimon 480 m² €2.180. Nu scrie dacă e cu TVA.
- Modelul folosește 6 €/m² + 0,7 €/m² servicii.
- Ia o hală care are deja destinație industrială. Altfel îți trebuie autorizație de construire pentru schimbarea destinației (Legea 50/1991).

**Oameni (lei/lună):**
- Salariul minim: 4.325 lei brut din 1.07.2026 (HG 146/2026).
- Operator asamblare: ~4.500 lei brut (anunțurile dau 4.050–4.800).
- Tehnician electronist: 5.300–7.700 lei brut.
- Inspector QC: 4.050–7.763 lei.
- Operator CNC: ~4.000–7.000 lei net [neverificat].
- Programator CNC/CAM: ~10–11k lei brut [estimare]. E un profil rar.
- Angajatorul plătește în plus CAM 2,25%.

**Autorizații: lista exactă și cine le dă:**

| Ce | Cine | Cât / când | Pentru ce variantă |
|---|---|---|---|
| Punct de lucru, CAEN 2640, cu declarație pe propria răspundere (Legea 359/2004, art. 15) | ONRC | taxe ONRC | B, C, D |
| Actualizare CAEN Rev.3: termen 25.09.2026, poate prelungit la 1.04.2027 (HG 788/2026) | ONRC | [neverificat] | toate |
| Autorizație de mediu pentru asamblare (2640): **neclar dacă trebuie**. Lista e în coduri CAEN vechi | APM Ilfov / APM București | **întreabă în scris** | B |
| Autorizație de mediu pentru SMT propriu (2611/2612), CNC (2562), anodizare (2561) | APM | 500–1.500 lei emitere [de confirmat] + viză anuală 100 lei (Ord. 1150/2020); până la ~90 zile lucrătoare | C, D |
| ISU: aviz sau autorizație doar peste 600 m² (HG 571/2016) | ISU București-Ilfov | Sub 600 m²: instruire, stingătoare, dosar PSI (Legea 307/2006) | B, C, D |
| Depozitare baterii Li-ion: dulap ignifug. Cifrele P118/1-2025 (20 m², 1,8 m, 60% SoC) | ISU | [neverificat] | B, C, D |
| REGES-ONLINE, înainte de primul contract de muncă | ITM | amendă 15–20k lei dacă lipsește (anunț 2025) | B, C, D |
| SSM + PSI externalizat | firmă SSM | 120 lei/lună (1–5 angajați), 450 lei/post, 500 lei dosar PSI ([zotas](https://zotas.ro/ghiduri/cat-costa-ssm-firma-mica/)) | B, C, D |
| Medicina muncii | clinică | ~50–100 lei/om/an | B, C, D |
| Registrul producătorilor de EEE (Ord. 269/2019) + registrul de baterii | autoritatea de mediu (după research: ANMAP) | 500 lei | **toate** (ești producător chiar dacă externalizezi) |
| Contract cu un OIREP (organizație de responsabilitate extinsă) + declarații la AFM | OIREP, AFM | după cantități | toate |
| Transport aerian: UN3481 / PI 967 (baterie în aparat). ≤30% SoC recomandat. UN38.3 test summary obligatoriu | curier | – | toate |
| CE / RED | per **produs**, nu per fabrică (vezi `docs/04-COMPLIANCE.md`) | – | toate |
| Anodizare în casă: autorizație integrată doar peste 30 m³ de băi (Dir. 2010/75/UE). Plus mediu, Apele Române, NTPA-002 (pH 6,5–8,5, Ni 1,0 mg/L) | APM, Apele Române, operatorul de canalizare | [de confirmat] | nu o facem |

**Cheltuieli lunare pentru un atelier T0 de ~200 m² cu 2 operatori și 1 tehnician [estimare]:** ~€4,6–5k/lună. Chiria ~€1.000 + TVA, salariile ~15,9k lei, SSM, utilități și asigurare ~€0,5–0,8k. Capacitate ~5–6k buc./an.

## 7. Bani pentru fabrică

**Pe scurt: azi nu există niciun grant verificat care să plătească celula CNC (~€104k) sau linia SMT (~€36k).**

| Sursă | Ce plătește | Când | Pentru fabrică? |
|---|---|---|---|
| **PR BI PoC 1.1** (€50–200k, de minimis) | Cercetare, TRL 3 → 5 | Depunere realist dec. 2026 – feb. 2027 | **Nu.** Poate intra echipament mic de test (jig, stație de flash) dacă ghidul final îl permite [de confirmat] |
| **PR BI 1.2** (media ~€1M, GBER art. 25 + 28) | Produse noi până la TRL 7/8: pilot, pre-CE | Realist T2–T3 2027 [estimare] | **Nu linie de producție.** Echipamentele intră de obicei doar ca amortizare pe durata proiectului [dedus; ghidul nu e publicat] |
| PR BI 9.1 STEP | neclar | T1–T2 2027 | Neclar |
| Start-Up Nation 2026 | – | – | ARTEMIS **nu e eligibilă** |
| PoCIDIF (ajutor regional) | investiții | închis; ar cere punct de lucru în Ilfov | Poate, la o rundă nouă [neverificat] |
| IMM Plus (credit garantat) | credit | – | Notat în vault ca nepotrivit acum |
| Leasing / credit bancar pentru CNC | mașina | oricând | **N-am oferte.** Cere de la 2–3 firme de leasing doar când T1 devine real |

Detalii: [[Finanțare — toate sursele pentru SOUL]].

## 8. Plan pe etape

| Când | Ce faci | Legătura cu banii |
|---|---|---|
| **oct.–dec. 2026** | Pornești P0 pe placă. Trimiți un singur pachet RFQ (STEP, BOM, specificația de test, cantități 25 / 250 / 1.000 / 10.000) la Felix EMS, EMS-Electra, ICCO, Epsicom, PCBWay; ARSAT, Alvi, JLCCNC, Anorom; Mirit, Felix Glass; Web2Print. Faci simularea CAM pe STEP pentru timpul de ciclu. Întrebi APM în scris despre CAEN 2640. | Dosarul PoC 1.1 |
| **dec. 2026 – feb. 2027** | Depui PoC 1.1. Comanzi mostrele-etalon de anodizare pe 5 culori. | Depunere PoC 1.1 |
| **2027 S1** | Dacă PoC e aprobat: prototipuri din aluminiu făcute afară, jig de test DIY, primul PCB custom (Eurocircuits / Aisler / JLCPCB). **Nu fabrică.** | PoC 1.1 = cercetare |
| **T2–T3 2027** | Depui PR BI 1.2: pilotul de 25, pre-CE, IP. Pilotul de 25 îl asamblezi tu. Începe CE/RED. | PR BI 1.2 |
| **2027 S2 – 2028 S1** | Primele sute de bucăți. Decizi între atelier T0 și box build la EMS, după oferte (pragul: ~16,5 €/buc. la 1.000). Dacă alegi T0: punct de lucru, 40–60 m², 1 operator. | Venituri + 1.2 |
| **2028** | Doar dacă vinzi sigur peste ~5–10k/an: reevaluezi CNC-ul propriu cu oferte reale și leasing. SMT doar peste ~20k plăci/an. La 10k+, dosarul de fabricație trece pe ambutisare 5052 + CNC de finisare. | Leasing / credit / investitori |

## 9. Riscuri

- **Prețurile-cheie sunt estimări:** box build și PCBA la EMS din România, carcasa CNC livrată, timpul de ciclu CNC. Rezultatele se pot inversa după RFQ. O diferență de ±2 € pe carcasă schimbă break-even-ul CNC.
- **Culoarea la anodizare:** 5 culori, iar portocaliul și șampania sunt sensibile la proces. Mostre-etalon și o singură baie pe culoare.
- **Volumul e nesigur.** O mașină CNC de ~€100k care stă e cea mai scumpă greșeală posibilă.
- **Oamenii:** un programator CNC/CAM e greu de găsit. Dacă pleacă, se oprește tot.
- **Bateriile:** stocul de Li-ion cere dulap ignifug și reguli de transport (SoC, UN38.3).
- **Autorizații:** autorizația de mediu pentru asamblare e neclară. CNC-ul și SMT-ul cer sigur una. Poate dura până la ~90 de zile lucrătoare.
- **Dependența de Asia:** display AMOLED (deocamdată un singur furnizor calificat), modul, celulă, sticlă. Cam 30–45% din valoarea BOM-ului [estimare].
- **Banii:** niciun grant nu plătește azi utilaje de producție. T1 și T2 ar fi pe credit, leasing sau investitori.
- **Furnizori mari:** sub ~5–10k/an, un client mic e prioritate mică la Cicor, HELBAKO sau Kimball.

## 10. Surse

Accesate pe 15.10.2026, dacă nu scrie altfel.
- Modelul: `micul-smecher/docs/factory/SOUL-fabrica-model.xlsx` (toate ipotezele, cu sursă sau [estimare]).
- Dosare interne: `micul-smecher/docs/01-BOM.md`, `02-MANUFACTURING.md`, `04-COMPLIANCE.md`, `06-SUPPLIERS.md`; [[Finanțare — oferte de preț pentru PoC 1.1]]; [[Planul de bani Micul Șmecher]].
- CNC: [Haas VF-2](https://machinetoolindex.com/machines/haas-vf-2) · [Haas Mini Mill](https://machinetoolindex.com/machines/haas-mini-mill) · [Brother Speedio](https://machinetoolindex.com/machines/brother-speedio-s500xd2) · [Tormach](https://tormach.com/machines/mills/1100mx.html) · [Haas second-hand](https://www.machineseeker.com/mss/haas+vf+2) · [Hurco Surplex RO](https://www.surplex.com/ro/m/centru-de-prelucrare-vertical-hurco-vmx24-782504.html) · [Haas DT-1](https://www.machinio.com/models/haas/dt-1) · [aluminiu Baduc](https://www.baduc.ro/metalurgice/4113-bara-rotunda-aluminiu--=-60-mm) · [timpi 6061](https://precisionsmith.com/capabilities/aluminum-6061-machining/)
- SMT: [YY1](https://www.esdshop.eu/Neoden-YY1/) · [NeoDen4](https://www.neodentech.eu/contents/en-uk/d8_NEODEN4.html) · [IN6](https://neoden-solution.com/collections/reflow-ovens/products/neoden-in6-reflow-oven) · [Juki](https://www.machinio.com/cat/juki-pick-&-place-machines) · [JLCPCB](https://jlcpcb.com/help/article/pcb-assembly-price)
- Anodizare: [Dir. 2010/75/UE Anexa I](https://legislation.gov.uk/eudr/2010/75/annex/I/2020-01-31) · [NTPA-002](https://lege5.ro/Gratuit/gqydqnzx/normativul-ntpa-002-privind-conditiile-de-evacuare-a-apelor-uzate-in-retelele-de-canalizare-ale-localitatilor-si-direct-in-statiile-de-epurare-din-28022002) · [PFonline 2009](https://www.pfonline.com/articles/adding-anodizing) · [lista CAEN mediu](https://www.specialist-mediu.ro/cand-este-necesara-autorizatia-de-mediu/)
- Parteneri: [Felix EMS](https://www.felix-ems.ro/index_ro.html) · [EMS-Electra](https://www.ems-electra.ro/en/services/electronic-manufacturing) · [ICCO EMT](https://iccoemt.ro/en/) · [Epsicom](https://epsicom.ro/) · [EBS](https://ebs-electric.eu/en/electronic-manufacturing-and-assembly-ems/) · [HELBAKO](https://helbako.com/en/your-production-partner/contract-manufacturing/) · [Cicor Arad](https://www.cicor.com/en/locations/europe/romania/arad/) · [Elemaster](https://www.elemaster.com/en/locations/elemaster-romania-en/) · [pcbpret = WellPCB](https://pcbpret.com/servicii/asamblare-pcb/) · [ARSAT](https://www.arsat.ro/ro/industrie-prelucrare-metalica-cnc) · [Alvi](https://www.alvi-technik.com/) · [Anorom](https://anorom.ro/) · [Mirit Glas](https://miritglas.com/en/) · [Capib](https://capib.ro/3dprint/printare-3d-sls-mjf/) · [Protolabs](https://www.protolabs.com/en-gb/services/injection-moulding/production/) · [Web2Print](https://web2print.ro/cutii-personalizate/) · [PCBWay box build](https://www.pcbway.com/oem/electronics-manufacturing.html)
- Spațiu și oameni: [hală Berceni](https://www.proprietati-industriale.ro/hale-spatii-depozitare-de-inchiriat/hala-berceni) · publi24 Ilfov (10–15.10.2026) · [operator CNC](https://ro.jooble.org/locuri-de-munca-operator+cnc/Bucure%C5%9Fti) · [SSM](https://zotas.ro/ghiduri/cat-costa-ssm-firma-mica/)
- T0: [Fixturfab](https://fixturfab.com/fixtures) · [Düperthal](https://www.lion-care.com/en/Dueperthal-BATTERY-standard-line-XL-storage-cabinet/DUPSHSBLSXL1) · [Gweike](https://shop.gweikecloud.com/products/g6-mopa-30w-60w-100w-fiber-laser-marking-engraving-machine) · [Nordson](https://esd.equipment/en/wl21683.html) · [Espressif Flash Tool](https://docs.espressif.com/projects/esp-test-tools/en/latest/esp8266/production_stage/tools/flash_download_tool.html)
