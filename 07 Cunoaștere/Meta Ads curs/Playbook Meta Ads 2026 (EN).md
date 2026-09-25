# MundiShop Meta Ads Playbook (distilled course, 25 Sep 2026)

**Labels:**
- **[OFF]** = META-OFFICIAL.
- **[PRAC]** = PRACTITIONER.
- **[FOLK]** = folklore or unverified.
- **[MINE]** = my synthesis, not a sourced rule.

Meta help pages are undated; I read them in Sep 2026.

**Bottom line:** At 350 lei/day and 1–2 purchases/day, three things decide results: one consolidated Advantage+ sales campaign, 3–5 genuinely different new creatives every week, and offers that justify above-market prices. Structure tricks and bid caps will not fix a weak ad or a weak offer.

## 0. The "course": who teaches what

- **Meta Blueprint** [1]:
  - Free courses: "Performance 5" (30 min): simplify the account, automate, diversify creative, send good data, validate results. "Advantage+ sales" (25 min).
  - The paid Media Buying Professional exam (410-101, ~$99–150) mostly tests manual-era skills; you don't need it.
- **Jon Loomer** [2–4] (Jul 2025–Jul 2026): keep structure minimal, "the algorithm is literal", ads do the targeting, judge results in aggregate.
- **Foxwell Digital** [5–6] (Oct 2025, Mar 2026): creative-testing frameworks, BFCM calendar and offers.
- **Common Thread Collective (CTC)** [7] (2025–26): consolidation and a cost-control study of 253 accounts.
- **Motion** [8–9] (2026): the largest public creative dataset (578,750 ads, $1.29B spend).
- **Savannah Sanchez / Barry Hott / Dara Denney** [9–11]: hooks, native "ugly" ads, visual diversity.
- **Ben Heath** [12]: 80/20 scaling/testing split, creators, rule-based scaling.
- **Pilothouse** [13]: 3-3-3 testing, catalog feed.
- **Nick Shackelford** [14]: true CAC.
- **Charley Tichenor** [15]: 3:2:2 dynamic creative. It dates from Feb 2024, before Andromeda, so treat it as outdated.
- **Gaps:** I found no public toy-specific Meta benchmark. Ben Heath's 2026 video transcripts weren't retrievable, so I used his blog and a secondary summary.

## 1. Account and tracking setup

1. **[OFF]** Shopify "Facebook & Instagram" app: set Data sharing to **Maximum**. This runs pixel plus Conversions API (CAPI), and purchases sent server to server "can't be blocked by browser-based ad blockers" [16].
   - Pixel + CAPI brought small e-commerce advertisers 11% more purchase conversions than the pixel alone (Meta data, 2023) [17].
   - Meta also cites 17.8% lower cost per result with CAPI (2026) [3][18].
   - Without Shopify, use Meta's free one-click CAPI (Apr 2026), which deduplicates automatically [18].
2. **[OFF]** Deduplicate: the browser `eventID` must match the server `event_id` [19]. Duplicate Purchases make CPA look falsely cheap.
3. **[PRAC]** Event Match Quality: send email and phone, which COD orders already capture. The "7.5+" target is from vendors; Meta publishes none.
4. **[OFF/PRAC]** Define Audience Segments: engaged audience (visitors from the last 180 days + email list) and existing customers (purchasers + customer list). You get new-vs-returning breakdowns [3].
5. **Cash on delivery.** The Purchase event fires even if the parcel is later refused.
   - **[OFF]** CAPI accepts events up to 7 days old [19], so a custom "Delivered/Paid" event is possible.
   - **[PRAC]** Its value for optimization is unproven, so use it for reporting and keep optimizing for Purchase.
6. **[PRAC]** Keep the default 7-day-click attribution and reconcile against Shopify orders net of refusals [2][3]. CTC: low-volume accounts can test adding 1-day view on one campaign [7].
7. **[PRAC]** Feed hygiene: clean titles and descriptions, GTINs, accurate availability [13].

