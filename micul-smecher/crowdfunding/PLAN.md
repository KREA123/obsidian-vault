---
tip: plan
afacere: Micul Șmecher
actualizat: 2026-10-22
---

# SOUL on Indiegogo: campaign plan (v3, 2026-10-22, after the review)

> Company: **ARTEMIS DIGITAL S.R.L.** (Bucharest, CUI 53145290, reg. no. J2025098748009, micro SME, not VAT-registered today).
> Product backed: **SOUL size S** (MĂRGĂRITAR, 63 × 71 × 23–26 mm, round 1.75″ AMOLED 466 × 466). The working prototype today is the bigger **M** (90 × 101 mm, 2.8″ 480 × 480).
> **One source of numbers:** every size, price, date and campaign fact is in [`facts.json`](facts.json) (+ `../docs/size-s.json`, checked by `tools/facts.py`). The goal is computed by `tools/goal_model.py` → `tools/goal_model.out.json`. If this text and those files disagree, the files win. Change them, then run `goal_model.py`, `build_copy.py` and `check_copy.py --strict`.
> Tags: **[E]** = estimate, no quote yet · **[verify]** = not confirmed from a primary source · **[snippet]** = only seen in a search excerpt (Indiegogo Creator Guidelines/ToU are Cloudflare-blocked).
> **v3 (2026-10-22, later the same day) applies the 25-issue review of the kit** (copy EN+RO, images, rewards, video, guide): new reward ladder and batch caps, D9 applied as the safe default, UK out of campaign 1, US/Canada no longer a stretch goal, fixed shipping, CE wording in one state, no grant named as a money source. Open founder decisions: `DECIZII-FONDATOR.md`.
> **v2 replaces v1 (2026-10-20).** v1 planned a pre-CE campaign on ladder A with a €270k goal. That contradicted `facts.json` (after CE, ladder B, €75k) and the founder's rule. v2 follows `facts.json`.
> Read with: `01 Afaceri/Micul Șmecher/Finanțare — crowdfunding și alte surse pentru SOUL.md` (all non-grant money, 2026-10-20), `campaign/00-README.md` (the copy kit), `GHID-POSTARE-INDIEGOGO.md` (step-by-step posting).

> **Blocajul de acum nu e campania, ci expertul științific pentru PoC 1.1.** Răspunsul e în [[Finanțare — expertul științific pentru PoC 1.1]] (actualizat 2026-10-22): 3 căi în paralel săptămâna asta (inginer embedded senior angajat pe CIM ca expert intern, emailul către Tudose/Radovici/Cucu de la UPB, PRECIS/transfer tehnologic UPB sau EDIH). Campania de mai jos are nevoie ca PoC 1.1 să fie decis, deci depinde tot de expert.

## Rezumat (RO)

- **Indiegogo merge pentru ARTEMIS, pe hârtie.** România e listată cu plata în EUR, firma intră ca „Business”, verificarea (KYC) o face Adyen. Două posibile piedici la KYC: numărul ONRC în formatul nou (J2025098748009) și CUI-ul fără „RO”. Testul gratuit: **Andu își face contul și un draft până pe 15.11.2026.** Dacă nu merge: Ulule [verify], apoi precomenzi pe site-ul nostru după CE.
- **Doar „totul sau nimic”. Obiectiv €70,000 = 270 de SOUL S** (lotul 1), cel mai mic lot la care livrăm tot: fabricație, pregătirea lotului, rezervă pentru neprevăzute (15 % + rotunjirea), TVA, comisioane 8 %, plăți eșuate, rezervă de rambursare 5 %. **CE-ul (~€42k) și marketingul (€17,5k) se plătesc înainte de campanie**, din bani proprii și împrumuturi (decizia D11), niciodată din grant.
- **Recompense (scara B, după review):** Soul Supporter €10 · First Light €249 (primii 150, cu numărul gravat pe picior) · Campaign Price €269 (100, lotul 1) · Two Souls €498 (€249 bucata, 10 seturi, lotul 1) · **Campaign Price · lotul 2** €269 (fără limită, livrare mai târzie) · OU în plus €35 · Late Pledge €299 (lotul 2). Culoarea e opțiune la același preț (Argint, Grafit, Jar). Ochii nu se aleg și nu se vând.
- **Calendar:** nicio lansare fără filmare reală. S pe placa reală 15.12.2026 → SOUL S din aluminiu filmat 12.02.2027 → CE gata 31.08.2027 → go/no-go 07.09 → **lansare marți 05.10.2027, 35 de zile, până pe 09.11.2027** → Late Pledge ~30.11.2027. **Livrare estimată: mai 2028 (UE) pentru lotul 1, august 2028 pentru lotul 2** (D9 aplicat ca variantă sigură). UK nu e în campania 1 (D13).
- **Listă de email:** minim 2,500 de adrese confirmate, țintă 3,300 (5.000 ideal), ca să facem 30 % din obiectiv în prima zi.
- **Doar tu:** contul Indiegogo, identitatea, documentele firmei, banca. Plus deciziile din `DECIZII-FONDATOR.md` (D1–D15, F1–F4).

