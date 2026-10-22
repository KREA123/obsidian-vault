---
tip: finanțare
afacere: Micul Șmecher
actualizat: 2026-10-22
---

# Oferte de preț pentru PoC 1.1 (fiecare linie de buget)

> Dosarul: [[Finanțare — PR BI PoC 1.1 pentru SOUL]] · expertul: [[Finanțare — expertul științific pentru PoC 1.1]] · pași: [[De continuat — SOUL]] · harta: [[SOUL — Harta memoriei]].
> Prețuri citite pe paginile publice pe **12.10.2026**. Nu am contactat pe nimeni și nu am trimis niciun formular.
> **[neverificat]** = pagina ne-a blocat sau prețul nu s-a putut confirma. Faci tu printscreen manual.
> **Actualizare 2026-10-22 — produsul e mărimea S** (decizia din 20.10.2026, `micul-smecher/docs/size-s.json`, `docs/12-SIZE-S.md`): ~63 × 70,8 × 23 mm, sticlă plată Ø52, AMOLED rotund 1,75″ 466×466 (CO5300, QSPI), baterie LiPo 750 mAh (603040). Liniile L11, CNC (§4.3), PCBA (§4.4) și laboratorul (§4.5) cer acum piese și oferte pentru S. Placa 2.8C, panourile 2,8″ și celulele 1500 mAh rămân doar pentru **prototipul M** (dovada TRL 3, din bani proprii, în afara bugetului).
> Cursuri folosite doar pentru estimare: 1 € ≈ 5,10 lei ≈ 4,25 PLN; 1 $ ≈ 0,87 €; 1 CHF ≈ 1,07 €. În MySMIS se folosește cursul InforEuro din ghid.

## 1. Pe scurt

**Câte oferte:** minim **2 surse pentru FIECARE linie de buget**, chiar și cele mici. Textul din 29.09.2026 a scos cuvântul „semnificativă”.

> „Centralizator justificare costuri (Anexă obligatorie) – min. 2 surse pentru fiecare linie bugetară, cu excepția situațiilor temeinic justificate [...] • Oferte de preț, printscreen-uri website, cataloage, devize estimative, etc. – ca surse justificative” — Decizia CM 54/29.09.2026, p.56 (criteriul 2.2)

- **Forma:** oferte, cataloage, site-uri, printscreen-uri. Un printscreen contează **doar dacă arată linkul activ (URL)** (d54 p.58).
- **Comparabile:** cele 2 surse trebuie să aibă **aceleași specificații tehnice**, cele din Planul de afaceri (Anexa 3). Altfel linia pică (d54 p.58).
- **Punctaj 2.2b (4 p):** toate liniile cu 2 surse = 4 p. O linie fără = 2 p. Mai multe = 0 p.
- **O singură sursă** se acceptă doar cu notă justificativă și dovezi (furnizor unic, titular de drept unic). Se potrivește la taxele EUIPO (d54 p.58; Ghid p.67).
- **Fără oferte:** salariile (L1–L4, L25) și costurile indirecte de 7 % (L28).
- **Se depune:** Centralizatorul în formatul **Anexa 19** + sursele atașate (Ghid p.70). Anexa 19 nu e în folderul `apel/`. Trebuie descărcată.
- Ofertele în altă limbă se acceptă cu traducere simplă (Ghid p.66). Nu există o vechime maximă pentru oferte. Recomand totuși: datate, pe numele ARTEMIS, valabile ≥ 90 de zile.

**Regula de aur: ceri oferte, NU comanzi, NU semnezi, NU plătești nimic înainte de depunere.**
- Altfel se pierde efectul stimulativ și proiectul e neeligibil (d54 p.21; Ghid p.43).
- Excepții permise: consultanța pentru cerere (L24, inclusiv expertul) și managementul de proiect.
- La ofertele instant online: încarci fișierul, salvezi oferta. **Nu apeși „Order”, „Checkout”, „Pay”.**

**TVA:** ARTEMIS **nu e plătitor de TVA**. TVA-ul e un cost real și e eligibil (proiect sub 5 mil. €). Toate sumele din buget sunt **cu TVA**.
- Furnizor din RO: plătești TVA RO 21 %. Cel mai simplu.
- Furnizor din UE: îți pune TVA-ul țării lui (19 % DE, 23 % PL). Peste 10.000 €/an achiziții din UE trebuie cod special de TVA (art. 317 Cod fiscal) și plătești TVA RO. **De confirmat cu contabilul.**
- Furnizor din China: taxă vamală ~6 % + TVA de import 21 %. Ceri preț **DAP/DDP București**.
- Cere mereu: **preț fără TVA + TVA, separat**.

**Bugetul din dosar, aliniat la prețurile găsite (12.10.2026): 191.240 € total eligibil** (înainte: 191.308 €).
- am schimbat 7 linii unde avem prețuri verificate (L5, L6, L7, L14, L19, L21, L23) și am scăzut L17 ca să compensez;
- restul liniilor rămân la cifra din dosar, pentru că încă nu au preț (CNC, PCBA, laboratoare, audit etc.);
- sursa unică e `micul-smecher/investors/poc-1.1/dosar/draft/_build/data.py` (subtotalurile se calculează automat); tabelul complet e în `dosar/03-NUCLEU-PROIECT.md` §10.

