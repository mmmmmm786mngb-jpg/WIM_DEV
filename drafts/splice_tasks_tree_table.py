#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rebuild tasks_tree_table.html with new section grouping."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH_IN = ROOT / "ДимаХ" / "Переход_01_04_2026" / "КСобранию_2026_04_14" / "tasks_tree_table.html"


def find_line_index(lines: list[str], needle: str) -> int:
    for i, line in enumerate(lines):
        if needle in line:
            return i
    raise ValueError("not found: " + needle)


def find_nth_line_index(lines: list[str], needle: str, n: int) -> int:
    c = 0
    for i, line in enumerate(lines):
        if needle in line:
            c += 1
            if c == n:
                return i
    raise ValueError("not found nth: " + needle)


def join_lines(lines: list[str], start: int, end: int) -> str:
    return "".join(lines[start:end])


def strip_task_tree(task_html: str) -> tuple[str, str]:
    """Split trailing <div class=\"tree\">... from task; return (task_html_without_tree, tree_fragment)."""
    marker = "<div class=\"tree\">"
    idx = task_html.find(marker)
    if idx == -1:
        return task_html.rstrip() + "\n", ""
    prefix = task_html[:idx]
    rest = task_html[idx:]
    rest = rest.rstrip() + "\n"
    task_close = "                </div>\n"
    pos = rest.rfind(task_close)
    if pos == -1:
        raise ValueError("task close not found: " + repr(rest[-120:]))
    tree_html = rest[:pos].rstrip() + "\n"
    note = (
        '                    <p class="muted" style="font-size:11px;margin:6px 2px 0;">'
        "Исследования по задаче вынесены в раздел 1.5."
        "</p>\n"
    )
    base = prefix.rstrip() + "\n" + note + "                </div>\n"
    return base, tree_html


