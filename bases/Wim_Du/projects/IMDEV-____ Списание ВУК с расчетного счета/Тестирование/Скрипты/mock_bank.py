# -*- coding: utf-8 -*-
"""Заглушка веб-сервиса выписок ВТБ для стенда (кнопка "Прочитать" в Загрузке выписок ДУ).

Обработка обращается к http://AMAPTIBCO:8890/BankReports/... (адрес из макета WSDL); на этой машине AMAPTIBCO
в hosts указывает на 127.0.0.1. Заглушка на любой POST отвечает SOAP-конвертом с элементом Корень из файла
mock\\statement_<сценарий>.xml; сценарий берется из mock\\current.txt (переключается без перезапуска).
Каждый запрос 1С сохраняется в mock\\request_<время>.xml.

python mock_bank.py            - слушать 127.0.0.1:8890
"""
import datetime as dt
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
MOCK = os.path.join(HERE, "mock")


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        stamp = dt.datetime.now().strftime("%H%M%S")
        with open(os.path.join(MOCK, f"request_{stamp}.xml"), "wb") as f:
            f.write(body)
        with open(os.path.join(MOCK, "current.txt"), encoding="utf-8") as f:
            kind = f.read().strip()
        with open(os.path.join(MOCK, f"statement_{kind}.xml"), encoding="utf-8") as f:
            root = f.read().strip()
        answer = ('<?xml version="1.0" encoding="UTF-8"?>'
                  '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"><soap:Body>'
                  f'{root}</soap:Body></soap:Envelope>').encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/xml; charset=utf-8")
        self.send_header("Content-Length", str(len(answer)))
        self.end_headers()
        self.wfile.write(answer)
        print(stamp, "POST", self.path, "->", kind, len(answer), "байт", flush=True)

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"mock bank statements")

    def log_message(self, *args):
        pass


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    os.makedirs(MOCK, exist_ok=True)
    print("заглушка выписок: 127.0.0.1:8890", flush=True)
    HTTPServer(("127.0.0.1", 8890), Handler).serve_forever()


if __name__ == "__main__":
    main()