## 0. Rules this plan never breaks

- **Sold:** SOUL **S**. **Shown working:** the M prototype until the aluminium S exists (G2), always with the label *"Prototype shown at a larger size (M). The product you back is S: 63 × 71 mm with a 1.75″ AMOLED."* (`labels.prototype_footage`).
- **Renders:** always labelled *"Render (CGI), not a photo."* v9 object-only renders are scale-neutral and may be reused. Anything showing scale uses **`renders/v10/`** hand/desk, with the old glowing eyes painted over and the flat SoulOS eyes drawn by the eyes engine (`images/src/templates.js → v10eyes`, caption "Render (CGI), not a photo. Eyes drawn by the SOUL eyes engine."); ou_night and vs_m are pending. The other option is the true-scale vector graphic (`images/gallery_1_size_1200x630.png`, `story_06_size.png`: S next to a card and a €2 coin). **Never** `soul_v9_hand.png` / `soul_v9_desk.png`.
- **SoulOS screens:** firmware 1.9.0 has never run on a real board, so every screen is a simulator or web capture and says so: *"SoulOS simulator capture at the S screen size (466 × 466). Not a recording of a real device."* (`labels.soulos_s`). *"SoulOS (shown on the prototype)"* only for real device recordings.
- **Never claim** that AI is included (*"Works with your own Claude or your own OpenAI API key (in development), or offline. SOUL does not include AI."*; a ChatGPT account never works), CE/FCC/UKCA, invented backers, press or reviews, battery life (`null` until measured), a single thickness (*"23–26 mm, being finalised"*), "% off" or a struck-through retail price, or "incl. VAT" while unregistered. **No Founders edition.**
- **Founder rule kept:** *"no customer payment before grant and CE"* → scenario **after_ce** (D1). The kit can switch to `before_ce` only with the founder's written waiver.

## 1. Verdict: does Indiegogo work for ARTEMIS?

**Yes, on the evidence available. One free test remains, and it can only be done by the founder.**

| Question | Evidence (help centre checked 2026-10-22) | Status |
|---|---|---|
| Romania as creator country | Romania → **EUR** in the payout-currency table (HC/671, updated 13.10.2026). Romanian formats defined: 24-char IBAN in EUR or RON, ONRC number, `RO`+digits VAT number (HC/506). The table lists currency, not eligibility; eligibility shows in the dashboard (HC/494). | ✅ likely |
| SRL as creator | Account types: individual, **business**, sole proprietorship; business KYC by Adyen, "Submit for review" (HC/470). Two-step review: platform + financial KYC (HC/645). | ✅ |
| Documents | ONRC extract ≤ 12 months; bank document ≤ 12 months showing the exact legal name, full IBAN and bank logo/stamp; director ID in colour with the MRZ, front and back as separate files; JPG/PNG/PDF ≤ 15 MB (HC/504, HC/505). In English, sworn translation possible; IDs of key shareholders and of the signer [snippet]. | founder only |
| KYC friction 1 | Our number is the **new ONRC format `J2025098748009`** (Jurnal decizii 2026-10-12); Indiegogo's sample is `J40/8302/1997`. | ⚠️ enter as on the extract; support if rejected |
| KYC friction 2 | CUI **53145290 has no `RO` prefix** (not VAT-registered); "missing country prefix" is the listed tax-number error (HC/507). Disappears if we register for VAT (D2). | ⚠️ |
| Timing | **Business onboarding must be complete before the Upcoming (preview) page can be published** (HC/484). | plan KYC for Mar 2027 |
| Risk profile | "Elevated risk" creators can face withheld funds, milestone/escrow release, requests for production agreements or guarantees; payouts wait until provided [snippet]. A first-time hardware creator fits. | ⚠️ trust pack at G3 (§6) |
| Kickstarter | Romania not eligible; only through a company in an eligible country (`Finanțare — crowdfunding…` §2). | ❌ |

**The free test (founder, by Sun 15 Nov 2026):** create the account, start a Draft, choose Business, and check that location Romania and currency EUR can be picked. Then try the registration number and the CUI on the Business tab. **Never** share passwords, ID scans or bank data with Claude.

**Fallbacks, in order:**
1. **Ulule** (FR, all-or-nothing, EUR) [verify RO companies accepted].
2. **Our own pre-order page after CE** (Shopify Payments works in RO): refundable deposit, balance charged at shipping, our own threshold ("if fewer than N by date X, everyone is refunded"). Full EU consumer law applies: 14-day withdrawal, delivery date on the page, OUG 34/2014 (`04-COMPLIANCE.md`). No platform traffic.
3. **Crowd Supply** (accepts worldwide projects; ~12 % + 3.75 %, prefers open hardware) [verify].
4. **Kickstarter through a foreign company: not now.** A new related company can break the PoC 1.1 SME/de minimis status and IP ownership (`Finanțare — crowdfunding…` §2, §4).

