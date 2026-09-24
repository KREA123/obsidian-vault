---
tip: aplicatie
afacere: MundiShop
status: pauză
actualizat: 2026-09-24
sursa: Claude Code
---
# Aplicația MundiShop

## 1. Pe scurt
Aplicația de Android a magazinului mundishop.ro (seturi LEGO® originale), pentru clienții care cumpără deja de pe site. Rolul principal: **retenția**, adică îi aducem înapoi cu notificări push gratuite. Numele e „MundiShop”, fără „LEGO” în titlu.

## 2. Stadiu (la 2026-09-24)
**Gata și verificat:**
- Instalarea proiectului: `npm install` rulează fără probleme, iar verificarea de cod (`tsc`) trece.
- **Accesul la magazin fără token** (pasul 1), testat pe 21 sept. Aplicația citește direct de pe mundishop.ro:
  - 82 de categorii, 1.037 de produse, prețuri în lei;
  - căutarea, cele mai vândute, noutățile, pagina de produs;
  - coșul și linkul de plată.
- Prețurile ies formatate ca pe site („1.499,00 lei”). Reducerile se calculează corect: din 250 de produse, 7 aveau preț tăiat.
- Recomandările „Ți-ar putea plăcea” merg tot fără token (10 produse înrudite pe produs).
- **Baza aplicației** (23 sept.):
  - bara de jos cu 4 taburi: Acasă, Categorii, Căutare, Coș;
  - iconițele și logo-ul, desenate după specificația de marcă;
  - cardul de produs, prețul cu reducere;
  - ecranele de încărcare, de eroare și de „nu am găsit nimic”.
- Mesajele de eroare pe care le vede clientul au acum diacritice.
- Tabul Coș arată deocamdată „Coșul tău e gol”. Coșul adevărat vine la pasul 3.

**Scris, dar neverificat:**
- Ecranul Acasă și pagina unei categorii. Au fost scrise de agenți înainte de oprire și nu au fost încă verificate, nici în cod, nici în browser.

**Lipsește:**
- Ecranele Categorii, Căutare și pagina de produs (deocamdată au doar câte o linie provizorie).
- Tot ce urmează după pasul 2: coșul adevărat, plata, notificările, contul de client, iconița și ecranul de pornire, publicarea.

**Stricat:** nimic cunoscut. Ecranele scrise de agenți trebuie însă verificate înainte să fie considerate bune.

**Shopify:** nu s-a modificat nimic. S-a doar citit.

## 3. Tehnic
- **Unde e codul:** `P:\aplicatie lego\mundishop-app` (nu e depozit git).
- **Stack:**
  - Expo SDK 57, React Native, TypeScript;
  - expo-router, cu rute care urmează adresele site-ului: `/products/...`, `/collections/...`, `/search`, `/cart`;
  - Shopify Storefront API 2026-07, fără token;
  - Checkout Kit de la Shopify, pentru plată.
- **Identificator Play:** `ro.mundishop.app`.
- **Fișiere importante:**
  - `CLAUDE.md` — regulile proiectului și stadiul la zi;
  - `src/lib/shopify/` — legătura cu magazinul;
  - `src/lib/hooks/` — încărcarea datelor, cu memorie de 5 minute;
  - `src/components/` — piesele comune;
  - `src/app/` — ecranele.
- **Cum se rulează:**
  - Pe PC nu există Android SDK, deci verificarea se face în versiunea web a aplicației, pe dimensiune de telefon: `npx expo start --web` (configurat în `.claude/launch.json`).
  - Plata (Checkout Kit) nu merge în web și nici în Expo Go. Ea se testează doar cu un build pe telefon (`npx expo run:android` sau EAS).
- **Fișierul `.env`** conține doar domeniul magazinului, fără token.

