# Risks and challenges

<!-- Indiegogo required section. story-paste.html pastes it in full. Plain words on purpose. The f-blocks come from facts.json via tools/build_copy.py. -->

SOUL is a product in development, made by a small company. Backing it is not buying from a shop: you are helping us build the first batch, and some things can go wrong. Here is what we know can go wrong, and what we do about it.

**1. The batch is still ahead of us.**
Our bench prototype, being built now (board ordered, not yet tested), is the bigger M size. The SOUL you back is S (63 × 71 mm, round 1.75″ AMOLED).
[[G1: "SoulOS runs on the real S board with hold-to-talk voice since <date>."]]
[[G2: "An aluminium SOUL S has been assembled and filmed working in one take on <date>."]]
Between a few hand-built units and a batch of a few hundred there is still work: the final depth, the final battery, testing every unit. What we do: we didn't launch on renders. This page went live only after a real S worked on camera, and the specifications say clearly what is final and what is still being decided.

**2. Certification.**
<!--f:ce_risk-->SOUL passed radio, EMC, electrical safety and EN 18031 tests at [[CE: lab name]]; the EU Declaration of Conformity was signed on [[CE: date the EU DoC is signed]]. What remains: every unit in the batch is tested at the end of the line (radio signal, charging, screen), and any component change is re-assessed before it ships.<!--/f-->

**3. The delivery date can slip.**
Our estimate for batch 1 is <!--f:delivery-->May 2028 (EU)<!--/f-->. <!--f:delivery_risk-->CE must pass before launch; if it slips, the launch moves, not your delivery date. What can still move the date: machining and anodising the batch, and parcels around the holidays. We've kept about 10 weeks of buffer.<!--/f--> Most hardware campaigns ship late; we planned for that, but we can't rule it out.
What we do: an update every two weeks, weekly once shipping starts, and the same week for any delay, with the reason and the new date. If we miss the estimated month, you can cancel for a full refund (see *Refunds and cancellation*). Backers get their SOULs before any shop order.

**4. Colours can be hard to match.**
Anodised colours vary between batches, and warm colours like Ember the most. That's why this campaign offers <!--f:colours_n-->three<!--/f--> colours, not five. What we do: one approved golden sample per colour, one bath per colour, and inspection under daylight-standard light. Small variation between units is normal for anodised aluminium.

**5. Costs can be higher than we think.**
Until suppliers send written quotes, every unit cost is our estimate, and the goal includes a 15 % safety margin for that.
[[G3: "Written quotes from <partners> are within <x> % of our model."]]
If costs rise, we absorb them; we won't ask you for more money for your reward. Shipping is the fixed per-zone rate on this page: if the courier costs more, we pay the difference.

**6. Some parts come from a single source.**
<!--f:supply_risk-->The board inside SOUL S comes from one supplier (Waveshare ESP32-S3-Touch-AMOLED-1.75). What we do: a written volume quote before launch, and we buy every board for the batch as soon as the first payout arrives. A board of our own (with a pre-certified radio module) is a project for a later batch, not this one. [[D8: electronics route not decided yet; this paragraph follows facts.json decisions.D8]]<!--/f-->

**7. AI providers can change their terms.**
SOUL connects to your own Claude or your own OpenAI API key; it doesn't include AI. Anthropic and OpenAI can change their APIs, prices or rules at any time. OpenAI key support is still in development, and "Sign in with ChatGPT" depends on OpenAI's approval, which we don't control, so we don't promise it. You pay them directly for what you use.
What we do: SOUL works offline with no AI at all (eyes, moods, notes, reminders, alarms, focus), and it can switch between AIs without losing SOUL Memory. If we ever disappear, we publish the firmware so SOUL never becomes a brick.

**8. Voice depends on a speech service.**
<!--f:voice-->One honest detail: turning your voice into text needs a speech service. Today SoulOS uses OpenAI's, with your own OpenAI key. Voice for owners who only use Claude is in development. Typing on its round keyboard always works, with any AI and offline.<!--/f-->

**9. We are a small company.**
ARTEMIS DIGITAL is a small company in Bucharest, and this is our first campaign. What we do: specialist partners for machining, anodising, assembly and lab testing [[G3: name them]], a limited list of shipping countries, and rewards capped to what batch 1 can deliver (<!--f:batch1-->270<!--/f--> SOULs). Anything beyond batch 1 is "Campaign Price · batch 2", with its own later month (<!--f:delivery_b2-->August 2028<!--/f-->) shown on the reward before you pledge: we never move a pledge made under one date to a later one.

**10. If we can't deliver.**
If something makes delivery impossible, we refund every backer, and publish an account of where the money went. The full policy is in *Refunds and cancellation*.

Not a toy. SOUL is for people aged <!--f:age-->18<!--/f--> and over. It contains small parts and a lithium battery.
