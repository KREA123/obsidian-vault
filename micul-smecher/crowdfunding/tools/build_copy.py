#!/usr/bin/env python3
"""Fill every fact-driven block in the campaign copy from facts.json + the goal model, then export the paste files.

    python3 -I micul-smecher/crowdfunding/tools/build_copy.py

1. In every campaign/**/*.md, the text between <!--f:KEY--> and <!--/f--> is replaced by BLOCKS[KEY] (EN or RO,
   by folder). Blocks can be inline (a price in a sentence) or whole tables. Never edit inside a block by hand:
   change facts.json, re-run tools/goal_model.py, then this.
2. Writes campaign/perks.csv (what goes into Indiegogo's reward form; no internal columns).
3. Writes campaign/story-paste.html: the Story, Specs, Budget & timeline, Team, Risks, Refunds and FAQ sections,
   ready to copy into Indiegogo's editor (a "Copy" button per section; image slots are marked [IMAGE: file]).
"""
import csv, html, io, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from facts import load, month, day, eur, CF  # noqa: E402

F = load()
if "model" not in F:
    raise SystemExit("run tools/goal_model.py first")
M, L, SCN, C, G, P, S = F["model"], F["lad"], F["scn"], F["campaign"], F["gates"], F["pricing"], F["size_S"]
CAMP = os.path.join(CF, "campaign")
NUM_RO = {2: "două", 3: "trei", 4: "patru", 5: "cinci"}
NUM_EN = {2: "two", 3: "three", 4: "four", 5: "five"}
COL_RO = {"Silver": "Argint", "Graphite": "Grafit", "Midnight": "Albastru noapte", "Ember": "Jar", "Champagne": "Șampanie"}


def e(v, lang):
    return eur(v, lang)


def join_list(xs, lang):
    if len(xs) == 1:
        return xs[0]
    return ", ".join(xs[:-1]) + (" și " if lang == "ro" else " and ") + xs[-1]


def colours(lang, which="launch"):
    xs = F["colours"] if which == "launch" else F["product"]["colours_launch"]["later"]
    if lang == "ro":
        xs = [f"{COL_RO[x]}" for x in xs]
    return join_list(xs, lang)


def ce_passed():
    return bool(G["CE"]["passed"])


def gate_line(k, lang):
    g = G[k]
    if g.get("passed"):
        when = day(g["date"], lang) if g.get("date") else ""
        return ("✓ " if lang == "en" else "✓ ") + (when + ": " if when else "")
    return None


# ------------------------------------------------------------------------------------------------ blocks
def b_goal(lang): return e(M["goal_eur"], lang)
def b_devices(lang): return f"{M['devices']:,}".replace(",", "." if lang == "ro" else ",")
def b_launch_price(lang): return e(L["launch"]["price_eur"], lang)
def b_launch_cap(lang): return str(L["launch"]["cap"])
def b_campaign_price(lang): return e(L["campaign"]["price_eur"], lang)
def b_two_price(lang): return e(L["two"]["price_eur"], lang)
def b_two_each(lang): return e(L["two"]["price_eur"] / 2, lang)
def b_two_cap(lang): return str(L["two"]["cap"])
def b_retail(lang): return e(L["retail_planned_eur"], lang)
def b_late_price(lang): return e(L["late_pledge_eur"], lang)
def b_supporter(lang): return e(P["supporter_eur"], lang)
def b_ou_extra(lang): return e(P["ou_extra_eur"], lang)
def b_days(lang): return str(C["length_days"])
def b_campaign_dates(lang):
    a, b = SCN["launch"], SCN["end"]
    da, db = day(a, lang), day(b, lang)
    ya = da.rsplit(" ", 1)
    return f"{ya[0]} – {db}" if da[-4:] == db[-4:] else f"{da} – {db}"
def b_launch_day(lang): return day(SCN["launch"], lang, weekday=True)
def b_end_day(lang): return day(SCN["end"], lang, weekday=True)
def b_late_open(lang): return day(SCN["late_pledge_open"], lang)
def b_delivery(lang):
    d = SCN["estimated_delivery"]
    return f"{month(d['EU'], lang)} ({'UE' if lang == 'ro' else 'EU'})"


def b_delivery_eu(lang): return month(SCN["estimated_delivery"]["EU"], lang)
def b_delivery_uk(lang):
    return b_delivery(lang)


def b_batch2(lang): return month(SCN["estimated_delivery"]["late_pledge_batch_2"], lang)
def b_colours(lang): return colours(lang)
def b_colours_n(lang): return (NUM_RO if lang == "ro" else NUM_EN)[len(F["colours"])]
def b_colours_later(lang): return colours(lang, "later")
def b_list_needed(lang): return f"{M['list_needed']:,}".replace(",", "." if lang == "ro" else ",")
def b_weight(lang): return f"~{S['weight_g']['min']}–{S['weight_g']['max']} g"
def b_depth(lang): return f"{S['thickness_mm']['min']}–{S['thickness_mm']['max']} mm"


def b_status_bar(lang):
    st = ce_state()
    if st in ("passed", "live"):
        if lang == "ro":
            return f"**Lotul se face după campanie · declarația UE de conformitate semnată ({ce_date(lang)}) · imaginile marcate „Render (CGI)” nu sunt fotografii.** Citește *Riscuri și provocări* înainte să susții."
        return f"**Batch made after the campaign · EU Declaration of Conformity signed ({ce_date(lang)}) · images labelled \"Render (CGI)\" are not photos.** Read *Risks and challenges* before you back."
    if lang == "ro":
        return "**În dezvoltare · fără certificare CE încă: pleacă doar după ce trece testele · imaginile marcate „Render (CGI)” nu sunt fotografii.** Citește *Riscuri și provocări* înainte să susții."
    return "**In development · not CE-certified yet: ships only after it passes · images labelled \"Render (CGI)\" are not photos.** Read *Risks and challenges* before you back."


def b_ce_short(lang):
    """For the live page and anything sent after launch: one state only."""
    if ce_state() in ("passed", "live"):
        if lang == "ro":
            return f"A trecut testele radio, EMC, de siguranță și EN 18031 la {ce_lab(lang)}; declarația UE de conformitate e semnată ({ce_date(lang)})."
        return f"Radio, EMC, safety and EN 18031 tests passed at {ce_lab(lang)}; EU Declaration of Conformity signed ({ce_date(lang)})."
    return ("Nu are încă certificare CE: pleacă doar după ce trece testele." if lang == "ro" else "Not CE-certified yet: ships only after it passes.")


def b_ce_faq(lang):
    if ce_state() in ("passed", "live"):
        if lang == "ro":
            return f"Da. SOUL a trecut testele radio, EMC, de siguranță și de securitate cibernetică (EN 18031) la {ce_lab(lang)}, iar declarația UE de conformitate e semnată din {ce_date(lang)}."
        return f"Yes. SOUL passed radio, EMC, safety and cybersecurity (EN 18031) tests at {ce_lab(lang)}, and the EU Declaration of Conformity was signed on {ce_date(lang)}."
    if lang == "ro":
        return "Încă nu. Are Wi-Fi și Bluetooth, deci trebuie să treacă testele radio, EMC, de siguranță și EN 18031 într-un laborator acreditat. Testele sunt imediat după campanie și nimic nu pleacă înainte de declarația UE de conformitate semnată."
    return "Not yet. It has Wi-Fi and Bluetooth, so it must pass radio, EMC, safety and cybersecurity (EN 18031) tests at an accredited lab. Testing is right after the campaign, and nothing ships before the EU Declaration of Conformity is signed."


