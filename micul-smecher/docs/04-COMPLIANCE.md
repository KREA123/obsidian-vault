# 04 · Compliance (EU / Romania)

*SOUL package · 25 Sep 2026. **Not legal advice.** Book one hour with a compliance consultant (~€200) before the first euro is collected. Sources: `research/03-compliance-2026-09-24.md` (with [V]/[S]/[K] tags), `research/10` §6, `research/09` §3.8, the vault note „Conformitate și riscuri Micul Șmecher", `ai/README.md`, `investors/INVESTORS.md`. The seller of record is **ARTEMIS DIGITAL S.R.L.** (Bucharest).*

## The three findings that shape the plan

1. **The Waveshare board uses a bare ESP32-S3R8, not a certified module**, so there is no module radio certificate to reuse. Founders 00 needs **full radio testing** (€5–12k). At 1k, a custom PCB with an **ESP32-S3-WROOM-1** reuses part of Espressif's evidence.
2. **The battery must be user-replaceable from 18 Feb 2027** (Battery Regulation Art. 11). This applies per unit placed on the market, including preorders delivered after that date. P0 already complies by design: screwed back, MX1.25 connector, foam not glue, standard Torx/PH.
3. **RED cybersecurity (EN 18031) applies**: SOUL connects to the internet through the phone or PC, and it has microphones. Stay on self-declaration by following the EN 18031 rules: no default passwords, LE Secure Connections, signed updates, secure boot + flash encryption in production.

## Rule by rule

| Area | What applies to SOUL | What we do | Cost [E] |
|---|---|---|---|
| **CE / RED 2014/53/EU** | EN 300 328 (2.4 GHz), EN 301 489-1/-17 (EMC), EN IEC 62368-1 (safety; cells IEC 62133-2), EN 62479 (RF exposure). Module A self-declaration. **No small-series exemption for consumer sales.** | Quote 3 labs (PL/RO or Shenzhen). Pre-scan first. Technical file + EU DoC + CE on the product. Manual lists the bands and max power. | €5–12k (PL/RO), €8–20k (DE); 4–6 weeks best case, 8–12 with fixes |
| **EN 18031-1/-2/-3** (Delegated Reg. 2022/30, since 1 Aug 2025) | 3.3(d) network, 3.3(e) privacy (internet-connected + mics), 3.3(f) fraud (no payments; probably out of scope) | Unique per-device credentials, BLE LESC 6-digit pairing (exists), signed OTA, secure boot v2 + flash/NVS encryption, debug locked. Scope memo from the lab. | €0–9k; a notified body only if a harmonised-standard restriction is hit |
| **Cyber Resilience Act** | Vulnerability/incident reporting since 11 Sep 2026; full obligations 11 Dec 2027 | security@ address, disclosure policy, SBOM for firmware and `ai/` | internal process |
| **Battery Regulation 2023/1542** | Art. 11 removability (18 Feb 2027); CE + DoC for the battery; crossed bin since 18 Aug 2025; label/QR ~2027–28 | Replaceable cell, spares for 5 years, instructions; cell maker's DoC + **UN38.3 test summary**; register as battery producer | ~€0 design + €0–300 docs |
| **WEEE / EPR, Romania (ANMAP)** | EEE producer register (500 lei), battery producer register (500 lei), collective scheme contract (Environ / Ecotic), AFM monthly declarations by the 25th, timbru verde (~0.15 lei/unit) | Register before the first sale. **Sell in Romania only** for Founders 00, since every other EU country needs its own registration + authorised representative (€1–3k per country per year). | ≈ €200 fees + a few hundred €/yr |
| **GPSR 2023/988** | Risk analysis + technical file kept 10 years; type/batch/serial on the product; manufacturer name, postal and e-mail address; RO instructions; complaints channel; accidents reported via Safety Business Gateway; online listing shows manufacturer, picture, identifier, warnings | Base laser mark + box label (02-MANUFACTURING §10), QC log per serial, RO/EN guide, complaints e-mail | €0.5–1.5k |
| **Toys** | Not a toy if marketed to adults | "Nu este o jucărie. Nu este destinat copiilor sub 14 ani." No child-play claims. | – |
| **AI Act** | **Art. 50(1) disclosure from 2 Aug 2026**: users must know they talk to an AI. No emotion-recognition claims (high-risk from 2 Dec 2027). No manipulation or exploiting vulnerabilities. | First boot: „Sunt SOUL. Sunt un AI, nu un om.", repeated on pairing and in Settings → About. Box and site carry the AI notice. Prompts enforce disclosure (`ai/`). | – |
| **Anthropic usage policy** | AI disclosure; no sexual content; no manipulation; extra safeguards for minors; "Claude" is a trademark | Launch **18+** for AI accounts. Write "works with Claude" + "SOUL is independent, not affiliated with or endorsed by Anthropic". **No Claude/Anthropic logos.** The Hardware Buddy API is in developer mode, so treat it as a layer, not the foundation. | – |
| **OpenAI usage policies / Apps SDK** | Public ChatGPT app needs OpenAI review (policies, privacy policy, OAuth) | Submit in SoulOS 0.6. Developer mode for tests. Never ask users for ChatGPT/Claude account passwords. | – |
| **GDPR / privacy** | On-device only: not a controller. Cloud memory, voice, BYO-key relay, waitlist: **controller**. | Privacy notice (purpose, basis, retention, rights, transfers), EU hosting, memory view and erase (endpoint exists), DPA with processors (Anthropic/OpenAI/hosting), double opt-in waitlist, cookie consent only if analytics are added | €0.3–1.5k |
| **Consumer law (preorders)** | 14-day withdrawal from receipt; **online withdrawal button required since 19 Jun 2026** (Directive 2023/2673); delivery ≤ 30 days unless an estimated month is agreed; 2-year legal guarantee; ANPC/SAL links | Wording in research/03 ("Pre-order – Founders 00 … Estimated shipping: [Month Year] … cancel for a full refund …"). Charge only after CE tests pass, or with a clear ship month. | drafting |
| **Shipping lithium** | ~1.85–3.7 Wh in equipment = **UN3481, PI 967 Section II**, ≤ 30 % SoC recommended | DHL/UPS/FedEx or RO couriers by road; no Deutsche Post / Poste Italiane | ~€0 |
| **Trademark "SOUL"** | **High conflict risk**: the word is crowded in classes 9 and 42 (many "Soul" marks: headphones, software, cars) | **TMview/EUIPO search this week** in classes 9, 42 (+14, 28). File an EU mark (€850 for 1 class + €50 for the 2nd + €150 each after). Apply for the **EUIPO SME Fund voucher first** (75 %, up to €1,000; deadline 4 Dec 2026). Keep a fallback: "SOUL by Suflet", a figurative mark, or a registered design for the shell. Check the domain and handles. | €0.9–3k (+ lawyer €300–600) |
| **Registered design (shell)** | Protects the v6 silhouette | EU registered Community design (~€350) with the v6 renders or CAD views, **before public launch** or within 12 months of disclosure (grace period) | ~€350 |

