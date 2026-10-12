# Tema Shopify SOUL: cum o pui online

Tema e landing-ul v3 transformat în temă Shopify Online Store 2.0. Fișierul de urcat este:

`store/soul-theme.zip`

Tema pornește în **mod prelansare**. În modul ăsta nu există buton de cumpărare, nici coș. Pe pagina produsului apare lista de așteptare. Așa rămâne până ai certificarea CE.

Ia pașii în ordine. Fiecare pas spune unde dai click în Shopify Admin.

---

## 1. Creezi magazinul

1. Intră pe **shopify.com**, apasă **Start free trial** și fă contul cu emailul firmei.
2. **Settings → Store details**
   - Store name: `SOUL`
   - Legal business name: `ARTEMIS DIGITAL S.R.L.`
   - Adresa: sediul social, Str. Vlăhița nr. 1, bl. PM18bis, sc. 2, ap. 123, Sector 3, București
   - Nu pune telefonul firmei nicăieri public.
   - Store currency: **EUR**. Alege moneda înainte de prima comandă, pentru că după aceea e greu de schimbat.
3. **Settings → Plan**: alege un plan. Pe perioada de probă, magazinul are parolă și nimeni nu vede lista de așteptare. Parola o scoți la pasul 9.

## 2. Limbile (engleză și română)

1. **Settings → Languages**. Engleza e limba implicită.
2. **Add language → Romanian (Română) → Add**, apoi apasă **Publish** lângă Romanian.
3. Textele site-ului sunt deja traduse în temă (`locales/en.default.json` și `locales/ro.json`). Ca să schimbi un text:
   - Mergi la **Online Store → Themes**.
   - Apasă pe **…** de lângă temă, apoi **Edit default theme content**.
   - Alege limba sus și caută textul.
4. Butoanele EN / RO din antet schimbă limba. Adresa paginii devine `/ro/...`.

## 3. Piețele: EUR și RON

1. **Settings → Markets**.
2. Piața **Romania**: Currency = **RON (lei)**.
3. Piața **Europe** (sau **International**): Currency = **EUR**.
4. Prețul de bază rămâne în EUR (249). Pentru un preț fix în lei:
   - Deschide **Markets → Romania → Products and pricing**.
   - Pune prețul manual, de exemplu `1.249 lei`, după ce decizi cât să fie.
5. Atenție: Shopify convertește în RON doar dacă **Shopify Payments** e activ pe magazin. Fără el, toți vizitatorii văd EUR. În prelansare nu plătește nimeni nimic, deci nu e o problemă acum.
6. Când există mai multe țări, subsolul site-ului arată automat un selector **Țară / monedă**.

## 4. Urci tema

1. **Online Store → Themes → Add theme → Upload zip file**, apoi alege `soul-theme.zip`.
2. Apasă **Customize** pe tema urcată, apoi **Theme settings** (iconița cu rotiță, jos în stânga):
   - **SOUL store**:
     - **Pre-launch mode**: lasă-l **bifat**.
     - **SOUL product**: îl alegi după pasul 5.
     - **Fallback price**: 249.
     - **Waitlist tag**: `waitlist`.
   - **Company (legal)**: vin deja completate din certificatul ONRC (verificate la ANAF pe 12.10.2026). Legea 365/2002 art. 5 le cere înainte ca magazinul să fie public:
     - Denumire: ARTEMIS DIGITAL S.R.L.
     - Sediu social: Str. Vlăhița nr. 1, bl. PM18bis, sc. 2, ap. 123, Sector 3, București
     - CUI: 53145290 (fără prefixul RO: firma nu e plătitoare de TVA)
     - Nr. Reg. Com.: J2025098748009 · EUID: ROONRC.J2025098748009
     - Email de contact: `office@krea.ro`
     - **VAT-registered** rămâne **debifat**. Așa, subsolul scrie „Neplătitor de TVA. Prețurile afișate sunt finale.” Dacă firma devine plătitoare de TVA, bifează-l, pune RO în fața CUI-ului și verifică textele despre preț.
   - **Brand and sharing**:
     - **Favicon**: logo-ul pătrat din `brand/SOUL-Brand-Package/Favicon`.
     - **Social share image**: o imagine de 1200×630, de exemplu randarea hero.
3. Apasă **Save**, apoi, din **Themes**, apasă **Publish** pe tema SOUL.

## 5. Creezi produsul SOUL cu cele 5 culori