| Categorie (cu TVA) | Dosar vechi | Dosar nou | De ce |
|---|---:|---:|---|
| Salarii CDI L1–L4 (fără oferte) | 99.387 € | 99.387 € | neschimbat |
| Echipamente L5–L10 | 15.488 € | **13.249 €** | osciloscop 1.004, analizor spectru 2.952, Joulescope JS320 1.065; PC, cutie RF și SLA neschimbate (fără surse complete) |
| Materiale L11 | 4.507 € | 4.507 € | sub-articolele cu preț găsit fac ≈ 1.200 €; rămâne loc pentru panouri, rășină, componente |
| Prototipare L12 CNC + L13 PCBA | 10.346 € | 10.346 € | **niciun preț încă** (doar ofertă după STEP/Gerber) |
| Testare și R&D L14–L16 | 13.310 € | **16.940 €** | L14 = 8.470 (7.000 + TVA): EMC la ZUT (PL) ≈ 4.610 € net pe 2 sesiuni + radio EN 300 328 ≈ 2.390 € net [E], fără preț public |
| Workshop-uri L17 | 2.500 € | **1.500 €** | redusă ca să compenseze L14/L23: e linia cea mai slab justificată (doar sala are preț, ≈ 250–300 € pe 2 zile) |
| SaaS L18 | 5.000 € | 5.000 € | prețuri unitare găsite; totalul depinde de consum |
| PI L19–L20 | 3.502 € | **3.037 €** | EUIPO real: 1.050 (marcă, 3 clase) + 475 (2 designuri) = 1.525 € |
| Diseminare L21–L23 | 7.788 € | **7.799 €** | APC Frontiers 2.842; focus grupuri 2.057 (2 × 850 + TVA) |
| II.2–II.5 L24–L27 (plafon 10 %) | 16.964 € | 16.964 € | 8,9 % din total, sub plafon (19.124 €) |
| **Costuri directe** | 178.793 € | **178.729 €** | (suma veche a liniilor era de fapt 178.792) |
| Indirecte 7 % (fără oferte) | 12.515 € | **12.511 €** | |
| **TOTAL ELIGIBIL** | **191.308 €** | **191.240 €** | sub 200.000 € (rezervă de curs ~4,4 %); activitatea de bază 153.966 € = 80,5 % (min. 50 %) |

**Cele 4 corecturi sunt aplicate în dosar (12.10.2026):**
1. **L19 EUIPO:** 1.525 € (marcă 3 clase 1.050 + 2 designuri 475), nu 1.990 €.
2. **L14 EMC/radio:** 8.470 € (7.000 + TVA) în loc de 4.840 €. Partea radio EN 300 328 e încă [E]: cere ofertele de la PIT, cetecom, NMi.
3. **L7:** Anexa 3 scrie „Joulescope JS320 sau echivalent” (JS220 nu se mai fabrică).
4. **L5:** Anexa 3 scrie „decodare I²S de dorit, nu obligatorie”.

## 2. Furnizorii pe fiecare linie

Legendă: ✔ = verificat pe pagină · ✎ = corectat la verificare · **[neverificat]** = de confirmat manual · ✘ = nu folosi ca sursă.

### Echipamente (active corporale)

| Linie | Furnizor | Preț | Termen | Link | Cum ceri oferta |
|---|---|---|---|---|---|
| L5 Osciloscop | ✔ RIGOL EU (rigolshop.eu), DE | Rigol DHO924S 719 € net / 855,61 € cu TVA DE | în stoc, 2–3 zile | https://rigolshop.eu/dho924s.html | info@rigolshop.eu |
| L5 | ✔ aparate-masura-control.ro (RONEXPRIM SRL), RO | DHO924S 5.102 lei cu TVA | la cerere | https://www.aparate-masura-control.ro/ro/1/16/1637_rigol-dho924s--osciloscop-digital--250-mhz--4-canale-analogice--1-25-gsa-s-rigol-dho924s.php | formularul de pe site |
| L5 (alt model) | ✔ T&M eVision, DE | Siglent SDS1204X-E 659 € net / 768 € cu TVA (nu are I2S) | în stoc | https://evision-webshop.eu/siglent/sds1204x-e-oscilloscope | info@evision-instruments.com |
| L6 Analizor spectru | ✔ Welectron, DE | Siglent SSA3032X Plus 2.902 € cu TVA DE (2.439 net), cu tracking generator | la cerere | https://www.welectron.com/Siglent-SSA3032X-Plus-Spectrum-Analyzer | formularul de contact |
| L6 | ✔ Batronix, DE | același model 2.902,41 € cu TVA DE | în stoc | https://www.batronix.com/shop/spectrum-analyzer/Siglent-SSA3032X-plus.html | service@batronix.com |
| L6 (a 3-a) | ✔ Batronix, DE | Rigol RSA3030N 3.912,47 € (TG neconfirmat) | în stoc | https://www.batronix.com/shop/spectrum-analyzer/Rigol-RSA3030N.html | service@batronix.com |
| L7 Analizor consum | ✔ Joulescope (Jetperch), US | JS320-K000 $999 net; calibrat K001 $1.399 | livrare | https://www.joulescope.com/products/js320 | pagina Contact / Distributors |
| L7 | ✔ Welectron, DE | JS320 1.045 € cu TVA DE (878 net) | 10+ în stoc | https://www.welectron.com/Jetperch-JS320-Precision-DC-Energy-Analyzer | formularul de contact |
| L8 Cutie ecranată RF | ✎ Ramsey, prin R.A. Mayes, US | STE2200M $475 (încape aparatul); STE2300M $795; opțiuni USB/SMA separat | la cerere | https://www.ramayes.com/RF_Shielded_Test_Enclosures.htm | „Request Quote” pe https://rfshieldbox.com/product/ste2300-rf-shielded-test-enclosure/ |
| L8 | ✔ Ranatec, SE | la cerere | – | https://ranatec.com/product-category/rf-shield-box/ | info@ranatec.com (cere model de banc + izolația la 6 GHz) |
| L8 | ✔ Orbis Systems, FI | la cerere | – | https://www.orbissystems.eu/shop/rf-shield-box-1/ | formularul de ofertă (cere dB la 2,4/5/6 GHz) |
| L9 Stație PC | **fără surse** | – | – | – | de căutat (ex. 2 magazine IT din RO, aceeași configurație) |
| L10 Imprimantă SLA | **fără surse** | – | – | – | de căutat (Formlabs Form 4 vs Elegoo/Anycubic, specificații comparabile) |

