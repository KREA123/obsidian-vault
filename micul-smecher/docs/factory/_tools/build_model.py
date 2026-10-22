#!/usr/bin/env python3
"""Builds SOUL-fabrica-model.xlsx: cost & break-even model for a small SOUL factory / production chain.
Base size: SOUL S (decision 2026-10-20; docs/size-s.json, docs/12-SIZE-S.md §3). M (the 2.8C prototype) is the comparison delta.
Usage: python3 build_model.py OUT.xlsx, then recalc (LibreOffice) before reading values."""
import re, sys
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

OUT = sys.argv[1]
FONT = "Arial"
F_IN = Font(name=FONT, color="0000FF", size=10)
F_IN_B = Font(name=FONT, color="0000FF", size=10, bold=True)
F_N = Font(name=FONT, size=10)
F_B = Font(name=FONT, size=10, bold=True)
F_H = Font(name=FONT, size=14, bold=True)
F_SEC = Font(name=FONT, size=11, bold=True, color="FFFFFF")
F_LINK = Font(name=FONT, size=10, color="008000")
F_NOTE = Font(name=FONT, size=9, italic=True, color="555555")
FILL_KEY = PatternFill("solid", fgColor="FFFF00")
FILL_SEC = PatternFill("solid", fgColor="2F4F6F")
FILL_TOT = PatternFill("solid", fgColor="E8EEF4")
FILL_HDR = PatternFill("solid", fgColor="D9D9D9")
THIN = Side(style="thin", color="999999")
B_TOP = Border(top=THIN)
WRAP = Alignment(wrap_text=True, vertical="top")

EUR0 = '#,##0" €";-#,##0" €";"-"'
EUR2 = '#,##0.00" €";-#,##0.00" €";"-"'
NUM0 = '#,##0;-#,##0;"-"'
NUM1 = '#,##0.0;-#,##0.0;"-"'
NUM2 = '#,##0.00;-#,##0.00;"-"'
NUM4 = '0.0000'
PCT = '0.0%;-0.0%;"-"'
LEI = '#,##0" lei"'
USD = '"$"#,##0.00'

VC = ["C", "D", "E", "F"]  # volume columns, identical in every sheet

wb = openpyxl.Workbook()
RM = wb.active
RM.title = "Citește-mă"
IP = wb.create_sheet("Ipoteze")
SC = wb.create_sheet("Scenarii")
BE = wb.create_sheet("Break-even")
CP = wb.create_sheet("Capacitate")
RZ = wb.create_sheet("Rezultate")
wb.move_sheet("Rezultate", offset=-4)  # order: Citește-mă, Rezultate, Ipoteze, Scenarii, Break-even, Capacitate

REG = {}      # key -> (row, tiered)
SROW = {}     # Scenarii row map
BROW = {}     # Break-even row map


def ipref(key, col):
    r, tiered = REG[key]
    return f"Ipoteze!{col}${r}" if tiered else f"Ipoteze!$C${r}"


def T(tpl, col, rowmap):
    """[key] -> Ipoteze ref; {S:name} -> Scenarii!col row; {B:name} -> Break-even!col row; {name} -> same-sheet."""
    s = re.sub(r"\[([A-Za-z0-9_]+)\]", lambda m: ipref(m.group(1), col), tpl)
    s = re.sub(r"\{S:([A-Za-z0-9_]+)\}", lambda m: f"Scenarii!{col}{SROW[m.group(1)]}", s)
    s = re.sub(r"\{B:([A-Za-z0-9_]+)\}", lambda m: f"'Break-even'!{col}{BROW[m.group(1)]}", s)
    s = re.sub(r"\{([A-Za-z0-9_]+)\}", lambda m: f"{col}{rowmap[m.group(1)]}", s)
    return s


# ------------------------------------------------------------------ Ipoteze
IP.column_dimensions["A"].width = 18
IP.column_dimensions["B"].width = 58
for c in VC:
    IP.column_dimensions[c].width = 12
IP.column_dimensions["G"].width = 11
IP.column_dimensions["H"].width = 95
IP.column_dimensions["I"].width = 12
IP["A1"] = "IPOTEZE: toate datele de intrare ale modelului (singurul loc unde se modifică cifre)"
IP["A1"].font = F_H
IP["A2"] = ("Legendă: text albastru = intrare editabilă; fond galben = pârghie-cheie; negru = formulă. "
            "Coloanele C–F = valori pe volum (100 / 1.000 / 5.000 / 20.000 unit./an); un singur număr în C = valabil pentru toate volumele. "
            "Sumele sunt FĂRĂ TVA, cu excepția celor marcate „cu TVA”. Sursele au URL + dată; [estimare] = raționament propriu, de înlocuit cu oferte (RFQ).")
IP["A2"].font = F_NOTE
IP["A2"].alignment = WRAP
IP.merge_cells("A2:I2")
IP.row_dimensions[2].height = 42
hdr = ["Cheie", "Parametru", "100 / valoare", "1.000", "5.000", "20.000", "Unitate", "Sursă / notă (data accesării)", "Încredere"]
for i, h in enumerate(hdr):
    c = IP.cell(row=4, column=i + 1, value=h)
    c.font = F_B
    c.fill = FILL_HDR
IP.freeze_panes = "C5"
ip_row = [5]


def sec(ws, row, title, ncols=9):
    c = ws.cell(row=row, column=1, value=title)
    c.font = F_SEC
    for i in range(1, ncols + 1):
        ws.cell(row=row, column=i).fill = FILL_SEC


def isec(title):
    ip_row[0] += 1
    sec(IP, ip_row[0], title)
    ip_row[0] += 1


def inp(key, label, vals, unit, src, conf="[estimare]", fmt=NUM2, key_lever=False):
    r = ip_row[0]
    tiered = isinstance(vals, list)
    REG[key] = (r, tiered)
    IP.cell(row=r, column=1, value=key).font = F_NOTE
    IP.cell(row=r, column=2, value=label).font = F_N
    IP.cell(row=r, column=2).alignment = WRAP
    vv = vals if tiered else [vals]
    for j, v in enumerate(vv):
        col = VC[j]
        cell = IP[f"{col}{r}"]
        if isinstance(v, str) and v.startswith("="):
            cell.value = T(v, col, {})
            cell.font = F_N
        else:
            cell.value = v
            cell.font = F_IN_B if key_lever else F_IN
        cell.number_format = fmt
        if key_lever:
            cell.fill = FILL_KEY
    IP.cell(row=r, column=7, value=unit).font = F_N
    h = IP.cell(row=r, column=8, value=src)
    h.font = F_N
    h.alignment = WRAP
    IP.cell(row=r, column=9, value=conf).font = F_N
    ip_row[0] += 1


V = "vault"
E = "[estimare]"
L = "listare"
O = "oficial"

isec("1. Generale")
inp("fx_eur_lei", "Curs EUR → lei", 5.10, "lei/€", "Vault: „Finanțare — oferte de preț pentru PoC 1.1” (curs folosit pentru estimare, 12.10.2026)", V)
inp("fx_usd_eur", "Curs USD → EUR", 0.87, "€/$", "Vault: idem (1 $ ≈ 0,87 €)", V)
inp("vol", "Volum analizat", [100, 1000, 5000, 20000], "unit./an", "Cererea fondatorului: pilot → sute → mii → zeci de mii pe an", "input", NUM0, True)
inp("price_retail", "Preț de vânzare (include TVA dacă firma e plătitoare)", 249, "€", "Plan: preț de la €249 (Planul de bani Micul Șmecher)", "input", EUR0)
inp("vat_rate", "Cotă TVA România", 0.21, "%", "Vault BOM.csv P0-17: TVA import 21 %", V, PCT)
inp("vat_threshold_lei", "Plafon de scutire TVA (cifra de afaceri anuală)", 395000, "lei",
    "[de verificat cu contabilul] 395.000 lei (art. 310 Cod fiscal, din 1.09.2025, după cunoștințele mele; nu am verificat în această rundă). "
    "Sub plafon ARTEMIS nu recuperează TVA → TVA = cost real pe achiziții (aplicat automat).", E, NUM0)
inp("el_route", "Arhitectura electronică: 1 = PCB propriu (ESP32-S3-WROOM-1 + panou AMOLED 1,75″), 2 = placă Waveshare ESP32-S3-Touch-AMOLED-1.75",
    [2, 1, 1, 1], "cod", "02-MANUFACTURING §11: PCB custom de la ~1k buc. La 100 buc. NRE-ul PCB (~$15–30k) nu se justifică → placa Waveshare [estimare]. Atenție: cu placa Waveshare corpul e S-P0 (25,65 mm, LiPo 503030 ~450 mAh [estimare]; docs/12 §2.3), nu produsul de 23 mm", E, NUM0, True)
inp("pcba_sel", "Referință PCBA externalizat: 1 = JLCPCB (Asia), 2 = EMS România", 2, "cod",
    "Lanțul recomandat în cercetare (15.10.2026): Felix EMS / EMS-Electra fac PCBA + box build + flash/test. JLCPCB = cel mai ieftin reper public.", "input", NUM0, True)
inp("days", "Zile lucrătoare pe an", 220, "zile", "Cercetare T1 (15.10.2026): 220 zile/an", E, NUM0)
inp("shift_h", "Ore pe schimb", 8, "h", "Standard", "input", NUM0)
inp("oee", "Eficiență (timp productiv din schimb)", 0.85, "%", "Cercetare T1: ~408 min productive / schimb (85 %)", E, PCT)
inp("shift_min", "Minute productive pe schimb", "=[shift_h]*60*[oee]", "min", "Formulă", "calcul", NUM0)
inp("hours_fte", "Ore productive pe an per normă întreagă (FTE)", "=[days]*[shift_h]*[oee]", "h", "Formulă", "calcul", NUM0)
inp("max_shifts", "Număr maxim de schimburi pe utilaj", 2, "schimburi", "Cercetare: T1 se justifică pe 2 schimburi; al 3-lea schimb nemodelat", E, NUM0)
inp("target_util", "Utilizare țintă a stațiilor (rezervă pentru opriri)", 0.8, "%", "[estimare]", E, PCT)
inp("batches", "Loturi de producție pe an", [1, 4, 8, 12], "loturi", "[estimare] 1 lot la pilot, apoi trimestrial → lunar", E, NUM0)
inp("colours", "Culori de anodizare active", [2, 5, 5, 5], "culori", "02-MANUFACTURING §3: Founders = argint + grafit; 5 culori ulterior", V, NUM0)
inp("thr_vol", "Volum de la care atelierul are laser, dulap Li-ion și raft de rodaj proprii", 500, "unit./an", "[estimare] sub prag: marcare la furnizor/FabLab", E, NUM0)

isec("2. BOM per unitate, mărimea S (AMOLED 1,75″ 466×466, 63×70,8×23 mm; docs/size-s.json)")
inp("display_usd", "Panou rotund AMOLED 1,75\" 466×466 CO5300 (QSPI) + touch on-cell", [17, 10, 9.5, 9], "$/buc",
    "docs/12 §1.2: Tailor-Pixels TOH175XRT-02CG $9–17 la eșantion (https://tailorpixels.com/product/1-75-inch-amoled-round-on-cell-touch-466x466-mipi-qspi/, 20.10.2026); "
    "docs/12 §3.1 folosește $10 la 1.000; MOQ doar prin RFQ (NoseDisplay, Lianxun) [estimare]", E, USD)
inp("mcu_usd", "Modul ESP32-S3-WROOM-1-N16R8", [4.6, 3.46, 3.40, 3.30], "$/buc",
    "LCSC C2913202: ~$5,16–5,54 @1, ~$3,46 @650+, ~$3,40 @1.300+ (https://www.lcsc.com/product-detail/WiFi-Modules_Espressif-Systems-ESP32-S3-WROOM-1-N16R8_C2913202.html, 15.10.2026); 100 și 20k [estimare]", L, USD)
inp("other_el_usd", "Restul componentelor PCB (PMIC, IMU, codec+amp, 2 mic MEMS, USB-C, pogo, ~120 pasive)", [7, 5, 4.2, 3.6], "$/buc",
    "[estimare] nu există încă BOM pentru PCB-ul custom", E, USD)
inp("pcb_bare_usd", "PCB gol 4 straturi rotund ~Ø46 mm", [1.6, 0.8, 0.56, 0.44], "$/buc", "[estimare] docs/12 §3.1: $0,8 la 1.000 (M: $1,0); reper prototip AISLER 14 € + 0,13 €/cm² (vault)", E, USD)
inp("ws_board_usd", "Placă Waveshare ESP32-S3-Touch-AMOLED-1.75 (doar la arhitectura 2; are 2 microfoane, ES7210 + ES8311, difuzor în kit)", 29.99, "$/buc",
    "docs/12 §1.1: $29,99–39,99 pe waveshare.com, verificat 20.10.2026 (https://www.waveshare.com/esp32-s3-touch-amoled-1.75.htm); split pe variante nepublicat", V, USD)
