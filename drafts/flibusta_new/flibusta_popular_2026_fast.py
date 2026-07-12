#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bystryy poisk: top skachivaniy + proverka zhanra/avtora za 2026."""

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

STAT_PAGES = [("/stat/24", "stat_day"), ("/stat/w", "stat_week"), ("/stat/b", "stat_popular")]
LOVE = ("любовное фэнтези", "любовно-фантаст", "любовные романы", "эротическая литература")
FANT = ("фантаст", "фэнтези", "попадан", "realrpg", "литрpg", "литрпг", "ужас", "мисти", "космическ", "альтернативная история")
FEM_PAT = re.compile(r"\b[\w-]+(?:овна|евна|ична|инична)\b", re.I)
MALE_PAT = re.compile(r"\b[\w-]+(?:ович|евич|ич)\b", re.I)
FEM_NAMES = {
    "ольга", "анна", "елена", "марина", "наталья", "татьяна", "ирина", "мария", "виктория",
    "людмила", "светлана", "евгения", "галина", "надежда", "валентина", "любовь", "полина",
    "алекса", "амалия", "дарина", "мила", "лена", "юлия", "диана", "екатерина", "алёна",
    "алена", "ксения", "оксана", "анастасия", "милана", "майя", "римма", "злата", "шарлотта",
    "elena", "olga", "maria", "natalia", "tatiana", "victoria", "мarta", "марта",
}


@dataclass
class Book:
    book_id: str
    title: str
    author: str = ""
    upload_date: str = ""
    genres: list[str] = field(default_factory=list)
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
        return s


def is_female(name: str) -> bool:
    if FEM_PAT.search(name):
        return True
    if MALE_PAT.search(name):
        return False
    first = re.split(r"[\s(]+", name.strip())[0].lower().replace("ё", "е")
    return first in FEM_NAMES


def fetch(path: str, port: int) -> str:
    s = requests.Session()
    s.proxies.update(build_proxies(port))
    return fetch_html(s, urljoin(DEFAULT_BASE, path), 120)


def parse_stat(html: str) -> list[tuple[int, str, str, str]]:
    soup = BeautifulSoup(html, "lxml")
    out = []
    pos = 0
    for li in soup.find_all("li"):
        links = li.find_all("a", href=True)
        book = next((a for a in links if re.fullmatch(r"/b/\d+", a["href"])), None)
        author = next((a for a in links if re.fullmatch(r"/a/\d+", a["href"])), None)
        if book:
            pos += 1
            out.append((pos, book["href"].split("/")[-1], book.get_text(strip=True), author.get_text(strip=True) if author else ""))
    return out


def enrich(book: Book, port: int) -> Book:
    s = requests.Session()
    s.proxies.update(build_proxies(port))
    html = fetch_html(s, urljoin(DEFAULT_BASE, f"/b/{book.book_id}"), 90)
    m = re.search(r"Добавлена:\s*(\d{2}\.\d{2}\.\d{4})", html)
    if m:
        book.upload_date = m.group(1)
        book.year_2026 = book.upload_date.endswith(".2026")
    if "2026" in book.title or "Фантастика 2026" in html or "издание 2026" in html:
        book.year_2026 = True
    soup = BeautifulSoup(html, "lxml")
    book.genres = [a.get_text(strip=True) for a in soup.select("p.genre a.genre")]
    if not book.author:
        a = soup.find("a", href=re.compile(r"^/a/\d+$"))
        if a:
            book.author = a.get_text(strip=True)
    return book


def ok(b: Book) -> bool:
    if not b.year_2026 and "2026" not in b.title:
        return False
    if is_female(b.author):
        return False
    g = " ".join(b.genres).lower()
    if any(x in g for x in LOVE):
        return False
    if b.genres and not any(x in g for x in FANT):
        return False
    return True


def main() -> int:
    port = detect_proxy_port(None)
    store: dict[str, Book] = {}
    for path, field in STAT_PAGES:
        for pos, bid, title, author in parse_stat(fetch(path, port)):
            b = store.get(bid) or Book(book_id=bid, title=title, author=author, year_2026=True)
            setattr(b, field, pos)
            store[bid] = b
        safe_print(f"{path}: ok")

    books = list(store.values())
    safe_print(f"Unikalno: {len(books)}. Proverka kartochek...")
    out_books: list[Book] = []
    with ThreadPoolExecutor(max_workers=10) as pool:
        futs = [pool.submit(enrich, b, port) for b in books]
        for i, fut in enumerate(as_completed(futs), 1):
            if i % 30 == 0:
                safe_print(f"  {i}/{len(books)}")
            out_books.append(fut.result())

    hits = [b for b in out_books if ok(b)]
    hits.sort(key=lambda x: x.score, reverse=True)

    path = Path(__file__).resolve().parent / "data" / "popular_2026_stat_only.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            [{**asdict(b), "score": b.score} for b in hits[:30]],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    safe_print("")
    safe_print("TOP (fantastika/fentezi, 2026, muzh-avtory, ne lyubovnoe):")
    for i, b in enumerate(hits[:15], 1):
        safe_print(f"{i:2}. {b.title[:55]} | {b.author[:30]}")
        safe_print(
            f"    {b.upload_date or '?'} | den={b.stat_day or '-'} ned={b.stat_week or '-'} "
            f"pop={b.stat_popular or '-'} | {', '.join(b.genres[:3])}"
        )
    safe_print(f"JSON: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
