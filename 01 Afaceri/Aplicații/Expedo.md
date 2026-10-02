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

**Gata (verificat în modul demo, 214 teste automate trec):**
- Fluxul complet: comenzi din Shopify, verificare adresă, AWB, factură, expediere în Shopify, urmărire, ramburs încasat.
- **Modul de probă:** rulează pe comenzi reale cu curier și facturare de test. Nu se emite nimic real și Shopify nu se atinge.
- Reguli de alegere a curierului (ex. easybox → Sameday).
- Procesare în masă, etichete într-un singur PDF, listă de picking, export ramburs (CSV).
- Reîncercare automată la erori temporare. Nu dă niciodată AWB sau factură dublă.
- Integrări scrise:
  - curieri: Cargus, Sameday, FAN Courier, GLS, DPD;
  - facturare: SmartBill, FGO, Oblio.

**Netestat:**
- Integrările **nu au fost încercate pe conturi reale**, pentru că nu avem datele de conectare.
- Locurile nesigure sunt marcate în cod cu `VERIFY`.
- FGO: documentația lor actuală cere JSON, nu formular. Ăsta e un motiv probabil (neconfirmat) pentru eroarea „hash” de la MI-DA.

**Lipsește:**
- Server cu disc persistent (Render Starter + disc).
- Aplicația creată în Shopify Dev Dashboard și accesul la datele clienților (nume, adresă, telefon).
- Test pe MundiShop: întâi în modul de probă, apoi live, cu Cargus + SmartBill.
- Validare: ≥5 comercianți care ar plăti, dacă vrem s-o vindem în Shopify App Store (vezi [[Aplicații#Cum alegem o aplicație]]).

## 3. Tehnic

- **Codul:** `P/apps/expedo`, în acest vault, pe ramura `claude/expedo-comenzi-shopify`.
- **Stack:** Node 22, Express, SQLite.
- **Demo:** `npm install && npm run demo`. **Teste:** `npm test`.
- Detalii complete în `P/apps/expedo/README.md`.
