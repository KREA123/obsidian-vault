#!/usr/bin/env python3
"""Load the campaign facts: ../facts.json + ../../docs/size-s.json (the S design source) + the goal model output.

    from facts import load            # tools/ on sys.path
    F = load()                        # dict, with F["design"] (size-s.json), F["scn"] (active scenario), F["lad"] (ladder)

The two sources must agree. load() raises if a size fact in facts.json is not backed by size-s.json
(rounded width/height, the depth range covering both electronics routes, weight and battery ranges).
"""
import json, math, os

HERE = os.path.dirname(os.path.abspath(__file__))
CF = os.path.dirname(HERE)
MS = os.path.dirname(CF)
MONTHS_EN = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
MONTHS_RO = ["ianuarie", "februarie", "martie", "aprilie", "mai", "iunie", "iulie", "august", "septembrie", "octombrie", "noiembrie", "decembrie"]


class FactsError(Exception):
    pass


def _check(F, d):
    S = F["size_S"]
    errs = []
    if round(d["dims_mm"]["w"]) != S["width_mm"]:
        errs.append(f"width {S['width_mm']} vs size-s.json {d['dims_mm']['w']}")
    if round(d["dims_mm"]["h"]) != S["height_mm"]:
        errs.append(f"height {S['height_mm']} vs size-s.json {d['dims_mm']['h']}")
    t = S["thickness_mm"]
    depths = [d["dims_mm"]["d"], d["variants"]["S-P0_dev_board"]["dims_mm"]["d"]]
    if not all(t["min"] <= x <= t["max"] for x in depths):
        errs.append(f"thickness range {t['min']}–{t['max']} does not cover both routes {depths}")
    R = S["electronics_routes"]
    if R["A"]["depth_mm"] != d["dims_mm"]["d"] or R["B"]["depth_mm"] != d["variants"]["S-P0_dev_board"]["dims_mm"]["d"]:
        errs.append("electronics_routes depths differ from size-s.json")
    if R["A"]["battery_mAh"] != d["battery_mAh"] or R["B"]["battery_mAh"] != d["variants"]["S-P0_dev_board"]["battery_mAh"]:
        errs.append("electronics_routes batteries differ from size-s.json")
    b = S["battery"]["range_mAh"]
    if b != sorted([d["battery_mAh"], d["variants"]["S-P0_dev_board"]["battery_mAh"]]):
        errs.append(f"battery range {b} vs size-s.json")
    w = S["weight_g"]
    if not (w["min"] <= d["weight_g_est"] <= w["max"] and w["min"] <= d["variants"]["S-P0_dev_board"]["weight_g_est"] <= w["max"]):
        errs.append(f"weight range {w['min']}–{w['max']} does not cover size-s.json estimates")
    if S["screen"]["resolution_px"] != d["resolution"]:
        errs.append("screen resolution differs")
    if errs:
        raise FactsError("facts.json and docs/size-s.json disagree: " + "; ".join(errs))


def month(ym, lang="en", short=False):
    y, m = ym.split("-")[:2]
    name = (MONTHS_RO if lang == "ro" else MONTHS_EN)[int(m) - 1]
    if short:
        name = name[:3]
    return f"{name} {y}"


def day(iso, lang="en", weekday=False):
    import datetime as dt
    d = dt.date.fromisoformat(iso)
    wd_en = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    wd_ro = ["luni", "marți", "miercuri", "joi", "vineri", "sâmbătă", "duminică"]
    if lang == "ro":
        s = f"{d.day} {MONTHS_RO[d.month - 1]} {d.year}"
        return (wd_ro[d.weekday()] + ", " + s) if weekday else s
    s = f"{d.day} {MONTHS_EN[d.month - 1]} {d.year}"
    return (wd_en[d.weekday()] + " " + s) if weekday else s


def eur(v, lang="en"):
    s = f"{v:,.0f}"
    if lang == "ro":
        s = s.replace(",", ".")
    return "€" + s


def load(with_model=True):
    F = json.load(open(os.path.join(CF, "facts.json"), encoding="utf-8"))
    d = json.load(open(os.path.normpath(os.path.join(CF, F["size_S"]["source"])), encoding="utf-8"))
    _check(F, d)
    F["design"] = d
    C = F["campaign"]
    F["scn"] = C["scenarios"][C["scenario"]]
    F["lad"] = F["pricing"]["ladders"][C["ladder"]]
    F["colours"] = F["product"]["colours_launch"]["value"]
    if with_model:
        p = os.path.join(HERE, "goal_model.out.json")
        if os.path.exists(p):
            F["model"] = json.load(open(p, encoding="utf-8"))
    return F


if __name__ == "__main__":
    F = load()
    print("ok: facts.json agrees with", F["size_S"]["source"], "| scenario", F["campaign"]["scenario"], "| ladder", F["campaign"]["ladder"],
          "| goal", F.get("model", {}).get("goal_eur"))
