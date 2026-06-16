#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compare 8899 OLD and NEW snapshot CSV files."""

from collections import Counter, defaultdict
from pathlib import Path

OLD_PATH = Path(
    r"c:\1c\Cursor_1c\WIM_DEV\bases\Wim_Du\projects\IMDEV-8899 Вечерние регламенты Этап2"
    r"\Обработки\внБыстроеУдалениеПлановРеглОперацийДУ_epf\8899_OLD_20260610.8899.csv"
)
NEW_PATH = Path(
    r"c:\1c\Cursor_1c\WIM_DEV\bases\Wim_Du\projects\IMDEV-8899 Вечерние регламенты Этап2"
    r"\Обработки\внБыстроеУдалениеПлановРеглОперацийДУ_epf\8899_snapshot_20260610.8899_НОВЫЙ.8899.csv"
)


def load(path):
    meta = {}
    rows = []
    header = None
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("#"):
                if "=" in line:
                    key, value = line[1:].strip().split("=", 1)
                    meta[key] = value
                continue
            if line.startswith("ДоговорДУ"):
                header = line.strip().split("|")
                continue
            parts = line.strip().split("|")
            if header and len(parts) == 9:
                rows.append(dict(zip(header, parts)))
    return meta, rows


def plan_summary(rows):
    by_contract = defaultdict(
        lambda: {"plan": None, "posted": None, "plan_rows": [], "subdocs": []}
    )
    for row in rows:
        contract = row["ДоговорДУ"]
        by_contract[contract]["plan"] = row["План"]
        by_contract[contract]["posted"] = row["ПланПроведен"]
        if row["ТипДокумента"] == "<строка плана>":
            by_contract[contract]["plan_rows"].append(row)
        else:
            by_contract[contract]["subdocs"].append(row)
    return by_contract


def subdoc_profile(data):
    types = sorted({s["ТипДокумента"] for s in data["subdocs"]})
    counts = tuple(
        sorted((t, sum(1 for s in data["subdocs"] if s["ТипДокумента"] == t)) for t in types)
    )
    posted_sub = sum(1 for s in data["subdocs"] if s["ДокументПроведен"] == "1")
    return len(data["subdocs"]), counts, posted_sub