inp("mic_lei", "Microfon extern (arhitectura 2) — la S nu trebuie: placa AMOLED-1.75 are 2 microfoane", 0, "lei cu TVA", "docs/12 §1.1 [V]; la M era INMP441, Bitmi 20,99 lei", V, NUM2)
inp("amp_lei", "Amplificator extern (arhitectura 2) — la S nu trebuie: codecul ES8311 e pe placă", 0, "lei cu TVA", "docs/12 §1.1 [V]; la M era MAX98357A, Robofun 44,18 lei", V, NUM2)
inp("battery_usd", "Celulă LiPo 603040 750 mAh cu PCM (la 100 buc. cu placa Waveshare: 503030 ~450 mAh, S-P0)", [3.45, 1.50, 1.40, 1.35], "$/buc",
    "docs/12 §3.1: 503030 ≈ 3,00 € la 100 (S-P0) [estimare]; 603040 $1,5 la 1.000 [estimare]; listarea A&S Power 603040 750 mAh (HKTDC). Cere UN38.3 + IEC 62133.", E, USD)
inp("speaker_eur", "Difuzor 15×11 mm (la 100 buc.: difuzorul din kitul plăcii Waveshare)", [0, 0.8, 0.6, 0.5], "€/buc", "docs/12 §3.1: la 100 fără difuzor separat (kit); volume mari [estimare]", E, EUR2)
inp("glass_usd", "Sticlă frontală plată Ø52, 2.5D, întărită chimic, print negru", [6.0, 2.2, 1.4, 0.9], "$/buc",
    "docs/12 §3.1: × ~0,75 față de M (Ø74 → Ø52, setup dominant). Felix Glass $2,88–8,11; Hengping $0,60–1,90 @MOQ 100; Saida $0,20–3,00 @MOQ 100 (https://saidaglass.en.made-in-china.com/product/ZdbJyzMDEYWm/, listări 2–2,5 ani) — ales în interval [estimare]", E, USD)
inp("mech_eur", "Mecanice mici (șuruburi, magneți, spumă, monedă PCB contacte)", [3.5, 2.0, 1.5, 1.25], "€/buc", "[estimare] docs/12 §3.1 (−0,5 € față de M); BOM.csv @25 ≈ 4,9 €", E, EUR2)
inp("cable_eur", "Cablu USB-C", [2.2, 1.2, 0.9, 0.8], "€/buc", "[estimare] BOM.csv P0-15: 2,5 € @25", E, EUR2)
inp("chassis_eur", "Șasiu + bază/picior din polimer", [4.5, 2.6, 1.1, 0.6], "€/buc", "[estimare] docs/12 §3.1: 4,5 € @100, 2,6 € @1.000 (M: 6 / 3,5); BOM.csv P0-10", E, EUR2)
inp("ou_eur", "Oul OU (carcasă + electronică de încărcare)", [15, 10, 6.7, 5], "€/buc",
    "[estimare] docs/12 §3.1: 15 € @100, 10 € @1.000 (M: 18 / 12); BOM P0-13/14: 33 € @25 (SLA); 02-MANUFACTURING §9: $8–12 la 10k", E, EUR2)
inp("pack_eur", "Ambalaj (cutie rigidă, certificat, ghid, etichetă)", [9, 5, 3.0, 2.2], "€/buc",
    "[estimare] docs/12 §3.1: 9 € @100, 5 € @1.000 (cutie mai mică); BOM P0-16 8 € + F-03/F-04 2 € @25; Web2Print București de la 25 buc., preț la cerere", E, EUR2)
inp("freight_pct", "Transport din Asia (% din valoarea mărfii)", [0.10, 0.06, 0.04, 0.03], "%", "[estimare] BOM P0-17: DHL ~$14/kg; la volum maritim/feroviar", E, PCT)
inp("duty_el_pct", "Taxă vamală medie componente electronice", 0.02, "%", "[estimare] multe componente au 0 %", E, PCT)
inp("duty_shell_pct", "Taxă vamală carcase aluminiu", 0.06, "%", "02-MANUFACTURING §2 / BOM P0-17: ~6 % (HS 7616/8529 după broker; risc antidumping 7616 99 90)", V, PCT)

isec("3. Procese externalizate (scenariul A și reperele de comparație)")
inp("jlc_setup_usd", "JLCPCB taxă setup PCBA (Standard, două fețe)", 51.12, "$/lot", "https://jlcpcb.com/help/article/pcb-assembly-price (15.10.2026)", O, USD)
inp("jlc_stencil_usd", "JLCPCB stencil", 8.21, "$/lot", "idem", O, USD)
inp("jlc_feeder_usd", "JLCPCB taxă feeder per piesă „extended”", 3.07, "$/piesă/lot", "idem (Economic; aplicat și la Standard [estimare])", O, USD)
inp("ext_parts", "Piese „extended” distincte pe placă", 10, "buc", "[estimare]", E, NUM0)
inp("joints", "Puncte de lipire pe placă", 400, "puncte", "[estimare] ~150 componente", E, NUM0)
inp("comps", "Componente plasate pe placă", 150, "buc", "[estimare] cercetare T2: 150–250", E, NUM0)
inp("jlc_joint_usd", "JLCPCB preț per punct de lipire", [0.0016, 0.0016, 0.0014, 0.0012], "$/punct", "JLCPCB: $0,0016/punct, Standard scade până la $0,0012 (tierul exact [estimare])", O, NUM4)
inp("ems_pcba_eur", "EMS România: asamblare PCBA per placă (fără componente)", [12, 4, 2.5, 1.8], "€/placă",
    "[estimare] Felix EMS / EMS-Electra / ICCO nu publică prețuri; o ofertă UE de 6 plăci = €312,81 (forum, cercetare). Cere RFQ cu Gerber+BOM+CPL.", E, EUR2, True)
inp("cnc_buy_eur", "Prelucrare CNC set S (față + spate), externalizat, fără finisaj", [55, 23, 17.5, 14.3], "€/set",
    "[estimare] = valorile M (85 / 35 / 27 / 22) × 0,65, factorul carcasei S externe din docs/12 §3.1 și size-s.json cnc.external_shell_factor_vs_M, același în modelul de obiectiv al campaniei (suprafață × 0,50, semifabricat × 0,40, taxe fixe); Vault: S @25 = 92 €/set cu finisaj (BOM P0-12); 1k China $25–45/set pentru S (02-MANUFACTURING §11); "
    "curba PREMSA 6061 ~100×70×40: $118 @1 / $61 @25 / $54 @100 (https://premsaindustries.com/en/aluminum-machining). La ≥10k dosarul trece pe ambutisare 5052 (nemodelat).", E, EUR2, True)
inp("blast_buy_eur", "Sablare externalizată (glass bead) per set S", [1.3, 1.0, 0.8, 0.65], "€/set", "[estimare] M × 0,65 (docs/12 §3.1)", E, EUR2)
inp("anod_base_eur", "Anodizare tip II colorată + sigilare, per set S (fără taxa de lot)", [3.25, 2.6, 2.3, 1.95], "€/set", "[estimare] M (5 / 4 / 3,5 / 3) × 0,65 (docs/12 §3.1); Anorom/Alvi/ARSAT nu publică prețuri", E, EUR2)
inp("anod_lot_usd", "Taxă minimă per lot de anodizare (per culoare)", 100, "$/lot", "Regulă din industrie: minim ≥$100 per lot (cercetare 15.10.2026) [estimare]", E, USD)
inp("golden_eur", "Golden sample per culoare", 100, "€/culoare", "Vault BOM B-11: 100 € [E]", E, EUR0)
inp("laser_buy_eur", "Marcare laser externalizată (serie + CE/WEEE)", [2, 1.2, 0.8, 0.6], "€/buc", "Vault BOM F-01: 2 € @25 [E]; FabLab Jilava 0,20 €/cm² (vault)", E, EUR2)
inp("transport_anod_eur", "Transport intern la anodizator RO și retur (scenariile C, D)", 0.5, "€/set", "[estimare]", E, EUR2)
inp("bb_eur", "EMS România: box build (asamblare + flash + test funcțional + ambalare)", [15, 10, 8, 7], "€/buc",
    "[estimare] ~20–30 min la ~20–25 €/h; fără preț public. RFQ: Felix EMS (office@felix-ems.ro), EMS-Electra (office@ems-electra.ro)", E, EUR2, True)
inp("a_int_min", "Scenariul A: minute interne per unitate (QC final + ambalare/expediere)", 5, "min", "[estimare]", E, NUM0)

isec("4. Atelier T0: asamblare, flash, calibrare, test, QC, ambalare")
inp("asm_min", "Manoperă internă per unitate (toți pașii manuali)", [45, 25, 20, 15], "min/unit.",
    "02-MANUFACTURING §6: ~45 min în serie la început; cercetare: 15–25 min cu fixturi [estimare]", E, NUM0, True)
inp("test_min", "Ciclu jig de test funcțional", 4, "min", "[estimare] cercetare: 3–5 min", E, NUM1)
inp("flash_min", "Ciclu flash (per port)", 2, "min", "[estimare]; Espressif Flash Download Tool mod Factory, multi-canal (https://docs.espressif.com/projects/esp-test-tools/en/latest/esp8266/production_stage/tools/flash_download_tool.html)", E, NUM1)
inp("flash_ports", "Porturi flash în paralel", 4, "porturi", "[estimare] 4–8 porturi", E, NUM0)
inp("burnin_min", "Rodaj (burn-in) per unitate", 10, "min", "02-MANUFACTURING §7: 10 min demo fără reboot", V, NUM0)
inp("burnin_slots", "Locuri pe raftul de rodaj", 20, "locuri", "[estimare]", E, NUM0)
inp("laser_min", "Ciclu marcare laser", 1, "min", "[estimare] cercetare: 30–90 s", E, NUM1)
inp("scrap_base", "Rebut / rezervă pe materiale cumpărate", 0.03, "%", "[estimare] vault folosește +10 % la 25 buc.; la serie 3 %", E, PCT)
inp("qc_tech", "Tehnician QC/test (normă)", [0, 0, 1, 1], "FTE", "[estimare] cercetare: la 10k/an 2–3 operatori + 1 QC", E, NUM1)
inp("warehouse_n", "Gestionar/logistică (normă)", [0, 0, 0, 1], "FTE", "[estimare]", E, NUM1)
inp("space_B", "Suprafață atelier T0 (incl. stoc)", [0, 60, 150, 300], "m²",
    "Cercetare: T0 40–60 m²; faza 2 ~200 m² pentru 5–6k/an; pilotul pe bancul fondatorului, fără hală [estimare]", E, NUM0)
inp("kwh_B", "Consum electric atelier T0", [0, 1000, 2000, 3000], "kWh/lună", "Cercetare: 1.000–3.000 kWh/lună [estimare]", E, NUM0)
inp("bench_eur", "Banc de lucru ESD (Treston Concept Ergo)", 2495, "€/buc", "€1.595–3.395 (https://www.wrepair.com/product/esd-workstation-180x75cm/) — mijlocul intervalului", L, EUR0)
inp("jig_dev_usd", "Jig de test pogo Fixturfab Dev Pro (sub prag)", 1799, "$", "https://fixturfab.com/fixtures (15.10.2026)", L, USD)
inp("jig_prod_usd", "Jig de test pogo Fixturfab Production (peste prag)", 7399, "$", "idem", L, USD)
inp("flash_eur", "Stație flash (hub USB + cabluri + jig)", 300, "€", "[estimare] software Espressif gratuit", E, EUR0)
inp("laser_eur", "Laser fibră MOPA Gweike G6", 4469, "€", "https://shop.gweikecloud.com/products/g6-mopa-30w-60w-100w-fiber-laser-marking-engraving-machine", L, EUR0)
inp("liion_cab_eur", "Dulap Li-ion tip 90 Düperthal XL", 4660, "€", "https://www.lion-care.com/en/Dueperthal-BATTERY-standard-line-XL-storage-cabinet/DUPSHSBLSXL1 (fără TVA)", L, EUR0)
inp("liion_small_eur", "Container ignifug mic pentru celule (sub prag)", 400, "€", "[estimare]", E, EUR0)
inp("burnin_eur", "Raft de rodaj + surse USB", 1000, "€", "[estimare]", E, EUR0)
inp("tools_base_eur", "Scule, IT, imprimantă etichete, cântar 0,1 g", 1500, "€", "[estimare]", E, EUR0)
inp("tools_bench_eur", "Accesorii ESD + scule per banc", 500, "€/banc", "Kit ESD 386–702 lei (https://www.electronic-mag.ro/statii-de-lucru-esd/19582-...) + brățări, ionizator [estimare]", E, EUR0)
inp("setup_eur", "Înființare (autorizație mediu + consultant, dosar SSM/PSI)", 1500, "€",
    "Autorizație mediu 500 lei (Ord. 1108/2007), SSM 450 lei/funcție + PSI 500 lei (ZOTAS); restul consultant [estimare]", E, EUR0)
inp("dep_light", "Amortizare echipamente ușoare (T0)", 3, "ani", "[estimare]", E, NUM0)
inp("dep_heavy", "Amortizare utilaje (CNC, SMT)", 5, "ani", "[estimare] cercetare: 5 ani", E, NUM0)