1. **Products → Add product**.
   - Title: `SOUL`
   - Description: textul despre produs, scurt. Nu scrie nimic despre CE și nu pune recenzii.
   - Media: randările din `renders/v9`, cu text alternativ, de exemplu „Randare de concept: SOUL din aluminiu argintiu”.
   - Price: `249` EUR.
   - **Variants → Add options like size or color**:
     - Option name: **Colour**
     - Values: **Silver, Graphite, Midnight, Ember, Champagne**
     - Scrie exact aceste nume în engleză. Tema le recunoaște și pune culoarea și randarea potrivite.
   - **Inventory**:
     - Bifează **Track quantity**.
     - Pune cantitatea **0** la fiecare culoare.
     - **Debifează** „Continue selling when out of stock”.
     - Astfel, chiar dacă cineva ajunge pe un link direct, produsul nu se poate cumpăra.
   - **Shipping**: greutatea, când o știi.
   - Status: **Active**. Sales channels: **Online Store**.
2. Traducerea în română (gratuit):
   - Instalează aplicația **Translate & Adapt** de la Shopify.
   - Option name: **Culoare**.
   - Valori: **Argint, Grafit, Albastru noapte, Jar, Șampanie**. Tema le recunoaște și în română.
3. Întoarce-te la **Customize → Theme settings → SOUL store → SOUL product**, alege **SOUL** și apasă **Save**. De acum, prețurile de pe landing vin din produs și se convertesc pe piețe.

## 6. Paginile: Cum funcționează, Întrebări, Legal

**Online Store → Pages → Add page**. În dreapta, la **Theme template**, alegi șablonul:

| Pagină | Titlu (EN / RO prin Translate & Adapt) | Theme template |
|---|---|---|
| Cum funcționează | How it works / Cum funcționează | `how-it-works` |
| Întrebări | FAQ / Întrebări frecvente | `faq` |
| Date firmă | Company / Date firmă | `legal` (arată automat datele firmei din setări) |
| Cookie-uri | Cookies / Cookie-uri | `legal` |
| Garanție și conformitate (GPSR) | Product safety / Siguranța produsului | `legal` |

Apoi:

1. **Settings → Policies**: completezi **Privacy policy**, **Terms of service**, **Refund policy**, **Shipping policy** și **Contact information**. Shopify are un buton pentru șabloane, dar textele trebuie verificate de un avocat. Linkurile din subsol și din formularul de listă apar singure când politicile există.
   - Textul pentru **Privacy policy** (nota GDPR art. 13 pentru lista de așteptare: operator, scop, temei, păstrare, Shopify ca persoană împuternicită, drepturi, ANSPDCP), pentru retragere (14 zile, OUG 34/2014) și pentru garanția legală de 2 ani (OUG 140/2021) e gata în `site/legal.html`, în engleză și română. Îl copiezi în Privacy policy și Refund policy.
   - Garanția: creezi o pagină **Garanție** cu textul din `site/legal.html#warranty` și o alegi în **Theme settings → SOUL store → Warranty page**. Apare în subsol.
   - Linkul spre platforma ODR a UE nu mai există în subsol: platforma s-a închis pe 20 iulie 2025. Rămâne ANPC · SAL.
2. **Customize → Theme settings → SOUL store → Cookies page**: alege pagina „Cookie-uri”.
3. **Online Store → Navigation**:
   - Fă un meniu „Footer” cu paginile de mai sus.
   - În **Customize → Footer → Extra links menu**, alege meniul ăsta.
4. **Settings → Customer privacy**: pornește **Cookie banner** pentru UE (obligatoriu, GDPR).

## 7. Lista de așteptare: cum funcționează

- Formularul este formularul nativ Shopify de clienți.
- Fiecare înscriere creează un client cu acord de marketing pe email și cu etichetele:
  - `waitlist`
  - `colour-silver` / `colour-graphite` / `colour-midnight` / `colour-ember` / `colour-champagne`
  - `lang-en` sau `lang-ro`
- Bifa de acord e obligatorie. Fără ea, formularul nu se trimite.
- Recomandat: pornește confirmarea dublă (**double opt-in**), ca abonarea să fie confirmată prin email. O găsești în **Settings → Customer privacy** (în unele conturi apare la **Settings → Marketing**).

### Cum exporți lista

