---
tip: ghid
afacere: Micul Șmecher
actualizat: 2026-10-22
versiune: 3
---

# SOUL pe Indiegogo: cum îl postezi, pas cu pas

Pentru Andu. **v3** (22.10.2026, după review-ul kitului: 25 de probleme reparate) înlocuiește v2 și v1. **Ce decizi tu e în [`DECIZII-FONDATOR.md`](DECIZII-FONDATOR.md).** v1 lansa în aprilie 2027, înainte de CE, cu obiectiv €270k. v3 urmează `facts.json` și `PLAN.md` v3: **lansare după CE, marți 05.10.2027, obiectiv €70.000**.

> **Înainte de orice: expertul științific.** Campania are nevoie ca PoC 1.1 să fie decis, iar PoC 1.1 e blocat de expert. Ce faci săptămâna asta e în [[Finanțare — expertul științific pentru PoC 1.1]]: 3 căi în paralel (inginer embedded senior angajat pe CIM ca expert intern · emailul gata scris către Tudose, Radovici și Cucu de la UPB · PRECIS / transfer tehnologic UPB sau EDIH).

**Cum citești ghidul**
- Toate căile pornesc din `micul-smecher/crowdfunding/`. Textele (engleză) sunt în `campaign/`, traducerea pentru tine în `campaign/ro/`, imaginile în `images/`.
- `HC/478` = articolul `https://help.indiegogo.com/article/478` (centrul de ajutor Indiegogo, citit pe 20–22.10.2026).
- **Contul, actele, firma, banca, termenii și „Submit” le faci doar tu.** Claude nu vede parole, acte sau date bancare.
- Dacă o cifră de aici nu se potrivește cu `facts.json`, are dreptate `facts.json`.

---

## A. Ce îți trebuie înainte (le faci tu)

### A1. Testul gratuit: până duminică, **15.11.2026**
1. Îți faci cont pe indiegogo.com.
2. Avatar → **Go to admin area** → **Creator** → **My Projects** → **+ Add a project** → **Indiegogo campaign** (HC/515).
3. În **General setup** verifici: *Legal entity type* = **Business**, *Location* = **Romania**, *Currency* = **EUR**.
4. În tabul **Business** încerci nr. de registru și CUI-ul (vezi A2). Nu trimiți nimic.
5. Merge? Notezi în `03 Decizii/Jurnal decizii.md`. Nu merge? Îmi spui. Rezervele, în ordine: Ulule, precomenzi pe site-ul nostru după CE, Crowd Supply (`PLAN.md` §1).

### A2. Verificarea firmei (KYC, prin Adyen): în **martie 2027**
Unde: **Business account details** (HC/470), apoi **Submit for review**.
Fără KYC aprobat **nu poți publica nici pagina de pre-lansare** (HC/484).

| Câmp | Ce pui | Atenție |
|---|---|---|
| Tip cont | **Business** | nu „Individual”, nu „Sole proprietorship” |
| Denumire | ARTEMIS DIGITAL S.R.L., exact ca la ONRC | |
| Nr. Registrul Comerțului | **J2025098748009**, exact ca pe certificat | exemplul lor e formatul vechi (`J40/8302/1997`). Dacă refuză → Support |
| CUI | **53145290** (fără RO, firma nu e plătitoare de TVA) | eroarea „missing country prefix” e cunoscută (HC/507). Dacă refuză → Support. Dispare dacă te înregistrezi în scopuri de TVA (D2) |
| Adresa | cea din registru; strada și numărul în câmpuri separate | |
| Telefon | cu **+40** | |

**Documente** (JPG, PNG sau PDF, max. 15 MB; imagini min. 100 KB) (HC/504, HC/505):
- [ ] **Certificat constatator** ONRC, din ultimele 12 luni + **traducere în engleză** (pot cere traducere autorizată).
- [ ] **Extras / scrisoare de la bancă**, din ultimele 12 luni: **numele exact al firmei**, **IBAN-ul complet**, sigla sau ștampila băncii.
- [ ] **Buletin sau pașaport** al administratorului: color, valabil, cu rândurile de jos (MRZ) vizibile. **Fața și spatele în fișiere separate.**
- [ ] Actele asociaților principali, dacă le cer.

