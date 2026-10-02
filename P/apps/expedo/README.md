# Expedo — procesare comenzi Shopify

Expedo preia comenzile din Shopify și face restul: verifică adresa, generează AWB-ul la curier, emite factura, marchează comanda ca expediată în Shopify (clientul primește AWB-ul pe e-mail), urmărește coletul și, când e livrat, marchează rambursul ca încasat. E aceeași treabă ca la xConnector, construită pornind de la erorile pe care le avem acolo.

## De ce e mai bun decât xConnector

| Problema la xConnector | Ce face Expedo |
|---|---|
| AWB-urile Cargus dau erori, fără să spună de ce | Adresa e verificată **înainte** de curier (județ, localitate, sector, telefon, cod poștal). Localitatea e căutată în nomenclatorul curierului; dacă nu se potrivește, vezi „Ai vrut: X, Y, Z?” și o corectezi într-un clic. |
| Facturarea FGO dă „hashtagul nu a fost găsit” | Hash-ul FGO e calculat exact după documentația lor, cu teste automate. |
| Erori tehnice, în engleză sau JSON | Fiecare eroare are un mesaj scurt în română + ce să faci. Detaliile tehnice stau ascunse sub „Detalii tehnice”. |
| Erori temporare (curier căzut) = comandă blocată | Se reîncearcă singur după 1, 5, 15, 60, 180 de minute. |
| Risc de AWB sau factură dublă | O comandă nu primește niciodată două AWB-uri sau două facturi (blocare pe comandă + verificare în baza de date). |
| Facturi de test pe comenzi reale | **Modul de probă**: tot fluxul rulează pe comenzi reale, dar cu curier și facturare de test; Shopify nu se atinge. |
| Un singur curier pe magazin | **Reguli**: easybox → Sameday, peste 5 kg → 2 colete, ramburs peste 1.500 lei → în așteptare etc. |

În plus: etichete pentru mai multe comenzi într-un singur PDF (A6 sau A4), listă de picking, export ramburs (CSV) pentru verificarea plăților de la curieri, istoric complet pe fiecare comandă, panou cu ce e de făcut azi.

## Integrări

- **Curieri:** Cargus, Sameday (inclusiv easybox), FAN Courier (inclusiv FANbox), GLS, DPD.
- **Facturare:** SmartBill, FGO, Oblio.

Integrările sunt scrise după documentația oficială, dar **nu au fost încă testate pe conturi reale** (n-avem datele de conectare aici). Locurile nesigure sunt marcate în cod cu `// VERIFY:`. Primul pas la fiecare: „Testează conexiunea” din Setări, apoi o comandă în modul de probă, apoi una reală.

## Pornire rapidă (demo, fără Shopify)

```bash
npm install
npm run demo        # http://localhost:3000
```

Pornește cu un magazin demo cu 19 comenzi românești, inclusiv unele „problemă” (fără telefon, fără județ, firmă cu CUI, easybox, comandă anulată).

## Teste

```bash
npm test
```

## Instalare pe un magazin real

1. **Aplicație Shopify:** în Dev Dashboard (dev.shopify.com) creezi aplicația „Expedo”. Completezi `client_id` și adresele în `shopify.app.toml`, apoi `shopify app deploy`.
   - Aplicația citește nume, adrese și telefoane din comenzi, deci are nevoie de acces la **protected customer data** (nivelul 2: nume, adresă, telefon, e-mail). Se cere din Partner Dashboard → API access.
2. **Server:** `render.yaml` e gata pentru Render. **Atenție:** baza de date e SQLite, deci are nevoie de disc persistent (planul Starter + disc, ~7 $/lună). Pe planul gratuit datele se pierd la fiecare repornire.
3. **Variabile:** vezi `.env.example`. `APP_SECRET` criptează parolele curierilor și token-urile Shopify; nu se mai schimbă după pornire.
4. Instalezi aplicația pe magazin → se deschide în adminul Shopify → **Setări → Curieri** și **Facturare**: datele de conectare + „Testează conexiunea”.
5. Rulezi câteva zile în **modul de probă**, apoi **Setări → General → Live**.

## Cum e construit

- Node 22, Express, SQLite (`node:sqlite`), fără build pentru interfață.
- `src/core/` — validare adrese, reguli, fluxul de procesare (`pipeline.js`).
- `src/couriers/`, `src/invoicing/` — câte un fișier pe integrare, toate după același contract (`contract.js`).
- `src/shopify/` — OAuth, token exchange pentru aplicația din admin, webhook-uri, GraphQL Admin API (2026-07).
- `src/worker.js` — sarcini în fundal (procesare automată, urmărire colete la 30 min, resincronizare la 15 min), salvate în baza de date, deci nu se pierd la repornire.
- `public/` — interfața (HTML + JS simplu). Merge în adminul Shopify (App Bridge) și separat, cu parolă (`ADMIN_PASSWORD`).