def b_ce_risk(lang):
    route = F["decisions"]["D8"]["kit_default"]
    full = S["electronics_routes"][route]["radio_testing"].startswith("full")
    if ce_state() in ("passed", "live"):
        lab, dt = ce_lab(lang), ce_date(lang)
        if lang == "ro":
            return f"SOUL a trecut testele radio, EMC, de siguranță electrică și EN 18031 la {lab}; declarația UE de conformitate e semnată din {dt}. Ce rămâne: fiecare unitate din lot e testată la final (semnal radio, încărcare, ecran) și orice schimbare de componentă se re-evaluează înainte să plece."
        return f"SOUL passed radio, EMC, electrical safety and EN 18031 tests at {lab}; the EU Declaration of Conformity was signed on {dt}. What remains: every unit in the batch is tested at the end of the line (radio signal, charging, screen), and any component change is re-assessed before it ships."
    radio_ro = "Placa folosește un cip ESP32-S3 fără modul radio pre-certificat, deci are nevoie de testare radio completă" if full else "Placa folosește un modul ESP32-S3-WROOM-1 cu dovezi radio de la Espressif, dar EMC, siguranța și EN 18031 se testează complet"
    radio_en = "The board uses an ESP32-S3 chip that isn't a pre-certified radio module, so it needs full radio testing" if full else "The board uses an ESP32-S3-WROOM-1 module with Espressif's radio evidence, but EMC, safety and EN 18031 are still tested in full"
    if lang == "ro":
        return (f"SOUL are Wi-Fi și Bluetooth, deci înainte să-l primească cineva trebuie să treacă testele radio, EMC, de siguranță electrică și EN 18031 într-un laborator acreditat. {radio_ro}, iar un corp din aluminiu poate slăbi semnalul. "
                "Ce facem: o pre-scanare la laborator, o variantă de rezervă pentru antenă și o retestare în buget. Nimic nu pleacă înainte de declarația UE de conformitate.")
    return (f"SOUL has Wi-Fi and Bluetooth, so before anyone can receive one it must pass radio, EMC, electrical safety and EN 18031 tests at an accredited lab. {radio_en}, and an aluminium body can weaken the radio signal. "
            "What we do: a lab pre-scan, a fallback antenna design and one re-test in the budget. Nothing ships before the EU Declaration of Conformity is signed.")


def b_vat_note(lang):
    if P["vat_registered"]:
        return ("Prețurile sunt finale și includ TVA." if lang == "ro" else "Prices are final and include VAT.")
    if lang == "ro":
        return ("Prețurile sunt finale: plătești exact suma afișată, plus tariful fix de transport pentru țara ta. ARTEMIS nu e plătitoare de TVA azi. "
                "Ne așteptăm să datorăm TVA pe aceste susțineri (vânzări către alte țări UE și, în funcție de suma strânsă, pragul din România). Dacă îl datorăm, îl plătim din banii strânși; nu se adaugă niciodată la prețul tău.")
    return ("Prices are final: you pay exactly the amount shown, plus the fixed shipping rate for your country. ARTEMIS isn't VAT-registered today. "
            "We expect to owe VAT on these pledges (sales to other EU countries and, depending on the total raised, Romania's threshold). If we do, it's paid out of the money raised and never added to your price.")


def b_budget_table(lang):
    ro = lang == "ro"
    names_ro = {"make": "Fabricarea fiecărui SOUL", "setup": "Pregătirea lotului", "cont": "Rezervă pentru neprevăzute", "vat": "TVA pe care ne așteptăm să-l datorăm",
                "fees": "Comisioanele Indiegogo și de plată", "fail": "Susțineri care nu se încasează", "refund": "Rezervă pentru rambursări (5 %)"}
    notes_ro = {"make": f"piese, carcase din aluminiu în {b_colours_n('ro')} culori, ouăle OU, asamblare, testare, ambalare, 2 % rezerve",
                "setup": "mostre de referință pe culoare, pregătirea anodizării, asigurarea produsului, pregătirea depozitului",
                "cont": "15 % peste fiecare cost estimat până primim oferte scrise, plus restul până la o sumă rotundă",
                "vat": ("plătit din banii strânși, nu se adaugă niciodată la prețul tău" if not P["vat_registered"] else "inclusă în prețuri"),
                "fees": "5 % platforma + 3 % + €0,20 pe plată", "fail": "cam 3 %, după trei încercări", "refund": "ca oricine anulează înainte de livrare să-și primească banii"}
    names_en = {"vat": "VAT we expect to owe"}
    vat_en = "paid out of the money raised, never added to your price" if not P["vat_registered"] else "VAT included in the prices"
    rows = []
    hdr = "| | € | parte |\n|---|---|---|" if ro else "| | € | share |\n|---|---|---|"
    for l in M["budget_lines"]:
        if ro:
            name, note = names_ro[l["k"]], notes_ro[l["k"]]
        else:
            name, note = names_en.get(l["k"], l["label"]), (vat_en if l["k"] == "vat" else l["note"])
        rows.append(f"| **{name}**: {note} | {e(l['eur'], lang)[1:]} | {round(l['pct'] * 100)} % |")
    tot = "| **Total** | **" + e(M["goal_eur"], lang)[1:] + "** | **100 %** |"
    return "\n".join([hdr] + rows + [tot])


def b_before_campaign(lang):
    t = M["before_campaign_total_eur"]
    if lang == "ro":
        return f"Testele CE și EN 18031, dosarul tehnic, înregistrările de reciclare, marca, unitățile de test și sculele (~{e(t, lang)}) le plătim **înainte** de campanie, din banii noștri și din împrumuturi, nu din campanie. Nu sunt în obiectiv. Nici marketingul."
    return f"CE and EN 18031 testing, the technical file, recycling registrations, the trademark, the test units and the tooling (~{e(t, lang)}) are paid **before** the campaign, from our own money and loans, not from the campaign. They're not in the goal. Neither is marketing."


def _range(a, b, lang):
    if b is None:
        return month(a, lang)
    ma, mb = month(a[:7], lang), month(b[:7], lang)
    if ma == mb:
        return ma
    if ma[-4:] == mb[-4:]:
        return ma.rsplit(" ", 1)[0] + " – " + mb
    return ma + " – " + mb


