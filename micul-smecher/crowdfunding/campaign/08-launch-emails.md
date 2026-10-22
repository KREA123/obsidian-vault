# Campaign emails (4)

To the waitlist (opt-in only), from our email platform. Indiegogo's own backer emails are separate (updates, `09-updates-templates.md`). Footer: same as `07-prelaunch-emails.md`.
**Rules:** every number about the campaign's progress (amount raised, backers, % of goal, rewards left) is copied from the live page at the moment of sending, written here as `{{LIVE:…}}`. Never round up, never estimate. Every price, date and price-after-the-campaign line is an f-block generated from `facts.json`: no invented urgency (the price after the campaign is the Late Pledge price, and the email says so).

| # | When | Audience |
|---|---|---|
| 1 | launch day 09:00 (<!--f:launch_day-->Tuesday 5 October 2027<!--/f-->); a short resend at 13:00 to non-openers | whole list |
| 2 | launch + 48 h, 09:00 | whole list minus backers (if the platform can exclude them; otherwise everyone, with the backer line) |
| 3 | day 17, 09:00 (mid-campaign) | whole list |
| 4 | 48 h before the end + the last day 09:00 (end: <!--f:end_day-->Tuesday 9 November 2027<!--/f-->) | whole list minus backers |

---

## Email 1 · Launch day

**Subject:** SOUL is live. First Light: <!--f:launch_cap-->150<!--/f--> at <!--f:launch_price-->€249<!--/f-->.
**Preview:** It just opened its eyes on Indiegogo.

{{img:launch-700}} (700 × 700 "Live on Indiegogo" image, render labelled)

Hi,

**SOUL is live on Indiegogo.** → {{URL:campaign}}

<!--f:ladder_line-->**First Light:** the first 150 backers, €249, with its First Light number engraved on the foot · **Campaign Price:** €269 · **Two Souls:** €498 (€249 each) · after the campaign: **Late Pledge** at €299. Planned retail price after the campaign: €299.<!--/f-->

What you're backing:
- SOUL S: 63 × 71 mm of bead-blasted, anodised aluminium, a round 1.75″ AMOLED, two living eyes.
- Born with one of 120 pairs of eyes. Nobody picks them.
- <!--f:ai_line-->Works with your own Claude or your own OpenAI API key (in development), or offline. SOUL does not include AI.<!--/f-->
- No camera. It listens only while you hold the glass.
- OU, its charging egg, in the box.
- Estimated delivery: <!--f:delivery-->May 2028 (EU)<!--/f--> (batch 1).

It's **all-or-nothing**: if we don't reach the goal, nobody is charged. The first day decides a lot. If SOUL made you smile, today is the day.

**[Back SOUL →]** {{URL:campaign}}

Hold the glass,
[de completat: founder first name]

P.S. <!--f:ce_short-->Radio, EMC, safety and EN 18031 tests passed at [[CE: lab name]]; EU Declaration of Conformity signed ([[CE: date the EU DoC is signed]]).<!--/f--> Everything we know can go wrong is on the page, under "Risks and challenges".

**13:00 resend (non-openers only). Subject:** First Light: {{LIVE:first_light_left}} of <!--f:launch_cap-->150<!--/f--> left

---

## Email 2 · 48 hours

**Subject (if goal not reached):** {{LIVE:percent}} % in two days. Thank you.
**Subject (if goal reached):** We did it. SOUL is funded.
**Preview:** What happened, and what's still open.

Hi,

two days ago SOUL opened its eyes on Indiegogo. Since then **{{LIVE:backers}} people** have backed it, for **€{{LIVE:raised}}** ({{LIVE:percent}} % of the goal).

[If funded:] **SOUL is funded.** Every reward will be made. From here, every euro goes to stretch goals first: at <!--f:stretch_first-->€95,000<!--/f-->, SoulOS in German, French, Spanish and Italian.
[If not funded:] **We're at {{LIVE:percent}} %.** It's all-or-nothing, so until we pass <!--f:goal-->€70,000<!--/f-->, nobody is charged and nothing is certain. The next days decide it.

Still open:
- **First Light** (<!--f:launch_price-->€249<!--/f-->): {{LIVE:first_light_left}} left [or: sold out, thank you]
- **Two Souls** (<!--f:two_price-->€498<!--/f-->): two SOULs, any two colours: the gift one
- **Campaign Price** (<!--f:campaign_price-->€269<!--/f-->)

The question we've been asked most: "Does it include AI?" No. SOUL connects your own Claude or your own OpenAI API key (in development), or lives offline. You pay them directly, and there's no SOUL subscription.

**[See SOUL →]** {{URL:campaign}}

Already backed? Thank you. The most useful thing now is one message to one friend who'd love it.

Hold the glass,
[de completat: founder first name]

---

## Email 3 · Mid-campaign (day 17)

**Subject:** Halfway. Here's what we built since launch.
**Preview:** A look inside, and {{LIVE:days_left}} days left.

Hi,

we're halfway through the campaign: **{{LIVE:backers}} backers, €{{LIVE:raised}}, {{LIVE:days_left}} days left.**

What we did in these two weeks (only real things, with photos):
- [de completat: one real progress item, e.g. "the golden sample in Ember, approved" + a real photo]
- [de completat: one SoulOS item, e.g. "a new expression" + a capture, labelled]
- [de completat: the most interesting backer question and our answer]

Next stretch goal: **{{LIVE:next_stretch}}**.

If you were waiting to decide: the campaign price is <!--f:campaign_price-->€269<!--/f--> until the end. <!--f:after_campaign-->After the campaign: Late Pledge at €299, from 30 November 2027, delivered with batch 2 (estimated August 2028).<!--/f-->

**[Back SOUL →]** {{URL:campaign}}

Hold the glass,
[de completat: founder first name]

---

## Email 4 · Last 48 hours

**Subject:** <!--f:urgency_subject-->48 hours left. After that, €299 in Late Pledge.<!--/f-->
**Preview:** The campaign ends <!--f:end_day-->Tuesday 9 November 2027<!--/f-->.

Hi,

the SOUL campaign ends on **<!--f:end_day-->Tuesday 9 November 2027<!--/f-->** [de completat: exact end time from Indiegogo]. <!--f:after_campaign-->After the campaign: Late Pledge at €299, from 30 November 2027, delivered with batch 2 (estimated August 2028).<!--/f-->

Today: **{{LIVE:backers}} backers, €{{LIVE:raised}}** ({{LIVE:percent}} % of <!--f:goal-->€70,000<!--/f-->).

[If not funded:] We're **€{{LIVE:remaining}}** from the goal. It's all-or-nothing: if we don't get there, nobody is charged and we don't make the batch. If you were going to back it, now is when it counts.
[If funded:] SOUL is funded. In the last 48 hours we're aiming for the next stretch goal: {{LIVE:next_stretch}}.

Campaign price: **<!--f:campaign_price-->€269<!--/f-->** (Two Souls <!--f:two_each-->€249<!--/f--> each). Delivery estimate: <!--f:delivery-->May 2028 (EU)<!--/f--> for batch 1, <!--f:delivery_b2-->August 2028<!--/f--> for batch 2.

**[Back SOUL before it closes →]** {{URL:campaign}}

Hold the glass,
[de completat: founder first name]

**Last-day resend (09:00, non-backers). Subject:** Last day for SOUL on Indiegogo
Body: two lines + button. "<!--f:last_day-->SOUL's campaign closes tonight. €269 today; after that, €299 in Late Pledge.<!--/f--> → {{URL:campaign}}"
