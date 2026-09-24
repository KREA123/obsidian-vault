# MundiShop — execuția funnel-ului · jurnal (din 24.09.2026)

Handoff: `docs/mundishop-funnel-handoff-claude-code-24sept.md` · Pachetul A (temă): `shopify/tema-pachet-A-24sept/README.md` · Pachetul B (admin): `docs/mundishop-pachet-B-admin-24sept.md` · Capturi: `docs/audit-24sept/`

## Stare pe 24.09, seara

- **Pachetul A (temă) e pregătit și verificat în simulare, dar NU e aplicat pe site.** Conectorul Shopify din Claude cere re-autentificare, deci nu am putut citi sau scrie tema. Codul e scris ca snippet-uri Liquid plus instrucțiuni exacte pe fișier. L-am verificat rescriind în Chromium paginile live cu exact ce produce codul.
- **Pachetul B** nu e aplicat. Se face din admin, în aplicații. Pașii exacți sunt în `docs/mundishop-pachet-B-admin-24sept.md`.
- **Nimic din site nu s-a schimbat azi prin mine.** Nicio scriere de produs, nicio comandă, nicio campanie atinsă.

Ca să continui: reconectezi conectorul Shopify în claude.ai. Apoi fac o copie a temei live, aplic pachetul A pe copie și îți dau linkul de previzualizare. Publici tu (conectorul nu permite scrieri pe tema publicată).

## Jurnal

| Data | Schimbare | Etapă → metrică | Stare |
|---|---|---|---|
| 23.09 | Bloc nume + preț + „Plătești la curier” deasupra pozei pe telefon; breadcrumb ascuns; Forms ascuns pe produs; `#mbb` de la aterizare | produs → rata de coș pe telefon | aplicat (sesiunea anterioară) |
| 24.09 | Checkout: e-mail nebifat, text ramburs, tarif Cargus + tranzit 1–2 zile, „Finalizează comanda”, total /cart cu livrare | checkout → checkout→comandă | aplicat (dimineața, conform handoff) |
| 24.09 | Instalat Breeze (fără reguli) | — | aplicat (conform handoff) |
| 24.09 | **Baza de măsurare începe** (noua definiție de sesiune Shopify) | toate | — |
| 24.09 | Audit pe telefon și viteză (cifrele de mai jos) | — | făcut |
| 24.09 | **Pachetul A** pregătit: A1 fără `#buybar` · A2 linie livrare · A3 retur ca link · A4 header pe un rând · A5 o singură promisiune (24–72 h) · A6 stele doar cu recenzii · A7 fără SOL + telefon vizibil · A8 preîncărcare poză, fără minifigurine pe produs, fără Hoppy · widgetul de recenzii mutat sub descriere | produs → **rata de coș pe telefon, landing = produs** | pregătit, verificat în simulare, **neaplicat** |
| — | Pachetul A publicat (data și ora se completează la publicare) | | |
| — | B1 Breeze: ramburs primul + redenumit | checkout → **checkout→comandă** | de făcut |
| — | B2 Checkout abandonat 1 h / 24 h / 72 h | după checkout → comenzi recuperate | de făcut |
| — | B3 Judge.me: transparență, cerere la 7 zile, cererea pentru comenzile trecute, culori | produs (parte din A) | de făcut |
| — | B4 Clarity prin script | măsurare | de făcut (lipsește ID-ul proiectului) |

## Cum se măsoară

- **Baza începe pe 24.09.** Nu se compară cu perioadele de dinainte, pentru că Shopify a schimbat definiția sesiunii pe 21–23.09.
- Raport: Analytics → New exploration → Sessions, Sessions with cart additions, Sessions that reached checkout, Sessions that completed checkout. Dimensiuni: Device type, Landing page type, UTM campaign. Filtru: sesiuni umane.
  - Rata de coș pe telefon (pachetul A) = Sessions with cart additions ÷ Sessions, cu Device = Mobile și Landing page type = Product.
  - Coș→checkout = Sessions that reached checkout ÷ Sessions with cart additions.
  - Checkout→comandă (B1) = Sessions that completed checkout ÷ Sessions that reached checkout.
- 14 zile după fiecare publicare, fără alte schimbări pe aceeași etapă în perioada asta.
- **Fereastra „înainte” e scurtă.** Dacă pachetul A se publică pe 25–26.09, „înainte” are doar 1–2 zile (24.09 → publicare). Comparația va fi orientativă, nu o dovadă. Varianta curată: publicare pe 08.10, după 14 zile de bază. Costă două săptămâni. **Decide Andu.** B1 (checkout) poate merge în paralel, pentru că e altă etapă.

| Metrică | Înainte (24.09 → publicare) | După (14 zile) |
|---|---|---|
| Rata de coș pe telefon, landing = produs | | |
| Coș → checkout | | |
| Checkout → comandă | | |

## Cifrele auditului din 24.09 (telefon 390×660, browserul din Facebook simulat)

**Primul ecran pe produs** (`/products/lego-75456`), înainte → după pachetul A (simulare):

| | Înainte | După |
|---|---|---|
| Banda de sus + header | 208 px (header 174 px, pe 3 rânduri) | 91 px (header 57 px, un rând) |
| Titlul începe la | 275 px | 126 px |
| Linia de livrare sub preț | — | 209 px |
| Poza principală | 405–725 px (se vede ~190 px din 320) | 278–598 px (se vede întreagă) |
| Bare lipite jos după derulare | 2 (`#buybar` 73 px z55 + `#mbb` 65 px z58) | 1 (`#mbb`) |
| Widgetul de recenzii | la 9.828 px (după produsele similare) | la 3.813 px (după descriere) |
| Derulare orizontală | nu | nu |
| Erori noi în consolă | — | niciuna |