### Materiale (L11, câte 2 surse pe fiecare sub-articol)

| Sub-articol | Furnizor | Preț | Termen | Link | Cum ceri oferta |
|---|---|---|---|---|---|
| **L11a Placa AMOLED-1.75 (8 buc), SOUL S** | ✔ Waveshare, CN (verificat 20.10.2026, docs/12 §1.1) | $29,99–39,99 (split pe variante nepublicat) | „Add to Cart”, din CN | https://www.waveshare.com/esp32-s3-touch-amoled-1.75.htm | sales@waveshare.com |
| L11a | ✔ The Pi Hut, UK (verificat 20.10.2026) | £28,80 cu TVA (Standard) | **epuizat** | https://thepihut.com/products/esp32-s3-1-75-amoled-round-touch-display-dev-board-466x466 | contactul de pe site |
| L11a | openelab, EU **[neverificat]** | -B 39,85 € | epuizat | https://openelab.io/a/s/products/waveshare-esp32-s3-1-75inch-amoled-round-touch-display-with-case | info@openelab.io |
| L11a-M Placa 2.8C (prototipul M; din bani proprii, în afara bugetului) | ✔ Waveshare, CN | $39,99 net (cu touch, SKU 29086; de confirmat) | din CN | https://www.waveshare.com/esp32-s3-touch-lcd-2.8c.htm | sales@waveshare.com |
| L11a | ✔ Kamami, PL | 192,57 PLN cu TVA (156,56 net) | stoc contradictoriu, întreabă | https://kamami.pl/en/esp32/1197479-esp32-s3-2-8inch-round-display-development-board-480-480-32-bit-lx7-dual-core-processor-supports-5902186321694.html | sprzedaz@kamami.pl |
| L11a | ✎ OpenELAB Technology Ltd. (depozit München) | **47,25 € cu TVA** → 8 buc = 378 € | în stoc | https://openelab.io/products/waveshare-esp32-s3-round-display-2-8inch | info@openelab.io |
| L11a | Sigmanortec, RO **[neverificat]** | 386,10 lei (din căutare), fără stoc | – | https://sigmanortec.ro/en/waveshare-esp32-s3-development-board-capacitive-touch-round-ips-lcd-28-inch-480x480-wifi-and-bluetooth | formularul de contact |
| **L11b Panouri AMOLED 1,75″ 466×466 goale (20 buc), SOUL S** | ✔ Tailor-Pixels TOH175XRT-02CG (docs/12 §1.2) | $9–17, MOQ nedeclarat | la cerere | https://tailorpixels.com/product/1-75-inch-amoled-round-on-cell-touch-466x466-mipi-qspi/ | RFQ: CO5300, QSPI, touch on-cell, desenul FPC |
| L11b | NoseDisplay ND018ECG466466-A02 **[neverificat]** (CO5300 + CST9217, perechea Waveshare) | la cerere | – | https://www.nosedisplay.com/products/amoled-1-75-inch-round-display-466x466-resolution-700nits-qspi-interface/ | aceeași specificație |
| L11b | Lianxun LX175A3101CTP01 **[neverificat]** | la cerere | – | https://www.lxdisplay.com/Product_details/1349774513965064192.html | aceeași specificație |
| L11b-M Panouri 2,8″ (doar prototipul M, nu intră în buget) | ✔ Shenzhen Zhuohong, CN | $8–10, **fără touch** | răspuns RFQ ~12 h | https://www.tft-displaylcd.com/sale-53843821-2-8-inch-ips-round-lcd-display-480x480-with-st7701s-driver-ic.html | „Request A Quote”: ST7701S RGB18 + CTP GT911 |
| L11b | ✔ Twoyas, CN | $11,50, **fără touch** | în stoc | https://www.twoyas.com/products/2-8-inch-round-tft-lcd-module-screen-480-480-rgb-ic-st7701s | formularul: aceeași specificație |
| L11b | ✘ BuyDisplay ER-TFT028-2 | MIPI, nu RGB: incompatibil | – | – | nu folosi |
| L11c Microfon INMP441 (25) | ✔ ArduShop, RO | 25,64 lei cu TVA | stoc mic, întreabă de 25 | https://ardushop.ro/en/modules/1944-omnidirectional-microphone-module-i2s-interface-inmp441-mems-high-precision-low-power-ultra-small-volume-for-esp32-6427854029614.html | office@ardushop.ro |
| L11c | ✔ Bitmi, RO | 20,99 lei cu TVA | în stoc | https://www.bitmi.ro/electronica/modul-microfon-omnidirectional-interfata-i2s-mems-inmp441-11003.html | vanzari@bitmi.ro |
| L11c Amplificator MAX98357A (25) | ✔ Robofun, RO (Adafruit) | 44,18 lei cu TVA | fără stoc acum | https://www.robofun.ro/module/amplificator-3w-i2s-max98357a.html | info@robofun.ro |
| L11c | ✘ Optimus Digital | link mort (404) | – | – | **lipsește a 2-a sursă** |
| L11c Difuzor 20×30 8 Ω (25) | ✔ Drot, RO | 6,61 lei cu TVA | în stoc | https://www.drot.ro/platforma-arduino/121355-difuzor-1w-8-ohm-20-x-30-mm.html | info@drot.ro |
| L11c | ✔ electronicmarket.ro, RO | 5,06 lei cu TVA | fără stoc | https://electronicmarket.ro/mini-difuzor-1w-8ohm-20x30mm | contactul de pe site |
| L11c | ✔ Eckstein, DE | 2,65 € cu TVA (2 W, cu cavitate) | în stoc | https://eckstein-shop.de/Waveshare-2030-8ohm-2w-cavity-speaker-en | formularul de contact |
| **L11d LiPo 603040, 750 mAh (30), SOUL S** | A&S Power (HKTDC) **[neverificat: listare, nu ofertă]** | – | – | https://www.hktdc.com/event/hkelectronicsfairae/en/product/1X24UT0L | RFQ: 6,2 × 30,5 × 42 mm, PCM, MX1.25 |
| L11d | eBay.de, clasa 603040 (800 mAh) **[neverificat]** | – | – | căutare „603040 lipo” | – |
| L11d-M LiPo 803450 (prototipul M, în afara bugetului) | ✔ Conex Electronic, RO | 52 lei cu TVA (Akyga) | în stoc | https://www.conexelectronic.ro/cumpara/acumulator-li-po-3-7v-1500mah-aky-lp803450-16115 | contact@conexelectronic.ro |
| L11d | ✔ AMPUL SYSTEM, CZ | 8,28 € net (3 fire, protecție) | la furnizor | https://ampul.eu/en/battery/5249-li-pol-battery-1500mah-37v-803450-3-wires | info@ampul.eu |
| L11d | eMAG (Liter Energy) **[neverificat]** | 50,84 lei (din căutare) | – | https://www.emag.ro/acumulator-li-polymer-1500mah-3-7v-ntc-jst-803450-216/pd/DC94SSMBM/ | mesaj către vânzător |
| L11e Inserții M2 | ✔ ruthex, DE | 8,99 € / 70 buc | în stoc | https://www.ruthex.de/en/products/ruthex-gewindeeinsatz-m2-70-stuck-rx-m2x4-messing-gewindebuchsen | contactul de pe site |
| L11e | ✔ 3DPrima | 8,99 € / 70 buc | în stoc | https://www.3dprima.com/spare-parts-accessories/others/post-processing/ruthex-m2-threaded-insert-rx-m2x4-70-pcs_30171_12598 | contactul de pe site |
| L11e Magneți Ø6×2 | ✔ supermagnete, DE | N45: 0,26 €/buc la 40 (cu TVA) | 1–3 zile | https://www.supermagnete.de/eng/disc-magnets-neodymium/disc-magnet-diameter-6mm-height-2mm-neodymium-n45-nickel-plated_S-06-02-N | support@supermagnete.com |
| L11e Modul TP4056 USB-C | ✔ Bitmi, RO | 3,99 lei | în stoc | https://www.bitmi.ro/electronica/modul-tp4056-cu-usb-tipc-incarcare-acumulatori-litiu-5v-1a-10446.html | vanzari@bitmi.ro |
| L11e Coș pasive/conectori | TME, RO **[neverificat]** | ofertă pe coș | – | https://www.tme.eu/ro/ | cerere de ofertă din coș/BOM |
| L11e | Mouser **[neverificat]** | ofertă pe coș | – | https://ro.mouser.com/ | „Request a Quote” (max. 99 linii); a 3-a: Farnell https://www.farnell.com/equotes |
| L11g Ciocan de lipit | ✔ Botland, PL | Pinecil V2 39,90 € | disponibil | https://botland.store/soldering-irons/25835-pinecil-v2-smart-portable-mini-soldering-iron-oled-risc-v-pine64--850796007840.html (redirecționează) | office@botland.store |
| L11g | ✔ IQ Electric, RO | TS101 65 W 335 lei cu TVA | – | https://www.iqelectric.ro/echipamente-de-laborator/letcon-portabil-ts101-cu-alimentare-type-c-24v-3a.html | contactul de pe site |
| L11f Rășină, consumabile | **fără surse** | – | – | – | de căutat |

