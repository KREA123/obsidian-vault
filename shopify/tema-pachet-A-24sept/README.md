# Pachetul A — pagina de produs (24.09.2026)

Metrica urmărită: **rata de coș pe telefon, pe sesiunile care aterizează pe produs** (azi ~1,48%, ținta ≥2,5%).
Tot pachetul e o singură schimbare de măsurat. Pe durata celor 14 zile nu se mai modifică nimic altceva pe pagina de produs.

Nimic de aici nu scrie date de produs (titlu, descriere, preț, poze, taguri, metafield-uri, colecții). Toate modificările sunt în temă: Liquid, CSS, JS, `templates/product.json`, `config/settings_data.json` și `locales`.

## Stare: aplicat pe copia nepublicată 206388068684 (24.09, 11:45)

- Copia „Mundi — pachet A 24.09 (previzualizare)” a fost făcută din tema live 204842565964 cu `themeDuplicate`. Cele 13 fișiere din `tema-copie/` au fost încărcate cu `themeFilesUpsert` și verificate după încărcare, cu sume MD5 identice.
- Originalele din tema live sunt în `tema-live-inainte/`, pentru comparație (`diff -r tema-live-inainte tema-copie`) și pentru revenire.
- **Previzualizare pe telefon:** `https://mundishop.ro/?preview_theme_id=206388068684`.
- **Publicare:** Andu, din Online Store → Themes → „Mundi — pachet A 24.09 (previzualizare)” → Publish. Data și ora se notează în `docs/mundishop-funnel-executie-24sept.md`. Pentru revenire se republică tema anterioară, care rămâne neatinsă.
- Înainte de publicare: insignele de transparență pornite în Judge.me (pachetul B, B3.4).

Pașii de mai jos descriu exact ce s-a schimbat, ca să poată fi refăcuți de mână pe altă temă.

## Fișiere noi (se copiază ca atare în `snippets/`)

| Fișier | Ce face |
|---|---|
| `snippets/mundi-pp-ship.liquid` | Linia „Livrare 25 lei · Cargus · ajunge în 24–72 de ore” sub preț. Promisiunea e scrisă o singură dată, aici. Nu apare la produsele epuizate. |
| `snippets/mundi-pp-stars.liquid` | Stelele sub preț, **doar dacă produsul are ≥1 recenzie**. Fără JavaScript. Citește ratingul pus de Judge.me în metafield-uri și nu scrie nimic. |
| `snippets/mundi-pp-style.liquid` | Stilurile noi de pe produs. Pe telefon scoate golul de 32 px de deasupra cardului. Pune culorile magazinului pe widgetul Judge.me. |
| `snippets/mundi-header-mobil.liquid` | Header-ul pe un rând pe telefon și lupa care deschide căutarea. |
| `snippets/mundi-lcp-preload.liquid` | Preîncarcă poza principală de produs din `<head>`. |
| `snippets/mundi-clarity.liquid` | Microsoft Clarity, pentru pachetul B (rămâne inactiv cât timp nu are ID). |

## Modificări în fișierele existente

### 1. `sections/main-product.liquid`

**A1 · șterge vechea bară lipită `#buybar`.** Se șterge tot blocul care începe cu `<div class="buybar" id="buybar" …>` și scriptul de imediat după el, cel cu `real.getBoundingClientRect().bottom < 0` și comentariul „butonul a ieșit pe sus”. Rămâne doar `#mbb` (`snippets/mundi-buybar.liquid`).
Opțional: regulile `.buybar…` și `body.buybar-on .pagew{…}` din `assets/mundi-legacy.css` rămân fără efect și se pot șterge.

**Stiluri.** Imediat după blocul `<style>` existent, cel cu comentariul „Telefon: nume + preț + plată la curier deasupra pozei…”:
```liquid
{% render 'mundi-pp-style' %}
```

**A2 + A6 · sus, pe telefon (`.pp-mtop`).** Imediat după `</div>`-ul care închide `.pp-mtop-p`, înainte de `<p class="pp-mtop-s">`:
```liquid
{% render 'mundi-pp-stars', product: product %}
{% render 'mundi-pp-ship', product: product, cls: 'pp-mtop-ship' %}
```

**A3 · „Retur 14 zile” ca link, sus.** În `<p class="pp-mtop-s">`, textul `Retur 14 zile` devine:
```liquid
<a href="/pages/politica-de-retur">Retur 14 zile</a>
```

