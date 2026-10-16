# -*- coding: utf-8 -*-
"""Заглушка адаптера стакана для тестовых сборок IMDEV-9531.

GET /wait?ms=1000 отвечает через указанное число миллисекунд. Ожидание - сетевое, как ответ прокси адаптера на ПРОД,
процессор сервера 1С не занимает. Запросы обслуживаются параллельно (потоки реинвестирования ждут одновременно).
GET /stats - число обслуженных запросов ожидания с запуска или последнего /reset.

    python stakan_mock.py [порт]      порт по умолчанию 18541
"""
import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

LOCK = threading.Lock()
COUNT = {"wait": 0}


class Handler(BaseHTTPRequestHandler):

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/wait":
            ms = int(parse_qs(url.query).get("ms", ["1000"])[0])
            time.sleep(ms / 1000.0)
            with LOCK:
                COUNT["wait"] += 1
            body = b"ok"
        elif url.path == "/stats":
            with LOCK:
                body = json.dumps(COUNT).encode()
        elif url.path == "/reset":
            with LOCK:
                COUNT["wait"] = 0
            body = b"reset"
        else:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 18541
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    print("stakan mock on", port, flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