def b_timeline_table(lang):
    ro = lang == "ro"
    tr_ro = {
        "the campaign ({days} days, all-or-nothing)": "campania ({days} de zile, totul sau nimic)",
        "payments collected; you confirm colour, address and add-ons in the Pledge Manager": "se încasează plățile; îți confirmi culoarea, adresa și extra-urile în Pledge Manager",
        "batch orders: boards, cells, glass, aluminium shells, OU, packaging (tooling and the first article were approved before launch)": "comenzile pentru lot: plăci, baterii, sticlă, carcase din aluminiu, OU, ambalaj (sculele și prima piesă sunt aprobate înainte de lansare)",
        "machining the shells (5–6 weeks, holidays included)": "frezarea carcaselor (5–6 săptămâni, cu tot cu sărbători)",
        "anodising in {colours_n} colours, against the golden samples approved before launch": "anodizarea în {colours_n} culori, după mostrele de referință aprobate înainte de lansare",
        "pilot run of 25 units, full quality check": "lot pilot de 25 de bucăți, verificare completă",
        "assembly and testing of the batch": "asamblarea și testarea lotului",
        "shipping starts (best case)": "pleacă primele colete (cel mai bun caz)",
        "estimated delivery, EU": "livrare estimată, UE",
        "estimated delivery, batch 1 (EU)": "livrare estimată, lotul 1 (UE)",
        "estimated delivery, batch 2 (only pledges beyond batch 1)": "livrare estimată, lotul 2 (doar susținerile de după lotul 1)",
        "payments collected; Pledge Manager": "se încasează plățile; Pledge Manager",
        "EPR registrations in the shipping countries (weeks per country)": "înregistrările EPR în țările de livrare (câteva săptămâni pe țară)",
        "CE/RED + EN 18031 testing at an accredited lab (6–12 weeks, re-test included)": "testele CE/RED + EN 18031 într-un laborator acreditat (6–12 săptămâni, cu retestare)",
        "machining the shells": "frezarea carcaselor",
        "anodising in {colours_n} colours": "anodizarea în {colours_n} culori",
        "pilot run, then assembly and testing": "lotul pilot, apoi asamblarea și testarea",
        "shipping starts (best case), only after the EU DoC is signed": "pleacă primele colete (cel mai bun caz), doar după declarația UE semnată",
    }
    rows = ["| când (estimare) | ce |\n|---|---|" if ro else "| when (estimate) | what |\n|---|---|"]
    for a, b, what, kind in SCN["timeline"]:
        w = tr_ro.get(what, what) if ro else what
        w = w.format(days=C["length_days"], colours_n=b_colours_n(lang))
        when = _range(a, b, lang)
        if kind == "promise":
            when, w = f"**{when}**", f"**{w}**"
        rows.append(f"| {when} | {w} |")
    return "\n".join(rows)


def b_before_launch(lang):
    ro = lang == "ro"
    tr = {"SoulOS runs on the S board, with hold-to-talk voice": "SoulOS rulează pe placa S, cu vocea „ține degetul și vorbește”",
          "an aluminium SOUL S, filmed working in one take": "un SOUL S din aluminiu, filmat funcționând dintr-o singură dublă",
          "EU cybersecurity features built into SoulOS": "funcțiile UE de securitate cibernetică, construite în SoulOS",
          "radio/EMC pre-scan at the lab": "pre-scanarea radio/EMC la laborator",
          "recycling (WEEE, battery, packaging) registrations started in the shipping countries": "înregistrările de reciclare (DEEE, baterii, ambalaje) pornite în țările de livrare",
          "CE/RED + EN 18031 tests passed, EU Declaration of Conformity signed": "testele CE/RED + EN 18031 trecute, declarația UE de conformitate semnată",
          "go / no-go: quotes in writing, list size, KYC, VAT": "decizia go / no-go: oferte scrise, mărimea listei, KYC, TVA",
          "go / no-go": "decizia go / no-go"}
    out = []
    for d, k, what in SCN["before_launch"]:
        w = tr.get(what, what) if ro else what
        g = G.get(k, {})
        if g.get("passed"):
            when = day(g["date"], lang) if g.get("date") else month(d[:7], lang)
            proof = f" ({g['proof']})" if g.get("proof") else ""
            out.append(f"- ✓ **{when}:** {w}{proof}")
        else:
            out.append(f"- {'planificat' if ro else 'planned'} {month(d[:7], lang)}: {w}")
    return "\n".join(out)


def b_stretch_table(lang):
    ro = lang == "ro"
    tr = {"languages": "SoulOS în germană, franceză, spaniolă și italiană",
          "pouch": "un săculeț de pâslă pentru drum în fiecare cutie",
          "birth_card": "un certificat de naștere tipărit în fiecare cutie: ochii SOUL-ului tău, ID-ul cipului și data nașterii"}
    en = {"languages": "SoulOS in German, French, Spanish and Italian",
          "pouch": "a felt travel pouch in every box",
          "birth_card": "a printed birth card in every box: your SOUL's eyes, its chip ID and its birth date"}
    rows = ["| la | ce |\n|---|---|" if ro else "| at | what |\n|---|---|"]
    for s in M["stretch_goals"]:
        rows.append(f"| {e(s['at_eur'], lang)} | {(tr if ro else en)[s['id']]} |")
    return "\n".join(rows)


def b_stretch_short(lang):
    xs = [e(s["at_eur"], lang) for s in M["stretch_goals"]]
    return join_list(xs, lang)


def b_stretch_first(lang):
    s = M["stretch_goals"][0]
    return e(s["at_eur"], lang)


def b_specs_table(lang):
    ro = lang == "ro"
    rows = [
        ("formă", "shape", "MĂRGĂRITAR", "MĂRGĂRITAR"),
        ("mărime", "size", f"{S['width_mm']} × {S['height_mm']} mm, {b_depth(lang)} adâncime (se finalizează)", f"{S['width_mm']} × {S['height_mm']} mm, {b_depth(lang)} deep (being finalised)"),
        ("greutate", "weight", f"{b_weight(lang)} (estimare, se cântărește pe SOUL S real)", f"{b_weight(lang)} (estimate, to be weighed on the real S unit)"),
        ("ecran", "display", "AMOLED rotund 1,75″, 466 × 466, negru adevărat, sub sticlă neagră", "round 1.75″ AMOLED, 466 × 466, true black, under black glass"),
        ("corp", "body", "aluminiu 6061, sablat, anodizat", "aluminium 6061, bead-blasted, anodised"),
        ("culori", "colours", f"{colours('ro')} (același preț)", f"{colours('en')} (same price)"),
        ("ochi", "eyes", "unul din 120 de modele, decis la naștere; 31 de expresii", "one of 120 designs, decided at birth; 31 expressions"),
        ("creier", "brain", "ESP32-S3, Wi-Fi 2,4 GHz și Bluetooth LE", "ESP32-S3, Wi-Fi 2.4 GHz and Bluetooth LE"),
        ("senzori", "sensors", "sticlă tactilă, senzor de mișcare (6 axe)", "touch glass, motion sensor (6-axis)"),
        ("voce", "voice", "2 microfoane, pornite doar cât ții degetul pe sticlă; difuzor", "2 microphones, on only while your finger is on the glass; speaker"),
        ("cameră", "camera", "niciuna", "none"),
        ("ai", "ai", "propriul Claude sau ChatGPT (ChatGPT în dezvoltare), sau offline. AI-ul nu e inclus", "your own Claude or ChatGPT (ChatGPT in development), or offline. AI is not included"),
        ("memorie", "memory", "SOUL Memory, pe dispozitiv", "SOUL Memory, on the device"),
        ("baterie", "battery", "litiu, gândită să fie înlocuibilă (spate cu șuruburi, conector, fără lipici); capacitatea se finalizează", "lithium, designed to be replaceable (screwed back, connector, no glue); capacity being finalised"),
        ("autonomie", "battery life", "o publicăm după ce o măsurăm pe SOUL S real", "published after we measure it on the real S unit"),
        ("încărcare", "charging", "în OU, oul lui, prin contactele aurii din picior", "in OU, its egg, through gold contacts in its foot"),
        ("stare", "status", (f"lotul se face după campanie · **declarația UE de conformitate semnată ({ce_date('ro')})**" if ce_state() != "pre" else "în dezvoltare · **fără certificare CE încă**"),
         (f"batch made after the campaign · **EU Declaration of Conformity signed ({ce_date('en')})**" if ce_state() != "pre" else "in development · **not CE-certified yet**")),
    ]
    out = ["| | SOUL S (produsul pe care îl susții) |\n|---|---|" if ro else "| | SOUL S (the product you back) |\n|---|---|"]
    for a, b, c, d in rows:
        out.append(f"| {a if ro else b} | {c if ro else d} |")
    return "\n".join(out)