**A2 + A6 · în coloana de informații (`.pinfo`).**
- Imediat după `</div>`-ul care închide `.pr` (prețul): `{% render 'mundi-pp-stars', product: product %}`
- În `.stock`: cheia `product.in_stock` („● În stoc — livrare în 24–72 ore”) e înlocuită cu una nouă, `product.in_stock_short` („● În stoc”), pentru că livrarea are acum linia ei. Cheia veche rămâne în `locales/ro.json` pentru alte eventuale utilizări. Logica de stoc (în stoc / epuizat) rămâne cum e.
- Imediat după `</div>`-ul care închide `.stock`: `{% render 'mundi-pp-ship', product: product %}`

**A3 · „Retur 14 zile” ca link, lângă buton.** În lista `.trust`, sub butoane, textul „Retur simplu în 14 zile” se înfășoară în `<a href="/pages/politica-de-retur">…</a>`. Iconița rămâne în afara linkului.

### 2. `sections/mundi-header.liquid` (A4 · header pe un rând)

- `<header class="mh-bar" id="mh-bar">` devine
  `<header class="mh-bar{% if request.page_type == 'index' %} mh-bar--home{% endif %}" id="mh-bar">`.
  Pe prima pagină câmpul de căutare rămâne deschis.
- `<form class="mh-search" …>` primește `id="mh-sform"`.
- Primul copil din `<div class="mh-act">`, înainte de `<a class="mh-acc" …>`:
  ```html
  <button type="button" class="mh-sbtn" id="mh-sbtn" aria-label="Caută" aria-expanded="false" aria-controls="mh-sform"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg></button>
  ```
- La finalul secțiunii, înainte de `{% schema %}`: `{% render 'mundi-header-mobil' %}`

Cauza ruperii pe rânduri: `assets/mundi-toy.css` repune etichetele „Favorite” și „Coșul meu” pe telefon (`.mh-bar .mh-act a {font-size:12.5px}`), așa că iconițele nu mai încap lângă logo. Snippetul le scoate din nou, doar pe telefon. Pe desktop nu se schimbă nimic.

### 3. Subsolul (secțiunea `footer`, `class="mf"`) · A7

- Linkul „Soluționarea online a litigiilor (SOL)” din coloana „Informații” vine din meniul `footer` (Online Store → Navigation). În temă, bucla meniului sare peste orice link către `ec.europa.eu/consumers/odr`, deci dispare odată cu publicarea temei. Elementul se poate șterge și din meniu, oricând după aceea.
- Se scoate insigna **SOL** din banda `.mf-band` (`<a href="https://ec.europa.eu/consumers/odr" …>`).
- Rămân linkul „ANPC - SAL” și insigna ANPC SAL (`https://anpc.ro/ce-este-sal/`).
- Datele firmei sunt vizibile în `.mf-legal`: ARTEMIS DIGITAL S.R.L., J2025098748009, CUI 53145290, sediul din Sectorul 3. **Telefonul** e însă doar în coloana „Contact”, care pe telefon e strânsă. Se adaugă la finalul primului paragraf din `.mf-legal`: ` · Tel. <a href="tel:0771530286">0771 530 286</a> · <a href="mailto:office@krea.ro">office@krea.ro</a>`.

### 4. `layout/theme.liquid` · A8 (viteză)

Imediat după `<meta name="viewport" …>`:
```liquid
{% render 'mundi-lcp-preload' %}
```
Verificare în previzualizare: în DevTools → Network, poza principală se descarcă **o singură dată**. Dacă apare de două ori, galeria folosește altă poză sau alte lățimi și snippetul trebuie aliniat cu ea.

### 5. Animația cu minifigurine (`mcrew`, snippetul cu `.mcrew-hi` / `mfig-ghost.webp`) · A8

În `function boot()`, `intro();` devine:
```js
if (TPL !== 'product') intro();
```
Azi, la prima vizită din sesiune, două minifigurine urcă peste poza produsului și peste bara „Adaugă în coș” timp de ~3,7 s. Asta se întâmplă exact la aterizarea din reclamă. Pe prima pagină și pe colecții animația rămâne.

### 6. `templates/product.json` · recenziile mai sus

Widgetul Judge.me de recenzii există deja pe produs (secțiunea `…1786919316f319acbc`, blocul `judge_me_reviews_review_widget`). Azi e la ~9.800 px, după „În detaliu”, specificații, întrebări și produsele similare, deci practic nu-l vede nimeni. În `"order"`:
- `"1786919316f319acbc"` se mută imediat după `"main"`, înainte de `"product_extras"`. În simulare, widgetul urcă de la 9.828 px la 3.813 px, imediat după descriere.
- Se scot `"178913132619078dc7"` (secțiune goală) și `"1789386595a051a3c4"` (blocul Hoppy Trust Badges, aplicație dezactivată), din `"order"` și din `"sections"`.

