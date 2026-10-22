#!/usr/bin/env python3
"""SOUL size S - Indiegogo goal model v2 (bottom-up, honest minimum).

    python3 -I micul-smecher/crowdfunding/tools/goal_model.py          # tables + writes goal_model.out.json
    python3 -I micul-smecher/crowdfunding/tools/goal_model.py --quiet

The goal is the smallest batch at which the money collected, minus VAT we will owe, platform fees and failed
payments, pays for every reward of that batch plus the one-time costs that sit INSIDE the goal for the active
scenario, plus a contingency. One-time costs paid BEFORE the campaign (from PoC 1.1, a loan or own money) are
listed separately and are not in the goal. Marketing is never in the goal.

Scenarios (facts.json campaign.scenarios): after_ce (default, keeps the founder's rule) and before_ce (needs the
D1 waiver). Ladders: pricing.ladders A and B. Routes: size_S.electronics_routes A (custom PCB) and B (Waveshare).
Sources:
  [model]  micul-smecher/docs/factory/SOUL-fabrica-model.xlsx (sheet Ipoteze, M size, EUR net)
  [s]      micul-smecher/docs/12-SIZE-S.md §1.2, §3.1 (S electronics, battery, BOM delta)
  [compl]  micul-smecher/docs/04-COMPLIANCE.md
  [poc]    01 Afaceri/Micul Șmecher/Finanțare — oferte de preț pentru PoC 1.1.md (L14 ≈ €7k net EMC + radio)
  [E]      estimate, no quote yet
"""
import json, math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from facts import load  # noqa: E402

F = load(with_model=False)
SF = F["size_S"]["cost_factors_vs_M"]
P = F["pricing"]
VAT = P["vat_rate_assumed_for_model"]
FEE_PCT = P["platform_fee_pct"] + P["processing_fee_pct"]
FEE_FIX = P["processing_fee_fixed_eur"]
USD = 0.87  # [model] fx_usd_eur
SPARE_PCT = 0.02       # spares for warranty / DOA [E]
CONTINGENCY = 0.15     # on everything inside the goal [E]
FAILED_PCT = 0.03      # pledges never collected after 3 retries [E]
REFUND_PCT = 0.05      # refund reserve: backers may cancel for a full refund at any time before shipping (13-refunds.md) [E]
N_MIN = 150            # below this, CNC/anodise/EMS set-up makes no sense [E]
MARKETING = 17500      # pre-launch €9,500 + in-campaign ads cap €8,000 (PLAN.md §8) [E]; never in the goal


def li(points, n):
    """Log-log interpolation between (volume, value) anchors, like the factory model."""
    pts = sorted(points)
    if n <= pts[0][0]:
        return pts[0][1] * (pts[0][0] / n) ** 0.15   # mild penalty below the first anchor
    for (v0, y0), (v1, y1) in zip(pts, pts[1:]):
        if n <= v1:
            t = math.log(n / v0) / math.log(v1 / v0)
            return y0 * (y1 / y0) ** t
    return pts[-1][1]


def unit_cost(n, route="B", colours=3):
    """EUR net of VAT per finished S unit at a batch of n."""
    c = {}
    if route == "A":   # [s] own PCB @1000: panel $10 + WROOM $3.46 + parts $5 + PCB $0.8 = €16.76 + PCBA €4; @100 ≈ $31 parts + €8 PCBA [E]
        c["electronics: own PCB + WROOM module + bare AMOLED panel"] = li([(100, 35.0), (1000, 20.8), (5000, 17.0)], n)
        c["cell 603040, 750 mAh"] = li([(100, 2.6), (1000, 1.31), (5000, 1.1)], n)          # [s]
    else:              # [s] Waveshare AMOLED-1.75 list $29.99–41.99; volume price by RFQ [E]
        c["electronics: Waveshare ESP32-S3-Touch-AMOLED-1.75"] = li([(100, 34.0), (1000, 29.0), (5000, 26.0)], n)
        c["cell 503030 class, ~450 mAh"] = li([(100, 3.0), (1000, 1.9), (5000, 1.6)], n)            # [s]
    c["front glass Ø52 2.5D black print"] = li([(100, 8 * USD), (1000, 3 * USD), (5000, 1.9 * USD)], n) * SF["glass"]
    c["speaker"] = li([(100, 1.07), (1000, 0.8), (5000, 0.6)], n)
    imported = sum(c.values())
    c["freight + duty on imported parts"] = imported * (li([(100, 0.10), (1000, 0.06), (5000, 0.04)], n) + 0.02)
    cnc = li([(100, 85), (1000, 35), (5000, 27)], n) * SF["cnc"]
    blast = li([(100, 2), (1000, 1.5), (5000, 1.2)], n) * SF["anodise_blast"]
    anod = li([(100, 5), (1000, 4), (5000, 3.5)], n) * SF["anodise_blast"]
    lots = 100 * USD * colours * 2 / n   # $100 min per lot × colours × 2 lots
    c["shell: CNC 2 halves"] = cnc
    c["shell: blast + anodise + lot fees"] = blast + anod + lots
    c["shell: duty / transport (6 %)"] = (cnc + blast + anod) * 0.06
    c["chassis + foot (polymer)"] = li([(100, 6), (1000, 3.5), (5000, 1.5)], n) * SF["chassis"]
    c["OU egg (shell + charging board)"] = li([(100, 18), (1000, 12), (5000, 8)], n) * SF["ou"]
    c["packaging (rigid box, guide, label)"] = li([(100, 10), (1000, 5.5), (5000, 3.3)], n) * SF["packaging"]
    c["USB-C cable"] = li([(100, 2.2), (1000, 1.2), (5000, 0.9)], n)
    c["small mechanics"] = li([(100, 4), (1000, 2.5), (5000, 1.8)], n) * SF["mech"]
    c["laser mark (serial, CE, WEEE)"] = li([(100, 2), (1000, 1.2), (5000, 0.8)], n)
    c["box build at EMS (assembly, flash, test, pack)"] = li([(100, 15), (1000, 10), (5000, 8)], n)
    c["internal QC (5 min)"] = 5 / 60 * 7.24
    mat = sum(v for k, v in c.items() if not k.startswith(("box build", "internal QC")))
    c["scrap 3 %"] = mat * 0.03
    return c