isec("5. Personal și spațiu")
inp("sal_op_lei", "Salariu operator asamblare (brut)", 4500, "lei/lună", "Paylab 4.050–6.785; minim 4.325 brut din 1.07.2026 (HG 146/2026)", L, LEI)
inp("sal_tech_lei", "Salariu tehnician electronică / QC / SMT (brut)", 6500, "lei/lună", "WageIndicator 2026: 5.303–7.714 brut", L, LEI)
inp("sal_prog_lei", "Salariu programator CNC (brut), primul operator CNC", 10800, "lei/lună", "[estimare] Indeed: de la 6.500 net → ~10.500–11.100 brut", E, LEI)
inp("sal_cncop_lei", "Salariu operator CNC (brut)", 6000, "lei/lună", "meseriile.ro / Jooble București 2026: ~4.000–7.000", L, LEI)
inp("sal_wh_lei", "Salariu gestionar depozit", 4150, "lei/lună", "OLX Sector 4 (30.09.2026): 4.000–4.300", L, LEI)
inp("cam_rate", "Contribuția asiguratorie pentru muncă (angajator)", 0.0225, "%", "[de verificat] CAM 2,25 % (Cod fiscal art. 220^1)", E, PCT)
inp("rent_m2", "Chirie spațiu mic de producție", 6.0, "€/m²/lună", "[estimare] cercetare 6–8 €/m²; publi24 Ilfov 13–15.10.2026: 3,5–8,5 €/m² (https://www.publi24.ro/anunturi/imobiliare/de-inchiriat/spatii-comerciale/hala-industriala/ilfov/)", E, EUR2)
inp("service_m2", "Servicii / mentenanță spațiu", 0.7, "€/m²/lună", "[estimare] 0,5–0,9 €/m²", E, EUR2)
inp("elec_lei_kwh", "Energie electrică all-in (fără TVA)", 1.4, "lei/kWh", "[estimare] 1,2–1,6; POSF 792,93 lei/MWh doar energie, S1 2026 (https://posf.ro/comparator/files/furnizori/1767174801Oferta-noncasnici-Business-Stabil-01.01.2026.pdf)", E, NUM2)

isec("6. Permise, asigurări, SSM")
inp("ins_A", "Asigurări scenariul A (RC produs)", 1000, "€/an", "[estimare] 500–2.000 €/an; doar Groupama RC generală de la €160/an (2022)", E, EUR0)
inp("ins_B", "Asigurări scenariile B–D (RC produs + bunuri)", 1500, "€/an", "[estimare]", E, EUR0)
inp("epr_fixed", "EPR: OIREP + declarații AFM (fix)", 600, "€/an", "[estimare] înregistrări ANMAP 2 × 500 lei (EEE + baterii)", E, EUR0)
inp("env_visa_lei", "Viză anuală autorizație de mediu (CAEN 2640 e pe lista Ord. 1798/2007)", 100, "lei/an", "Ord. 1150/2020 art. 8(1)", O, LEI)
inp("ssm_small_lei", "SSM + PSI externalizat, 1–5 angajați", 120, "lei/lună", "ZOTAS (10.10.2026) https://zotas.ro/ghiduri/cat-costa-ssm-firma-mica/", L, LEI)
inp("ssm_emp_lei", "SSM + PSI externalizat, peste 5 angajați", 22, "lei/angajat/lună", "idem (6–29 angajați)", L, LEI)
inp("med_lei", "Medicina muncii", 100, "lei/pers./an", "50–100 lei (avizemedicale.ro)", L, LEI)
inp("payroll_lei", "Salarizare / contabilitate per angajat", 50, "lei/angajat/lună", "[estimare]", E, LEI)
inp("psi_eur", "PSI: stingătoare, verificări", 200, "€/an", "[estimare]", E, EUR0)
inp("soft_B_eur", "Software trasabilitate / MES ușor / etichete", 600, "€/an", "[estimare]", E, EUR0)

isec("7. Celulă CNC proprie (T1) — anodizarea rămâne externă")
inp("cnc_list_usd", "Haas VF-2, preț listă SUA", 70995, "$", "https://machinetoolindex.com/machines/haas-vf-2 (verificat 2.10.2026); preț UE doar la cerere (HFO). Alternativă second-hand: VF-2SSYT 2012 €32.500 + TVA", L, NUM0, True)
inp("cnc_extra_pct", "Opțiuni + transport UE + instalare (% peste listă)", 0.20, "%", "[estimare]", E, PCT)
inp("cnc_tooling_eur", "Scule, menghine, fixturi, palpator per mașină", 17500, "€", "[estimare] cercetare: €10–25k", E, EUR0)
inp("blast_cab_lei", "Cabină de sablare 350 L (Big Red Jack)", 4905, "lei cu TVA", "Mtools, ofertă 1–31.10.2026 (https://www.mtools.ro/...dulap-de-sablare-cu-cabina-350-litri-si-aspirator-big-red-jack)", L, LEI)
inp("compressor_lei", "Compresor cu șurub 7,5 kW Fiac New Silver 10", 21901, "lei cu TVA", "Dedeman (https://www.dedeman.ro/ro/compresor-aer-cu-surub-cu-ulei-fiac-new-silver-10-7-5-kw-10-cp/p/1066403)", L, LEI)
inp("ultrasonic_eur", "Baie cu ultrasunete 30 L profesională", 2320, "€", "Multilab (+TVA) https://www.multilab.ro/bai/baie_curatare_ultrasunete.html", L, EUR0)
inp("cnc_install_eur", "Racord trifazic 25–40 kVA, pardoseală, zonă șpan", 5000, "€", "[estimare]", E, EUR0)
inp("cam_usd", "Autodesk Fusion (CAM comercial)", 680, "$/an", "https://vagon.io/blog/fusion-360-pricing (prețuri Autodesk SUA, 11.08.2026)", L, USD)
inp("maint_pct", "Mentenanță utilaje (% din capex/an)", 0.03, "%", "[estimare]", E, PCT)
inp("ct_S", "Timp ciclu CNC set S (2 carcase)", 24, "min/set", "docs/size-s.json cnc.cycle_min_per_set = 24 [estimare] (20–30; M 45 × 0,53, docs/12 §3.2); de verificat prin simulare CAM pe STEP-ul S de 23 mm, care nu există încă", E, NUM0, True)
inp("ct_Malt", "Timp ciclu CNC set M (prototipul, comparație)", 45, "min/set", "size-s.json cnc.m_reference = 45 [estimare] (cercetare: 30–60 min)", E, NUM0)
inp("mat_kg_S", "Semifabricat aluminiu per set S", 0.4, "kg/set", "docs/size-s.json cnc.billet_kg_per_set = 0,4 (0,36 kg calculat + 11 %, docs/12 §3.2)", E, NUM2)
inp("mat_kg_Malt", "Semifabricat aluminiu per set M (prototipul, comparație)", 1.0, "kg/set", "size-s.json cnc.m_reference = 1,0 [estimare] (cercetare: ~0,49 kg/jumătate)", E, NUM2)
inp("mat_lei_kg", "Bară aluminiu (reper 6082-T6 Ø60)", 41.5, "lei/kg cu TVA", "Baduc 326,86 lei/m cu TVA la 7,63 kg/m (https://www.baduc.ro/metalurgice/4113-bara-rotunda-aluminiu--=-60-mm); 6061-T6 doar la cerere", L, NUM2)
inp("tool_wear_eur", "Uzură scule per set S", 0.8, "€/set", "[estimare] M 1,5 € × 24/45 min (cercetare: €1–2 pe set M)", E, EUR2)
inp("cnc_kw", "Putere medie CNC în lucru", 9, "kW", "[estimare] cercetare: 8–10 kW", E, NUM1)
inp("blast_cons_eur", "Consumabile sablare per set", 0.3, "€/set", "[estimare] glass bead ~$47–59 / sac 50 lb", E, EUR2)
inp("scrap_cnc", "Rebut CNC în casă", 0.05, "%", "[estimare]", E, PCT)
inp("m2_cnc", "Suprafață per mașină CNC", 50, "m²", "[estimare] Speedio 1,6×2,1 m; VF-2 3,5 t + acces, șpan", E, NUM0)
inp("m2_cnc_common", "Suprafață comună CNC (sablare, compresor, debavurare)", 30, "m²", "[estimare]", E, NUM0)
inp("waste_eur", "Contract deșeuri periculoase (emulsie 12 01 09*)", 600, "€/an", "[estimare] CAEN 2562 e și el pe lista Ord. 1798/2007", E, EUR0)
inp("mpo", "Mașini CNC deservite de un operator", 2, "mașini", "[estimare]", E, NUM0)
inp("f_cnc_Malt", "M (comparație): factor preț CNC externalizat față de S", 1.54, "×", "[estimare] 1 / 0,65 (docs/12 §3.1)", E, NUM2)
inp("f_anod_Malt", "M (comparație): factor anodizare/sablare față de S", 1.54, "×", "[estimare] 1 / 0,65 (suprafață × 2, dar taxe fixe pe bucată)", E, NUM2)

isec("8. Linie SMT proprie (T2)")
inp("printer_eur", "Imprimantă pastă NeoDen FP2636", 1028.50, "€", "https://neodentech.eu/contents/en-uk/p55129_NEODEN-FP2636-Stencil-Printer-for-frameless-stencils.html", L, EUR2)
inp("pnp_eur", "Pick-and-place NeoDen4 cu conveyor", 11977.79, "€", "PrintTec EU (snippet căutare; https://www.neodentech.eu/contents/en-uk/d8_NEODEN4.html dădea 503)", L, EUR2)
inp("reflow_usd", "Cuptor reflow NeoDen IN6", 3500, "$", "$2.399–5.499 (https://neoden-solution.com/collections/reflow-ovens/products/neoden-in6-reflow-oven) — mijloc [estimare]", E, USD)
inp("aoi_usd", "AOI offline NeoDen ND880", 15999, "$", "https://www.neodensmt.com/automatic-inspection-machine/nd880-offline-aoi-machine.html", L, USD)
inp("msl_eur", "Dulap uscat MSL", 1500, "€", "[estimare, neverificat]", E, EUR0)
inp("feeders_eur", "Feedere suplimentare", 3000, "€", "[estimare]", E, EUR0)
inp("smt_install_eur", "Extracție fum, ESD, instalare", 2000, "€", "[estimare]", E, EUR0)
inp("cph_real", "Viteză reală P&P", 2500, "comp./h", "[estimare] 4.000 CPH nominal × ~60 %", E, NUM0)
inp("handling_min", "Încărcare/descărcare per placă", 0.5, "min", "[estimare]", E, NUM1)
inp("smt_var_eur", "Pastă, consumabile per placă", 0.20, "€/placă", "[estimare]", E, EUR2)
inp("yield_in", "Pierderi de randament SMT în casă", 0.02, "%", "[estimare]", E, PCT)
inp("yield_out", "Pierderi de randament la EMS", 0.005, "%", "[estimare]", E, PCT)
inp("smt_kw", "Putere medie linie SMT", 1.7, "kW", "[estimare] reflow ~700 W în lucru + P&P + AOI", E, NUM1)
inp("m2_smt", "Suprafață linie SMT", 50, "m²", "[estimare] cercetare: +40–60 m²", E, NUM0)
inp("smt_cons_eur", "Stenciluri, piese de schimb", 300, "€/an", "[estimare]", E, EUR0)

isec("9. NRE produs (comun tuturor scenariilor; nu ține de fabrică)")
inp("pcb_design_usd", "Proiectare PCB custom + PCBA NRE (doar arhitectura 1)", 22500, "$", "02-MANUFACTURING §11: $15–30k [E]", E, NUM0)
inp("glass_nre_usd", "NRE sticlă custom + laminare", 10000, "$", "02-MANUFACTURING §11: $5–15k [E]", E, NUM0)
inp("ou_tool_eur", "Matrițe OU", [0, 5000, 18300, 18300], "€", "[estimare] 1k: aluminiu Protolabs; ≥5k: oțel $16–26k (02-MANUFACTURING §9)", E, EUR0)
inp("nre_years", "Ani pe care se amortizează NRE", 3, "ani", "[estimare]", E, NUM0)

# ------------------------------------------------------------------ Scenarii
SC.column_dimensions["A"].width = 16
SC.column_dimensions["B"].width = 62
for c in VC:
    SC.column_dimensions[c].width = 14
SC.column_dimensions["G"].width = 70
SC["A1"] = "SCENARII: cost per unitate, capex și costuri fixe (mărimea S, EUR fără TVA; TVA apare ca cost doar sub plafonul de scutire)"
SC["A1"].font = F_H
SC["A2"] = ("A = totul externalizat (EMS face PCBA + box build, CNC + anodizare + sticlă la parteneri; noi QC final + ambalare). "
            "B = atelier T0 propriu (asamblare, flash, calibrare, test, QC, ambalare). C = B + celulă CNC proprie. D = C + linie SMT proprie. "
            "Anodizarea rămâne externă în toate.")
SC["A2"].font = F_NOTE
SC["A2"].alignment = WRAP
SC.merge_cells("A2:G2")
SC.row_dimensions[2].height = 40
SC.freeze_panes = "C5"
for i, h in enumerate(["Cheie", "Linie", "", "", "", "", "Explicație"]):
    c = SC.cell(row=4, column=i + 1, value=h)
    c.font = F_B
    c.fill = FILL_HDR