## 2. Campaign structure for a small budget

**The math [MINE]:** at 135–156 lei CPA, 350 lei/day buys about 16–18 purchases a week. **[OFF]** Learning exits after "about 50 results in the week after the ad set's last significant edit" [20]. That would take about 1,000 lei/day in a single ad set, so every split makes things worse.

1. **[OFF]** Run one Sales campaign with Advantage+ on (campaign budget, audience, placements) [1].
   - Advantage+ placements: −11.7% CPA (147k campaigns, 2025).
   - Advantage+ audience: −7.2% cost per result (469 A/B tests) [21].
2. **[OFF]** "By combining similar ad sets, you also combine learnings." For learning-limited ad sets Meta suggests: combine, broaden, raise budget or bid, or optimize for a more frequent event [20].
3. **[PRAC]** Keep structure minimal.
   - Loomer: 1 campaign, 1 ad set. Add pieces only for a different goal, product line or season, and only if each piece is fundable [3].
   - CTC: open a new campaign only when it needs a different setting [7].
4. **[PRAC]** No separate retargeting campaign. Advantage+ audience already spends about 20–25% on warm users [3], and catalog ads re-show viewed products.
5. **[OFF/PRAC]** Hard controls only: Romania, minimum age, exclusions. Use value rules, not gender/interest locks, if data proves a problem [3].
6. **Layout.**
   - **Default (Loomer/CTC):** one ad set with 1 Advantage+ catalog ad + 5–8 distinct creative ads. Test with Meta's in-ad-set creative-testing tool [3].
   - **Fallback (Heath/Foxwell):** about 80% to scaling and about 20% to an ABO test ad set. Use it only if new ads never get spend [5][12].
7. **Optimization event: [OFF] vs [PRAC] conflict.**
   - Meta suggests Add to Cart when learning is limited [20].
   - Loomer: you "may never exit the learning phase" with pricier products and still do well [4].
   - **[MINE]** Stay on Purchase. Test ATC only as a separate campaign judged on Shopify orders.
8. **[OFF]** No cost-per-result goal or bid cap yet.
   - Meta: goal bidding "works best when your ad set gets at least 50–100 weekly conversions". Set the goal 10–20% above average CPA, with a budget of at least 5–10× the goal [22].
   - **[PRAC]** CTC (253 accounts): cost-per-result goals delivered 140% of target on average; bid caps, 123% [7].

## 3. Creative strategy (physical products and toys)

1. **[OFF] Diversify, don't iterate.**
   - "When multiple ads look or feel alike, these are seen as variations of the same creative."
   - Make ads "truly different in look, feel, storyline, and message", e.g. emotional appeal vs product features. A new text line on the same image is iteration, not diversification [23].
2. **[OFF] Use 9:16 video with sound.** Ad sets with at least 20% of assets in this format had 7% lower CPA (correlational, 2026) [24].
3. **[OFF] Catalog ads with video.**
   - Catalog product video gave +20% conversions per dollar (observational, 1M+ ad sets). In one A/B case (On), cost per purchase fell 45% [24].
   - Tips: start with top sellers, hook within 2 seconds, CTA by 5–6 seconds [24].
4. **[OFF] Partnership (creator) ads** added to normal ads: −19% CPA (about 2,400 advertisers, Jun 2025) [24].
5. **[OFF] Language limit:** Meta's AI text and video generation doesn't support Romanian [25].
6. **[PRAC] Motion 2026** [8]:
   - Hit rates by format: Unboxing 9.8%, Offer-first banner 8.6%, Demo 8.1%, Testimonial 6.5%.
   - By asset type: text-only 11.6%, product image with text 8.75%, UGC 7.6%, high production 6.9%.
   - Top hooks: Newness, Sale announcement, Price anchor, Urgency. The data window includes BFCM.
7. **[PRAC] Hooks.**
   - The first 3 seconds need a *visual* change for Meta to see a new ad. Keep the body and swap hooks (Sanchez) [10].
   - Heath: ask creators for about 10 openings per video [12].