def b_shipping_table(lang):
    sh = C["shipping_eur"]
    z1, z2 = sh["EU_zone_1 (AT, DE, PL, NL, BE)"], sh["EU_zone_2 (FR, IT, ES, SE)"]
    if lang == "ro":
        return ("| Zona | Țări | Pe colet (fix) |\n|---|---|---|\n"
                f"| RO | România | {e(sh['RO'], lang)} |\n"
                f"| UE 1 | Germania, Austria, Polonia, Olanda, Belgia | {e(z1, lang)} |\n"
                f"| UE 2 | Franța, Italia, Spania, Suedia | {e(z2, lang)} |\n"
                f"| Încă un SOUL în același colet | – | +{e(sh['extra_unit_same_parcel'], lang)} |")
    return ("| Zone | Countries | Per parcel (fixed) |\n|---|---|---|\n"
            f"| RO | Romania | {e(sh['RO'], lang)} |\n"
            f"| EU 1 | Germany, Austria, Poland, the Netherlands, Belgium | {e(z1, lang)} |\n"
            f"| EU 2 | France, Italy, Spain, Sweden | {e(z2, lang)} |\n"
            f"| Extra SOUL in the same parcel | – | +{e(sh['extra_unit_same_parcel'], lang)} |")


def b_ladder_line(lang):
    la, ca, tw, lp = L["launch"], L["campaign"], L["two"], L["late_pledge_eur"]
    if lang == "ro":
        return (f"**{la['name']}:** primii {la['cap']} susținători, {e(la['price_eur'], lang)}, cu numărul First Light gravat pe picior · **{ca['name']}:** {e(ca['price_eur'], lang)} · "
                f"**{tw['name']}:** {e(tw['price_eur'], lang)} ({e(tw['price_eur'] / 2, lang)} bucata) · după campanie: **Late Pledge** {e(lp, lang)}. Prețul de vânzare planificat după campanie: {e(L['retail_planned_eur'], lang)}.")
    return (f"**{la['name']}:** the first {la['cap']} backers, {e(la['price_eur'], lang)}, with its First Light number engraved on the foot · **{ca['name']}:** {e(ca['price_eur'], lang)} · "
            f"**{tw['name']}:** {e(tw['price_eur'], lang)} ({e(tw['price_eur'] / 2, lang)} each) · after the campaign: **Late Pledge** at {e(lp, lang)}. Planned retail price after the campaign: {e(L['retail_planned_eur'], lang)}.")


def b_offer_bullet(lang):
    la, ca, tw = L["launch"], L["campaign"], L["two"]
    if lang == "ro":
        return f"**{e(la['price_eur'], lang)} pentru primii {la['cap']}**, cu numărul First Light gravat pe picior. Apoi {e(ca['price_eur'], lang)}; doi SOUL, {e(tw['price_eur'], lang)}. Prețul planificat după campanie: {e(L['retail_planned_eur'], lang)}."
    return f"**{e(la['price_eur'], lang)} for the first {la['cap']}**, with its First Light number engraved on the foot. Then {e(ca['price_eur'], lang)}; two SOULs for {e(tw['price_eur'], lang)}. Planned retail price after the campaign: {e(L['retail_planned_eur'], lang)}."


def b_after_campaign(lang):
    lp = L["late_pledge_eur"]
    if lang == "ro":
        return f"După campanie: Late Pledge la {e(lp, lang)}, din {b_late_open(lang)}, livrat cu lotul 2 (estimat {b_batch2(lang)})."
    return f"After the campaign: Late Pledge at {e(lp, lang)}, from {b_late_open(lang)}, delivered with batch 2 (estimated {b_batch2(lang)})."


def b_urgency_subject(lang):
    lp = L["late_pledge_eur"]
    return (f"Încă 48 de ore. Apoi {e(lp, lang)}, în Late Pledge." if lang == "ro" else f"48 hours left. After that, {e(lp, lang)} in Late Pledge.")


def b_urgency_social(lang):
    ca, lp = L["campaign"]["price_eur"], L["late_pledge_eur"]
    return (f"48 de ore. {e(ca, lang)} acum, {e(lp, lang)} în Late Pledge după." if lang == "ro" else f"48 hours. {e(ca, lang)} now, {e(lp, lang)} in Late Pledge after.")


def b_last_day(lang):
    ca, lp = L["campaign"]["price_eur"], L["late_pledge_eur"]
    return (f"Campania SOUL se închide în seara asta. Azi {e(ca, lang)}; după, {e(lp, lang)} în Late Pledge." if lang == "ro"
            else f"SOUL's campaign closes tonight. {e(ca, lang)} today; after that, {e(lp, lang)} in Late Pledge.")


def b_voice(lang):
    ok = F["product"]["voice"]["claude_only_voice_works"]
    if lang == "ro":
        if ok:
            return "Ține degetul pe sticlă și vorbește cu AI-ul tău, inclusiv doar cu Claude. Scrisul pe tastatura rotundă merge mereu, cu orice AI și offline."
        return ("Un detaliu onest: ca să-ți transforme vocea în text, SOUL are nevoie de un serviciu de vorbire. Azi SoulOS îl folosește pe cel de la OpenAI, cu propria ta cheie OpenAI. "
                "Vocea pentru cei care folosesc doar Claude e în dezvoltare. Scrisul pe tastatura rotundă merge mereu, cu orice AI și offline.")
    if ok:
        return "Hold the glass and talk to your own AI, Claude included. Typing on its round keyboard always works, with any AI and offline."
    return ("One honest detail: turning your voice into text needs a speech service. Today SoulOS uses OpenAI's, with your own OpenAI key. "
            "Voice for owners who only use Claude is in development. Typing on its round keyboard always works, with any AI and offline.")


def b_goal_para(lang):
    if lang == "ro":
        return (f"Campania e **totul sau nimic**. Dacă nu ajungem la {b_goal(lang)}, nu plătește nimeni și nu se face nimic. "
                f"{b_goal(lang)} nu e un număr de marketing: e cel mai mic lot (cam {b_devices(lang)} de SOUL) la care banii acoperă fabricarea și livrarea fiecărei recompense, după TVA și comisioane, cu o marjă de siguranță.")
    return (f"This campaign is **all-or-nothing**. If we don't reach {b_goal(lang)}, nobody is charged and nothing is made. "
            f"{b_goal(lang)} isn't a marketing number: it's the smallest batch (about {b_devices(lang)} SOULs) at which the money covers making and delivering every reward, after VAT and fees, with a safety margin.")