for col in VC:
    SC[f"{col}4"] = f"={ipref('vol', col)}"
    SC[f"{col}4"].number_format = '#,##0" buc/an"'
    SC[f"{col}4"].font = F_LINK
    SC[f"{col}4"].fill = FILL_HDR
sc_row = [5]


def ssec(title):
    sc_row[0] += 1
    sec(SC, sc_row[0], title, 7)
    sc_row[0] += 1


def srow(name, label, tpl, fmt=EUR2, note="", bold=False, total=False):
    r = sc_row[0]
    SROW[name] = r
    SC.cell(row=r, column=1, value=name).font = F_NOTE
    SC.cell(row=r, column=2, value=label).font = F_B if bold else F_N
    for col in VC:
        cell = SC[f"{col}{r}"]
        cell.value = T(tpl, col, SROW)
        cell.number_format = fmt
        cell.font = F_B if bold else F_N
        if total:
            cell.fill = FILL_TOT
    if total:
        SC.cell(row=r, column=2).fill = FILL_TOT
    if note:
        n = SC.cell(row=r, column=7, value=note)
        n.font = F_NOTE
    sc_row[0] += 1


ssec("Comun tuturor scenariilor")
srow("vol", "Volum", "=[vol]", NUM0)
srow("route", "Arhitectura electronică (1 = PCB propriu, 2 = placă Waveshare)", "=[el_route]", NUM0)
srow("turnover_lei", "Cifră de afaceri estimată", "={vol}*[price_retail]*[fx_eur_lei]", LEI)
srow("vatflag", "Firma e plătitoare de TVA? (1 = da)", "=IF({turnover_lei}>[vat_threshold_lei],1,0)", NUM0, "peste plafon înregistrarea e obligatorie → TVA deductibil")
srow("vatcost", "TVA nerecuperabil aplicat achizițiilor", "=[vat_rate]*(1-{vatflag})", PCT)
srow("hourly_op", "Cost operator per oră productivă", "=[sal_op_lei]*(1+[cam_rate])*12/[fx_eur_lei]/[hours_fte]", EUR2)
srow("el_comp", "Electronică (panou + modul + componente + PCB gol, sau placa Waveshare AMOLED-1.75)",
     "=IF({route}=1,([display_usd]+[mcu_usd]+[other_el_usd]+[pcb_bare_usd])*[fx_usd_eur],[ws_board_usd]*[fx_usd_eur]+([mic_lei]+[amp_lei])/(1+[vat_rate])/[fx_eur_lei])")
srow("batt", "Baterie LiPo 750 mAh (~450 mAh la S-P0)", "=[battery_usd]*[fx_usd_eur]")
srow("glass", "Sticlă frontală 2.5D", "=[glass_usd]*[fx_usd_eur]")
srow("small", "Difuzor + mecanice mici + cablu", "=[speaker_eur]+[mech_eur]+[cable_eur]")
srow("imp_el", "Subtotal piese importate", "={el_comp}+{batt}+{glass}+{small}")
srow("log_el", "Transport + taxă vamală piese importate", "={imp_el}*((1+[freight_pct])*(1+[duty_el_pct])-1)")
srow("local", "Piese locale (OU, ambalaj, șasiu/bază)", "=[ou_eur]+[pack_eur]+[chassis_eur]")
srow("bom", "BOM total livrat (fără carcasă Al și fără manoperă)", "={imp_el}+{log_el}+{local}", EUR2, bold=True, total=True)
srow("pcba_jlc", "PCBA la JLCPCB per placă (manoperă + setup/lot, livrat)",
     "=IF({route}=1,([joints]*[jlc_joint_usd]+([jlc_setup_usd]+[jlc_stencil_usd]+[jlc_feeder_usd]*[ext_parts])*[batches]/{vol})*[fx_usd_eur]*(1+[freight_pct])*(1+[duty_el_pct]),0)")
srow("pcba_ems", "PCBA la EMS România per placă", "=IF({route}=1,[ems_pcba_eur],0)")
srow("pcba_buy", "PCBA externalizat folosit (după selector)", "=IF([pcba_sel]=1,{pcba_jlc},{pcba_ems})", EUR2, bold=True)
srow("anod_set", "Anodizare per set (bază + taxe de lot × culori × loturi / volum)", "=[anod_base_eur]+[anod_lot_usd]*[fx_usd_eur]*[colours]*[batches]/{vol}")
srow("shell_buy", "Carcasă S externalizată (CNC + sablare + anodizare, livrată)",
     "=([cnc_buy_eur]+[blast_buy_eur]+{anod_set})*(1+[freight_pct])*(1+[duty_shell_pct])", EUR2, bold=True)
srow("mat_eur_kg", "Aluminiu net de TVA", "=[mat_lei_kg]/(1+[vat_rate])/[fx_eur_lei]", EUR2, "€/kg")
srow("shell_make_cnc", "CNC în casă: material + scule + energie + sablare, cu rebut",
     "=([mat_kg_S]*{mat_eur_kg}+[tool_wear_eur]+[cnc_kw]*[ct_S]/60*[elec_lei_kwh]/[fx_eur_lei]+[blast_cons_eur])*(1+[scrap_cnc])")
srow("shell_make", "Carcasă S în casă: variabil (CNC propriu + anodizare RO + transport)", "={shell_make_cnc}+{anod_set}+[transport_anod_eur]", EUR2, bold=True)
srow("board_val", "Valoarea componentelor de pe PCB (pentru pierderi SMT)", "=IF({route}=1,([mcu_usd]+[other_el_usd]+[pcb_bare_usd])*[fx_usd_eur],0)")
srow("smt_make", "SMT în casă: variabil per placă (consumabile + pierderi suplimentare)", "=IF({route}=1,[smt_var_eur]+([yield_in]-[yield_out])*{board_val},0)", EUR2, bold=True)

ssec("Capacitate și personal (calculat din volum)")
srow("asm_h", "Ore de manoperă internă T0 pe an", "={vol}*[asm_min]/60", NUM0)
srow("asm_fte_raw", "Operatori asamblare necesari (FTE exact)", "={asm_h}/[hours_fte]", NUM2)
srow("asm_fte", "Operatori plătiți (sub 0,5 = part-time/fondator plătit la oră; altfel rotunjit la 0,5)", "=IF({asm_fte_raw}<0.5,{asm_fte_raw},CEILING({asm_fte_raw},0.5))", NUM2)
srow("benches", "Bancuri ESD", "=MAX(1,CEILING({asm_fte_raw},1))", NUM0)
srow("jigs", "Jig-uri de test", "=MAX(1,CEILING({vol}*[test_min]/60/[hours_fte]/[target_util],1))", NUM0)
srow("hc_B", "Angajați T0 (număr de persoane)", "=CEILING({asm_fte},1)+[qc_tech]+[warehouse_n]", NUM0)
srow("jig_price", "Preț jig de test", "=IF({vol}<[thr_vol],[jig_dev_usd],[jig_prod_usd])*[fx_usd_eur]", EUR0)
srow("golden", "Golden samples (per culoare)", "=[colours]*[golden_eur]", EUR0)
srow("cnc_cap", "Capacitate CNC: seturi S / mașină / schimb / an", "=[shift_min]/[ct_S]*[days]", NUM0)
srow("cnc_m", "Mașini CNC necesare", "=CEILING({vol}/({cnc_cap}*[max_shifts]),1)", NUM0)
srow("cnc_sh", "Schimburi CNC", "=MIN([max_shifts],CEILING({vol}/({cnc_cap}*{cnc_m}),1))", NUM0)
srow("cnc_ops", "Operatori CNC (primul = programator)", "={cnc_sh}*CEILING({cnc_m}/[mpo],1)", NUM0)
srow("cnc_util", "Utilizare CNC", "={vol}/({cnc_cap}*{cnc_m}*{cnc_sh})", PCT)
srow("cnc_machine_eur", "Cost mașină CNC instalată", "=[cnc_list_usd]*[fx_usd_eur]*(1+[cnc_extra_pct])", EUR0)
srow("cnc_common", "Echipamente comune CNC (sablare, compresor, ultrasunete, instalare)", "=([blast_cab_lei]+[compressor_lei])/[fx_eur_lei]+[ultrasonic_eur]+[cnc_install_eur]", EUR0)
srow("cnc_capex", "Capex celulă CNC (net)", "={cnc_m}*({cnc_machine_eur}+[cnc_tooling_eur])+{cnc_common}", EUR0)
srow("smt_cap", "Capacitate SMT: plăci / linie / schimb / an", "=[shift_min]/([comps]/[cph_real]*60+[handling_min])*[days]", NUM0)
srow("smt_lines", "Linii SMT", "=IF({route}=1,CEILING({vol}/({smt_cap}*[max_shifts]),1),1)", NUM0)
srow("smt_sh", "Schimburi SMT", "=IF({route}=1,MIN([max_shifts],CEILING({vol}/({smt_cap}*{smt_lines}),1)),1)", NUM0)
srow("smt_techs", "Tehnicieni SMT", "={smt_sh}*{smt_lines}", NUM0)
srow("smt_capex_line", "Capex per linie SMT (net)", "=[printer_eur]+[pnp_eur]+([reflow_usd]+[aoi_usd])*[fx_usd_eur]+[msl_eur]+[feeders_eur]+[smt_install_eur]", EUR0)
srow("smt_capex", "Capex SMT (net)", "={smt_lines}*{smt_capex_line}", EUR0)
srow("hc_C", "Angajați scenariul C", "={hc_B}+{cnc_ops}", NUM0)
srow("hc_D", "Angajați scenariul D", "={hc_C}+{smt_techs}", NUM0)


def perm_tpl(hc, extra=""):
    return ("=[ins_B]+[epr_fixed]+[env_visa_lei]/[fx_eur_lei]+(IF({%s}<=5,[ssm_small_lei]*12,[ssm_emp_lei]*12*{%s})"
            "+[med_lei]*{%s}+[payroll_lei]*12*{%s})/[fx_eur_lei]+[psi_eur]+[soft_B_eur]%s") % (hc, hc, hc, hc, extra)


def summary(p, var_parts, scrap_base_parts, vat_parts):
    srow(f"{p}_scrap", "Rebut / rezervă", "=(" + "+".join("{%s}" % x for x in scrap_base_parts) + ")*[scrap_base]")
    srow(f"{p}_vat", "TVA nerecuperabil pe achiziții (doar sub plafon)", "=(" + "+".join("{%s}" % x for x in vat_parts + [f"{p}_scrap"]) + ")*{vatcost}")
    srow(f"{p}_var", "COST VARIABIL / unitate", "=" + "+".join("{%s}" % x for x in var_parts + [f"{p}_scrap", f"{p}_vat"]), EUR2, bold=True, total=True)
    srow(f"{p}_fix_u", "Cost fix / unitate", "={%s_fixed}/{vol}" % p)
    srow(f"{p}_total", "COST TOTAL / unitate (fără NRE produs)", "={%s_var}+{%s_fix_u}" % (p, p), EUR2, bold=True, total=True)
    srow(f"{p}_nre", "NRE produs / unitate (comun: PCB, sticlă, matrițe OU, pe 3 ani)",
         "=((IF({route}=1,[pcb_design_usd],0)+[glass_nre_usd])*[fx_usd_eur]+[ou_tool_eur])/([nre_years]*{vol})")
    srow(f"{p}_total_nre", "COST TOTAL / unitate cu NRE", "={%s_total}+{%s_nre}" % (p, p), EUR2, bold=True)
    srow(f"{p}_price", "Preț net încasat (fără TVA dacă firma e plătitoare)", "=IF({vatflag}=1,[price_retail]/(1+[vat_rate]),[price_retail])")
    srow(f"{p}_margin", "Marjă brută / unitate (cu NRE)", "={%s_price}-{%s_total_nre}" % (p, p), EUR2, bold=True)
    srow(f"{p}_margin_pct", "Marjă brută %", "=IF({%s_price}=0,0,{%s_margin}/{%s_price})" % (p, p, p), PCT)


# ---- Scenario A
ssec("Scenariul A — totul externalizat (lanț de producție)")
srow("A_capex", "CAPEX (jig de test predat la EMS + golden samples)", "=({jigs}*{jig_price}+{golden})*(1+{vatcost})", EUR0, bold=True, total=True)
srow("A_rent", "Chirie + utilități", "=0", EUR0, "fără hală: stocul stă la EMS / 3PL")
srow("A_sal", "Salarii", "=0", EUR0, "QC final plătit la oră, în costul variabil")
srow("A_dep", "Amortizare", "={A_capex}/[dep_light]", EUR0)
srow("A_perm", "Asigurări, EPR", "=[ins_A]+[epr_fixed]", EUR0)
srow("A_fixed", "COSTURI FIXE / an", "={A_rent}+{A_sal}+{A_dep}+{A_perm}", EUR0, bold=True, total=True)
srow("A_v_bom", "BOM livrat", "={bom}")
srow("A_v_pcba", "PCBA externalizat", "={pcba_buy}")
srow("A_v_shell", "Carcasă externalizată", "={shell_buy}")
srow("A_v_laser", "Marcare laser la furnizor", "=[laser_buy_eur]")
srow("A_v_bb", "Box build la EMS (asamblare + flash + test + ambalare)", "=[bb_eur]")
srow("A_v_lab", "QC final + expediere internă", "=[a_int_min]/60*{hourly_op}")
summary("A", ["A_v_bom", "A_v_pcba", "A_v_shell", "A_v_laser", "A_v_bb", "A_v_lab"],
        ["A_v_bom", "A_v_pcba", "A_v_shell"], ["A_v_bom", "A_v_pcba", "A_v_shell", "A_v_laser", "A_v_bb"])

