#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read saoudrizwan.claude-dev state value."""

import os
import sqlite3

db = os.path.expandvars(r"%APPDATA%\Code\User\globalStorage\state.vscdb")
con = sqlite3.connect(db)
cur = con.cursor()
val = cur.execute(
    "SELECT value FROM ItemTable WHERE key = ?",
    ("saoudrizwan.claude-dev",),
).fetchone()
print(repr(val[0] if val else None))
# dump all keys containing claude or cline case insensitive via lower
rows = cur.execute("SELECT key FROM ItemTable").fetchall()
for (k,) in rows:
    kl = k.lower()
    if "claude" in kl or "cline" in kl or "saoud" in kl:
        print("KEY:", k)
con.close()
