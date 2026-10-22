#!/usr/bin/env python3
"""Check the campaign copy against facts.json (+ docs/size-s.json + the goal model) and the campaign rules.

    python3 -I micul-smecher/crowdfunding/tools/check_copy.py            # report
    python3 -I micul-smecher/crowdfunding/tools/check_copy.py --strict   # also fail on open placeholders (use before posting)
    python3 -I micul-smecher/crowdfunding/tools/check_copy.py -v         # list every open placeholder

Errors (exit 1):
  - banned claims: CE-certified, AI included, invented press, M-scale renders, Founders edition, rarity as a prize,
    'made in Romania', 'incl. VAT' while not VAT-registered, '% off' the planned retail price, 'no two alike',
    'hold the glass and talk to Claude' before product.voice.claude_only_voice_works, dropped rewards (Early Bird, Spectrum)
  - an M size on a line that doesn't say it's the M prototype
  - a size pair, euro amount, thickness, weight or month that isn't in facts.json / the goal model
  - false urgency: a 48-hour / last-day line whose price isn't the campaign, Two Souls or Late Pledge price
  - an f-block that is unfilled or unknown; an {{img:…}} that 00-image-map.md doesn't map to a file
  - perks.csv prices or caps that disagree with facts.json
Warnings (errors with --strict): open placeholders ({{AGE}}, [[G…]]/[[D8…]], [de completat…], {{URL:…}}).
"""
import csv, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from facts import load, MONTHS_EN, MONTHS_RO  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CAMPAIGN = ROOT / "campaign"
F = load()
STRICT = "--strict" in sys.argv
S, C, P, L, SCN, M = F["size_S"], F["campaign"], F["pricing"], F["lad"], F["scn"], F.get("model", {})
NEG = re.compile(r"\b(not|never|no|don't|doesn't|isn't|won't|nu|niciodată|fără|until|before|only after|banned|interzis|nu e|nu are|n-are|încă|yet|never write|doar după|doar dacă|doar cu|only with|gone|dropped|a dispărut)\b|n't|n-", re.I)

BANNED = [
    (r"CE[- ]certified|CE-certificat|certificat CE|certificare CE|marcaj CE|UKCA|FCC[- ]certified", "CE/FCC/UKCA claim without a negation"),
    (r"includes? AI|AI included|built-in AI|AI inside|with (Claude|ChatGPT) inside|powered by (Claude|ChatGPT|AI)|AI[- ]powered|ChatGPT[- ]powered|Claude[- ]powered|include AI|inclus AI|AI inclus", "AI-included claim without a negation"),
    (r"as seen in|featured in|apărut în|press coverage", "press claim"),
    (r"soul_v9_hand|soul_v9_desk", "M-scale hand/desk render"),
    (r"Founders? edition|ediți[ae] Founders", "Founders edition"),
    (r"chance to win|win a (Mythic|Legendary|Rare)|câștigi un", "rarity marketed as a prize"),
    (r"made in Romania|fabricat în România", "'made in Romania' (only 'designed in Romania' until partners are confirmed)"),
    (r"\b(The )?Spectrum\b|Early Bird", "a reward that no longer exists (Early Bird, The Spectrum)"),
]
if not P["vat_registered"]:
    BANNED.append((r"incl(\.|uding|udes)? VAT|VAT[- ]inclusive|VAT included|cu TVA inclus|TVA inclus|includ TVA", "'VAT included' while ARTEMIS is not VAT-registered (pricing.vat_registered)"))
NO_NEG_EXEMPT = [
    (r"no two (are )?(quite )?alike|never look quite the same|nu există doi la fel|niciodată nu arată la fel", "'no two alike' is false (about 1 in 112 pairs repeat)"),
    (r"[−-]\s?\d+\s?% off|\d+\s?% off €|% din €\d+|reducere de \d+ ?%", "'% off' the planned retail price (never sold at that price: Omnibus rule)"),
]
if not F["product"]["voice"]["claude_only_voice_works"]:
    NO_NEG_EXEMPT.append((r"(hold|holding) the glass[^.]{0,40}(talk|ask)[^.]{0,30}Claude|(talk|speak) to (your own )?Claude|ask your own Claude|vorbești cu Claude|îl întrebi pe Claude", "voice with Claude only is not working yet (product.voice.claude_only_voice_works = false)"))