# ---- Scenario B
ssec("Scenariul B — atelier T0 propriu (asamblare + flash + calibrare + test + QC + ambalare)")
srow("B_capex", "CAPEX T0",
     "=({benches}*[bench_eur]+{jigs}*{jig_price}+[flash_eur]+IF({vol}>=[thr_vol],[laser_eur]+[liion_cab_eur]+[burnin_eur],[liion_small_eur])"
     "+[tools_base_eur]+[tools_bench_eur]*{benches}+[setup_eur]+{golden})*(1+{vatcost})", EUR0, bold=True, total=True)
srow("B_rent", "Chirie + servicii", "=[space_B]*([rent_m2]+[service_m2])*12*(1+{vatcost})", EUR0)
srow("B_util", "Energie atelier", "=[kwh_B]*12*[elec_lei_kwh]/[fx_eur_lei]*(1+{vatcost})", EUR0)
srow("B_sal", "Salarii (operatori + QC + gestionar, cu CAM)", "=({asm_fte}*[sal_op_lei]+[qc_tech]*[sal_tech_lei]+[warehouse_n]*[sal_wh_lei])*(1+[cam_rate])*12/[fx_eur_lei]", EUR0)
srow("B_dep", "Amortizare", "={B_capex}/[dep_light]", EUR0)
srow("B_perm", "Permise, asigurări, SSM, medicina muncii, EPR, software", perm_tpl("hc_B"), EUR0)
srow("B_fixed", "COSTURI FIXE / an", "={B_rent}+{B_util}+{B_sal}+{B_dep}+{B_perm}", EUR0, bold=True, total=True)
srow("B_v_bom", "BOM livrat", "={bom}")
srow("B_v_pcba", "PCBA externalizat", "={pcba_buy}")
srow("B_v_shell", "Carcasă externalizată", "={shell_buy}")
srow("B_v_laser", "Marcare laser (externă sub prag, apoi laser propriu)", "=IF({vol}>=[thr_vol],0,[laser_buy_eur])")
summary("B", ["B_v_bom", "B_v_pcba", "B_v_shell", "B_v_laser"],
        ["B_v_bom", "B_v_pcba", "B_v_shell"], ["B_v_bom", "B_v_pcba", "B_v_shell", "B_v_laser"])

# ---- Scenario C
ssec("Scenariul C — T0 + celulă CNC proprie (anodizare externă)")
srow("C_capex", "CAPEX T0 + CNC", "={B_capex}+{cnc_capex}*(1+{vatcost})", EUR0, bold=True, total=True)
srow("C_rent", "Chirie + servicii (T0 + CNC)", "={B_rent}+({cnc_m}*[m2_cnc]+[m2_cnc_common])*([rent_m2]+[service_m2])*12*(1+{vatcost})", EUR0)
srow("C_util", "Energie atelier (energia CNC e în costul variabil)", "={B_util}", EUR0)
srow("C_sal", "Salarii (T0 + programator + operatori CNC)", "={B_sal}+([sal_prog_lei]+({cnc_ops}-1)*[sal_cncop_lei])*(1+[cam_rate])*12/[fx_eur_lei]", EUR0)
srow("C_dep", "Amortizare (T0 pe 3 ani, CNC pe 5 ani)", "={B_dep}+{cnc_capex}*(1+{vatcost})/[dep_heavy]", EUR0)
srow("C_perm", "Permise, asigurări, SSM, deșeuri, mentenanță, CAM",
     perm_tpl("hc_C", "+[waste_eur]+[maint_pct]*{cnc_m}*{cnc_machine_eur}+[cam_usd]*[fx_usd_eur]"), EUR0)
srow("C_fixed", "COSTURI FIXE / an", "={C_rent}+{C_util}+{C_sal}+{C_dep}+{C_perm}", EUR0, bold=True, total=True)
srow("C_v_bom", "BOM livrat", "={bom}")
srow("C_v_pcba", "PCBA externalizat", "={pcba_buy}")
srow("C_v_shell", "Carcasă în casă (variabil) + anodizare RO", "={shell_make}")
srow("C_v_laser", "Marcare laser", "=IF({vol}>=[thr_vol],0,[laser_buy_eur])")
summary("C", ["C_v_bom", "C_v_pcba", "C_v_shell", "C_v_laser"],
        ["C_v_bom", "C_v_pcba"], ["C_v_bom", "C_v_pcba", "C_v_shell", "C_v_laser"])

# ---- Scenario D
ssec("Scenariul D — T0 + CNC + linie SMT proprie")
srow("D_capex", "CAPEX T0 + CNC + SMT", "={C_capex}+{smt_capex}*(1+{vatcost})", EUR0, bold=True, total=True)
srow("D_rent", "Chirie + servicii", "={C_rent}+{smt_lines}*[m2_smt]*([rent_m2]+[service_m2])*12*(1+{vatcost})", EUR0)
srow("D_util", "Energie (atelier + SMT)", "={C_util}+[smt_kw]*[shift_h]*[days]*{smt_sh}*{smt_lines}*[elec_lei_kwh]/[fx_eur_lei]*(1+{vatcost})", EUR0)
srow("D_sal", "Salarii (C + tehnicieni SMT)", "={C_sal}+{smt_techs}*[sal_tech_lei]*(1+[cam_rate])*12/[fx_eur_lei]", EUR0)
srow("D_dep", "Amortizare", "={C_dep}+{smt_capex}*(1+{vatcost})/[dep_heavy]", EUR0)
srow("D_perm", "Permise, asigurări, SSM, deșeuri, mentenanță, CAM, consumabile SMT",
     perm_tpl("hc_D", "+[waste_eur]+[maint_pct]*({cnc_m}*{cnc_machine_eur}+{smt_capex})+[cam_usd]*[fx_usd_eur]+[smt_cons_eur]"), EUR0)
srow("D_fixed", "COSTURI FIXE / an", "={D_rent}+{D_util}+{D_sal}+{D_dep}+{D_perm}", EUR0, bold=True, total=True)
srow("D_v_bom", "BOM livrat (componentele PCB le cumpărăm noi)", "={bom}")
srow("D_v_pcba", "SMT în casă (variabil)", "={smt_make}")
srow("D_v_shell", "Carcasă în casă (variabil) + anodizare RO", "={shell_make}")
srow("D_v_laser", "Marcare laser", "=IF({vol}>=[thr_vol],0,[laser_buy_eur])")
summary("D", ["D_v_bom", "D_v_pcba", "D_v_shell", "D_v_laser"],
        ["D_v_bom", "D_v_pcba"], ["D_v_bom", "D_v_pcba", "D_v_shell", "D_v_laser"])

# ------------------------------------------------------------------ Break-even
BE.column_dimensions["A"].width = 14
BE.column_dimensions["B"].width = 52
for i in range(3, 17):
    BE.column_dimensions[get_column_letter(i)].width = 13
BE["A1"] = "BREAK-EVEN: de la ce volum bate producția proprie externalizarea (CNC și SMT)"
BE["A1"].font = F_H
BE["A2"] = ("Comparație pe proces izolat, cu firma plătitoare de TVA (la aceste volume e obligatoriu). "
            "Prețul de cumpărare între volumele din Ipoteze e interpolat logaritmic; peste 20.000 rămâne la valoarea de 20.000. "
            "Costul fix propriu crește în trepte (a doua tură, încă o mașină/linie, încă un operator).")
BE["A2"].font = F_NOTE
BE["A2"].alignment = WRAP
BE.merge_cells("A2:P2")
BE.row_dimensions[2].height = 32
be_row = [4]


def brow(name, label, tpl, fmt=EUR2, bold=False):
    r = be_row[0]
    BROW[name] = r
    BE.cell(row=r, column=1, value=name).font = F_NOTE
    BE.cell(row=r, column=2, value=label).font = F_B if bold else F_N
    for col in VC:
        cell = BE[f"{col}{r}"]
        cell.value = T(tpl, col, BROW)
        cell.number_format = fmt
        cell.font = F_B if bold else F_N
    be_row[0] += 1


def bsec(title):
    be_row[0] += 1
    sec(BE, be_row[0], title, 16)
    be_row[0] += 1


bsec("1. Valori pe treptele de volum")
brow("tv", "Volum (treaptă)", "=[vol]", NUM0, True)
brow("S_buy", "CNC S: carcasă externalizată livrată (€/set)", "={S:shell_buy}")
brow("S_make", "CNC S: carcasă în casă, variabil (€/set)", "={S:shell_make}")
brow("anod_set", "Anodizare per set S", "={S:anod_set}")
brow("Mc_buy", "CNC M (comparație): carcasă externalizată livrată (€/set)",
     "=([cnc_buy_eur]*[f_cnc_Malt]+([blast_buy_eur]+{anod_set})*[f_anod_Malt])*(1+[freight_pct])*(1+[duty_shell_pct])")
brow("Mc_make", "CNC M (comparație): carcasă în casă, variabil (€/set)",
     "=([mat_kg_Malt]*{S:mat_eur_kg}+[tool_wear_eur]*[ct_Malt]/[ct_S]+[cnc_kw]*[ct_Malt]/60*[elec_lei_kwh]/[fx_eur_lei]+[blast_cons_eur]*[f_anod_Malt])*(1+[scrap_cnc])"
     "+{anod_set}*[f_anod_Malt]+[transport_anod_eur]")
brow("ems", "SMT: PCBA la EMS România (€/placă)", "=[ems_pcba_eur]")
brow("jlc", "SMT: PCBA la JLCPCB livrat (€/placă)",
     "=([joints]*[jlc_joint_usd]+([jlc_setup_usd]+[jlc_stencil_usd]+[jlc_feeder_usd]*[ext_parts])*[batches]/{tv})*[fx_usd_eur]*(1+[freight_pct])*(1+[duty_el_pct])")
brow("smt_make", "SMT: în casă, variabil (€/placă)", "=[smt_var_eur]+([yield_in]-[yield_out])*([mcu_usd]+[other_el_usd]+[pcb_bare_usd])*[fx_usd_eur]")

# scalar helper cells (column C)
bsec("2. Costuri fixe de bază (o mașină / o linie, un schimb)")
scal = {}


def bscal(name, label, formula, fmt=EUR0):
    r = be_row[0]
    BE.cell(row=r, column=1, value=name).font = F_NOTE
    BE.cell(row=r, column=2, value=label).font = F_N
    c = BE[f"C{r}"]
    c.value = T(formula, "C", BROW)
    c.number_format = fmt
    c.font = F_N
    scal[name] = f"'Break-even'!$C${r}"
    be_row[0] += 1


bscal("mach", "Mașină CNC instalată", "=[cnc_list_usd]*[fx_usd_eur]*(1+[cnc_extra_pct])")
bscal("cnc_common", "Echipamente comune CNC", "=([blast_cab_lei]+[compressor_lei])/[fx_eur_lei]+[ultrasonic_eur]+[cnc_install_eur]")
bscal("emp_over", "Cost SSM + medicina muncii + salarizare per angajat suplimentar / an", "=([ssm_emp_lei]*12+[med_lei]+[payroll_lei]*12)/[fx_eur_lei]")
bscal("op_prog", "Programator CNC, cost anual", "=[sal_prog_lei]*(1+[cam_rate])*12/[fx_eur_lei]")
bscal("op_cnc", "Operator CNC, cost anual", "=[sal_cncop_lei]*(1+[cam_rate])*12/[fx_eur_lei]")
bscal("space_cost", "Chirie + servicii per m² / an", "=([rent_m2]+[service_m2])*12", EUR2)
bscal("capS", "Capacitate CNC S: seturi / mașină / schimb / an", "=[shift_min]/[ct_S]*[days]", NUM0)
bscal("capMc", "Capacitate CNC M (comparație): seturi / mașină / schimb / an", "=[shift_min]/[ct_Malt]*[days]", NUM0)
bscal("smt_line", "Capex linie SMT", "=[printer_eur]+[pnp_eur]+([reflow_usd]+[aoi_usd])*[fx_usd_eur]+[msl_eur]+[feeders_eur]+[smt_install_eur]")
bscal("smt_cap", "Capacitate SMT: plăci / linie / schimb / an", "=[shift_min]/([comps]/[cph_real]*60+[handling_min])*[days]", NUM0)
bscal("tech", "Tehnician SMT, cost anual", "=[sal_tech_lei]*(1+[cam_rate])*12/[fx_eur_lei]")


def cnc_fixed(m, s, o):
    """formula text for CNC fixed annual cost given cell refs for machines, shifts, operators"""
    return (f"({m}*({scal['mach']}+{ipref('cnc_tooling_eur','C')})+{scal['cnc_common']})/{ipref('dep_heavy','C')}"
            f"+{scal['op_prog']}+({o}-1)*{scal['op_cnc']}+{o}*{scal['emp_over']}"
            f"+({m}*{ipref('m2_cnc','C')}+{ipref('m2_cnc_common','C')})*{scal['space_cost']}"
            f"+{ipref('maint_pct','C')}*{m}*{scal['mach']}+{ipref('cam_usd','C')}*{ipref('fx_usd_eur','C')}+{ipref('waste_eur','C')}")