def main() -> None:
    text = PATH_IN.read_text(encoding="utf-8")
    lines = text.splitlines(True)

    i_css_cross = find_line_index(
        lines, ".base-label.cross { color: var(--fin); border: 2px solid var(--fin); }"
    )
    if ".base-label.mo" not in text:
        lines.insert(
            i_css_cross + 1,
            "        .base-label.mo    { color: #b84d0e; border: 2px solid #c96d33; }\n",
        )
        text = "".join(lines)
        lines = text.splitlines(True)

    text = "".join(lines)
    text = text.replace(
        "        /* ── Раздел (В работе / В планах) ── */",
        "        /* ── Разделы по статусам (1.1-1.5) ── */",
    )
    lines = text.splitlines(True)

    i_zag = find_line_index(lines, "<!-- Загрузка сделок -->")
    i_t = find_line_index(lines, "<!-- Исполнение Т -->")
    i_t1 = find_line_index(lines, "<!-- Исполнение Т-1 -->")
    i_obmen = find_line_index(lines, "<!-- Обмен ДУ-Финансы -->")
    i_vech = find_line_index(lines, "<!-- Вечерние регламенты -->")
    i_fin_base = find_line_index(lines, "<!-- === БАЗА ФИН === -->")
    i_fin_exec = find_line_index(lines, "<!-- Исполнение ФИН -->")
    i_fin_rdu = find_line_index(lines, "<!-- Регламенты РДУ -->")
    i_kon_fin = find_line_index(lines, "<!-- конец БАЗА ФИН -->")
    i_pif_base = find_line_index(lines, "<!-- === БАЗА ПИФ === -->")
    i_kon_pif = find_line_index(lines, "<!-- конец БАЗА ПИФ -->")

    i_plans_du = find_line_index(lines, "            <!-- ДУ -->")
    i_plans_fin = find_line_index(lines, "            <!-- ФИН -->")
    i_plans_cross = find_line_index(lines, "<!-- Сквозная ДУ + ФИН -->")
    i_second_blockbody = find_nth_line_index(lines, "        </div><!-- block-body -->", 2)

    i_wrap = find_line_index(lines, "</div><!-- wrap -->")
    i_old_start = find_line_index(lines, "<!-- ==================== 1.1 В РАБОТЕ ==================== -->")

    task_zag = join_lines(lines, i_zag, i_t)
    task_t = join_lines(lines, i_t, i_t1)
    task_t1 = join_lines(lines, i_t1, i_obmen)
    task_obmen_full = join_lines(lines, i_obmen, i_vech)
    task_vech_full = join_lines(lines, i_vech, i_fin_base)
    task_fin_exec_full = join_lines(lines, i_fin_exec, i_fin_rdu)
    task_fin_rdu = join_lines(lines, i_fin_rdu, i_kon_fin - 1)
    task_pif = join_lines(lines, i_pif_base, i_kon_pif + 1)

    task_pay = join_lines(lines, i_plans_du, i_plans_fin)
    # Только внутренний <div class="task">...</div> НДФЛ, без обертки <div class="base"> (она добавляется в 1.4)
    i_ndfl_start = i_plans_fin + 3
    i_ndfl_end_excl = i_plans_cross - 2
    task_ndfl = join_lines(lines, i_ndfl_start, i_ndfl_end_excl)
    task_cross = join_lines(lines, i_plans_cross, i_second_blockbody)

    obmen_main, obmen_tree = strip_task_tree(task_obmen_full)
    vech_main, vech_tree = strip_task_tree(task_vech_full)
    fin_exec_main, fin_exec_tree = strip_task_tree(task_fin_exec_full)

    head = "".join(lines[:i_old_start])
    tail = "".join(lines[i_wrap:])

    task_mo = (
        '                <div class="task">\n'
        '                    <div class="task-header"><span class="task-badge">Задача</span> '
        "Оптимизация выполнения регламентных операций в МО под РДУ</div>\n"
        "                    <table>\n"
        "                        <tr>\n"
        "                            <th>БЫЛО</th>\n"
        "                            <th>СТАЛО</th>\n"
        "                            <th>Потоки (тест)</th>\n"
        "                            <th>Целевое время</th>\n"
        "                            <th>Статус цели</th>\n"
        "                        </tr>\n"
        "                        <tr>\n"
        '                            <td class="muted">нет данных</td>\n'
        '                            <td class="muted">нет данных</td>\n'
        '                            <td class="muted">—</td>\n'
        '                            <td class="muted">уточняется</td>\n'
        '                            <td><span class="status close">Ближайшие планы</span></td>\n'
        "                        </tr>\n"
        "                    </table>\n"
        "                </div>\n"
    )

    ndfl_html = task_ndfl.replace(
        '<td><span class="status pending">В планах</span></td>',
        '<td><span class="status close">Ближайшие планы</span></td>',
    )

    research_bundle = (
        '            <div class="base">\n'
        '                <div class="base-label cross">Исследования (продолжение по завершенным / к релизу задачам)</div>\n'
        f"{obmen_tree}\n"
        f"{vech_tree}\n"
        f"{fin_exec_tree}\n"
        "            </div>\n"
    )

    middle = (
        '    <!-- ==================== 1.1 ВЫПОЛНЕНО ==================== -->\n'
        '    <div class="block">\n'
        '        <h2 class="block-title">1.1 ВЫПОЛНЕНО</h2>\n'
        '        <div class="block-body">\n'
        '            <div class="base">\n'
        '                <div class="base-label du">ДУ (ДУ 1.5)</div>\n'
        f"{task_zag}"
        f"{task_t1}"
        f"{obmen_main}"
        "            </div>\n"
        '            <div class="base">\n'
        '                <div class="base-label fin">ФИН (ДУ 2.0)</div>\n'
        f"{fin_exec_main}"
        "            </div>\n"
        "        </div><!-- block-body -->\n"
        "    </div><!-- 1.1 ВЫПОЛНЕНО -->\n\n"
        '    <!-- ==================== 1.2 К РЕЛИЗУ ==================== -->\n'
        '    <div class="block">\n'
        '        <h2 class="block-title">1.2 - К РЕЛИЗУ</h2>\n'
        '        <div class="block-body">\n'
        '            <div class="base">\n'
        '                <div class="base-label du">ДУ (ДУ 1.5)</div>\n'
        f"{task_t}"
        f"{vech_main}"
        "            </div>\n"
        "        </div><!-- block-body -->\n"
        "    </div><!-- 1.2 К РЕЛИЗУ -->\n\n"
        '    <!-- ==================== 1.3 В РАБОТЕ ==================== -->\n'
        '    <div class="block">\n'
        '        <h2 class="block-title">1.3 - В РАБОТЕ</h2>\n'
        '        <div class="block-body">\n'
        '            <div class="base">\n'
        '                <div class="base-label fin">ФИН (ДУ 2.0)</div>\n'
        f"{task_fin_rdu}"
        "            </div>\n"
        "        </div><!-- block-body -->\n"
        "    </div><!-- 1.3 В РАБОТЕ -->\n\n"
        '    <!-- ==================== 1.4 БЛИЖАЙШИЕ ПЛАНЫ ==================== -->\n'
        '    <div class="block">\n'
        '        <h2 class="block-title">1.4 - БЛИЖАЙШИЕ ПЛАНЫ</h2>\n'
        '        <div class="block-body">\n'
        '            <div class="base">\n'
        '                <div class="base-label fin">ФИН (ДУ 2.0)</div>\n'
        f"{ndfl_html}"
        "            </div>\n"
        '            <div class="base">\n'
        '                <div class="base-label mo">МО</div>\n'
        f"{task_mo}"
        "            </div>\n"
        "        </div><!-- block-body -->\n"
        "    </div><!-- 1.4 БЛИЖАЙШИЕ ПЛАНЫ -->\n\n"
        '    <!-- ==================== 1.5 В ПЛАНАХ ==================== -->\n'
        '    <div class="block">\n'
        '        <h2 class="block-title">1.5 - В ПЛАНАХ</h2>\n'
        '        <div class="block-body">\n'
        f"{task_pay}"
        f"{task_pif}"
        f"{task_cross}"
        f"{research_bundle}"
        "        </div><!-- block-body -->\n"
        "    </div><!-- 1.5 В ПЛАНАХ -->\n\n"
    )

    out = head + middle + tail
    PATH_IN.write_text(out, encoding="utf-8")
    print("OK wrote", PATH_IN)


if __name__ == "__main__":
    main()
