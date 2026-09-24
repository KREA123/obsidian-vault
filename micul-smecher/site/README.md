# Pagina de lansare / precomandă SUFLET

Pagina de lansare pentru SUFLET („Micul Șmecher”). Totul e într-un singur fișier, `index.html` (~120 KB, cu CSS și JS inline), plus folderul `media/`. `preview.html` e o prezentare scurtă, în română, a ce s-a construit (pentru telefon).

```
site/
├── index.html            # pagina completă, EN implicit + comutator RO/EN
├── preview.html          # prezentare pe o pagină, în română, pentru fondator
├── media/
│   ├── *.mp4             # clipuri din simulatorul firmware-ului (copiate din ../media)
│   ├── posters/*.jpg     # primul cadru al fiecărui clip (se vede înainte să pornească video-ul)
│   └── render-*.jpg      # randări web (hero, lineup, bag, desk, night, inside), fiecare + varianta -sm pentru telefon
└── screenshots/          # capturi Playwright 390×844 și 1440×900 (doar pentru verificare; nu se publică)
```

## Ce face pagina

- **Hero cu ochi vii** pe `<canvas>`. Este portul în JS al `firmware/lib/Suflet/src/Face.cpp`: elipse crem #FFF0C8 (0,12 × 0,19 din diametru, centre la ±0,19), pleoapa înclinată 0,16 rad, highlight și halo. Ochii clipesc (la 2,2–6 s, uneori de două ori), urmăresc cursorul sau degetul cu un arc elastic, se uită singuri în jur și respiră (±2 % la 4 s). O atingere face „boop” (^ ^, obraji roșii, inimioare, turtire), două atingeri îi fac să râdă (> <). După 15 s fără activitate SUFLET-ul ațipește, apoi adoarme (arce închise și z z), iar orice mișcare îl trezește. Cu `prefers-reduced-motion` totul rămâne static.
- **Pietrele din pagină sunt toate vii**: cele trei din secțiunea 3-în-1 (viu / ascultă / Claude), demo-ul interactiv „Works with Claude” (ții apăsat 1,2 s ca să aprobi, atingi de două ori ca să refuzi; de la tastatură, Space ține, Esc refuză), certificatul de naștere (butonul „Hatch another” naște un suflet nou, cu raritățile din firmware) și piatra de la formular, care doarme până începi să scrii.
- Clipurile rulează doar când sunt vizibile pe ecran (IntersectionObserver).
- Alegerea limbii se păstrează în `localStorage`. Pagina se poate deschide direct în română cu `index.html#ro`.

## Cum schimbi prețurile, datele și endpoint-ul

Toate aceste valori sunt într-un singur obiect, `window.SUFLET_CONFIG`, chiar la începutul lui `index.html`:

```js
window.SUFLET_CONFIG = {
  WAITLIST_ENDPOINT: "",          // URL-ul la care formularul trimite JSON (gol = mod demo)
  CURRENCY: "EUR",
  PRICES: { founders: 119, voiceDeposit: 10, voiceExpected: 149 },
  FOUNDERS_RANGE: "001–300",
  VOICE_AI_MONTHS: 6,
  SHIP: { founders: { en: "spring 2027", ro: "primăvara 2027" },
          voice:    { en: "autumn 2027", ro: "toamna 2027" } },
  CONTACT_EMAIL: "hello@suflet.example"
};
```

Valorile se completează automat peste tot, inclusiv în FAQ și în ambele limbi: `data-price="founders"` afișează prețul, iar `data-cfg="shipFounders"` afișează data.
Formatul prețului: în EN „€119”, în RO „119 €”.

**Datele de livrare (`SHIP`) sunt provizorii.** Pune-le pe cele reale înainte de lansare.

## Cum schimbi textele