def smt_fixed(lines, s, techs):
    return (f"{lines}*{scal['smt_line']}/{ipref('dep_heavy','C')}+{techs}*({scal['tech']}+{scal['emp_over']})"
            f"+{lines}*{ipref('m2_smt','C')}*{scal['space_cost']}+{ipref('maint_pct','C')}*{lines}*{scal['smt_line']}"
            f"+{ipref('smt_kw','C')}*{ipref('shift_h','C')}*{ipref('days','C')}*{s}*{lines}*{ipref('elec_lei_kwh','C')}/{ipref('fx_eur_lei','C')}"
            f"+{ipref('smt_cons_eur','C')}")


bscal("F_cnc1", "Cost fix anual celulă CNC (1 mașină, 1 schimb, 1 programator)", "=" + cnc_fixed("1", "1", "1"))
bscal("F_smt1", "Cost fix anual linie SMT (1 linie, 1 schimb, 1 tehnician)", "=" + smt_fixed("1", "1", "1"))

bsec("3. Break-even analitic pe trepte (o mașină / o linie, un schimb): N* = cost fix / (preț cumpărare − variabil propriu)")
brow("be_S", "CNC S: volum de break-even (seturi/an)", f"=IF({{S_buy}}-{{S_make}}<=0,\"niciodată\",{scal['F_cnc1']}/({{S_buy}}-{{S_make}}))", NUM0, True)
brow("be_S_ok", "… încape într-o mașină pe un schimb? (1 = da)", f"=IF(ISNUMBER({{be_S}}),IF({{be_S}}<={scal['capS']},1,0),0)", NUM0)
brow("be_Mc", "CNC M (comparație): volum de break-even (seturi/an)", f"=IF({{Mc_buy}}-{{Mc_make}}<=0,\"niciodată\",{scal['F_cnc1']}/({{Mc_buy}}-{{Mc_make}}))", NUM0, True)
brow("be_Mc_ok", "… încape într-o mașină pe un schimb? (1 = da)", f"=IF(ISNUMBER({{be_Mc}}),IF({{be_Mc}}<={scal['capMc']},1,0),0)", NUM0)
brow("be_ems", "SMT vs EMS România: volum de break-even (plăci/an)", f"=IF({{ems}}-{{smt_make}}<=0,\"niciodată\",{scal['F_smt1']}/({{ems}}-{{smt_make}}))", NUM0, True)
brow("be_jlc", "SMT vs JLCPCB: volum de break-even (plăci/an)", f"=IF({{jlc}}-{{smt_make}}<=0,\"niciodată\",{scal['F_smt1']}/({{jlc}}-{{smt_make}}))", NUM0, True)

tier_vols = f"'Break-even'!$C${BROW['tv']}:$F${BROW['tv']}"


def interp(price_row, vcell, icell):
    rng = f"'Break-even'!$C${BROW[price_row]}:$F${BROW[price_row]}"
    return (f"IF({icell}>=4,INDEX({rng},1,4),INDEX({rng},1,{icell})+(INDEX({rng},1,{icell}+1)-INDEX({rng},1,{icell}))"
            f"*LN({vcell}/INDEX({tier_vols},1,{icell}))/LN(INDEX({tier_vols},1,{icell}+1)/INDEX({tier_vols},1,{icell})))")


BE_RESULTS = {}


def cnc_grid(title, buy_row, make_row, cap_ref, key):
    bsec(title)
    heads = ["Volum (seturi/an)", "Treaptă", "Cumpărat €/set", "Cumpărat €/an", "Mașini", "Schimburi", "Operatori",
             "Fix propriu €/an", "Variabil propriu €/set", "Propriu €/an", "Propriu €/set", "Economie €/an", "Propriu mai ieftin?"]
    r0 = be_row[0]
    for i, h in enumerate(heads):
        c = BE.cell(row=r0, column=i + 1, value=h)
        c.font = F_B
        c.fill = FILL_HDR
        c.alignment = WRAP
    be_row[0] += 1
    vols = [250, 500, 1000, 1500, 2000, 2500, 3000, 4000, 5000, 7500, 10000, 15000, 20000]
    first = be_row[0]
    for v in vols:
        r = be_row[0]
        BE[f"A{r}"] = v
        BE[f"A{r}"].font = F_IN
        BE[f"B{r}"] = f"=MATCH(A{r},{tier_vols},1)"
        BE[f"C{r}"] = "=" + interp(buy_row, f"A{r}", f"B{r}")
        BE[f"D{r}"] = f"=A{r}*C{r}"
        BE[f"E{r}"] = f"=CEILING(A{r}/({cap_ref}*{ipref('max_shifts','C')}),1)"
        BE[f"F{r}"] = f"=MIN({ipref('max_shifts','C')},CEILING(A{r}/({cap_ref}*E{r}),1))"
        BE[f"G{r}"] = f"=F{r}*CEILING(E{r}/{ipref('mpo','C')},1)"
        BE[f"H{r}"] = "=" + cnc_fixed(f"E{r}", f"F{r}", f"G{r}")
        BE[f"I{r}"] = "=" + interp(make_row, f"A{r}", f"B{r}")
        BE[f"J{r}"] = f"=H{r}+A{r}*I{r}"
        BE[f"K{r}"] = f"=J{r}/A{r}"
        BE[f"L{r}"] = f"=D{r}-J{r}"
        BE[f"M{r}"] = f"=IF(J{r}<D{r},1,0)"
        for cc, fm in zip("ABCDEFGHIJKLM", [NUM0, NUM0, EUR2, EUR0, NUM0, NUM0, NUM0, EUR0, EUR2, EUR0, EUR2, EUR0, NUM0]):
            BE[f"{cc}{r}"].number_format = fm
            if cc != "A":
                BE[f"{cc}{r}"].font = F_N
        be_row[0] += 1
    last = be_row[0] - 1
    r = be_row[0]
    BE[f"B{r}"] = "Primul volum din grilă la care producția proprie e mai ieftină"
    BE[f"B{r}"].font = F_B
    BE[f"C{r}"] = f"=IFERROR(INDEX(A{first}:A{last},MATCH(1,M{first}:M{last},0)),\"peste 20.000\")"
    BE[f"C{r}"].number_format = NUM0
    BE[f"C{r}"].font = F_B
    BE[f"C{r}"].fill = FILL_TOT
    BE_RESULTS[key] = f"'Break-even'!$C${r}"
    be_row[0] += 1
    r = be_row[0]
    BE[f"B{r}"] = "Volume din grilă unde e mai ieftin (număr din 13)"
    BE[f"C{r}"] = f"=SUM(M{first}:M{last})"
    BE_RESULTS[key + "_n"] = f"'Break-even'!$C${r}"
    be_row[0] += 1


def smt_grid():
    bsec("6. Grilă SMT (linie NeoDen4 + AOI) vs EMS România și vs JLCPCB")
    heads = ["Volum (plăci/an)", "Treaptă", "EMS RO €/placă", "JLC €/placă", "Linii", "Schimburi", "Tehnicieni",
             "Fix propriu €/an", "Variabil propriu €/placă", "Propriu €/an", "Propriu €/placă", "EMS €/an", "JLC €/an", "Bate EMS?", "Bate JLC?"]
    r0 = be_row[0]
    for i, h in enumerate(heads):
        c = BE.cell(row=r0, column=i + 1, value=h)
        c.font = F_B
        c.fill = FILL_HDR
        c.alignment = WRAP
    be_row[0] += 1
    vols = [500, 1000, 2500, 5000, 7500, 10000, 15000, 20000, 25000, 30000, 40000, 50000, 60000]
    first = be_row[0]
    cap = scal["smt_cap"]
    for v in vols:
        r = be_row[0]
        BE[f"A{r}"] = v
        BE[f"A{r}"].font = F_IN
        BE[f"B{r}"] = f"=MATCH(A{r},{tier_vols},1)"
        BE[f"C{r}"] = "=" + interp("ems", f"A{r}", f"B{r}")
        BE[f"D{r}"] = "=" + interp("jlc", f"A{r}", f"B{r}")
        BE[f"E{r}"] = f"=CEILING(A{r}/({cap}*{ipref('max_shifts','C')}),1)"
        BE[f"F{r}"] = f"=MIN({ipref('max_shifts','C')},CEILING(A{r}/({cap}*E{r}),1))"
        BE[f"G{r}"] = f"=E{r}*F{r}"
        BE[f"H{r}"] = "=" + smt_fixed(f"E{r}", f"F{r}", f"G{r}")
        BE[f"I{r}"] = "=" + interp("smt_make", f"A{r}", f"B{r}")
        BE[f"J{r}"] = f"=H{r}+A{r}*I{r}"
        BE[f"K{r}"] = f"=J{r}/A{r}"
        BE[f"L{r}"] = f"=A{r}*C{r}"
        BE[f"M{r}"] = f"=A{r}*D{r}"
        BE[f"N{r}"] = f"=IF(J{r}<L{r},1,0)"
        BE[f"O{r}"] = f"=IF(J{r}<M{r},1,0)"
        for cc, fm in zip("ABCDEFGHIJKLMNO", [NUM0, NUM0, EUR2, EUR2, NUM0, NUM0, NUM0, EUR0, EUR2, EUR0, EUR2, EUR0, EUR0, NUM0, NUM0]):
            BE[f"{cc}{r}"].number_format = fm
            if cc != "A":
                BE[f"{cc}{r}"].font = F_N
        be_row[0] += 1
    last = be_row[0] - 1
    for lbl, colf, key in [("Primul volum la care SMT propriu bate EMS România", "N", "smt_ems"),
                           ("Primul volum la care SMT propriu bate JLCPCB", "O", "smt_jlc")]:
        r = be_row[0]
        BE[f"B{r}"] = lbl
        BE[f"B{r}"].font = F_B
        BE[f"C{r}"] = f"=IFERROR(INDEX(A{first}:A{last},MATCH(1,{colf}{first}:{colf}{last},0)),\"peste 60.000\")"
        BE[f"C{r}"].number_format = NUM0
        BE[f"C{r}"].font = F_B
        BE[f"C{r}"].fill = FILL_TOT
        BE_RESULTS[key] = f"'Break-even'!$C${r}"
        be_row[0] += 1
    for lbl, colf in [("Volume din grilă unde SMT propriu bate EMS (număr din 13)", "N"), ("Volume din grilă unde SMT propriu bate JLCPCB (număr din 13)", "O")]:
        r = be_row[0]
        BE[f"B{r}"] = lbl
        BE[f"C{r}"] = f"=SUM({colf}{first}:{colf}{last})"
        be_row[0] += 1


cnc_grid("4. Grilă CNC mărimea S (Haas VF-2 nou; anodizare externă în ambele variante)", "S_buy", "S_make", scal["capS"], "cnc_S")
cnc_grid("5. Grilă CNC mărimea M, prototipul (comparație: ciclu 45 min, 1,0 kg, preț extern ×1,54)", "Mc_buy", "Mc_make", scal["capMc"], "cnc_Mc")
smt_grid()

# ------------------------------------------------------------------ Capacitate
CP.column_dimensions["A"].width = 34
CP.column_dimensions["B"].width = 12
for c in "CDEFGHIJK":
    CP.column_dimensions[c].width = 13
CP.column_dimensions["L"].width = 50
CP["A1"] = "CAPACITATE: unități pe schimb per stație, necesar de stații și gâtuirea liniei"
CP["A1"].font = F_H
CP["A2"] = ("Unități/schimb = minute productive pe schimb × posturi paralele / timp ciclu. Necesar = volum / (capacitate anuală pe 1 schimb × utilizare țintă), rotunjit în sus. "
            "Pentru CNC și SMT necesarul vine din Scenarii (cu 2 schimburi înainte de a cumpăra încă o mașină).")
CP["A2"].font = F_NOTE
CP["A2"].alignment = WRAP
CP.merge_cells("A2:L2")
CP.row_dimensions[2].height = 30
heads = ["Stație", "Timp ciclu (min)", "Posturi paralele", "Unități / schimb", "Unități / an (1 schimb)",
         "Necesar @100", "Necesar @1.000", "Necesar @5.000", "Necesar @20.000", "Utilizare @20.000", "", "Notă"]
for i, h in enumerate(heads):
    c = CP.cell(row=4, column=i + 1, value=h)
    c.font = F_B
    c.fill = FILL_HDR
    c.alignment = WRAP
