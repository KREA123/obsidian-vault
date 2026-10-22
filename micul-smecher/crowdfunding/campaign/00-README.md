# SOUL on Indiegogo: campaign copy (v3, 2026-10-22, after the review)

English copy to paste into Indiegogo, in the voice of the approved landing (`micul-smecher/site/index.html`). The Romanian translation for the founder is in [`ro/`](ro/) (the Romanian press release there is sent as-is to Romanian media).

**Posting is blocked until decision D1 is written in `03 Decizii/Jurnal decizii.md`** and every gate of the active scenario has passed (`facts.json → campaign.scenarios.<scenario>.needs`). This kit is built for scenario **after_ce** (campaign only after CE, which keeps the founder's rule "no customer payment before grant and CE"). Flip `campaign.scenario` to `before_ce` only with the founder's written waiver.

## How the numbers get into the text

Every price, date, goal, colour list, delivery month, CE line and VAT line is an **f-block**: an HTML comment `f:KEY` before it and `/f` after it, invisible on the page. `tools/build_copy.py` rewrites the inside of each block from `facts.json` (+ `docs/size-s.json` via `tools/facts.py`) and `tools/goal_model.py`. Never edit inside a block by hand. After changing a fact:

```
python3 -I micul-smecher/crowdfunding/tools/goal_model.py
python3 -I micul-smecher/crowdfunding/tools/build_copy.py
python3 -I micul-smecher/crowdfunding/tools/check_copy.py --strict
```

(`tools/build_all.sh` runs these plus the images and the video.) The checker flags numbers that disagree with `facts.json`, banned claims (CE-certified, AI included, "incl. VAT", "% off" the planned retail price, "no two alike", talk-to-Claude before G1, invented press or backers, M sizes shown as S, the v9 hand/desk renders) and every placeholder still open.

## What goes where in Indiegogo

| File | Indiegogo field (admin area) |
|---|---|
| `01-title-tagline.md` | Project name, short description, category, tags (General setup, HC/485) |
| **`story-paste.html`** (generated) | Project Details → Detailed description: one "Copy section" button per section (Story, Specs, Budget & timeline, Team, Risks, Refunds) + the FAQ entries. Image slots are marked `[IMAGE: file]` |
| `02-story.md` | the source of the story (edit here, then rebuild) |
| **`perks.csv`** (generated) / `03-perks.md` | Products → Rewards and Add-ons (HC/478, HC/526), column by column |
| `04-risks.md` | the required **Risks and challenges** section (inside story-paste.html) |
| `13-refunds.md` | the required **Refunds and cancellation** section (draft for the lawyer, the whole text) |
| `05-faq.md` | Project → Communication → FAQ (HC/523), one entry per question |
| `06-team.txt` | the "Team" section |
| `07-prelaunch-emails.md` | the email platform (waitlist, double opt-in), 5 emails before launch + broadcast A |
| `08-launch-emails.md` | the email platform, 4 emails during the campaign |
| `09-updates-templates.md` | Project → Communication → Updates (HC/489) |
| `10-press-release-en.md`, `ro/10-press-release.md` | press kit, sent at G3 under embargo |
| `11-social-posts.md` | IG, TikTok, X, LinkedIn: 2 weeks before launch + the campaign |
| `12-creator-outreach.md` | criteria and email templates for reviewers and YouTubers (no names) |
| `00-image-map.md` | every `{{img:…}}` / `{{video:…}}` placeholder → exactly one file in `../images/` (or a YouTube link), with its mandatory caption |

## Placeholders still open (the checker lists them)

| Placeholder | Meaning | Who closes it |
|---|---|---|
| block `f:age` | filled with 18 (the safe default) until D4 is decided | founder |
| `[[CE: …]]` | the CE lab and the date the EU DoC is signed; the live page is written in the after-CE state | founder, at the CE gate |
| `[[G1: …]]` | true only after gate G1 (SoulOS + voice on the real S board) | founder, at G1 |
| `[[G2: …]]` | true only after gate G2 (aluminium SOUL S working, filmed in one take) | founder, at G2 |
| `[[G3: …]]` | true only after G3 (written quotes, partners signed, battery measured) | founder, at G3 |
| `[[D8: …]]` | depends on the electronics route (decision D8) | founder |
| `[de completat: …]` | founder's own details (name, bio, photo, quote) | founder |
| `{{URL:…}}` | links that don't exist yet (campaign page, site domain, privacy notice, chip lookup) | founder |
| `{{LIVE:…}}` | numbers copied from the live page when sending | whoever sends |

Gate passed → set it in `facts.json → gates` (passed, date, proof) and rebuild: the "where SOUL is today" list, the CE lines and the status bar switch from plan to proof by themselves.

## Copy rules this set follows

- **Size.** The product backed is **SOUL S**: 63 × 71 mm, 23–26 mm deep (being finalised), round 1.75″ AMOLED 466 × 466. The prototype being built is the bigger **M** (90 × 101 mm, 2.8″; board ordered, not yet tested). Any real photo or video of the M prototype carries: *"Prototype shown at a larger size (M). The product you back is S: 63 × 71 mm with a 1.75″ AMOLED."*
- **Renders** always carry *"Render (CGI), not a photo."* Scale is shown by the true-scale graphic and by the `renders/v10` hand/desk renders with their eyes repainted by the eyes engine (caption: "… Eyes drawn by the SOUL eyes engine.").
- **SoulOS screens** are simulator or web captures (firmware 1.9.1 has never run on a real board): *"SoulOS simulator capture at the S screen size (466 × 466). Not a recording of a real device."* or the 480 × 480 web note. *"SoulOS (shown on the prototype)"* only for real recordings.
- **AI.** SOUL connects the owner's own Claude (API key, or the Claude app connector) or the owner's own OpenAI API key, or runs offline. It never includes, bundles or resells AI. A ChatGPT account or Plus subscription does **not** work (the checker bans the phrase). OpenAI key support is *in development*; "Sign in with ChatGPT" is *pending OpenAI approval*. **Voice:** speech-to-text uses the owner's own OpenAI key today; voice for Claude-only owners is *in development* (`facts.json → product.voice`); never "hold the glass and talk to Claude" before that flag is true.
- **CE:** generated from `facts.json → gates.CE`. Scenario after_ce: the live page, the launch emails, updates, press release and creator templates use `f:ce_short` / `f:ce_faq` in the after-CE state (with `[[CE: …]]` until the DoC is signed); only the waitlist emails sent before the DoC use `f:ce_now` ("not CE-certified yet"). The two states never meet on one page. Never a CE logo. No loan unit before the DoC.
- **VAT:** prices are final. ARTEMIS isn't VAT-registered today, so the copy never says "incl. VAT"; the budget line reads "VAT we expect to owe", paid from the money raised, never added to the price.
- **Shipping:** fixed per-zone rates, shown before anyone pledges; one wording from `facts.json` (`f:shipping_note`). Never "estimates" or "at cost". The UK is not in campaign 1 (D13).
- **Money sources:** never name a grant (PoC 1.1) as paying for anything on a public page (checker ban).
- **Batches:** rewards are capped to batch 1; "Campaign Price · batch 2" carries its own later month. In Indiegogo every EU tax rate is set to 0 % in all cases.
- **Prices:** the planned retail price is said in words only. Never a struck-through price, a "% off" badge or false urgency ("after that, €X" must be the real Late Pledge price).
- **Eyes:** never chosen, sold, rerolled or priced by rarity. Two SOULs *rarely* share eyes (about 1 in 112); never "no two are alike".
- **No invented** backers, press, reviews, quotes, certifications or specs. Battery capacity and battery life stay open until measured on the real S unit. Weight "~75–95 g (estimate)" (from `docs/size-s.json`).
- **No Founders edition.**
- **The founder alone** creates the account, verifies identity, connects the bank, accepts the terms and submits for review.

## Contact used in the copy
`office@krea.ro` (the public contact on the landing). If a SOUL address is created (e.g. hello@…), replace it everywhere with one search.