HARD_BANNED = [
    (r"\bPoC\b|\bgrant(ul|uri|ului)?\b|\bsubvenți", "a grant named as a source of money (PoC 1.1 is not awarded and never pays for anything claimed here; review 2026-10-22)"),
    (r"ChatGPT (account|subscription)|(Claude|ChatGPT) or ChatGPT account|cont(ul)? (de )?ChatGPT|abonament(ul)? ChatGPT", "a ChatGPT account doesn't work: only the owner's own OpenAI API key (in development)"),
    (r"\bat cost\b|estimated rates|per parcel \(estimates\)|Estimates; the prices|la cost\b|tarifele estimate|\(estimări\)", "shipping must be the fixed published rates (CRD art. 6(1)(e)), never 'estimates' or 'at cost'"),
    (r"\b\d{3,4}\s?mAh\b", "battery capacity figure (capacity is still variable)"),
    (r"\b\d+\s*(hours|days|ore|zile) of battery|battery lasts? \d|autonomie de \d", "battery-life figure (not measured yet)"),
]
if C["scenario"] == "after_ce":
    # the live page exists only after the EU DoC: never mix "not CE-certified yet" with "this campaign opens" (review 2026-10-22)
    HARD_BANNED.append((r"opens only after it passes|se deschide abia după ce trece|Not yet\. It has Wi-Fi|Încă nu\. Are Wi-Fi", "pre-CE wording on a page that only exists after CE (use f:ce_short / f:ce_now)"))
PRE_CE_FILES = {"07-prelaunch-emails.md"}   # sent before the DoC: the only place 'not CE-certified yet' may appear in scenario after_ce
M_SIZE = re.compile(r"90 × 101|2[.,]8\s?(″|\"|inch|in\b)|480 × 480")
M_CONTEXT = re.compile(r"\bM\b|prototype|prototip|larger|mai mare|bigger|web|simulator|480 × 480; on S|Captured at|Capturat la", re.I)
PAIR = re.compile(r"(\d+(?:[.,]\d+)?)\s?×\s?(\d+(?:[.,]\d+)?)")
ALLOWED_PAIRS = {(S["width_mm"], S["height_mm"]), tuple(F["prototype_M"]["dims_mm"][:2]), tuple(S["screen"]["resolution_px"]),
                 tuple(F["prototype_M"]["screen"]["resolution_px"]), tuple(F["size_graphics"]["reference_objects_mm"]["credit_card_ID-1"]),
                 (85.6, 54), (700, 700), (1743, 498), (1200, 630), (1200, 900), (1080, 1080), (140, 140)}
ALLOWED_PAIRS = {tuple(map(float, x)) for x in ALLOWED_PAIRS}


def num(x):
    return float(x.replace(",", "."))


