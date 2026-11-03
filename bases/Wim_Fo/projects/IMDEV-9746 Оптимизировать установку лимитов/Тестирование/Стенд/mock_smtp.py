# -*- coding: utf-8 -*-
"""Заглушка SMTP-сервера для теста писем обработки распространения правил лимитов на dev ФО (IMDEV-9746).

Принимает письма без авторизации и шифрования и сохраняет каждое в results/mail/<номер>.eml; строка о письме
дописывается в results/mail/index.log. Писем никуда не пересылает.

    python mock_smtp.py            слушает 127.0.0.1:18525
"""
import datetime
import os
import smtpd  # noqa: deprecated - модуль есть в Python 3.11, отдельная зависимость не нужна
import asyncore
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MAIL_DIR = os.path.join(HERE, "results", "mail")
HOST, PORT = "127.0.0.1", 18525


class Server(smtpd.SMTPServer):
    def process_message(self, peer, mailfrom, rcpttos, data, **kwargs):
        os.makedirs(MAIL_DIR, exist_ok=True)
        number = len([n for n in os.listdir(MAIL_DIR) if n.endswith(".eml")]) + 1
        name = f"{number:04d}.eml"
        with open(os.path.join(MAIL_DIR, name), "wb") as f:
            f.write(data if isinstance(data, bytes) else data.encode("utf-8"))
        with open(os.path.join(MAIL_DIR, "index.log"), "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} {name} from={mailfrom} to={','.join(rcpttos)} "
                    f"bytes={len(data)}\n")
        return None


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    Server((HOST, PORT), None, decode_data=False)
    print(f"Заглушка SMTP: {HOST}:{PORT}, письма в {MAIL_DIR}", flush=True)
    asyncore.loop()


if __name__ == "__main__":
    main()