Not to use now: **Express crowdfunding** (HC/641, for products ready to ship), **Preorders** (HC/690, store sales), **Shipping Guarantee** (holds the money we need for production), **Stretch Pay** during the campaign.

## 2. Funding type and goal

### 2.1 Funding type
**Fixed goal, all-or-nothing.** It's the only model for new campaigns (flexible was discontinued, HC/645), and the right one: if the minimum batch isn't funded, nobody is charged. Fees are **5 % + 3 % + €0.20 per payment**, and nothing if the goal is missed (HC/596). On a €249 pledge that is €20.12 (8.08 %). Indiegogo also **holds 5 % of net volume for 6 months** as a reserve (HC/766), which is cash flow, not cost: ~€3.5k at the goal.

### 2.2 Unit cost of SOUL S at 270 units (route B: Waveshare board inside, 3 colours)
From `tools/goal_model.py`. M prices come from the factory model (`docs/factory/SOUL-fabrica-model.xlsx`, scenario A, everything outsourced, the cheapest route below 5,000/yr per `SOUL — Fabrică și lanț de producție.md` §1) × S factors (`facts.json → size_S.cost_factors_vs_M`). The board is priced from Waveshare's list. **All [E] until written quotes.**

| Group | Lines | €/unit |
|---|---|---|
| Imported parts | Waveshare ESP32-S3-Touch-AMOLED-1.75 31.75 · cell 2.46 · glass Ø52 3.19 · speaker 0.94 · freight + duty 3.84 | 42.18 |
| Aluminium shell | CNC 2 halves 38.26 · blast + anodise + lot fees 6.47 · transport 2.57 | 47.30 |
| Other parts | OU egg 12.84 · packaging 6.95 · chassis + foot 4.04 · mechanics 2.94 · USB-C cable 1.69 · laser mark 1.60 | 30.06 |
| Assembly | EMS box build (assembly, flash, test, pack) 12.59 · internal QC 0.60 | 13.19 |
| Scrap 3 % | | 3.59 |
| **Total** | | **136.35** |

### 2.3 Goal: €70,000 (ladder B after the review, after CE, route B)
The model finds the smallest batch at which collected money minus VAT, fees, failed payments and the refund reserve covers every cost of delivering. Mix [E]: First Light (150) sells out, 6 % of devices go in Two Souls, the rest at Campaign Price, 5 % add an extra OU, and supporters equal 5 % of backers. The average pledge is **€254.18**. Two Souls at €498 (the First Light price per unit) brought the goal from €75k to €70k: the old €5.5k "rounding" is gone.

| Build-up of the goal (`goal_model.out.json → budget_lines`) | € | % |
|---|---|---|
| Making 270 SOULs + 2 % spares + extra OU add-ons | 37,753 | 54 % |
| Batch set-up: golden samples (3 colours), anodise set-up, packaging samples €1,900 · product liability insurance €800 · 3PL onboarding, UN3481 labels €700 | 3,400 | 5 % |
| Contingency: 15 % on every cost (all [E] until quotes) plus the rest up to a round goal (the separate 'rounding' line read as padding, review 2026-10-22) | 6,702 | 10 % |
| VAT we expect to owe (21 %, inside the prices; never added on top) | 11,767 | 17 % |
| Indiegogo 5 % + Adyen 3 % + €0.20 per payment | 5,479 | 8 % |
| Pledges that fail after 3 retries (~3 %) [E] | 2,097 | 3 % |
| Refund reserve 5 % (D15: the lawyer sizes it to the refund promise) | 2,802 | 4 % |
| **Goal** | **70,000** | |

**Paid before the campaign, so outside the goal (€42,000, `one_offs_before_campaign`):**

| Item | € [E] |
|---|---|
| CE/RED lab: EN 300 328, EN 301 489-1/-17, EN IEC 62368-1, EN 62479, pre-scan, one re-test. Full radio testing is needed because route B has a bare ESP32-S3R8, not a certified module. | 14,000 |
| EPR: RO + 9 EU countries + UK (WEEE, batteries, packaging) | 12,000 |
| EN 18031-1/-2 (RED cybersecurity) | 4,500 |
| CNC programming + first article, test jig, glass print set-up | 4,000 |
| EVT/DVT: 2 × 10 aluminium S units (CE samples, video, press loaners) | 3,000 |
| Compliance consultant + legal texts | 1,700 |
| Technical file, GPSR, EU DoC, labels | 1,500 |
| EU trademark + design (SME Fund may cover 75 %) | 1,300 |

Sources: `docs/04-COMPLIANCE.md`, `Finanțare — oferte de preț pentru PoC 1.1.md` (L14 ≈ €7k net EMC + radio), the factory model.

