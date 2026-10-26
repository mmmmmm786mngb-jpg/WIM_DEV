# -*- coding: utf-8 -*-
import re
text = open(r"c:\1c\Cursor_1c\WIM_DEV\.cursor\skills\form-compile\scripts\form-compile.ps1", encoding="utf-8").read()
for kind in ("InputField", "Table", "Command"):
    match = re.search(r"'%s' = '([^']+)'" % kind, text)
    if not match:
        print(kind, "missing")
        continue
    parts = match.group(1).split()
    print("==", kind)
    for name in ("ChoiceButton", "ListChoiceMode", "TextEdit", "Events", "ChildItems", "Picture", "Action", "Title"):
        if name in parts:
            print(name, parts.index(name))
