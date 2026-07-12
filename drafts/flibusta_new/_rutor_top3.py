#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Top movies from rutor.info/new via Tor SOCKS proxy."""

import re
from pathlib import Path


def main():
    html_path = Path(__file__).with_name("_rutor_new.html")
    html = html_path.read_text(encoding="utf-8", errors="replace")

    # Only movie sections from /new page
    movie_blocks = []
    for section in ("kino", "nashe_kino", "nauchno_popularnoe"):
        block_m = re.search(
            rf'<h2><a href="/{section}">.*?</h2>(.*?)(?=<h2>|$)',
            html,
            re.S,
        )
        if block_m:
            movie_blocks.append(block_m.group(1))

    films = []
    for block in movie_blocks:
        rows = re.findall(r'<tr class="(?:gai|tum)">.*?</tr>', block, re.S)
        for row in rows:
            title_m = re.search(
                r'<a href="(/torrent/\d+[^"]*)">([^<]+)</a></td>',
                row,
            )
            if not title_m:
                continue
            link_path, title = title_m.group(1), title_m.group(2)
            title = re.sub(r"\s+", " ", title).strip()
            peers_m = re.search(
                r'class="green"[^>]*>.*?&nbsp;(\d+)</span>.*?class="red">&nbsp;(\d+)</span>',
                row,
                re.S,
            )
            if not peers_m:
                continue
            seeds = int(peers_m.group(1))
            leech = int(peers_m.group(2))
            size_m = re.search(
                r'<td align="right">([\d.]+\s*&nbsp;(?:GB|MB|KB|TB))</td>', row
            )
            size = size_m.group(1).replace("&nbsp;", " ") if size_m else "?"
            films.append(
                {
                    "title": title,
                    "seeds": seeds,
                    "leech": leech,
                    "size": size,
                    "link": "https://rutor.info" + link_path,
                }
            )

    films.sort(key=lambda x: (x["seeds"], x["seeds"] + x["leech"]), reverse=True)

    seen = set()
    unique = []
    for item in films:
        base = re.sub(
            r"\s*(BDRip|WEB-DL|WEB-DLRip|HDRip|UHD|720p|1080p|2160p|4K).*",
            "",
            item["title"],
            flags=re.I,
        ).strip()
        if base in seen:
            continue
        seen.add(base)
        unique.append(item)

    for i, item in enumerate(unique[:3], 1):
        print(f"{i}. {item['title']}")
        print(f"   Razmer: {item['size']}, sidy: {item['seeds']}, kachayut: {item['leech']}")
        print(f"   {item['link']}")
        print()


if __name__ == "__main__":
    main()