def b_delivery_risk(lang):
    wk = SCN["buffer_weeks"]
    if C["scenario"] == "after_ce":
        if ce_passed():
            pre_ro = f"Certificarea CE s-a terminat înainte de lansare (declarația UE semnată pe {ce_date('ro')}), deci nu mai e pe drumul critic."
            pre_en = f"CE testing finished before launch (EU Declaration of Conformity signed on {ce_date('en')}), so it isn't on the critical path."
        else:
            pre_ro = "CE trebuie să treacă înainte de lansare; dacă întârzie, se mută lansarea, nu data ta de livrare."
            pre_en = "CE must pass before launch; if it slips, the launch moves, not your delivery date."
        if lang == "ro":
            return f"{pre_ro} Ce mai poate muta data: frezarea și anodizarea lotului și coletele din perioada sărbătorilor. Am păstrat cam {wk} săptămâni de rezervă."
        return f"{pre_en} What can still move the date: machining and anodising the batch, and parcels around the holidays. We've kept about {wk} weeks of buffer."
    if lang == "ro":
        return f"Ce poate muta data: testul CE în laborator (un test picat înseamnă reparații și retestare) și anodizarea, care merg în paralel. Am păstrat cam {wk} săptămâni de rezervă."
    return f"What can move the date: the CE lab test (a failed test means fixes and a re-test) and anodising, which run in parallel. We've kept about {wk} weeks of buffer."


def b_supply_risk(lang):
    r = F["decisions"]["D8"]["kit_default"]
    dec = F["decisions"]["D8"]["decided"]
    if r == "B":
        if lang == "ro":
            t = ("Placa din SOUL S vine de la un singur furnizor (Waveshare ESP32-S3-Touch-AMOLED-1.75). Ce facem: cerem o ofertă scrisă de volum înainte de lansare și cumpărăm toate plăcile pentru lot imediat după prima plată. "
                 "O placă proprie (cu modul radio pre-certificat) e un proiect pentru un lot următor, nu pentru acesta.")
        else:
            t = ("The board inside SOUL S comes from one supplier (Waveshare ESP32-S3-Touch-AMOLED-1.75). What we do: a written volume quote before launch, and we buy every board for the batch as soon as the first payout arrives. "
                 "A board of our own (with a pre-certified radio module) is a project for a later batch, not this one.")
    else:
        if lang == "ro":
            t = ("SOUL S are o placă proprie, cu un modul ESP32-S3-WROOM-1 și un ecran AMOLED de 1,75″ cumpărat separat. Ecranul vine de la un număr mic de producători. "
                 "Ce facem: un al doilea ecran calificat înainte de lansare și toate ecranele pentru lot cumpărate la prima plată.")
        else:
            t = ("SOUL S has a board of our own, with an ESP32-S3-WROOM-1 module and a 1.75″ AMOLED panel bought separately. The panel comes from a small number of makers. "
                 "What we do: a second qualified panel before launch, and every panel for the batch bought at the first payout.")
    return t + ("" if dec else " [[D8: electronics route not decided yet; this paragraph follows facts.json decisions.D8]]")


def b_rewards_md(lang):
    la, ca, tw, b2 = L["launch"], L["campaign"], L["two"], L["campaign_b2"]
    dl, d2 = b_delivery(lang), b_batch2(lang)
    cols = colours(lang)
    ro = lang == "ro"
    if ro:
        out = [
            f"### Soul Supporter · {e(P['supporter_eur'], lang)}",
            "Fără dispozitiv, doar din suflet. Numele tău în registrul de nașteri SOUL (opțional), pachetul digital de wallpapere cu ochi și fiecare update.",
            "- **Fără limită** · **Livrare:** digital, în prima lună după campanie; registrul se publică atunci când pleacă primii SOUL",
            "",
            f"### {la['name']} · {e(la['price_eur'], lang)} · {la['cap']} bucăți · 1 de susținător · lotul 1",
            f"Primii {la['cap']} SOUL, la cel mai mic preț din campanie, fiecare cu **numărul lui First Light (001–{la['cap']}) gravat cu laserul pe picior**. Un SOUL S (63 × 71 mm, AMOLED rotund de 1,75″) în culoarea aleasă ({cols}), născut cu ochii aleși de el, și OU, oul lui de încărcare.",
            f"{b_ai_line(lang)} {b_ce_short(lang)} Prețul planificat după campanie: {e(L['retail_planned_eur'], lang)}. Prețul e final (nu se adaugă TVA).",
            "*Render (CGI), nu fotografie.*",
            f"- **Conține:** 1 × SOUL S (opțiune de culoare), 1 × OU, cablu USB-C, ghid · **Livrare estimată:** {dl}",
            "",
            f"### {ca['name']} · {e(ca['price_eur'], lang)} · {ca['cap']} bucăți · lotul 1",
            f"Un SOUL S în culoarea aleasă, cu ochii aleși de el, și OU. Restul textului ca la {la['name']}, fără gravură.",
            f"- **Conține:** 1 × SOUL S, 1 × OU, cablu USB-C, ghid · **Livrare estimată:** {dl}",
            "",
            f"### {tw['name']} · {e(tw['price_eur'], lang)} ({e(tw['price_eur'] / 2, lang)} bucata) · {tw['cap']} seturi · lotul 1",
            f"Doi SOUL S la prețul First Light pe bucată, oricare două culori, fiecare cu OU-ul lui. Unul pentru tine, unul pentru cineva drag. Fiecare se naște cu ochii lui, deci rareori se potrivesc.",
            f"- **Conține:** 2 × SOUL S, 2 × OU, 2 × cablu USB-C, ghid · un singur colet · **Livrare estimată:** {dl}",
            "",
            f"### Campaign Price · lotul 2 · {e(b2['price_eur'], lang)} · fără limită",
            f"Același SOUL S și OU, din lotul 2, pentru cine vine după ce lotul 1 s-a terminat. **Livrare estimată: {d2}.**",
            f"- **Conține:** 1 × SOUL S, 1 × OU, cablu USB-C, ghid · **Livrare estimată:** {d2}",
            "",
            f"### Extra: încă un ou OU · {e(P['ou_extra_eur'], lang)}",
            "Al doilea ou de încărcare, pentru birou sau noptieră. Vine în același colet cu SOUL, fără transport în plus.",
            "",
            f"### Late Pledge (după campanie) · {e(L['late_pledge_eur'], lang)}",
            b_after_campaign(lang),
        ]
    else:
        out = [
            f"### Soul Supporter · {e(P['supporter_eur'], lang)}",
            "No device, all heart. Your name in the SOUL birth register (opt-in), the campaign's digital eye wallpaper pack, and every backer update.",
            "- **Cap:** none · **Delivery:** digital, within a month of the campaign's end; the birth register is published when the first SOULs ship",
            "",
            f"### {la['name']} · {e(la['price_eur'], lang)} · {la['cap']} available · 1 per backer · batch 1",
            f"The first {la['cap']} SOULs, at the lowest price of the campaign, each with **its First Light number (001–{la['cap']}) laser-engraved on its foot**. One SOUL S (63 × 71 mm, round 1.75″ AMOLED) in the colour you choose ({cols}), born with the eyes it chooses, and OU, its charging egg.",
            f"{b_ai_line(lang)} {b_ce_short(lang)} Planned retail price after the campaign: {e(L['retail_planned_eur'], lang)}. Price is final (no VAT is added).",
            "*Render (CGI), not a photo.*",
            f"- **Items:** 1 × SOUL S (colour option), 1 × OU charging egg, USB-C cable, quick-start guide · **Estimated delivery:** {dl}",
            "",
            f"### {ca['name']} · {e(ca['price_eur'], lang)} · {ca['cap']} available · batch 1",
            f"One SOUL S in the colour you choose, born with the eyes it chooses, and OU. Same text as {la['name']} otherwise, without the engraving.",
            f"- **Items:** 1 × SOUL S, 1 × OU, USB-C cable, guide · **Estimated delivery:** {dl}",
            "",
            f"### {tw['name']} · {e(tw['price_eur'], lang)} ({e(tw['price_eur'] / 2, lang)} each) · {tw['cap']} sets · batch 1",
            "Two SOULs S at the First Light price each, any two colours, each with its own OU. One for you, one for someone you like. Each is born with its own eyes, so they rarely match.",
            f"- **Items:** 2 × SOUL S, 2 × OU, 2 × USB-C cable, guide · ships to one address · **Estimated delivery:** {dl}",
            "",
            f"### Campaign Price · batch 2 · {e(b2['price_eur'], lang)} · no cap",
            f"The same SOUL S and OU, from batch 2, for anyone who comes after batch 1 is gone. **Estimated delivery: {d2}.**",
            f"- **Items:** 1 × SOUL S, 1 × OU, USB-C cable, guide · **Estimated delivery:** {d2}",
            "",
            f"### Add-on: Extra OU egg · {e(P['ou_extra_eur'], lang)}",
            "A second charging egg, for the office or the bedside. Ships in the same parcel as your SOUL, no extra shipping.",
            "",
            f"### Late Pledge (after the campaign) · {e(L['late_pledge_eur'], lang)}",
            b_after_campaign(lang),
        ]
    return "\n".join(out)