**Cash needed before the first payout: €59,500** (€42,000 above + €17,500 marketing, §8). **This is the real money problem, not the goal.** Candidates are in `Finanțare — crowdfunding…` §1/§5: own or KREA loan, friends-and-family loans, Patria Credit InvestEU (≤ 245,000 lei).
- **PoC 1.1 does not pay for this.** Its L14/L15 pre-tests are eligible only after the financing contract (est. Aug–Oct 2027), and final CE is explicitly out of scope (`Finanțare — PR BI PoC 1.1…`, "Nu intră").
- Anything done earlier must be paid from non-grant money and **never also claimed in PoC 1.1** (double funding). That is **decision D11, due by 31 Jan 2027.** The public page says only "from our own money and loans, not from the campaign"; `check_copy.py` fails on any mention of a grant or PoC 1.1 in the copy.

**Sensitivity** (`goal_model.out.json`):

| Case | Devices | Goal |
|---|---|---|
| Base (B after the review, after CE, route B) | 270 | €70k |
| unit costs +15 % | 400 | €110k |
| unit costs −15 % | 180 | €50k |
| 5 colours instead of 3 | 290 | €80k |
| marketing recovered inside the goal | 510 | €135k |

The goal is **recomputed at G3 (7 Sep 2027) with written quotes**. If the quotes come in more than 15 % above the model, the goal moves up before submission. It can't change after launch (HC/517).

### 2.4 VAT and OSS (the accountant decides, we prepare: D2)
- **Romania's VAT threshold is 395,000 lei (~€79k), and advance payments count toward it** (`Finanțare — crowdfunding…` §6). At the €70k goal the campaign alone is ~350–360k lei, so crossing it depends on the amount raised, Late Pledge and other turnover in the year. The surer trigger is **cross-border B2C sales above €10k/yr (OSS)**. The model therefore treats 21 % VAT as **inside** every price, and the copy says "we expect to owe VAT … if we do, it's paid from the money raised" (never "the campaign crosses the threshold").
- **On Indiegogo:** reward prices are entered **net**, and since 4 Aug 2026 the EU tax rates come **pre-filled per country** (HC/478, HC/597). **Set every EU rate to 0 %** so the backer pays exactly €249/€269. Copy says "Price is final (no VAT is added)", never "incl. VAT" while unregistered.
- Destination rates differ (SE 25 %, DE 19 %). The model's flat 21 % is a small error at this size [E].
- **Accountant, before G3:** the registration date (before launch is cleaner); OSS; invoices to backers; whether ARTEMIS stays a micro-company.
- **UK: not in campaign 1 (D13).** If it is added later: Indiegogo collects UK VAT only up to £135, so UK parcels ship **DAP** (~€320 landed for a €249 reward); the accountant checks whether ARTEMIS can collect UK VAT itself.

## 3. Rewards (ladder B after the review; D3, D12)

Indiegogo sorts rewards by price, and one can be pinned (HC/478). Each reward shows one **month + year** for delivery. The page never shows "% off" or a struck-through €299 (EU price-indication rules; there is no prior selling price).

| Reward | Price | Cap | Batch / delivery | Contents |
|---|---|---|---|---|
| **Soul Supporter** (no device) | €10 | none | digital | name in the SOUL birth register (opt-in), digital eye wallpaper pack, backer updates |
| **First Light** | €249 | **150**, 1 per backer | batch 1 · May 2028 | 1 × SOUL S (colour option) + OU + cable + guide, **its First Light number 001–150 laser-engraved on the foot** |
| **Campaign Price** | €269 | **100** | batch 1 · May 2028 | same, no engraving |
| **Two Souls** | €498 (€249 each) | **10 sets** | batch 1 · May 2028 | 2 × SOUL S (any two colours), 2 × OU, one parcel |
| **Campaign Price · batch 2** | €269 | none | batch 2 · August 2028 | same as Campaign Price, later month shown before pledging |
| Add-on **Extra OU egg** | €35 | none | with the SOUL | a second charging egg, same parcel |
| **Late Pledge** (after the campaign) | €299 | batch 2 capacity | batch 2 · August 2028 | same as Campaign Price |

- **Batch 1 = 270 devices = 150 + 100 + 10 × 2** (`campaign.batch_1`, D12): the batch the post-campaign timeline is sized for. Nobody who pledges under one date is moved to a later one (delivery date = essential pre-contract term, CRD / OUG 34/2014). Raise the caps only with written CNC/anodise/EMS capacity at G3.
- **Why this ladder (review):** First Light was only €20 under Campaign Price → the engraved number adds a non-rarity reason to be early (the laser mark is already in the unit cost). Two Souls at €259 each had no pull → now the First Light price per unit. The single-unit price is **not** cut (First Light contribution is only ~€49/device); the price is justified as a machined-aluminium object (macro shot F11).
- **Colour is a variant** with its own SKU (`SOUL-S-SIL/-GRA/-EMB`), no price difference. Launch colours: **Silver, Graphite, Ember** (D7).
- **Eyes:** born from the chip ID with published odds; never priced, sold, rerolled or used as a prize. Two SOULs share a pair ~0.9 % of the time.
- **Contribution per device** after unit cost, VAT and fees: First Light €49.31, Campaign €64.24, Two Souls €49.41, Late Pledge €86.64.
- **Ladder A (alternative):** First Light €199 (cap 300), Campaign €219, Two Souls €418, Late Pledge €249; needs a ~€120k goal and a ~7,000-email list. Not recommended for a first-time creator with no audience yet.
- **Settings:** Stretch Pay off. Allow-list the shipping countries (§5). Pin First Light while it lasts, then Two Souls. **Stable Pledge (D10):** irreversible; turn it on at G3 only if every batch quote and the courier quote are in writing.