def main():
    old_meta, old_rows = load(OLD_PATH)
    new_meta, new_rows = load(NEW_PATH)
    old_c = plan_summary(old_rows)
    new_c = plan_summary(new_rows)

    print("=== META ===")
    for key in sorted(set(old_meta) | set(new_meta)):
        print(f"{key}: OLD={old_meta.get(key)} NEW={new_meta.get(key)}")

    contracts_old = set(old_c)
    contracts_new = set(new_c)
    common = contracts_old & contracts_new
    print(f"\nContracts: OLD={len(contracts_old)} NEW={len(contracts_new)} common={len(common)}")

    old_posted = {c for c, d in old_c.items() if d["posted"] == "1"}
    new_posted = {c for c, d in new_c.items() if d["posted"] == "1"}
    print(f"Plan posted: OLD={len(old_posted)} unposted={len(contracts_old - old_posted)}")
    print(f"Plan posted: NEW={len(new_posted)} unposted={len(contracts_new - new_posted)}")

    posted_diff = [c for c in common if old_c[c]["posted"] != new_c[c]["posted"]]
    old0_new1 = [c for c in posted_diff if old_c[c]["posted"] == "0" and new_c[c]["posted"] == "1"]
    old1_new0 = [c for c in posted_diff if old_c[c]["posted"] == "1" and new_c[c]["posted"] == "0"]
    print(f"Posting status changed: {len(posted_diff)}")
    print(f"  OLD unposted -> NEW posted: {len(old0_new1)}")
    print(f"  OLD posted -> NEW unposted: {len(old1_new0)}")

    subdoc_diff = []
    same_profile = 0
    for contract in common:
        old_prof = subdoc_profile(old_c[contract])
        new_prof = subdoc_profile(new_c[contract])
        if old_prof != new_prof:
            subdoc_diff.append((contract, old_prof, new_prof))
        else:
            same_profile += 1
    print(f"\nSubdoc profile same: {same_profile}")
    print(f"Subdoc profile different: {len(subdoc_diff)}")

    breakdown = Counter((o[0], n[0]) for _, o, n in subdoc_diff)
    print("Subdoc count transitions (old -> new):")
    for pair, count in sorted(breakdown.items(), key=lambda x: -x[1])[:15]:
        print(f"  {pair[0]} -> {pair[1]}: {count}")

    vid_changes = Counter()
    for contract in common:
        old_vids = {r["ВидОперации"]: r["Выполнять"] for r in old_c[contract]["plan_rows"]}
        new_vids = {r["ВидОперации"]: r["Выполнять"] for r in new_c[contract]["plan_rows"]}
        for vid in set(old_vids) | set(new_vids):
            if old_vids.get(vid) != new_vids.get(vid):
                vid_changes[(vid, old_vids.get(vid), new_vids.get(vid))] += 1
    print("\nVypolnyat changes (vid_prefix, old, new): count")
    for (vid, old_v, new_v), count in vid_changes.most_common(20):
        print(f"  {vid[:8]}... {old_v}->{new_v}: {count}")

    old_types = Counter(
        r["ТипДокумента"] for r in old_rows if r["ТипДокумента"] != "<строка плана>"
    )
    new_types = Counter(
        r["ТипДокумента"] for r in new_rows if r["ТипДокумента"] != "<строка плана>"
    )
    print("\nSubdoc types OLD:", dict(old_types))
    print("Subdoc types NEW:", dict(new_types))

    old_zero = sum(1 for c in contracts_old if subdoc_profile(old_c[c])[0] == 0)
    new_zero = sum(1 for c in contracts_new if subdoc_profile(new_c[c])[0] == 0)
    print(f"\nContracts with 0 subdocs: OLD={old_zero} NEW={new_zero}")

    both_posted_same = 0
    both_posted_diff = 0
    for contract in common:
        if old_c[contract]["posted"] == "1" and new_c[contract]["posted"] == "1":
            if subdoc_profile(old_c[contract])[:2] == subdoc_profile(new_c[contract])[:2]:
                both_posted_same += 1
            else:
                both_posted_diff += 1
    print(f"\nBoth posted: same subdoc profile {both_posted_same}, different {both_posted_diff}")

    rsa_only = []
    three_types = []
    for contract in old0_new1:
        n = new_c[contract]
        types = set(s["ТипДокумента"] for s in n["subdocs"])
        if types == {"Расчет СЧА/РСА"}:
            rsa_only.append(contract)
        elif len(types) == 3:
            three_types.append(contract)
    print(f"\nAmong {len(old0_new1)} OLD-fail -> NEW-ok:")
    print(f"  NEW has all 3 subdoc types: {len(three_types)}")
    print(f"  NEW has only RSA/SCA: {len(rsa_only)}")

    print("\nSample OLD unposted -> NEW posted:")
    for contract in old0_new1[:3]:
        o = old_c[contract]
        n = new_c[contract]
        n_types = sorted({s["ТипДокумента"] for s in n["subdocs"]})
        print(f"  {contract}: sub OLD={len(o['subdocs'])} NEW={len(n['subdocs'])} types={n_types}")

    # Plan rows count per contract
    plan_rows_old = Counter(len(d["plan_rows"]) for d in old_c.values())
    plan_rows_new = Counter(len(d["plan_rows"]) for d in new_c.values())
    print("\nPlan rows per contract OLD:", dict(sorted(plan_rows_old.items())))
    print("Plan rows per contract NEW:", dict(sorted(plan_rows_new.items())))

    # Vypolnyat=0 count in NEW for all contracts
    new_v0 = sum(1 for r in new_rows if r["ТипДокумента"] == "<строка плана>" and r["Выполнять"] == "0")
    old_v0 = sum(1 for r in old_rows if r["ТипДокумента"] == "<строка плана>" and r["Выполнять"] == "0")
    print(f"\nPlan rows with Vypolnyat=0: OLD={old_v0} NEW={new_v0}")


if __name__ == "__main__":
    main()