### A3. Banii: ce cont îți trebuie
- **Doar contul bancar al firmei**, în EUR (sau RON): IBAN românesc de 24 de caractere (HC/506).
- **Stripe: nu.** Campaniile noi merg prin **Adyen**, iar contul Adyen se face singur din KYC (HC/599, HC/645).
- **Payoneer: nu.** Nu e cerut nicăieri. Documentul trebuie să vină de la bancă, pe numele firmei.
- **Metodă de plată de rezervă:** un card al firmei, din care se plătesc rambursările dacă soldul nu ajunge. Project → Settings → Backup payment method (HC/611).
- Comisioane: **5 % + 3 % + €0,20** pe plată (la €249 = €20,12). Dacă obiectivul nu e atins, **nu plătești nimic** (HC/596).
- Plăți: **vinerea noaptea** (CET), cu o **rezervă de 5 %** ținută 6 luni (HC/474, HC/766). Pot cere și acte în plus (oferte, contracte de producție) dacă te consideră „risc ridicat”.

### A4. La contabil (până pe 07.09.2027)
- [ ] **D2: TVA + OSS.** Vânzările în alte țări UE peste €10k declanșează OSS; pragul de 395.000 lei depinde de suma strânsă. Prețurile rămân **€249 / €269, finale**.
- [ ] Rămâne ARTEMIS microîntreprindere?
- [ ] Facturile către susținători.

---

## B. Pas cu pas în editorul Indiegogo

### B1. General setup (HC/485)

| Câmp | Ce pui | De unde / atenție |
|---|---|---|
| Project name | `SOUL: Living Eyes for Your Own AI` | `campaign/01-title-tagline.md` → CHOSEN |
| Short description | `A palm-sized aluminium desk companion that looks up when your AI needs you. Or keep it offline.` | același fișier. Limitele de caractere le vezi în draft |
| Project URL | `soul-living-eyes` | ⚠️ se blochează când publici pre-lansarea |
| Category | Tech & Innovation → Gadgets (sau cea mai apropiată) | ⚠️ se blochează când publici pre-lansarea |
| Tags | lista din `01-title-tagline.md` | |
| Thumbnail | `images/01_card_thumbnail_700x700.jpg` | cazul de folosire principal + telefonul pentru mărime |
| Cover | `images/02_cover_1743x498.jpg` | fără text |
| Social image | `images/03_social_share_1200x630.jpg` | |
| Avatar | `images/04_avatar_700x700.png` | |
| Contact | office@krea.ro | |
| Legal entity / Location / Currency | Business / Romania / EUR | |
| **Funding** | **Fixed (totul sau nimic)**: e singurul tip | nu „Express”, nu „Preorders” (HC/641, HC/690) |
| **Campaign goal** | **70000** EUR | ⚠️ se blochează la lansare. Îl recalculăm pe 07.09.2027 cu ofertele scrise (`tools/goal_model.py`) |
| Launch date | **marți 05.10.2027, 09:00**, ora României | min. 7 zile după Submit |
| End date | **marți 09.11.2027** (35 de zile) | ⚠️ se blochează la lansare |
| Endgame | pornit | |
| Displayed funding value | only crowdfunding | |

### B2. Pagina: Project settings → Project Details → Detailed description (HC/483)
1. Deschizi **`campaign/story-paste.html`** în browser. Are câte un buton **„Copy section”** pentru fiecare secțiune.
2. În Indiegogo, tabul **Crowdfunding campaign**: faci o secțiune nouă, apeși „Copy section”, lipești.
3. La fiecare `[IMAGE: fișier]` urci fișierul din `images/` și **pui legenda de sub el**, exact cum scrie în `campaign/00-image-map.md`.
4. Publici secțiunea (rama galbenă = nepublicată).

| Secțiunea | Din `story-paste.html` |
|---|---|
| Story | Story (sus: linkul YouTube al filmării reale cu SOUL S) |
| Specs | Specs |
| Budget & timeline | Budget & timeline |
| Team | Team + **poza ta reală, numele și 60–80 de cuvinte** (`story_13_team_PLACEHOLDER.png` nu se publică; F4 în `DECIZII-FONDATOR.md`) |
| Risks and challenges (obligatorie) | Risks and challenges, integral |
| Refunds and cancellation (obligatorie) | Refunds and cancellation, **după avocat** |

**Legende, obligatoriu:**
- randare → „Render (CGI), not a photo.”
- orice poză sau film cu prototipul M → „Prototype shown at a larger size (M). The product you back is S: 63 × 71 mm with a 1.75″ AMOLED.”
- ecrane SoulOS (toate sunt din simulator; firmware-ul n-a rulat încă pe o placă reală) → „SoulOS simulator capture at the S screen size (466 × 466). Not a recording of a real device.” „SoulOS (shown on the prototype)” doar pentru filmări reale de pe placă.
- randările v10 cu ochii redesenați (`story_06b_in_hand.jpg`, `story_06c_on_desk.jpg`, `gallery_6_in_hand`) → „Render (CGI), not a photo. Eyes drawn by the SOUL eyes engine.”
- mărimea o arăți **doar** cu `gallery_2_size_1200x630.png` / `story_06_size.png` sau cu randările S de mai sus. **Niciodată** `soul_v9_hand.png` sau `soul_v9_desk.png`.

