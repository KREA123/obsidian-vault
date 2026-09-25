# 05 · Launch plan: from today to Founders 00 shipping

*SOUL package · 25 Sep 2026. Target: **25 numbered aluminium SOULs (Founders 00, Nº 001–025) at €349 incl. VAT, shipped in spring 2027, only after CE radio tests.** Sources: `research/10` §6–8, `research/03`, `investors/INVESTORS.md` (weekly plan), `investors/DECK.md` §11, `investors/FINANTARE-ROMANIA.md`. All costs are [E], in EUR.*

## Timeline

| Phase | Weeks (from 28 Sep 2026) | What happens | Exit gate | Cash out [E] |
|---|---|---|---|---|
| **0. Decide** | W0 (this week) | The **screen-size decision** (research/12: S 1.75" AMOLED = hero; build an M 2.8" IPS test in parallel?). EUIPO/TMview search for "SOUL". The ARTEMIS eligibility checklist (FINANTARE §1). Waitlist endpoint live (Formspree). **Do not change ARTEMIS shareholders or administrators** (a PoC grant condition). | Name is clear or a fallback is chosen; S confirmed | €0 |
| **1. Prototype P0** | W1–W3 | Order 2 × AMOLED-1.75 + 2 × 1.75C (the RF reference) + cells/speakers/screws/inserts (BOM P0-01…08). FDM fit print of the `plastic` STLs, measure the UNVERIFIED dims, rev B of the CAD. Flash, calibrate, pair with Claude Desktop. SLA looks-like + Cerakote. **Film the first real clip** (Claude asks → hold to approve). | P0 plastic works in hand; photos of a real unit | €300–450 |
| **2. First metal + RF** | W3–W6 | The same STEP (`alu` / `alu_band`) goes to JLCCNC, PCBWay, RapidDirect, Weerg, Xometry, ARSAT, Alvi → a real quote table. Order **2 CNC sets** (silver + graphite). RSSI test: bare board vs 1.75C vs P0 alu vs P0 alu_band (≤ 6 dB). Lab RFQs (3 labs). | RF loss ≤ 6 dB with the chosen variant; real CNC price @25 | €450–700 |
| **3. Design freeze + pre-scan** | W6–W8 | Rev C of the CAD, anodise golden samples approved. Pre-scan RF/EMC at the lab. Firmware security for EN 18031 (unique BLE credentials, signed-OTA plan, secure boot/flash encryption). SME Fund voucher → EU trademark + design filed. | Pre-scan passes or fixes are known | €2–3.5k |
| **4. CE / RED** | W8–W16 | Full RED + EMC + safety + RF exposure + EN 18031 on the frozen P0. Technical file, DoC, RO/EN guide, labels. ANMAP registration, collective scheme. Privacy, terms, withdrawal button. Insurance. | **EU DoC signed, CE on the product** | €7–17k |
| **5. Sell (in parallel from W8)** | W8–W16 | Waitlist → Founders 00 page: 25 units, €349 (#001–#010 €399 or an auction). **Take preorders with an honest ship month**, or a refundable €50 deposit until CE. Owners become co-designers (a Discord/WhatsApp group). | 25 reservations | marketing €0–1k |
| **6. Pilot run** | W12–W18 | Order 25 + 5 CNC sets in one anodise bath. Print chassis/pins/bands and OU capsules. Boxes, certificates, guides. Hand assembly (~45 min/unit) + the full QC checklist (02 §7). | 25 units pass QC | €5–5.5k |
| **7. Ship Founders 00** | W18–W20 (≈ Feb 2027) | ≤ 30 % SoC, DHL/courier in Romania, serial log (GPSR). **Ship before 18 Feb 2027 or keep the battery user-replaceable** (it already is). Collect feedback; film the unboxing. | 25 happy owners, 0 safety issues | shipping €150–300 |
| **8. Next** | from W20 | PoC grant (if won) → custom PCB with WROOM (EVT) → Batch 1 (300) → pre-seed. | – | – |

**Total to Founders 00 shipped ≈ €15–27k** (the BOM estimate is ≈ €20.3k). **Revenue ≈ €8.7k** at €349 × 25 (≈ €7.2k net of 21 % VAT, when VAT applies). The gap is the certification, which is **a brand and market investment**. It can be covered by the angel round (DECK: raising €350k) or by the PR BI PoC grant. **Do not buy anything from a future grant budget before the application is submitted.**

## Funding (from `investors/FINANTARE-ROMANIA.md`, in 5 lines)

1. **PR BI 1.1 Proof of Concept** (ADR Bucharest-Ilfov): €50–200k at up to 100 % (de minimis), no minimum company age, TRL 3 → 5. The call opens and closes in **Nov 2026**. Official annexes are in [`../investors/poc-1.1/`](../investors/poc-1.1/). **Best fit.**
2. **EUIPO SME Fund 2026:** 75 % of trademark/design fees up to €1,000 (+ €3,500 for patents), until 4 Dec 2026. Apply **before** paying the fees.
3. **EDIH** (Wallachia eHub, Green eDIH, FIT EDIH): free test-before-invest and EIC coaching (counts as de minimis).
4. **EIC Accelerator:** send a short proposal now; the full proposal (grant < €2.5M + equity) in 2027, at TRL 6 with traction.
5. **PR BI 1.2** (Dec 2026) or **Eurostars Call 12** (4 Mar 2027) for DVT/pilot/CE. Equity (angel €350k → pre-seed €1–1.5M) stays the main engine. A realistic non-dilutive total over 12 months is €0.1–0.25M.

## One checklist

**This week**
- [ ] Decide S vs M screen (read `research/12`, look at `renders/v7/`).
- [ ] TMview/EUIPO search "SOUL" cl. 9/42 + domain + handles.
- [ ] ARTEMIS eligibility data (CUI, balance sheets, de minimis received, employees, CAEN Rev.3 updated).
- [ ] Set up the waitlist `WAITLIST_ENDPOINT` (Formspree), then publish the landing page.
- [ ] Order the P0 parts (BOM section a) + 2 × 1.75C.

**Weeks 1–3**
- [ ] FDM fit print → calipers → CAD rev B (`prototip/cad/soul_p0.py`).
- [ ] Flash `amoled175`, calibrate the panel/touch/IMU, pair with Claude Desktop.
- [ ] SLA looks-like + Cerakote; first real photos and clip.
- [ ] Ask a UPB ETTI / IMT researcher to validate the TRL-3 report (PoC).

**Weeks 3–6**
- [ ] Send the STEP to 7 CNC shops (2/10/25/30), pick one, order 2 sets.
- [ ] RSSI test (bare / 1.75C / alu / alu_band) → choose the variant.
- [ ] Quotes from 3 labs (RED + EMC + safety + EN 18031).
- [ ] EUIPO SME Fund voucher.

**Weeks 6–8**
- [ ] Freeze the design; approve the anodise golden samples.
- [ ] Firmware EN 18031 hardening; rename the BLE device to SOUL.
- [ ] Pre-scan at the lab.
- [ ] File the EU trademark + design.
- [ ] Submit the PR BI PoC 1.1 application (Nov 2026 window).

**Weeks 8–16**
- [ ] Full CE/RED tests, technical file, DoC, labels, RO/EN guide.
- [ ] ANMAP EEE + battery registration, collective scheme, AFM.
- [ ] Privacy/terms/withdrawal button/legal footer; insurance.
- [ ] Open Founders 00 preorders (25) with an honest ship month.

**Weeks 12–20**
- [ ] Order 30 CNC sets (one bath), prints, OU capsules, boxes, certificates.
- [ ] Assemble and QC 25 units; keep the serial log.
- [ ] Ship at ≤ 30 % SoC; film the unboxing; collect feedback.