8. **[PRAC] Look native.** "Blend in to stand out": no logo, studio lighting or white background in the first frame. Phone-shot is fine, but the ad still needs a hook and a sell (Hott) [11]. Real people beat AI avatars [10][11].

**LEGO translation [MINE]** (Circana: ~40% of Europeans bought toys for themselves or another adult in 2025; building sets +18%, their 6th straight year of growth [26]):
- **Personas:**
  - Gift-buying parent or grandparent: age fit, screen-free, arrives before Moș Nicolae or Christmas, cash on delivery.
  - Adult builder buying for themselves.
  - Collector: retiring sets.
- **Concepts:** build timelapse, unboxing, founder "why order from us" (trust for COD buyers), gift guide by age/budget, offer-first banners in promos, catalog video for the top 20 sellers.
- **Prices above market:**
  - Skip price-anchor hooks. Sell availability, speed, advice, gift wrap and bundles.
  - Consider a catalog product set that excludes SKUs priced far above eMAG.

## 4. Testing framework

1. **Volume.**
   - **[PRAC]** Motion: accounts under $10k/month average 2.8 new creatives a week, and the top quarter manage 4.8. About 5% of ads win [9].
   - Foxwell: one new batch a week [5].
   - **[MINE]** 3–5 new concepts weekly, each one ad with 2–3 hook or format variants.
2. **[OFF] Keep ad counts low.** "Decrease ads per ad set, but maintain diverse creative assets per ad set. One ad can contain multiple (up to 10) creative assets" [27].
   - **[PRAC]** Loomer found 20–50 ads at once "wasteful" [3].
   - Keep 6–10 ads active.
3. **Test budget.**
   - **[PRAC]** Pilothouse: at least 1× AOV per concept [13]. Sanchez: 4× AOV before judging [10].
   - Loomer: "five ads splitting $50/day won't generate meaningful purchase data" [3].
   - **[MINE]** About 20–30% of spend (500–700 lei a week) on new concepts.
4. **[OFF]** Adding an ad resets learning [29]. Launch once a week, in one batch.
5. **[PRAC]** Judge 7-day windows at least two weeks in, never daily swings. Don't judge on CTR or CPM alone [2][3].
6. **Kill rules.**
   - **[OFF]** Meta labels an ad "creative fatigue" at 2× or more of past cost per result [27].
   - **[PRAC]** Ben & Vic: switch off tests at 2–3× target CPA [28]. Foxwell: pause ads Meta won't spend on, to make room [5].
   - **[PRAC]** CTC: ad-level stop-loss rules showed no measurable effect on account results [7]. You kill ads to free space, not to save money.
   - **[MINE]** After 7 days, pause any ad with at least 2× target CPA spent and 0 purchases, or with under 5% of ad-set spend.
7. **[PRAC] Winners.** A winner takes real spend and holds target CPA for 7+ days [5]. Carry the winning *theme* into new formats [3].

## 5. Scaling rules

1. **[PRAC] Precondition.** Scale only when Shopify-verified CPA, net of refused parcels, is below break-even.
   - Break-even CPA = AOV × margin − shipping − COD fees − cost of refusals. Shackelford and CTC both focus on true CAC and first-order margin [7][14].
   - **[MINE]** An earlier MundiShop analysis estimated break-even at about 57–66 lei, against a historical CPA of 135–156 lei. If that holds, fix creative and offer before adding budget.
2. **[OFF]** Whether a budget change counts as a significant edit "depends on the magnitude". $100→$101 is unlikely to reset learning; $100→$1,000 may. Meta gives **no percentage** [29].
3. **[PRAC] How fast to raise budget.**
   - Loomer (2026): "I'm not going to tell you to only raise budget by 20 percent" [4].
   - Heath Media: an automated +3%/day rule that fires while 3-day cost per result is under target, with a cap and a reverse rule [12].
   - **[MINE]** +20–30% every 3–4 days is a comfort convention, not a Meta rule.
