---
title: "Cum iei decizii cu puține date"
verified_at: 2026-09-23
version: "1.0"
status: cercetare_si_propuneri
tags: [mundishop, ecommerce, meta-ads, romania]
sources: [S22]
---

# Cum iei decizii cu puține date

## Nu confunda livrarea algoritmică cu un experiment

Două reclame în același ad set nu primesc neapărat trafic comparabil. Rezultatul lor este util operațional, dar nu este automat un A/B test randomizat. Pentru o concluzie cauzală, folosește un instrument și un design de test adecvate. Materialul Meta despre A/B și lift este resursa de pornire. [S22]

La trafic mic, prioritatea este să repari erori evidente, să validezi oferta și să obții observații suficiente. Un test multivariat cu șase modificări simultane poate consuma săptămâni fără un răspuns clar. Dacă nu ai putere statistică, marchează rezultatul exploratoriu.

## O regulă de risc pentru zero comenzi

EXEMPLU matematic: într-un model simplificat în care numărul de comenzi urmează o distribuție Poisson și CPA real este CPA țintă, probabilitatea de a vedea zero comenzi după o cheltuială egală cu 1 × CPA este aproximativ 37%; după 2 × CPA, 14%; după 3 × CPA, 5%. Formula este exp(-cheltuială / CPA țintă).

Modelul presupune performanță stabilă, observare completă și evenimente aproximativ independente. Publicitatea reală nu respectă perfect aceste condiții. Prin urmare, pragul de 3 × CPA este o posibilă alarmă de risc, nu o lege Meta sau un test care garantează că o reclamă este slabă.

PROPUNERE de decizie: dacă un test a atins limita de pierdere convenită și nu are comenzi după fereastra normală de întârziere, oprește sau investighează. Verifică întâi măsurarea, destinația și oferta. Nu aștepta o săptămână să descoperi că pagina nu se deschide, dar nici nu opri un set scump după câteva clicuri.

## Criterii de păstrare și scalare

Păstrează o ofertă când contribuția după reclame este pozitivă pe date suficient de mature, rezultatul nu depinde de una sau două comenzi atipice și stocul o poate susține. Pentru un produs scump, verifică distribuția valorilor; o singură comandă poate schimba mult media.

Scalează prin creșteri măsurate ale bugetului sau prin extinderea ofertelor și materialelor validate, în pași pe care fluxul de numerar îi permite. Un interval precum 10-20% poate fi folosit ca ritm intern de încercare, dar nu garantează stabilitate și nu este regulă obligatorie Meta. Modifică un factor important odată și așteaptă cât cere întârzierea conversiilor.

Pregătește o condiție de revenire: pierdere cumulată peste limită, contribuție sub țintă după maturizarea cohortelor, lipsă de stoc, creștere a refuzurilor ori probleme de livrare. Ia în calcul că marja se poate schimba când vinzi alt mix de produse.

## Note asociate

[[MundiShop_Research_2026-09-23/06_Economie_comanda|Economia unei comenzi înainte de setarea bugetului]] | [[MundiShop_Research_2026-09-23/12_Raportare_KPI|Raportarea zilnică și săptămânală]] | [[MundiShop_Research_2026-09-23/19_Experimente|Experimentele cu cea mai mare utilitate]]

[[MundiShop_Research_2026-09-23/00_Index|Înapoi la index]] | [[MundiShop_Research_2026-09-23/99_Surse|Registrul surselor]]

## În vault-ul nostru (legat de Claude, 24.09)

**La noi, pe date reale:**
- Aceeași matematică ca regula noastră: la ~1 comandă/zi, o zi fără comenzi ≈ 34–37% → verdict la 7–14 zile.
- Regula noastră de buget: +20% doar după 3 zile sub prag.

Legat: [[Cum rulăm un experiment]] · [[Reguli de lucru pe reclame]] · [[JARVIS]] · [[Lecții MundiShop]] · [[Hartă cunoaștere MundiShop]]
