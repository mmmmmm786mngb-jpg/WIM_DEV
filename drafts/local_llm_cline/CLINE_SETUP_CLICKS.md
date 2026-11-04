# Осталось вручную в VS Code (4 клика)

Управление мышью через Cursor Computer Use сейчас недоступно
(ошибка подписи sidecar). Ниже — что сделать вручную после
загрузки модели в LM Studio.

## 1. LM Studio

1. Откройте LM Studio (уже установлен).
2. Вкладка **My Models** / локальные модели — должна быть
   `qwen2.5-coder-7b-instruct-q4_k_m`.
3. Вкладка **Developer** (или Local Server) — **Start Server**.
4. Адрес: `http://127.0.0.1:1234` (по умолчанию).
5. Загрузите модель в память (Load), контекст поставьте **16384**
   или **32768** (больше — медленнее на CPU).

Проверка из PowerShell:

```powershell
curl http://127.0.0.1:1234/v1/models
```

## 2. Cline в VS Code

1. Откройте папку `WIM_DEV` в VS Code.
2. Иконка Cline в боковой панели.
3. Шестеренка Settings.
4. API Provider: **LM Studio** (или OpenAI Compatible).
5. Base URL: `http://localhost:1234` (для OpenAI Compatible —
   `http://localhost:1234/v1`).
6. Model: выберите загруженную модель из списка.
7. Context Window: **32768**.
8. Features: включите **Enable Skills**, **Use Compact Prompt**.

Примечание: Compact Prompt ускоряет локальную модель, но может
ограничить MCP. Для проверки MCP выключите Compact Prompt.

## 3. Откат

```powershell
powershell -ExecutionPolicy Bypass -File "c:\1c\Cursor_1c\WIM_DEV\drafts\local_llm_cline\uninstall_local_llm_pilot.ps1"
```

Удалит LM Studio, модели, Cline и папки `.cline` / `.clinerules`
пилота. Cursor не трогает.