def b_internal_contrib(lang):
    c = M["contribution_per_device_eur"]
    return (f"Contribution per device after unit cost at the goal batch ({M['devices']} units, {e(M['unit_cost_eur'], 'en')} each) [estimate, tools/goal_model.py]: "
            f"{L['launch']['name']} €{c['launch']:.0f} · {L['campaign']['name']} €{c['campaign']:.0f} · {L['two']['name']} €{c['two']:.0f} per device · Late Pledge €{c['late']:.0f}.")


def b_delivery_field(lang):
    return f"{month(SCN['reward_delivery_field'], lang)} ({SCN['reward_delivery_remark']}); Campaign Price · batch 2: {month(SCN['batch_2_delivery_field'], lang)} ({SCN['batch_2_delivery_remark']})"


def b_launch_upper(lang):
    return day(SCN["launch"], lang).upper()


def b_campaign_para(lang):
    la, ca = L["launch"], L["campaign"]
    if lang == "ro":
        return (f"**Campania.** Campania se desfășoară **{b_campaign_dates(lang)}** pe Indiegogo, totul sau nimic, cu un obiectiv de {b_goal(lang)}: cel mai mic lot la care toate recompensele pot fi făcute și livrate. "
                f"Recompensele pornesc de la {e(la['price_eur'], lang)} pentru primii {la['cap']} susținători (First Light), apoi {e(ca['price_eur'], lang)}; prețul de vânzare planificat după campanie e {b_retail(lang)}. "
                f"Livrare estimată pentru lotul 1: {b_delivery(lang)}. Prima campanie livrează în {b_countries(lang)}.")
    return (f"**Campaign.** The campaign runs **{b_campaign_dates(lang)}** on Indiegogo, all-or-nothing, with a goal of {b_goal(lang)}: the smallest batch at which every reward can be made and delivered. "
            f"Rewards start at {e(la['price_eur'], lang)} for the first {la['cap']} backers (First Light), then {e(ca['price_eur'], lang)}; the planned retail price after the campaign is {b_retail(lang)}. "
            f"Estimated delivery for batch 1: {b_delivery(lang)}. The first campaign ships to {b_countries(lang)}.")


def ce_state():
    """'passed' (gate passed) · 'live' (scenario after_ce: the live page exists only after CE, so it is written in the
    passed state with [[CE: …]] placeholders that block publishing) · 'pre' (pre-CE campaign)."""
    if ce_passed():
        return "passed"
    return "live" if C["scenario"] == "after_ce" else "pre"


def ce_lab(lang):
    return G["CE"]["lab"] or ("[[CE: numele laboratorului]]" if lang == "ro" else "[[CE: lab name]]")


def ce_date(lang):
    return day(G["CE"]["date"], lang) if G["CE"].get("date") else ("[[CE: data semnării declarației UE]]" if lang == "ro" else "[[CE: date the EU DoC is signed]]")


def b_delivery_b2(lang):
    return month(SCN["estimated_delivery"]["late_pledge_batch_2"], lang)


def b_batch1(lang):
    return str(C["batch_1"]["devices"])


def b_age(lang):
    return str(F["product"]["age"]["page"])


def b_countries(lang):
    en = {"RO": "Romania", "DE": "Germany", "AT": "Austria", "FR": "France", "BE": "Belgium", "NL": "the Netherlands", "IT": "Italy", "ES": "Spain", "PL": "Poland", "SE": "Sweden", "GB": "the United Kingdom"}
    ro = {"RO": "România", "DE": "Germania", "AT": "Austria", "FR": "Franța", "BE": "Belgia", "NL": "Olanda", "IT": "Italia", "ES": "Spania", "PL": "Polonia", "SE": "Suedia", "GB": "Marea Britanie"}
    xs = [(ro if lang == "ro" else en)[c] for c in C["shipping_countries_campaign_1"]]
    return join_list(xs, lang)


def b_ai_line(lang):
    if lang == "ro":
        return "Merge cu propriul Claude sau cu propria cheie API OpenAI (în dezvoltare), ori offline. SOUL nu include AI."
    return F["labels"]["ai_short"]


def b_ce_now(lang):
    """For messages sent before the EU DoC is signed (waitlist emails): today's truth, rebuilt before every send."""
    if ce_passed():
        return b_ce_short(lang)
    if C["scenario"] == "after_ce":
        return ("Nu are încă certificare CE. Campania pornește doar după ce testele sunt trecute și declarația UE de conformitate e semnată." if lang == "ro"
                else "SOUL is not CE-certified yet. The campaign starts only once the tests are passed and the EU Declaration of Conformity is signed.")
    return b_ce_short(lang)


def b_shipping_note(lang):
    sh = C["shipping_eur"]
    if lang == "ro":
        return f"Transportul se plătește după campanie, în Pledge Manager, la tarifele fixe de mai sus. {sh['wording_ro']}"
    return f"Shipping is paid after the campaign, in the Pledge Manager, at the fixed rates above. {sh['wording_en']}"


def b_batch_line(lang):
    la, ca, tw = L["launch"], L["campaign"], L["two"]
    n = C["batch_1"]["devices"]
    if lang == "ro":
        return (f"Lotul 1 are {n} de SOUL: {la['cap']} First Light, {ca['cap']} Campaign Price și {tw['cap']} seturi Two Souls. Livrare estimată: {b_delivery(lang)}. "
                f"Când se termină, **Campaign Price · lotul 2** (același preț, {e(L['campaign_b2']['price_eur'], lang)}) se livrează în {b_batch2(lang)} (estimare). Data scrisă la recompensa ta e cea care contează.")
    return (f"Batch 1 is {n} SOULs: {la['cap']} First Light, {ca['cap']} Campaign Price and {tw['cap']} Two Souls sets. Estimated delivery: {b_delivery(lang)}. "
            f"When they're gone, **Campaign Price · batch 2** (same price, {e(L['campaign_b2']['price_eur'], lang)}) delivers in {b_batch2(lang)} (estimate). The date on your reward is the one that counts.")


def b_ce_short_ro(lang):
    return b_ce_short("ro")


def b_launch_day_ro(lang):
    return b_launch_day("ro")