### Prototipare (L12 CNC, L13 PCB)

| Linie | Furnizor | Preț | Termen | Link | Cum ceri oferta |
|---|---|---|---|---|---|
| L12 CNC + anodizare | ✔ Weerg, IT | ofertă instant după STEP | expediere ~3 zile | https://www.weerg.com/en/ | cont + date firmă salvate → „Download” ofertă PDF; 6082 (nu 6061), culori: roșu, albastru, negru, verde, natur, auriu |
| L12 | ✔ Hubs (Protolabs Network), NL | ofertă instant | – | https://www.hubs.com/instant-quotes/ | ofertă PDF / „share quote”; preț blocat 30 de zile; **nu plăti** |
| L12 | ✔ PCBWay CNC, CN | ofertă instant | 1–2 zile + transport | https://www.pcbway.com/rapid-prototyping/CNC-machining/ | ofertă online + email 3dcnc@pcbway.com pentru culori și marcare |
| L12 | ✔ JLCCNC, CN | ofertă instant | ~3 zile + transport | https://jlccnc.com/cnc-machining-quote | ofertă formală prin https://jlccnc.com/help/contact/CNC%20Inquiry |
| L12 | ✔ RapidDirect, CN | ofertă instant | ~5 zile | https://app.rapiddirect.com | prin vânzări |
| L12 (RO) | ✔ Alvi Technik, Cluj | la cerere (CNC + sablare + eloxare) | – | https://www.alvi-technik.com/ | office@alvi-technik.com sau formularul |
| L12 (RO) | ✔ ARSAT Industrie, Arad | la cerere (anodizare prin parteneri, marcare laser) | – | https://www.arsat.ro/ro/contact | formularul de contact |
| L12 (doar anodizare) | ✔ Anorom, Hunedoara | la cerere | – | https://anorom.com/cere-oferta/ | office@anorom.ro |
| L12 | Xometry Europe, DE **[neverificat]** | ofertă instant | – | https://xometry.eu/en/cnc-milling/ | info@xometry.eu |
| L12 | ✘ Protolabs (in-house) | același grup cu Hubs | – | – | nu-l pune pereche cu Hubs |
| L13 PCB + PCBA | ✔ JLCPCB, CN | tabel de taxe: setup $51,12 două fețe, stencil $16,42, $0,0016/punct (nu e ofertă) | – | https://jlcpcb.com/help/article/pcb-assembly-price | ofertă instant cu Gerber + BOM + CPL → salvezi PDF |
| L13 | ✔ PCBWay, CN | „PCBA $29 pentru 20 buc” (doar manoperă) | 3–5 zile | https://www.pcbway.com/pcb-assembly.html | service@pcbway.com |
| L13 | ✔ Eurocircuits, BE | calculator (cu cont) | 6 zile lucrătoare | https://www.eurocircuits.com/services/pcb-proto/ | calculatorul online |
| L13 | ✎ AISLER, NL/DE | 4 straturi: 14 € + 0,13 €/cm² pe placă, min. 3 buc; stencil 5 € + 0,095 €/cm² | – | https://community.aisler.net/t/our-simple-pricing/102 | support@aisler.net |
| L13 (RO) | ✔ Circuite Imprimate (Binar Holding) | la cerere | – | https://circuite-imprimate.ro/servicii/asamblare-pcb | contact@circuite-imprimate.ro |
| L13 (RO) | ✔ SADELEC PCB, Pașcani | la cerere | – | https://www.sadelec-pcb.com/ro/index.php | contact@sadelec-pcb.com |