- **Engleza** stă direct în HTML. Fiecare text traductibil are un atribut `data-i18n="cheie"`. Pentru atribute precum `aria-label` și `alt` se folosește `data-i18n-attr="aria-label:cheie"`.
- **Româna** stă în obiectul `const RO = { ... }` din scriptul de la finalul paginii, cu aceleași chei.
- Textele generate din JS (terminalul din demo-ul Claude, erorile formularului, certificatul) sunt în `const DYN = { en: {...}, ro: {...} }`.
- Dacă adaugi un text nou: pune `data-i18n="cheie.noua"` în HTML și `"cheie.noua": "…"` în `RO`. Când o cheie lipsește din RO, pagina afișează textul în engleză.

## Formularul (waitlist)

Trimite prin `POST` un JSON `{email, edition, consent, lang, ts, source}` la `WAITLIST_ENDPOINT`, cu `Content-Type: application/json`.

- **Endpoint gol (acum):** înscrierea se salvează doar în browserul vizitatorului (`localStorage`, cheia `suflet-waitlist`) și apare mesajul de mulțumire. **În acest mod nu primești niciun email.** E bun doar pentru demo.
- Variante reale (endpoint-ul trebuie să accepte CORS și JSON):
  - **Formspree / Getform / Basin**: creezi un formular, primești un URL `https://formspree.io/f/xxxx` și îl pui în `WAITLIST_ENDPOINT`.
  - **Brevo / Mailchimp / Klaviyo**: printr-o funcție serverless mică (Netlify Function sau Cloudflare Worker) care primește JSON-ul și îl adaugă în listă. Cheia API nu se pune niciodată în pagină.
  - **Google Apps Script** (Web App) care scrie într-un Google Sheet: gratuit, dar cu grijă la GDPR, adică datele trebuie să rămână în UE sau să ai temei legal.
- Formularul are un câmp-capcană ascuns (`website`) contra boților, validare de email și bifă de consimțământ obligatorie.
- Recomandat: double opt-in (email de confirmare) din serviciul folosit.

## Randările și varianta de rezervă

Imaginile `media/render-*.jpg` sunt generate din `../renders/*.png` (Blender) și din modelul CAD, cu:

```bash
python3 ../renders/src/export_web.py              # decupează + comprimă (JPEG progresiv, < 400 KB, 2 lățimi)
python3 ../renders/src/export_web.py --cad-hires  # re-randează și vederea explodată CAD la 1500 px (OpenSCAD, ~45 s)
```

Unde apar în pagină:

| Imagine | Secțiune | Ce arată |
|---|---|---|
| `render-hero` (4:3) | Design | Moneda albă, 3/4 |
| `render-bag` (4:5) | Design | Picătura pe mânerul unei genți |
| `render-lineup` (2:1) | Design | Cele 4 forme: nor, monedă, cabochon, picătură |
| `render-inside` (4:5) | Design → „Inside” | Vedere explodată CAD, moneda 1,43″ varianta Founders (fără baterie) |
| `render-desk` (16:9) | Works with Claude | Moneda pe suport lângă laptop |
| `render-night` (16:9) | Charter | Moneda noaptea, lampă de veghe |

Fiecare `<img>` are `srcset` (varianta `-sm` pentru telefon), `alt` și legendă în EN/RO (cheile `design.cap*`, `design.alt*`, `in.*`, `claude.cap`, `claude.alt`, `charter.cap`, `charter.alt` din obiectul `RO`).
Dacă `render-hero` sau `render-lineup` lipsesc, handler-ul `onerror` le ascunde și afișează siluete SVG inline (monedă, picătură, cabochon, nor, la scară, cu dimensiunile din CAD).

Fiecare randare are eticheta „Concept render” / „Randare de concept”, iar vederea explodată are eticheta „CAD”. Păstrează-le până există fotografii ale unui prototip real.

## Testare locală

```bash
cd micul-smecher/site
python3 -m http.server 8000     # apoi deschide http://localhost:8000
```

(Deschis direct ca `file://`, pagina funcționează, dar unele browsere blochează clipurile.)

## Publicare (deploy)

