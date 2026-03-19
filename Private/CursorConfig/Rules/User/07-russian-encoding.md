# Правило работы с русской кодировкой и кракозябрами

> **Тип:** User Rule (глобальная настройка Cursor)

---

## Проблема
В Windows консоли и некоторых редакторах русские символы отображаются как кракозябры из-за проблем с кодировкой. Это происходит из-за несоответствия между UTF-8 (стандарт для веб и современных систем) и устаревшими кодировками Windows (CP1251, CP866).

## Решения

### 1. Для Python скриптов
- **ВСЕГДА** добавляй `#!/usr/bin/env python3` в первую строку.
- **ВСЕГДА** добавляй `# -*- coding: utf-8 -*-` во вторую строку.
- **ВСЕГДА** используй `encoding='utf-8'` при работе с файлами.
- **КЛЮЧЕВОЕ ПРАВИЛО:** Для консольного вывода (`print()`) **ИСПОЛЬЗУЙ ТОЛЬКО ASCII СИМВОЛЫ**.
- **ВСЕГДА** заменяй специальные символы на их ASCII эквиваленты перед выводом в консоль.

### 2. Для консольных команд
- **Для PowerShell:** `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8`
- **Для CMD:** `chcp 65001`
- **ВСЕГДА** устанавливай: `$env:PYTHONIOENCODING = "utf-8"`

### 3. Для файлов
- **ВСЕГДА** создавай файлы с **АНГЛИЙСКИМИ** именами для консольных команд.
- **ВСЕГДА** используй кодировку UTF-8 для всех текстовых файлов.

### 4. Работа со специальными символами
- **НИКОГДА** не выводи напрямую в консоль символы вроде `+`, `(C)`, `pi` и т.п.

## Таблица замены специальных символов

| Категория | Специальный символ | ASCII замена | Описание |
|---|---|---|---|
| Математика | pi, alpha, beta, gamma | pi, alpha, beta, gamma | Греческие буквы |
| Статус | galochka, krestik | OK, ERROR | Галочка и крестик |
| Валюты | EUR, GBP, JPY, RUB | EUR, GBP, JPY, RUB | Валюты |
| Единицы | gradus, C, F | deg, C, F | Градусы |

## Пример правильного кода

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Пример правильного скрипта для работы с кириллицей.
"""

import sys

def safe_print(text):
    """Безопасный вывод - только ASCII"""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode('ascii', 'replace').decode('ascii'))

# Создание файла с правильной кодировкой
with open('data_russian.txt', 'w', encoding='utf-8') as f:
    f.write('Русский текст')

# Вывод в консоль
safe_print("Russkiy tekst bez problem")
safe_print("OK - operaciya vypolnena")
```

## Настройка консоли (PowerShell)

```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
chcp 65001
$env:PYTHONIOENCODING = "utf-8"
```

## Автоматизация
Добавьте в профиль PowerShell (`notepad $PROFILE`):
```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"
chcp 65001 | Out-Null
```

## Альтернативы для сложного вывода
Если нужно вывести красивые отчеты с кириллицей и спецсимволами:
1. Сгенерируй HTML файл и открой в браузере
2. Сохрани результат в .txt/.md файл в UTF-8
3. Выведи данные в JSON
