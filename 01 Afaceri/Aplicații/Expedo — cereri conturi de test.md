---
tip: aplicatie
afacere: Aplicații
status: de trimis
actualizat: 2026-10-02
sursa: Claude Code
---
# Expedo — cereri conturi de test

Cu conturile de test verificăm fiecare integrare cap-coadă (AWB, etichetă, anulare, urmărire; factură, PDF, stornare), fără MundiShop și fără bani reali. Vezi [[Expedo]].

## Ce cerem și de la cine

| Cine | Ce cerem | Cum |
|---|---|---|
| **Sameday** | Cont pe serverul lor de test (sameday-api.demo.zitec.com) | E-mail la echipa de integrări (adresa de pe sameday.ro, secțiunea pentru dezvoltatori / API) |
| **GLS România** | Cont MyGLS de test (api.test.mygls.ro) | E-mail la departamentul IT / integrări GLS România |
| **Cargus** | Cheie API (portalul urgentcargus) + cont de test sau acces de test pe contul MundiShop | Cont pe portalul API Cargus + e-mail la agentul de vânzări / IT |
| **FAN Courier** | Cont de test pentru API v2 | E-mail la IT / integrări FAN |
| **DPD România** | Utilizator API de test | E-mail la IT / integrări DPD |
| **FGO** | Acces la serverul de test (api-testuat.fgo.ro) | E-mail la suport FGO |
| **SmartBill** | — | Cont nou de probă gratuit (30 de zile), pe o firmă de test; tokenul API e în Setări → Integrări |
| **Oblio** | — | Cont gratuit; datele API sunt în Setări → Date firmă → API |

Adresele de e-mail exacte se iau de pe site-ul fiecăruia; nu le-am verificat.

## Modelul de e-mail (curieri)

> **Subiect:** Cerere cont de test API — integrare Shopify (ARTEMIS DIGITAL SRL)
>
> Bună ziua,
>
> Suntem ARTEMIS DIGITAL SRL și dezvoltăm Expedo, o aplicație de procesare a comenzilor pentru magazinele Shopify din România (generare AWB, etichete, urmărire colete, ramburs).
>
> Am finalizat integrarea cu API-ul [NUME CURIER] după documentația oficială și dorim să o testăm înainte de lansare. Vă rugăm să ne puneți la dispoziție un cont de test pentru API (utilizator, parolă și, dacă e cazul, cheie / client ID și un punct de ridicare de test).
>
> Integrarea folosește: autentificare, nomenclatorul de localități, creare AWB (inclusiv ramburs și livrare la locker, unde există), descărcare etichetă PDF, anulare AWB și urmărire colete.
>
> Mulțumim,
> Andu
> ARTEMIS DIGITAL SRL · office@krea.ro

## Modelul de e-mail (FGO)

> **Subiect:** Acces mediu de test API — integrare Shopify (ARTEMIS DIGITAL SRL)
>
> Bună ziua,
>
> Dezvoltăm Expedo, o aplicație care emite automat facturi FGO pentru comenzile din magazinele Shopify. Am implementat API-ul FGO după documentația v7.0 (emitere, print, anulare, stornare, încasare, status) și dorim să o testăm pe mediul de test (api-testuat.fgo.ro). Vă rugăm să ne activați un cont de test (CUI de test și cheie privată).
>
> Mulțumim,
> Andu
> ARTEMIS DIGITAL SRL · office@krea.ro
