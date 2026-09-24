# MundiShop — pachetul B (admin și aplicații), pași exacți · 24.09.2026

Acești pași se fac din admin, în aplicații: Breeze, Messaging și Judge.me nu au API pe care să-l pot folosi de aici. Fiecare pas are metrica lui și se notează cu data în `docs/mundishop-funnel-executie-24sept.md`.
Reguli: fără comenzi de test (checkout-ul se verifică până la pasul de plată, fără „Finalizează comanda”). Nu se atinge gateway-ul de plată, doar felul în care e afișat. Nu se ating campaniile.

---

## B1. Breeze: rambursul primul și cu nume clar

**Metrică:** checkout→comandă (47% → ≥57%). 83% din comenzi sunt ramburs. Azi rambursul nu e primul în listă, iar numele „Numerar la livrare (COD)” sună tehnic.

1. Apps → **Payment Customisation – Breeze** → **Move** → Add rule
   - Payment option: `Numerar la livrare (COD)`. Dacă lista o arată ca „Cash on Delivery (COD)”, adaugă regula pentru ambele denumiri.
   - Position: **Top** → Save / Activate.
2. Breeze → **Rename** → Add rule
   - Payment option: aceeași metodă de mai sus
   - New name: `Plata la curier (ramburs) — plătești când primești coletul`
   - Save / Activate.
3. **Verificare:** într-o fereastră privată, pe telefon, adaugi un produs în coș → Finalizează comanda → completezi adresa → la pasul de plată: rambursul e **primul**, are **numele nou**, iar textul de sub el e cel din 24.09 („Plătești la curier, după ce primești coletul…”). Card, Apple Pay și Google Pay rămân vizibile. **Nu apeși „Finalizează comanda”.**
4. Nu se schimbă: metoda manuală din Settings → Payments (AWB-urile Cargus rămân la fel) și Google Pay / Apple Pay.

---

## B2. Messaging: recuperarea checkout-ului abandonat (1 h / 24 h / 72 h)

**Metrică:** comenzi recuperate pe lună. Realist: +0,5–1,5 comenzi pe lună, pentru că doar ~12–15 checkout-uri abandonate pe lună au e-mail.

1. Marketing → **Automations**:
   - Sunt două „Recuperați coșul abandonat”. Oprește și șterge-o pe cea mai veche sau pe cea nefolosită, ca să nu primească omul două e-mailuri.
   - „Recuperați plata abandonată” (azi cu 5 trimiteri) → Edit workflow: **3 trimiteri** la 1 h, 24 h, 72 h, cu condiția „checkout-ul nu s-a transformat în comandă” înaintea fiecăreia.
   - Cele două fluxuri „bun venit” și „Convertiți răsfoirea” rămân cum sunt (altă etapă).
2. **Destinatari:** „doar abonați” (sigur legal) sau „toți clienții” (zonă gri, L. 506/2004). **Decide Andu.** Până decide, rămâne „doar abonați”.
3. Textele (ton direct, fără superlative):

**E-mail 1 · la 1 oră · fără reducere**
- Subiect: `Setul tău e încă în coș`
- Corp: blocul cu produsele din checkout + butonul „Finalizează comanda”, apoi:
  > Plătești la curier, după ce primești coletul · Livrare Cargus 24–72 h · Retur 14 zile · Original, sigilat, cu factură
  >
  > Ai avut o problemă la comandă? Răspunde la acest e-mail sau sună la 0771 530 286.

**E-mail 2 · la 24 de ore**
- Subiect: `Te-a oprit ceva la comandă?`
- Corp: produsele + butonul, apoi:
  > Dacă ceva nu ți-a fost clar (livrarea, plata, dacă setul e potrivit pentru vârsta copilului), răspunde la acest e-mail și îți scriem noi în aceeași zi.
  > Seturile pleacă din stocul nostru. Nu le putem ține rezervate, așa că se poate să nu mai fie disponibile peste câteva zile.

  (Fără „stoc limitat” generic: e o afirmație de urgență care trebuie să fie adevărată pentru fiecare produs.)