def one_offs(route="B", colours=3):
    """(key, item, EUR net, source). Which ones sit inside the goal depends on the scenario."""
    return [
        ("ce_lab", "CE/RED lab: EN 300 328, EN 301 489-1/-17, EN IEC 62368-1, EN 62479, pre-scan, one re-test",
         9000 if route == "A" else 14000, "[compl] €5–12k + pre-scan €1–2k; [poc] L14 ≈ €7k net; route A reuses the module's radio evidence [E]"),
        ("en18031", "EN 18031-1/-2 (RED cybersecurity) assessment", 4500, "[compl] €0–9k"),
        ("tech_file", "Technical file, GPSR risk analysis, EU DoC, guide RO/EN, labels", 1500, "[compl]"),
        ("legal", "Compliance consultant; terms, refund policy, privacy notice, withdrawal button", 1700, "[compl]"),
        ("epr", "EPR: RO + 9 EU countries + UK (WEEE, batteries, packaging; authorised representative where required)", 12000, "[compl] €1–3k per country per year [E €1.1k avg]"),
        ("trademark", "EU trademark + registered design", 1300, "[compl]; SME Fund voucher may cover 75 %"),
        ("evt_dvt", "EVT/DVT: 2 rounds × 10 aluminium S units (CE samples, video, press loaners)", 3000, "[E] ~€150/unit at qty 10"),
        ("tooling", "CNC programming + first article, test jig (Fixturfab Dev Pro $1,799), glass print set-up", 4000, "[model] jig_dev_usd; rest [E]"),
        ("nre_pcb", "Custom PCB + glass/lamination NRE (route A only)", F["size_S"]["electronics_routes"][route]["nre_eur_estimate"], "[s] §1.2 [E]"),
        ("batch_setup", f"Golden samples ({colours} colours), anodise set-up, packaging samples", 1000 + 300 * colours, "[model] golden_eur 100/colour + [E]"),
        ("insurance", "Product liability insurance, year 1", 800, "[compl]"),
        ("fulfilment", "Fulfilment set-up: 3PL onboarding, UN3481 labels, lithium shipping documents", 700, "[E]"),
    ]


def ladder_prices(lad):
    L = P["ladders"][lad]
    return {"launch": L["launch"]["price_eur"], "campaign": L["campaign"]["price_eur"], "two": L["two"]["price_eur"],
            "supporter": P["supporter_eur"], "ou": P["ou_extra_eur"], "late": L["late_pledge_eur"], "retail": L["retail_planned_eur"]}, L


def mix(n, L):
    """Device count n -> pledges per reward [E]: launch tier sells out first, 6 % of devices in Two Souls packs."""
    out, left = {}, n
    two = min(L["two"]["cap"], round(0.06 * n / 2))
    out["two"] = (two, 2 * two); left -= 2 * two
    la = min(L["launch"]["cap"], max(left, 0))
    out["launch"] = (la, la); left -= la
    out["campaign"] = (max(left, 0), max(left, 0))
    backers = sum(p for p, _ in out.values())
    out["supporter"] = (round(0.05 * backers), 0)
    return out


