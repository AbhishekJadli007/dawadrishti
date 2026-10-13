"""Step 2 of the ETL: merge all sources into one clean staging table, then resolve manufacturer identities.

Output: data/staging/nsq_findings.csv (one row per failed batch) and data/staging/manufacturers.csv.
Original text is always kept next to the cleaned value (columns ending in _raw).
"""
from __future__ import annotations

import glob
import json
import re

import pandas as pd

from .. import config as C
from . import clean, entities, parse_pdf

MON = {m: i for i, m in enumerate(["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"], 1)}


def _month(s) -> str | None:
    m = re.match(r"([A-Za-z]{3})[-\s]?(\d{4})", str(s or ""))
    return f"{m.group(2)}-{MON[m.group(1).upper()]:02d}" if m and m.group(1).upper() in MON else None


def load_portal() -> pd.DataFrame:
    rows = []
    for f in sorted(glob.glob(str(C.DATA / "raw" / "portal" / "*.json"))):
        tab = "spurious" if "spurious_" in f else "nsq"
        for r in json.load(open(f)):
            rows.append({
                "product_name": r.get("str_product_name") or r.get("product_name_from_dtl"),
                "batch_no": r.get("str_batch_no"), "mfg_date": r.get("dt_manufacturing_date"),
                "exp_date": r.get("dt_expiry_date"),
                "manufacturer": (r.get("str_spurious_manufacturer_name") or r.get("str_manufactured_by")),
                "nsq_result": r.get("str_nsq_result"), "reporting_source": r.get("str_reporting_source"),
                "reporting_lab": r.get("str_reported_by_lab_or_state"),
                "alert_month": _month(r.get("dt_reporting_month_year")),
                "source": "portal-" + tab, "source_doc": f.split("/")[-1],
                "remarks": r.get("str_nsq_remarks") or "", "firm_reply": r.get("str_firm_reply") or "",
            })
    return pd.DataFrame(rows)


def build_staging() -> pd.DataFrame:
    portal = load_portal()
    pdf = parse_pdf.parse_all(months_before=portal.alert_month.min())
    df = pd.concat([pdf, portal], ignore_index=True)
    for c in ["product_name", "manufacturer", "nsq_result", "batch_no", "reporting_lab", "remarks", "firm_reply"]:
        df[c] = df[c].fillna("").astype(str).str.replace(r"\s+", " ", regex=True).str.strip()
    df = df[(df.product_name != "") & df.alert_month.notna()]
    df["is_spurious"] = df.source.eq("portal-spurious") | df.remarks.str.contains("spurious", case=False) | \
        df.firm_reply.str.contains("not been manufactured|not manufactured|spurious", case=False)
    df["manufacturer_unknown"] = df.manufacturer.str.contains("under investigation|not known|unknown", case=False) | df.manufacturer.eq("")
    # some alerts name the public buyer that supplied the batch (e.g. "Supplied by Kerala Medical Services Corporation"),
    # not its maker: such rows say nothing about any manufacturer
    buyer_named = df.manufacturer.str.contains(r"medical services corporation|medical supplies corporation|^supplied by", case=False)
    df["manufacturer_note"] = buyer_named.map({True: "names the supplying public buyer, not the maker", False: ""})
    df.loc[buyer_named, "manufacturer_unknown"] = True

    mf = df.manufacturer.map(clean.split_manufacturer)
    df["manufacturer_name"] = [a for a, _ in mf]
    df["manufacturer_address"] = [b for _, b in mf]
    st = df.manufacturer.map(clean.state_of)
    df["state"] = [a for a, _ in st]
    df["state_basis"] = [b for _, b in st]
    prod = df.product_name.map(clean.clean_product).apply(pd.Series)
    fail = df.nsq_result.map(clean.classify_failure).apply(pd.Series)
    df = pd.concat([df, prod, fail], axis=1)
    df.loc[df.is_spurious, ["primary_failure", "severity"]] = ["Spurious (fake)", "critical"]
    # A fake that uses a real firm's name must not count against that firm: the firm denied making it.
    denied = df.is_spurious & df.firm_reply.str.contains("not been manufactured|not manufactured|has not|spurious", case=False)
    df["impersonated_firm"] = df.manufacturer.where(denied, "")
    df.loc[denied, "manufacturer_unknown"] = True
    src = df.reporting_source.fillna("").str.strip().str.lower()
    df["reporting_source"] = src.map(lambda x: "CDSCO lab" if "cdsco" in x or "central" in x else "State lab" if "state" in x
                                     else "Drugs inspector" if "not applicable" in x or "inspector" in x else "Other")
    df = df.drop_duplicates(["batch_no", "product_name", "manufacturer", "alert_month"]).reset_index(drop=True)
    df.insert(0, "finding_id", range(1, len(df) + 1))
    return df


def resolve_entities(df: pd.DataFrame) -> pd.DataFrame:
    """Give every row a unit id (firm + state) and a firm id (units joined across states). See etl/entities.py."""
    known = df[~df.manufacturer_unknown]
    df = df.copy()
    keys, pairs = entities.resolve(known.manufacturer_name, known.state)
    # canonical name = the most frequent spelling in the group
    names = known.assign(key=known.manufacturer_name.map(clean.name_key))
    best = names.groupby("key").manufacturer_name.agg(lambda s: s.value_counts().index[0])
    top = keys.sort_values("n", ascending=False)
    unit_name = {u: best.get(k, k) for u, k in top.drop_duplicates("unit")[["unit", "key"]].values}
    firm_name = {f: best.get(k, k) for f, k in top.drop_duplicates("firm")[["firm", "key"]].values}
    lookup = {(r.key, r.state): (r.unit, r.firm) for r in keys.itertuples()}
    unit, firm, uname, fname = [], [], [], []
    for r in df.itertuples():
        e = None if r.manufacturer_unknown else lookup.get((clean.name_key(r.manufacturer_name), r.state))
        unit.append(f"M{e[0]:05d}" if e else "M_UNKNOWN")
        firm.append(f"F{e[1]:05d}" if e else "F_UNKNOWN")
        uname.append(unit_name[e[0]] if e else "Unknown / under investigation")
        fname.append(firm_name[e[1]] if e else "Unknown / under investigation")
    df["manufacturer_id"], df["manufacturer_canonical"], df["firm_id"], df["firm_canonical"] = unit, uname, firm, fname
    pairs.to_csv(C.STAGING / "entity_matches.csv", index=False)
    return df


def main():
    C.STAGING.mkdir(parents=True, exist_ok=True)
    df = resolve_entities(build_staging())
    df.to_csv(C.STAGING / "nsq_findings.csv", index=False)
    m = df[df.manufacturer_id != "M_UNKNOWN"].groupby(["manufacturer_id", "manufacturer_canonical", "state", "firm_id", "firm_canonical"]).size()
    m.reset_index(name="findings").sort_values("findings", ascending=False).to_csv(C.STAGING / "manufacturers.csv", index=False)
    print(f"staged {len(df)} findings ({df.alert_month.min()} to {df.alert_month.max()}), "
          f"{df.manufacturer_id.nunique()} manufacturing units of {df.firm_id.nunique()} firms, {df.state.nunique()} states/regions")
    print("  sources:", df.source.value_counts().to_dict())
    print("  state found for", f"{(df.state != 'Unknown').mean():.1%}", "| class found for",
          f"{(df.therapeutic_class != 'Other / unclassified').mean():.1%}", "| failure classified for",
          f"{(df.primary_failure != 'Other').mean():.1%}")


if __name__ == "__main__":
    main()
