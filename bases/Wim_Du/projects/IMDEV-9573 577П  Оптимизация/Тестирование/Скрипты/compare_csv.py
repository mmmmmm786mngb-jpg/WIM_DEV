# -*- coding: utf-8 -*-
"""Побайтное сравнение двух каталогов выгрузки CSV 577-П (прежняя и потоковая обработка).

python compare_csv.py <каталог_эталон> <каталог_проверка> [отчет.txt] [--ignore колонка]

--ignore: колонка по имени заголовка не учитывается при построчном сравнении (если есть в файле).

Для каждого файла R1-R11.csv и sr_sved_purcb.csv: совпадение байтов (SHA-256), размер, метка UTF-8,
концы строк, число строк, заголовок, первые расхождения по строкам с номерами колонок.
Код возврата 0 - все файлы совпали побайтно, 1 - есть расхождения.
"""
import hashlib
import os
import sys

FILES = [f"R{n}.csv" for n in range(1, 12)] + ["sr_sved_purcb.csv"]
BOM = b"\xef\xbb\xbf"
MAX_DIFFS = 5


def describe(data):
    crlf = data.count(b"\r\n")
    lf = data.count(b"\n") - crlf
    return {
        "размер": len(data),
        "BOM": data.startswith(BOM),
        "CRLF": crlf,
        "LF": lf,
        "конец файла": "перевод строки" if data.endswith(b"\n") else "без перевода строки",
    }


IGNORE = []


def lines(data):
    text = data[len(BOM):] if data.startswith(BOM) else data
    result = text.decode("utf-8").replace("\r\n", "\n").split("\n")
    head = result[0].split("|")
    drop = [head.index(name) for name in IGNORE if name in head]
    if drop:
        result = ["|".join(v for j, v in enumerate(s.split("|")) if j not in drop) if s else s for s in result]
    return result


def compare_file(name, path_a, path_b, out):
    if not os.path.exists(path_a) or not os.path.exists(path_b):
        out.append(f"{name}: нет файла ({'эталон' if not os.path.exists(path_a) else 'проверка'})")
        return False
    a = open(path_a, "rb").read()
    b = open(path_b, "rb").read()
    if a == b:
        out.append(f"{name}: СОВПАДАЕТ побайтно, {len(a):,} байт, {len(lines(a)) - 1:,} строк, "
                   f"sha256 {hashlib.sha256(a).hexdigest()[:16]}")
        return True
    out.append(f"{name}: РАЗЛИЧАЕТСЯ")
    da, db = describe(a), describe(b)
    for key in da:
        mark = "" if da[key] == db[key] else "  <-"
        out.append(f"    {key}: {da[key]} / {db[key]}{mark}")
    la, lb = lines(a), lines(b)
    out.append(f"    строк: {len(la):,} / {len(lb):,}")
    if la == lb:
        note = f" без колонок {IGNORE}" if IGNORE else ""
        out.append(f"    текст строк совпадает{note}: значения и порядок строк те же")
        return False
    shown = 0
    for i in range(max(len(la), len(lb))):
        sa = la[i] if i < len(la) else None
        sb = lb[i] if i < len(lb) else None
        if sa == sb:
            continue
        shown += 1
        if shown > MAX_DIFFS:
            out.append("    ...")
            break
        if sa is None or sb is None:
            out.append(f"    строка {i + 1}: эталон={sa!r} проверка={sb!r}")
            continue
        ca, cb = sa.split("|"), sb.split("|")
        cols = [j + 1 for j in range(max(len(ca), len(cb)))
                if (ca[j] if j < len(ca) else None) != (cb[j] if j < len(cb) else None)]
        out.append(f"    строка {i + 1}: колонок {len(ca)}/{len(cb)}, различаются колонки {cols[:10]}")
        for j in cols[:3]:
            va = ca[j - 1] if j <= len(ca) else None
            vb = cb[j - 1] if j <= len(cb) else None
            head = lines(a)[0].split("|")
            title = head[j - 1] if j <= len(head) else "?"
            out.append(f"        {j} {title}: {va!r} / {vb!r}")
    return False


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    args = sys.argv[1:]
    while "--ignore" in args:
        i = args.index("--ignore")
        IGNORE.append(args[i + 1])
        del args[i:i + 2]
    dir_a, dir_b = args[0], args[1]
    out = [f"Эталон:   {dir_a}", f"Проверка: {dir_b}", ""]
    ok = 0
    for name in FILES:
        if compare_file(name, os.path.join(dir_a, name), os.path.join(dir_b, name), out):
            ok += 1
    out += ["", f"Итог: совпало {ok} из {len(FILES)} файлов"]
    text = "\n".join(out)
    print(text)
    if len(args) > 2:
        with open(args[2], "w", encoding="utf-8") as f:
            f.write(text + "\n")
    sys.exit(0 if ok == len(FILES) else 1)


if __name__ == "__main__":
    main()
