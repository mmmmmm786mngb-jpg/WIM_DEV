#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sravnenie sostava rasshireniya 1S s bazovoy konfiguratsiey (nalichie faylov XML).
Generiruet HTML: zaimstvovannye (izmenyaemye) i sobstvennye obekty, perehvatchiki moduley i form.
"""

from __future__ import annotations

import argparse
import html
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

CHILD_TYPE_DIRS: dict[str, str] = {
    "Catalog": "Catalogs",
    "Document": "Documents",
    "Enum": "Enums",
    "CommonModule": "CommonModules",
    "CommonPicture": "CommonPictures",
    "CommonCommand": "CommonCommands",
    "CommonTemplate": "CommonTemplates",
    "ExchangePlan": "ExchangePlans",
    "Report": "Reports",
    "DataProcessor": "DataProcessors",
    "InformationRegister": "InformationRegisters",
    "AccumulationRegister": "AccumulationRegisters",
    "ChartOfCharacteristicTypes": "ChartsOfCharacteristicTypes",
    "ChartOfAccounts": "ChartsOfAccounts",
    "AccountingRegister": "AccountingRegisters",
    "ChartOfCalculationTypes": "ChartsOfCalculationTypes",
    "CalculationRegister": "CalculationRegisters",
    "BusinessProcess": "BusinessProcesses",
    "Task": "Tasks",
    "Subsystem": "Subsystems",
    "Role": "Roles",
    "Constant": "Constants",
    "FunctionalOption": "FunctionalOptions",
    "DefinedType": "DefinedTypes",
    "FunctionalOptionsParameter": "FunctionalOptionsParameters",
    "CommonForm": "CommonForms",
    "DocumentJournal": "DocumentJournals",
    "SessionParameter": "SessionParameters",
    "StyleItem": "StyleItems",
    "EventSubscription": "EventSubscriptions",
    "ScheduledJob": "ScheduledJobs",
    "SettingsStorage": "SettingsStorages",
    "FilterCriterion": "FilterCriteria",
    "CommandGroup": "CommandGroups",
    "DocumentNumerator": "DocumentNumerators",
    "Sequence": "Sequences",
    "IntegrationService": "IntegrationServices",
    "CommonAttribute": "CommonAttributes",
}

INTERCEPTOR_RE = re.compile(
    r"^&(Перед|После|ИзменениеИКонтроль|Вместо)\(\"([^\"]+)\"\)"
)


def local_name(tag: str) -> str:
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def read_source_path(bases_wim_fin: Path) -> Path | None:
    p = bases_wim_fin / "source-path.txt"
    if not p.is_file():
        return None
    text = p.read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            candidate = Path(line)
            return candidate
    return None


def parse_configuration_meta(ext_root: Path) -> dict[str, Any]:
    cfg_xml = ext_root / "Configuration.xml"
    tree = ET.parse(cfg_xml)
    root = tree.getroot()
    props = None
    for cfg in root.iter():
        if local_name(cfg.tag) != "Configuration":
            continue
        for child in cfg:
            if local_name(child.tag) == "Properties":
                props = child
                break
        break
    if props is None:
        return {"name": "?", "prefix": "", "purpose": "?"}

    def text_child(name: str) -> str:
        for c in props:
            if local_name(c.tag) == name:
                return (c.text or "").strip()
        return ""

    return {
        "name": text_child("Name"),
        "prefix": text_child("NamePrefix"),
        "purpose": text_child("ConfigurationExtensionPurpose"),
    }


def iter_configuration_objects(ext_root: Path) -> list[tuple[str, str]]:
    tree = ET.parse(ext_root / "Configuration.xml")
    root = tree.getroot()
    for cfg in root.iter():
        if local_name(cfg.tag) == "Configuration":
            for child in cfg:
                if local_name(child.tag) != "ChildObjects":
                    continue
                out: list[tuple[str, str]] = []
                for obj in child:
                    if obj.text is None:
                        continue
                    ln = local_name(obj.tag)
                    if ln == "Language":
                        continue
                    name = obj.text.strip()
                    if name:
                        out.append((ln, name))
                return out
    return []


def load_object_xml(path: Path) -> ET.Element | None:
    if not path.is_file():
        return None
    try:
        return ET.parse(path).getroot()
    except ET.ParseError:
        return None


def get_properties_el(obj_root: ET.Element) -> ET.Element | None:
    for child in obj_root:
        if local_name(child.tag) == "Properties":
            return child
    return None


def object_belonging_and_uuid(obj_root: ET.Element) -> tuple[bool, str]:
    props = get_properties_el(obj_root)
    if props is None:
        return False, ""
    ob = ""
    ext_uuid = ""
    for c in props:
        ln = local_name(c.tag)
        if ln == "ObjectBelonging":
            ob = (c.text or "").strip()
        elif ln == "ExtendedConfigurationObject":
            ext_uuid = (c.text or "").strip()
    return ob == "Adopted", ext_uuid


def collect_bsl_files(obj_type: str, obj_name: str, ext_root: Path) -> list[Path]:
    if obj_type not in CHILD_TYPE_DIRS:
        return []
    base = ext_root / CHILD_TYPE_DIRS[obj_type] / obj_name
    if not base.is_dir():
        return []
    files: list[Path] = []
    ext_dir = base / "Ext"
    if ext_dir.is_dir():
        for f in ext_dir.glob("*.bsl"):
            files.append(f)
    forms = base / "Forms"
    if forms.is_dir():
        for f in forms.rglob("Module.bsl"):
            files.append(f)
    return sorted(set(files))


def parse_interceptors(bsl_path: Path) -> list[tuple[str, str, int]]:
    try:
        lines = bsl_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    res: list[tuple[str, str, int]] = []
    for i, line in enumerate(lines, start=1):
        m = INTERCEPTOR_RE.match(line.strip())
        if m:
            res.append((m.group(1), m.group(2), i))
    return res


def parse_form_interceptors(form_xml: Path) -> tuple[bool, list[str]]:
    if not form_xml.is_file():
        return False, []
    try:
        tree = ET.parse(form_xml)
    except ET.ParseError:
        return False, []
    root = tree.getroot()
    borrowed = False
    for el in root.iter():
        if local_name(el.tag) == "BaseForm":
            borrowed = True
            break
    lines: list[str] = []
    for el in root.iter():
        if local_name(el.tag) == "Event" and "callType" in el.attrib:
            nm = el.attrib.get("name", "")
            ct = el.attrib.get("callType", "")
            handler = (el.text or "").strip()
            lines.append(f"Событие формы: {nm} [{ct}] -> {handler}")
    for cmd in root.iter():
        if local_name(cmd.tag) != "Command":
            continue
        cmd_name = cmd.attrib.get("name", "")
        for action in cmd:
            if local_name(action.tag) == "Action" and "callType" in action.attrib:
                ct = action.attrib.get("callType", "")
                handler = (action.text or "").strip()
                lines.append(f"Команда: {cmd_name} [{ct}] -> {handler}")
    return borrowed, lines


def analyze_child_objects_summary(obj_root: ET.Element) -> dict[str, Any]:
    own_attrs = own_ts = own_forms = borrowed_items = 0
    form_names: list[str] = []
    for ch in obj_root:
        if local_name(ch.tag) != "ChildObjects":
            continue
        for c in ch:
            if c.text and local_name(c.tag) == "Form":
                form_names.append(c.text.strip())
                continue
            props = None
            for sub in c:
                if local_name(sub.tag) == "Properties":
                    props = sub
                    break
            adopted = False
            if props is not None:
                for p in props:
                    if local_name(p.tag) == "ObjectBelonging" and (p.text or "").strip() == "Adopted":
                        adopted = True
                        break
            if adopted:
                borrowed_items += 1
                continue
            ln = local_name(c.tag)
            if ln == "Attribute":
                own_attrs += 1
            elif ln == "TabularSection":
                own_ts += 1
            elif ln == "Form":
                own_forms += 1
        break
    return {
        "own_attrs": own_attrs,
        "own_ts": own_ts,
        "own_forms": own_forms,
        "borrowed_items": borrowed_items,
        "form_names": form_names,
    }


def form_xml_path(ext_root: Path, obj_type: str, obj_name: str, form_name: str) -> Path:
    d = CHILD_TYPE_DIRS[obj_type]
    return ext_root / d / obj_name / "Forms" / form_name / "Ext" / "Form.xml"


def base_object_xml_exists(base_root: Path | None, obj_type: str, obj_name: str) -> bool | None:
    if base_root is None:
        return None
    if obj_type not in CHILD_TYPE_DIRS:
        return None
    p = base_root / CHILD_TYPE_DIRS[obj_type] / f"{obj_name}.xml"
    return p.is_file()


def build_report(
    ext_root: Path,
    base_root: Path | None,
    bases_wim_fin: Path,
) -> str:
    meta = parse_configuration_meta(ext_root)
    objects = iter_configuration_objects(ext_root)

    borrowed_rows: list[dict[str, Any]] = []
    own_rows: list[dict[str, Any]] = []

    for otype, oname in objects:
        dir_name = CHILD_TYPE_DIRS.get(otype)
        if not dir_name:
            continue
        xml_path = ext_root / dir_name / f"{oname}.xml"
        obj_root = load_object_xml(xml_path)
        if obj_root is None:
            continue
        inner = None
        for c in obj_root:
            if local_name(c.tag) not in ("InternalInfo",):
                inner = c
                break
        if inner is None:
            continue
        is_adopted, ext_uuid = object_belonging_and_uuid(inner)

        bsl_files = collect_bsl_files(otype, oname, ext_root)
        mod_details: list[str] = []
        for bsl in bsl_files:
            rel = bsl.relative_to(ext_root).as_posix()
            ic = parse_interceptors(bsl)
            if ic:
                for kind, method, line in ic:
                    mod_details.append(f"{rel}:{line} &{kind}(\"{method}\")")
            else:
                mod_details.append(f"{rel} (нет перехватчиков вида &Перед/...)")

        summary = analyze_child_objects_summary(inner)
        form_details: list[str] = []
        for fn in summary["form_names"]:
            fpath = form_xml_path(ext_root, otype, oname, fn)
            is_borrowed_form, flines = parse_form_interceptors(fpath)
            tag = "заимствованная" if is_borrowed_form else "собственная"
            if flines:
                form_details.append(f"Форма {fn} ({tag}): " + "; ".join(flines))
            else:
                form_details.append(f"Форма {fn} ({tag}), без callType в Form.xml")

        parts = []
        if summary["own_attrs"]:
            parts.append(f"добавленных реквизитов: {summary['own_attrs']}")
        if summary["own_ts"]:
            parts.append(f"добавленных табличных частей: {summary['own_ts']}")
        if summary["own_forms"]:
            parts.append(f"добавленных форм: {summary['own_forms']}")
        if summary["borrowed_items"]:
            parts.append(f"элементов из базы: {summary['borrowed_items']}")
        child_summary = ", ".join(parts) if parts else "без дополнительных дочерних объектов в выгрузке"

        base_ok = base_object_xml_exists(base_root, otype, oname)
        row = {
            "type": otype,
            "name": oname,
            "ext_uuid": ext_uuid,
            "modules": mod_details,
            "forms": form_details,
            "child_summary": child_summary,
            "base_ok": base_ok,
        }
        if is_adopted:
            borrowed_rows.append(row)
        else:
            own_rows.append(row)

    gen_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    base_cfg = (base_root / "Configuration.xml") if base_root else None
    base_note = ""
    if base_root is None:
        base_note = (
            "<p class=\"warn\">Выгрузка базовой конфигурации в XML не найдена: путь из "
            f"<code>{html.escape(str(bases_wim_fin / 'source-path.txt'))}</code> "
            "отсутствует или в каталоге нет Configuration.xml. "
            "Колонка «В выгрузке базы есть .xml» в таблице не заполняется.</p>"
        )
    elif not base_cfg.is_file():
        base_note = (
            "<p class=\"warn\">В каталоге базы нет Configuration.xml: "
            f"<code>{html.escape(str(base_root))}</code></p>"
        )
    else:
        base_note = (
            "<p class=\"ok\">Базовая конфигурация (проверка наличия файла объекта): "
            f"<code>{html.escape(str(base_root))}</code></p>"
        )

    def esc(s: str) -> str:
        return html.escape(s, quote=True)

    def base_cell(ok: bool | None) -> str:
        if ok is None:
            return "<td class=\"muted\">-</td>"
        if ok:
            return "<td class=\"ok\">да</td>"
        return "<td class=\"err\">нет</td>"

    rows_html = ""
    for r in sorted(borrowed_rows, key=lambda x: (x["type"], x["name"])):
        mods = "<br/>".join(esc(m) for m in r["modules"]) if r["modules"] else "-"
        frms = "<br/>".join(esc(f) for f in r["forms"]) if r["forms"] else "-"
        rows_html += (
            "<tr>"
            f"<td>{esc(r['type'])}</td>"
            f"<td><strong>{esc(r['name'])}</strong></td>"
            f"<td class=\"mono\">{esc(r['ext_uuid'] or '-')}</td>"
            f"{base_cell(r['base_ok'])}"
            f"<td>{esc(r['child_summary'])}</td>"
            f"<td class=\"detail\">{mods}</td>"
            f"<td class=\"detail\">{frms}</td>"
            "</tr>"
        )

    own_html = ""
    for r in sorted(own_rows, key=lambda x: (x["type"], x["name"])):
        own_html += (
            "<tr>"
            f"<td>{esc(r['type'])}</td>"
            f"<td><strong>{esc(r['name'])}</strong></td>"
            f"<td class=\"mono\">{esc(r['ext_uuid'] or '-')}</td>"
            f"{base_cell(r['base_ok'])}"
            f"<td>{esc(r['child_summary'])}</td>"
            "</tr>"
        )

    title = f"Расширение {meta['name']}: изменяемые объекты базы"
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8"/>
<title>{esc(title)}</title>
<style>
body {{ font-family: Segoe UI, Arial, sans-serif; margin: 24px; background: #f8f9fa; color: #212529; }}
h1 {{ color: #212529; font-size: 1.35rem; }}
h2 {{ color: #495057; font-size: 1.1rem; margin-top: 1.5rem; }}
.meta {{ color: #6c757d; font-size: 0.9rem; margin-bottom: 1rem; }}
table {{ border-collapse: collapse; width: 100%; background: #fff; box-shadow: 0 1px 3px rgba(0,0,0,.08); }}
th, td {{ border: 1px solid #dee2e6; padding: 8px 10px; text-align: left; vertical-align: top; }}
th {{ background: #e9ecef; font-weight: 600; }}
.mono {{ font-family: Consolas, monospace; font-size: 0.85rem; }}
.detail {{ font-size: 0.88rem; max-width: 420px; }}
.ok {{ color: #28a745; font-weight: 600; }}
.err {{ color: #dc3545; font-weight: 600; }}
.muted {{ color: #6c757d; }}
.warn {{ background: #fff3cd; border: 1px solid #ffc107; padding: 12px; border-radius: 4px; }}
code {{ background: #e9ecef; padding: 2px 6px; border-radius: 3px; font-size: 0.88rem; }}
</style>
</head>
<body>
<h1>{esc(title)}</h1>
<div class="meta">
<p><strong>Расширение:</strong> {esc(meta['name'])} &nbsp;|&nbsp; <strong>Префикс:</strong> {esc(meta['prefix'] or '-')}
 &nbsp;|&nbsp; <strong>Назначение:</strong> {esc(meta['purpose'])}</p>
<p><strong>Каталог расширения:</strong> <code>{esc(str(ext_root))}</code></p>
<p><strong>Сформировано:</strong> {esc(gen_time)}</p>
</div>
{base_note}
<h2>1. Заимствованные объекты (изменение базовой конфигурации)</h2>
<p>Объекты основной конфигурации, подключённые в расширении: модули, формы, добавленные реквизиты и т.п.</p>
<table>
<thead>
<tr>
<th>Тип метаданных</th>
<th>Имя</th>
<th>UUID объекта базы</th>
<th>В выгрузке базы есть .xml</th>
<th>Дочерние изменения (сводка)</th>
<th>Модули (перехватчики)</th>
<th>Формы (callType)</th>
</tr>
</thead>
<tbody>
{rows_html if rows_html else '<tr><td colspan="7">Нет объектов</td></tr>'}
</tbody>
</table>
<h2>2. Собственные объекты расширения</h2>
<p>Объекты, созданные в расширении (не заимствованные из базы).</p>
<table>
<thead>
<tr>
<th>Тип метаданных</th>
<th>Имя</th>
<th>UUID связи с базой</th>
<th>В выгрузке базы есть .xml</th>
<th>Сводка ChildObjects</th>
</tr>
</thead>
<tbody>
{own_html if own_html else '<tr><td colspan="5">Нет собственных объектов в составе расширения</td></tr>'}
</tbody>
</table>
</body>
</html>
"""


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent
    bases_wim_fin = project_root.parent.parent

    parser = argparse.ArgumentParser(
        description="HTML otchet po obektam rasshireniya 1S i ih svyazi s bazoy"
    )
    parser.add_argument(
        "--extension",
        type=Path,
        default=project_root / "FP",
        help="Katalog rasshireniya (Configuration.xml)",
    )
    parser.add_argument(
        "--base",
        type=Path,
        default=None,
        help="Katalog vygruzki bazovoy konfiguratsii (Configuration.xml). Po umolchaniyu iz source-path.txt",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=project_root / "Документация" / "fp_extension_objects_report.html",
        help="Put k vyhodnomu HTML",
    )
    args = parser.parse_args()
    ext_root = args.extension.resolve()
    if not (ext_root / "Configuration.xml").is_file():
        print("ERROR: net Configuration.xml v kataloge rasshireniya", file=sys.stderr)
        return 1

    base_root: Path | None
    if args.base is not None:
        base_root = args.base.resolve()
        if not (base_root / "Configuration.xml").is_file():
            base_root = None
    else:
        sp = read_source_path(bases_wim_fin)
        base_root = sp if sp and (sp / "Configuration.xml").is_file() else None

    html_text = build_report(ext_root, base_root, bases_wim_fin)
    out = args.output.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html_text, encoding="utf-8")
    print("OK: written", str(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
