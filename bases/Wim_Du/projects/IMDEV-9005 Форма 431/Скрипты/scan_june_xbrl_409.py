#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Check June XBRL zip for 409 / schemaRef."""

import re
import zipfile
from pathlib import Path

BASE = Path(r"c:\1c\Cursor_1c\WIM_DEV\bases\Wim_Du\projects\9005_Ортикон\СУПЕРТЕСТ")


def scan_zip(zp: Path):
    print("===", zp.name)
    with zipfile.ZipFile(zp) as z:
        infos = sorted(z.infolist(), key=lambda i: i.file_size, reverse=True)[:8]
        for i in infos:
            print(f"  {i.file_size:>12} {i.filename[-90:]}")
        target = None
        for i in z.infolist():
            low = i.filename.lower()
            if low.endswith(".xbrl") and i.file_size > 1_000_000:
                target = i
                break
        if target is None:
            for i in z.infolist():
                if i.file_size > 5_000_000:
                    target = i
                    break
        if target is None:
            print(" no target")
            return
        print(" scan", target.filename, "size", target.file_size)
        keys = ["0420409", "Rek_kred", "SR_0420409", "0420415", "0420431", "0420401"]
        hits = {k: 0 for k in keys}
        with z.open(target.filename) as f:
            head = f.read(80000).decode("utf-8", errors="ignore")
            m = re.search(r'schemaRef[^>]+href="([^"]+)"', head)
            print(" schemaRef:", m.group(1) if m else None)
            # continue scanning rest
            buf = head.encode("utf-8", errors="ignore")
            while True:
                chunk = f.read(8 * 1024 * 1024)
                if not chunk:
                    break
                buf += chunk
                text = buf.decode("utf-8", errors="ignore")
                for k in keys:
                    hits[k] += text.count(k)
                buf = buf[-3000:]
        # recount head too roughly already included
        print(" hits:", hits)


def main():
    for zp in sorted(BASE.glob("*.zip")):
        scan_zip(zp)


if __name__ == "__main__":
    main()