## 4. Delivery estimate and critical path

### 4.1 Before launch (all must pass; a slipped gate moves every later date by the same amount)

| Target | Gate | What |
|---|---|---|
| ~mid-Nov 2026 [E] | – | 3 × Waveshare AMOLED-1.75 + 2 × 1.75C arrive. **Order from waveshare.com by 31 Oct**: EU distributors were out of stock on 20 Oct (`docs/12-SIZE-S.md`). |
| Tue 15 Dec 2026 | **G1** | SoulOS Alive + hold-to-talk voice on the S board, with the founder's own keys |
| Fri 12 Feb 2027 | **G2** | aluminium SOUL S assembled, working, **filmed in one take** = the launch-footage gate |
| Fri 7 May 2027 | EN18031_FW | secure boot, flash encryption, signed OTA, unique credentials in SoulOS |
| Fri 21 May 2027 | PRESCAN | RF/EMC pre-scan on DVT units, no blocker |
| Tue 1 Jun 2027 | EPR | WEEE/battery/packaging registrations started in the shipping countries |
| Tue 31 Aug 2027 | **CE** + QUOTES | full RED/EMC/safety + EN 18031 passed, **EU DoC signed**; written quotes within +15 % |
| Tue 7 Sep 2027 | **G3** | go/no-go (§6) |

**The pre-launch critical path:** G1 → S CAD → 10 CNC sets → G2 → DVT → pre-scan → CE lab (6–12 weeks incl. a re-test) → DoC. It needs the €42k in §2.3. A failed radio test (aluminium attenuates RF) is the biggest single slip risk.

### 4.2 After the campaign (`facts.json → scenarios.after_ce.timeline`)

| Dates | Step |
|---|---|
| 5 Oct – 9 Nov 2027 | campaign, 35 days |
| 10 – 26 Nov | payments collected (15 days, 3 retries, HC/637); Pledge Manager: colour, address, add-ons, shipping |
| from Fri ~19 Nov | weekly Friday payouts (HC/474), minus the 5 % reserve |
| 22 Nov – 10 Dec | batch orders: boards, cells, glass, shells, OU, packaging. **Everything from China ordered by 10 Dec**, because **Chinese New Year is Wed 26 Jan 2028** (factories close ~2–3 weeks) |
| 6 Dec – 21 Jan 2028 | CNC machining of the shells (5–6 weeks, holidays included) |
| 17 Jan – 11 Feb | anodising in 3 colours against the golden samples |
| 7 – 11 Feb | pilot run, 25 units, full QC |
| 14 Feb – 3 Mar | assembly and test of the batch (EMS) |
| March 2028 | shipping starts (best case); **nothing ships without the signed DoC** |
| **May 2028 (EU, batch 1)** | **promise on the page** (D9 applied as the safe default: ~10 weeks of buffer) |
| ~30 Nov 2027 → **August 2028** | Campaign Price · batch 2 and Late Pledge |

- **Buffer: ~10 weeks** with D9 applied (was ~6). Comparable campaigns shipped ~1 month late (StackChan) to ~13 months late (Butter Bot shop orders) (teardown §A). A late promise kept beats an early one broken.
- Backers ship before any shop order. Nothing is ever charged to the shop before the backers are served.

## 5. Shipping (fixed per zone, published before anyone pledges, paid in the Pledge Manager; rates cover the 8 % fees; if the courier costs more, ARTEMIS pays the difference)

| Zone | Countries | Per parcel | Notes |
|---|---|---|---|
| RO | Romania | €6 | 3PL locker/courier |
| EU-1 | DE, AT, PL, NL, BE | €12 | road courier; Li-ion in equipment = UN3481 PI 967 Sec. II, ≤ 30 % charge |
| EU-2 | FR, IT, ES, SE | €15 | as EU-1 |
| Extra SOUL, same parcel | – | +€4 | the extra OU add-on ships free |
| **Not in campaign 1** | GB, US, CA, CH, NO, AU, rest of world | – | **GB (D13):** needs a UK gate (PSTI statement of compliance: support period, vulnerability disclosure, no default passwords; UK WEEE/battery distance-seller arrangements; DAP import VAT, ~€320 landed). **US/CA (D14):** FCC/ISED; no longer a stretch goal (it rewarded nobody who could back). Since the end of US de minimis, every US parcel pays duty and brokerage [verify]. CH/NO import VAT and local rules [verify]. These open in Late Pledge only when done. |

