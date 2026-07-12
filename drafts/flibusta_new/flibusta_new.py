#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Чтение новинок Flibusta через Tor (SOCKS5).

Примеры:
  python flibusta_new.py --url "/new/655427?page=2"
  python flibusta_new.py --pages 1-3
  python flibusta_new.py --pages 1 --html-report reports/page1.html
  python flibusta_new.py --save-state data/seen.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin, urlparse, parse_qs

import requests
from bs4 import BeautifulSoup

DEFAULT_BASE = "http://flibustaongezhld6dibs2dps6vm4nvqg2kp7vgowbu76tzopgnhazqd.onion"
DEFAULT_PROXY_PORTS = (9150, 9050)


@dataclass
class BookEntry:
    book_id: str
    title: str
    author: str
    date: str
    genres: list[str]
    size: str
    url: str
    page: int


def safe_print(text: str) -> None:
    """Bezopasnyy vyvod v konsol (tolko ASCII pri neobhodimosti)."""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", "replace").decode("ascii"))


def build_proxies(port: int) -> dict[str, str]:
    proxy = f"socks5h://127.0.0.1:{port}"
    return {"http": proxy, "https": proxy}


def detect_proxy_port(explicit_port: int | None) -> int:
    if explicit_port:
        return explicit_port

    import socket

    for port in DEFAULT_PROXY_PORTS:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.5)
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                return port

    raise RuntimeError(
        "Tor ne dostupen. Zapustite Tor Browser ili sluzhbu tor (porty 9150/9050)."
    )


def parse_pages_spec(spec: str) -> list[int]:
    pages: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            left, right = part.split("-", 1)
            start = int(left)
            end = int(right)
            if start > end:
                start, end = end, start
            pages.update(range(start, end + 1))
        else:
            pages.add(int(part))
    return sorted(pages)


def normalize_url(base: str, url: str) -> str:
    if url.startswith("http://") or url.startswith("https://"):
        return url
    return urljoin(base.rstrip("/") + "/", url.lstrip("/"))


def extract_path_and_page(full_url: str, base: str) -> tuple[str, int]:
    parsed = urlparse(full_url)
    base_parsed = urlparse(base)
    path = parsed.path or "/new/655427"
    query = parse_qs(parsed.query)
    page = int(query.get("page", ["1"])[0])
    if parsed.netloc and parsed.netloc != base_parsed.netloc:
        return path, page
    return path, page


def fetch_html(session: requests.Session, url: str, timeout: int) -> str:
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or "utf-8"
    return response.text


def parse_books(html: str, base: str, page: int) -> list[BookEntry]:
    soup = BeautifulSoup(html, "lxml")
    books: list[BookEntry] = []
    current_date = ""

    for element in soup.find_all(["h4", "div"]):
        if element.name == "h4":
            current_date = element.get_text(strip=True)
            continue

        classes = element.get("class") or []
        if element.name != "div" or not any(class_name.startswith("g-") for class_name in classes):
            continue

        title_link = element.find("a", href=re.compile(r"^/b/\d+$"))
        if title_link is None:
            continue

        book_id = title_link["href"].split("/")[-1]
        author_link = element.find("a", href=re.compile(r"^/a/\d+"))
        size_span = element.find("span")
        genres = [genre.get_text(strip=True) for genre in element.select("p.genre a.genre")]

        books.append(
            BookEntry(
                book_id=book_id,
                title=title_link.get_text(strip=True),
                author=author_link.get_text(strip=True) if author_link else "",
                date=current_date,
                genres=genres,
                size=size_span.get_text(strip=True) if size_span else "",
                url=urljoin(base, title_link["href"]),
                page=page,
            )
        )

    return books


def deduplicate_books(books: Iterable[BookEntry]) -> list[BookEntry]:
    seen: set[str] = set()
    result: list[BookEntry] = []
    for book in books:
        if book.book_id in seen:
            continue
        seen.add(book.book_id)
        result.append(book)
    return result


def load_state(path: Path) -> set[str]:
    if not path.exists():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    return set(data.get("book_ids", []))