def money_set():
    v = {M.get("goal_eur"), P["supporter_eur"], P["ou_extra_eur"], M.get("before_campaign_total_eur"), 2, 1, 0.2}
    for lad in P["ladders"].values():
        v |= {lad["retail_planned_eur"], lad["launch"]["price_eur"], lad["campaign"]["price_eur"], lad["two"]["price_eur"], lad["two"]["price_eur"] / 2, lad["late_pledge_eur"]}
    for k, x in C["shipping_eur"].items():
        if isinstance(x, (int, float)):
            v.add(x)
    for s in M.get("stretch_goals", []):
        v |= {s["at_eur"], s["at_eur"] // 1000}
    for r in C["realistic_range_note"]["eur"]:
        v |= {r, r // 1000}
    return {x for x in v if x is not None}


MONEY = re.compile(r"€\s?(\d{1,3}(?:[.,]\d{3})+|\d+(?:[.,]\d{1,2})?)(k)?")


def parse_money(m):
    raw, k = m.group(1), m.group(2)
    v = float(re.sub(r"[.,]", "", raw)) if re.fullmatch(r"\d{1,3}(?:[.,]\d{3})+", raw) else num(raw)
    return v * 1000 if k else v


def allowed_months():
    out = set()
    sc = C["scenarios"][C["scenario"]]
    vals = [sc["launch"], sc["end"], sc["late_pledge_open"], sc["reward_delivery_field"], *sc["estimated_delivery"].values()]
    for a, b, *_ in sc["timeline"]:
        vals += [a] + ([b] if b else [])
    for d, *_ in sc["before_launch"]:
        vals.append(d)
    for g in F["gates"].values():
        if isinstance(g, dict):
            vals += [x for x in (g.get("target"), g.get("date")) if x]
    import datetime as dt
    for x in vals:
        y, m = int(x[:4]), int(x[5:7])
        # every month between consecutive dates in a range is fine (e.g. "October – November 2027")
        out.add((y, m))
    sc_months = sorted(out)
    lo, hi = min(sc_months[0], (2026, 10)), sc_months[-1]   # from today (drafting) to the last promise
    full = set()
    y, m = lo
    while (y, m) <= hi:
        full.add((y, m))
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return full


MONTH_RX = re.compile(r"\b(" + "|".join(MONTHS_EN + [x[:3] for x in MONTHS_EN] + MONTHS_RO) + r")\.? (20\d\d)\b", re.I)
ALLOWED_MONTHS = allowed_months()
URGENCY = re.compile(r"48 (hours|h\b|de ore)|last day|ultima zi|closes tonight|se închide în seara", re.I)
URGENT_OK = {L["campaign"]["price_eur"], L["two"]["price_eur"], L["two"]["price_eur"] / 2, L["late_pledge_eur"], L["launch"]["price_eur"]}

errors, warns = [], []
ALLOWED_MONEY = money_set()
image_map = (CAMPAIGN / "00-image-map.md").read_text(encoding="utf-8")
defined = dict(re.findall(r"^\| `\{\{((?:img|video):[a-z0-9-]+)\}\}` \| ([^|]+) \|", image_map, re.M))
PLACEHOLDERS = [
    (r"\{\{AGE\}\}", "{{AGE}} (decision D4)"),
    (r"\[\[[A-Z][A-Z0-9_/]*:[^\]]*\]\]", "[[G…/D…]] gate or decision text"),
    (r"\[de completat[^\]]*\]", "[de completat]"),
    (r"\{\{URL:[a-z0-9-]+\}\}", "{{URL:…}}"),
]
SKIP_RULE_FILES = {"00-README.md", "00-image-map.md", "README.md"}
BLOCK = re.compile(r"<!--f:([a-z0-9_]+)-->(.*?)<!--/f-->", re.S)
sys.path.insert(0, str(Path(__file__).resolve().parent))

files = sorted(p for p in CAMPAIGN.rglob("*") if p.suffix in {".md", ".txt"})
for p in files:
    rel = p.relative_to(CAMPAIGN)
    text = p.read_text(encoding="utf-8")
    rule_file = p.name in SKIP_RULE_FILES
    for m in BLOCK.finditer(text):
        if m.group(2).strip() in ("", "x"):
            errors.append(f"{rel}: f-block '{m.group(1)}' is not filled (run tools/build_copy.py)")
    if text.count("<!--f:") != text.count("<!--/f-->"):
        errors.append(f"{rel}: unbalanced f-blocks")
    in_internal = False
    for i, line in enumerate(text.splitlines(), 1):
        where = f"{rel}:{i}"
        if line.startswith("## "):
            in_internal = "internal" in line.lower() or "intern" in line.lower()
        if rule_file:
            continue
        for rx, why in BANNED:
            if re.search(rx, line, re.I) and not NEG.search(line) and "?" not in line and not in_internal:
                errors.append(f"{where}: {why}: {line.strip()[:120]}")
        for rx, why in NO_NEG_EXEMPT:
            if re.search(rx, line, re.I) and not re.search(r"\bnever (show|write)|niciodată (nu )?(apare|scriem)|nu apare niciodată|„−x %”|\"% off\" badge|never a \"% off\"", line, re.I):
                errors.append(f"{where}: {why}: {line.strip()[:120]}")
        if C["scenario"] == "after_ce" and p.name not in PRE_CE_FILES and re.search(r"not CE-certified yet|fără certificare CE încă|Nu are încă certificare CE", line, re.I) and not in_internal:
            errors.append(f"{where}: 'not CE-certified yet' on a live-campaign text (scenario after_ce): {line.strip()[:100]}")
        for rx, why in HARD_BANNED:
            if re.search(rx, line, re.I):
                errors.append(f"{where}: {why}: {line.strip()[:120]}")
        if M_SIZE.search(line) and not M_CONTEXT.search(line):
            errors.append(f"{where}: M size without M/prototype context: {line.strip()[:120]}")
        for a, b in PAIR.findall(line):
            if (num(a), num(b)) not in ALLOWED_PAIRS:
                errors.append(f"{where}: size pair {a} × {b} not in facts.json")
        for m in MONEY.finditer(line):
            v = parse_money(m)
            if v not in ALLOWED_MONEY and not re.search(r"\| [\d,.]+ \||cost|budget|buget|LIVE|contribution|unit cost", line, re.I):
                errors.append(f"{where}: euro amount {m.group(0)} not in facts.json / goal model")
        if URGENCY.search(line):
            for m in MONEY.finditer(line):
                if parse_money(m) not in URGENT_OK and "LIVE" not in line:
                    errors.append(f"{where}: urgency line with a price that isn't the campaign / Late Pledge price: {line.strip()[:100]}")
        for m in re.finditer(r"(\d{2})–(\d{2}) mm", line):
            if (int(m.group(1)), int(m.group(2))) != (S["thickness_mm"]["min"], S["thickness_mm"]["max"]):
                errors.append(f"{where}: thickness {m.group(0)} ≠ facts.json")
        for m in re.finditer(r"(\d{2,3})–(\d{2,3}) g\b", line):
            if (int(m.group(1)), int(m.group(2))) != (S["weight_g"]["min"], S["weight_g"]["max"]):
                errors.append(f"{where}: weight {m.group(0)} ≠ facts.json")
        for m in MONTH_RX.finditer(line):
            name, y = m.group(1).lower(), int(m.group(2))
            idx = next((k for k, x in enumerate(MONTHS_EN) if x.lower().startswith(name[:3])), None)
            if idx is None:
                idx = next(k for k, x in enumerate(MONTHS_RO) if x == name)
            if (y, idx + 1) not in ALLOWED_MONTHS:
                errors.append(f"{where}: month '{m.group(0)}' is outside the active scenario's dates")
        for m in re.finditer(r"\{\{((?:img|video):[a-z0-9-]+)\}\}", line):
            if m.group(1) not in defined:
                errors.append(f"{where}: {{{{{m.group(1)}}}}} is not mapped to a file in 00-image-map.md")
        for rx, name in PLACEHOLDERS:
            for m in re.finditer(rx, line):
                warns.append((name, f"{where}: {m.group(0)[:80]}"))

# perks.csv vs facts
perks = CAMPAIGN / "perks.csv"
want = {"supporter": P["supporter_eur"], "first_light": L["launch"]["price_eur"], "campaign": L["campaign"]["price_eur"], "campaign_b2": L.get("campaign_b2", {}).get("price_eur", L["campaign"]["price_eur"]),
        "two_souls": L["two"]["price_eur"], "ou_extra": P["ou_extra_eur"], "late_pledge": L["late_pledge_eur"]}
caps = {"first_light": L["launch"]["cap"], "two_souls": L["two"]["cap"], "campaign": L["campaign"].get("cap") or ""}
if not perks.exists():
    errors.append("perks.csv missing (run tools/build_copy.py)")
else:
    with perks.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["id"] in want and float(row["price_eur"]) != float(want[row["id"]]):
                errors.append(f"perks.csv: {row['id']} price {row['price_eur']} ≠ facts.json {want[row['id']]}")
            if row["id"] in caps and str(caps[row["id"]]) != row["cap"]:
                errors.append(f"perks.csv: {row['id']} cap {row['cap']!r} ≠ facts.json {caps[row['id']]!r}")
            if re.search(r"ChatGPT account|[Ee]stimates\.|at cost", row["description"] + row["shipping"]):
                errors.append(f"perks.csv: {row['id']} has a banned shipping/AI wording")
            if row["ships_to"] != "worldwide" and set(row["ships_to"].split(", ")) != set(C["shipping_countries_campaign_1"]):
                errors.append(f"perks.csv: {row['id']} ships_to differs from facts.json shipping_countries_campaign_1")
            if re.search(r"% off|−\d+ ?%", row["description"]):
                errors.append(f"perks.csv: {row['id']} shows a percentage off")
            if row["image"] and not (ROOT / "images" / row["image"]).exists():
                errors.append(f"perks.csv: {row['id']} image {row['image']} not found in images/")
for key, fn in defined.items():
    fn = fn.strip().strip("`")
    if re.fullmatch(r"[\w.-]+\.(png|jpg|mp4|gif)", fn) and not (ROOT / "images" / fn).exists():
        errors.append(f"00-image-map.md: {key} → images/{fn} does not exist")

print(f"checked {len(files)} files in {CAMPAIGN} (scenario {C['scenario']}, ladder {C['ladder']}, goal €{M.get('goal_eur'):,})")
for e in errors:
    print("ERROR ", e)
counts = {}
for key, _ in warns:
    counts[key] = counts.get(key, 0) + 1
if warns:
    print("\nopen placeholders (must be closed before publishing):")
    for k, v in sorted(counts.items()):
        print(f"  {v:4d} × {k}")
    if "-v" in sys.argv:
        for _, w in warns:
            print("  ", w)
if not F["decisions"]["D1"]["decided"]:
    print("\nBLOCKED: decision D1 is not written in Jurnal decizii (facts.json decisions.D1.decided = false).")
    warns.append(("D1", "decision D1"))
fail = bool(errors) or (STRICT and bool(warns))
print(f"\n{len(errors)} errors, {len(warns)} open placeholders -> {'FAIL' if fail else 'OK'}")
sys.exit(1 if fail else 0)
