# SOUL v3 — "the amulet": design language (raw, 2026-09-24)

Tags: **[V]** verified today (URL fetched 2026-09-24) · **[K]** background knowledge (verify before quoting publicly) · **[E]** estimate / engineering judgement.
Builds on `06-product-design-v2` (board mechanicals, BOM, battery model, reference objects: r1, Humane, Playdate, Tamagotchi, Nothing, Oura, AirTag, Plaud, Pebble, TE, Rams) and `05-brand-productdev-funding` (launch playbook, iPhone keynote template). Not repeated here.
Context: v1 = frosted-white coin pendant on a bail, big black domed glass, glowing eyes → founder: "an amulet, has a soul". v2 = 68×60 palm pebble lying flat → lost it. Diagnosis [E]: v2 removed the three things that made v1 an amulet — **a hanging point, a round centred "eye", and verticality** (it lay down like a remote). v3 restores them without giving up v2's battery/speaker/carry lessons.

---

## 1. Amulet / talisman archetypes — what makes an object read "amulet"

| Archetype | Form facts | Why it carries weight | Steal for SOUL |
|---|---|---|---|
| **Locket** | pendant that "opens to reveal a space" for photos/keepsakes; ovals, hearts, circles; gold/silver; 1–2 photos; late-17th-c. origins; ~1860 memento lockets replaced mourning rings; given at christenings, weddings, funerals [V wiki/Locket] | a **hidden inside** that only the owner knows; holds a person | the back is private: a caseback that opens to something personal (name, birth record, battery) |
| **Pocket watch** | hunter case (hinged lid) or open face; **pendant/bow + crown at 12**, sub-seconds at 6; chain/fob to waistcoat; glass on dials from 1610; stem-wind 1851 [V wiki/Pocket_watch]; heirloom, US retirement gift [V] | the most "precious machine" archetype: crown, chain, engraved caseback, **passed on** | crown-at-12 as the hanging point; engraved caseback; the "opening the lid" gesture. Size match: 16s/18s movements ≈ Ø43–45 mm, cases ~Ø50–55 [K] ≈ our Ø46 module — **SOUL is literally pocket-watch-sized** |
| **Compass** | round, glass over a live needle, lid, lanyard ring [K] | a small round thing that is *alive* and *points you somewhere* | the eyes as the needle: they turn toward you/what matters (IMU) |
| **Nazar** (🧿) | concentric dark-blue/white/light-blue/black **eye** in glass; Mediterranean, beads from 16th c. BCE; Turkey/Greece/Persia/India; worn, hung on doors/cars; "if it breaks it absorbed a curse"; Unicode 2018 [V wiki/Nazar] | **an eye that watches over you** — the oldest protective symbol in our region | our eyes *are* a nazar that blinks. Concentric rings: glass → halo → rim = a nazar in plan view |
| **Mărțișor** (RO/MD) | red+white intertwined string + small charm (coins, shapes); pinned to the chest from 1 March, worn days–months, then **tied to a tree**; a gift between people; talisman for fortune/protection; UNESCO ICH [V wiki/Mărțișor] | Romanian-native ritual: *given*, *worn over the heart*, *released* | red-white cord edition on 1 March; "given, not bought" gifting flow; founder story |
| **Byzantine enkolpion / panagia** | medallion with an icon, worn on the chest by Orthodox bishops on a long chain; oval/round/rhombus; jewels around the icon; can be a hollow **reliquary**; Byzantine origin, possibly from monks' eucharistic lockets [V wiki/Encolpion]; Romanian baptismal cross/iconiță from the godparent [K] | a **face in a frame, worn on the sternum**, hollow with something sacred inside | the frame-around-a-face composition; long-chain sternum drop; "a face that is a presence" |
| **Omamori** | small brocade pouch, prayer inside **not to be opened**; on bags, backpacks, phone straps, cars; **renewed yearly**, old ones returned to the shrine [V wiki/Omamori] | purpose-specific (exam, travel, health); ritual renewal | bag-charm carry mode; yearly "renewal" = new seasonal skin/cord + diary-of-the-year keepsake |
| **Scarab** | beetle top, flat **inscribed base** used as a seal; 6–40 mm, mostly 10–20; **heart scarabs** 4–12 cm placed over the heart; rebirth/Khepri [V wiki/Scarab] | domed living top + flat inscribed underside = the canonical amulet section | domed face, flat engraved back; the back is a "seal" (your identity) |
| **Tamagotchi** | egg-shaped keychain, 3 buttons; first conceived "to be worn like a wristwatch"; 40M in 2 years, 98M+ by 2025 [V wiki/Tamagotchi] | a creature you carry and care for; shape = "something is born in here" | the "birth" moment; care loop; chain-carry |
| **Poké Ball** | red/white sphere, black band, central button [K] | readable in silhouette; one centre button = the whole meaning | a centre that is the button |
| **AirTag / Apple Watch** | AirTag Ø31.9×8 mm, 11 g (gen 2 11.8 g, Jan 2026), no mounting hole → accessory ecosystem ("accessory tax") [V wiki/AirTag]; Watch 38→46 mm cases, Digital Crown scroll/zoom, press = home; crown prototyped as a dongle [V wiki/Apple_Watch] | engraving at purchase makes a mass product personal [K]; accessories = carry modes | engraving; one attachment standard for many carries — but *build the attachment into the object* (AirTag's lesson) |

**Formal grammar of "amulet"** [E, synthesised from the table]:
1. **A hanging point** (bail, bow, loop, crown) — the single strongest cue. Without it, a disc is a coaster/puck (v2's failure).
2. **Verticality / a top and a bottom** — the bail defines 12 o'clock; the object has an orientation, like a face.
3. **A centre "eye" / stone / icon** in a **frame** (rim/bezel) — concentric composition (nazar, enkolpion, watch dial, cabochon).
4. **Dome over flat**: domed precious front, flat inscribed back (scarab, cabochon, watch caseback).
5. **A private back** — engraving, hidden compartment, seal; something only the owner sees (locket, omamori).
6. **Worn near the heart / on the sternum** and **touched often** (rubbed, held, checked like a watch).
7. **Given, named, passed on** — provenance is part of the object (mărțișor, baptismal cross, retirement watch).
8. **Small enough to close a hand over** (≤ ~60 mm) — a talisman disappears into a fist; a gadget doesn't [E].

---

## 2. What made tech objects iconic → rules

| Object | The one thing | Rule it teaches |
|---|---|---|
| iPhone 2007 (115×61×11.6 mm, 135 g, 3.5", one home button, glass front/Al back; Time Invention of the Year) [V wiki/iPhone_1st_gen] | the face *is* the product; one button to go home | **One face, one button.** Everything else disappears. |
| iPod click wheel (capacitive ring over 4 mechanical buttons; credited to Schiller; 4th gen) [V wiki/IPod_click_wheel] | thumb circles → thousands of songs | **A signature gesture native to the shape** (round object → circular gesture). |
| Apple Watch Digital Crown [V] | old watch part given new meaning | **Reuse an archetype's organ, re-wire it** (crown/bail → our connector). |
| Force Touch / iPhone 7 home button: electrodes around the display sense pressure; Taptic Engine linear actuator peaks in one cycle, ~10 ms pulse → felt "click" with no moving button [V wiki/Force_Touch] | a click you feel but that doesn't move | **Haptics can fake mechanics** — the path to "the whole face is a button". |
| AirTag [V] | white disc + polished steel back, engraving | **Two-material contrast**: humble front, precious back. |
| Nothing Phone (1): 900 LEDs on transparent back, Glyph synced to sounds/charging [V wiki/Nothing_Phone_(1)] | light as language | **Light is the voice when the screen sleeps.** |
| Teenage Engineering (OP-1, Pocket Operators, Playdate crank, r1, Frekvens) [V wiki/TE] | strict graphic/colour language, tactile | **One fixed visual system**, playful but disciplined. |
| Tamagotchi [V] | egg = something is alive inside | **Shape tells the story** before the screen turns on. |
| Friend pendant: white disc ~2" on a "shoelace-thin cord", colour glow, one touch button, $129, 15 h claimed; "Life Alert button disguised as an Apple product", white plastic yellows; strangers asked 3× [V fortune.com 2025-10-03; search snippet] | pendant + glow gets noticed | **Avoid: cheap cord, yellowing white ABS/PC, medical-alert look, always-listening.** Use UV-stable/frosted glass or ceramic white, a real necklace, and a visible privacy gesture. |
| Humane AI Pin: two magnetic parts sandwich clothing; touchpad tap to listen; heat → ice packs, 9-min projector cap [V wiki/Humane] | the magnet mount | **Magnetic carry works; thermal and "replace the phone" don't.** |
| Meta Muse Charm (prototype, Sept 2026): keychain "digital charm", small screen with animated avatar "Jolly", **fingerprint sensor in a corner** to talk, layout not final [V the-gadgeteer 2026-09-24] | charm + avatar + voice | Our moat must be **the object** (precious, round, eye-as-button) — not the concept, which Meta now owns in the press. Ship the design language first. |
| Limitless Pendant: acquired by Meta (site confirms) [V limitless.ai] | recorder pendant | memory pendants consolidate into Big Tech → the independent, beautiful, private one has room. |
| Rabbit r1 / Humane (see 06) | — | great object ≠ daily reason. |

**The 8 rules of icon-making** [E]:
1. **Silhouette in shadow**: recognisable as a black shape at 20 px (iPod, Poké Ball, Tamagotchi). For SOUL: *circle + crown at 12*.
2. **The face is the product**: one glass, edge-to-edge; no logos on the front.
3. **One signature gesture** that you can name in two words ("press the eye", "turn the crank", "spin the wheel").
4. **One hero material + one precious contrast** (glass/aluminium; white/steel).
5. **An organ borrowed from an archetype and rewired** (crown, wheel, crank).
6. **Light/animation as character**, consistent across all states.
7. **A private side** that makes it yours (engraving, back).
8. **Nothing that says "gadget"**: no visible screws, ports, grilles, stickers on the hero faces.

---

## 3. Pendant ergonomics & fitting the 1.75 board

### 3.1 What jewellery norms say
- Gold pendants: light 1–2 g, everyday 2–4 g, statement 5–8 g, heavy festive 8–12 g; "ideal 2–6 g"; daily wear 2–3 g [V blog.bluestone.com]. Everyday pendants 1–5 g; designer/22 ct 6–12 g [V search snippet, simplyrusticjewelry].
- Jewellers' forum: a 0.85 oz (~24 g) stainless pendant and a 1 oz (~28 g) pendant worn comfortably by some; "weight is personal — wear it for an extended time and see" [V orchid.ganoksin.com].
- Chain: 16–18" sits at the collarbone, 18" most common, 20" for layering [V bluestone]; shorter chains keep a pendant in place; **pinch test** — if the chain forms a tight V at the bail, the pendant is too heavy for that chain [V elainebjewelry].
- No jewellery source quantifies > ~30 g as comfortable daily. Tech/heritage comparables: AirTag 11 g [V], Plaud NotePin ~17 g [V in 06], Humane ~34 g + booster [K], military dog tags ~2×5 g [K], pocket watches 70–130 g but carried in a pocket with the chain only as a leash [K].
- **Conclusion [E]:** ≤ 25 g = jewellery; 25–45 g = "statement pendant", fine on a 2–3 mm cord/leather or ≥ 2.5 mm chain worn long (70–80 cm, sternum), flat back, all-day OK for most; 45–60 g = noticeable neck drag after hours, swings/bounces when walking, hits the sternum when bending → wear for occasions, carry the rest of the time; > 60 g = not a necklace. Weight felt ≈ weight × swing; a flat back + low centre of mass + long cord reduces bounce.
- **Safety**: breakaway (pop-apart) clasps release under a sharp pull to reduce snag/choke hazard, snap back together [V search snippet, lanyard vendors]; no release-force standard found today — spec our own [E]: release at ~20–40 N (well above 0.6 N static load of a 60 g amulet ×~5 g dynamic ≈ 3 N, well below injurious neck force). Mandatory for an 18+ product anyway; strangulation is the #1 cord risk for kids (keep 18+ positioning from 05).
- Keychain/bag charm: Tamagotchi egg ~40×45×15 mm ~20 g [K]; bag charms (Labubu-class) are often 60–100 mm and 30–80 g [K] → a Ø56 × 16 mm, 50 g SOUL is normal as a bag charm and a pocket watch; only the necklace mode is at the edge.

### 3.2 Carry modes and their limits
| Mode | Accepts | Notes |
|---|---|---|
| Long necklace (70–80 cm, 2–3 mm waxed cotton / leather / 2.5 mm curb chain, breakaway clasp) | ≤ 55 g | sits on the sternum like an enkolpion; face-out; IMU knows "worn" (vertical + walk cadence) |
| Pocket-watch chain / fob to belt loop or bag ring | any | the default everyday carry; lifts out to talk — "checking the watch" gesture |
| Bag charm / keyring (short chain + lobster) | any | omamori mode; tumbling → metal rim + sapphire/AR glass must survive keys |
| Palm (no attachment) | any | v2's lesson kept: the domed back sits in the hand |
| Desk "altar" (magnetic cradle, charging, 15–20° tilt) | — | Claude approvals / focus; the icon-corner on the desk |
| Wrist strap (short loop) | — | for runners/field; **not** a watch |

### 3.3 Packaging the Waveshare 1.75 into Ø56–58 [E, from STEP numbers in 06]
- Radial: module/PCB Ø46.0, cover glass Ø48.96. Wall 1.8–2.2 mm + 1.0 mm halo light-pipe → **inner Ø ≈ 51.5, outer Ø 56 (production, snap/bayonet, no insert bosses outside the glass)**. v1's Ø60.8 came from insert bosses; a **bayonet caseback** (twist-lock, like a watch/Tamagotchi battery door) removes them. Dev proto on the stock board: Ø58–60.
- Axial stack (production, custom board, no 8-pin header): glass dome proud 0.6 → module at battery zone 8.9 → foam/shield 0.5 → cell 5.0–6.0 → caseback 1.2–1.5 (domed 0.5 at centre) = **16.5–17.5 mm centre, ~11–12 mm at the rim** (chamfered/curved flank). Stock Waveshare board (12.7 mm header at the edge) → proto 19–20 mm unless the header is desoldered (then ~17.5).
- Cell: a rectangle must fit inside the inner Ø ~51 → diagonal ≤ 50 mm: **603040 (6×30×40, ~650–700 mAh, ~13 g)** or 503040 (~550–600 mAh, ~11 g); a round pouch Ø40×5 is ~350–450 mAh [K/E]. Choose **603040 ≈ 650 mAh** (v1 had 400; v2 planned 1000).
- Speaker: the 2030 kit speaker doesn't fit behind a 6 mm cell. Use a **1511 or 1813 box speaker (~3 mm)** in one of the two side segments beside the 30 mm cell, firing through a micro-perforated slot **under the crown** (the crown hides the grille — rule 8); LRA (Ø8–10 mm coin or 8×4 X-axis) in the other segment.
- Weight budget [E]: module (glass+AMOLED+PCB) ~18–22 g · cell 13 · speaker+LRA 4 · halo LEDs+light pipe 2 · shell front ring (PC/ceramic-look) 6–8 · caseback 5 (PC) / 10 (stainless or zirconia) · crown/bail 2–4 · **≈ 50–58 g** (PC back ~50, steel/ceramic back ~56). Target **≤ 52 g base**; the "Heirloom" edition (steel caseback) ~56 g is positioned as pocket-watch/bag carry first.
- Battery life (06 model, 360 mAh/day typical): 650 mAh → **~1.8 days typical, a full day heavy**. Amulet-specific savings: when worn face-in or in a pocket (proximity/IMU) the panel is off and the **halo** carries status at ~1–3 mA → realistic 2 days; nightly altar charging is the ritual ("put your soul to sleep").

---

## 4. Signature features — ranked (wow × ESP32-S3 feasibility × cost)

Scores 1–5; rank = wow × feasibility × (6 − cost) [E].

| # | Feature | Mechanism (concrete) | Wow | Feas. | Cost (1 = cheap) | Score | Risks / mitigations |
|---|---|---|---|---|---|---|---|
| **1** | **"Press the eye" — the whole glass face is the button** (hold = talk, click = wake/confirm, double = back) | Module bonded into an inner **floating carrier** (PC/Al) on a perimeter silicone gasket (0.3–0.4 mm travel, also the seal). Behind the carrier: **one central 5 mm metal dome** (≈ 2.5–3.5 N) on a small flex + 3 PTFE glide pads at 120° so an edge press still actuates (the iPod centre-button trick). Alternative solid-state: 3 thin-film strain gauges/FSRs (e.g. FSR-400 class) under the carrier → HX711-class ADC or ESP32 ADC; threshold + LRA 10–15 ms click (Force Touch pattern). Touch panel (CST9217) stays for swipes; **mic power hard-gated by the dome** (privacy promise made physical, cf. 06). | 5 | 4 | 2 | **80** | Pocket/chest false presses → gate by IMU orientation + proximity + "held" capacitance; ingress at the gasket → IP54 target, not IP67; AMOLED/glass stress → carrier takes the load, not the panel; drop: carrier travel stop. Dome life ≥ 1M cycles [K]. Prototype first — it *is* the product. |
| **2** | **Soul light — frosted halo ring** around the glass that glows state colours (listening = warm white breath, thinking = slow orbit, needs-you = amber pulse, Claude approval = the Claude orange, private/mic-off = no light) | 8–12 side-emitting RGB LEDs (SK6812-mini-E / WS2812-2020 class) on the PCB rim → 1 mm frosted PC/PMMA light-pipe ring flush with the glass; 1 GPIO (RMT). ~0.5–3 mA dim avg. Visible when the panel is off and when **worn face-in** (halo edge still glows) | 5 | 5 | 1 | **125** | light bleed into the AMOLED edge → black gasket; must feel "soul", not "gaming RGB" → one colour at a time, slow curves, max 20 % brightness. Custom board needed (Waveshare has no free LED rim) — proto with a flex ring. |
| **3** | **The Crown** — a magnetic bail at 12 o'clock that clicks into every carry: necklace, fob chain, bag charm, wrist loop, **altar dock** (charging through the crown contacts) | Crown = small stainless knuckle with 2 N52 magnets + mechanical spring latch (magnet aligns, latch holds; release by pinch — never magnet-only for a 50 g swinging object). Two gold pogo targets on the crown seat = charging (USB-C only on dev units). Accessories each carry a "crown socket". | 4 | 4 | 3 | 48 | snag → breakaway is at the **clasp**, not the crown; magnets near compass/IMU → calibrate; pogo corrosion from sweat → gold-plate, recessed; tooling cost for a precise latch. |
| **4** | **Heirloom caseback** — bayonet-twist caseback (opens with a coin, like a watch), laser-engraved on the inside: name the owner gave the soul, **birth certificate** (soul no. #00001/…, date/time "born", place "Cluj-Napoca, RO", firmware seed of its personality); outside: owner's engraving. Behind it: replaceable cell (EU Battery Regulation 2027). | Fibre-laser engraving on stainless/zirconia or PC laser-mark; certificate also as a signed record in the app; transferable ("pass it on" = wipe memory, keep the name/lineage). | 4 | 5 | 2 | **80** | bayonet seal/ingress → O-ring; engraving lead time → engrave at fulfilment, not at factory; cost +€2–8. |
| **5** | **Two souls meet** — two SOULs within ~1–2 m notice each other (BLE), look at each other, blink, halos sync colour; optional "exchange a mărțișor" (a note/contact) with both faces pressed | BLE 5 advertising with rotating ID + RSSI threshold; opt-in; no data leaves without both presses. ESP32-S3 does BLE adv/scan concurrently with low duty cycle (~0.5–1 mA) [K]. | 5 | 5 | 1 | **125** | privacy/tracking → rotating identifiers, off by default in public, "friends only" mode; battery → scan windows only when awake/worn. Pure firmware — viral demo material. |
| 6 | "Hold it to your heart" — first-boot naming ritual and daily unlock: held vertical against the chest (IMU orientation + back capacitive "held" + proximity covered) for 3 s → eyes close, halo breathes in time, soul "wakes"/bonds | IMU + ESP32-S3 touch pad on the caseback inner face + ALS/proximity | 3 | 5 | 1 | 75 | no biometric claims (it does *not* read your heartbeat — say so); make it ritual, not security. Include as the **onboarding**, not a headline. |
| 7 | Rotating bezel / crown scroll | magnet ring + AS5600 hall encoder, or detent ring | 3 | 2 | 4 | 12 | snags, dust, seal, +3–4 mm Ø, reads "watch/diver". **Replace with a software "rim scroll"**: circular swipe on the outer 4 mm of the touch glass (click-wheel gesture on the glass) + LRA ticks. Cost €0. |

**Pick for v3:** #1 Press-the-eye (the headline gesture), #2 Soul light halo, #4 Heirloom caseback, #5 Two souls meet (launch demo), #3 Crown as the carry system; #6 as onboarding ritual; #7 as software rim-scroll only.

---

## 5. Recommendation — "SOUL v3 — the amulet"

| Item | Spec [E unless tagged] |
|---|---|
| Shape | Round coin-amulet, **crown bail at 12** (defines up), domed black glass "eye" in a thin frosted halo ring, slim bright rim; domed flat-ish caseback. Silhouette: circle + crown. |
| Dimensions | **Ø56 × 16.5 mm centre / ~11.5 mm at rim** (production); crown adds ~6 mm height → 62 mm overall. Dev proto on Waveshare 1.75: Ø58–60 × 19–20. |
| Display | 1.75" 466×466 AMOLED, Ø43.76 active, cover glass Ø48.96 domed/2.5D black, AR + oleophobic; option: sapphire crystal on Heirloom. |
| Front materials | frosted white (or smoke) glass-filled PC / PMMA halo ring; bead-blasted stainless or ceramic-white rim (non-metal zone near the antenna at 2–4 o'clock). No logo on the front. |
| Caseback | bayonet twist (coin slot), stainless (Heirloom) or pearl-white ceramic-look PC; outside: owner engraving; inside: soul **birth certificate** (no., name, born date/time, "born in Romania"); O-ring; replaceable 650 mAh cell behind. |
| Colours | **Bone** (frosted white, v1 DNA), **Onyx** (smoke/black), **Mărțișor** edition (bone + red-white cord, 1 March drops); seasonal cords, never seasonal personalities. |
| Inputs | **Press the eye** (floating face on a dome: hold = talk, mic hard-gated; click = wake/OK; double = back); touch glass (tap/swipe, rim-scroll); IMU (lift-to-wake, face-in = sleep/DND, walk = worn); capacitive "held" back; proximity/ALS; 1 hidden reset in the crown seat. |
| Outputs | eyes (home screen); **soul-light halo** (status when the screen sleeps); 1511/1813 speaker firing under the crown; LRA haptic "heartbeat"/click. |
| Carry modes | long necklace 75 cm (waxed cord or 2.5 mm chain, breakaway clasp); pocket-watch fob chain; bag charm; palm; wrist loop; **Altar** desk dock (magnetic crown seat, pogo charging, 15–20° tilt). |
| Battery | **603040 ≈ 650 mAh**, 0.5C charge (~1.5 h) via crown pogo pins; ~2 days typical, >7 days standby [E from 06 model]. |
| Weight | **≈ 50 g** (Bone, PC back) / ~56 g (Heirloom steel back). Necklace comfortable for hours; everyday carry = fob/bag/pocket. |
| Radio | Wi-Fi + BLE (ESP32-S3); two-souls BLE meet; Claude Desktop Buddy BLE; phone relay. |
| Ingress / safety | IP54; breakaway clasp; 18+; no always-listening; mic physically gated by the press. |
| Price / COGS | COGS ~€45–60 @1k (06 BOM minus bigger cell/speaker, plus halo/dome/crown/caseback engraving); retail **€149 Bone/Onyx with cord + altar, €249 Heirloom** (steel back, sapphire, chain, numbered). |

**The rules of SOUL** (design language):
1. **SOUL is a round eye in a frame, hung from a crown** — if the silhouette in shadow isn't a circle with a crown, it isn't SOUL.
2. **The face is the soul and the only button**: one glass, no logo, no second control on the front — you press the eye to speak, and only then does it hear you.
3. **When the eyes sleep, the light speaks**: one colour at a time, slow as breath, never louder than a candle.
4. **The front is humble, the back is precious**: the caseback carries your name, its birth record and its battery — made to be opened, engraved and passed on.
5. **It is carried, not operated**: it hangs over your heart, lives on your chain or your altar, and every interaction ends with the eyes looking back at you.

**Launch line** (spirit of "an iPod, a phone, an internet communicator"):
> "Today we're introducing three things. A talisman. A voice for your AI. And a keeper of your day. A talisman… a voice for your AI… a keeper of your day. These are not three devices — this is one soul. We call it **SOUL**."
Short tag: **"Press the eye. It listens."** / RO: **„Apasă ochiul. Te ascultă."**

---

## 6. Open questions / next steps
- Build 3 looks-like models (Ø54 / 56 / 58, 45/50/56 g with lead shot) and wear each 3 days on cord vs chain → pick Ø and weight by felt comfort (pinch test, bounce when walking).
- Works-like "press the eye": Waveshare board in an SLA floating carrier on a 5 mm dome + LRA; measure false-press rate on a necklace/in a pocket for a week.
- Custom board needed for halo LEDs, crown pogo, speaker placement; keep ESP32-S3 + CO5300 + AXP2101 architecture.
- Verify: Friend exact weight/diameter, Limitless pendant specs, breakaway release forces (ask clasp vendors), pocket-watch Lancashire sizes, cell datasheets (603040 capacity/weight) before public use.

## 7. Sources (all fetched 2026-09-24 unless noted)
- https://en.wikipedia.org/wiki/Locket [V]
- https://en.wikipedia.org/wiki/Nazar_(amulet) [V]
- https://en.wikipedia.org/wiki/Mărțișor [V]
- https://en.wikipedia.org/wiki/Encolpion [V]
- https://en.wikipedia.org/wiki/Omamori [V]
- https://en.wikipedia.org/wiki/Scarab_(artifact) [V]
- https://en.wikipedia.org/wiki/Pocket_watch [V]
- https://en.wikipedia.org/wiki/Tamagotchi [V]
- https://en.wikipedia.org/wiki/AirTag [V]
- https://en.wikipedia.org/wiki/Apple_Watch [V]
- https://en.wikipedia.org/wiki/IPhone_(1st_generation) [V]
- https://en.wikipedia.org/wiki/IPod_click_wheel [V]
- https://en.wikipedia.org/wiki/Force_Touch [V]
- https://en.wikipedia.org/wiki/Nothing_Phone_(1) [V]
- https://en.wikipedia.org/wiki/Teenage_Engineering [V]
- https://en.wikipedia.org/wiki/Humane_AI_Pin [V]
- https://en.wikipedia.org/wiki/Friend_(product) [V] (size "just under two inches")
- https://fortune.com/2025/10/03/friend-ai-necklace-review-avi-schiffmann/ [V]
- https://the-gadgeteer.com/2026/09/24/meta-muse-charm-ai-assistant-keychain/ [V]
- https://www.limitless.ai/ [V] (acquired by Meta)
- https://blog.bluestone.com/how-many-grams-is-a-gold-pendant-average-weight-length-for-women/ [V]
- https://orchid.ganoksin.com/t/pendant-weight-it-is-too-heavy/37347 [V]
- https://www.elainebjewelry.com/blogs/jewelry-tips-quick-history/choosing-pendant-weight-for-comfort-and-style [V]
- WebSearch snippets only (page 503 / not opened): simplyrusticjewelry.com necklace weight guide; specialistid.com / nametag.com breakaway lanyards; techbuzz.ai Friend review ($129, 15 h) — treat as [V-snippet].
- Poké Ball wiki fetch returned no usable content → Poké Ball notes are [K].
- Project: research/05, research/06, cad/micul_smecher.scad (STEP-derived dimensions) [V].
