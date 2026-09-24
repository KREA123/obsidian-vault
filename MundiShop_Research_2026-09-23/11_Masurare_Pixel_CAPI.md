---
title: "Măsurarea care permite decizii bune"
verified_at: 2026-09-23
version: "1.0"
status: cercetare_si_propuneri
tags: [mundishop, ecommerce, meta-ads, romania]
sources: [S25, S26, S27, S28, S30]
---

# Măsurarea care permite decizii bune

## Trei perspective necesare

Shopify și evidența operațională spun ce s-a comandat, livrat și încasat. GA4 arată traseul vizitelor pentru partea de trafic măsurată. Ads Manager arată conversiile atribuite conform setărilor Meta. Diferențele dintre ele nu sunt automat erori: consimțământul, ferestrele de atribuire, modelele, momentul raportării și anulările pot produce diferențe legitime.

Nu însuma conversiile atribuite de Meta, Google și email ca și când ar fi comenzi unice. O comandă poate fi revendicată de mai multe sisteme. Reconcilierea se face pe identificatori interni de comandă și pe totalurile magazinului, fără expunerea datelor personale în documentele de lucru.

## Evenimente și verificări

| Pas al cumpărătorului | Denumire uzuală Meta | Echivalent GA4 | Verificarea necesară |
|---|---|---|---|
| Vede un produs | ViewContent | view_item | ID-ul și prețul produsului corespund paginii |
| Adaugă în coș | AddToCart | add_to_cart | Cantitatea și valoarea reprezintă acțiunea reală |
| Începe finalizarea | InitiateCheckout | begin_checkout | Nu se declanșează doar pentru deschiderea unui meniu |
| Plasează comanda | Purchase | purchase | Un singur eveniment logic, ID comandă, monedă și valoare corecte |
| Rambursezi o comandă | Flux operațional documentat | refund, când integrarea îl implementează | Venitul este ajustat în evidența comercială |

Tabelul este o mapare de verificare, nu o promisiune că toate evenimentele sunt active. Implementarea GA4 recomandă evenimente de comerț electronic și parametri expliciți pentru produse, tranzacții și rambursări. [S30]

## Pixel și Conversions API

Shopify oferă niveluri de partajare a datelor pentru integrarea Facebook and Instagram by Meta, inclusiv Pixel și Conversions API. Setarea mai bogată în date nu elimină obligațiile de informare și consimțământ. Documentația recomandă evitarea pixelilor vechi instalați simultan cu integrarea nouă dacă produc date duplicate. [S25, S26]

PROPUNERE de QA: stabilește o singură implementare responsabilă pentru fiecare eveniment. Dacă browserul și serverul raportează aceeași cumpărare, verifică mecanismul de deduplicare al integrării, inclusiv concordanța dintre numele evenimentului și identificatorul comun event_id. Două identificatoare diferite pentru aceeași comandă pot indica o implementare greșită; tehnicianul trebuie să valideze în Events Manager și în documentația curentă a integrării. Nu adăuga un al doilea plugin CAPI doar pentru că un curs îl recomandă.

Schimbarea pixelilor poate modifica numărul de evenimente din cauza consimțământului sau a diferențelor de implementare. Shopify avertizează explicit că instrumentele de consimțământ trebuie sincronizate cu mecanismul său de confidențialitate. Nu reparăm scăderea măsurării ignorând refuzul utilizatorului. [S27, S28]

## Testele minime înainte de scalare

1. Alege un produs simplu și un pachet. Confirmă corespondența pagină-catalog-eveniment.
2. Într-un mediu sau proces de test controlat, verifică afișare, adăugare, checkout și confirmarea comenzii.
3. Reîncarcă pagina de confirmare și verifică dacă apare o cumpărare suplimentară nejustificată.
4. Verifică dacă 159,99 lei se transmit ca 159.99 RON, nu 15999 RON și nu EUR.
5. Notează dacă valoarea Purchase include transport, taxe și reduceri; folosește aceeași definiție în ținte.
6. Testează separat card, ramburs și eventuale plăți accelerate. Nu presupune același moment de recunoaștere a venitului.
7. Testează acceptarea și refuzul cookie-urilor. Evenimentele trebuie să respecte configurația validată pentru România.
8. Verifică ce se întâmplă cu anulările, refuzurile și retururile în raportul intern.
9. Compară evenimentele test cu comenzile test după ID și oră, în același fus orar.
10. Documentează ce a fost verificat, pe ce dispozitiv, de cine și ce a rămas deschis.

Pentru ramburs, păstrează evenimentul standard al integrării și adaugă raportarea operațională a comenzilor livrate. Nu trimite încă un Purchase când coletul este livrat dacă asta ar dubla comanda. O optimizare avansată pe evenimente de calitate se discută numai după validarea volumului, latenței și capacității tehnice.

## UTM și denumiri

Folosește o convenție stabilă, documentată, care identifică sursa, campania, ad setul și reclama. Preferă ID-uri persistente în câmpurile de analiză, deoarece numele se pot schimba. Exemplu conceptual: source=facebook, medium=paid_social, campaign=ID campanie, content=ID reclamă, term=ID ad set. Pentru Instagram, sursa trebuie să reflecte plasamentul dacă integrarea permite.

Dacă folosești parametri dinamici Meta, validează macros-urile disponibile în cont și deschide linkul final din previzualizare. Nu pune nume, adrese, emailuri sau telefoane în URL. Păstrează separat un registru care traduce ID-ul reclamei în concept, produs, ofertă și data lansării.

## Note asociate

[[MundiShop_Research_2026-09-23/10_Structura_campanii|Structura propusă în Ads Manager]] | [[MundiShop_Research_2026-09-23/12_Raportare_KPI|Raportarea zilnică și săptămânală]] | [[MundiShop_Research_2026-09-23/25_Reguli_incredere|Reguli comerciale și de încredere]]

[[MundiShop_Research_2026-09-23/00_Index|Înapoi la index]] | [[MundiShop_Research_2026-09-23/99_Surse|Registrul surselor]]

## În vault-ul nostru (legat de Claude, 24.09)

**La noi, pe date reale:**
- Testele 1–9: Purchase 28 = 28, un singur pixel (canalul Shopify, cu CAPI), RON corect; AddToCart 29% fără valoare pe CAPI — impact mic.
- Pasul 7 (consimțământ) pică: bannerul de cookie e scos din 8.09 → [[Eliminarea bannerului de cookie]].
- Google raportează conversii false/dublate — sursa de adevăr rămâne Shopify.

Legat: [[Tracking MundiShop]] · [[Eliminarea bannerului de cookie]] · [[Sufix URL Google și regula Merchant Center]] · [[Google Ads MundiShop]] · [[Hartă cunoaștere MundiShop]]