**Animațiile:** MP4 (`anim_1…`, `anim_2…`, `anim_3…`), nu GIF.

**Galeria de sus**, în ordinea asta: videoul real (YouTube, G2) · `gallery_1_approve` (cazul principal: Claude întreabă, tu aprobi) · `gallery_2_size` · `gallery_3_hero` · `gallery_4_eyes` · `gallery_5_colours` · `gallery_6_in_hand`. Până la G2, singurul înlocuitor acceptat pe pagina de pre-lansare e o filmare reală cu M, etichetată (F2).

**FAQ:** Project → Communication → FAQ → **+add question**, câte una din secțiunea „FAQ tab” din `story-paste.html` (sursa e `05-faq.md`) (HC/523).
**Română (opțional):** Project settings → Translations → RO, din `campaign/ro/` (HC/525).

### B3. Recompensele: Products → Rewards (HC/478)
Sursa: **`campaign/perks.csv`** (un rând = o recompensă; tabelul explicat e în `03-perks.md`).

**Întâi, o singură dată:** faci produsul **„SOUL S”** cu opțiunea **Colour: Silver / Graphite / Ember** (SKU `SOUL-S-SIL / -GRA / -EMB`, fără diferență de preț) și produsul **„OU charging egg”**.

| Coloana din CSV | Câmpul din Indiegogo |
|---|---|
| `title` | Reward name |
| `price_eur` | **Regular price.** *Discount price* rămâne **gol** (fără preț tăiat, fără „% off”) |
| `description` + `shipping` | Description (lipești `shipping` la final) |
| `items` | Reward items → **+ add a product to this reward** |
| `cap` | Stock (First Light **150**, Campaign Price **100**, Two Souls **10**; „Campaign Price · batch 2” fără limită) |
| `per_backer_limit` | Per-backer limit, **pe recompensă** (First Light = 1) |
| `estimated_delivery` + `delivery_remark` | lotul 1: **May 2028** + „EU: May 2028 (estimate)”; lotul 2 și Late Pledge: **August 2028** + „Batch 2, EU: August 2028 (estimate)” |
| `ships_to` | Available only in: RO, DE, AT, FR, BE, NL, IT, ES, PL, SE (fără UK, D13). Supporter: oriunde |
| `image` | fișierul din `images/` |
| `pin` | fixezi **First Light**; după ce se epuizează, **Two Souls** |

| Recompensa | Preț | Unde |
|---|---|---|
| Soul Supporter (fără SOUL) | €10 | Rewards |
| First Light (primii 150, numărul gravat pe picior) | €249 | Rewards |
| Campaign Price (lotul 1, 100) | €269 | Rewards |
| Two Souls (2 × SOUL S, 10 seturi) | €498 (€249 bucata) | Rewards. Pui „SOUL S” de **2 ori**, ca fiecare să-și aleagă culoarea |
| Campaign Price · batch 2 | €269 | Rewards, luna de livrare august 2028 (`reward_3b_campaign_batch2_700x700.jpg`) |
| Extra OU egg | €35 | **Products → Add-ons** |
| Late Pledge | €299 | **abia după campanie** (E2) |

- **Ochii nu sunt opțiune, recompensă sau add-on.** Niciodată.
- Project settings → Orders: **nu** permiți comenzi doar cu add-on (HC/497).
- **Stretch goals** (Project settings → Stretch goals → automatic, „backed funds”) (HC/491): **€95.000** limbi (`stretch_1_languages_700x700.png`) · **€130.000** săculeț de fetru (`stretch_2_felt_pouch_700x700.png`) · **€175.000** certificat de naștere tipărit (`stretch_3_birth_card_700x700.png`). SUA/Canada nu mai e stretch goal (D14).
- **Follower gift:** decizi **înainte** de pre-lansare, apoi nu se mai schimbă (HC/490). Propunere: pachetul digital de wallpapere cu ochi. Fără reducere.

