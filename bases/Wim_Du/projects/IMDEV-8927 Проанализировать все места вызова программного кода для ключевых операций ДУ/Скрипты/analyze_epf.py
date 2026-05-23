#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Анализ всех внешних обработок (EPF) Wim_Du:
- читает функцию СведенияОВнешнейОбработке из ObjectModule.bsl
- извлекает Наименование, Версию, Информацию, список Команд
- сохраняет результат в JSON для последующего сопоставления с ключевыми операциями
"""

import os
import re
import json

EPF_ROOT = r'C:\1c\Cursor_1c\WORK\Wim_Du\SRC\epf'
OUT_PATH = os.path.join(os.path.dirname(__file__), 'epf_analysis.json')


def find_object_module(epf_dir):
    """Поиск ObjectModule.bsl внутри распакованной EPF."""
    for root, dirs, files in os.walk(epf_dir):
        if 'ObjectModule.bsl' in files:
            return os.path.join(root, 'ObjectModule.bsl')
    return None


def parse_registration(text):
    """Извлекает параметры регистрации и команды из текста модуля."""
    info = {
        'Наименование': None,
        'Версия': None,
        'Информация': None,
        'Вид': None,
        'Команды': []
    }

    pattern = re.compile(
        r'ПараметрыРегистрации\.Вставить\(\s*"([^"]+)"\s*,\s*"([^"]*)"\s*\)',
        re.IGNORECASE
    )
    for m in pattern.finditer(text):
        key = m.group(1)
        val = m.group(2)
        if key in info:
            info[key] = val

    cmd_pattern = re.compile(
        r'ДобавитьКоманду\s*\(\s*[^,]+,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"',
        re.IGNORECASE | re.DOTALL
    )
    for m in cmd_pattern.finditer(text):
        info['Команды'].append({
            'Представление': m.group(1),
            'Идентификатор': m.group(2),
            'Использование': m.group(3)
        })

    return info


def main():
    if not os.path.isdir(EPF_ROOT):
        print('EPF root not found:', EPF_ROOT)
        return

    result = []
    for entry in sorted(os.listdir(EPF_ROOT)):
        full = os.path.join(EPF_ROOT, entry)
        if not os.path.isdir(full):
            continue

        module_path = find_object_module(full)
        if not module_path:
            continue

        try:
            with open(module_path, 'r', encoding='utf-8-sig') as f:
                text = f.read()
        except Exception as exc:
            try:
                with open(module_path, 'r', encoding='cp1251') as f:
                    text = f.read()
            except Exception:
                print('Cannot read:', module_path, exc)
                continue

        info = parse_registration(text)
        info['EPF'] = entry
        info['Module'] = module_path
        result.append(info)

    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print('Total EPF analyzed:', len(result))
    print('Saved to:', OUT_PATH)
    with_name = [r for r in result if r['Наименование']]
    print('With registration:', len(with_name))


if __name__ == '__main__':
    main()