def economics(n, scenario="after_ce", lad="A", route="B", colours=3, cost_mult=1.0, include_marketing=False):
    pr, L = ladder_prices(lad)
    m = mix(n, L)
    gross = sum(pr[k] * p for k, (p, _) in m.items())
    orders = sum(p for k, (p, _) in m.items())
    dev_orders = orders - m["supporter"][0]
    addon = 0.05 * dev_orders * pr["ou"]
    uc_lines = unit_cost(n, route, colours)
    uc = sum(uc_lines.values()) * cost_mult
    addon_cost = 0.05 * dev_orders * uc_lines["OU egg (shell + charging board)"] * cost_mult * 1.2
    gross += addon
    collected = gross * (1 - FAILED_PCT)
    vat = collected * VAT / (1 + VAT)
    fees = collected * FEE_PCT + FEE_FIX * orders
    refund = (collected - vat) * REFUND_PCT
    net = collected - vat - fees - refund
    variable = n * uc * (1 + SPARE_PCT) + addon_cost
    oo = one_offs(route, colours)
    in_goal_keys = set(F["campaign"]["scenarios"][scenario]["one_offs_in_goal"])
    fixed_in = sum(v for k, _, v, _ in oo if k in in_goal_keys)
    fixed_before = sum(v for k, _, v, _ in oo if k not in in_goal_keys)
    contingency = (variable + fixed_in) * CONTINGENCY
    mkt = MARKETING if include_marketing else 0
    total = variable + fixed_in + contingency + mkt
    return dict(n=n, gross=gross, collected=collected, vat=vat, fees=fees, net=net, uc=uc, variable=variable,
                fixed_in=fixed_in, fixed_before=fixed_before, contingency=contingency, mkt=mkt, total=total,
                failed=gross - collected, refund=refund, margin=net - total, orders=orders, dev_orders=dev_orders, mix=m,
                avg_pledge=gross / max(orders, 1), avg_device=gross / n)


def min_batch(**kw):
    for n in range(N_MIN, 8000, 10):
        e = economics(n, **kw)
        if e["margin"] >= 0:
            return e
    return None


def round_goal(x, step=5000):
    return int(math.ceil(x / step) * step)


def eur(x):
    return f"€{x:,.0f}"


def contribution(price, units, n, route, colours):
    net = price / (1 + VAT) - (price * FEE_PCT + FEE_FIX)
    return net / units - sum(unit_cost(n, route, colours).values())