**E-mail 3 · la 72 de ore**
- Subiect: `Ultimul mesaj despre coșul tău`
- Corp: produsele + blocul „produse recomandate” din Shopify Email (seturi similare) + butonul.
- Codul existent de 5%: **doar dacă Andu îl aprobă** pentru acest flux.

4. **Verificare:** din fiecare e-mail, „Send test” către office@krea.ro. Fără comenzi de test.

---

## B3. Judge.me: sistemul de recenzii (nu recenziile)

**Situația găsită pe 24.09 (API-ul public Judge.me, nu presupuneri):**
- **4 recenzii de produs**: LEGO Art 31214 (cumpărător verificat, invitație), Super Mario 72051, Friends 42681 și Pokémon 72160 (toate trei de la vizitatori, neverificate).
- **12 recenzii de magazin**: 5 importate din Google Business, 4 „prin invitația magazinului” (neverificate), 3 de la vizitatori ai site-ului. Toate au 5★, iar majoritatea sunt din 16–19 august.
- Setările Judge.me **ascund insignele de transparență**, adică eticheta care spune de unde vine fiecare recenzie (Google, invitație, vizitator).
- Widgetul de recenzii există pe produs, dar e la ~9.800 px (îl mută pachetul A).

Pașii:

1. **Limba:** Settings → Language: română. Texte la persoana a II-a singular, ca pe site. Azi fereastra „Scrie o recenzie” spune „Cum ați evalua…” și „dumneavoastră”. Propunere:
   - Titlu: `Cum ți se pare setul?`
   - Subtitlu: `Două rânduri sincere îi ajută pe alți părinți să aleagă.`
   - Titlul widgetului: `Recenzii`
2. **Aspect:** Widgets → Review Widget → Customize: culoare principală `#0055D4`, stele `#F5A300`, colțuri rotunjite (12 px), fontul temei. Azi e verdele implicit Judge.me, care nu seamănă cu nimic din magazin. Tema pune deja aceste culori prin variabile CSS, dar widgetul nou le citește din setările lui.
3. **Cererea automată:** Requests → Timing: **7 zile după expediere** (Fulfilled + 7). Canal: e-mail. Un reminder după încă 7 zile, dacă nu a răspuns. Fără cupon pentru recenzie pozitivă: recenzia plătită doar dacă e pozitivă e interzisă.
4. **Transparență și publicare (Legea 148/2023, Directiva 2005/29 Anexa I pct. 23b–23c):**
   - Pornește **insignele de transparență** (Review Widget → Transparency badges / „How reviews are collected”) și linkul „Cum sunt colectate recenziile?”. Azi sunt ascunse.
   - Auto-publicare pentru **toate** recenziile de la cumpărători verificați, **indiferent de numărul de stele**. Publicarea doar a celor de 4–5★ e practică interzisă (pct. 23c).
   - Recenziile de la vizitatori (neverificate): moderare manuală. Se aprobă cele reale, fără filtru după stele. Se resping doar spamul și cele fără legătură cu produsul.
   - Andu confirmă de unde vin cele 4 recenzii „prin invitație” de magazin și cele 3 de la vizitatori din 16–19 august. Până atunci, **nu se folosesc** ca argument în reclame sau în bannere de tipul „4,9★ din 12 recenzii”.
5. **Cererea unică pentru comenzile trecute** (~60 de clienți): Requests → Send requests for past orders → comenzile expediate înainte de azi. Text:
   - Subiect: `Cum ți se pare setul LEGO de la MundiShop?`
   - Corp: `Salut {nume}, sperăm că setul a ajuns cu bine și a fost deja construit. Ne-ar ajuta mult o părere sinceră — două rânduri și, dacă vrei, o poză cu setul construit. Spune-ne și pentru cine a fost (copil/adult/cadou) și ce vârstă are — îi ajută pe alți părinți să aleagă. Mulțumim! MundiShop.ro`
   - Opțional: câmpuri personalizate (Custom forms) „Pentru cine a fost?” (copil / adult / cadou) și „Vârsta”. Apoi se pot filtra în widget.
