#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compare OPT-related logic before and after refactor (git HEAD vs working tree)."""

import re
import subprocess
import sys
from pathlib import Path

REPO = Path(r"c:\1c\Cursor_1c\WIM_DEV")
BSL_REL = (
    "bases/Wim_Du/projects/IMDEV-9096 Выписки/erf_Оптимизация_Тест1/"
    "внЗагрузкаВыписокДУ_epf/внЗагрузкаВыписокДУ/Ext/ObjectModule.bsl"
)
BSL_PATH = REPO / BSL_REL

OPT_FUNCTIONS = [
    "СобратьУникальныеНомераСчетовДляКэшаДоговоровДУ",
    "ЗаполнитьКэшДоговоровДУПоСчетам",
    "ДоговорДУПоСчетуОднимЗапросом",
    "ДоговорДУПоСчету",
    "ПостроитьКартуПрефиксовЕРС",
    "НайтиДоговорПоКартеПрефиксов",
    "ЕРС_ДоговорДУ_ПоСчетуИНазначению",
    "ПолучитьДанныеДепоПоСчету",
    "НайтиДоговорВДанныхДепо",
    "ЕРС_ДоговорДУ_ПоСчетуИСчетуДепо",
    "ПолучитьПлатежныеПорученияОкна",
    "ЕРС_ДоговорДУ_ПоПлатежномуПоручению",
    "ПрочитатьОбъекты",
]

REMOVED_HELPERS = [
    "НормализоватьНомерСчетаДляКэшаДоговоровДУ",
    "ДобавитьНомерСчетаВМножествоДляКэша",
    "МассивКлючейИзСоответствия",
    "ТекстЗапросаДоговоровДУПоНомерамСчетов",
    "ДоговорДУПоНайденнымСтрокамЗапроса",
]


def read_head_text() -> str:
    result = subprocess.run(
        ["git", "show", f"HEAD:{BSL_REL.replace(chr(92), '/')}"],
        cwd=REPO,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr or "git show failed")
    return result.read() if hasattr(result, "read") else result.stdout


def read_working_text() -> str:
    return BSL_PATH.read_text(encoding="utf-8")


def strip_comments_and_ws(text: str) -> str:
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("//"):
            continue
        lines.append(stripped)
    return "\n".join(lines)


def extract_function(text: str, name: str) -> str | None:
    if name == "ПрочитатьОбъекты":
        pattern = rf"(?ms)^Процедура\s+{re.escape(name)}\s*\(.*?\n.*?^КонецПроцедуры"
    else:
        pattern = rf"(?ms)^Функция\s+{re.escape(name)}\s*\(.*?\n.*?^КонецФункции"
    match = re.search(pattern, text)
    return match.group(0) if match else None


def extract_opt_init_block(proc_body: str) -> str:
    start = proc_body.find("ДанныеСчетовДляКэша")
    end = proc_body.find("сч = 0")
    if start < 0 or end < 0:
        return ""
    return proc_body[start:end]


def main() -> int:
    old_text = read_head_text()
    new_text = read_working_text()

    issues = []
    ok = []

    for helper in REMOVED_HELPERS:
        if extract_function(new_text, helper):
            issues.append(f"NEW: helper still present: {helper}")
        else:
            ok.append(f"removed helper OK: {helper}")

    for name in OPT_FUNCTIONS:
        old_fn = extract_function(old_text, name)
        new_fn = extract_function(new_text, name)
        if old_fn is None:
            issues.append(f"OLD missing: {name}")
            continue
        if new_fn is None:
            issues.append(f"NEW missing: {name}")
            continue

        old_norm = strip_comments_and_ws(old_fn)
        new_norm = strip_comments_and_ws(new_fn)

        if name == "ПрочитатьОбъекты":
            old_norm = strip_comments_and_ws(extract_opt_init_block(old_fn))
            new_norm = strip_comments_and_ws(extract_opt_init_block(new_fn))

        if old_norm == new_norm:
            ok.append(f"logic OK: {name}")
        else:
            issues.append(f"logic DIFF: {name} (normalized body changed)")

    # sanity: no duplicate function definitions
    for name in OPT_FUNCTIONS:
        if name == "ПрочитатьОбъекты":
            count = len(re.findall(rf"^Процедура\s+{re.escape(name)}\s*\(", new_text, re.M))
        else:
            count = len(re.findall(rf"^Функция\s+{re.escape(name)}\s*\(", new_text, re.M))
        if count != 1:
            issues.append(f"duplicate/missing def: {name} count={count}")

    print("=== REFACTOR LOGIC CHECK (HEAD vs working tree) ===")
    print(f"OK items: {len(ok)}")
    for item in ok:
        print(f"  OK  {item}")
    print(f"Issues: {len(issues)}")
    for item in issues:
        print(f"  ERR {item}")

    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