Perechi independente: JLCPCB, JLCCNC și JLC3DP sunt **același grup**. Hubs și Protolabs la fel. FabLab, debitarelaser.ro și gravura.ro sunt **o singură firmă**.

### Piese care lipsesc din buget (GAP-uri)

| Ce | Furnizor | Preț | Link | Cum ceri |
|---|---|---|---|---|
| Mostre de culoare + marcare laser | în oferta CNC (JLCCNC, PCBWay, RapidDirect) | sub-linie în oferta L12 | – | le pui ca articole separate în RFQ |
| Marcare laser (local) | ✎ FabLab / Debitare Laser, Jilava | gravură de la 0,20 €/cm² (debitarelaser.ro) | https://debitarelaser.ro/servicii-preturi-debitare-gravura-laser/ | contact@debitarelaser.ro |
| Oul OU (print SLA, 15–20) | ✔ Sanel Factory, Chitila | calculator STL, prețuri cu TVA, −5 % de la 20 buc | https://sanelfactory.com/#stl-quote | după ce există STL-ul OU |
| Oul OU | ✔ 3DPrintable, București | la cerere, 24 h | https://www.3dprintable.ro/ | contact@3dprintable.ro |
| Oul OU (UE, cu vopsire) | ✔ Materialise OnSite, BE | ofertă instant | https://www.materialise.com/en/industrial/3d-printing-services/online-3d-printing | onsite@materialise.com |
| Oul OU | ✘ Capib | tabelul e „medie de piață”, nu ofertă | – | doar prin configurator |
| Lentilă PMMA (prototip) | ✔ LASER CUT București | 4,5 lei/ml (2 mm) cu TVA, min. 30 lei | https://www.lasercutbucuresti.ro/pret-debitare-si-gravura-laser/ | formularul de contact |
| Lentilă PMMA | ✔ FabLab Jilava | 7 lei/ml (2–3 mm) fără TVA, min. 100 lei | https://www.fablab.ro/index.php/preturi/prelucrare-laser/ | contact@fablab.ro |
| Lentilă sticlă călită | ✔ Mirit Glas, DK / Felix Glass, CN | la cerere | https://miritglas.com/en/contact-us/ | post@miritglas.com / formularul Felix |
| 2 unități RF de referință | ✔ Waveshare AMOLED-1.75C cu carcasă Al | $39,99–41,99 | https://www.waveshare.com/esp32-s3-touch-amoled-1.75c.htm | a 2-a sursă: Kamami sau OpenELAB |

### Servicii (L14–L27)