La 375×812 rezultatele sunt identice (header 57 px, poza la 278–583 px, o singură bară). Capturi: `docs/audit-24sept/01…09`.

**Viteză (Lighthouse 12, mobil simulat, 3–6 rulări, mediane).** Au fost excluse rulările blocate de proxy-ul din mediul de test (>10 s):

| Varianta | LCP | TBT (timp blocat) |
|---|---|---|
| Azi | ~3,5 s | ~6,3 s |
| Fără Shopify Forms | ~3,7 s | ~4,5 s |
| Fără Forms + fără tagul Google Ads dublat | ~4,1 s | ~4,6 s |

- LCP-ul din laborator **nu** coboară sub 2,5 s prin ce se poate face din temă sau prin cele două decizii. Diferențele de LCP de mai sus sunt în zgomotul măsurătorii. Nu pot promite ținta ≤2,5 s din laborator.
- Oprirea Forms scade timpul blocat cu ~1,8 s. Contează pentru cât de repede răspunde butonul „Adaugă în coș” în primele secunde.
- Fără tagul Google Ads dublat nu s-a văzut un câștig suplimentar în laborator.
- LCP-ul real se urmărește în **Shopify admin → Online Store → Themes → Web performance** (date de la vizitatori reali). Asta e sursa pentru ținta ≤2,5 s.
- Pe telefonul simulat, 25 s de lucru pe firul principal, din care ~12 s execuție de scripturi. Cel mai mult cer: pixelii Shopify, Meta, Google Tag Manager, Shopify Forms și Judge.me. Detalii: `docs/audit-24sept/lighthouse-24sept.json`.
- Observat, fără throttling: TTFB ~0,4–0,8 s, iar poza principală are 37 KB (webp, 640 px). Poza nu e problema.

**Promisiunea de livrare (A5).** Pe site e deja peste tot „24–72 de ore”. Locurile, pentru când decide Andu între 24–72 h și 24–48 h:
- banda de sus (secțiunea header) și coșul gol („îl trimitem în 24–72 de ore”);
- pe produs: `.stock` (se scoate în pachetul A), `.trust`, specificațiile și întrebările din `product_extras`, și noul `snippets/mundi-pp-ship.liquid` (o singură variabilă);
- prima pagină: hero, carduri, întrebări;
- paginile Contact și Livrare și plată; totalul din /cart (`locales`); tariful Cargus din checkout.
- Descrierile de produs spun „Livrare rapidă din stoc”, fără cifră. Nu se ating (date de produs).
- Nealiniate: doar **reclamele Meta („24–48h”)**. Nu se ating (regula 3).
- Linia sub preț folosește „24–72 de ore”, nu „1–3 zile lucrătoare”, ca să nu apară două promisiuni pe același ecran. Pe pagină mai scrie „24–72” de 4 ori. Estimarea din checkout („vin., 25 sept.” pentru o comandă de joi, 24.09) e în interiorul promisiunii.

**Recenzii (Judge.me, API public).** Docul spunea 0. Pe 24.09 există 4 recenzii de produs (1 verificată) și 12 de magazin (5 importate din Google Business, 4 prin invitație, neverificate, și 3 de la vizitatori). Toate au 5★, majoritatea din 16–19.08. Insignele de transparență sunt ascunse din setări. Detalii și pașii în pachetul B, B3.

## Găsite în afara temei (decizii pentru Andu)

1. **Pixel personalizat Google Ads stricat** (Settings → Customer events → „Google Ads – conversie Google Shopping App Purchase”, instalat pe 07.09). Linia 10 începe cu un `s` rătăcit, așa că pixelul aruncă „ReferenceError: s is not defined” pe fiecare pagină și nu face nimic. Conversia de cumpărare **nu** se pierde: aplicația Google & YouTube o trimite deja pe aceeași etichetă `AW-18376254111/kg0fCMi4xd0cEJ_FvbpE`. Dacă se repară, riscă să dubleze conversiile. Recomandare: se șterge.
2. **Tagul Google Ads dublat în `theme.liquid`** (`gtag/js?id=AW-18376254111` + `config`), pe lângă aplicația Google & YouTube: 166 KB în plus pe fiecare pagină. Tot aici, GA4 (`G-TS3NDM80PQ`) e configurat și în temă, și în aplicație, deci probabil numără de două ori vizualizările de pagină **în GA4**. Cifrele din Shopify Analytics nu sunt afectate.
3. **GA4 pe colecții:** cererea `g/collect` primește 413 (prea mare, probabil lista de produse din `view_item_list`), deci evenimentul se pierde. Afectează doar GA4.
4. **Shopify Forms** („Reducere 5%”): 906 KB de JS pe fiecare pagină, inclusiv pe produs, unde e ascuns. Varianta: se oprește sau rămâne (item 8 din handoff).
5. **Bannerul de cookie-uri pentru SEE** trebuie verificat de pe un telefon din România. Testele de aici au rulat din SUA, unde Shopify nu arată bannerul.

## Ce urmează

1. Reconectarea conectorului Shopify. Apoi: copie a temei → pachetul A aplicat pe copie → linkul de previzualizare → verificare pe telefon (lista din README) → Andu publică → data în jurnal.
2. B1 (Breeze) și B3 (Judge.me, întâi transparența) din admin. B1 poate merge în paralel cu A (altă etapă).
3. După 14 zile de la publicarea lui A: completarea tabelului de măsurare, apoi punctele 9–10 (coșul și specificațiile).