4. **[PRAC]** Don't duplicate winners; duplicates cause auction overlap [12]. Scale with new creative, not new ad sets.
5. **[OFF]** Budget scheduling pre-sets increases for peak days and reverts automatically [30].
6. **[OFF]** Add cost controls only once you have 50–100 purchases a week, the volume at which Meta says goal bidding "works best" [22].

## 6. Offers and conversion

1. **[PRAC] Fix the offer before the ads.** "Don't try to ad-buy your way out of a problem. Change the offer, the pitch, or the page" (Foxwell) [6]. Heath ranks the offer above targeting and structure [12].
2. **[PRAC] BFCM offers that work** [6]:
   - 20%+ off.
   - "Up to X% off", with hero products at 20–30%.
   - Buy more, save more.
   - BOGO, if margin allows.
   - Gift-with-purchase lifts AOV but not volume.
3. **[Independent]** "Extra costs too high" is the #1 reason shoppers abandon checkout (40%, Baymard) [31]. **[MINE]** Set a free-shipping threshold just above AOV (about 300 lei) and show it in ads.
4. **[OFF]** Meta promo codes auto-apply in the in-app browser: +4.6% average conversion-rate lift for small businesses [32].
5. **[MINE]** Bundles (set + minifigures + gift wrap) add value without discounting a SKU that is already priced above market.
6. **Urgency and gifting.**
   - **[OFF]** December is Meta's "gifting phase" [33]. **[PRAC]** Foxwell: switch to gifting messaging from Cyber Monday to 15 Dec [6].
   - Use real deadlines, e.g. "order by X for Christmas delivery". Urgency and FOMO hooks over-index [8].
   - EU Omnibus rules require showing the lowest price of the previous 30 days next to any discount.
7. **[OFF]** 59% of Meta holiday shoppers messaged a business [33]. Add the WhatsApp/Messenger browser add-on.

## 7. Mistakes that keep small accounts stuck in learning

- Too many campaigns or ad sets for the budget [2][20].
- Gender, age or interest locks [2][3].
- Frequent edits. Any new ad or creative change, targeting or bid-strategy change, or a pause of 7+ days resets learning [29]. Batch changes weekly.
- A cost goal below your real CPA, which causes "bid limited" delivery [22].
- Near-duplicate creatives [23].
- Switching off the ad Meta favors because its average CPA looks worse. This is the "breakdown effect" [3].
- Judging on 1–3 days of data [2].
- Optimizing for traffic or engagement: "the algorithm is literal" [2].
- Broken or duplicate Purchase events [2].
- A separate retargeting campaign overlapping prospecting [3].
- Manual placement cuts and dayparting [2].
- Blaming the algorithm instead of the ads and offer [2].

## 8. Q4 2026 preparation for toys (Romania)

- **Now to mid-October.**
  - **[OFF]** "Start ads by mid-October to let Meta learn before the peak… plan so budgets lean in, not pull back" (Meta SMB playbook, Aug 2026). Turn on Advantage+ placements early [33].
  - Audit tracking and the feed, and build 15–20 distinct concepts.
  - **[PRAC]** Test your Black Friday offer at least 2 weeks early [6].
- **Mid-October: [PRAC]** start gifting messaging [6]. **[OFF]** This is Meta's "discovery phase" (Oct to early Nov) [33].
- **Fri 6 Nov: eMAG Black Friday** [34], Romania's deal peak. Meta's timeline is built around US Black Friday on 27 Nov [33], so launch your main offer earlier than US playbooks suggest.
  - Schedule budget increases for peak days [30].
  - Foxwell doubles spend on Black Friday [6]; do that only while CPA holds.
- **27 Nov–1 Dec:** US BF/Cyber Monday plus Romania's National Day, a second deal window.
- **6 Dec (Moș Nicolae) through December:**
  - Gift guides by age and budget, gift wrap, delivery deadlines.
  - Keep evergreen winners live and add holiday "wrappers" [6].
