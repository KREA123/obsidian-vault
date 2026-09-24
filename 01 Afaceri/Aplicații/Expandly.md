---
tip: aplicatie
afacere: Aplicații
status: pauză
actualizat: 2026-09-23
sursa: Claude Code
---
# Expandly

## 1. Pe scurt

Expandly e o aplicație publică pentru Shopify, a firmei ARTEMIS DIGITAL SRL. Pune pe paginile de produs și în coș elemente care ajută clientul să cumpere mai mult: reduceri la cantitate, pachete „cumpără împreună”, cadou peste o sumă, coș lateral, bară de livrare gratuită și altele. E gândită pentru magazine Shopify din toată lumea și se vinde pe abonament lunar, prin Shopify App Store. Regula de bază: nimic fals pe magazin, iar prețul afișat pe pagină e exact prețul plătit la finalizarea comenzii.

## 2. Stadiu

**Gata și funcțional (verificat pe magazinul de test):**
- Aplicația rulează live la https://expandly.onrender.com. Pe magazinul de test e publicată versiunea extensiei **expandly-29**.
- Cele 11 elemente:
  - reduceri la cantitate;
  - cumpărate împreună (pachete);
  - cadou la prag;
  - coș lateral;
  - bară de livrare gratuită;
  - estimare de livrare;
  - bară fixă „Adaugă în coș”;
  - rând de garanții;
  - insigne și stoc redus;
  - bară de anunțuri;
  - produse văzute recent.
- **Design nou pe magazin.** Elementele preiau culorile, fontul și colțurile temei și merg și pe teme închise la culoare. Testat pe temele Dawn și Horizon, pe telefon și pe desktop.
- **Română și engleză peste tot:** pe magazin (după limba clientului), în editorul de teme, în admin (după limba contului) și la finalizarea comenzii („Reducere de la 3 buc.”, „Cadou gratuit”).
- **Setare simplă.** Aplicația se deschide pe „Acasă”, cu un ghid în 3 pași și oferte gata făcute la un clic (Moderat, Standard, Generos). Mai are paginile Oferte, Elemente (arată dacă un bloc e pe tema publicată) și Planuri.
- **Planuri Gratuit și Pro.**
  - Codul e gata: aplicația recunoaște planul, blochează elementele Pro pe Gratuit și are pagina Planuri.
  - Magazinele de test primesc Pro gratuit.
  - În Partner Dashboard, planurile `free` și `pro` sunt create, dar sistemul de prețuri nu e încă activat.
- **Logo ales:** „Trepte”, albastru cobalt cu galben. Iconița e urcată de Andu în Partner Dashboard.
- **Distribuție publică** aleasă (definitiv).
- **Listarea în engleză** e parțial completată, în ciornă: textele de bază, categoria, etichetele, limbile, contactele.
- **Verificări automate:** 94 de teste pentru calculul reducerilor, 17 reguli pentru extensia de temă și o verificare a traducerilor. Publicarea extensiei se oprește dacă una pică.

**Terminat pe calculator, dar nepublicat (pus pe pauză pe 23 sept.):**
- verificarea zilnică a planurilor mutată în server (nu mai e nevoie de secret în Render și GitHub);
- cererea automată de recenzie în aplicație (fereastra oficială Shopify, doar după ce comerciantul are oferte care merg);
- textele finale ale listării, gata de copiat;
- imaginile listării (4 bucăți, 1600×900), refăcute fără marca Shopify pe produse;
- ecranele adminului în engleză, pentru filmuleț.

**Lipsește:**
- montajul filmulețului demonstrativ pentru recenzenți;
- verificarea independentă a lucrului de mai sus, apoi publicarea lui;
- completarea listării (imagini, filmuleț, instrucțiuni pentru recenzent), apoi „Submit for review”.

**Stricat:** nimic cunoscut acum. Ultima eroare mare (ofertele Pro nu apăreau pe magazin) a fost reparată și verificată pe 21 sept.

## 3. Tehnic