def main(quiet=False):
    C = F["campaign"]
    scn, lad = C["scenario"], C["ladder"]
    route = F["decisions"]["D8"]["kit_default"]
    colours = len(F["product"]["colours_launch"]["value"])
    base = min_batch(scenario=scn, lad=lad, route=route, colours=colours)
    goal = round_goal(base["gross"])
    rules = C["list_rules"]
    day1 = goal * rules["day1_share_of_goal"]
    list_needed = day1 / base["avg_pledge"] / rules["day1_list_conversion"]
    stretch = [dict(s, at_eur=round_goal(goal * s["factor"])) for s in C["stretch_goals"]]
    # the published goal, line by line (shares of the rounded goal)
    vat_label = "VAT we expect to owe on the pledges (paid from the money raised, never added to your price)" if not P["vat_registered"] else "VAT included in the prices"
    lines = [
        ("make", "Making every SOUL", f"parts, aluminium shells in {colours} colours, OU eggs, assembly, testing, packaging, {int(SPARE_PCT*100)} % spares", base["variable"]),
        ("setup", "Batch set-up", "golden samples per colour, anodise set-up, product insurance, fulfilment set-up", base["fixed_in"]),
        ("cont", "Contingency", "15 % on every cost until supplier quotes are in writing, plus the rest up to a round goal", base["contingency"]),
        ("vat", "VAT", vat_label, base["vat"]),
        ("fees", "Indiegogo and payment fees", "5 % platform + 3 % + €0.20 per payment", base["fees"]),
        ("fail", "Pledges that fail to collect", "about 3 %, after three retries", base["failed"]),
        ("refund", "Refund reserve (5 %)", "so anyone who cancels before shipping gets a full refund", base["refund"]),
    ]
    # rounding up to a round goal is not a separate line: it is merged into the contingency (review 2026-10-22)
    lines[2] = (lines[2][0], lines[2][1], lines[2][2], lines[2][3] + goal - sum(l[3] for l in lines))
    grid = []
    for s in ("after_ce", "before_ce"):
        for L in ("A", "B"):
            for r in ("A", "B"):
                e = min_batch(scenario=s, lad=L, route=r, colours=colours)
                grid.append({"scenario": s, "ladder": L, "route": r, "devices": e["n"], "goal_eur": round_goal(e["gross"]),
                             "unit_cost": round(e["uc"], 2), "before_campaign_eur": round(e["fixed_before"]),
                             "list_needed": int(round(round_goal(e["gross"]) * rules["day1_share_of_goal"] / e["avg_pledge"] / rules["day1_list_conversion"], -2))})
    sens = []
    for label, kw in [("unit costs +15 %", {"cost_mult": 1.15}), ("unit costs −15 %", {"cost_mult": 0.85}),
                      ("5 colours instead of 3", {"colours": 5}), ("marketing recovered inside the goal", {"include_marketing": True})]:
        k = dict(scenario=scn, lad=lad, route=route, colours=colours); k.update(kw)
        e = min_batch(**k)
        sens.append({"case": label, "devices": e["n"], "goal_eur": round_goal(e["gross"])})
    pr, L = ladder_prices(lad)
    contrib = {k: round(contribution(pr[k], 2 if k == "two" else 1, base["n"], route, colours), 2)
               for k in ("launch", "campaign", "two", "late")}
    oo = one_offs(route, colours)
    ing = set(C["scenarios"][scn]["one_offs_in_goal"])
    out = {
        "_note": "generated by tools/goal_model.py; do not edit",
        "scenario": scn, "ladder": lad, "route": route, "colours": colours,
        "goal_eur": goal, "devices": base["n"], "pledges": base["orders"], "device_pledges": base["dev_orders"],
        "unit_cost_eur": round(base["uc"], 2), "avg_pledge_eur": round(base["avg_pledge"], 2), "avg_device_eur": round(base["avg_device"], 2),
        "day1_eur": round(day1), "day1_pledges": int(round(day1 / base["avg_pledge"])), "list_needed": int(round(list_needed, -2)),
        "list_minimum": int(round(list_needed * 0.75, -2)),
        "budget_lines": [{"k": k, "label": a, "note": b, "eur": round(v), "pct": v / goal} for k, a, b, v in lines],
        "one_offs_in_goal": [{"item": i, "eur": v} for k, i, v, _ in oo if k in ing and v],
        "one_offs_before_campaign": [{"item": i, "eur": v, "source": s} for k, i, v, s in oo if k not in ing and v],
        "before_campaign_total_eur": round(base["fixed_before"]), "marketing_eur": MARKETING,
        "cash_before_first_payout_eur": round(base["fixed_before"] + MARKETING),
        "contribution_per_device_eur": contrib, "stretch_goals": stretch, "grid": grid, "sensitivity": sens,
        "unit_cost_lines": {k: round(v, 2) for k, v in unit_cost(base["n"], route, colours).items()},
        "realistic_range_eur": C["realistic_range_note"]["eur"],
    }
    json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "goal_model.out.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if quiet:
        print(f"goal {eur(goal)} · {base['n']} devices · scenario {scn} · ladder {lad} · route {route} · list needed {out['list_needed']:,}")
        return out
    print(f"## Active: scenario {scn}, ladder {lad}, route {route}, {colours} colours\n")
    print(f"Honest minimum: {base['n']} devices, {base['orders']} pledges, gross {eur(base['gross'])} → goal {eur(goal)}")
    print(f"Unit cost {eur(base['uc'])}; avg pledge {eur(base['avg_pledge'])}; day 1 (30 %) {eur(day1)} ≈ {out['day1_pledges']} pledges → confirmed list ≈ {out['list_needed']:,}")
    print(f"Paid before the campaign (not in the goal): {eur(base['fixed_before'])} + marketing {eur(MARKETING)}")
    print("\n| line | € | share |\n|---|---|---|")
    for l in out["budget_lines"]:
        print(f"| {l['label']} | {eur(l['eur'])} | {l['pct']*100:.0f} % |")
    print("\n## Unit cost at the goal batch\n")
    for k, v in out["unit_cost_lines"].items():
        print(f"| {k} | {v:.2f} |")
    print("\n## One-time costs\n")
    for k, i, v, s in oo:
        if v:
            print(f"| {i} | {eur(v)} | {'IN GOAL' if k in ing else 'before campaign'} | {s} |")
    print("\n## Grid: scenario × ladder × route\n\n| scenario | ladder | route | devices | goal | unit € | before campaign | list needed |\n|---|---|---|---|---|---|---|---|")
    for g in grid:
        print(f"| {g['scenario']} | {g['ladder']} | {g['route']} | {g['devices']} | {eur(g['goal_eur'])} | {g['unit_cost']} | {eur(g['before_campaign_eur'])} | {g['list_needed']:,} |")
    print("\n## Sensitivity (active scenario)\n")
    for s in sens:
        print(f"| {s['case']} | {s['devices']} | {eur(s['goal_eur'])} |")
    print("\nContribution per device after unit cost at the goal batch:", contrib)
    print("Stretch goals:", [(s["id"], s["at_eur"]) for s in stretch])
    return out


if __name__ == "__main__":
    main(quiet="--quiet" in sys.argv)