BLOCKS = {k[2:]: v for k, v in globals().items() if k.startswith("b_") and callable(v)}
RX = re.compile(r"<!--f:([a-z0-9_]+)-->(.*?)<!--/f-->", re.S)


def fill(text, lang):
    unknown = []

    def rep(m):
        k = m.group(1)
        if k not in BLOCKS:
            unknown.append(k)
            return m.group(0)
        v = BLOCKS[k](lang)
        if "\n" in v and not m.group(2).startswith("\n"):
            v = "\n" + v + "\n"
        elif "\n" in v:
            v = "\n" + v + "\n"
        return f"<!--f:{k}-->{v}<!--/f-->"
    out = RX.sub(rep, text)
    if unknown:
        raise SystemExit(f"unknown block(s): {unknown}")
    return out


def fill_all():
    n = 0
    for root, _, files in os.walk(CAMP):
        for f in files:
            if not f.endswith(".md"):
                continue
            p = os.path.join(root, f)
            lang = "ro" if os.sep + "ro" in root else "en"
            t = open(p, encoding="utf-8").read()
            t2 = fill(t, lang)
            if t2 != t:
                open(p, "w", encoding="utf-8").write(t2)
                n += 1
    return n


# ------------------------------------------------------------------------------------------------ perks.csv
def perks_csv():
    la, ca, tw, b2 = L["launch"], L["campaign"], L["two"], L["campaign_b2"]
    sh = C["shipping_eur"]
    ship = (f"Per parcel, fixed: Romania €{sh['RO']}; DE, AT, PL, NL, BE €{sh['EU_zone_1 (AT, DE, PL, NL, BE)']}; FR, IT, ES, SE €{sh['EU_zone_2 (FR, IT, ES, SE)']}; "
            f"+€{sh['extra_unit_same_parcel']} per extra SOUL in the same parcel. Paid after the campaign in the Pledge Manager. {sh['wording_en']}")
    common = (F["labels"]["ai_short"] + " " + b_ce_short("en") + f" Planned retail price after the campaign: €{L['retail_planned_eur']}. Price is final (no VAT is added). Render (CGI), not a photo.")
    col_opt = "Colour: " + " / ".join(F["colours"]) + " (same price)"
    sku = "SOUL-S-{" + "|".join(c[:3].upper() for c in F["colours"]) + "}"
    deliv, remark = SCN["reward_delivery_field"], SCN["reward_delivery_remark"]
    deliv2, remark2 = SCN["batch_2_delivery_field"], SCN["batch_2_delivery_remark"]
    countries = ", ".join(C["shipping_countries_campaign_1"])
    dims = f"{S['width_mm']} × {S['height_mm']} mm, round 1.75″ AMOLED"
    rows = [
        dict(id="supporter", title="Soul Supporter", price_eur=P["supporter_eur"],
             description="No device, all heart. Your name in the SOUL birth register (opt-in), the campaign's digital eye wallpaper pack, and every backer update.",
             items="Name in the SOUL birth register (opt-in); digital eye wallpaper pack; backer updates", options="", cap="", per_backer_limit="",
             estimated_delivery=SCN["end"][:7], delivery_remark="Wallpaper pack within a month of the campaign's end. The birth register is published when the first SOULs ship.",
             shipping="Digital, no shipping", ships_to="worldwide", sku="SOUL-SUP", image="reward_1_soul_supporter_700x700.png", pin="no"),
        dict(id="first_light", title=la["name"], price_eur=la["price_eur"],
             description=f"The first {la['cap']} SOULs, at the lowest price of the campaign, each with its First Light number (001–{la['cap']}) laser-engraved on its foot. One SOUL S ({dims}) in the colour you choose, born with the eyes it chooses, and OU, its charging egg. Batch 1. " + common,
             items="1 × SOUL S (colour option, First Light number engraved); 1 × OU charging egg; USB-C cable; quick-start guide", options=col_opt, cap=la["cap"], per_backer_limit=1,
             estimated_delivery=deliv, delivery_remark=remark, shipping=ship, ships_to=countries, sku=sku, image="reward_2_first_light_700x700.jpg", pin="yes, while available"),
        dict(id="campaign", title=ca["name"], price_eur=ca["price_eur"],
             description=f"One SOUL S ({dims}) in the colour you choose, born with the eyes it chooses, and OU, its charging egg. Batch 1 ({ca['cap']} available). " + common,
             items="1 × SOUL S (colour option); 1 × OU charging egg; USB-C cable; quick-start guide", options=col_opt, cap=ca["cap"], per_backer_limit="",
             estimated_delivery=deliv, delivery_remark=remark, shipping=ship, ships_to=countries, sku=sku, image="reward_3_campaign_price_700x700.jpg", pin="no"),
        dict(id="two_souls", title=tw["name"], price_eur=tw["price_eur"],
             description=f"Two SOULs S at the First Light price each (€{tw['price_eur'] // 2} each), any two colours, each with its own OU. One for you, one for someone you like. Each is born with its own eyes, so they rarely match. Batch 1. " + common.replace(f"€{L['retail_planned_eur']}.", f"€{L['retail_planned_eur']} each."),
             items="2 × SOUL S (colour option each); 2 × OU charging egg; 2 × USB-C cable; quick-start guide", options="Colour of SOUL 1 and SOUL 2: " + " / ".join(F["colours"]), cap=tw["cap"], per_backer_limit="",
             estimated_delivery=deliv, delivery_remark=remark, shipping=ship + " Both SOULs ship to one address.", ships_to=countries, sku="SOUL-S-2PK", image="reward_4_two_souls_700x700.jpg", pin="yes, after First Light sells out"),
        dict(id="campaign_b2", title=b2["name"], price_eur=b2["price_eur"],
             description=f"The same SOUL S ({dims}) and OU, from batch 2, for anyone who comes after batch 1 is gone. Estimated delivery {month(deliv2)} (later than batch 1). " + common,
             items="1 × SOUL S (colour option); 1 × OU charging egg; USB-C cable; quick-start guide", options=col_opt, cap="", per_backer_limit="",
             estimated_delivery=deliv2, delivery_remark=remark2, shipping=ship, ships_to=countries, sku=sku, image="reward_3b_campaign_batch2_700x700.jpg", pin="no (open it when batch 1 is gone; it can also be live from day 1)"),
        dict(id="ou_extra", title="Extra OU egg (add-on)", price_eur=P["ou_extra_eur"],
             description="A second charging egg, for the office or the bedside. Ships in the same parcel as your SOUL, no extra shipping. Render (CGI), not a photo.",
             items="1 × OU charging egg; USB-C cable", options="", cap="", per_backer_limit="", estimated_delivery=deliv, delivery_remark="With your SOUL (same parcel, same month).",
             shipping="Ships with your SOUL; no extra shipping", ships_to=countries, sku="SOUL-OU", image="reward_5_addon_extra_ou_700x700.jpg", pin="no"),
        dict(id="late_pledge", title="Late Pledge (after the campaign)", price_eur=L["late_pledge_eur"],
             description=f"Missed the campaign? From about {b_late_open('en')}: €{L['late_pledge_eur']}, delivered with batch 2 (estimated {b_batch2('en')}). Same SOUL S + OU. " + common.replace(f" Planned retail price after the campaign: €{L['retail_planned_eur']}.", ""),
             items="1 × SOUL S (colour option); 1 × OU charging egg; USB-C cable; quick-start guide", options=col_opt, cap="batch 2 capacity", per_backer_limit="",
             estimated_delivery=deliv2, delivery_remark=remark2,
             shipping=ship, ships_to=countries, sku=sku, image="reward_6_late_pledge_700x700.jpg", pin="n/a"),
    ]
    p = os.path.join(CAMP, "perks.csv")
    with open(p, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return p


# ------------------------------------------------------------------------------------------------ story-paste.html
IMG_RX = re.compile(r"\{\{(img|video):([a-z0-9-]+)\}\}")


def image_files():
    """placeholder -> published file, from the table in campaign/00-image-map.md."""
    t = open(os.path.join(CAMP, "00-image-map.md"), encoding="utf-8").read()
    m = {}
    for row in re.finditer(r"^\| `\{\{((?:img|video):[a-z0-9-]+)\}\}` \| ([^|]+) \|", t, re.M):
        m[row.group(1)] = row.group(2).strip().strip("`")
    return m


def md_to_html(text, files):
    import markdown
    text = re.sub(r"<!--f:[a-z0-9_]+-->|<!--/f-->", "", text)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)

    def slot(m):
        key = f"{m.group(1)}:{m.group(2)}"
        f = files.get(key, "?")
        if m.group(1) == "video":
            return f"\n<p class=\"slot\" data-file=\"{html.escape(f)}\">[VIDEO: {html.escape(f)}]</p>\n"
        return f"\n<p class=\"slot\" data-file=\"{html.escape(f)}\">[IMAGE: {html.escape(f)}]</p>\n"
    text = IMG_RX.sub(slot, text)
    return markdown.markdown(text, extensions=["tables", "sane_lists"])