need_cols = ["F", "G", "H", "I"]
stations = [
    ("Banc asamblare (1 operator)", f"={ipref('asm_min','D')}", "1", "Ciclul = manopera totală la 1.000 buc./an; necesarul folosește minutele per volum (Ipoteze 4). Gâtuirea reală a T0 = oamenii.", "asm"),
    ("Stație flash", f"={ipref('flash_min','C')}", f"={ipref('flash_ports','C')}", "Espressif Flash Download Tool, mod Factory", None),
    ("Jig test funcțional", f"={ipref('test_min','C')}", "1", "Fixturfab; cutie ecranată pentru RSSI", None),
    ("Raft rodaj (burn-in)", f"={ipref('burnin_min','C')}", f"={ipref('burnin_slots','C')}", "Nesupravegheat", None),
    ("Laser MOPA marcare", f"={ipref('laser_min','C')}", "1", "Serie + CE/WEEE după anodizare", None),
]
r = 5
t0_first = r
for name, ct, par, note, kind in stations:
    CP[f"A{r}"] = name
    CP[f"B{r}"] = ct
    CP[f"C{r}"] = 1 if par == "1" else par
    CP[f"D{r}"] = f"={ipref('shift_min','C')}*C{r}/B{r}"
    CP[f"E{r}"] = f"=D{r}*{ipref('days','C')}"
    for j, col in enumerate(VC):
        nc = need_cols[j]
        if kind == "asm":
            CP[f"{nc}{r}"] = f"=Scenarii!{col}{SROW['asm_fte_raw']}"
        else:
            CP[f"{nc}{r}"] = f"=MAX(1,CEILING({ipref('vol', col)}/(E{r}*{ipref('target_util','C')}),1))"
    if kind == "asm":
        CP[f"J{r}"] = f"=I{r}/MAX(1,CEILING(I{r},1))"
    else:
        CP[f"J{r}"] = f"={ipref('vol','F')}/(E{r}*IF(I{r}<1,1,CEILING(I{r},1)))"
    CP[f"L{r}"] = note
    r += 1
t0_last = r - 1
# CNC, SMT rows
CP[f"A{r}"] = "CNC mărimea S (1 mașină)"
CP[f"B{r}"] = f"={ipref('ct_S','C')}"
CP[f"C{r}"] = 1
CP[f"D{r}"] = f"={ipref('shift_min','C')}*C{r}/B{r}"
CP[f"E{r}"] = f"=D{r}*{ipref('days','C')}"
for j, col in enumerate(VC):
    CP[f"{need_cols[j]}{r}"] = f"=Scenarii!{col}{SROW['cnc_m']}"
CP[f"J{r}"] = f"=Scenarii!F{SROW['cnc_util']}"
CP[f"L{r}"] = "Necesar = mașini (cu până la 2 schimburi). Gâtuirea scenariilor C/D."
cnc_r = r
r += 1
CP[f"A{r}"] = "CNC mărimea M, comparație (1 mașină)"
CP[f"B{r}"] = f"={ipref('ct_Malt','C')}"
CP[f"C{r}"] = 1
CP[f"D{r}"] = f"={ipref('shift_min','C')}*C{r}/B{r}"
CP[f"E{r}"] = f"=D{r}*{ipref('days','C')}"
for j, col in enumerate(VC):
    CP[f"{need_cols[j]}{r}"] = f"=CEILING({ipref('vol', col)}/(E{r}*{ipref('max_shifts','C')}),1)"
CP[f"J{r}"] = f"={ipref('vol','F')}/(E{r}*I{r}*{ipref('max_shifts','C')})"
CP[f"L{r}"] = "Comparație M: ciclu de ~1,9× mai lung → ~0,53× seturi pe mașină"
r += 1
CP[f"A{r}"] = "Linie SMT (NeoDen4 + reflow + AOI)"
CP[f"B{r}"] = f"={ipref('comps','C')}/{ipref('cph_real','C')}*60+{ipref('handling_min','C')}"
CP[f"C{r}"] = 1
CP[f"D{r}"] = f"={ipref('shift_min','C')}*C{r}/B{r}"
CP[f"E{r}"] = f"=D{r}*{ipref('days','C')}"
for j, col in enumerate(VC):
    CP[f"{need_cols[j]}{r}"] = f"=Scenarii!{col}{SROW['smt_lines']}"
CP[f"J{r}"] = f"={ipref('vol','F')}/(E{r}*Scenarii!F{SROW['smt_lines']}*Scenarii!F{SROW['smt_sh']})"
CP[f"L{r}"] = "Reflow-ul NeoDen IN6 nu e gâtuire la aceste volume"
smt_r = r
r += 1
for rr in range(5, r):
    CP[f"B{rr}"].number_format = NUM1
    CP[f"C{rr}"].number_format = NUM0
    CP[f"D{rr}"].number_format = NUM1
    CP[f"E{rr}"].number_format = NUM0
    for nc in need_cols:
        CP[f"{nc}{rr}"].number_format = NUM2 if rr == t0_first else NUM0
    CP[f"J{rr}"].number_format = PCT
    for cc in "ABCDEFGHIJ":
        CP[f"{cc}{rr}"].font = F_N
    CP[f"L{rr}"].font = F_NOTE
    CP[f"L{rr}"].alignment = WRAP
r += 1
CP[f"A{r}"] = "Gâtuirea T0 (stația cu cele mai puține unități/schimb)"
CP[f"A{r}"].font = F_B
CP[f"D{r}"] = f"=MIN(D{t0_first}:D{t0_last})"
CP[f"D{r}"].number_format = NUM1
CP[f"E{r}"] = f"=INDEX(A{t0_first}:A{t0_last},MATCH(D{r},D{t0_first}:D{t0_last},0))"
CP.merge_cells(f"E{r}:I{r}")
CP[f"D{r}"].fill = FILL_TOT
CP[f"E{r}"].fill = FILL_TOT
CP[f"E{r}"].font = F_B
cap_bneck_t0 = r
r += 1
CP[f"A{r}"] = "Gâtuirea scenariilor C/D (unități/schimb)"
CP[f"A{r}"].font = F_B
CP[f"D{r}"] = f"=MIN(D{t0_first}:D{cnc_r})"
CP[f"D{r}"].number_format = NUM1
CP[f"E{r}"] = f"=INDEX(A{t0_first}:A{cnc_r},MATCH(D{r},D{t0_first}:D{cnc_r},0))"
CP.merge_cells(f"E{r}:I{r}")
CP[f"D{r}"].fill = FILL_TOT
CP[f"E{r}"].fill = FILL_TOT
CP[f"E{r}"].font = F_B
cap_bneck_c = r
r += 2
CP[f"A{r}"] = "Personal necesar (persoane)"
CP[f"A{r}"].font = F_B
for j, col in enumerate(VC):
    CP[f"{need_cols[j]}{r}"] = f"={ipref('vol', col)}"
    CP[f"{need_cols[j]}{r}"].number_format = '#,##0" buc"'
    CP[f"{need_cols[j]}{r}"].font = F_B
r += 1
for lbl, key in [("Scenariul B (operatori + QC + gestionar)", "hc_B"), ("Scenariul C (+ CNC)", "hc_C"), ("Scenariul D (+ SMT)", "hc_D")]:
    CP[f"A{r}"] = lbl
    CP[f"A{r}"].font = F_N
    for j, col in enumerate(VC):
        CP[f"{need_cols[j]}{r}"] = f"=Scenarii!{col}{SROW[key]}"
        CP[f"{need_cols[j]}{r}"].number_format = NUM0
        CP[f"{need_cols[j]}{r}"].font = F_N
    r += 1

# ------------------------------------------------------------------ Rezultate
RZ.column_dimensions["A"].width = 6
RZ.column_dimensions["B"].width = 60
for c in VC:
    RZ.column_dimensions[c].width = 15
RZ.column_dimensions["G"].width = 60
RZ["A1"] = "REZULTATE: fabrică SOUL vs lanț de producție (mărimea S, EUR fără TVA)"
RZ["A1"].font = F_H
RZ["A2"] = ("Totul se calculează din foaia Ipoteze. Multe intrări sunt [estimare] până vin ofertele (RFQ): EMS RO, CNC, anodizare, sticlă, PCB custom. "
            "Fabrica (B–D) nu schimbă CE/RED, care e per produs (04-COMPLIANCE.md).")
RZ["A2"].font = F_NOTE
RZ["A2"].alignment = WRAP
RZ.merge_cells("A2:G2")
RZ.row_dimensions[2].height = 30
rz = [4]
SCN = [("A", "A — totul externalizat"), ("B", "B — atelier T0 (asamblare + test)"), ("C", "C — T0 + CNC propriu"), ("D", "D — T0 + CNC + SMT propriu")]


def rtable(title, key_suffix, fmt, best=None):
    r = rz[0]
    RZ[f"B{r}"] = title
    RZ[f"B{r}"].font = F_B
    RZ[f"B{r}"].fill = FILL_HDR
    for col in VC:
        RZ[f"{col}{r}"] = f"=Scenarii!{col}{SROW['vol']}"
        RZ[f"{col}{r}"].number_format = '#,##0" buc/an"'
        RZ[f"{col}{r}"].font = F_B
        RZ[f"{col}{r}"].fill = FILL_HDR
    r += 1
    first = r
    for p, lbl in SCN:
        RZ[f"A{r}"] = p
        RZ[f"B{r}"] = lbl
        RZ[f"A{r}"].font = F_N
        RZ[f"B{r}"].font = F_N
        for col in VC:
            RZ[f"{col}{r}"] = f"=Scenarii!{col}{SROW[p + key_suffix]}"
            RZ[f"{col}{r}"].number_format = fmt
            RZ[f"{col}{r}"].font = F_LINK
        r += 1
    last = r - 1
    if best:
        RZ[f"B{r}"] = best
        RZ[f"B{r}"].font = F_B
        for col in VC:
            RZ[f"{col}{r}"] = f"=INDEX($A${first}:$A${last},MATCH(MIN({col}{first}:{col}{last}),{col}{first}:{col}{last},0))"
            RZ[f"{col}{r}"].font = F_B
            RZ[f"{col}{r}"].fill = FILL_TOT
            RZ[f"{col}{r}"].alignment = Alignment(horizontal="center")
        r += 1
    rz[0] = r + 1
    return first


first_total = rtable("1. Cost total / unitate (fără NRE produs)", "_total", EUR2, "Cel mai ieftin scenariu")
rtable("2. Cost total / unitate cu NRE produs (PCB, sticlă, matrițe OU pe 3 ani)", "_total_nre", EUR2, "Cel mai ieftin scenariu")
rtable("3. Cost variabil / unitate", "_var", EUR2)
rtable("4. Capex (investiție inițială)", "_capex", EUR0)
rtable("5. Costuri fixe anuale (chirie, salarii, amortizare, permise/asigurări)", "_fixed", EUR0)
rtable("6. Marjă brută / unitate la prețul de €249 (cu NRE)", "_margin", EUR2)

r = rz[0]
RZ[f"B{r}"] = "7. Break-even: de la ce volum producția proprie bate externalizarea"
RZ[f"B{r}"].font = F_B
RZ[f"B{r}"].fill = FILL_HDR
RZ[f"C{r}"] = "Grilă"
RZ[f"D{r}"] = "Analitic @1.000"
RZ[f"E{r}"] = "Analitic @5.000"
RZ[f"F{r}"] = "Analitic @20.000"
for c in "CDEF":
    RZ[f"{c}{r}"].font = F_B
    RZ[f"{c}{r}"].fill = FILL_HDR
r += 1
be_lines = [
    ("CNC mărimea S (seturi/an)", "cnc_S", "be_S"),
    ("CNC mărimea M, comparație (seturi/an)", "cnc_Mc", "be_Mc"),
    ("SMT propriu vs EMS România (plăci/an)", "smt_ems", "be_ems"),
    ("SMT propriu vs JLCPCB (plăci/an)", "smt_jlc", "be_jlc"),
]
for lbl, gkey, akey in be_lines:
    RZ[f"B{r}"] = lbl
    RZ[f"B{r}"].font = F_N
    RZ[f"C{r}"] = f"={BE_RESULTS[gkey]}"
    RZ[f"C{r}"].number_format = NUM0
    RZ[f"C{r}"].font = F_LINK
    for c, bc in zip("DEF", "DEF"):
        RZ[f"{c}{r}"] = f"='Break-even'!{bc}{BROW[akey]}"
        RZ[f"{c}{r}"].number_format = NUM0
        RZ[f"{c}{r}"].font = F_LINK
    r += 1
RZ[f"B{r}"] = "Atelier T0 (B) vs box build la EMS (A), unități/an"
RZ[f"B{r}"].font = F_N
RZ[f"C{r}"] = "–"
RZ[f"C{r}"].alignment = Alignment(horizontal="center")
for c in "DEF":
    RZ[f"{c}{r}"] = (f"=IF(Scenarii!{c}{SROW['A_var']}-Scenarii!{c}{SROW['B_var']}<=0,\"niciodată\","
                     f"(Scenarii!{c}{SROW['B_fixed']}-Scenarii!{c}{SROW['A_fixed']})/(Scenarii!{c}{SROW['A_var']}-Scenarii!{c}{SROW['B_var']}))")
    RZ[f"{c}{r}"].number_format = NUM0
    RZ[f"{c}{r}"].font = F_LINK
bvsa_row = r
r += 1
RZ[f"B{r}"] = ("Grilă = primul volum (cu trepte reale: al 2-lea schimb, încă o mașină) la care propriul e mai ieftin. "
               "Analitic = cost fix pentru 1 mașină/linie pe 1 schimb împărțit la economia per bucată la prețurile treptei respective.")
RZ[f"B{r}"].font = F_NOTE
RZ[f"B{r}"].alignment = WRAP
RZ.merge_cells(f"B{r}:G{r}")
RZ.row_dimensions[r].height = 30
r += 2

