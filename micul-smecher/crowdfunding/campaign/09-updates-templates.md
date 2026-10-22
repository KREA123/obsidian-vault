# Indiegogo update templates

Project → Communication → Updates (HC/489). Each update has a **title**, an **abstract** (one line), **content** and an **audience** (everyone / backers only / a backer group). Publishing doesn't notify anyone: click **"send notifications"** after publishing.

Cadence promise (on the page): **every 2 weeks** during production, **weekly** once shipping starts, and **the same week** for any delay or problem. Use the "Production update" template unless something specific happened.

House rules for every update:
- Real photos and videos of real parts. Renders labelled "Render (CGI), not a photo."; M prototype labelled "Prototype shown at a larger size (M). The product you back is S."
- Dates as month + "estimate" unless confirmed. Never round numbers up.
- Say what went wrong before what went right.
- `{{…}}` = fill in; `[de completat]` = founder's words; f-blocks are generated from `facts.json`.

---

## U1 · Launch day thank-you (day 1, evening)
**Audience:** everyone
**Title:** Day one. Thank you.
**Abstract:** {{backers}} people backed SOUL today. Here's what happens next.

Today {{backers}} of you backed SOUL, for €{{raised}} ({{percent}} % of the goal). We read every comment.

What happens now:
- The campaign runs until **<!--f:end_day-->Tuesday 9 November 2027<!--/f-->**. It's all-or-nothing: nobody is charged unless we reach <!--f:goal-->€70,000<!--/f-->.
- We'll answer every question in the comments within 48 hours, and add the common ones to the FAQ.
- Next update: [de completat: a real thing you'll show this week, e.g. "the second S shell sample"].

Hold the glass,
[de completat: founder first name]

## U2 · Funded
**Audience:** everyone
**Title:** SOUL is funded.
**Abstract:** Every reward will be made. Here's what changes and what doesn't.

We reached **<!--f:goal-->€70,000<!--/f-->** on {{date}}, with {{backers}} backers. Thank you.

What this means:
- Every reward on the page will be made and delivered. The estimate stays **<!--f:delivery-->May 2028 (EU)<!--/f-->** for batch 1 and **<!--f:delivery_b2-->August 2028<!--/f-->** for batch 2.
- <!--f:ce_short-->Radio, EMC, safety and EN 18031 tests passed at [[CE: lab name]]; EU Declaration of Conformity signed ([[CE: date the EU DoC is signed]]).<!--/f-->
- From here, money above the goal goes first to stretch goals. Next: **<!--f:stretch_first-->€95,000<!--/f-->, SoulOS in German, French, Spanish and Italian.**
- Rewards with caps stay capped. We won't promise more units than the first batch can deliver on time.

## U3 · Stretch goal unlocked
**Audience:** everyone
**Title:** Unlocked: {{stretch_name}}
**Abstract:** What it is, when you get it, and what it doesn't change.

At €{{amount}} we unlocked **{{stretch_name}}**.
- What you get: {{what}}
- When: {{when}} (for the languages: with the first software update after delivery; the pouch and the birth card: in every box).
- What it doesn't change: the hardware or the delivery date.
Next: {{next_stretch}}.

## U4 · Campaign ended
**Audience:** everyone
**Title:** It's done. What happens with your pledge now.
**Abstract:** Payments, the Pledge Manager, and the months to delivery.

The campaign closed with **€{{raised}} from {{backers}} backers**.
1. **Payments** are collected over the next days (Indiegogo retries a failed card up to 3 times over 15 days). If yours fails, you'll get an email: please update your card.
2. **Pledge Manager** opens on {{date}}: confirm your colour, your address, add an extra OU, and pay shipping.
3. **Refunds:** you can cancel for a full refund at any time before your SOUL ships (policy on the page).
4. **Next update:** in two weeks, with the first purchase orders.

## U5 · Pledge Manager open
**Audience:** backers
**Title:** Your turn: colour, address, shipping
**Abstract:** The Pledge Manager is open until {{close_date}}.

Open your pledge: {{URL:pledge_manager}}
- **Colour:** <!--f:colours-->Silver, Graphite and Ember<!--/f-->. You can change it until {{close_date}}.
- **Address:** we ship to <!--f:countries-->Romania, Germany, Austria, France, Belgium, the Netherlands, Italy, Spain, Poland and Sweden<!--/f-->.
- **Shipping**, per parcel:

<!--f:shipping_table-->
| Zone | Countries | Per parcel (fixed) |
|---|---|---|
| RO | Romania | €6 |
| EU 1 | Germany, Austria, Poland, the Netherlands, Belgium | €12 |
| EU 2 | France, Italy, Spain, Sweden | €15 |
| Extra SOUL in the same parcel | – | +€4 |
<!--/f-->

<!--f:shipping_note-->Shipping is paid after the campaign, in the Pledge Manager, at the fixed rates above. These rates are fixed: if the courier costs more, we pay the difference.<!--/f-->

- **Add-on:** extra OU egg, <!--f:ou_extra-->€35<!--/f-->.
The eyes aren't an option, as promised: each SOUL is born with its own.

## U6 · Production update (every 2 weeks)
**Audience:** backers (or everyone, if there's nothing private)
**Title:** Production #{{n}}: {{one_line_headline}}
**Abstract:** {{the one thing that moved, in one sentence}}

**Where we are** (status against the timeline on the page):

Copy the timeline table from the page and add a status column (done / in progress / late by x):

<!--f:timeline_table-->
| when (estimate) | what |
|---|---|
| October – November 2027 | the campaign (35 days, all-or-nothing) |
| November 2027 | payments collected; you confirm colour, address and add-ons in the Pledge Manager |
| November – December 2027 | batch orders: boards, cells, glass, aluminium shells, OU, packaging (tooling and the first article were approved before launch) |
| December 2027 – January 2028 | machining the shells (5–6 weeks, holidays included) |
| January – February 2028 | anodising in three colours, against the golden samples approved before launch |
| February 2028 | pilot run of 25 units, full quality check |
| February – March 2028 | assembly and testing of the batch |
| March 2028 | shipping starts (best case) |
| **May 2028** | **estimated delivery, batch 1 (EU)** |
| **August 2028** | **estimated delivery, batch 2 (only pledges beyond batch 1)** |
<!--/f-->

**What went wrong:** {{or "nothing new"}}
**What went right:** {{…}}
**Photos:** {{real photos; label any render}}
**Delivery estimate:** {{unchanged: <!--f:delivery-->May 2028 (EU)<!--/f--> / changed: see below}}
**Next update:** {{date}}

## U7 · Delay notice (the same week we know)
**Audience:** everyone
**Title:** A delay: {{what}}, new estimate {{month}}
**Abstract:** What happened, what we're doing, and your options.

We have a delay, and you're hearing it the week we found out.
- **What happened:** {{plain facts}}
- **What it moves:** delivery estimate from {{old}} to {{new}} for {{which backers}}.
- **What we're doing:** {{fix, owner, date}}
- **Your options:** you can cancel for a full refund at any time before your SOUL ships: reply to this update or write to office@krea.ro. [If this update sets a new date after a missed estimated month] if we miss this new date too, you can end your pledge for a full refund (policy on the page).
- **Next update:** {{date}}, whether or not it's fixed.

## U8 · CE lab result
**Audience:** everyone
**Title:** CE testing: {{passed / failed {{test}}, re-test on {{date}}}}
**Abstract:** What the lab tested and what it found.

SOUL went through {{tests: radio EN 300 328, EMC EN 301 489-1/-17, safety EN IEC 62368-1, RF exposure EN 62479, cybersecurity EN 18031}} at {{lab}}.
- **Result:** {{exact result per test}}
- [If passed] We'll sign the EU Declaration of Conformity once {{remaining steps}}; only then does CE go on the product and the first parcel leave.
- [If failed] What failed, why, the fix, the re-test date, and what it does to the delivery estimate.
Never write "CE-certified" before the Declaration of Conformity is signed.

## U9 · Shipping has started (weekly from here)
**Audience:** backers
**Title:** SOULs are on their way: wave {{n}}
**Abstract:** Who ships this week and how to track it.

This week: **{{count}} SOULs** to {{countries / reward groups}}. You'll get a tracking email from {{courier}}.
- SOUL travels at low charge (lithium battery rules). Put it in OU when it arrives.
- At first power-on, your SOUL is born. Tell us which eyes you got: we'll publish the birth register (opt-in names only).
- Problem with your parcel? Write to office@krea.ro with your pledge number. We reply within 48 hours.
- Next wave: {{date}}.

## U10 · Late Pledge open
**Audience:** everyone
**Title:** Late Pledge is open
**Abstract:** <!--f:late_price-->€299<!--/f-->, delivered with batch 2.

Missed the campaign? From today, SOUL is available in Late Pledge at **<!--f:late_price-->€299<!--/f-->** delivered with batch 2 (estimated <!--f:batch2-->August 2028<!--/f-->). Same SOUL S, same OU, same countries. Backers of the campaign ship first.

## U11 · Campaign didn't reach its goal (if it happens)
**Audience:** everyone
**Title:** We didn't make it this time. Nobody is charged.
**Abstract:** What happens to your pledge, and what we'll do next.

The campaign closed at **€{{raised}}** of <!--f:goal-->€70,000<!--/f-->. It was all-or-nothing, so **nobody is charged**, and nothing more is needed from you.
What we learned: {{honest, 3 lines}}.
What's next: {{e.g. a smaller first batch, a new date, or nothing yet}}. You'll hear it first, by email, only if you stay on the list.
Thank you for believing in a pebble that looks back.
