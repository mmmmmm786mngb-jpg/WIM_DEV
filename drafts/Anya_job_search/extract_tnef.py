#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Decode OK test email body and extract winmail.dat attachments."""

from pathlib import Path
import email
from email import policy
from tnefparse import TNEF

OUT = Path(r"c:\1c\Cursor_1c\WIM_DEV\drafts\Anya_job_search\ok_test_extract")
payload = (OUT / "payload_raw.bin").read_bytes()

msg = email.message_from_bytes(payload, policy=policy.default)
print("Subject:", msg.get("Subject"))
print("From:", msg.get("From"))
print("To:", msg.get("To"))
print("Date:", msg.get("Date"))

for part in msg.walk():
    ctype = part.get_content_type()
    if ctype == "text/plain":
        body = part.get_payload(decode=True) or b""
        print("text/plain bytes:", len(body))
        for enc in ("koi8-r", "cp1251", "utf-8"):
            try:
                text = body.decode(enc)
            except Exception as e:
                print(enc, "fail", e)
                continue
            print("--- body", enc, "---")
            print(text)
            (OUT / "email_body_utf8.txt").write_text(text, encoding="utf-8")
            break
    elif ctype == "text/html":
        body = part.get_payload(decode=True) or b""
        for enc in ("koi8-r", "cp1251", "utf-8"):
            try:
                text = body.decode(enc)
                (OUT / "email_body.html").write_text(text, encoding="utf-8")
                print("saved html via", enc)
                break
            except Exception:
                continue

tnef_path = OUT / "winmail.dat"
tnef = TNEF(tnef_path.read_bytes())
print("attachments:", len(tnef.attachments))
for a in tnef.attachments:
    name = a.long_filename() or a.name or "unknown.bin"
    data = a.data
    safe = "".join(c if c.isalnum() or c in "._- ()[]" else "_" for c in name)
    path = OUT / safe
    path.write_bytes(data)
    print("ATT:", name, "->", path.name, len(data), "bytes")

# optional body from tnef
for attr in ("body", "htmlbody"):
    val = getattr(tnef, attr, None)
    if val:
        print(attr, "len", len(val) if isinstance(val, (bytes, str)) else type(val))
        if isinstance(val, bytes):
            for enc in ("koi8-r", "cp1251", "utf-8"):
                try:
                    (OUT / f"tnef_{attr}.txt").write_text(val.decode(enc), encoding="utf-8")
                    print("saved tnef", attr, "as", enc)
                    break
                except Exception:
                    continue
        elif isinstance(val, str):
            (OUT / f"tnef_{attr}.txt").write_text(val, encoding="utf-8")
