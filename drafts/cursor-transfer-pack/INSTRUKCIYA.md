# Перенос Cursor на другой компьютер

Пошаговая инструкция. Сначала настраиваем Cursor, потом подключаем Git.

---

## Что в архиве CursorTransferPack.zip

| Папка / файл | Назначение |
|--------------|------------|
| `dot-cursor/` | Правила проекта (rules) и skills для 1С |
| `user-settings/settings.json` | Настройки редактора, BSL, терминала, Git |
| `user-rules/` | Пользовательские правила для AI (вставить вручную) |
| `skills-1c-bsl-coding/` | Навык разработки BSL |
| `extensions.txt` | Список расширений Cursor |
| `install.ps1` | Скрипт автоматической установки |
| `INSTRUKCIYA.md` | Эта инструкция |

---

## ШАГ 0. На новом компьютере установить

1. **Cursor** — https://cursor.com
2. **Git** — https://git-scm.com/download/win
3. **Java 17** (для BSL Language Server) — Eclipse Adoptium JDK 17
4. **BSL Language Server** — скачать `bsl-language-server.jar`, положить в `C:\bsl\`

   Если пути другие — после установки поправьте в Cursor:
   `File -> Preferences -> Settings -> language-1c-bsl`

---

## ШАГ 1. Перенести архив на новый ПК

Скопируйте файл на флешку / в облако / по сети:

```
CursorTransferPack.zip
```

Распакуйте, например в:

```
C:\1c\Cursor_1c\cursor-transfer-pack\
```

---

## ШАГ 2. Установить настройки Cursor (ДО Git)

Откройте PowerShell **от имени обычного пользователя**:

```powershell
cd C:\1c\Cursor_1c\cursor-transfer-pack
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

Скрипт:
- скопирует `.cursor` (rules + skills) в `C:\1c\Cursor_1c\WIM_DEV\.cursor`
- установит `settings.json`
- попробует установить расширения из `extensions.txt`

Если папки проекта ещё нет — скрипт создаст её.

### Перезапустите Cursor после установки.

---

## ШАГ 3. User Rules (правила для AI) — вручную

User Rules хранятся внутри Cursor, их нельзя скопировать одним файлом.

1. Откройте Cursor
2. **Settings** (Ctrl+,) -> **Rules** -> **User Rules**
3. Откройте файл `user-rules\USER-RULES-COMBINED.md` из архива
4. Скопируйте весь текст и вставьте в User Rules
5. Сохраните

---

## ШАГ 4. Подключить Git (клонировать репозиторий)

### Вариант A — через Cursor

1. **Ctrl+Shift+P** -> `Git: Clone`
2. URL:
   ```
   https://github.com/mmmmmm786mngb-jpg/WIM_DEV.git
   ```
3. Папка: `C:\1c\Cursor_1c\`
4. Откройте папку `WIM_DEV`

### Вариант B — через терминал

```powershell
mkdir C:\1c\Cursor_1c
cd C:\1c\Cursor_1c
git clone https://github.com/mmmmmm786mngb-jpg/WIM_DEV.git
```

При запросе авторизации — войдите в GitHub (браузер или Personal Access Token).

### Открыть в Cursor

**File -> Open Folder** -> `C:\1c\Cursor_1c\WIM_DEV`

---

## ШАГ 5. Проверка Git

В терминале Cursor:

```powershell
cd C:\1c\Cursor_1c\WIM_DEV
git remote -v
git pull
```

Должно показать:
```
origin  https://github.com/mmmmmm786mngb-jpg/WIM_DEV.git
```

---

## ШАГ 6. Базы 1С (не в Git)

Создайте каталог и скопируйте базы с текущего ПК:

```powershell
mkdir C:\1c\Cursor_1c\WORK
```

Или подключитесь к серверным базам (список в `drafts\AChmykhalov_1C.v8i`).

Скопировать список баз 1С:

```powershell
copy "C:\1c\Cursor_1c\WIM_DEV\drafts\AChmykhalov_1C.v8i" "$env:APPDATA\1C\1CEStart\ibases.v8i"
```

---

## Ежедневная синхронизация между двумя ПК

```powershell
# Перед работой
git pull

# После работы
git add .
git commit -m "opisanie izmenenij"
git push
```

---

## Если что-то не работает

| Проблема | Решение |
|----------|---------|
| Git clone — 403 / auth failed | Войти в GitHub в Cursor или создать Personal Access Token |
| BSL не подсвечивает код | Проверить пути Java и bsl-language-server.jar в Settings |
| Skills не видны | Убедиться что открыта папка `WIM_DEV`, а не подпапка |
| Кракозябры в терминале | Перезапустить Cursor (настройки UTF-8 уже в settings.json) |
| Расширения не ставятся | Установить вручную: Extensions -> поиск по имени из extensions.txt |

---

## Ссылка на репозиторий

```
https://github.com/mmmmmm786mngb-jpg/WIM_DEV
```

---

## Порядок действий (кратко)

```
1. Установить Cursor + Git + Java + BSL jar
2. Распаковать CursorTransferPack.zip
3. Запустить install.ps1
4. Вставить User Rules в Cursor Settings
5. Перезапустить Cursor
6. git clone WIM_DEV
7. Открыть WIM_DEV в Cursor
8. Скопировать базы 1С в WORK
```
