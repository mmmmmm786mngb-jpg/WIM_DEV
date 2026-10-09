#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scan vendor CF container for IMDEV-9458 markers after zlib inflate."""

import io
import os
import sys
import zlib

from v8unpack.container import Container, Container64

CF_PATH = r"C:\1c\Cursor_1c\WORK\WIM_FIn\1Cv8_fin_2_8_9_3_вендор.cf"
OUT_DIR = r"C:\1c\Cursor_1c\WORK\WIM_FIn\_scan_2893_hits"

NEEDLES = [
    "ОставитьТолькоПарыСПулом",
    "ОставитьТолькоПарыСОборотами",
    "ЗаписатьСОбработкойКоллизииНомера",
    "ЭтоОшибкаНеуникальногоЗначения",
    "НеСоздаватьНДФЛПоКлиентамБезОборотов",
    "СчетаОборотовДляОтбораНДФЛ",
    "СоздаватьНДФЛТолькоПоПулу",
    "ПулДляОтбораНДФЛ",
    "ГруппаСчетаОборотовНДФЛ",
    "ГруппаПулОтбораНДФЛ",
    "IMDEV-9458",
    "IMDEV9458",
    "В заполнение включать только клиентов с доходами",
    "В заполнение включать только клиентов выбранного пула",
]


def safe_print(text):
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", "replace").decode("ascii"))


def join_chunks(file_obj):
    return b"".join(file_obj.data)


def inflate(raw):
    try:
        return zlib.decompress(raw, -15)
    except Exception:
        return None


def is_container(data):
    if len(data) < 8:
        return False
    if data[0:4] == b"\xFF\xFF\xFF\x7F":
        return True
    if data[0:8] == b"\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF":
        return True
    return False


def make_container(data, offset=0):
    bio = io.BytesIO(data)
    bio.seek(offset)
    first = bio.read(8)
    bio.seek(offset)
    if first[0:4] == b"\xFF\xFF\xFF\x7F":
        cont = Container()
    else:
        cont = Container64()
    cont.read(bio, offset)
    return cont


def save_hit(rel_path, data, needle):
    os.makedirs(OUT_DIR, exist_ok=True)
    safe = rel_path.replace("/", "_").replace("\\", "_")
    if len(safe) > 120:
        safe = safe[-120:]
    dest = os.path.join(OUT_DIR, safe + ".bin")
    if not os.path.exists(dest):
        with open(dest, "wb") as f:
            f.write(data)
    txt = dest + ".txt"
    if not os.path.exists(txt):
        text = None
        for enc in ("utf-8-sig", "utf-8", "utf-16-le", "cp1251"):
            try:
                text = data.decode(enc)
                break
            except Exception:
                continue
        if text:
            with open(txt, "w", encoding="utf-8") as f:
                f.write(text)
    with open(os.path.join(OUT_DIR, "hits.log"), "a", encoding="utf-8") as log:
        log.write("%s\t%s\t%d\n" % (needle, rel_path, len(data)))


def scan_bytes(data, rel_path, hits, depth):
    found_here = []
    for s in NEEDLES:
        if s.encode("utf-8") in data or s.encode("utf-16le") in data:
            found_here.append(s)
            hits.append((rel_path, s, len(data), depth))
            save_hit(rel_path, data, s)
    if found_here:
        safe_print("HIT depth=%s size=%s %s -> %s" % (depth, len(data), rel_path, ", ".join(found_here)))
    if is_container(data):
        try:
            walk_container(data, rel_path, hits, depth + 1)
        except Exception as err:
            safe_print("skip container %s: %s" % (rel_path, err))


def walk_container(data, rel_path, hits, depth):
    if depth > 8:
        return
    cont = make_container(data, 0)
    if not cont.files:
        return
    for name, file_obj in cont.files.items():
        raw = join_chunks(file_obj)
        inflated = inflate(raw)
        child = inflated if inflated is not None else raw
        child_path = rel_path + "/" + name
        scan_bytes(child, child_path, hits, depth)


def main():
    if not os.path.isfile(CF_PATH):
        safe_print("CF not found: " + CF_PATH)
        return 1
    os.makedirs(OUT_DIR, exist_ok=True)
    log_path = os.path.join(OUT_DIR, "hits.log")
    if os.path.exists(log_path):
        os.remove(log_path)
    safe_print("scan " + CF_PATH)
    with open(CF_PATH, "rb") as f:
        data = f.read()
    hits = []
    scan_bytes(data, "root", hits, 0)
    safe_print("hits total: %d" % len(hits))
    summary = os.path.join(OUT_DIR, "summary.txt")
    with open(summary, "w", encoding="utf-8") as f:
        if not hits:
            f.write("NO HITS\n")
        for item in hits:
            f.write("%s\n" % "\t".join(str(x) for x in item))
    return 0


if __name__ == "__main__":
    sys.exit(main())
