# Expedo — procesare comenzi Shopify

Expedo preia comenzile din Shopify și face restul: verifică adresa, generează AWB-ul la curier, emite factura, marchează comanda ca expediată în Shopify (clientul primește AWB-ul pe e-mail), urmărește coletul și, când e livrat, marchează rambursul ca încasat. E aceeași treabă ca la xConnector, construită pornind de la erorile pe care le avem acolo.

## De ce e mai bun decât xConnector

| Problema la xConnector | Ce face Expedo |
|---|---|
| AWB-urile Cargus dau erori, fără să spună de ce | Adresa e verificată **înainte** de curier (județ, localitate, sector, telefon, cod poștal). Localitatea e căutată în nomenclatorul curierului; dacă nu se potrivește, vezi „Ai vrut: X, Y, Z?” și o corectezi într-un clic. |
| Facturarea FGO dă „hashtagul nu a fost găsit” | Hash-ul FGO e calculat exact după documentația lor (v7.0, martie 2026), cu teste automate. Cererile se trimit ca JSON, cum cere acum FGO. |
| Erori tehnice, în engleză sau JSON | Fiecare eroare are un mesaj scurt în română + ce să faci. Detaliile tehnice stau ascunse sub „Detalii tehnice”. |
| Erori temporare (curier căzut) = comandă blocată | Se reîncearcă singur după 1, 5, 15, 60, 180 de minute. |
| Risc de AWB sau factură dublă | O comandă nu primește niciodată două AWB-uri sau două facturi (blocare pe comandă + verificare în baza de date). |
| Facturi de test pe comenzi reale | **Modul de probă**: tot fluxul rulează pe comenzi reale, dar cu curier și facturare de test; Shopify nu se atinge. |
| Un singur curier pe magazin | **Reguli**: easybox → Sameday, peste 5 kg → 2 colete, ramburs peste 1.500 lei → în așteptare etc. |

În plus: etichete pentru mai multe comenzi într-un singur PDF (A6 sau A4), listă de picking, export ramburs (CSV) pentru verificarea plăților de la curieri, istoric complet pe fiecare comandă, panou cu ce e de făcut azi, și **istoricul de refuzuri**: dacă un client a mai refuzat un colet cu ramburs, comanda lui nouă arată „Clientul a refuzat 2 colete înainte (din 5)” înainte de AWB (și se poate face o regulă „Colete refuzate înainte > 0 → în așteptare”).

## Datele clienților

- Numele, adresele, telefoanele și e-mailurile sunt **criptate** în baza de date (AES-256-GCM, cheie din `APP_SECRET`). Căutarea după nume / telefon / e-mail merge prin coduri (HMAC), doar pe potrivire exactă; comanda, AWB-ul și factura se caută ca înainte. Bazele vechi se criptează singure la prima pornire.
- **Setări → Date clienți**: câte zile se păstrează datele clienților după livrare / retur / anulare (90, 180, 365, 730; implicit 180). Zilnic se șterg; rămân nr. comenzii, sumele, AWB-ul și factura. Comenzile în lucru nu se ating.
- **Activitate → Acces la date**: cine a deschis o comandă sau a descărcat etichete, facturi, picking, export ramburs, date client (păstrat un an).
- Cererile GDPR din Shopify (date client, ștergere client, ștergere magazin) sunt tratate automat; cererea de date apare în Activitate cu buton de descărcare.
- Pagini publice: `/confidentialitate`, `/termeni` (cu acordul de prelucrare a datelor), în engleză `/privacy`, `/terms`. Procedura pentru incidente și răspunsurile la chestionarul Shopify: [`docs/securitate.md`](docs/securitate.md).

## Integrări

- **Curieri:** Cargus, Sameday (inclusiv easybox), FAN Courier (inclusiv FANbox), GLS, DPD.
- **Facturare:** SmartBill, FGO, Oblio.

Integrările sunt scrise după documentația oficială și verificate pe serverele reale cu date de conectare greșite intenționat (adrese, autentificare, erori). **Răspunsurile reușite (AWB creat, factură emisă) nu au fost încă văzute pe un cont real** (n-avem datele de conectare aici). Locurile nesigure sunt marcate în cod cu `// VERIFY:`. Primul pas la fiecare: „Testează conexiunea” din Setări, apoi o comandă în modul de probă, apoi una reală.

## Pornire rapidă (demo, fără Shopify)

```bash
npm install
npm run demo        # http://localhost:3000
```

Pornește cu un magazin demo cu 21 de comenzi românești, inclusiv unele „problemă” (fără telefon, fără județ, firmă cu CUI, easybox, comandă anulată) și un client care a mai refuzat un colet cu ramburs.

## Teste

```bash
npm test
```

## Instalare pe un magazin real

1. **Aplicație Shopify:** în Dev Dashboard (dev.shopify.com) creezi aplicația „Expedo”. Completezi `client_id` și adresele în `shopify.app.toml`, apoi `shopify app deploy`.
   - Aplicația citește nume, adrese și telefoane din comenzi, deci are nevoie de acces la **protected customer data** (nivelul 2: nume, adresă, telefon, e-mail). Se cere din Partner Dashboard → API access; răspunsurile la chestionar sunt în `docs/securitate.md`. La „Privacy policy URL” pui `https://<server>/privacy` (sau `/confidentialitate`).
2. **Server:** `render.yaml` e gata pentru Render. **Atenție:** baza de date e SQLite, deci are nevoie de disc persistent (planul Starter + disc, ~7 $/lună). Pe planul gratuit datele se pierd la fiecare repornire.
3. **Variabile:** vezi `.env.example`. `APP_SECRET` criptează datele clienților, parolele curierilor și token-urile Shopify; nu se mai schimbă după pornire. `PUBLISHER_DETAILS` (CUI, sediu) apare pe paginile de confidențialitate și termeni.
4. Instalezi aplicația pe magazin → se deschide în adminul Shopify → **Setări → Curieri** și **Facturare**: datele de conectare + „Testează conexiunea”.
5. Rulezi câteva zile în **modul de probă**, apoi **Setări → General → Live**.

## Cum e construit

- Node 22, Express, SQLite (`node:sqlite`), fără build pentru interfață.
- `src/core/` — validare adrese, reguli, fluxul de procesare (`pipeline.js`).
- `src/couriers/`, `src/invoicing/` — câte un fișier pe integrare, toate după același contract (`contract.js`).
- `src/shopify/` — OAuth, token exchange pentru aplicația din admin, webhook-uri, GraphQL Admin API (2026-07).
- `src/worker.js` — sarcini în fundal (procesare automată, urmărire colete la 30 min, resincronizare la 15 min), salvate în baza de date, deci nu se pierd la repornire.
- `public/` — interfața (HTML + JS simplu). Merge în adminul Shopify (App Bridge) și separat, cu parolă (`ADMIN_PASSWORD`).

## Test pe un magazin de dezvoltare

```bash
SHOPIFY_API_KEY=... SHOPIFY_API_SECRET=... node scripts/e2e-devstore.mjs <magazin>.myshopify.com
```

Aplicația trebuie creată în Dev Dashboard de aceeași organizație ca magazinul, instalată pe el și cu acces la datele clienților (Partners → API access requests). Scriptul creează 3 comenzi de test și verifică tot fluxul în Shopify, fără e-mailuri către clienți. Magazinele proprii se pot lega și permanent prin `SHOPIFY_OWN_STORES`.