- **[PRAC] Don't neglect December.** In 2025 US toy sales, BFCM weeks were flat year on year while Christmas week rose 23% (Circana) [35].
- **After the courier cutoff:**
  - Switch to gift cards, then "fresh start" messaging (Meta: late Dec–Jan) [33].
  - Make sure out-of-stock sets drop out of the catalog.

## Folklore to ignore [FOLK]

- **"Never raise budget more than 20%."** Meta gives no percentage [29]. Loomer has dropped the rule [4].
- **"Below 50 conversions a week the campaign fails."** 50 is Meta's learning-exit guide, not a pass/fail line [4][20].
- **"The learning phase is now 10 conversions."** No Meta source; Meta's help page still says about 50.
- **"Andromeda needs 8–15 or 50 ads per ad set."** Meta gives no count, and its ad-volume page says to avoid high ad volumes [27].
- **"Entity ID: similar ads get one ticket."** Meta confirms that similar ads are grouped [23]; the "ticket" mechanics are practitioner theory.
- **"CAPI recovers 95–99% of conversions."** Vendor figure, unverified.
- **"Duplicate winning ad sets to scale."** This creates auction overlap [12].
- **"Frequency above 3 means fatigue."** Context-dependent [3].
- **"A cost cap guarantees your CPA."** Meta says "adherence is not guaranteed" [22]; CTC measured a 40% overshoot [7].