1. Deschide **Customers**.
2. Sus, în bara de căutare sau filtrare, scrie: `customer_tags CONTAINS 'waitlist'`. Sau folosește **Add filter → Tags → waitlist**.
3. Poți salva filtrul ca segment, de exemplu „Lista SOUL”.
4. Apasă **Export → Current search / segment → CSV for Excel**.
5. Coloana **Tags** arată culoarea preferată și limba fiecărui om.
6. Pentru anunțul de lansare folosește **Shopify Email**: **Marketing → Create campaign** și trimiți către segmentul „Lista SOUL”. Poți face câte un segment pe limbă, de exemplu cu `lang-ro`.

## 8. Domeniul

**Settings → Domains → Connect existing domain** (sau cumperi unul din Shopify) și urmezi pașii.

## 9. Deschizi site-ul (încă în prelansare)

1. **Online Store → Preferences → Password protection**: debifează parola. Merge doar după ce ai ales un plan la pasul 1.
2. Verifică pe telefon:
   - Bara de sus spune „încă fără certificare CE”.
   - Butonul **waitlist** duce la formular.
   - Formularul creează un client în **Customers**, cu etichetele de la pasul 7.
3. **Nu activa plățile** (**Settings → Payments**) până la CE.

## 10. După certificarea CE (lansarea vânzărilor)

1. **Settings → Payments**: activezi Shopify Payments (sau alt procesator).
2. Pe produs, pui stocul real la fiecare culoare.
3. **Customize → Theme settings → SOUL store**: **debifezi Pre-launch mode**.
   - Pe pagina produsului apare **adaugă în coș**.
   - În antet apare coșul.
   - Se activează sertarul de coș.
   - Bara „încă fără CE” dispare. Poți pune alt text în **Header group → Pre-launch bar → Text after launch**.
4. Abia acum scoți din texte „încă fără certificare CE” (**Edit default theme content**, căutând „CE”) și publici paginile legale finale.

---

## Ce e în temă (pentru cine face mentenanța)

- `layout/theme.liquid`: scheletul paginii, fonturile încărcate din temă și configurația pentru JS.
- `sections/`: câte o secțiune pentru fiecare bloc din landing v3:
  - `hero`, `marquee`, `alive`, `the-object`, `product-configurator`, `born-ritual`, `your-ai`, `soulos`, `ou-egg`, `privacy`, `specs-and-box`, `faq`, `waitlist`
  - grupurile `header-group.json` (bara de prelansare și antetul) și `footer-group.json` (subsolul și bara mobilă)
  - `main-product`, `main-page`, `cart-drawer` și paginile simple: `404`, `search`, `collection`, `cart`, `blog`, `article`
- `templates/`:
  - `index.json` este landing-ul.
  - `product.json` are culorile, lista de așteptare, „born with”, AI-ul tău, specificațiile și întrebările.
  - `page.how-it-works.json`, `page.faq.json` și `page.legal.json` sunt paginile de la pasul 6.
- `snippets/waitlist-form.liquid`: formularul `{% form 'customer' %}` cu etichete și acord.
- `sections/soulos.liquid`: SoulOS Alive într-o sticlă rotundă neagră. Patru ecrane din prototipul web (`os-alive-*.webp`, 440 și 880 px) se schimbă cu o clipire când apeși pe cele patru texte. Butonul „try SoulOS” apare doar dacă pui un link în setarea secțiunii.
- `snippets/soul-company.liquid`: datele firmei în subsol și pe pagina legală (sediu, CUI, Nr. Reg. Com., EUID, „Neplătitor de TVA”, email).
- `snippets/soul-price.liquid`: prețul „de la”, formatat de Shopify cu filtrul `money`, deci urmează moneda pieței.
- `locales/`: textele site-ului (`en.default.json`, `ro.json`) și textele din editor (`*.schema.json`).
- `assets/`:
  - `soul.css` și `soul-app.js` vin din landing v3.
  - `eyes.js` și `designs.js` sunt motorul de ochi.
  - `soul-product.js` gestionează variantele, iar `soul-cart.js` sertarul de coș.
  - Fonturile Bricolage Grotesque și Martian Mono vin din pachetul de brand (licență OFL).
  - Randările cu ochi vii sunt fișiere ale temei, nu imagini alese din editor, pentru că poziția sticlei e calibrată pe fiecare randare. Pozele produsului, favicon-ul, imaginea de distribuire și imaginile paginilor se încarcă din Admin și se servesc cu `image_url` / `image_tag`.
- Tema se poate regenera din landing cu `store/theme-src/build_theme.py`.
