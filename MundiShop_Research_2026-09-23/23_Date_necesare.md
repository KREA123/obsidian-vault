---
title: "Datele necesare pentru personalizare"
verified_at: 2026-09-23
version: "1.0"
status: cercetare_si_propuneri
tags: [mundishop, ecommerce, meta-ads, romania]
sources: []
---

# Datele necesare pentru personalizare

Nu este necesar să trimiți parole, tokenuri sau baze cu date personale. Exporturile agregate sau pseudonimizate sunt suficiente pentru prima analiză. Păstrează cheia care leagă ID-urile de clienți numai în sistemul tău.

## Date despre comenzi

Interval recomandat: ultimele 90 de zile, plus 12 luni la nivel lunar dacă există istoric, pentru sezonalitate. Câmpuri: ID comandă pseudonimizat, data plasării, data livrării, status final, client nou sau existent, SKU, cantitate, venit produse, reduceri, transport încasat, cost produse, cost curier, comisioane, rambursări și motiv de retur/refuz dacă este cunoscut. Fără nume, telefon, email sau adresă.

## Date despre reclame

Exportă pe zi, campanie, ad set și reclamă: ID-uri, nume, obiectiv, cheltuială, afișări, acoperire, frecvență, clicuri relevante, vizite pe pagina de destinație unde sunt disponibile, cumpărări, valoare cumpărări și setarea de atribuire. Exporturile pe plasament, dispozitiv sau vârstă se analizează separat, fără însumarea rândurilor din rapoarte care se suprapun.

## Date despre produse și site

Pentru SKU: preț, cost contabil relevant, stoc, termen de reaprovizionare, temă, cod LEGO, EAN, vârstă, piese, greutate și dimensiuni relevante pentru livrare, URL și apartenență la pachete. Pentru site: sesiuni pe sursă și dispozitiv, pagini de intrare, evenimente de comerț electronic, erori și date de performanță.

## Întrebările cu impact maxim

1. Care este bugetul lunar și pierderea de test acceptabilă?
2. Ce contribuție rămâne după produs, transport, taxe și ambalare?
3. Câte comenzi ajung livrate și nerefundate, separat pe ramburs și card?
4. Ce produse au stoc și reaprovizionare suficiente?
5. Ce campanii și oferte au produs deja comenzi profitabile?

Fără aceste răspunsuri, Claude trebuie să ofere scenarii și întrebări, nu să inventeze un CPA real sau un buget optim.

## Note asociate

[[MundiShop_Research_2026-09-23/01_Obiectiv_profit_anual|Modelul obiectivului de un milion de euro profit anual]] | [[MundiShop_Research_2026-09-23/06_Economie_comanda|Economia unei comenzi înainte de setarea bugetului]] | [[MundiShop_Research_2026-09-23/11_Masurare_Pixel_CAPI|Măsurarea care permite decizii bune]] | [[MundiShop_Research_2026-09-23/12_Raportare_KPI|Raportarea zilnică și săptămânală]]

[[MundiShop_Research_2026-09-23/00_Index|Înapoi la index]] | [[MundiShop_Research_2026-09-23/99_Surse|Registrul surselor]]

## În vault-ul nostru (legat de Claude, 24.09)

**La noi, pe date reale:**
- Multe răspunsuri există deja: pâlnia, cost pe comandă pe canal, marje pe bandă de preț. Lipsesc: q pe ramburs/card, comisioanele reale, capitalul și pierderea acceptată la teste.

Legat: [[Cifre cheie MundiShop]] · [[Conturi și unelte MundiShop]] · [[Prețuri și marje MundiShop]] · [[Hartă cunoaștere MundiShop]]