### B4. Livrare și taxe: Project → Settings → Shipping and taxes (HC/469, HC/623)
Transportul are **tarife fixe**, afișate înainte să susțină cineva, și **se plătește după campanie**, în Pledge Manager. Dacă firma de curierat cere mai mult, diferența o plătim noi. Îl setezi acum ca să-l testezi.
1. **Locations:** oprești tot, în afară de cele 10 țări (fără UK, D13).
2. **Zone și prețuri** (un singur model, „Courier”, default):

| Zona | Țări | Pe colet |
|---|---|---|
| RO | România | €6 |
| EU-1 | DE, AT, PL, NL, BE | €12 |
| EU-2 | FR, IT, ES, SE | €15 |

   +€4 pentru fiecare SOUL în plus din același colet. OU-ul în plus merge gratis.
3. **Taxe:** cotele de TVA din UE vin precompletate. **Le pui pe toate pe 0 %**, ca susținătorul să plătească exact €249 / €269 (HC/597). 
4. **Test:** Project Settings → Testing → te inviți ca tester și faci câte o comandă de test pe fiecare recompensă (HC/521).

### B5. Setări mici
- **Stretch Pay:** oprit.
- **Stable Pledge (D10):** ireversibil, doar înainte de lansare. Îl pornești **numai** dacă ai toate ofertele de producție și de curierat în scris (HC/471).
- **Analytics:** Meta Pixel + Google Analytics (HC/481).
- **Referral links:** câte unul pentru site, email, Instagram, TikTok, reclame (HC/488).

### B6. Pagina de pre-lansare („Upcoming”) și lista de pe site
- **Când:** în **martie 2027**, după KYC și după filmarea reală (G2, 12.02.2027).
- Ce pui în tabul **Crowdfunding draft**: videoul real, `story_01_object.jpg`, `story_02_eyes.png`, două paragrafe din Story și „Follow to get an email the minute we launch.” Fără recompense (altfel se văd prețurile de acum).
- Dashboard → **Publish project preview**. Lumea poate doar da **Follow**, nu plătește (HC/484).
- **Lista de pe site:**
  1. ⚠️ Azi formularul de pe site e în **mod demo** (`WAITLIST_ENDPOINT: ""` în `site/index.html`): înscrierile nu ajung nicăieri. **Înainte de orice reclamă**, legăm o platformă de email din UE, cu dublă confirmare. Lista rămâne a noastră.
  2. După ce publici pre-lansarea, îmi dai linkul. Pun pe site butonul **„Follow SOUL on Indiegogo”** cu linkul de referral „site”.
  3. Emailurile din `campaign/07-prelaunch-emails.md` trimit lista la Follow.
  4. În ziua lansării butonul devine **„Back SOUL on Indiegogo”**. Pe site nu scrie niciodată „precomandă”.

---

## C. Checklist înainte de lansare

**Go / no-go: marți 07.09.2027.** Submit for review: **marți 21.09.2027**. Dacă un punct nu e bifat, **amâni** (cel mai probabil la ~februarie 2028).

- [ ] **PoC 1.1 decis** (regula ta, D1). Depinde de expertul științific.
- [ ] **G1** (15.12.2026): SoulOS + voce pe placa S, cu cheile tale.
- [ ] **G2** (12.02.2027): **SOUL S din aluminiu, filmat funcționând, dintr-o singură dublă**, pe YouTube. **Fără el nu se lansează.**
- [ ] Orice imagine cu M are legenda „Prototype shown at a larger size (M)…”. Orice randare are „Render (CGI), not a photo.”
- [ ] **CE:** testele trecute și **declarația UE de conformitate semnată** (31.08.2027). Marchezi CE ca trecut în `facts.json → gates` (laborator, dată), refaci textele: dispar marcajele `[[CE: …]]`. Pagina live e scrisă într-o singură stare (după CE); „not CE-certified yet” apare doar în emailurile către lista de așteptare. **Nicio siglă CE.** Nicio unitate împrumutată creatorilor înainte de declarație.
- [ ] Rândul „SOUL does not include AI” + disclaimerul de mărci sunt pe pagină. Niciodată „ChatGPT account”: doar propria cheie API OpenAI (în dezvoltare). Fără sigle Claude sau OpenAI.
- [ ] `python3 -I micul-smecher/crowdfunding/tools/check_copy.py --strict` trece. Nu a rămas niciun `[[G…]]`, `[[CE…]]`, `{{URL:…}}`, `[de completat]`. Vârsta (D4) e 18+ până decizi altfel.
- [ ] **TVA / OSS (D2)** făcut cu contabilul. Cotele UE în Indiegogo pe 0 %.
- [ ] Ofertele scrise sunt în limita +15 % (altfel recalculăm obiectivul). Capacitatea lotului 1 (D12) confirmată în scris. D9 (data livrării) și D10 (Stable Pledge) decise.
- [ ] Textul de rambursări și rezerva verificate de avocat (D15). Politica de confidențialitate are link.
- [ ] **Lista de email: min. 3.300 de adrese confirmate** (ținta 5.000). Între 2.500 și 3.299 mergi doar cu ≥ 1.000 de Follow pe Indiegogo. Sub 2.500 → amâni.
- [ ] **Reclamele gata:** creativele cu legende, publicurile, pixelul. Plafon **€6.600** în campanie; continui doar la **ROAS ≥ 5×**.
- [ ] KYC aprobat, card de rezervă pus, comenzile de test trecute.
- [ ] Poza ta, numele și povestea puse (F4); filmarea reală cu SOUL S prima în galerie (F1). Follower gift decis.
- [ ] Presa primește materialele cu embargo până pe 05.10, 09:00. Fără „as seen in” până nu apare ceva publicat.

