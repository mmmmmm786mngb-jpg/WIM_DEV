#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Top fantasy/sci-fi books for July by positive Flibusta reviews.
"""

from __future__ import annotations

import json
import re
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from flibusta_new import (
    DEFAULT_BASE,
    build_page_url,
    build_proxies,
    detect_proxy_port,
    deduplicate_books,
    fetch_html,
    parse_books,
    safe_print,
)

FANTASY_KEYWORDS = (
    "фантаст",
    "фэнтези",
    "popадан",
    "попадан",
    "realrpg",
    "космическ",
    "космо",
    "ужас",
    "horror",
    "мисти",
    "бoeвая",
    "боевая",
    "героическ",
    "научная",
    "социально-психолог",
    "античн",
    "стимпанк",
    "cyber",
    "кибер",
    "постапок",
    "детективная фантаст",
    "юмористическая фантаст",
    "сказк",
)

POSITIVE_SCORES = {
    "отлично": 5,
    "хорошо": 4,
    "неплохо": 3,
    "удовлетворительно": 2,
    "плохо": 1,
    "нечитаемо": 0,
    "мусор": 0,
    "отврат": 0,
}

GENRE_GROUPS = [
    ("Научная фантастика", ("научная фантастика", "космическая фантастика", "social", "социально-психологическая")),
    ("Фэнтези", ("фэнтези", "героическая фантастика", "приключенческое фэнтези", "бытовое фэнтези", "детская фантастика: фэнтези")),
    ("Любовное фэнтези", ("любовное фэнтези", "любовно-фантастические")),
    ("Боевая фантастика", ("боевая фантастика", "военная фантастика")),
    ("Попаданцы и альтернативная история", ("попаданцы", "альтернативная история", "realrpg", "литрпг")),
    ("Ужасы и мистика", ("ужасы", "мистика", "триллер")),
    ("Детская фантастика", ("детская фантастика", "детская фэнтези")),
    ("Юмористическая фантастика", ("юмористическая фантастика", "юмористическое фэнтези")),
]


@dataclass
class BookRating:
    book_id: str
    title: str
    author: str
    date: str
    genres: list[str]
    url: str
    recommend_count: int = 0
    rating_avg: float = 0.0
    rating_count: int = 0
    positive_reviews: int = 0
    neutral_reviews: int = 0
    negative_reviews: int = 0
    review_samples: list[str] = field(default_factory=list)
    score: float = 0.0


def is_fantasy(genres: list[str]) -> bool:
    text = " ".join(genres).lower()
    return any(keyword in text for keyword in FANTASY_KEYWORDS)


def is_july_2026(date_text: str) -> bool:
    parts = date_text.split(".")
    return len(parts) == 3 and parts[1] == "07" and parts[2] == "2026"


def date_sort_key(date_text: str) -> tuple[int, int, int]:
    day, month, year = date_text.split(".")
    return int(year), int(month), int(day)


def review_score(score_text: str) -> int:
    low = score_text.lower().strip()
    for key, value in sorted(POSITIVE_SCORES.items(), key=lambda item: -len(item[0])):
        if key in low:
            return value
    return 0


def parse_ratings(html: str, book_id: str) -> dict:
    recommend_match = re.search(r"рекомендовали\s+(\d+)", html, re.I)
    recommend_count = int(recommend_match.group(1)) if recommend_match else 0

    rating_avg = 0.0
    rating_count = 0

    summary_match = re.search(
        r"Оценки:\s*(\d+),\s*от\s+(\d+)\s+до\s+(\d+),\s*среднее\s+([\d.]+)",
        html,
        re.I,
    )
    if summary_match:
        rating_count = int(summary_match.group(1))
        rating_avg = float(summary_match.group(4))
    else:
        newann_match = re.search(r"id='newann'.*?Оценки:\s*([^<]+)", html, re.S | re.I)
        if newann_match:
            raw = newann_match.group(1).strip()
            single_match = re.match(r"(\d+)\s*:\s*(\d+)", raw)
            if single_match:
                left = int(single_match.group(1))
                right = int(single_match.group(2))
                if right <= 5 and left > 5:
                    rating_count, rating_avg = left, float(right)
                elif left <= 5 and right > 5:
                    rating_count, rating_avg = right, float(left)
                elif left <= 5:
                    rating_count, rating_avg = 1, float(max(left, right))
                else:
                    rating_count, rating_avg = max(left, right), float(min(left, right))
            else:
                pairs = re.findall(r"(\d+)\s*:\s*(\d+)", raw)
                total = 0
                weighted = 0.0
                for stars, count in pairs:
                    stars_i = int(stars)
                    count_i = int(count)
                    if stars_i <= 5:
                        total += count_i
                        weighted += stars_i * count_i
                    elif count_i <= 5:
                        total += stars_i
                        weighted += count_i * stars_i
                if total:
                    rating_count = total
                    rating_avg = weighted / total

    reviews: list[tuple[str, str]] = []
    soup = BeautifulSoup(html, "lxml")
    for span in soup.select(f"span.container_{book_id}"):
        text = span.get_text("\n", strip=True)
        score_match = re.search(r"Оценка:\s*([^\n/]+)", text, re.I)
        score = score_match.group(1).strip() if score_match else ""
        body = text
        if score_match:
            body = text.split(score_match.group(0), 1)[-1].strip()
        reviews.append((score, body[:250]))

    positive = sum(1 for score, _ in reviews if review_score(score) >= 4)
    neutral = sum(1 for score, _ in reviews if review_score(score) == 3)
    negative = sum(1 for score, _ in reviews if 0 < review_score(score) < 3)

    composite = (
        positive * 10
        + recommend_count * 5
        + rating_avg * rating_count
        + (rating_count if rating_avg >= 4 else 0)
    )

    return {
        "recommend_count": recommend_count,
        "rating_avg": round(rating_avg, 2),
        "rating_count": rating_count,
        "positive_reviews": positive,
        "neutral_reviews": neutral,
        "negative_reviews": negative,
        "review_samples": [f"{s}: {t[:120]}" for s, t in reviews[:3] if s],
        "score": round(composite, 2),
    }


def collect_july_fantasy(session: requests.Session, max_pages: int = 40) -> list:
    books = []
    seen_july = False
    for page in range(1, max_pages + 1):
        url = build_page_url(DEFAULT_BASE, "/new/655427", page)
        safe_print(f"List page {page}: {url}")
        html = fetch_html(session, url, 90)
        page_books = parse_books(html, DEFAULT_BASE, page)
        if not page_books:
            break

        page_july = [book for book in page_books if is_july_2026(book.date)]
        if page_july:
            seen_july = True
        books.extend(page_july)

        dates = [book.date for book in page_books if book.date]
        if dates and seen_july:
            oldest = min(dates, key=date_sort_key)
            if not is_july_2026(oldest):
                safe_print(f"Stop at page {page}, oldest date {oldest}")
                break
        time.sleep(0.3)

    fantasy = [book for book in deduplicate_books(books) if is_fantasy(book.genres)]
    fantasy.sort(key=lambda book: date_sort_key(book.date), reverse=True)
    return fantasy


def fetch_one_book(book, proxy_port: int) -> BookRating | None:
    session = requests.Session()
    session.proxies.update(build_proxies(proxy_port))
    session.headers.update({"User-Agent": "FlibustaFantasyTop/1.0"})
    try:
        html = fetch_html(session, book.url, 90)
        data = parse_ratings(html, book.book_id)
    except requests.RequestException:
        return None

    return BookRating(
        book_id=book.book_id,
        title=book.title,
        author=book.author,
        date=book.date,
        genres=book.genres,
        url=book.url,
        **data,
    )


def fetch_book_ratings(books: list, proxy_port: int, workers: int = 8) -> list[BookRating]:
    result: list[BookRating] = []
    total = len(books)
    completed = 0

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(fetch_one_book, book, proxy_port): book for book in books}
        for future in as_completed(futures):
            completed += 1
            if completed % 25 == 0 or completed == total:
                safe_print(f"Progress {completed}/{total}")
            rated = future.result()
            if rated is not None:
                result.append(rated)

    result.sort(key=lambda item: item.book_id, reverse=True)
    return result


def assign_genre_groups(book: BookRating) -> list[str]:
    text = " ".join(book.genres).lower()
    groups: list[str] = []
    for group_name, markers in GENRE_GROUPS:
        if any(marker in text for marker in markers):
            groups.append(group_name)
    if not groups:
        groups.append("Прочая фантастика")
    return groups


def top_by_genre(books: list[BookRating], top_n: int = 3) -> dict[str, list[BookRating]]:
    grouped: dict[str, list[BookRating]] = defaultdict(list)
    for book in books:
        for group in assign_genre_groups(book):
            grouped[group].append(book)

    tops: dict[str, list[BookRating]] = {}
    for group, items in grouped.items():
        ranked = sorted(
            items,
            key=lambda book: (
                book.positive_reviews,
                book.recommend_count,
                book.rating_avg * book.rating_count,
                book.rating_avg,
                book.rating_count,
            ),
            reverse=True,
        )
        tops[group] = ranked[:top_n]
    return dict(sorted(tops.items(), key=lambda item: item[0]))


def main() -> int:
    port = detect_proxy_port(None)
    session = requests.Session()
    session.proxies.update(build_proxies(port))
    session.headers.update({"User-Agent": "FlibustaFantasyTop/1.0"})

    cache_path = Path(__file__).resolve().parent / "data" / "july_fantasy_ratings.json"
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    books = collect_july_fantasy(session)
    safe_print(f"July fantasy books: {len(books)}")

    rated = fetch_book_ratings(books, port)
    cache_path.write_text(
        json.dumps([asdict(item) for item in rated], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    tops = top_by_genre(rated, top_n=3)
    rated_any = [book for book in rated if book.positive_reviews or book.rating_count or book.recommend_count]

    safe_print("")
    safe_print(f"Books with ratings/reviews: {len(rated_any)} / {len(rated)}")
    safe_print("")

    for group, items in tops.items():
        safe_print("=" * 80)
        safe_print(group)
        safe_print("-" * 80)
        shown = 0
        for book in items:
            if book.positive_reviews == 0 and book.rating_count == 0 and book.recommend_count == 0:
                continue
            shown += 1
            safe_print(
                f"{shown}. [{book.date}] {book.title} | {book.author} | "
                f"otzyvy+={book.positive_reviews}, rekom={book.recommend_count}, "
                f"ocenki={book.rating_avg} ({book.rating_count})"
            )
            for sample in book.review_samples[:1]:
                safe_print(f"   -> {sample}")
        if shown == 0:
            safe_print("Net knig s polozhitelnymi otzyvami/ocenkami v etom zhanre za iyul")

    return 0


if __name__ == "__main__":
    sys.exit(main())