1. **GitHub Pages**: pui conținutul folderului `site/` într-un repo (sau în `/docs`), apoi Settings → Pages → Deploy from branch. Poți adăuga un domeniu propriu (fișier `CNAME`). Gratuit, HTTPS inclus.
2. **Netlify**: tragi folderul `site/` în app.netlify.com/drop, sau conectezi repo-ul cu publish directory `site`. Primești HTTPS, domeniu propriu, Netlify Forms sau Functions pentru waitlist. Cea mai simplă variantă.
3. **Shopify** (dacă magazinul e pe Shopify):
   - *Varianta simplă*: găzduiești pagina pe Netlify sau GitHub Pages (de exemplu `suflet.ro` sau `launch.suflet.ro`) și din Shopify faci link sau redirect spre ea.
   - *Varianta în temă*: Online Store → Themes → Edit code → creezi template-ul `page.suflet.liquid` (sau o secțiune „Custom Liquid”) și lipești conținutul din `<style>`, `<body>` și `<script>`. Clipurile și PNG-urile le urci în Content → Files și schimbi căile `media/...` cu URL-urile Shopify CDN. Pagina de conținut simplă din editorul Shopify elimină scripturile, deci ai nevoie de template.
   - Precomanda cu plată se face apoi prin produse Shopify (avans de 10 € ca produs separat) și aplicații de pre-order. Nu se face prin formularul acesta.

Pagina se poate previzualiza și ca artifact pe claude.ai: are tokenuri de culoare, temă întunecată, lățime de telefon și fonturi Google.

## Checklist înainte de lansare

**Legal și firmă**
- [ ] Footer: denumirea reală (acum `ARTEMIS DIGITAL S.R.L. [placeholder]`), adresă, CUI, Nr. Reg. Com. și email de contact (`CONTACT_EMAIL`). Toate câmpurile marcate cu portocaliu sunt placeholdere.
- [ ] **GPSR** (Reg. UE 2023/988): numele și adresa poștală și electronică a producătorului, identificatorul produsului (tip, model, lot sau serie; acum `[SF-143]`/`[SF-175]` sunt inventate), avertismente („Nu este jucărie”, 16+, baterie litiu la Voice Edition), instrucțiuni în română.
- [ ] Politica de confidențialitate, Termenii de vânzare și Cookies: acum sunt linkuri `#privacy`, `#terms`, `#cookies`. Trebuie pagini reale (GDPR: operator, scop, temei, durată, drepturi, transferuri).
- [ ] Linkul ANPC SAL e deja pus. Adaugă și pictogramele ANPC dacă vinzi efectiv.
- [ ] Când începi să încasezi bani: butonul de retragere (obligatoriu din 19.06.2026, Directiva 2023/2673), dreptul de retragere de 14 zile, garanția legală de 2 ani, data estimată de livrare și dreptul de anulare cu rambursare dacă întârzii (vezi `../research/03-compliance-2026-09-24.md`). Nu încasa plata integrală înainte de DVT.
- [ ] Disclaimer-ul despre Claude/Anthropic rămâne în footer. Nu folosi logo-ul Anthropic sau Claude.

**Prețuri și promisiuni**
- [ ] `PRICES`, `SHIP` și `FOUNDERS_RANGE` în `SUFLET_CONFIG`, apoi verifică textul „Prices include VAT”.
- [ ] Tot ce promite pagina trebuie să fie adevărat la lansare: servere în UE, memorie care poate fi citită și ștearsă, publicarea firmware-ului dacă firma dispare, baterie înlocuibilă, fără cameră, 6 luni de AI vocal incluse. Șterge ce nu poți garanta.
- [ ] „Voice Edition · in development” rămâne până funcția e gata.

**Tehnic**
- [ ] `WAITLIST_ENDPOINT` setat și testat cap-coadă (înscriere → apare în listă → email de confirmare).
- [ ] Domeniu, HTTPS, imaginea `og:image` (acum `media/posters/idle.jpg`; ideal o imagine 1200×630 cu URL absolut).
- [ ] Dacă adaugi analytics: banner de consimțământ pentru cookie-uri.
- [ ] Test pe iPhone (Safari) și Android (Chrome): atingere, dublă atingere, ținut apăsat în demo, clipuri, comutator RO/EN, formular.
- [ ] Rulează din nou capturile Playwright și verifică să nu apară scroll orizontal și erori în consolă.
