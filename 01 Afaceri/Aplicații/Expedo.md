---
tip: aplicatie
afacere: Aplicații
status: în lucru
actualizat: 2026-10-02
sursa: Claude Code
---
# Expedo

## 1. Pe scurt

Expedo procesează comenzile Shopify, ca xConnector, dar construit pornind de la erorile pe care le avem acolo:
- [[MundiShop]]: AWB-urile Cargus dau erori.
- [[MI-DA PRO TRADE]]: FGO dă „hashtagul nu a fost găsit”.

Ce face, pentru fiecare comandă:
1. Verifică adresa.
2. Generează AWB-ul.
3. Emite factura.
4. Marchează comanda ca expediată în Shopify; clientul primește AWB-ul pe e-mail.
5. Urmărește coletul.
6. La livrare, trece rambursul ca încasat.

## 2. Stadiu

**Gata și verificat (02.10.2026, 341 de teste automate trec):**
- Fluxul complet: comenzi din Shopify, verificare adresă, AWB, factură, expediere în Shopify, urmărire, ramburs încasat.
- **Testat pe magazinul de test dexters-laboratory** (aplicația „Expedo test” din Dev Dashboard): citirea comenzilor, adresa, ramburs, TVA (inclusiv magazine cu prețuri fără TVA), firmă cu CUI, marcare expediată cu AWB, etichete, marcare plătită, anulare expediere, fără dubluri. Comenzile de test au eticheta „expedo-e2e”.
- **Serverele reale ale curierilor și facturării** verificate cu date de conectare greșite intenționat: adresele, autentificarea și erorile lor reale sunt înțelese corect. Peste 30 de reparații pe baza răspunsurilor reale (ex. GLS blochează contul după 5 parole greșite → Expedo se oprește după prima).
- **FGO:** mesajele lor de eroare nu pomenesc „hash”; reîncercarea fără diacritice e reparată. Listele de județe și localități FGO se potrivesc.
- **Revizuire independentă a codului:** peste 40 de bug-uri reparate (mod de probă vs live, ramburs pe comenzi deja plătite, dubluri la întreruperi, securitate).
- Mod de probă, reguli, procesare în masă, etichete într-un PDF, listă de picking, export ramburs.

**Verificat fără conturi ale noastre (02.10.2026, 396 de teste):**
- **FAN Courier: testat cap-coadă pe contul public de test al FAN** — AWB real creat (ramburs, Cont Colector), etichetă PDF, urmărire, anulare. Au ieșit 3 bug-uri, reparate.
- **Sameday, GLS, DPD, Cargus, SmartBill, FGO, Oblio:** nu publică cont de test; Expedo e verificat pe răspunsurile oficiale din documentații și din modulele lor oficiale (SDK Sameday, plugin Cargus, spec SmartBill, plugin Oblio, PDF FGO). Bug-uri reale găsite și reparate (ex. SmartBill ar fi pus „Taxare inversă” la neplătitori de TVA; 638 de puncte Ship & Go Cargus fără stradă).
- FGO are mediu de test gratuit (testuat.fgo.ro/inregistrare), dar cere un cont pe firmă.

**Ce poate confirma doar un cont real** (vezi [[Expedo — cereri conturi de test]]):
- Răspunsurile reușite ale fiecărui curier (AWB creat, etichetă, urmărire) și ale programelor de facturare (factură emisă).
- Detalii marcate `VERIFY` în cod: coduri de status la Cargus/Sameday/GLS, câteva câmpuri FGO/SmartBill/Oblio.

**Lipsește:**
- Conturi de test la curieri și facturare (e-mailurile sunt gata).
- Server cu disc persistent (Render Starter + disc) și aplicația publică în Dev Dashboard.
- Pentru App Store: politică de confidențialitate, termeni, ștergerea datelor vechi, criptarea comenzilor salvate (răspunsurile „No” din formularul Shopify de protecția datelor).
- Validare: ≥5 comercianți care ar plăti (vezi [[Aplicații#Cum alegem o aplicație]]).

## 3. Tehnic

- **Codul:** `P/apps/expedo`, în acest vault, pe ramura `claude/expedo-comenzi-shopify`.
- **Stack:** Node 22, Express, SQLite.
- **Demo:** `npm install && npm run demo`. **Teste:** `npm test`.
- Detalii complete în `P/apps/expedo/README.md`.

## 4. Stadiu nou (04.10.2026)

- **Interfața în engleză**, cu româna ca a doua limbă (se alege după limba din adminul Shopify).
- **Planuri de preț** (Shopify App Pricing, decizie Andu 04.10): fără plan gratuit; 5 zile de probă gratuită, apoi **Pro $15** (1.000 comenzi/lună) sau **Pro Max $30** (nelimitat + procesare automată, istoric refuzuri, export ramburs, mai multe magazine, suport prioritar). Fără plan: doar modul de probă. Pași de configurare: `P/apps/expedo/PRICING.md`.
- **Protecția datelor pentru App Store:** date criptate, ștergere automată după 180 de zile, jurnal de acces, GDPR, pagini /privacy și /terms.
- **Istoric colete refuzate** după telefon/e-mail (Pro Max).
- **Trailer motion design** 56 s, EN + RO, orizontal + vertical: `P/apps/expedo/marketing/trailer/`. Muzică Mixkit (licență gratuită comercială, fără TV/radio), voce Microsoft neurală.
- **Trusa App Store în engleză:** iconiță, imagine principală, 6 capturi + 3 pe telefon, texte, prețuri, filmuleț și instrucțiuni pentru recenzenți: `P/apps/expedo/marketing/listing/LISTING.md`.
- 452 de teste automate trec.

- **Publicat (04.10.2026):** serverul rulează la https://expedo.onrender.com (Render, Frankfurt, totul gratuit: datele se copiază criptat într-un Key Value gratuit și se refac singure la repornire, verificat 08.10; serverul nu mai adoarme). Configurația Shopify (adresa aplicației, redirect, permisiuni, webhook-uri) e trimisă în aplicația „Expedo test” (versiunea expedo-2). Verificat pe dexters-laboratory: comenzile se sincronizează, iar o comandă nouă apare în aplicație în câteva secunde, prin webhook.

**Rămâne (doar cu conturile lui Andu):**
- cele două planuri de preț din Dev Dashboard (`PRICING.md`);
- încărcarea listării și „Submit for review” (`marketing/listing/LISTING.md`).