One wording everywhere (`facts.json → shipping_eur.wording_en`, `f:shipping_note`): never "estimates" or "at cost" (CRD art. 6(1)(e): the total price including delivery must be known before the pledge). Parcel ~0.4 kg, ~140 × 140 × 90 mm (`size_S.shipping_parcel`). Get DPD/GLS/DHL + 3PL quotes before G3. Every extra EU country adds ~€1–3k/yr of EPR, so add one only for an expected ≥ 25 backers (D5).

## 6. Timeline: pre-launch → launch → Late Pledge

| Date | Milestone | Who |
|---|---|---|
| **by 31 Oct 2026** | Decisions D1–D8 (D9–D11 later). Order the S boards. Book the accountant (VAT/OSS/micro). TMview search for "SOUL". **Start the PoC 1.1 expert search now** (the expert note). | founder |
| **by Sun 15 Nov 2026** | Indiegogo account + Draft test (§1) | **founder only** |
| Nov 2026 | Flash the S board, BRINGUP. S CAD → SLA prints → RFQ for 10 CNC sets. RFQ to labs (PIT, cetecom, NMi, EMCLab) with pre-scan. Site waitlist switched to S, double opt-in, intent survey (colour, price, country). | Claude + founder |
| Tue 15 Dec 2026 | **G1** | Claude + founder |
| Dec 2026 – Feb 2027 | PoC 1.1 submission (window not open yet; needs the expert). Ask the consultant if a public waitlist and a later campaign clash with the TRL claim. | founder |
| 11 – 18 Jan 2027 | **CPL test, €500**: Meta/IG lead ads with labelled v10 renders + labelled M footage. Continue only if CPL ≤ €2.5. | Claude drafts, founder runs |
| Fri 12 Feb 2027 | **G2** → shoot the one-take video + the campaign video by end Feb | founder (+ videographer) |
| **Mar 2027** | **Business KYC** (extract + translation, bank doc, ID, shareholders), then **publish the Upcoming page** (followers only, no payment). URL and category lock at this point. | **founder only** |
| Mar – Sep 2027 | Lead ads paced to the list target; dev diary from real production (CNC, anodise, lab); eyes clips | Claude + founder |
| Apr – Aug 2027 | DVT, EN 18031 firmware, pre-scan, CE lab, EPR, quotes (§4.1). Press list built from G2 footage. **No loan unit before the EU DoC is signed** (lending non-CE radio equipment = making it available on the market, Blue Guide); before that, only demos supervised by ARTEMIS. | founder + Claude |
| 1 – 30 Sep 2027 | 5–10 DVT loaners to creators under embargo, **only now that the DoC is signed** | founder |
| **Tue 7 Sep 2027** | **G3 go/no-go:** CE DoC signed; real footage of SOUL S and the founder on the page (F1–F4); quotes ≤ +15 % (else recompute goal); list ≥ 3,300 confirmed; KYC approved; VAT decision executed (D2); PoC 1.1 decided (D1 rule); legal texts final; trust pack ready (quotes, production plan, risks, refunds, team); D9/D10 decided. | founder |
| **Tue 21 Sep 2027** | **Submit for review** (≥ 7 days before launch; review ≤ 3 business days; HC/486) | founder |
| **Tue 5 Oct 2027** | **LAUNCH**, 35 days, Endgame on (HC/605). Launch email (700×700 "Live now"). | all |
| 5 – 7 Oct | Day 1–3: list emails (T0, T+4 h, T+24 h), creator embargo lifts, community posts | all |
| **Tue 9 Nov 2027** | **End** (before Black Friday, 26 Nov) | – |
| 10 – 26 Nov | collection + Pledge Manager. Unpaid orders stay open by default (HC/637): let them pay in the Pledge Manager, but build only for paid orders. | – |
| ~16 Nov | request Late Pledge review (cooldown ≤ 15 days, HC/602) | founder |
| **~Tue 30 Nov 2027** | **Late Pledge opens** at €299 | – |
| Dec 2027 – May 2028 | production and shipping per §4.2; **an update every 2 weeks** and the same week for any slip | founder + Claude |

**If PoC 1.1 isn't decided by G3**, the D1 rule ("grant and CE") blocks launch. The founder then either accepts "submitted, under evaluation" in writing, or the launch moves to **~Feb 2028**, after the holidays. Same rule if CE slips: the launch moves, the promise is never made before the DoC.

## 7. Stretch goals (only real ones; each reaches backers who can pledge today; nothing that changes the hardware or delays delivery)

