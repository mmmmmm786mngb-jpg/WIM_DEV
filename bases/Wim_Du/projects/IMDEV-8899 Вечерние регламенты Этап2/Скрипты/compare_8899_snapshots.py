#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compare 8899 OLD and NEW snapshot CSV files."""

from collections import Counter, defaultdict
from pathlib import Path

BASE_PATH = Path(
    r"c:\1c\Cursor_1c\WIM_DEV\bases\Wim_Du\projects\IMDEV-8899 Вечерние регламенты Этап2"
    r"\Обработки\внБыстроеУдалениеПлановРеглОперацийДУ_epf"
)
SNAPSHOT_PATHS = {
    "OLD": BASE_PATH / "8899_OLD_20260610.8899.csv",
    "OLD2": BASE_PATH / "8899_OLD2_20260610.8899.csv",
    "NEW": BASE_PATH / "8899_snapshot_20260610.8899_НОВЫЙ.8899.csv",
}

VID_NAMES = {
    "ed8da25e-e59e-4932-9edc-643a2add8ba9": "PereocDS_UU",
    "fc5efdc7-4f64-4d5a-bfe0-fa1eee366caf": "Defolt_BU",
    "74e61bfc-d148-4ae7-832e-b73d5a2f1164": "Defolt_UU",
    "f096371e-bb4e-4203-af5f-28d32833c95f": "Kontrol_UU",
    "4b4f7a79-db26-492d-a380-2b17ea75edcd": "NKD_UU",
    "5e5d4997-eb05-49c4-98f5-f373c84e6992": "Pereoc_UU",
    "8b24ba06-b0de-4ef9-b48d-247f98102e45": "RSA_BU",
    "2fc35b83-3d32-446f-b745-fd3aad76d7b0": "SCA_BU",
}


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


def types_set(data):
    return {s["ТипДокумента"] for s in data["subdocs"]}


def compare_snapshots(label_left, label_right):
    left_meta, left_rows = load(SNAPSHOT_PATHS[label_left])
    right_meta, right_rows = load(SNAPSHOT_PATHS[label_right])
    left_c = plan_summary(left_rows)
    right_c = plan_summary(right_rows)
    common = set(left_c) & set(right_c)

    print("=" * 60)
    print(f"COMPARE {label_left} vs {label_right}")
    print(
        f"META {label_left}: MARK={left_meta.get('MARK')} ROWS={left_meta.get('ROWS')} "
        f"CREATED={left_meta.get('CREATED')}"
    )
    print(
        f"META {label_right}: MARK={right_meta.get('MARK')} ROWS={right_meta.get('ROWS')} "
        f"CREATED={right_meta.get('CREATED')}"
    )

    left_posted = sum(1 for contract in left_c if left_c[contract]["posted"] == "1")
    right_posted = sum(1 for contract in right_c if right_c[contract]["posted"] == "1")
    print(
        f"Plans posted: {label_left}={left_posted} unposted={len(left_c) - left_posted}; "
        f"{label_right}={right_posted} unposted={len(right_c) - right_posted}"
    )

    posted_diff = [c for c in common if left_c[c]["posted"] != right_c[c]["posted"]]
    left_fail_right_ok = [
        c for c in posted_diff if left_c[c]["posted"] == "0" and right_c[c]["posted"] == "1"
    ]
    left_ok_right_fail = [
        c for c in posted_diff if left_c[c]["posted"] == "1" and right_c[c]["posted"] == "0"
    ]
    print(
        f"Posting changed: {len(posted_diff)} "
        f"({label_left} fail -> {label_right} ok: {len(left_fail_right_ok)}, reverse: {len(left_ok_right_fail)})"
    )

    same_profile = 0
    profile_diff = 0
    transitions = Counter()
    for contract in common:
        left_prof = subdoc_profile(left_c[contract])
        right_prof = subdoc_profile(right_c[contract])
        if left_prof == right_prof:
            same_profile += 1
        else:
            profile_diff += 1
            transitions[(left_prof[0], right_prof[0])] += 1
    print(f"Subdoc profile same: {same_profile}, different: {profile_diff}")
    if transitions:
        print("Subdoc count transitions:")
        for pair, count in sorted(transitions.items(), key=lambda item: -item[1])[:10]:
            print(f"  {pair[0]} -> {pair[1]}: {count}")

    left_types = Counter(
        row["ТипДокумента"] for row in left_rows if row["ТипДокумента"] != "<строка плана>"
    )
    right_types = Counter(
        row["ТипДокумента"] for row in right_rows if row["ТипДокумента"] != "<строка плана>"
    )
    print(f"Subdoc totals {label_left}:", dict(left_types))
    print(f"Subdoc totals {label_right}:", dict(right_types))

    for label, data in ((label_left, left_c), (label_right, right_c)):
        three_types = sum(
            1 for contract in data if data[contract]["posted"] == "1" and len(types_set(data[contract])) == 3
        )
        rsa_only = sum(
            1
            for contract in data
            if data[contract]["posted"] == "1" and types_set(data[contract]) == {"Расчет СЧА/РСА"}
        )
        zero_subdocs = sum(1 for contract in data if subdoc_profile(data[contract])[0] == 0)
        print(
            f"{label}: posted 3-types={three_types}, posted rsa-only={rsa_only}, zero-subdocs={zero_subdocs}"
        )

    vid_changes = Counter()
    for contract in common:
        left_vids = {row["ВидОперации"]: row["Выполнять"] for row in left_c[contract]["plan_rows"]}
        right_vids = {row["ВидОперации"]: row["Выполнять"] for row in right_c[contract]["plan_rows"]}
        for vid in set(left_vids) | set(right_vids):
            if left_vids.get(vid) != right_vids.get(vid):
                name = VID_NAMES.get(vid, vid[:8])
                vid_changes[(name, left_vids.get(vid), right_vids.get(vid))] += 1
    if vid_changes:
        print("Vypolnyat changes:")
        for (name, old_value, new_value), count in vid_changes.most_common(10):
            print(f"  {name} {old_value}->{new_value}: {count}")

    both_posted_same = sum(
        1
        for contract in common
        if left_c[contract]["posted"] == "1"
        and right_c[contract]["posted"] == "1"
        and subdoc_profile(left_c[contract])[:2] == subdoc_profile(right_c[contract])[:2]
    )
    print(f"Both posted + same subdoc types/count: {both_posted_same}")


def main():
    compare_snapshots("OLD2", "NEW")
    compare_snapshots("OLD", "OLD2")
    compare_snapshots("OLD", "NEW")


if __name__ == "__main__":
    main()