| Linie | Furnizor | Preț | Link | Cum ceri oferta |
|---|---|---|---|---|
| L14 EMC + radio | ✔ Łukasiewicz-PIT Poznań, PL (EMC + EN 300 328) | la cerere | https://pit.lukasiewicz.gov.pl/wp-content/uploads/2025/04/Badania-Radiowe-i-Kompatybilnosci-Elektromagnetycznej-oferta.pdf | sprzedaz@pit.lukasiewicz.gov.pl |
| L14 | ✔ cetecom advanced, DE | la cerere | https://cetecomadvanced.com/en/contact/ | mail@cetecomadvanced.com |
| L14 | ✔ NMi Testlab (fost Phoenix), DE | la cerere | https://www.nmi-testlab.de/ | „Angebot anfordern” |
| L14 | ✔ CERTeLab/EMCLab Suceava, RO (RENAR, doar EMC?) | la cerere | https://emclab.ro/services.php | contact@emclab.ro (întreabă de EN 300 328) |
| L14 (doar EMC) | ✔ ZUT Szczecin, PL | ≈ 9.800 PLN net pe sesiune (RE+CE+RI+ESD cu expert) | https://lhtwimim.zut.edu.pl/pracownia-badan-i-certyfikacji-emc/oferta-badawcza-bke-emc/ | printscreen + formularul Kontakt |
| L14 | ICMET Craiova **[neverificat]** | acreditare veche | https://www.icmet.ro/eng/lab_emc.htm | icmet@icmet.ro |
| L15 EN 18031 | ✔ cetecom advanced / ✔ Applus+ / ✔ QIMA | toate la cerere | https://www.qima.com/consumer-products/lab-testing/cybersecurity/en-18031-compliance-services | formularele de ofertă |
| L16 Antenă (R&D extern) | ✔ IMT București | la cerere | https://www.imt.ro/ | office@imt.ro |
| L16 | ✔ Ignion, ES | la cerere | https://ignion.io/contact/ | „Talk to an RF engineer” |
| L16 | UPB ETTI **[neverificat]** | la cerere | https://upb.ro/ | prin decanatul ETTI |
| L17 Sală workshop | ✎ Education Point, București | Sala D 630 lei/zi (L–V) | https://educationpoint.ro/ | office@educationpoint.ro |
| L17 | ✔ Traininguri.ro, București | 130 €/zi L–J, cafea inclusă | https://www.traininguri.ro/inchiriere-sala-cursuri/ | info@traininguri.ro |
| L18 API AI | ✔ Anthropic | Sonnet 5.5: $2 / $10 pe milion de tokeni | https://claude.com/pricing | printscreen |
| L18 | ✔ OpenAI | gpt-6.1-sol: $2 / $10 (comparabil) | https://developers.openai.com/api/docs/pricing | printscreen |
| L18 Hosting UE | ✔ Hetzner CX23 (2 vCPU, 4 GB) | 5,49 €/lună + 0,50 € IPv4, net | https://docs.hetzner.com/general/infrastructure-and-availability/price-adjustment/ | printscreen |
| L18 | ✔ Scaleway PLAY2-NANO (2 vCPU, 4 GB) | ≈ 20,10 €/lună net | https://www.scaleway.com/en/pricing/virtual-instances/ | printscreen |
| L18 CAD | ✔ Onshape Standard | $1.500/utilizator/an | https://www.onshape.com/en/pricing | printscreen |
| L18 | Autodesk Fusion **[neverificat]** | ≈ $680/an (surse terțe) | https://www.autodesk.com/products/fusion-360/overview | printscreen manual din magazinul UE |
| L19 EUIPO marcă | ✔ EUIPO | 850 + 50 + 150 = **1.050 €** (3 clase), fără TVA | https://www.euipo.europa.eu/en/trade-marks/before-applying/fees-payments | sursă unică + notă; a 2-a: Reg. (UE) 2017/1001 Anexa I pe EUR-Lex |
| L19 EUIPO design | ✔ EUIPO | 350 € primul + 125 € al doilea = **475 €** | https://www.euipo.europa.eu/en/designs/before-applying/fees-payments | a 2-a: Reg. (UE) 2024/2822 (125 € nu apare pe pagină) |
| L20 Consilier PI | ✔ Lupșa și Asociații | onorariu marcă 240 € (+40 €/clasă); design 1.000 lei | https://lupsa.ro/inregistrare-marci-uniunea-europeana/ | marci@lupsa.ro |
| L20 | ✔ OTDIP | 1.800 lei marcă UE (fără taxe oficiale) | https://otdip.ro/produs/inregistrare-marca-europeana/ | office@otdip.ro |
| L21 APC | ✔ IEEE Access | $2.160 + taxe | https://ieeeaccess.ieee.org/about/article-processing-charges/ | printscreen |
| L21 | ✔ Frontiers in Robotics and AI | CHF 2.195 | https://www.frontiersin.org/journals/robotics-and-ai/for-authors/publishing-fees | printscreen |
| L21 | ✔ JMIR Human Factors | $1.985 | https://humanfactors.jmir.org/about-journal/article-processing-fees | printscreen |
| L21 | MDPI Sensors **[neverificat]** | CHF 2.600 | https://www.mdpi.com/journal/sensors/apc | printscreen manual |
| L22 Conferință | ✔ embedded world 2027 (16–18.03.2027) | stand start-up 2.890 € până la 15.01.2027; bilete nepublicate | https://edge.sitecorecloud.io/nurnbergmes0e18-nmmultisite6e34-prod50da-6065/media/Project/NuernbergMesse/embedded-world/PDFs/embedded-en-exhibitor-brochure-ew27.pdf | printscreen când apar taxele + zbor/hotel (2 variante) |
| L23 Focus grupuri | ✔ focusgrupuri.ro | 850 €/grup; interviu 170 € | https://focusgrupuri.ro/ | formularul de contact |
| L23 | ✔ IZI Data | 1.440–1.940 €/grup | https://izidata.ro/cercetare-dedicata/ | formularul de pe pagină |
| L24 Consultanță CF | ✔ Aria United | 350 lei/oră | https://ariaunited.com/consultanta-fonduri-europene-si-consultanta-in-afaceri-tarife-servicii/ | office@ariaunited.com (cere preț fix) |
| L24 | ✔ Neotrust (pagină veche) | 5.900 lei | https://www.neotrust.ro/pret-consultanta-fonduri-europene/ | office@neotrust.ro (ofertă nouă) |
| L24 | ✔ Cash Consult | 5–8 % + comision de succes (evită) | https://cashconsult.ro/consultanta-accesare-fonduri-nerambursabile/ | contact@cashconsult.ro |
| L24 Expert științific | **fără preț** | estimare 1.500–2.500 € | [[Finanțare — expertul științific pentru PoC 1.1]] | 2 oferte cu CV |
| L26 Audit | ✔ Contello / ✔ Orior / ✔ Audit Galis / ✔ Tănasă & Partners | toate la cerere | https://contello.ro/audit/fonduri | office@contello.ro; Orior nu și la L24 |
| L27 Afiș A3, vizibilitate | **fără surse** | – | – | 2 tipografii din București |