def split_sections(md):
    """'## title [section: X]' -> list of (X, title, body)."""
    out, cur = [], None
    for line in md.splitlines():
        m = re.match(r"^## (.+?) \[section: ([^\]]+)\]\s*$", line)
        if m:
            cur = [m.group(2).replace(" (required)", ""), m.group(1), []]
            out.append(cur)
        elif cur is not None:
            cur[2].append(line)
    return [(a, b, "\n".join(c)) for a, b, c in out]


def story_paste():
    files = image_files()
    story = open(os.path.join(CAMP, "02-story.md"), encoding="utf-8").read()
    secs = split_sections(story)
    extra = {"Risks and challenges": "04-risks.md", "Refunds and cancellation": "13-refunds.md"}
    blocks = []
    for name, title, body in secs:
        if name in extra:
            body = open(os.path.join(CAMP, extra[name]), encoding="utf-8").read()
            body = re.sub(r"^# .*\n", "", body)
            body = re.sub(r"^> \*\*Draft[^\n]*\n", "", body, flags=re.M)
            title = None
        blocks.append((name, title, md_to_html(body, files)))
    faq = open(os.path.join(CAMP, "05-faq.md"), encoding="utf-8").read()
    faq = re.sub(r"^# .*\n", "", faq)
    blocks.append(("FAQ tab (one entry per question)", None, md_to_html(faq, files)))
    unresolved = sorted(set(re.findall(r"\[\[[A-Z0-9_]+:[^\]]*\]\]|\{\{AGE\}\}|\{\{URL:[a-z-]+\}\}|\[de completat[^\]]*\]", story + faq)))
    secs_html = []
    for i, (name, title, body) in enumerate(blocks):
        h = f"<h2>{html.escape(title)}</h2>\n" if title else ""
        secs_html.append(f"""<section class="sec">
<header><div><span class="eb">Indiegogo section</span><h1>{html.escape(name)}</h1></div><button data-i="{i}">Copy section</button></header>
<div class="content" id="c{i}">{h}{body}</div>
</section>""")
    warn = ""
    if unresolved:
        warn = ("<div class=\"warn\"><b>Not ready to publish.</b> These placeholders are still open and must be closed first "
                "(tools/check_copy.py --strict): " + ", ".join(html.escape(x[:60]) for x in unresolved[:40]) + (" …" if len(unresolved) > 40 else "") + "</div>")
    doc = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SOUL story paste</title>
<style>
:root{{--bg:#f6f3ec;--ink:#16181d;--mute:#5a5d66;--line:#d8d3c7;--card:#fff;--acc:#d2622c;--slot:#fff0c8}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--bg:#0d0d0f;--ink:#f6f3ec;--mute:#a4a7ae;--line:#2a2a30;--card:#16161a;--slot:#3a3320}}}}
:root[data-theme="dark"]{{--bg:#0d0d0f;--ink:#f6f3ec;--mute:#a4a7ae;--line:#2a2a30;--card:#16161a;--slot:#3a3320}}
body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}}
main{{max-width:860px;margin:0 auto;padding:24px 16px 80px}}
.intro{{border:1px solid var(--line);background:var(--card);border-radius:14px;padding:16px 18px;margin-bottom:24px}}
.warn{{border:2px solid var(--acc);border-radius:12px;padding:12px 16px;margin:0 0 24px}}
.sec{{border:1px solid var(--line);background:var(--card);border-radius:14px;margin:0 0 28px;overflow:hidden}}
.sec header{{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:12px 16px;border-bottom:1px solid var(--line)}}
.sec h1{{font-size:20px;margin:2px 0 0}} .eb{{font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--mute)}}
button{{font:600 14px system-ui;border:0;border-radius:999px;padding:9px 16px;background:var(--ink);color:var(--bg);cursor:pointer;flex:none}}
.content{{padding:8px 18px 18px;overflow-wrap:anywhere}} .content table{{border-collapse:collapse;width:100%;display:block;overflow-x:auto}}
.content td,.content th{{border:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}}
.slot{{background:var(--slot);border-radius:8px;padding:8px 10px;font:600 13px ui-monospace,monospace}}
</style></head><body><main>
<div class="intro"><b>SOUL · paste file for Indiegogo's editor</b> (generated by tools/build_copy.py from campaign/*.md and facts.json; scenario <code>{C['scenario']}</code>, ladder <code>{C['ladder']}</code>, goal {b_goal('en')}).<br>
For each section: press <b>Copy section</b>, click into the matching section in Indiegogo (Project settings → Project details → Detailed description), paste. Then, at every yellow <code>[IMAGE: file]</code> line, upload that file from <code>images/</code> with the editor's image button, keep the italic caption line under it, and delete the marker line. <code>[VIDEO: …]</code> = paste the YouTube link.</div>
{warn}
{chr(10).join(secs_html)}
</main>
<script>
document.querySelectorAll('button[data-i]').forEach(b=>b.addEventListener('click',async()=>{{
  const el=document.getElementById('c'+b.dataset.i);
  try{{await navigator.clipboard.write([new ClipboardItem({{'text/html':new Blob([el.innerHTML],{{type:'text/html'}}),'text/plain':new Blob([el.innerText],{{type:'text/plain'}})}})]);b.textContent='Copied';}}
  catch(e){{const r=document.createRange();r.selectNodeContents(el);const s=getSelection();s.removeAllRanges();s.addRange(r);document.execCommand('copy');b.textContent='Copied (selection)';}}
  setTimeout(()=>b.textContent='Copy section',1800);
}}));
</script></body></html>"""
    p = os.path.join(CAMP, "story-paste.html")
    open(p, "w", encoding="utf-8").write(doc)
    return p, unresolved


if __name__ == "__main__":
    n = fill_all()
    print(f"filled blocks in {n} file(s)")
    print("wrote", perks_csv())
    p, un = story_paste()
    print("wrote", p, f"({len(un)} open placeholders listed on the page)")
