---
tip: finanțare
proiect: SOUL-PoC
actualizat: 2026-09-25
sursa: Anexa 10 — Grila ETF PoC 1.1 (versiunea 03.06.2026); Ghid §8.4–8.5
---

# 02 · Punctajul ETF — cum luăm maximul și cât e realist

## Regulile jocului
- **Maximum 100 de puncte**: Contribuția la OS 1.1 = 40 · Calitatea documentației = 37 · Capacitatea de implementare = 9 · Sustenabilitate și teme orizontale = 14.
- **Pragul minim de calitate: 70 de puncte.** Sub 70 proiectul e respins (§3.1 p. 22; §8.5 p. 80).
- **Selecția se face în ordinea descrescătoare a punctajului, până se epuizează bugetul** (§8.1 p. 77; §8.4 p. 80). Bugetul apelului e **5.000.000 €** (§3.3 p. 22). La ~190 k€ pe proiect, se finanțează **~25–30 de proiecte**. Cei care au trecut de 70 dar nu încap intră pe lista de rezervă.
- **Punctajul care câștigă e necunoscut.** În apelurile competitive de acest tip, ultimul proiect finanțat are adesea 85–90+ puncte [E]. **Ținta noastră e ≥ 92.**
- **Clarificările NU pot crește punctajul** (Grila, final). Tot ce aduce puncte trebuie să fie în dosar **la depunere**.
- **Departajarea la punctaj egal:** 1) Calitate (secțiunea 2) → 2) Relevanță (secțiunea 1) → 3) Sustenabilitate și teme orizontale (secțiunea 4) → 4) subcriteriul 1.2 → 5) **data depunerii** (§8.4 p. 80). Deci depunem devreme.
- **Corelare:** Anexa 3 și Anexa 16 avertizează că cererile de clarificări pentru necorelări „pot conduce la depunctarea proiectului”. Totul se copiază din `03-NUCLEU-PROIECT.md`.

---

## Criteriu cu criteriu

### 1. Contribuția la OS 1.1 — 40 p.

| Sub | Max | Ce cere grila | Cum luăm maximul (dovezi concrete de atașat) | Estimare realistă |
|---|---|---|---|---|
| **1.1** RIS3 BI (≥ 2 domenii) | 5 | argumentare explicită, consecventă în CF + Anexa 3 („Piață”, „Tehnologie”) + Anexa 16 (încadrare tematică) | **TIC + Sisteme și Componente Inteligente**, fiecare legat de obiective/activități/rezultate concrete (`03-NUCLEU` §2). Aceeași formulare în cele trei documente. Citarea subdomeniilor exacte din strategia RIS3 BI | **5** |
| **1.2** Relevanța problemei | 15 | problemă demonstrată la nivel **european/internațional** cu surse verificabile (studii, statistici, regulamente, literatură); diferențiere tehnologică **măsurabilă**; **nu** se punctează afirmațiile generice despre AI/IoT | Problema pe patru axe (cloud-dependence și „bricking”, latență, text pe ecrane rotunde, reparabilitate), cu dovezi: regulamentele UE (2023/1542 art. 11, 2024/1799, 2024/1689, 2022/30); cazurile Humane/Moxie/Rabbit cu link; datele de piață (Plaud, Fuzozo, campanii Kickstarter); benchmark-ul celor 24 de competitori (research 11) ca tabel anexat; ≥ 3 lucrări științifice; tabelul N1–N5 „ce e nou” cu cifre-țintă; dovezile TRL 3 | **10–15** (ținta 15; riscul: evaluatorul vede „încă un gadget AI” și dă 10 pentru relevanță doar națională) |
| **1.3** Sediu/punct de lucru în BI înregistrat ≤ 31.12.2025 | 5 | certificat constatator emis cu ≤ 30 de zile înainte de depunere; data înregistrării sediului/punctului de lucru | Sediul ARTEMIS din București. Confirmăm pe certificat că data înregistrării e ≤ 31.12.2025 (dacă sediul a fost mutat după această dată: 2 p.) | **5** (❓ de confirmat) |
| **1.4** Publicare open-access | 10 | 10 p. = **OA cu peer-review**, minim trimiterea în perioada de implementare; linie bugetară pentru publicare **sau** soluție gratuită concretă; publicarea pe site-ul propriu **nu** contează; regula „patent first, publish later” e acceptată dacă e coerentă în calendar | Linia 21 (APC ≈ 3,4 k€); **revista numită** (ex. MDPI *Electronics* / IEEE *Access*) cu captura paginii de APC; plus preprint Zenodo; calendar: IP la L5–L6 → trimitere ≤ L20; menționat în CF „Activități”, „Buget”, în Anexa 16 (planul de diseminare) și în Anexa 3 (§6.2) | **10** |
| **1.5** Economie circulară în soluție | 5 | principiul EC aplicat **direct produsului**, descris explicit și demonstrabil tehnic | Baterie înlocuibilă de utilizator (Reg. 2023/1542 art. 11), șuruburi Torx, carcasă monomaterial Al reciclabilă, OTA, funcționare fără server (anti-„bricking”), piese de schimb 5 ani; **protocolul P10** măsoară înlocuirea în ≤ 5 min (`03-NUCLEU` §12) | **5** |
| **Subtotal** | **40** | | | **35–40** |