RZ[f"B{r}"] = "8. Capex pe treaptă (net de TVA)"
RZ[f"B{r}"].font = F_B
RZ[f"B{r}"].fill = FILL_HDR
RZ[f"C{r}"] = "Capex €"
RZ[f"D{r}"] = "Capacitate / schimb"
RZ[f"C{r}"].font = F_B
RZ[f"D{r}"].font = F_B
RZ[f"C{r}"].fill = FILL_HDR
RZ[f"D{r}"].fill = FILL_HDR
r += 1
caps = [
    ("T0 atelier (configurația pentru 1.000 buc./an)", f"=Scenarii!D{SROW['B_capex']}", f"='Capacitate'!D{cap_bneck_t0}", "unități/operator/schimb (gâtuire: oamenii)"),
    ("T0 atelier (configurația pentru 20.000 buc./an)", f"=Scenarii!F{SROW['B_capex']}", None, ""),
    ("T1: + 1 mașină CNC Haas VF-2 + scule + echipamente comune", f"={scal['mach']}+{ipref('cnc_tooling_eur','C')}+{scal['cnc_common']}", f"={ipref('shift_min','C')}/{ipref('ct_S','C')}", "seturi S / schimb"),
    ("T1: fiecare mașină CNC în plus (cu scule)", f"={scal['mach']}+{ipref('cnc_tooling_eur','C')}", None, ""),
    ("T2: + 1 linie SMT (NeoDen4 + FP2636 + IN6 + AOI + MSL)", f"={scal['smt_line']}", f"={ipref('shift_min','C')}/('Capacitate'!B{smt_r})", "plăci / schimb"),
    ("Celulă CNC la 20.000 seturi S (mașini × capex)", f"=Scenarii!F{SROW['cnc_capex']}", f"=Scenarii!F{SROW['cnc_m']}", "mașini necesare"),
]
for lbl, f1, f2, unit in caps:
    RZ[f"B{r}"] = lbl
    RZ[f"B{r}"].font = F_N
    RZ[f"C{r}"] = f1
    RZ[f"C{r}"].number_format = EUR0
    RZ[f"C{r}"].font = F_LINK
    if f2:
        RZ[f"D{r}"] = f2
        RZ[f"D{r}"].number_format = NUM1
        RZ[f"D{r}"].font = F_LINK
        RZ[f"E{r}"] = unit
        RZ[f"E{r}"].font = F_NOTE
    r += 1
r += 1
# ---- RFQ thresholds
RZ[f"B{r}"] = "9. Praguri de ofertă pentru RFQ: peste aceste prețuri externe, varianta proprie devine mai ieftină"
RZ[f"B{r}"].font = F_B
RZ[f"B{r}"].fill = FILL_HDR
for col in VC:
    RZ[f"{col}{r}"] = f"=Scenarii!{col}{SROW['vol']}"
    RZ[f"{col}{r}"].number_format = '#,##0" buc/an"'
    RZ[f"{col}{r}"].font = F_B
    RZ[f"{col}{r}"].fill = FILL_HDR
r += 1
thr_rows = {}
for lbl, cur, num, extra, key in [
    ("Box build EMS (€/buc.) — ipoteza curentă", "bb", None, None, "bb_cur"),
    ("Box build EMS (€/buc.) — prag peste care atelierul T0 (B) e mai ieftin", "bb", ("B_total", "A_total"), "vat", "bb_thr"),
    ("Carcasă S externă livrată (€/set) — ipoteza curentă", "shell", None, None, "sh_cur"),
    ("Carcasă S externă livrată (€/set) — prag peste care CNC propriu (C vs B) e mai ieftin", "shell", ("C_total", "B_total"), "scrapvat", "sh_thr"),
    ("PCBA EMS (€/placă) — ipoteza curentă", "pcba", None, None, "pc_cur"),
    ("PCBA EMS (€/placă) — prag peste care SMT propriu (D vs C) e mai ieftin", "pcba", ("D_total", "C_total"), "scrapvat", "pc_thr"),
]:
    RZ[f"B{r}"] = lbl
    RZ[f"B{r}"].font = F_B if num else F_N
    for c in VC:
        if cur == "bb":
            base = ipref("bb_eur", c)
        elif cur == "shell":
            base = f"Scenarii!{c}{SROW['shell_buy']}"
        else:
            base = f"Scenarii!{c}{SROW['pcba_buy']}"
        if num is None:
            f = f"={base}"
        else:
            delta = f"(Scenarii!{c}{SROW[num[0]]}-Scenarii!{c}{SROW[num[1]]})"
            if extra == "vat":
                div = f"(1+Scenarii!{c}{SROW['vatcost']})"
            else:
                div = f"((1+{ipref('scrap_base', c)})*(1+Scenarii!{c}{SROW['vatcost']}))"
            f = f"={base}+{delta}/{div}"
            if cur == "pcba":
                f = f"=IF(Scenarii!{c}{SROW['route']}=2,\"fără PCB propriu\",{base}+{delta}/{div})"
        RZ[f"{c}{r}"] = f
        RZ[f"{c}{r}"].number_format = EUR2
        RZ[f"{c}{r}"].font = F_LINK
        if num:
            RZ[f"{c}{r}"].fill = FILL_TOT
    thr_rows[key] = r
    r += 1
RZ[f"B{r}"] = "Dacă oferta reală e SUB prag, externalizarea rămâne mai ieftină la acel volum. Pragurile includ toate costurile fixe ale treptei (oameni, chirie, amortizare)."
RZ[f"B{r}"].font = F_NOTE
RZ[f"B{r}"].alignment = WRAP
RZ.merge_cells(f"B{r}:G{r}")
RZ.row_dimensions[r].height = 28
r += 2

RZ[f"B{r}"] = "10. Ce citim din model (se actualizează automat din ipoteze; verifică după RFQ)"
RZ[f"B{r}"].font = F_B
RZ[f"B{r}"].fill = FILL_HDR
r += 1
best = first_total + 4


def num_txt(ref, fmt="#,##0"):
    return f'IF(ISNUMBER({ref}),TEXT({ref},"{fmt}"),{ref})'


texts = [
    (f'="• Cel mai ieftin la 100 / 1.000 / 5.000 / 20.000 buc./an: "&C{best}&" / "&D{best}&" / "&E{best}&" / "&F{best}'
     f'&". Diferențele de câțiva €/buc. sunt sub marja de eroare a estimărilor."'),
    (f'="• Atelierul T0 (B) bate box build-ul la EMS dacă EMS cere peste "&TEXT(D{thr_rows["bb_thr"]},"0.0")&" € la 1.000 buc. și peste "'
     f'&TEXT(E{thr_rows["bb_thr"]},"0.0")&" € la 5.000 (ipoteza: "&TEXT(D{thr_rows["bb_cur"]},"0.0")&" / "&TEXT(E{thr_rows["bb_cur"]},"0.0")'
     f'&" €). Argumentul real pentru T0 e controlul: flash, calibrare, test, serie, QC."'),
    (f'="• CNC propriu S: o mașină plină pe un schimb (~"&TEXT({scal["capS"]},"#,##0")&" seturi/an) e aproape de break-even; în grila cu trepte reale '
     f'propriul câștigă de la "&{num_txt(BE_RESULTS["cnc_S"])}&" seturi/an (M, comparație: "&{num_txt(BE_RESULTS["cnc_Mc"])}&"). Prima celulă: ~"'
     f'&TEXT({scal["mach"]}+{ipref("cnc_tooling_eur","C")}+{scal["cnc_common"]},"#,##0")&" € capex."'),
    (f'="• SMT propriu bate EMS România abia pe la "&{num_txt(BE_RESULTS["smt_ems"])}&" plăci/an (la limită) și nu bate JLCPCB în grilă ("'
     f'&{num_txt(BE_RESULTS["smt_jlc"])}&"). Plus: PCB-ul custom încă nu există."'),
    '="• Anodizarea rămâne externă în toate scenariile: CAEN 2561 cere autorizație de mediu, ape uzate NTPA-002 (Ni 1,0 mg/L), acetat de nichel; culoarea pe 5 nuanțe e riscul principal."',
]
for t in texts:
    RZ[f"B{r}"] = t
    RZ[f"B{r}"].font = F_N
    RZ[f"B{r}"].alignment = WRAP
    RZ.merge_cells(f"B{r}:G{r}")
    RZ.row_dimensions[r].height = 30
    r += 1

# ------------------------------------------------------------------ Citește-mă
RM.column_dimensions["A"].width = 120
lines = [
    ("SOUL — model de cost și break-even: fabrică mică vs lanț de producție", F_H),
    ("ARTEMIS DIGITAL S.R.L. · model construit 15.10.2026, refăcut pe 22.10.2026 pe mărimea de bază S (AMOLED 1,75″ 466×466, 63×70,8×23 mm, LiPo 750 mAh; docs/size-s.json, docs/12-SIZE-S.md §3) · M (prototipul 2.8C) e comparația din Break-even", F_NOTE),
    ("", F_N),
    ("Întrebarea: „ce ar însemna să facem efectiv o fabrică? mică, pentru asta, sau un lanț de producție măcar”", F_B),
    ("", F_N),
    ("Scenarii", F_B),
    ("A — Lanț de producție, totul externalizat: EMS (Felix EMS / EMS-Electra) face PCBA + asamblare + flash + test; CNC + anodizare + sticlă la parteneri; noi facem QC final și ambalare.", F_N),
    ("B — Atelier T0 propriu: PCBA și carcasa le cumpărăm; asamblarea, flash-ul, calibrarea, testul funcțional, QC, marcarea laser și ambalarea le facem noi.", F_N),
    ("C — T1: B + celulă CNC proprie (Haas VF-2, sablare, ultrasunete). Anodizarea rămâne externă (Anorom / Alvi / ARSAT).", F_N),
    ("D — T2: C + linie SMT proprie (NeoDen FP2636 + NeoDen4 + IN6 + AOI).", F_N),
    ("Volume: 100 / 1.000 / 5.000 / 20.000 unități pe an.", F_N),
    ("", F_N),
    ("Foi", F_B),
    ("Rezultate — tabelul-cheie: cost/unitate pe scenariu × volum, capex, costuri fixe, marjă, break-even CNC și SMT, capex pe treaptă.", F_N),
    ("Ipoteze — TOATE intrările (albastru = editabil, galben = pârghie-cheie), cu sursă + URL + dată sau [estimare] cu raționament.", F_N),
    ("Scenarii — calculul complet: BOM, procese, capacitate și personal, apoi capex / fix / variabil / total pentru A, B, C, D.", F_N),
    ("Break-even — make vs buy pentru CNC (S și M, comparație) și SMT (vs EMS România și vs JLCPCB): analitic pe trepte + grilă cu trepte reale de capacitate.", F_N),
    ("Capacitate — unități/schimb pe stație, stații necesare pe volum, gâtuirea (bottleneck) și personalul.", F_N),
    ("", F_N),
    ("Cum se folosește", F_B),
    ("1. Schimbi doar celulele albastre din Ipoteze. Exemplu: când vine oferta de la Felix EMS pentru box build, pui prețul în rândul bb_eur pe volumul respectiv.", F_N),
    ("2. Selectorul pcba_sel (1 = JLCPCB, 2 = EMS RO) schimbă reperul de PCBA în A, B și C. el_route alege placa Waveshare (2) sau PCB-ul propriu (1) pe fiecare volum.", F_N),
    ("3. Pentru un CNC second-hand, schimbă cnc_list_usd (ex. VF-2SSYT 2012: €32.500 ≈ $37.360) și cnc_extra_pct.", F_N),
    ("", F_N),
    ("Convenții", F_B),
    ("• EUR fără TVA. Sub plafonul de scutire ARTEMIS nu recuperează TVA, așa că modelul adaugă 21 % la achiziții automat (la 100 buc./an).", F_N),
    ("• Costul total/unitate = variabil + (chirie + salarii + amortizare + permise/asigurări) / volum. NRE-ul produsului (PCB, sticlă, matrițe OU) e separat și comun tuturor scenariilor.", F_N),
    ("• Nu sunt incluse: certificarea CE/RED (per produs, 04-COMPLIANCE.md), marketing, fulfilment către clienți (3PL), timpul fondatorului în afara manoperei directe, costul capitalului.", F_N),
    ("• [estimare] = cifră fără ofertă; NU folosi modelul ca ofertă. Pașii următori: RFQ cu STEP/Gerber/BOM la Felix EMS, EMS-Electra, ICCO, ARSAT, Alvi, JLCCNC, Anorom, Felix Glass, Mirit, Web2Print.", F_N),
    ("• Simplificări: prețul extern între trepte e interpolat logaritmic; la ≥10k carcasa ar trece pe ambutisare 5052 (nemodelat, ar face CNC-ul propriu și mai puțin atractiv).", F_N),
]
for i, (t, f) in enumerate(lines, start=1):
    RM[f"A{i}"] = t
    RM[f"A{i}"].font = f
    RM[f"A{i}"].alignment = Alignment(wrap_text=True, vertical="top")

for ws in wb.worksheets:
    ws.sheet_view.showGridLines = True
wb.active = 1
wb.save(OUT)
print("saved", OUT)