---

## D. Ziua lansării: marți 05.10.2027

| Când | Ce faci |
|---|---|
| Seara dinainte | Pleacă emailul „Tomorrow, 09:00”. Verifici ora pe calculator. |
| **09:00** | Campania pornește singură. Verifici pagina și o plată. |
| 09:00 | **Emailul de lansare** (`08-launch-emails.md` #1, cu `05_launch_email_700x700.jpg`). Postările din `11-social-posts.md`. Butonul de pe site → „Back SOUL”. |
| 09:00 | Pornesc reclamele: întâi lista și vizitatorii site-ului. |
| 13:00 | Al doilea email, scurt, celor care n-au deschis. |
| Toată ziua | Răspunzi la **fiecare** comentariu în max. 2 ore. Doar adevărul. |
| Seara | Update #1 cu cifrele reale (`06_update_header_700x700.jpg`). Apeși **„send notifications”**, altfel nu pleacă pe email (HC/489). |
| Ziua 2 | Al treilea email. Ținta: **30 % din obiectiv în prima zi** (≈ €21.000, ≈ 83 de susținători). |
| Ziua 3 | Ținta: **50 %**. Dacă ești sub, încă un email și postările creatorilor. |

Pe urmă: 2 update-uri pe săptămână, emailuri în ziua 17 și în ultimele 48 h. Oprești orice set de reclame sub ROAS 5×.

---

## E. După campanie (de pe 09.11.2027)

### E1. Banii
- Plățile se încasează 15 zile (10–26.11), cu 3 reîncercări (HC/637).
- Banii vin **vinerea**, din ~19.11, minus rezerva de 5 %.
- Rambursările le faci tu, din **Orders**.

### E2. Late Pledge (fostul „InDemand”)
- Pe ~**16.11.2027**: Dashboard → **Late Pledge setup** → Submit. Pauza e de până la 15 zile, comisioanele la fel (HC/602).
- Se deschide pe ~**30.11.2027**: recompensa „Late Pledge” cu **€299** (`reward_6_late_pledge_700x700.jpg`). Se livrează cu lotul 2 (august 2028).
- ⚠️ **Întâi Late Pledge, apoi Pledge Manager.** Invers nu mai merge.

### E3. Pledge Manager
- Susținătorii confirmă culoarea și adresa, plătesc transportul, pot adăuga OU (HC/494).
- Fabrici doar pentru comenzile plătite.

### E4. Livrarea
- **Tot ce vine din China comandat până pe 10.12.2027** (Anul Nou Chinezesc e pe 26.01.2028).
- Carcase → anodizare → lot pilot de 25 → asamblare → expediere din **martie 2028**.
- Promis pe pagină: **mai 2028 (UE), lotul 1**; **august 2028**, lotul 2 și Late Pledge (D9 aplicat).
- Coletele pleacă cu bateria ≤ 30 % și eticheta UN3481. Susținătorii primesc înaintea oricărei comenzi din magazin.

### E5. Actualizări
- Project → Communication → Updates → **Add an update**, cu textele din `campaign/09-updates-templates.md`. Apoi **publish + „send notifications”**.
- **La 2 săptămâni** în producție. O întârziere o anunți **în aceeași săptămână** în care o afli.

---
*Surse: `facts.json`, `PLAN.md` v3, `DECIZII-FONDATOR.md`, `campaign/00-README.md`, `campaign/00-image-map.md`, `campaign/perks.csv`, centrul de ajutor Indiegogo (HC/…, citit pe 20–22.10.2026). Termenii și ghidul pentru creatori sunt blocați de Cloudflare.*
