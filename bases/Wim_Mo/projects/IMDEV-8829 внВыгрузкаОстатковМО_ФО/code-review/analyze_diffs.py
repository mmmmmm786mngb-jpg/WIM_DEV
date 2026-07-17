#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Analyze Alexey vs Fedor diffs for code review."""

import json
from pathlib import Path

p = Path(__file__).with_name("diff_summary.json")
s = json.loads(p.read_text(encoding="utf-8"))
om = s["files"]["ObjectModule.bsl"]
print("=== CHANGED ObjectModule (sorted by ratio asc) ===")
for ch in sorted(om["changed_procs"], key=lambda x: x["ratio"]):
    print(
        f"{ch['ratio']:.3f} {ch['kind']} {ch['name']}: "
        f"A{ch['alex_lines']} -> F{ch['fedor_lines']} "
        f"(A@{ch['alex_start']} F@{ch['fedor_start']})"
    )
print()
fm = s["files"]["Form_Module.bsl"]
print("=== CHANGED Form Module ===")
for ch in sorted(fm["changed_procs"], key=lambda x: x["ratio"]):
    print(
        f"{ch['ratio']:.3f} {ch['kind']} {ch['name']}: "
        f"A{ch['alex_lines']} -> F{ch['fedor_lines']}"
    )
print("only fedor", fm["only_fedor"])
print()
sf = s["files"]["SettingsForm_Module.bsl"]
print(
    "Settings identical?",
    sf["identical"],
    "changed",
    len(sf.get("changed_procs", [])),
    "only_f",
    sf.get("only_fedor"),
    "only_a",
    sf.get("only_alex"),
)
print()
print("=== KEYWORDS delta ===")
for kw, v in s["keywords"].items():
    if v["obj_alex"] != v["obj_fedor"] or v["form_alex"] != v["form_fedor"]:
        print(
            f"{kw}: obj {v['obj_alex']}->{v['obj_fedor']} "
            f"form {v['form_alex']}->{v['form_fedor']}"
        )
print()
print("Form.xml only F", s["files"]["Form.xml"].get("only_fedor_meta"))
print("Form.xml only A", s["files"]["Form.xml"].get("only_alex_meta"))
print("SettingsForm.xml only F", s["files"]["SettingsForm.xml"].get("only_fedor_meta"))
print("SettingsForm.xml only A", s["files"]["SettingsForm.xml"].get("only_alex_meta"))
root = s["files"]["Root.xml"]
print(
    "Root identical?",
    root["identical"],
    "A",
    root["alex_lines"],
    "F",
    root["fedor_lines"],
    "add",
    root["added"],
    "rem",
    root["removed"],
)