## 4. Decizii luate și de ce
- **Mergem fără token (tokenless).** Varianta cu token ar cere publicarea tuturor produselor pe un canal nou, iar o scriere pe tot catalogul trimite catalogul Meta în re-verificare și oprește campaniile. Fără token nu se creează și nu se publică nimic, deci riscul e zero.
- **Scoase din cererea de produs:** stocul exact și câmpurile „piese” / „vârstă”. Fără token, Shopify refuză câmpurile astea, iar refuzul face să dispară tot produsul, nu doar câmpul.
- **Rutele din aplicație copiază adresele de pe site.** Un link spre mundishop.ro deschis pe telefon, sau o notificare push, duce direct la ecranul potrivit.
- **Fără biblioteci noi** pentru iconițe sau încărcarea datelor: sunt scrise în proiect, simplu, ca aplicația să rămână mică.
- **Construită de la zero, fără builder cu abonament** (decizie de dinainte, din notele proiectului).
- **Doar Android deocamdată.** iOS vine după ce se vede că oamenii instalează.

## 5. Pașii următori, în ordine
1. **Termină pasul 2:**
   - verifică Acasă și pagina de categorie (în cod și în browser);
   - scrie Categorii, Căutare și pagina de produs. Pagina de produs va avea galerie, preț, reducere, descrierea cu imagini și recomandări.
   - Un ecran pe rând, fiecare verificat.
2. **Coșul adevărat** (ținut minte pe telefon) și **plata** prin Checkout Kit.
3. **Notificări push** (OneSignal gratuit sau Firebase) — motivul principal pentru care există aplicația.
4. **Cont de client și istoric comenzi.** Aici e nevoie de token complet, deci și de discuția despre riscul pentru Meta.
5. **Pentru Google Play:** iconiță, ecran de pornire, capturi de ecran, descriere, politică de confidențialitate, formularele cerute de Play. Iconițele actuale sunt tot cele din șablon.
6. **Build final**, testat de Andu pe telefonul lui, apoi publicare.

## 6. Bani
- Nu s-a discutat preț sau venit în conversația asta.
- **Costuri:** niciun abonament nou. Accesul fără token e gratuit, iar pentru notificări varianta avută în vedere e OneSignal gratuit.
- **Alternativa respinsă:** builderele de aplicații Shopify (Apploy / Shopney / Vajro, 49–150 $/lună).

## 7. Probleme deschise și riscuri
- **Câmpurile „piese” și „vârstă”:** nu pot fi citite fără token, deci nu se știe încă dacă cheile din magazin sunt cele corecte (`custom.piese`, `custom.varsta`). Până atunci, pagina de produs nu le afișează.
- **Stocul exact:** nu se vede fără token. Se vede doar „În stoc” sau „Stoc epuizat”.
- **Formularul de ramburs Releasit:** merge doar pe site, nu în aplicație. În aplicație, plata la livrare apare ca metodă simplă din checkout-ul Shopify. Rămâne de decis dacă facem un formular propriu.
- **Tokenul complet (pasul 4 de mai sus):** cere publicarea produselor pe un canal nou. Asta e o scriere pe tot catalogul, cu risc pentru campaniile Meta, deci se face doar cu OK-ul lui Andu, la un moment ales de el.
- **Regula mărcii LEGO:** fără „LEGO” în numele aplicației și fără logo LEGO, altfel există risc de a fi scoasă din Play.

## 8. Lecții
- **Testează cererile reale ale aplicației, nu doar una simplă.** Testul simplu a mers, dar cererea de produs cădea din cauza unui singur câmp refuzat.
- **Un câmp refuzat de Shopify strică tot răspunsul,** nu doar câmpul respectiv.
- **Fără Android pe PC, versiunea web e cea mai rapidă verificare vizuală.** Plata însă se testează doar pe telefon.
- **Când ecranele sunt construite în timp ce serverul de test rulează, lista de adrese a aplicației se poate strica.** Repornirea serverului o repară.
- **Cinci ecrane construite deodată au durat mai mult decât timpul avut** și au fost oprite la jumătate. Mai bine un ecran pe rând, verificat, ca să rămână mereu ceva terminat.

---
Legături: [[Aplicații]] · [[MundiShop]] · [[Roadmap 1 milion €]] · [[Probleme deschise MundiShop]] · [[Reclame Meta MundiShop]] · [[Site și funnel MundiShop]]