def save_state(path: Path, known_ids: set[str], books: list[BookEntry]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "book_ids": sorted(known_ids),
        "last_books": [asdict(book) for book in books[:100]],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def render_html_report(
    books: list[BookEntry],
    source_url: str,
    output_path: Path,
    only_new: list[BookEntry] | None = None,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    new_count = len(only_new) if only_new is not None else 0

    rows = []
    for book in books:
        is_new = only_new is not None and any(item.book_id == book.book_id for item in only_new)
        row_class = "new" if is_new else ""
        genres = ", ".join(book.genres) if book.genres else "-"
        rows.append(
            f"""
            <tr class="{row_class}">
              <td>{book.date or "-"}</td>
              <td><a href="{book.url}">{book.title}</a></td>
              <td>{book.author or "-"}</td>
              <td>{genres}</td>
              <td>{book.size or "-"}</td>
              <td>{book.page}</td>
            </tr>
            """
        )

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <title>Flibusta new books</title>
  <style>
    body {{ font-family: Segoe UI, Arial, sans-serif; margin: 24px; color: #222; }}
    h1 {{ color: #17a2b8; }}
    .info {{ background: #e8f4f8; padding: 12px 16px; border-radius: 6px; margin-bottom: 20px; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #ddd; padding: 8px 10px; vertical-align: top; }}
    th {{ background: #f5f5f5; text-align: left; }}
    tr.new {{ background: #fff8dc; }}
    a {{ color: #0056b3; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
  </style>
</head>
<body>
  <h1>Novinki Flibusta</h1>
  <div class="info">
    <div><strong>Istochnik:</strong> {source_url}</div>
    <div><strong>Sformirovano:</strong> {generated_at}</div>
    <div><strong>Vsego knig:</strong> {len(books)}</div>
    <div><strong>Novyh (otnositelno state):</strong> {new_count}</div>
  </div>
  <table>
    <thead>
      <tr>
        <th>Data</th>
        <th>Nazvanie</th>
        <th>Avtor</th>
        <th>Zhanry</th>
        <th>Razmer</th>
        <th>Stranitsa</th>
      </tr>
    </thead>
    <tbody>
      {''.join(rows)}
    </tbody>
  </table>
</body>
</html>
"""
    output_path.write_text(html, encoding="utf-8")


def print_books(books: list[BookEntry], title: str) -> None:
    safe_print("")
    safe_print(title)
    safe_print("-" * 80)
    for book in books:
        genres = ", ".join(book.genres[:3]) if book.genres else "-"
        safe_print(
            f"[{book.date}] {book.title} | {book.author or '-'} | {genres} | str.{book.page}"
        )


def build_page_url(base: str, path: str, page: int) -> str:
    if page <= 1:
        return urljoin(base.rstrip("/") + "/", path.lstrip("/"))
    separator = "&" if "?" in path else "?"
    if "page=" in path:
        return urljoin(base.rstrip("/") + "/", re.sub(r"page=\d+", f"page={page}", path.lstrip("/")))
    return urljoin(base.rstrip("/") + "/", f"{path.lstrip('/')}{separator}page={page}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Chtenie novinok Flibusta cherez Tor")
    parser.add_argument(
        "--url",
        default="/new/655427?page=2",
        help="Put ili polnyy URL spiska novinok",
    )
    parser.add_argument(
        "--base",
        default=DEFAULT_BASE,
        help="Bazovyy onion-adres Flibusta",
    )
    parser.add_argument(
        "--pages",
        default="",
        help="Diapazon stranits, naprimer: 1-3 ili 2,4,5. Esli ne zadan, beretsya iz --url",
    )
    parser.add_argument(
        "--proxy-port",
        type=int,
        default=None,
        help="Port SOCKS5 proksi Tor (9150 dlya Tor Browser, 9050 dlya sluzhby tor)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=90,
        help="Taymaut zaprosa v sekundakh",
    )
    parser.add_argument(
        "--html-report",
        default="",
        help="Put k HTML-otchetu",
    )
    parser.add_argument(
        "--save-state",
        default="",
        help="JSON-fayl dlya khraneniya uzhe prosmotrennykh knig",
    )
    parser.add_argument(
        "--only-new",
        action="store_true",
        help="Pokazat tolko knigi, kotorykh net v state-fayle",
    )
    args = parser.parse_args()

    try:
        proxy_port = detect_proxy_port(args.proxy_port)
    except RuntimeError as error:
        safe_print(f"ERROR: {error}")
        return 2

    full_url = normalize_url(args.base, args.url)
    path, default_page = extract_path_and_page(full_url, args.base)
    pages = parse_pages_spec(args.pages) if args.pages else [default_page]

    session = requests.Session()
    session.proxies.update(build_proxies(proxy_port))
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) FlibustaReader/1.0",
            "Accept-Language": "ru-RU,ru;q=0.9",
        }
    )

    all_books: list[BookEntry] = []
    for page in pages:
        page_url = build_page_url(args.base, path, page)
        safe_print(f"Zagruzka: {page_url} (proxy 127.0.0.1:{proxy_port})")
        try:
            html = fetch_html(session, page_url, args.timeout)
        except requests.RequestException as error:
            safe_print(f"ERROR: ne udalos zagruzit stranitsu {page}: {error}")
            return 1
        page_books = parse_books(html, args.base, page)
        safe_print(f"  naydeno knig: {len(page_books)}")
        all_books.extend(page_books)

    books = deduplicate_books(all_books)
    known_ids = load_state(Path(args.save_state)) if args.save_state else set()
    new_books = [book for book in books if book.book_id not in known_ids] if known_ids else books

    if args.only_new and known_ids:
        print_books(new_books, f"Tolko novye knigi: {len(new_books)}")
    else:
        print_books(books, f"Vsego knig: {len(books)}")

    if args.html_report:
        report_path = Path(args.html_report)
        render_html_report(
            books=books if not args.only_new else new_books,
            source_url=full_url,
            output_path=report_path,
            only_new=new_books if known_ids else None,
        )
        safe_print(f"HTML otchet: {report_path.resolve()}")

    if args.save_state:
        state_path = Path(args.save_state)
        updated_ids = known_ids | {book.book_id for book in books}
        save_state(state_path, updated_ids, books)
        safe_print(f"State obnovlen: {state_path.resolve()} ({len(updated_ids)} knig)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