### 2. Calitatea documentației — 37 p.

| Sub | Max | Ce cere grila | Cum luăm maximul | Estimare |
|---|---|---|---|---|
| **2.1a** Nevoia de piață + grupul țintă | 2 | explicit, corelat, cu surse | Anexa 3 §III cu date de piață citate (research 01, 04, 11), segmente cuantificate, grupul țintă din `03-NUCLEU` §17 | 2 |
| **2.1b** Etapele de realizare în implementare | 2 | clar | tabelul A0–A8 + Gantt + milestone-uri | 2 |
| **2.1c** Poziționare competitivă (prețuri, canale, model de business, promovare) + avantaje | 2 | – | matricea competitorilor + harta de poziționare (research 11), prețuri 349/199–299 €, canalele, modelul | 2 |
| **2.1d** IP deja protejat **sau** demersuri concrete până la final | **5** | în implementare se cere dovada depunerii | Plan IP cu pași, termene, costuri (linii 19–20), consilier PI; **ideal**: căutarea TMview făcută și, dacă e posibil, marca depusă deja prin SME Fund înainte de depunere | **5** |
| **2.1e** Riscuri + mecanisme, **inclusiv eșecul de cercetare** | 4 | – | tabelul R1–R12 cu probabilitate/impact/măsuri; poarta IE2; Anexa 17; regula activelor pentru TRL 5 după poartă | 4 |
| **2.1 total** | **15** | P = integral · P/2 = parțial · 0 | fiecare afirmație cu sursă sau trimitere la anexă | **13–15** |
| **2.2a** Încadrarea corectă a liniilor + praguri | 2 | 1 linie greșită = −1; > 1 = 0 | fiecare linie cu categoria MySMIS exactă (`03-NUCLEU` §10.1); 10 % conexe și 7 % indirecte verificate; reverificare pe **Anexa 20** finală | 1–2 |
| **2.2b** ≥ 2 surse pentru **toate** liniile nesalariale | 3 | 1 linie fără surse = 1,5; > 1 = 0 | 2 surse pe fiecare linie (`01-DOCUMENTE` §C); **notă justificativă de sursă unică** pentru taxele EUIPO și, dacă e cazul, pentru serviciul CDI al universității | 1,5–3 |
| **2.2c** Salarii ≤ HG 1188/2022 + L. 183/2024 | 2 | 1 persoană peste = 1; > 1 = 0 | tarife sub plafoane cu marjă (34/35, 25/35, 12/15, 18/50 €/h); categoria HG scrisă în fișa de post; CAM separat | 2 |
| **2.2 total** | **7** | | | **5–7** |
| **2.3a** Problema, relevanța, obiectivele coerente cu ipoteza | 3 | – | ipoteza „dacă…, atunci…” cu cifre (`03-NUCLEU` §3.2), O1–O4 legate de H1–H5 | 3 |
| **2.3b** TRL de pornire argumentat prin dovezi verificabile | 2 | declararea simplă nu ajunge; nu se acceptă TRL bazat pe intenții | **Raportul de laborator TRL 3 pe placa 2.8C** (X1–X8) + 55/49 teste + simulator + video datat + hash git | **2** (doar dacă facem X1–X8; altfel 1) |
| **2.3c** Activități adecvate TRL 4–5, detaliate metodologic | 3 | protocoale, criterii, mediu de testare | tabelul P1–P11 cu metodă, baseline, prag TRL 4, prag TRL 5 și definiția mediului relevant | 3 |
| **2.3d** Resurse pentru TRL superior (infrastructură, laboratoare, afilieri) | 3 | „afirmațiile generale nesusținute de documente nu sunt suficiente” | **scrisori/acorduri** de la un laborator EMC/RF și de la o organizație de cercetare (UPB/IMT/ICI); oferte; fotografii ale bancului de lucru | 1,5–3 |
| **2.3e** Plan realist, cu termene și livrabile măsurabile | 2 | – | Gantt pe luni, dependențe, M1–M3, IE1–IE3, livrabilele L1.1–R5 cu responsabil | 2 |
| **2.3f** Ipoteze, indicatori științifici, rezultate cuantificabile | 2 | fără „îmbunătățire/optimizare” fără unități | H1–H5, P1–P11 cu unități și valori-țintă | 2 |
| **2.3 total** | **15** | | expertul trebuie să **semneze** un raport pe care l-a înțeles și asumat | **12,5–15** |
| **Subtotal** | **37** | | | **30–37** |