### Ce lipsește (gap-uri)
- **Fără niciun preț:** L9 PC, L10 imprimantă SLA, L11f rășină, L12 CNC, L13 PCBA (doar tabele de taxe), L15, L16, L24 expert, L26 audit, L27 afiș.
- **O singură sursă bună:** L8 (doar Ramsey are preț), amplificatorul MAX98357A (Optimus mort), magneții, TP4056, unitățile RF de referință, CAD (Fusion neverificat).
- **L11b panouri (S):** doar Tailor-Pixels publică un interval de preț ($9–17); MOQ-ul se află prin RFQ la toți trei. (Pentru prototipul M: nimeni nu dă preț pentru 2,8″ cu touch GT911.)
- **L11c audio (S):** placa AMOLED-1.75 are deja 2 microfoane, codecurile ES7210 + ES8311 și ieșire de difuzor. Pentru PCB-ul propriu se cer microfoane MEMS și difuzoare 15 × 11 mm; INMP441 + MAX98357A de mai sus sunt pentru prototipul M.
- **L14:** partea radio EN 300 328 nu are preț nicăieri. ZUT face doar EMC.
- **L22:** taxele de conferință 2027 nu sunt publicate.
- **Oul OU:** nu există încă STL/CAD, deci nimeni nu poate da preț.
- **STEP-ul:** produsul e S (~63 × 70,8 × 23 mm). STEP-ul de producție S la 23 mm **nu există încă** (`docs/12` §3.2). Există S-P0 (`prototip/step/s/`, 63 × 70,8 × 25,65 mm, varianta din plastic) și planșa `blueprints/final/soul_s_1_general_arrangement`. `prototip/step/alu/` e geometria veche a kitului M (112 × 125 × 31,6 mm). RFQ-ul trebuie să spună asta.

## 3. Ce faci tu, pas cu pas

**Pasul 1 — Ce salvezi direct ca PDF (fără email), săptămâna asta**
1. Deschizi pagina în Chrome. **Ctrl+P → Salvează ca PDF → Mai multe setări → bifezi „Anteturi și subsoluri”.** Așa apar data și URL-ul pe fiecare pagină.
2. Numești fișierul `L05_Rigol_rigolshop_2026-10-12.pdf` (linie, furnizor, dată).
3. Le pui pe toate într-un folder `oferte/` lângă dosar.
4. Merge pentru: toate paginile de produs de la L5, L6, L7, L11, taxele EUIPO, APC-urile, Hetzner/Scaleway, Anthropic/OpenAI, Onshape, focusgrupuri.ro, IZI Data, Aria United, sălile L17, ZUT, AISLER.
5. Paginile care ne-au blocat (Sigmanortec, eMAG, MDPI, Autodesk, TME, Xometry) le deschizi tu și faci la fel.

**Pasul 2 — Oferte instant online (cont gratuit, fără comandă)**
- **Weerg:** cont → salvezi datele firmei → încarci STEP → „Download” ofertă PDF.
- **Hubs:** încarci STEP → descarci PDF-ul ofertei. Poți bloca prețul 30 de zile. **Nu plătești.**
- **JLCPCB / PCBWay / JLCCNC:** încarci Gerber/BOM/CPL sau STEP → printezi pagina ofertei ca PDF. Apoi ceri pe email ofertă formală pe numele ARTEMIS.
- **Sanel Factory / Materialise:** la fel, după ce există STL-ul oului OU.
- Pentru L12 folosești **aceeași specificație și aceleași cantități** peste tot (3 / 5 / 15 / 23 de seturi).

**Pasul 3 — Ce ceri pe email (nu au preț public)**
- L8 Ranatec, Orbis · L11b panourile (Zhuohong, Twoyas) · L11e coșul TME + Mouser · L12 Alvi Technik, ARSAT · L13 Circuite Imprimate, Sadelec · L14 PIT, cetecom, NMi, EMCLab · L15 cetecom, Applus+, QIMA · L16 IMT, Ignion · L20 Lupșa, OTDIP (căutare anterioritate + opinie) · L24 2 consultanți + 2 experți · L26 Contello, Audit Galis · L27 2 tipografii.
- Folosești emailurile de mai jos. Trimiți de pe adresa firmei.

**Pasul 4 — Verifici fiecare ofertă primită**
- E pe numele ARTEMIS DIGITAL S.R.L.? Are dată? Preț net + TVA? Valabilitate ≥ 90 de zile? Specificațiile se potrivesc cu Anexa 3?
- Dacă e în engleză, scrii o traducere simplă de o pagină.
- Pui ambele surse în Centralizatorul Anexa 19.

**Pasul 5 — NU faci:** nu comanzi, nu semnezi contracte (doar L24 e permis), nu plătești avans, nu dai „Accept quote”.

## 4. Emailuri gata de trimis

### 4.1 Model general (RO)

**Subiect:** Cerere de ofertă de preț — proiect cu finanțare nerambursabilă (fără comandă)

Bună ziua,

Vă scriu din partea ARTEMIS DIGITAL S.R.L. (București, CUI 53145290).

Pregătim o cerere de finanțare nerambursabilă (Programul Regional București-Ilfov, Acțiunea 1.1 „Proof of Concept”). Ghidul ne cere oferte de preț pentru fiecare cheltuială din buget.

**Vă rugăm să ne trimiteți o ofertă de preț. Aceasta NU este o comandă.** Achiziția se va face doar dacă proiectul este aprobat.

Produsul / serviciul: [denumire]
Cantitate: [cantitate]
Specificații minime: [specificațiile din Anexa 3]

Vă rugăm ca oferta să conțină:
1. ofertă scrisă, pe antetul firmei, adresată ARTEMIS DIGITAL S.R.L., cu dată;
2. preț unitar și preț total;
3. prețul fără TVA și TVA-ul, separat (firma noastră nu este plătitoare de TVA);
4. valabilitate de cel puțin 90 de zile;
5. termenul de livrare / execuție și condițiile de livrare (București);
6. confirmarea că produsul respectă specificațiile de mai sus (sau fișa tehnică).

