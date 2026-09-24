---
title: "Economia unei comenzi înainte de setarea bugetului"
verified_at: 2026-09-23
version: "1.0"
status: cercetare_si_propuneri
tags: [mundishop, ecommerce, meta-ads, romania]
sources: [S07]
---

# Economia unei comenzi înainte de setarea bugetului

## Definiții de lucru

Contribuția înainte de reclame este venitul efectiv al unei comenzi minus costurile variabile necesare acelei comenzi. Nu este profitul net al firmei: chiria, salariile fixe, contabilitatea și alte costuri generale trebuie acoperite din ce rămâne.

Pentru un comerciant înregistrat în scopuri de TVA, folosește o bază coerentă de venituri și costuri fără TVA deductibil. Site-ul MundiShop se prezintă drept neînregistrat în scopuri de TVA; confirmă situația cu contabilul înainte de calcul. Pentru un neplătitor, TVA nerecuperabil din achiziții este cost. Nu împărți automat încasările la o cotă TVA. [S07]

Modelul recomandat folosește costul publicității efectiv suportat de firmă, inclusiv orice taxe nerecuperabile aplicabile, stabilite cu contabilul. Diferențele dintre factura Meta, Ads Manager și extrasul bancar se reconciliază.

Contribuție comandă păstrată = venit produse după reduceri + transport încasat - cost produse - curier - ambalare - procesare plată - alte costuri variabile.

Definim q = proporția comenzilor plasate care rămân livrate, plătite și nereturnate după o perioadă suficientă. Costul mediu al comenzilor care nu rămân valide trebuie calculat separat; include refuzuri, anulări, retururi și eventuale pierderi de produs, în funcție de caz.

Contribuție așteptată pe comandă plasată = q × contribuție comandă păstrată - (1 - q) × pierdere medie comandă nereținută.

CPA maxim pe comandă plasată = contribuție așteptată pe comandă plasată - contribuția dorită după reclame.

## Exemplu numeric ipotetic

| Element | Valoare |
|---|---:|
| Produse încasate după reduceri | 300 lei |
| Transport încasat | 25 lei |
| Cost de achiziție produse | 210 lei |
| Cost curier | 25 lei |
| Ambalare | 4 lei |
| Cost procesare și alte variabile | 6 lei |
| Contribuție pe comandă păstrată | 80 lei |
| Proporție q | 90% |
| Pierdere medie pe comandă nereținută | 20 lei |
| Contribuție așteptată pe comandă plasată | 70 lei |
| Contribuție dorită după reclame | 20 lei |
| CPA țintă pe comandă plasată | 50 lei |

Calcul: 300 + 25 - 210 - 25 - 4 - 6 = 80. Apoi 0,90 × 80 - 0,10 × 20 = 70. După o rezervă de 20 lei, CPA țintă este 50 lei. La o cheltuială de 150 lei pe zi și un CPA efectiv de 50 lei, ar rezulta matematic 3 comenzi plasate pe zi în medie. Acesta este un scenariu de planificare, nu o estimare a rezultatelor reale.

## De ce reducerile pot face reclamele neprofitabile

În exemplul de mai sus, o reducere de 10% din produs scade încasarea cu 30 lei. Dacă celelalte costuri rămân aceleași, contribuția pe comandă păstrată scade la 50 lei, iar contribuția așteptată pe comandă plasată la 43 lei. Cu aceeași rezervă de 20 lei, CPA țintă devine 23 lei. Reducerea a micșorat spațiul pentru reclamă de la 50 la 23 lei.

Transportul gratuit reduce contribuția numai cu suma pe care o suportă suplimentar magazinul; nu dubla costul curierului dacă era deja inclus. Un breloc cadou se evaluează la costul de achiziție și la costurile aferente, nu la prețul lui de vânzare. Reducerea, cadoul și transportul gratuit nu se cumulează fără recalcul.

## ROAS și limitele lui

ROAS = valoarea vânzărilor atribuite / cheltuiala de reclamă. Dacă valoarea raportată per comandă este 300 lei, iar CPA țintă este 50 lei, ROAS țintă echivalent este 6. Dacă integrarea transmite 325 lei incluzând transportul, valoarea echivalentă este 6,5. Nu compara praguri construite pe baze diferite.

Formula prescurtată ROAS de echilibru = 1 / marja de contribuție este valabilă doar când venitul, costurile și populația de comenzi sunt definite consecvent. Pentru ramburs și retururi, modelul pe comandă este mai sigur. Nu număra de două ori costul refuzurilor, o dată în q și încă o dată integral într-o rezervă separată.

LTV intră în calcule numai după ce cohortele demonstrează contribuția comenzilor repetate. Până atunci, dimensionează achiziția pe prima comandă. Venitul pe viață al unui client nu este profitul lui pe viață.

## Note asociate

[[MundiShop_Research_2026-09-23/01_Obiectiv_profit_anual|Modelul obiectivului de un milion de euro profit anual]] | [[MundiShop_Research_2026-09-23/08_Oferte_AOV|Oferte și creșterea valorii coșului]] | [[MundiShop_Research_2026-09-23/12_Raportare_KPI|Raportarea zilnică și săptămânală]] | [[MundiShop_Research_2026-09-23/20_Decizii_scalare|Cum iei decizii cu puține date]]

[[MundiShop_Research_2026-09-23/00_Index|Înapoi la index]] | [[MundiShop_Research_2026-09-23/99_Surse|Registrul surselor]]

## În vault-ul nostru (legat de Claude, 24.09)

**La noi, pe date reale:**
- Formula aplicată pe cifrele noastre: CPA maxim ≈ 47 lei (0 profit) / ~37 lei (rezervă 10) la coșul mediu; azi ~237 lei.
- Pe benzi de preț, vezi tabelul din [[Hartă cunoaștere MundiShop]]: doar seturile peste ~600 lei suportă costul Meta actual (188 lei).

Legat: [[Prețuri și marje MundiShop]] · [[Plan MundiShop pe profit]] · [[Cifre cheie MundiShop]] · [[Hartă cunoaștere MundiShop]] · [[Hartă cunoaștere MundiShop]]
