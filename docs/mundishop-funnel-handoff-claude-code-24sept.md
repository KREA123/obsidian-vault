# MundiShop.ro — handoff funnel pentru Claude Code (24 sept 2026)

Scop: **mai multe comenzi din același trafic**, pe tot drumul reclamă → pagină de produs → coș → checkout → plată → după comandă. Site-ul trebuie să fie mai bine făcut ca funnel și ca execuție (mobil, încredere, viteză), fără să strice campaniile.

## 0. Reguli fixe (nu se negociază)
1. **Nu se scriu date de produs** (titlu, descriere, preț, imagini, taguri, metafields, colecții automate care schimbă produse). Orice scriere pe produse trimite catalogul Meta în re-verificare și oprește reclamele. Lucrăm doar în temă (Liquid/CSS/JS/locale/secțiuni) și în setări.
2. **Nu se plasează comenzi de test.** Checkout-ul se verifică în previzualizare până la pasul de plată, fără a finaliza.
3. **Nu se ating campaniile Meta/Google** (Andu decide separat, după verdictul campaniei „Teme" din 30.09).
4. **O schimbare (sau un pachet cu o singură metrică) odată**, cu data notată; 14 zile de măsurare; fără alte modificări pe aceeași etapă între timp.
5. **Fără recenzii inventate, fără poze „de la clienți" generate.** Interzise (Legea 148/2023 / Directiva 2005/29 Anexa I pct. 23b–23c, amenzi ANPC) și distrug încrederea pe care o construim. Recenziile vin de la clienți reali (secțiunea 5).
6. Site-ul nu trebuie să „arate a AI": fără carduri generice cu bife, fără texte umflate, fără superlative. Ton direct, românesc, concret. Repere de UX: brickdepot.ro, qwertykey.ro (doar ca reper de calitate, nimic copiat).
7. Mobil întâi: 96% din sesiuni sunt de pe telefon, majoritatea din browserul din Facebook/Instagram. Verificare la 390×660 și 375×812.
8. Google Pay / Apple Pay rămân peste tot (decizia lui Andu). Livrare: 25 lei fix, fără prag gratuit (refuzat). Nu se schimbă prețuri.

## 1. Contextul tehnic
- Shopify, magazin `krea-9549` (admin: admin.shopify.com/store/krea-9549), domeniu mundishop.ro. Tema live: **ID 204842565964**, numită „Copie a Mundi — SEO colectii (H1 + descriere)", schema „Mundi" 1.0.0. Fișiere cheie: `layout/theme.liquid`, `sections/main-product.liquid`, `snippets/mundi-buybar.liquid` (bara nouă `#mbb`), un snippet mai vechi cu `#buybar` (de găsit cu grep „buybar"), `snippets/mundi-mega-menu.liquid`, `templates/index.json`, `locales/ro.json`, `config/settings_data.json` (app embeds).
- ~1.100 produse LEGO + accesorii; furnizor Clever Toys; stoc sincronizat imperfect.
- Plăți: Shopify Payments (card, Apple Pay, Google Pay), Shop Pay dezactivat, PayPal inactiv, metoda manuală „Numerar la livrare (COD)". **83% din comenzi sunt ramburs**, 17% card.
- Livrare: Cargus, 25 lei fix, promisiunea de pe site „24–72 de ore"; reclamele Meta noi spun „24–48h" (nealiniat — se alege una).
- Aplicații relevante: Judge.me (instalat, 0 recenzii), Shopify Forms (pop-up „Reducere 5%", 904 KB — cel mai greu script), Messaging (Shopify Email + Flow), **Payment Customisation – Breeze** (instalat 24.09, doar scopul Shopify Functions, fără reguli încă), Hoppy Trust Badges (dezactivat), Google & YouTube, Meta (pixel 1715806199648772 + CAPI). Windsor.ai pe office@krea.ro pentru date (GA4 549462102, Google Ads 750-778-2449, Meta act 37951658341114187).

## 2. Cifrele (Shopify, 21 aug–19 sept, sesiuni umane) și reperele
| Etapă | Noi | Reper | Sursă |
|---|---|---|---|
| Sesiuni → coș | **1,48%** (278/18.684) | 4,6% media Shopify, top 20% >7,5% | Littledata 2023, 2.800 magazine |
| Coș → checkout | 42% | mediană 45–60% | Cartylabs 2026 |
| Checkout → comandă | **47%** (54/116) | 45% media Shopify, 44% mobil, top 20% >59% | Littledata |
| Conversie | 0,29% | 1,2% mobil Shopify | Littledata |
| Meta clic → sesiune | ~53% | normal ~90%; <60% = plasament/viteză | Loomer 2023/2025 |

Concluzia: **pierderea mare e înainte de coș** (primul ecran, încredere, preț) și la coș→checkout; checkout-ul e mediu, nu stricat. Aritmetic: coș 1,48%→2,5%, coș→checkout 42%→50%, checkout→comandă 47%→57% ⇒ 54 → ~133 comenzi/lună la același trafic; realist jumătate din drum în 60 de zile.

**Atenție la măsurare:** Shopify a schimbat definiția sesiunii pe 21–23 sept 2026 → baza nouă începe pe **24 sept**; nu compara cu perioadele de dinainte. A/B pe conversie e imposibil statistic la volumul ăsta (ar cere ~148.000 sesiuni/variantă); se măsoară metricile din amonte pe 14 zile înainte/după: rata de coș pe telefon (landing = produs), coș→checkout, checkout→comandă. Raport: Analytics → New exploration (Sessions, Sessions with cart additions, Sessions that reached checkout, Sessions that completed checkout; dimensiuni Device, Landing page, UTM campaign; filtru Human).

## 3. Ce s-a făcut deja pe 24 sept (nu reface, nu anula)
- Checkout: căsuța de abonare email afișată (nebifată); textul rambursului „Plătești la curier, după ce primești coletul — în numerar, fără taxe în plus. Curierul Cargus te sună înainte de livrare."; tariful „Cargus (curierul te sună înainte de livrare)", detalii „Livrare în 24–72 de ore, oriunde în România", **timp în tranzit 1–2 zile lucrătoare** (checkout-ul arată acum „Livrare estimată vin., 25 sept." în loc de „marți 30 sept."); butonul final „Finalizează comanda" (conținut temă → Checkout & system → Pay now button label); pe /cart „Total produse (+ 25 lei livrare Cargus, 24–72 h):" (`locales` → Cart → Total).
- 23 sept (sesiunea anterioară): pe telefon, în `main-product.liquid`, bloc `pp-mtop*` cu titlu + preț + „În stoc · Plătești la curier, la primire · Retur 14 zile" deasupra pozei; breadcrumb ascuns pe telefon (`.pp-bc`); Shopify Forms ascuns pe paginile de produs; bara `#mbb` pornită de la aterizare (`var deep = true`).
- Instalat Breeze (Payment Customisation), fără reguli.

## 4. De făcut, în ordine

### A. Temă (Liquid/CSS/JS) — pachetul „pagina de produs", metrică: rata de coș pe telefon (țintă 1,5% → ≥2,5%)
1. **Ștergi vechea bară lipită `#buybar`** (scriptul cu `real.getBoundingClientRect().bottom < 0` și clasa `on`): după derulare, azi sunt două bare suprapuse (`#buybar` 73 px, z-index 55 și `#mbb` 65 px, z-index 58). Rămâne doar `#mbb`.
2. **Sub preț, pe produs:** o linie „Livrare 25 lei · Cargus · ajunge în 1–3 zile lucrătoare" (fără aplicație; textul poate calcula ziua din `'now' | date`). Dovadă: 64% caută costul livrării înainte de coș, 40% abandonează din cauza costurilor extra (Baymard 2025/2026).
3. **„Retur 14 zile" ca link** către politica de retur, lângă buton (60% îl caută pe pagina produsului).
4. **Header pe un rând pe telefon:** iconițele Favorite/Coș lângă logo (azi rup pe al doilea rând; header ~200 px = 1/3 din primul ecran). Ținta: primul ecran = nume, preț, poză, buton.
5. **O singură promisiune de livrare peste tot** (banda de sus, produs, coș, checkout, reclame): Andu alege „24–72 h" sau „24–48 h"; până decide, rămâne 24–72 h pe site.
6. **Stelele Judge.me sub preț** (`judgeme_preview_badge`) — afișate doar când produsul are ≥1 recenzie (widgetul e gol acum; stele goale scad încrederea).
7. **Subsol legal:** scoate linkul SOL (`ec.europa.eu/consumers/odr` — platforma a fost desființată pe 20.07.2025); păstrează pictograma SAL cu link la `anpc.ro/ce-este-sal`; verifică vizibile CUI 53145290, denumirea ARTEMIS DIGITAL S.R.L., adresa, telefonul.
8. **Viteză:** decide cu Andu dacă rămâne Shopify Forms (904 KB) pe restul site-ului; scoate scripturi/aplicații nefolosite; ținta LCP ≤2,5 s pe mobil (fiecare 0,1 s ≈ +8,4% conversie, Google/Deloitte).
9. Coșul (sertar + /cart): totalul cu livrare inclusă acolo unde se poate calcula (25 lei fix), butonul „Finalizează comanda" primul și clar; fără cross-sell decât din aceeași temă (o recomandare irelevantă face utilizatorii să le ignore pe toate — Baymard).
10. Opțional, după 1–9: bloc „Specificații" scanabil deasupra descrierii oficiale (piese, vârstă, minifigurine, nr. set) — există deja o secțiune „Specificații", de verificat că e completă și sus.

### B. Admin / aplicații (necesită acces la admin: UI, sau Admin GraphQL cu token de custom app dacă Andu îl face)
1. **Breeze → Move:** Payment Option „Cash on Delivery (COD)", Position „Top" (dacă nu prinde, adaugă și „Numerar la livrare (COD)"); **Breeze → Rename:** COD → „Plata la curier (ramburs) — plătești când primești coletul". Verificare în previzualizarea checkout-ului. Metrică: checkout→comandă (47% → ≥57%). Nu se atinge gateway-ul (doar afișarea) — AWB-urile Cargus rămân la fel.
2. **Messaging → Automatizări:** există 6 (două „Recuperați coșul abandonat" — șterge dublura; „Convertiți răsfoirea…"; „Recuperați plata abandonată" cu 5 trimiteri; două „bun venit"). Fluxul de checkout abandonat: email 1 la **1 h** (fără reducere; produsele + „Plătești la curier, după ce primești coletul · Livrare Cargus 24–72 h · Retur 14 zile · Original, sigilat, cu factură" + „Ai avut o problemă? Răspunde la acest email sau sună la 0771 530 286"), email 2 la 24 h (stoc limitat + întrebarea „ce te-a oprit?"), email 3 la 72 h (seturi similare; eventual codul de 5% existent). Realist: doar ~12–15 checkout-uri abandonate cu email pe lună → +0,5–1,5 comenzi/lună. Destinatari: „doar abonați" (sigur legal) sau „toți clienții" (zonă gri, L.506/2004) — decizia lui Andu.
3. **Judge.me:** limba română; cerere automată la **7 zile după expediere** (Fulfilled + 7); **cererea unică pentru comenzile trecute** (~60 clienți; text: subiect „Cum ți se pare setul LEGO de la MundiShop?"; corp: „Salut {nume}, sperăm că setul a ajuns cu bine și a fost deja construit. Ne-ar ajuta mult o părere sinceră — două rânduri și, dacă vrei, o poză cu setul construit. Spune-ne și pentru cine a fost (copil/adult/cadou) și ce vârstă are — îi ajută pe alți părinți să aleagă. Mulțumim! MundiShop.ro"); import recenzii din Google Business Profile ca recenzii de magazin; widget stele + carusel pe produs. Dovadă: +270% probabilitate de cumpărare de la 0 la 5 recenzii, primele 5 contează cel mai mult (Spiegel/Northwestern); 80% sunt reticenți la un brand nou fără recenzii (PowerReviews).
4. **Microsoft Clarity** — fără aplicația din App Store (cere „view and edit" pe produse/comenzi/clienți și vine cu un chat AI „Brand Agents"): Andu creează proiectul pe clarity.microsoft.com, scriptul se pune în `theme.liquid` cu Consent Mode. Înregistrările din checkout nu sunt disponibile (doar Plus); restul da.
5. Confirmarea comenzilor ramburs: emailul de confirmare (Settings → Notifications) cu suma exactă de plătit curierului + „dacă nu mai dorești coletul, răspunde la acest email"; la comenzi >300 lei, mesaj manual WhatsApp în ziua comenzii (tranzacțional, permis). Țintă: refuzuri ≤5%.

### C. Decizii care rămân la Andu (cu dovezile în `mundishop-funnel-plan-23sept`)
Prag de livrare gratuită la 299 lei (concurența LEGO îl are toată; 38% adaugă produse ca să-l prindă — Cargus 2026); taxă ramburs 3–5 lei / card gratuit; retur 30 zile; Cargus Ship&Go / easybox; BNPL pentru 250–999 lei; prețuri la nivelul pieței pe top 73 seturi; Meta după 30.09: diagnostic clic→sesiune pe plasamente (exclude ce are LPV/clic <60%), consolidare ad seturi, retargeting separat abia la >1.000 coșuri/lună.

## 5. Recenzii — regula exactă
- Se construiește **sistemul** de recenzii (widget, cereri automate, cerere pentru comenzile vechi, import Google), nu recenziile.
- Nicio recenzie scrisă de noi sau de AI, niciun rating pus manual, nicio poză generată prezentată ca a unui client. Pozele cu colete/seturi făcute de magazin se folosesc **ca poze ale magazinului** („așa arată coletul de la noi"), etichetate corect — asta e în regulă și utilă în reclame și pe produs.
- Stelele apar pe pagină abia când există recenzii reale.

## 6. Verificare la final (definition of done)
- Pe telefon (390×660): primul ecran pe produs are nume, preț, poză, linie livrare 25 lei, buton vizibil; o singură bară lipită; fără depășiri orizontale; consola fără erori noi.
- Checkout în previzualizare: rambursul primul și cu numele nou, butonul „Finalizează comanda", estimarea de livrare corectă; niciun eveniment Purchase generat.
- Pixel Meta neatins (ViewContent/AddToCart trimit ca înainte — verificare în Events Manager pe trafic real, fără test events).
- Jurnal: data fiecărei schimbări + metrica urmărită, scris în `docs/` (sau în proiectul Claude „mundishop", docul `mundishop-funnel-executie-24sept`).

## 7. Surse principale (pentru argumente)
Baymard: baymard.com/lists/cart-abandonment-rate · baymard.com/blog/show-shipping-costs-on-product-pages · baymard.com/blog/shipping-speed-vs-delivery-date · baymard.com/blog/payment-ux · baymard.com/blog/product-recommendations-cart. Recenzii: spiegel.medill.northwestern.edu/how-online-reviews-influence-sales/ · powerreviews.com/review-volume-and-recency/. Benchmark: littledata.io/average-website-performance · cartylabs.com/blog/shopify-checkout-conversion-benchmarks/. Shopify: help.shopify.com/en/manual/reports-and-analytics/discrepancies/session-measurement-update · help.shopify.com/en/manual/checkout-settings/checkout-customization · help.shopify.com/en/manual/promoting-marketing/create-marketing/migrate-abandoned-checkout. România: bursa.ro (sondaj Cargus/Visa 2025: 42% frică de fraudă, 38% vor să verifice produsul, 25% plătesc cu cardul la curier) · electroretail.ro (Cargus feb. 2026: 67,7% acceptă 1–3 zile, 86% vor tracking, 38% adaugă produse pentru livrare gratuită) · greculawyers.ro/platforma-sol-desfiintata/ · dataprotection.ro (amenzi cookie/SMS).