### 3. Capacitatea de implementare — 9 p.

| Sub | Max | Ce cere grila | Cum luăm maximul | Estimare |
|---|---|---|---|---|
| **3.1** Echipa nominalizată **la depunere** | 5 | (i) coordonator: doctor **sau** ≥ 5 ani în domeniu **sau** ≥ 2 proiecte CDI conduse **și** (ii) ≥ 1 expert cu studii superioare în domeniu și ≥ 2 ani (sau ≥ 1 publicație WoS/Scopus). Doar una dintre condiții = 3 p. | **Recrutăm înainte de depunere**: coordonator embedded ≥ 5 ani (ideal cadru didactic UPB cu doctorat) + inginer embedded ≥ 2 ani. CV Europass, diplome, adeverințe, declarații de disponibilitate | **3–5** (punctul cel mai slab azi) |
| **3.2a** Experiența CDI a firmei | 2 | dovezi documentare, nu declarații (prototipuri, rapoarte tehnice, validări, livrabile) | Raport tehnic „Activitatea CDI SOUL 2026” cu anexe: istoric git datat, rapoartele celor 55 + 49 de teste, clipurile simulatorului, prototipul SoulOS, raportul de laborator TRL 3, research 01–12 | **1–2** (risc: evaluatorul poate cere un contract/proiect „oficial”) |
| **3.2b** Încă un membru (în afara celor de la 3.1) cu experiență CDI | 2 | CV, publicații, proiecte | Andu (documentat) **sau** un al doilea inginer cu proiecte CDI | 1–2 |
| **Subtotal** | **9** | | | **5–9** |

### 4. Sustenabilitate și teme orizontale — 14 p.