## Sources
[1] Meta Blueprint: Performance 5 https://www.facebookblueprint.com/student/path/253157-performance-5 ; Advantage+ sales https://www.facebookblueprint.com/student/path/253126-advantage-plus-sales-course ; exam https://www.facebook.com/business/learn/certification/exams/410-101-exam
[2] Loomer, 19 Rules, 21 Jul 2025 https://www.jonloomer.com/19-rules-of-successful-meta-advertising/
[3] Loomer, Master Brief, 2 Jul 2026 https://www.jonloomer.com/meta-ads-master-brief/
[4] Loomer, I Was Wrong, 7 Apr 2026 https://www.jonloomer.com/meta-ads-approach-changed/
[5] Foxwell, testing frameworks, 13 Mar 2026 https://www.foxwelldigital.com/blog/the-meta-creative-testing-frameworks-top-brands-use-in-2026
[6] Foxwell, BFCM playbook, 10 Oct 2025 https://www.foxwelldigital.com/blog/your-no-stress-bfcm-playbook-what-actually-works-and-what-doesnt
[7] CTC cost-control study, 6 Aug 2026 https://commonthreadco.com/blogs/coachs-corner/meta-cost-controls-study-taylor-holiday-andrew-faris ; CTC 2025 guide, 22 Apr 2025 https://commonthreadco.com/blogs/ecommerce-playbook/2025-guide-to-meta-media-buying
[8] Motion Creative Benchmarks 2026 (data Sep 2025–Jan 2026) https://motionapp.com/library/research/creative-benchmarks-2026/top-visual-formats ; /top-hook-tactics ; /top-asset-types
[9] Motion volume talk, 17 Apr 2026 https://motionapp.com/library/talk/meta-ads-in-2026-how-many-creatives-do-you-actually-need-to-launch/ ; Andromeda/BFCM (Denney) https://motionapp.com/blog/andromeda-impact-on-bfcm
[10] Savannah Sanchez profile https://motionapp.com/library/expert/savannah-sanchez/
[11] Barry Hott https://motionapp.com/library/expert/barry-hott/ ; https://www.hottgrowth.com/post/ugly-ads-dont-mean-bad-ads-try-these-expert-tips-for-high-intent-ads
[12] Ben Heath: small-budget video, 20 Feb 2026 https://www.youtube.com/watch?v=XLagiyzYYpE ; summary (secondary) https://www.aimerce.ai/topics/ben-heath-facebook-ads-strategy-guide-47 ; scaling (2023) https://heathmedia.co.uk/how-to-scale-facebook-ads/
[13] Pilothouse 3-3-3 https://www.pilothouse.co/post/meta-creative-testing-framework-the-3-3-3-approach-to-finding-winners ; catalog https://www.pilothouse.co/post/meta-catalog-ads-turning-your-product-feed-into-a-performance-engine
[14] Shackelford, Foundr #635 (2026) https://podcasts.apple.com/ph/podcast/635-the-meta-ads-system-working-in-2026-nick-shackelford/id944627155?i=1000751916670
[15] Tichenor 3:2:2, Feb 2024 https://www.disrupterdispatch.com/p/build-322-ad-code-custom-events
[16] Shopify data sharing https://help.shopify.com/en/manual/promoting-marketing/analyze-marketing/meta-data-sharing
[17] Meta 2025 festive guide (PPC Land, 21 Nov 2025) https://ppc.land/meta-releases-2025-festive-season-guide-with-ai-campaign-tools/
[18] One-click CAPI (PPC Land, 27 Apr 2026) https://ppc.land/metas-free-one-click-conversions-api-is-now-live-no-developer-needed/
[19] CAPI server-event parameters https://developers.facebook.com/docs/marketing-api/conversions-api/parameters/server-event
[20] Meta learning phase https://www.facebook.com/business/help/112167992830700 ; learning limited https://www.facebook.com/business/help/269269737396981
[21] Advantage+ placements https://www.facebook.com/business/help/196554084569964 ; Advantage+ audience https://www.facebook.com/business/help/273363992030035
[22] Cost per result goal https://www.facebook.com/business/help/176339196621566 ; https://www.facebook.com/business/help/272336376749096 ; https://www.facebook.com/business/help/1725302974308722 ; https://www.facebook.com/business/help/491846184627504
[23] Meta, Demystifying Creative Diversification, 16 Dec 2025 https://www.facebook.com/business/news/demystifying-creative-diversification
[24] Meta newsroom, 26 Mar 2026 https://about.fb.com/br/news/2026/03/da-cultura-aos-negocios-como-a-ia-esta-impulsionando-conexoes-personalizadas-e-crescimento/ ; catalog video, 20 May 2024 https://www.facebook.com/business/news/catalog-product-video-a-new-solution-to-maximize-automation-performance
[25] Text-gen languages https://www.facebook.com/business/help/180641596861873 ; video-gen https://www.facebook.com/business/help/2242593819546848
[26] Circana, 27 Jan 2026 https://www.circana.com/post/global-toy-industry-rebounds-in-2025-as-sales-rise-7-fueled-by-pop-culture-collectibles-and-kidu
[27] Ad volume https://www.facebook.com/business/help/2720085414702598 ; fatigue statuses https://www.facebook.com/business/help/1346816142327858
[28] Ben & Vic (Motion) https://motionapp.com/blog/ultimate-guide-creative-testing-2025
[29] Significant edits https://www.facebook.com/business/help/316478108955072
[30] Budget scheduling https://www.jonloomer.com/qvt/budget-scheduling/
[31] Baymard https://baymard.com/lists/cart-abandonment-rate
[32] Promo codes https://www.facebook.com/business/help/1467642254076258
[33] Meta holiday 2026 (Social Media Today): 11 Jun https://www.socialmediatoday.com/news/meta-publishes-2026-holiday-planning-guide/822744/ ; 2 Aug https://www.socialmediatoday.com/news/meta-shares-holiday-2026-tips-for-small-businesses/826785/ ; 13 Aug https://www.socialmediatoday.com/news/meta-publishes-holiday-marketing-guides/827856/
[34] eMAG Black Friday 6 Nov 2026 https://startupcafe.ro/black-friday-2026-va-incpe-pe-data-de-6-noiembrie-la-emag-anunt-oficial-107361
[35] Circana via The Toy Book, 14 Feb 2026 https://toybook.com/circana-the-comeback-was-collectible/
