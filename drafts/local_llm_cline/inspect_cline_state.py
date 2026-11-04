#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Inspect VS Code state.vscdb for Cline keys."""

import os
import sqlite3
import sys

db = os.path.expandvars(r"%APPDATA%\Code\User\globalStorage\state.vscdb")
print("db:", db, "exists:", os.path.exists(db))
con = sqlite3.connect(db)
cur = con.cursor()
print("tables:", [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()])
rows = cur.execute(
    "SELECT key, length(value) FROM ItemTable WHERE key LIKE '%cline%' OR key LIKE '%claude-dev%' OR key LIKE '%saoudrizwan%'"
).fetchall()
print("matching keys:", len(rows))
for k, l in rows:
    print(f"  {k}  len={l}")
# also search for apiProvider / lmStudio in values
hits = cur.execute(
    "SELECT key, substr(value,1,200) FROM ItemTable WHERE typeof(value)='text' AND (value LIKE '%lmStudio%' OR value LIKE '%apiProvider%' OR value LIKE '%lmstudio%') LIMIT 30"
).fetchall()
print("value hits:", len(hits))
for k, v in hits:
    print(f"  KEY={k}")
    print(f"  VAL={v!r}")
con.close()
