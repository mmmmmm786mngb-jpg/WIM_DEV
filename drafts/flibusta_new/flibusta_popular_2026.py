#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Samye chitaemye knigi Flibusta 2026: fantastika/fentezi, bez lyubovnogo fentezi, bez zhenshchin-avtorov.
Istochnik: top skachivaniy (/stat/24, /stat/w, /stat/b) + lidery zhanrov 2026 (rank <= 150).
"""

from __future__ import annotations

import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from flibusta_new import DEFAULT_BASE, build_proxies, detect_proxy_port, fetch_html, safe_print

STAT_PAGES = [
    ("/stat/24", "stat_day"),
    ("/stat/w", "stat_week"),
    ("/stat/b", "stat_popular"),
]

GENRE_SLUGS = [
    "sf_action", "sf_fantasy", "sf_heroic", "sf_space", "sf_social", "sf_epic",
    "sf_etc", "sf_detective", "sf_humor", "sf_horror", "child_sf_hronoopera",
    "adventure_fantasy", "historical_fantasy", "slavic_fantasy", "russian_fantasy",
    "asian_fantasy", "nsf", "sf_technofantasy", "everyday_fantasy",
]

LOVE_MARKERS = ("любовное фэнтези", "любовно-фантаст", "любовные романы", "эротическая литература")
FANTASY_MARKERS = ("фантаст", "фэнтези", "popадан", "realrpg", "литрpg", "литрпг", "ужас", "мисти", "космическ")

FEMALE_PAT = re.compile(r"\b[\w-]+(?:овна|евна|ична|инична)\b", re.I)
MALE_PAT = re.compile(r"\b[\w-]+(?:ович|евич|ич)\b", re.I)
FEMALE_NAMES = {
    "ольга", "анна", "елена", "марина", "наталья", "татьяна", "ирина", "мария", "виктория",
    "людмила", "светлана", "евгения", "галина", "надежда", "валентина", "любовь", "полина",
    "алекса", "амалия", "дарина", "мила", "лена", "юлия", "диана", "екатерина", "алёна",
    "алена", "ксения", "оксана", "анастасия", "милана", "майя", "римма", "злата", "шарлотта",
    "сara", "сara", "сara", "мaria", "elena", "olga", "natalia", "tatiana", "victoria",
}

BOOK_RE = re.compile(
    r"(?:<h5><a href=\"/a/\d+\">([^<]*)</a></h5>\s*)?(\d+)\s*<a href=\"/b/(\d+)\">([^<]+)</a>",
    re.I,
)


@dataclass
class BookStat:
    book_id: str
    title: str
    author: str = ""
    upload_date: str = ""
    genres: set[str] = field(default_factory=set)
    best_rank: int = 999999
    stat_day: int = 0
    stat_week: int = 0
    stat_popular: int = 0
    year_2026: bool = False

    @property
    def score(self) -> float:
        s = 0.0
        if self.stat_day:
            s += (101 - self.stat_day) * 5
        if self.stat_week:
            s += (101 - self.stat_week) * 3
        if self.stat_popular:
            s += (101 - self.stat_popular) * 2
        if self.best_rank < 999999:
            s += max(0, 200 - self.best_rank)
        return s


def is_female(name: str) -> bool:
    name = name.strip()
    if not name:
        return False
    if FEMALE_PAT.search(name):
        return True
    if MALE_PAT.search(name):
        return False
    first = re.split(r"[\s(]+", name)[0].lower().replace("ё", "е")
    return first in FEMALE_NAMES


def fetch(path: str, port: int, timeout: int = 120) -> str:
    s = requests.Session()
    s.proxies.update(build_proxies(port))
    s.headers.update({"User-Agent": "FlibustaPopular2026/2.0"})
    return fetch_html(s, urljoin(DEFAULT_BASE, path), timeout)


def parse_stat(html: str) -> list[tuple[int, str, str, str]]:
    soup = BeautifulSoup(html, "lxml")
    out = []
    pos = 0
    for li in soup.find_all("li"):
        links = li.find_all("a", href=True)
        book = next((a for a in links if re.fullmatch(r"/b/\d+", a["href"])), None)
        author = next((a for a in links if re.fullmatch(r"/a/\d+", a["href"])), None)
        if not book:
            continue
        pos += 1
        out.append((pos, book["href"].split("/")[-1], book.get_text(strip=True), author.get_text(strip=True) if author else ""))
    return out


def parse_genre(html: str) -> list[tuple[int, str, str, str, str]]:
    out = []
    chunks = re.split(r"<h4>(\d{2}\.\d{2}\.(2026|2025))</h4>", html)
    date = ""
    last_author = ""
    for chunk in chunks:
        if re.fullmatch(r"\d{2}\.\d{2}\.2026", chunk):
            date = chunk
            continue
        if chunk == "2025":
            break
        if not date:
            continue
        for m in BOOK_RE.finditer(chunk):
            author = (m.group(1) or "").strip()
            if author:
                last_author = author
            rank = int(m.group(2))
            if rank > 150:
                continue
            out.append((rank, m.group(3), m.group(4).strip(), last_author, date))
    return out


def enrich(book: BookStat, port: int) -> BookStat:
    try:
        html = fetch(f"/b/{book.book_id}", port, 90)
    except requests.RequestException:
        return book
    soup = BeautifulSoup(html, "lxml")
    m = re.search(r"Дobavlena:\s*(\d{2}\.\d{2}\.\d{4})", html)
    if not m:
        m = re.search(r"Добавлена:\s*(\d{2}\.\d{2}\.\d{4})", html)
    if m:
        book.upload_date = m.group(1)
        book.year_2026 = book.upload_date.endswith(".2026")
    if re.search(r"2026", book.title) or "Фантастика 2026" in html or "издание 2026" in html:
        book.year_2026 = True
    genres = [a.get_text(strip=True) for a in soup.select("p.genre a.genre")]
    book.genres.update(genres)
    if not book.author:
        a = soup.find("a", href=re.compile(r"^/a/\d+$"))
        if a:
            book.author = a.get_text(strip=True)
    return book


def ok_book(book: BookStat) -> bool:
    if not book.year_2026 and "2026" not in book.title:
        return False
    if is_female(book.author):
        return False
    g = " ".join(book.genres).lower()
    if any(x in g for x in LOVE_MARKERS) or any(x in book.title.lower() for x in ("любовн", "любовное фэнтези")):
        return False
    if book.genres and not any(x in g for x in FANTASY_MARKERS):
        return False
    return True


def merge(store: dict[str, BookStat], item: BookStat) -> None:
    cur = store.get(item.book_id)
    if not cur:
        store[item.book_id] = item
        return
    if item.author:
        cur.author = item.author
    if item.title:
        cur.title = item.title
    cur.genres.update(item.genres)
    cur.best_rank = min(cur.best_rank, item.best_rank)
    cur.stat_day = cur.stat_day or item.stat_day
    cur.stat_week = cur.stat_week or item.stat_week
    cur.stat_popular = cur.stat_popular or item.stat_popular
    cur.year_2026 = cur.year_2026 or item.year_2026
    if item.upload_date:
        cur.upload_date = item.upload_date


def main() -> int:
    port = detect_proxy_port(None)
    books: dict[str, BookStat] = {}

    safe_print("Stat-stranitsy...")
    for path, field_name in STAT_PAGES:
        html = fetch(path, port, 120)
        rows = parse_stat(html)
        for pos, bid, title, author in rows:
            item = BookStat(book_id=bid, title=title, author=author, year_2026=True)
            setattr(item, field_name, pos)
            merge(books, item)
        safe_print(f"  {path}: {len(rows)}")

    safe_print("Zhanry 2026 (rank <= 150)...")
    for slug in GENRE_SLUGS:
        try:
            html = fetch(f"/g/{slug}", port, 180)
        except requests.RequestException as exc:
            safe_print(f"  skip {slug}: {exc}")
            continue
        rows = parse_genre(html)
        for rank, bid, title, author, date in rows:
            item = BookStat(book_id=bid, title=title, author=author, upload_date=date, best_rank=rank, year_2026=True)
            item.genres.add(slug)
            merge(books, item)
        safe_print(f"  {slug}: {len(rows)}")

    candidates = list(books.values())
    safe_print(f"Obogashchenie {len(candidates)} kartochek...")
    enriched: dict[str, BookStat] = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        futs = {pool.submit(enrich, b, port): b.book_id for b in candidates}
        done = 0
        for fut in as_completed(futs):
            done += 1
            if done % 40 == 0:
                safe_print(f"  {done}/{len(candidates)}")
            b = fut.result()
            enriched[b.book_id] = b

    result = [enriched.get(b.book_id, b) for b in candidates]
    result = [b for b in result if ok_book(b)]
    result.sort(key=lambda x: x.score, reverse=True)

    out = Path(__file__).resolve().parent / "data" / "popular_2026_male_fantasy.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = []
    for b in result[:40]:
        d = asdict(b)
        d["genres"] = sorted(b.genres)
        d["score"] = b.score
        payload.append(d)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    safe_print("")
    safe_print("TOP-20 samyh chitaemyh za 2026:")
    safe_print("-" * 90)
    for i, b in enumerate(result[:20], 1):
        safe_print(f"{i:2}. {b.title[:58]} | {b.author[:32]}")
        safe_print(
            f"    data={b.upload_date or '?'} | top_dnya={b.stat_day or '-'} | "
            f"top_ned={b.stat_week or '-'} | rank_zhanr={b.best_rank if b.best_rank < 999999 else '-'}"
        )
        if b.genres:
            safe_print(f"    {', '.join(sorted(b.genres))[:70]}")
    safe_print(f"\nJSON: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