Echivalent în editorul de temă: Produs → trage secțiunea cu „Judge.me Review Widget” sub secțiunea principală, apoi șterge cele două secțiuni goale.

**Condiție:** întâi se pornesc în Judge.me insignele de transparență (pachetul B, Judge.me, punctul 4). Recenziile de magazin afișate azi nu arată de unde vin, iar secțiunea devine mult mai vizibilă.

### 7. Hoppy Trust Badges

Embed-ul aplicației e deja oprit în `config/settings_data.json`. `animation.css` (4,8 KB, blochează afișarea) venea din **blocul** Hoppy din `templates/product.json`, adică secțiunea `…1789386595a051a3c4`, care se scoate la punctul 6. În `settings_data.json` nu mai e nimic de schimbat.

### 8. `locales/ro.json` · texte lipsă pentru cititoarele de ecran

Galeria afișează azi „Translation missing: ro.product.gallery” în atributele `aria-label`. Sub cheia `"product"` se adaugă:
```json
"in_stock_short": "● În stoc",
"gallery": "Galerie foto",
"prev_image": "Poza anterioară",
"next_image": "Poza următoare",
"go_to_image": "Poza"
```

## Ce NU face pachetul (decizii pentru Andu, cu cifrele în jurnal)

- **Shopify Forms** („Reducere 5%”): se încarcă pe fiecare produs (906 KB de JavaScript, blocare de ~1,1 s pe un telefon mediu), deși e ascuns pe produs din 23.09. Doar oprirea embed-ului îl scoate, iar asta îl scoate de pe tot site-ul.
- **Tagul Google Ads din `theme.liquid`** (`gtag/js?id=AW-18376254111`) **rămâne.** A fost pus pe 18.09 ca verificarea din Google Ads să vadă tagul pentru PMax (comentariul din temă explică de ce).
- **Pixelul personalizat „Google Ads – conversie Google Shopping App Purchase”** (Settings → Customer events): are un `s` rătăcit la începutul liniei 10 (`s// Google Ads…`). Aruncă „ReferenceError: s is not defined” pe fiecare pagină și nu rulează deloc. Conversia de cumpărare nu se pierde: aplicația Google & YouTube o trimite deja pe aceeași etichetă (`AW-18376254111/kg0fCMi4xd0cEJ_FvbpE`). De aceea, dacă se „repară”, riscă să dubleze conversiile. Recomandare: se șterge pixelul, după acordul lui Andu.
- Punctele 9–10 din handoff (coșul și blocul „Specificații”) vin după măsurarea acestui pachet.

## Lista de verificare în previzualizare (pe telefon, 390×660 și 375×812)

- [ ] Primul ecran pe produs: nume, preț, (stele, dacă există recenzii), „Livrare 25 lei · Cargus · ajunge în 24–72 de ore”, „În stoc · Plătești la curier, la primire · Retur 14 zile” (link), poza întreagă și bara „Adaugă în coș”.
- [ ] După derulare: **o singură** bară lipită jos (`#mbb`), fără a doua bară care se vede pe deasupra.
- [ ] Header pe un rând: meniu · logo · lupă · favorite · coș. Lupa deschide căutarea cu tastatura. Pe prima pagină căutarea e deschisă.
- [ ] `/products/lego-72160` (1 recenzie în Judge.me): stelele „5,0 · 1 recenzie” apar sub preț. `/products/lego-75456` (0 recenzii): nu apar stele. Dacă pe 72160 nu apar, citește „Stelele” din `docs/mundishop-pachet-B-admin-24sept.md`.
- [ ] Widgetul de recenzii e imediat după descriere, iar „Scrie o recenzie” deschide formularul.
- [ ] Subsol: fără SOL, cu ANPC SAL.
- [ ] Fără derulare orizontală, fără erori noi în consolă. „s is not defined” e pixelul Google de mai sus și exista și înainte.
- [ ] „Adaugă în coș” din bară și din pagină pune produsul în coș și deschide sertarul, ca înainte.

## Verificarea făcută pe 24.09 (fără acces la temă)

`verificare/prototip.js` deschide pagina live în Chromium și rescrie HTML-ul primit cu exact ce produce codul de mai sus, apoi măsoară și face capturi. Pe site nu se trimite nimic. Rezultatele și capturile sunt în `docs/mundishop-funnel-executie-24sept.md` și `docs/audit-24sept/`.
Snippet-urile Liquid au fost randate și cu `liquidjs`, pe produse simulate: 0, 1, 4, 23 și 101 recenzii, doar insigna Judge.me, produs epuizat.