## Checklist: order, owner, cost

Owners:
- **A** = Andu (founder).
- **C** = compliance consultant or lab.
- **L** = lawyer or accountant.
- **Cl** = Claude (drafting and code).

| # | When | Item | Owner | Cost [E] | Done |
|---|---|---|---|---|---|
| 1 | Week 0 | TMview/EUIPO search "SOUL" cl. 9/42 + domain/handles; decide the fallback mark | A (+Cl draft) | €0 | [ ] |
| 2 | Week 0 | Check the ARTEMIS eligibility list (FINANTARE §1); EORI number for imports | A + L | €0 | [ ] |
| 3 | Week 1 | 1 h compliance consultant: scope (RED + 18031 + battery + GPSR), Waveshare-in-a-case question | A + C | €200 | [ ] |
| 4 | Week 1 | RFQ to 3 labs for RED + EMC + safety + EN 18031, with a pre-scan option | A (+Cl emails) | €0 | [ ] |
| 5 | Week 1–2 | Cell supplier: DoC + UN38.3 summary + MSDS for the 503035 | A | €0–300 | [ ] |
| 6 | Week 2 | EUIPO SME Fund voucher application (before paying fees) | A | €0 | [ ] |
| 7 | Week 3 | File the EU trademark (+ design) | A / L | €0.9–1.3k | [ ] |
| 8 | Week 3–6 | Firmware security for 18031: unique BLE credentials, signed OTA plan, secure-boot/flash-encryption build flags, debug lock, SBOM | Cl + A | €0 | [ ] |
| 9 | Week 5–6 | Pre-scan on the first CNC unit (RF/EMC) | C | €1–2k (part of the lab budget) | [ ] |
| 10 | Week 6 | ANMAP EEE + battery registration, collective scheme contract | A | ≈ €200 + scheme | [ ] |
| 11 | Week 6–12 | Full RED/EMC/safety tests + 18031 assessment on the design-frozen P0 | C | €5–12k + €0–9k | [ ] |
| 12 | Week 8–12 | Technical file, risk analysis (GPSR), EU DoC, labels, RO/EN guide, AI notice | Cl draft + C review | €0.5–1.5k | [ ] |
| 13 | Week 10 | Privacy notice, terms of sale, withdrawal button, cookies, legal footer (company data) | L + Cl | €0.3–1.5k | [ ] |
| 14 | Week 10 | Product liability insurance | A | €300–800/yr | [ ] |
| 15 | Before shipping | CE on the product and box, DoC signed, AFM declarations running, ≤ 30 % SoC shipping | A | – | [ ] |
| 16 | Ongoing | CRA vulnerability handling (security@), complaints log, accident reporting | A | – | [ ] |

**Budget for Founders 00, Romania only: ≈ €7–20k** (€15k in the BOM). **At 1k+ units: €30–80k over 4–6 months** (full RED at an EU lab, EN 18031 ± a notified body, custom-cell IEC 62133-2 + UN38.3, EPR in 3–5 countries, CRA readiness).