| At | What | Cost [E] |
|---|---|---|
| €95,000 | SoulOS in German, French, Spanish, Italian | ~€4k |
| €130,000 | a felt travel pouch in every box | ~€4/unit |
| €175,000 | a printed birth card in every box (the SOUL's eyes, chip ID, birth date) | ~€1/unit |

US/Canada (FCC + ISED) is **not** a stretch goal any more: it rewarded nobody who could back. It is a separate pre-launch decision (D14). Announce the first stretch goal within 7 days of launch. **Never** a bigger battery, a new board, new colours, more eye designs (changes the published odds) or AI credits.

## 8. Marketing plan and budget (D6: €17,500 at risk, outside the goal)

**Positioning (review 2026-10-22: one hero use case everywhere):** *"It looks up when your AI needs you"*: Claude asks on the glass, you hold to approve. A palm-sized aluminium desk companion that gives the AI you already use a face. No camera. It listens only while you hold the glass. It works offline and never becomes a brick. Name: *"SOUL: Living Eyes for Your Own AI"*. Below it: *"Works with your own Claude or your own OpenAI API key (in development), or offline. SOUL does not include AI."* The approval feature is promised only after G1 shows it on the S board. Never a vendor name in the title (`campaign/01-title-tagline.md`). Read the title and tagline limits in the dashboard.

| Phase | Line | € [E] | Rule |
|---|---|---|---|
| Pre-launch | CPL test (Jan 2027) | 500 | go only if CPL ≤ €2.5 |
| | Lead ads, Meta/IG + TikTok, after G2 (Mar–Sep 2027) | 6,500 | ~2,600 confirmed leads at ≤ €2.5; pause any ad set > €3 |
| | One-take video + campaign video + photos of the **real S** | 2,500 | renders and M footage labelled |
| | Email platform (EU-hosted, double opt-in) | 400 | GDPR notice (`04-COMPLIANCE.md`) |
| | Press kit, translations EN/RO/DE | 400 | |
| | Shipping/insurance for 5–10 DVT loaners | 600 | units from the EVT/DVT budget |
| Campaign | Retargeting + lookalikes, **hard cap** | 6,600 | spend only while measured **ROAS ≥ 5×**. Break-even = €254.76 pledge / €64.24 contribution ≈ 4.0× (5.2× on First Light). |
| | Crowdfunding agencies | 0 | no margin for a % of funds |
| **Total** | | **17,500** | paid from ARTEMIS cash; recovered only above the goal |

**List target and conversion** (`list_rules`, `goal_model.out.json`) [E]:
- Day 1 = 30 % of the goal = €21k ≈ **83 pledges**. At 2.5 % day-1 conversion that needs **3,300 confirmed emails** (minimum 2,500). **Target 5,000.**
- Whole campaign: the list converts ~5 % (175 pledges ≈ €45k, ~60 % of the goal). Indiegogo traffic, creators and retargeting bring the other ~100 pledges.
- The general note's realistic range for a 3–5k list is €20–60k [E]. **So €70k is reachable only with the full list and the day-1 push. Never launch weak.**
- **Sources:** ~2,600 paid leads + ≥ 900 organic:
  - the site waitlist (founder: export the count);
  - eyes clips (blinking, following a finger, "birth" from a chip ID, `eyes/one.html`);
  - dev diary;
  - the ESP32/maker community (open eyes engine);
  - Romanian tech press;
  - Upcoming-page followers.
- Paid €1 reservations stay **off**: a payment before CE breaks D1.

**PR and creators: approach, no names yet** (`campaign/12-creator-outreach.md`):
- Build the press list at G2, when there is something real to show. Tiers: (1) Romanian tech and business media and podcasts; (2) EU design and gadget media; (3) AI-hardware, desk-setup and ESP32 creators.
- Pitch with the one-take video. Lend DVT units under embargo **only after the EU DoC is signed**, so hands-on pieces land on days 1–3 (the StackChan pattern).
- No paid reviews presented as independent. Any paid collaboration is disclosed. No press or "as seen in" claims until something is published.
- The trailer may sit in the gallery labelled "Renders (CGI)" (music licence: `trailer/MUSIC-LICENSE.md`; check the TTS voice terms before paid media).

## 9. KPIs

| Phase | KPI | Target | If missed |
|---|---|---|---|
| Pre-launch | Cost per confirmed lead | ≤ €2.5 (stop > €3) | new creative; real S footage |
| | Landing → signup / double opt-in | ≥ 25 % / ≥ 60 % | rewrite hero; real video first |
| | Confirmed list at G3 | ≥ 3,300 (target 5,000) | 2,500–3,299: go only if Upcoming followers ≥ 1,000 and ≥ 15 % of the survey say "will back at €249–269"; < 2,500: postpone to ~Feb 2028 |
| Launch | % of goal at 24 h / 72 h | 30 % / 50 % | day-3 list push, creator posts |
| | Funded by | day 7–10 | – |
| | Average pledge | ≥ €250 | push Two Souls |
| | Visitor → backer | ≥ 2 % cold, ≥ 10 % list | – |
| | Ad ROAS | ≥ 5× | pause the ad set |
| | Cancellations in-campaign | ≤ 5 % | FAQ/update on the cause |
| Post | Payment collection | ≥ 97 % | Pledge Manager reminders |
| | Updates | 2/week in the campaign, every 2 weeks in production, never < monthly | – |
| | Delivered by the promised month | ≥ 95 % | same-week update, refund offer |
| | Support first reply | < 48 h | – |

## 10. Risks (the page's required "Risks and challenges" section is `campaign/04-risks.md`)

| Risk | Likelihood | Mitigation |
|---|---|---|
| **PoC 1.1 blocked by the missing scientific expert** → "grant decided" condition fails | high today | expert note, 3 paths in parallel this week |
| Firmware 1.9.0 has never run on a real board; the S port and voice not proven | high | G1/G2 before anything public beyond the waitlist |
| €59.5k pre-campaign cash not found | high | D11 by 31 Jan 2027; loans; route B (no NRE); delay rather than cut CE |
| CE/RED fails (bare ESP32-S3R8 in an aluminium shell) | medium | pre-scan in May; 1 re-test budgeted; nothing ships before the DoC |
| Unit costs above the model | high | 15 % contingency; G3 quotes ≤ +15 % or recompute the goal |
| List too small → public failure (Maicat, Ominous R1) | medium–high | G3 list gate; postpone, never launch weak |
| VAT/OSS/micro-status handled wrong | medium | accountant before G3; prices final with VAT inside; EU rates 0 % on Indiegogo |
| KYC friction (new ONRC format, no RO prefix) or extra holds (escrow, milestones) | medium | Draft test by 15 Nov; KYC in Mar 2027; trust pack |
| Waveshare single source; Chinese New Year 26 Jan 2028 | medium | volume quote before G3; buy all boards at the first payout; China orders by 10 Dec |
| Anodise colour mismatch (Ember) | medium | golden samples, one bath per colour, 3 launch colours |
| Delivery slip | medium | D9 applied (~10 weeks); rewards capped to batch 1, batch 2 has its own month; same-week updates; backers before the shop; refund reserve (D15) |
| No real footage / no face on the page (review: the #1 reason a visitor won't back) | high today | G2 one-take + founder photo, name, story and F09 before the Upcoming page (F1–F4) |
| Lending non-CE units to reviewers | – | no loan before the EU DoC |
| AI access changes (API terms, Sign in with ChatGPT not approved) | medium | offline mode; never promise ChatGPT sign-in; trademark disclaimer |
| "SOUL" trademark conflict | medium | TMview/EUIPO before the Upcoming page |
| Over-funding strains a one-person company | low | batch-1 caps; batch 2 with a later month; EMS box build |

## 11. Who does what

**Only the founder:**
- the Indiegogo account and Draft test;
- business KYC (ID, extract, bank, shareholders) and connecting the bank;
- accepting the terms and submitting for review;
- signing quotes and lab orders;
- decisions D1–D11 (written in `03 Decizii/Jurnal decizii.md`).

Claude never handles passwords, IDs or bank data.

**Claude:**
- keeps `facts.json` and the model current;
- rebuilds the copy, images and video after each decision;
- builds the press list at G2;
- recomputes the goal with the quotes;
- writes the updates;
- drafts the trust pack;
- runs `check_copy.py --strict` before anything is pasted.

## Sources
- Indiegogo help centre, checked 2026-10-22 (`HC/<id>` = `https://help.indiegogo.com/article/<id>`): 470, 474, 478, 483, 484, 485, 486, 494, 503, 504, 505, 506, 507, 515, 517, 520, 523, 579, 596, 597, 599, 602, 605, 632, 637, 641, 645, 671, 690, 766, 471. Creator Guidelines/ToU only as [snippet].
- Teardown of 7 successful + 2 failed campaigns (research workflow, 2026-10-22): Plaud Note, Loona Deskmate, Cubie, StackChan, LOOI, Butter Bot, CODE27; Digital Dream Labs, Maicat.
- Vault: `facts.json`, `tools/goal_model.py` / `.out.json`, `campaign/perks.csv`, `../docs/size-s.json`, `../docs/12-SIZE-S.md`, `../docs/factory/SOUL-fabrica-model.xlsx`, `../docs/04-COMPLIANCE.md`, `../renders/v10/README.md`, `01 Afaceri/Micul Șmecher/SOUL — Fabrică și lanț de producție.md`, `…/Finanțare — oferte de preț pentru PoC 1.1.md`, `…/Finanțare — crowdfunding și alte surse pentru SOUL.md`, `…/Finanțare — PR BI PoC 1.1 pentru SOUL.md`, `…/Finanțare — expertul științific pentru PoC 1.1.md`, `…/De continuat — SOUL.md`, `03 Decizii/Jurnal decizii.md`.
