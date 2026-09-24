---
title: "Auditul public al magazinului"
verified_at: 2026-09-23
version: "1.0"
status: cercetare_si_propuneri
tags: [mundishop, ecommerce, meta-ads, romania]
sources: [S01, S02, S03, S04, S05, S06, S07, S08, S39]
---

# Auditul public al magazinului

## Ce funcționează ca bază comercială

Pagina principală oferă navigare după temă, vârstă, interes și buget. Sunt prezente pagini sub 100 și sub 200 lei, colecții pentru adulți, pachete cadou și selecții sezoniere. Magazinul comunică produse originale sigilate, factură, ramburs și card. Aceste elemente pot susține reclame cu destinații specifice; nu este necesar ca orice campanie să trimită pe homepage. [S01, S02]

## Constatări și intervenții propuse

| Prioritate | Observație verificată sau limită | Intervenție propusă |
|---|---|---|
| P0 | În headline apar peste 1.000 de seturi, iar meniul indică 676 de seturi | Verifică dacă cifra mare include accesorii, variante ori unități. Folosește aceeași definiție în reclame și catalog |
| P0 | Politica publică stabilește transport de 25 lei | Prezintă costul total aproape de decizia de cumpărare; testează pragul de gratuitate numai după calculul marjei |
| P0 | Mesajele scurte spun 24-72 ore; politica precizează ore lucrătoare de la confirmare | Uniformizează condiția și evită promisiuni de sosire garantată fără acoperire operațională |
| P1 | Linkul rapid Pentru adulți duce la colecția Icons | Folosește o selecție adultă care poate include și Technic, Botanicals, Architecture și alte teme relevante |
| P1 | Pachetul Harry Potter recomandă ghiozdane în zona Din aceeași temă | Corectează taxonomia și recomandările pentru pachete; sugerează produse Harry Potter și accesorii potrivite |
| P1 | În specificațiile pachetului apare MundiShop.ro ca producător | Distinge organizatorul pachetului de producătorii componentelor; completează datele fiecărei componente |
| P1 | Galerie cu etichete de accesibilitate Translation missing | Completează traducerile butoanelor și ale regiunii galeriei |
| P1 | Pachetul are taburi separate cu 0 recenzii produs și 12 recenzii magazin | Păstrează distincția; adu dovezi autentice despre magazin lângă ofertă, fără a le prezenta drept recenzii ale setului |
| P1 | Datele de contact folosesc office@krea.ro | Explică legătura cu operatorul sau folosește un contact de brand valid; evită confuzia în mesajele postcomandă |
| P1 | Footerul trimite încă la vechea platformă SOL | Actualizează informațiile după verificarea obligațiilor locale; platforma europeană ODR s-a închis |
| De verificat | Un cadru al caruselului principal nu a afișat fotografia în browserul de audit | Reproduce pe dispozitive și rețele reale; nu trata această observație izolată drept defect confirmat pentru toți vizitatorii |
| Necunoscut | Măsurarea, checkoutul mobil, erorile de plată și consimțământul real | Efectuează QA tehnic și comandă test controlată înainte de scalare |

Sursele observațiilor: homepage și catalog [S01, S02], pagina pachetului inspectată în browser [S03], politicile și datele comerciantului [S05-S07]. Închiderea ODR este confirmată de Comisia Europeană [S39]. Prioritățile și soluțiile sunt propuneri de lucru, nu rezultate de experiment.

## Exemplul pachetului Harry Potter

La verificare, pachetul cu setul 76471 și brelocul Dobby era disponibil la 529,99 lei. Pagina indica 640,98 lei pentru componente cumpărate separat și valoarea brelocului de 110,99 lei. Produsul avea trei imagini. Nu am verificat costurile componentelor sau istoricul prețurilor. [S03]

PROPUNERE: această ofertă merită un test cu o reclamă care arată clar ambele componente. Validarea comercială trebuie să includă costul real al cadoului, stocul simultan al componentelor, regulile de retur ale pachetului și eligibilitatea la reduceri. Diferența față de suma prețurilor separate nu este același lucru cu o reducere calculată față de propriul preț anterior.

Pagina poate răspunde mai repede la întrebările: pentru ce vârstă este setul, câte piese are, ce dimensiuni are construcția, ce include exact pachetul și cât plătesc cu transport. Specificațiile se completează din documentația producătorului. Nu le deduce din fotografie sau din tema Harry Potter.

## Un exemplu concret de competiție prin costul livrat

Comparația se referă la codul 10347, cu EAN 5702017814667. Prețul MundiShop a fost verificat în datele publice ale produsului, iar oferta Noriel în pagina publică extrasă de motorul de cercetare. Pagina Noriel fusese indexată cu câteva zile înainte și includea date de livrare deja trecute; cifrele sunt un instantaneu orientativ, nu o cotație garantată în checkout. [S04, S08]

| Ofertă observată | Produs | Transport afișat | Total calculat |
|---|---:|---:|---:|
| MundiShop prin curier | 159,99 lei | 25,00 lei | 184,99 lei |
| Noriel prin curier | 159,99 lei | 16,99 lei | 176,98 lei |
| Noriel la easybox | 159,99 lei | 9,99 lei | 169,98 lei |

Calcule proprii: diferența este de 8,01 lei față de curier și de 15,01 lei față de locker, în condițiile afișate. Dintr-un singur SKU nu rezultă că MundiShop este în general mai scump. Rezultă o ipoteză de test: la articole cu preț comparabil, transportul și avantajele pachetului pot decide alegerea. Nu reduce prețurile întregului catalog pe baza acestei comparații.

## Note asociate

[[MundiShop_Research_2026-09-23/16_Pagini_destinatie|Pagini de destinație care continuă promisiunea reclamei]] | [[MundiShop_Research_2026-09-23/17_Cos_checkout_livrare|Coșul, checkoutul și livrarea]] | [[MundiShop_Research_2026-09-23/25_Reguli_incredere|Reguli comerciale și de încredere]]

[[MundiShop_Research_2026-09-23/00_Index|Înapoi la index]] | [[MundiShop_Research_2026-09-23/99_Surse|Registrul surselor]]

## În vault-ul nostru (legat de Claude, 24.09)

**La noi, pe date reale:**
- Confirmat live 24.09: footer cu office@krea.ro, link ODR închis, „Translation missing” în galerie.
- Pierderea mare la noi e sesiune → coș (98,5%), nu vizibilă dintr-un audit desktop — vezi [[Cifre cheie MundiShop]].

Legat: [[Site și funnel MundiShop]] · [[Probleme deschise MundiShop]] · [[Pachete cadou]] · [[Pagina de produs pe telefon]] · [[Hartă cunoaștere MundiShop]]