- **Codul:** `P:\apps\conversion-suite`. Depozit GitHub privat `KREA123/expandly`.
- **Publicarea codului** se face doar cu `node scripts/push-snapshot.mjs "mesaj"`, nu cu `git push`: istoricul local vechi conține date care nu trebuie urcate. Fiecare publicare repornește serverul de pe Render (circa 6 minute).
- **Publicarea extensiei** și a funcției de reduceri în Shopify: `npm run deploy`, care rulează întâi verificările.
- **Din ce e făcută:**
  - aplicație Shopify (React Router, componentele Polaris);
  - extensie de temă (Liquid, JavaScript, CSS);
  - funcție Shopify pentru reduceri (TypeScript), care calculează în bani întregi (cenți);
  - baza de date Postgres.
- **Găzduire gratuită:**
  - Render: serverul, pornit din Dockerfile;
  - Neon: baza de date;
  - UptimeRobot: verifică adresa `/healthz` la 5 minute, ca serverul să nu adoarmă.
- **Verificări:** `npm run build:ext`, `npm run verify`, `npm run test:fn`, `npm run typecheck`, `npm run build`, `node scripts/check-admin-i18n.mjs`.
- **Previzualizare locală** (Dawn și Horizon, engleză și română, telefon și desktop): `npm run preview`. Acum imită și felul în care Shopify împachetează fragmentele de cod.
- **Magazin de test:** dexters-laboratory (magazin de dezvoltare), cu temele „Dawn expandly test” și Horizon. Vitrina are parolă, pe care o introduce doar Andu.
- **Documente în depozit:**
  - `STARE.md`: starea detaliată;
  - `LAUNCH.md`: pașii lansării;
  - `LISTING.md`: textele listării;
  - `README-DEV.md`: instrucțiuni tehnice;
  - `PRIVACY.md`: politica de confidențialitate, servită la /privacy.
- **Brand:** `brand/final` (iconița 1200×1200, logo, banner) și `brand/listing` (imaginile listării).

## 4. Decizii luate și de ce

- **Totul gratuit (Render, Neon, UptimeRobot).** Andu vrea zero investiție. Fly.io a fost respins pentru că cere card.
- **Planuri:**
  - Gratuit: insigne, rând de garanții, estimare de livrare, bară fixă, bară de livrare gratuită, bară de anunțuri, produse văzute recent.
  - Pro: 14,99 $ pe lună, cu primele 7 zile gratuite. Adaugă reducerile la cantitate, pachetele, cadoul și coșul lateral.
  - Fără plafon de vânzări, ca diferență față de concurenți.
- **Presetările de oferte:**
  - Moderat: 2 buc. −5%, 3 buc. −10%;
  - Standard: 2 buc. −10%, 3 buc. −15%;
  - Generos: 2 buc. −10%, 3 buc. −20%.
- **Adminul în română, cu „tu”** și diacriticele corecte (ș, ț).
- **„Proof” (testare A/B) scos din aplicație,** pentru că încă nu există. Nu arătăm funcții inexistente.
- **Fără permisiuni noi** cerute magazinelor, ca instalarea să rămână simplă.
- **Fără oferte pe carduri cadou și pe produse epuizate.** Shopify nu reduce cardurile cadou, deci oferta ar fi mințit clientul.
- **Distribuție publică,** ca aplicația să poată intra în App Store și să ceară abonament.
- **Logo „Trepte”, albastru.** Treptele sugerează nivelurile de reducere (1, 2, 3 bucăți).
- **Listare doar în engleză.** Româna nu e limbă a App Store, așa că e trecută doar la „Languages”.
- **Numele din listare: „Expandly Bundles & Upsells”, provizoriu.** „Expandly” simplu e deja luat de altă firmă. Andu ține la numele Expandly.
- **Filmulețul găzduit pe serverul aplicației,** ca să nu fie nevoie de YouTube.

## 5. Pașii următori, în ordine

1. **Repornirea lucrului oprit** (fac eu): montajul filmulețului, verificarea independentă, publicarea pe Render și în Shopify.
2. **Completarea listării** (fac eu): textele finale, cele 4 imagini, filmulețul, instrucțiunile pentru recenzent. Apoi salvare.
3. **Andu:**
   - creează cheia Partner API (Partner Dashboard → Settings → Partner API clients, permisiunea „Manage apps”) și o pune direct în Render, cu variabilele din `LAUNCH.md`;
   - completează Payouts: cont Hyperwallet pe firmă, cont bancar real, datele fiscale;
   - verifică dacă prețul Pro e 14,99 (lista afișa „$15/month”);
   - șterge un eventual plan privat creat din greșeală.