| Sub | Max | Ce cere grila | Cum luăm maximul | Estimare |
|---|---|---|---|---|
| **4.1** Strategie post-PoC (toate cele 5 elemente, cumulativ) | 5 | (i) traseul TRL; (ii) modelul de business; (iii) sursele de finanțare; (iv) calendar **≥ 5 ani**; (v) legătura cu rezultatul PoC | tabelul din `03-NUCLEU` §16 (Founders 00 → Batch 1/CE → Standard → Platforma), surse de finanțare numite, proiecția pe 5 ani cu ipoteze | **5** (2,5 dacă proiecția e slabă) |
| **4.2** ≥ 2 acorduri/scrisori valide, de la entități distincte | 4 | **toate cele 7 elemente**, datate cu ≤ 6 luni înainte de depunere; altfel nu se iau în calcul | 3–4 scrisori (una de rezervă) după **modelul din `04-CE-TREBUIE-SA-FACA-ANDU.md`**: un retailer/distribuitor, o firmă de software care folosește Claude Code (pilot), o organizație de cercetare/living lab | **4** |
| **4.3a** Tânăr ≤ 24 ani, înmatriculat în învățământul superior, în CD | 3 | dovezi: adeverință de student, CIM, fișă de post | student UPB angajat part-time, cu documentele atașate | **3** |
| **4.3b** ≥ 1 măsură suplimentară pentru egalitate de șanse | 2 | conform Metodologiei ADR BI pentru principiile orizontale | panelul TRL 5 cu ≥ 40 % femei + persoane cu dizabilități + testarea accesibilității cu o asociație; politica internă anexată | **2** |
| **Subtotal** | **14** | | | **12–14** |

---

## Estimarea totală

| Scenariu | 1 (40) | 2 (37) | 3 (9) | 4 (14) | **Total** | Condiții |
|---|---|---|---|---|---|---|
| **Maxim** | 40 | 37 | 9 | 14 | **100** | totul făcut perfect, evaluatori favorabili |
| **Realist (dacă executăm `04-CE-...`)** | 37–40 | 33–36 | 7–9 | 13–14 | **≈ 90–99** (cel mai probabil ~92) | expert bun, echipă nominalizată, 2 surse pe fiecare linie, dovezi TRL 3 pe placă |
| **Dacă lipsesc echipa și dovezile TRL 3** | 35 | 29 | 3–5 | 12 | **≈ 79–81** | trece de 70, dar probabil **nu intră în bugetul apelului** |
| **Pesimist** | 30 | 25 | 3 | 9,5 | **≈ 67–70** | 1.2 = 5, surse lipsă, fără scrisori valide → **risc de respingere** |

**Concluzia sinceră:** proiectul poate trece ușor de pragul de 70. **Câștigul real** (intrarea în primele ~25–30 de proiecte) depinde de patru lucruri pe care le controlăm: **(1) dovezile TRL 3 pe placa fizică, (2) un expert solid, (3) coordonatorul + inginerul nominalizați la depunere, (4) 2 surse pe fiecare linie.** Fiecare lipsă costă 2–5 puncte, iar la o competiție strânsă 5 puncte fac diferența.

## Ce NU putem controla
1. **Numărul și calitatea celorlalte proiecte** și, deci, punctajul-limită de finanțare.
2. **Subiectivitatea evaluatorilor** la 1.2 (european vs. național), 2.1 (P vs. P/2), 2.3 și 4.1.
3. **Ghidul final**: praguri, Anexa 20 (plafoane pe categorii), calendarul, schema de minimis, curs.
4. **Fereastra de depunere** (poate fi scurtă) și încărcarea MySMIS în ultimele zile.
5. **Cursul InforEuro** la semnare (plafonul de 200 k€ și cel de minimis).
6. **Durata evaluării**: dacă trece în 2027, se schimbă anii de referință IMM și se suspendă procesul până la depunerea bilanțului (§8.4 p. 79).
7. Disponibilitatea reală a persoanelor recrutate după contract.
8. Cum evaluează evaluatorul „experiența CDI a firmei” (3.2a) pentru o agenție de marketing/IT fără proiecte CDI finanțate anterior.

## Ce maximizează șansele (în ordinea impactului)
1. Dovezi TRL 3 pe hardware real (2.3b + 1.2 + credibilitate generală).
2. Echipa nominalizată la depunere (3.1 = 5, 3.2b = 2).
3. Surse complete pentru buget (2.2b = 3) + încadrare perfectă (2.2a = 2).
4. Scrisori de intenție cu toate cele 7 elemente (4.2 = 4).
5. Studentul + măsura suplimentară (4.3 = 5).
6. APC bugetat + revista numită (1.4 = 10).
7. Dosar perfect corelat, depus **în primele zile** ale ferestrei.
