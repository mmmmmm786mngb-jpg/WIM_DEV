# -*- coding: utf-8 -*-
"""Собирает документ для разработчика "Ускорение выгрузки МО - ФО - блокировки одним вызовом.html" в Документация:
причина замедления, решение, приложение с кодом 1.42 и 1.43 рядом (изменения выделены цветом).
Код берется из исходников ОРИГИНАЛ/src (1.42) и ОПТИМИЗИРОВАНО/src (1.43, проверена на стенде).

    python build_blocks_fix_doc.py
"""
import difflib
import html
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
OLD = os.path.join(PROJECT, "ОРИГИНАЛ", "src", "внВыгрузкаОстатковМО_ФО", "Ext", "ObjectModule.bsl")
NEW = os.path.join(PROJECT, "ОПТИМИЗИРОВАНО", "src", "внВыгрузкаОстатковМО_ФО", "Ext",
                   "ObjectModule.bsl")
TEMPLATE = os.path.join(HERE, "blocks_fix_doc_template.html")
OUT = os.path.join(PROJECT, "Документация", "Ускорение выгрузки МО - ФО - блокировки одним вызовом.html")
CONTEXT = 3

TITLES = [
    "Регистрация обработки: номер версии",
    "Опубликовать: инициализация перед циклом по мандатам",
    "Опубликовать: блок \"выгрузка блокировок\" в цикле по мандатам и конец пакета перед удалением блокировок",
    "Опубликовать: после цикла по мандатам",
    "Новые процедуры (перед ОпубликоватьАктивыРЕПО)",
]


def read(path):
    text = open(path, encoding="utf-8-sig").read().replace("\r\n", "\n")
    return [line.replace("\t", "    ") for line in text.split("\n")]


def cell(number, text, kind):
    num = "" if number is None else str(number)
    return f'<td class="ln">{num}</td><td class="c {kind}">{html.escape(text) or "&nbsp;"}</td>'


def hunk_rows(old, new, group):
    rows = []
    for tag, i1, i2, j1, j2 in group:
        if tag == "equal":
            for k in range(i2 - i1):
                rows.append(cell(i1 + k + 1, old[i1 + k], "eq") + cell(j1 + k + 1, new[j1 + k], "eq"))
            continue
        left = list(range(i1, i2)) if tag in ("replace", "delete") else []
        right = list(range(j1, j2)) if tag in ("replace", "insert") else []
        for k in range(max(len(left), len(right))):
            lc = cell(left[k] + 1, old[left[k]], "del") if k < len(left) else cell(None, "", "pad")
            rc = cell(right[k] + 1, new[right[k]], "add") if k < len(right) else cell(None, "", "pad")
            rows.append(lc + rc)
    return rows


def diff_html(old, new):
    matcher = difflib.SequenceMatcher(None, old, new, autojunk=False)
    groups = list(matcher.get_grouped_opcodes(CONTEXT))
    assert len(groups) == len(TITLES), f"ожидалось {len(TITLES)} фрагментов, найдено {len(groups)}"
    parts = []
    for number, (title, group) in enumerate(zip(TITLES, groups), start=1):
        rows = "\n".join(f"<tr>{row}</tr>" for row in hunk_rows(old, new, group))
        parts.append(f'<h3>А{number}. {html.escape(title)}</h3>\n<div class="diff-wrap"><table class="diff">\n'
                     f'<colgroup><col class="lnc"><col class="cc"><col class="lnc"><col class="cc"></colgroup>\n'
                     f'<tr><th colspan="2">Было: 1.42</th><th colspan="2">Стало: 1.43</th></tr>\n{rows}\n</table></div>')
    return "\n".join(parts)


def main():
    old, new = read(OLD), read(NEW)
    text = open(TEMPLATE, encoding="utf-8").read()
    assert "{{DIFF}}" in text
    text = text.replace("{{DIFF}}", diff_html(old, new))
    for bad in ("\u0451", "\u0401", "\u2014", "\u2013"):
        assert bad not in text, f"запрещенный символ {bad!r}"
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(text)
    print("ok", OUT)


if __name__ == "__main__":
    main()