6. **Google:** importul din Google Business Profile e deja făcut (5 recenzii cu eticheta „scrisă în Google Business”). Lasă sincronizarea pornită pentru cele noi. Rămân recenzii **de magazin**, nu de produs.
7. **Stelele de sub preț** (tema, `snippets/mundi-pp-stars.liquid`) citesc ratingul din metafield-urile produsului: `reviews.rating` / `reviews.rating_count` (standard Shopify) sau `judgeme.badge`. Verificare după publicarea pachetului A: pe `/products/lego-72160` trebuie să apară „5,0 · 1 recenzie”. Dacă nu apare, în Judge.me → Settings → Integrations pornește sincronizarea ratingului în metafield-urile Shopify („Shopify product reviews metafields” / Google Shopping). **Atenție:** asta înseamnă că Judge.me scrie metafield-uri pe produse. După prima sincronizare, verifică în Meta Commerce Manager că produsul respectiv nu intră în re-verificare. Dacă intră, sincronizarea se oprește, iar stelele de sub preț nu apar (nu strică nimic altceva).
8. **Pozele cu colete făcute de noi:** se folosesc ca poze ale magazinului („Așa arată coletul de la noi”), etichetate așa, pe pagina de livrare sau în reclame. Nu se încarcă în Judge.me ca poze ale clienților.

---

## B4. Microsoft Clarity (prin script, fără aplicație)

**De ce fără aplicație:** aplicația din App Store cere „view and edit” pe produse, comenzi și clienți și vine cu un chat AI („Brand Agents”). Scriptul nu cere nimic.

1. Andu: clarity.microsoft.com → New project → „MundiShop.ro”, URL `https://mundishop.ro` → Settings → Overview → copiază **Project ID** (10 caractere).
2. În temă (pe copia din pachetul A sau separat): `snippets/mundi-clarity.liquid` → `assign clarity_id = 'ID-ul'`. În `layout/theme.liquid`, înainte de `</head>`: `{% render 'mundi-clarity' %}`.
3. Ce face snippetul (testat pe 24.09 cu un ID fals): pornește doar cu consimțământ pentru analiză (Shopify Customer Privacy API). Se încarcă după „load”, în primul moment liber (~3,7 s în test), deci nu întârzie poza sau butonul. Trimite semnalul `consentv2` cerut în SEE.
4. În Clarity → Settings → Masking: „Balanced” (implicit), ca să nu se vadă nume, telefoane și adrese în înregistrări.
5. Înregistrările din checkout nu sunt disponibile (doar pe Shopify Plus). Restul drumului (produs, coș, sertar) da.
6. **Verificare:** Settings → Customer privacy → **Cookie banner pornit pentru SEE**. Testul de aici a rulat din SUA, unde Shopify nu arată bannerul, deci trebuie verificat de pe un telefon din România: fără acceptare nu pleacă nicio cerere către `clarity.ms`, după „Accept” pleacă.

---

## B5. (Opțional, din handoff) Confirmarea comenzilor ramburs

Settings → Notifications → **Order confirmation** → Edit code. Imediat după salut:
```liquid
{%- assign e_ramburs = false -%}
{%- for t in transactions -%}
  {%- assign g = t.gateway_display_name | default: t.gateway | downcase -%}
  {%- if g contains 'cod' or g contains 'ramburs' or g contains 'numerar' or g contains 'curier' -%}{%- assign e_ramburs = true -%}{%- endif -%}
{%- endfor -%}
{%- if e_ramburs -%}
  <p><strong>Ai de plătit curierului: {{ total_price | money }}</strong> (produse + livrare), în numerar, când primești coletul. Curierul Cargus te sună înainte de livrare.</p>
  <p>Dacă nu mai dorești coletul, răspunde la acest e-mail înainte să plece, ca să nu-l trimitem degeaba.</p>
{%- endif -%}
```
Verificare: butonul „Send test notification” (nu o comandă). La comenzile peste 300 de lei, mesajul manual pe WhatsApp în ziua comenzii rămâne pe mâna lui Andu. Ținta: refuzuri ≤5%.
