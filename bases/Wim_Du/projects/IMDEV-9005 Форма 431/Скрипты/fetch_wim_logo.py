#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fetch candidate logo URLs from wealthim.ru."""

import pathlib
import re
import urllib.request

OUT = pathlib.Path(__file__).resolve().parents[1] / "Обработки" / "_logo_extract"
URL = "https://www.wealthim.ru/"


def main() -> None:
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "wealthim_home.html").write_text(html, encoding="utf-8")

    urls = set(re.findall(r'(?:src|href)=["\']([^"\']+\.(?:png|jpg|jpeg|svg|webp))["\']', html, re.I))
    urls |= set(re.findall(r'url\(["\']?([^"\')]+\.(?:png|jpg|jpeg|svg|webp))["\']?\)', html, re.I))

    print("urls", len(urls))
    for u in sorted(urls):
        print(u)

    for m in re.finditer(r".{0,60}logo.{0,100}", html, re.I):
        print("CTX", m.group(0).replace("\n", " ")[:160])

    for u in sorted(urls):
        low = u.lower()
        if "logo" not in low and "brand" not in low and "header" not in low:
            continue
        abs_url = urllib.request.urljoin(URL, u)
        name = pathlib.Path(u.split("?")[0]).name or "logo.bin"
        try:
            data = urllib.request.urlopen(
                urllib.request.Request(abs_url, headers={"User-Agent": "Mozilla/5.0"}),
                timeout=30,
            ).read()
            fp = OUT / ("web_" + name)
            fp.write_bytes(data)
            print("DL", abs_url, "->", fp.name, len(data))
        except Exception as exc:  # noqa: BLE001
            print("FAIL", abs_url, exc)


if __name__ == "__main__":
    main()