4. **Activarea sistemului de prețuri** („Enable Shopify App Pricing”) și testul planurilor pe magazinul de test, unde Pro e gratuit.
5. **Pe pagina de trimitere:** rularea „automated checks” și bifa „My app won't use customer data”.
6. **Andu:** plătește taxa de 19 $ și spune „da”, apoi „Submit for review”.
7. **După aprobare:** strângem recenzii (cererea automată din aplicație), urmărim instalările și trecerile la Pro.

## 6. Bani

- **Prețul:** plan Gratuit și plan Pro de 14,99 $ pe lună, cu 7 zile gratuite. Magazinele de test au Pro gratuit.
- **Cum vin banii:** Shopify încasează abonamentele de la magazine și plătește lunar, în dolari, prin Hyperwallet, într-un cont bancar real (Payoneer nu e acceptat). După lansare, aplicația merge singură.
- **Comisioanele Shopify:**
  - 0% la primul 1 milion $ câștigat (socotit de la 1 ian. 2025);
  - 15% peste suma asta;
  - 2,9% taxă de procesare la fiecare plată.
- **Costuri:** o taxă unică de 19 $ pentru înregistrarea în App Store, plătită de Andu cu cardul. Găzduirea e gratuită.
- **Taxele pe venit** le stabilește contabilul firmei.
- **Concurenți (verificat pe 13 sept.):**
  - Kaching Bundles: 14,99 / 29,99 / 59,99 $ pe lună, cu plafon după venitul adus;
  - Fast Bundle: 19 / 49 / 139 $ pe lună, cu plafon după vânzări.
- **Cerința lui Andu:** aplicația să aducă bani fără implicarea lui. Din partea lui rămân doar pașii care țin de bani, identitate și chei de acces (vezi punctul 5).

## 7. Probleme deschise și riscuri

- **Numele** „Expandly Bundles & Upsells” poate fi respins la recenzie, pentru că începe cu numele altei aplicații. Rezervă verificată: „Trepta”.
- **Venitul nu e garantat.** Categoria e aglomerată, cu concurenți care au mii de recenzii. Instalările depind de poziția în App Store și de recenzii.
- **Fără cheia Partner API,** magazinele care plătesc Pro sunt tratate ca Gratuit.
- **Limitele serverelor gratuite:** Render adoarme fără UptimeRobot, iar Neon dă 100 de ore de calcul pe lună.
- **Lucrul nepublicat** stă pe calculator, necomis, până la repornire.
- **Parola bazei Neon** a apărut într-o captură de ecran. Trebuie schimbată, dacă nu s-a făcut.
- **Pe magazinul de test,** rândul de garanții trebuie bifat din nou în editorul de teme (s-a schimbat numele bifei).
- **Recenzia Shopify** poate dura și poate cere modificări.

## 8. Lecții

- **Previzualizarea locală nu e Shopify.** Două erori au arătat bine local, dar au stricat ofertele Pro pe magazin:
  - Shopify împachetează răspunsul fragmentelor de cod în comentarii HTML;
  - Shopify nu compară două date scrise ca text.

  Se testează mereu și pe magazinul real.
- **Particularități Shopify de ținut minte:**
  - nu acceptă acolada `}` în interiorul `{{ }}`;
  - traducerile sunt deja escapate, iar a doua escapare afișa „You&#39;ve”;
  - metacâmpurile se văd pe magazin doar cu o definiție cu acces pe vitrină;
  - funcția de reduceri are o limită de complexitate (30).
- **Tema Dawn:**
  - ascunde elementele goale, deci barele de progres nu se vedeau;
  - butonul „Add to cart” are culoarea paginii, deci culoarea aplicației se alege după contrast.
- **Numele se verifică în App Store înainte să construiești brandul pe el.**
- **Înainte de orice serviciu „gratuit”,** se verifică dacă cere card.
- **Pe configurația de producție nu se rulează `shopify app dev`:** mută aplicația live pe calculatorul local.
- **Shopify interzice marca sa în imaginile listării,** chiar și pe un produs din fundal.

---
Legături: [[Aplicații]] · [[MundiShop]] · [[KREA]] · [[Roadmap 1 milion €]]