Vă mulțumim!

[Nume și prenume]
ARTEMIS DIGITAL S.R.L.
[Telefon] · [email firmă]

### 4.2 Model general (EN, furnizori din UE și din afara ei)

**Subject:** Request for quotation — grant application (no order)

Dear Sir or Madam,

I am writing on behalf of ARTEMIS DIGITAL S.R.L. (Bucharest, Romania, company ID 53145290).

We are preparing an application for an EU-funded grant (Bucharest-Ilfov Regional Programme, Action 1.1 "Proof of Concept"). The rules require written price offers for every budget item.

**This is a REQUEST FOR QUOTATION only. It is NOT an order.** We will buy only if the grant is approved.

Item / service: [name]
Quantity: [quantity]
Minimum specification: [spec from the business plan]

Please include in your quotation:
1. a written quotation on company letterhead, addressed to ARTEMIS DIGITAL S.R.L., dated;
2. unit price and total price;
3. net price and VAT shown separately (we are not VAT-registered in Romania);
4. validity of at least 90 days;
5. lead time and delivery terms (DAP Bucharest, Romania, incl. shipping);
6. confirmation that the offer meets the specification above (or a datasheet).

Thank you!

[Name]
ARTEMIS DIGITAL S.R.L.
[Phone] · [company email]

### 4.3 CNC aluminiu + anodizare (EN; RO: aceleași puncte)

**Subject:** RFQ — CNC aluminium enclosure sets, coloured anodising (grant application, no order)

Dear Sir or Madam,

ARTEMIS DIGITAL S.R.L. (Bucharest, Romania, ID 53145290) is preparing a grant application. **This is a request for quotation only, not an order.**

Parts per set: front shell, back shell, base plate, chassis, 2 small pins. Reference files attached: the S-P0 shells (`micul-smecher/prototip/step/s/*.step.gz`, 63 × 70.8 × 25.65 mm) and the dimensioned drawing `micul-smecher/blueprints/final/soul_s_1_general_arrangement.png`. The production shape will be about **63 × 71 × 23 mm**, with a **Ø52 mm** flat glass seat and the same features; its STEP will follow. Please quote the attached S-P0 geometry and tell us how the price changes for the 23 mm version.

- Material: Al 6061-T6 or equivalent 6082-T6.
- Finish: bead or shot blast, type II anodise, dyed and sealed, 5 colours (or the closest from your standard palette). Please list your colours.
- One approved physical colour sample per colour.
- Laser marking on the base plate (logo + serial).
- Tapped M2 holes, ISO 2768-m; ±0.05 mm on the glass seat.
- Quantity tiers: **3, 5, 15 and 23 sets**. Price for each tier.

Please send a written quotation addressed to ARTEMIS DIGITAL S.R.L., dated, with unit and total price per tier, net price + VAT separately (we are not VAT-registered), shipping **DAP Bucharest**, validity ≥ 90 days, lead time, and confirmation of each spec point above.

[Name] · ARTEMIS DIGITAL S.R.L. · [Phone]

### 4.4 PCB + asamblare (PCBA)

**Subject:** RFQ — 4-layer PCB + assembly, 2 revisions × 10 pcs (grant application, no order)

Dear Sir or Madam,

ARTEMIS DIGITAL S.R.L. (Bucharest, Romania, ID 53145290) requests a **quotation only, not an order**, for a grant application.

- Board: round, about Ø46 mm. ESP32-S3-WROOM-1-N16R8 module (8 MB PSRAM, 16 MB flash), QSPI FPC connector for a 1.75" round AMOLED (CO5300, 466 × 466) with touch, IMU (QMI8658), RTC, PMU / LiPo charger (AXP2101 class), audio codecs ES8311 + ES7210 with 2 MEMS microphones and a speaker output, USB-C, pogo pads, module antenna.
- 4-layer FR4, 0.8 mm target (from our stack-up), ENIG. SMT on both sides, stencil included. Components sourced by you.
- Quantity: 2 revisions × 10 assembled boards (rev A now, rev B about 4 months later).
- Gerber/BOM/CPL: [will follow / attached]. If not ready, please quote from this description and your price table.

Please send a written quotation addressed to ARTEMIS DIGITAL S.R.L., dated: price per board and total per revision, PCB / assembly / components split, net + VAT separately, shipping DAP Bucharest, validity ≥ 90 days, lead time, and optional functional test.

[Name] · ARTEMIS DIGITAL S.R.L. · [Phone]

### 4.5 Laborator EMC / radio (pre-test)

**Subject:** RFQ — EMC and radio pre-compliance testing (RED), 2 sessions (grant application, no order)

Dear Sir or Madam,

ARTEMIS DIGITAL S.R.L. (Bucharest, Romania, ID 53145290) requests a **quotation only, not an order**, for a grant application.

- Device: handheld device in an aluminium enclosure, about 63 × 71 × 23 mm. ESP32-S3, Wi-Fi 2.4 GHz + Bluetooth LE, 1.75" AMOLED, 750 mAh LiPo, USB-C 5 V charging.
- **Pre-compliance (not certification), 2 sessions:** prototype rev A, then rev B about 4–6 months later.
- Scope: EN 301 489-1 / -17 (radiated + conducted emissions, ESD and immunity spot checks); EN 300 328 (2.4 GHz output power, occupied bandwidth, spurious emissions); optional EN 62479. Test report per session.
- Please say if your lab is accredited (RENAR / DAkkS / PCA) for these standards.

Please send a written quotation addressed to ARTEMIS DIGITAL S.R.L., dated: price per session and total, net + VAT separately (we are not VAT-registered), validity ≥ 90 days, earliest available dates, and what we must bring (samples, test firmware, power supply).

[Name] · ARTEMIS DIGITAL S.R.L. · [Phone]
