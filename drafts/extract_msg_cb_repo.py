#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract Outlook MSG body and attachments for CB RF REPO question."""

import extract_msg
import os
import json

msg_path = r"c:\1c\Cursor_1c\WIM_DEV\drafts\Тип контрагента ЦБ РФ в сделках РЕПО.msg"
out_dir = r"c:\1c\Cursor_1c\WIM_DEV\drafts\msg_cb_repo_extract"
os.makedirs(out_dir, exist_ok=True)

msg = extract_msg.Message(msg_path)
info = {
    "subject": msg.subject,
    "sender": msg.sender,
    "to": msg.to,
    "cc": msg.cc,
    "date": str(msg.date),
    "body": msg.body,
}
with open(os.path.join(out_dir, "message.json"), "w", encoding="utf-8") as f:
    json.dump(info, f, ensure_ascii=False, indent=2)
with open(os.path.join(out_dir, "body.txt"), "w", encoding="utf-8") as f:
    f.write(msg.body or "")

html = getattr(msg, "htmlBody", None)
if html:
    with open(os.path.join(out_dir, "body.html"), "wb") as f:
        if isinstance(html, bytes):
            f.write(html)
        else:
            f.write(str(html).encode("utf-8", errors="replace"))

att_dir = os.path.join(out_dir, "attachments")
os.makedirs(att_dir, exist_ok=True)
atts = []
for i, att in enumerate(msg.attachments):
    name = att.longFilename or att.shortFilename or f"att_{i}"
    safe = "".join(c if c.isalnum() or c in "._- ()[]" else "_" for c in name)
    path = os.path.join(att_dir, f"{i:02d}_{safe}")
    try:
        data = att.data
        with open(path, "wb") as f:
            f.write(data)
        atts.append({"index": i, "name": name, "path": path, "size": len(data)})
    except Exception as e:
        atts.append({"index": i, "name": name, "error": str(e)})

with open(os.path.join(out_dir, "attachments.json"), "w", encoding="utf-8") as f:
    json.dump(atts, f, ensure_ascii=False, indent=2)

print("SUBJECT:", msg.subject)
print("FROM:", msg.sender)
print("TO:", msg.to)
print("ATTS:", len(atts))
for a in atts:
    print(a)
print("---BODY---")
print((msg.body or "")[:5000])
msg.close()
