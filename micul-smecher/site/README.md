# Landing SOUL v3

Pagina publică pentru SOUL. Se publică doar ce e în lista de mai jos. Folderele `screenshots/`, `_archive/` și `_tools/` nu se publică (`_archive/v2-superseded/` = landing-ul vechi v2, pe mărimea M; e depășit, nu-l republica).

```
site/
├── index.html        # landing v3 (EN implicit, comutator RO), CSS inline
├── app.js            # logica paginii + dicționarul RO
├── legal.html        # nota de confidențialitate, cookie-uri, termeni, retragere, garanție (EN + RO)
├── os.html           # demo SoulOS (îl întreține alt flux; nu-l edita de aici)
├── eyes/             # motorul de ochi (eyes.js) + cele 120 de modele (designs.js)
├── fonts/            # Bricolage Grotesque + Martian Mono, găzduite local
├── media/v10 (S: hand-s, side-s, desk-s, og-s.jpg), media/v3, media/v2, media/v4
├── _tools/site_media_v10.py  # desk-s (sticla golită + harta sticlei) și og-s.jpg din renders/v10; nu se publică
└── favicon.*, icon-*.png, apple-touch-icon.png, site.webmanifest
```

## Ce e adevărat pe pagină

- Produsul e **mărimea S** (sursa unică: `docs/size-s.json`): 63 × 70,8 × 23 mm, sticlă plată Ø52, AMOLED rotund 1,75″ 466 × 466, LiPo 750 mAh, ≈ 85 g. Bateria (cam o zi, 21–34 h) și greutatea sunt **estimări** și pe pagină scrie asta. Prototipul de lucru e M (2.8C); pe pagină nu apare.
- Imaginile unde se vede mărimea vin din `renders/v10`: mâna (`hand-s`), profilul (`side-s`) și „la scară, lângă un telefon” (`desk-s`, telefon generic 71,5 × 147 mm). Restul randărilor (față, culori, familie, noapte) au aceeași formă MĂRGĂRITAR și nu arată mărimea.

- Prelansare: doar listă de așteptare. Nu se plătește nimic, nu există precomandă, avans sau ediție „Founders”.
- Preț: **de la 249 €**, preț final. ARTEMIS DIGITAL S.R.L. e neplătitoare de TVA (ANAF, scpTVA=false, verificat pe 12.10.2026), deci pagina nu scrie „cu TVA”; subsolul spune „Neplătitor de TVA”. Dacă firma devine plătitoare de TVA, adaugă textul înapoi și prefixul RO la CUI.
- Fără certificare CE încă. Pagina nu pretinde CE.
- AI: owner-ul își aduce propriul AI. Claude: propria cheie API Anthropic + SOUL adăugat ca conector personalizat în aplicația Claude. ChatGPT: propria cheie API OpenAI (în dezvoltare); „Sign in with ChatGPT” așteaptă aprobarea OpenAI. Sau offline.

## Configurare (`window.SOUL_CONFIG`, la începutul lui `index.html`)

```js
window.SOUL_CONFIG = {
  WAITLIST_ENDPOINT: "",   // "" = mod demo: înscrierile rămân în browser
  CURRENCY: "EUR",
  PRICES: { from: 249 },
  SHIP: { en: "after CE testing", ro: "după testele CE" },
  CONTACT_EMAIL: "office@krea.ro",
  COMPANY: { address: "Str. Vlăhița nr. 1, bl. PM18bis, sc. 2, ap. 123, Sector 3, București",
             cui: "53145290", reg: "J2025098748009", euid: "ROONRC.J2025098748009" }   // certificatul ONRC, verificat la ANAF
};
```

Datele firmei sunt scrise și direct în HTML-ul subsolului (se văd și fără JavaScript) și în `legal.html`. Dacă se schimbă ceva, schimbă-le în toate trei locurile. Telefonul firmei nu se publică.

## Înainte de orice URL public (checklist)

- [x] `COMPANY` completat din certificatul ONRC (Legea 365/2002 art. 5): sediu, CUI 53145290 (fără „RO”, firma nu e plătitoare de TVA), J2025098748009, EUID ROONRC.J2025098748009.
- [ ] Nota de confidențialitate din `legal.html` citită și confirmată (perioada de păstrare de 24 de luni, Shopify ca persoană împuternicită).
- [ ] Domeniul ales, apoi: `og:image` cu URL absolut, `<link rel="canonical">`, `/ro/` ca URL separat cu `hreflang`, `sitemap.xml`.
- [ ] Lista de așteptare reală: în Shopify (tema din `store/`), formularul nativ de client. Pe site-ul static, `WAITLIST_ENDPOINT` către un serviciu care respectă nota de confidențialitate.
- [ ] Termenii de vânzare, retragerea, garanția și datele GPSR se completează înainte să se deschidă rezervările.

## Tema Shopify

Tema din `store/theme` se generează din `index.html` + `app.js`: `cd store/theme-src && node extract_ro.js && python3 build_theme.py`. Verificare: `npx --yes @shopify/theme-check-node` (0 erori).
