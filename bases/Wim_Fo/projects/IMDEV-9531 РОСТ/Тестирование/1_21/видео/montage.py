# -*- coding: utf-8 -*-
"""Ролик ручной проверки 1.21 (один запуск с формы, время цены) из скриншотов клиента тестирования.

Кадры сняты с формы на dev ФО (клиент на отдельном рабочем столе, поэтому запись экрана недоступна). Каждый кадр:
подпись сверху, форма целиком, ниже увеличенная группа "Цены в работе". Сборка: Pillow -> PNG, ffmpeg concat -> mp4.

    python montage.py
"""
import glob
import os
import subprocess

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
SHOTS = r"C:\Users\Acer\.claude\projects\C--1c-Claude-1C-TestProject\a1d99005-935a-4f9b-9ae0-fc8de503f78a\tool-results"
FRAMES = os.path.join(HERE, "кадры")
OUT = os.path.join(HERE, "Цены в работе 1.21.mp4")
FONT = r"C:\Windows\Fonts\arial.ttf"
FONT_BOLD = r"C:\Windows\Fonts\arialbd.ttf"
W, H = 1280, 720
CAPTION_H = 64
FFMPEG = glob.glob(os.path.join(os.environ["LOCALAPPDATA"], "Microsoft", "WinGet", "Packages",
                                "Gyan.FFmpeg.Essentials*", "*", "bin", "ffmpeg.exe"))[0]

# (суффикс файла скриншота, секунды, подпись[, доли высоты для увеличенной вставки, если панель сообщений
# открыта и таблица выше обычного])
PLAN = [
    ("twbwnj", 4, "Версия 1.21. Закладка \"Инвестирование\": список покупки, 20 портфелей"),
    ("8edtqk", 4, "Нажата \"Создать отправить поручения покупка\": все четыре кнопки запуска недоступны",
     (0.22, 0.34)),
    ("2p1xt9", 4.5, "Создано 7: цена ОФЗ из кеша, новая колонка \"Цена получена\" - 16:33:12, ответ стакана"),
    ("mv7zjo", 4, "Все 20 поручений созданы: этап \"Проверка лимитов и отправка\""),
    ("gc679b", 4.5, "Поручения отправлены, итог 20; статусы \"Перевод в ОФЗ\", кнопки снова доступны"),
    ("1yawpe", 4, "Клиент A: продажа 100 поручений, кеш выключен - цена с биржи на каждое поручение"),
    ("p4jlhk", 5, "Клиент B открыл форму во время продажи в A: все четыре кнопки запуска недоступны",
     (0.22, 0.34)),
    ("bs6m54", 3.5, "Продажа в A идет: время цены обновляется с каждым запросом к стакану"),
    ("yl4rg2", 4.5, "Продажа в A завершена, итог 100; через несколько секунд кнопки в B включились сами"),
    ("254hbx", 6, "B, кнопка блокировок при запуске в A: \"Дождитесь завершения текущего запуска\"",
     (0.64, 0.98)),
    ("dt3zzk", 4, "A: реинвестирование 200 в 10 потоках, цена ОФЗ из кеша, ход по потокам"),
    ("r3xbjw", 4.5, "A: реинвестирование завершено, итог 200, одно сообщение", (0.64, 0.98)),
    ("gqzro5", 4, "B: продажи под блокировки LQDT, 60 портфелей, завершили 8 из 10 потоков"),
    ("wouxwy", 4.5, "B: итог 60, статус поручений PreAlert, одно сообщение", (0.64, 0.98)),
    ("tr8sj5", 6, "Стакан недоступен: итог \"Завершено с ошибками, см. лог\", кнопки доступны", (0.64, 0.98)),
]
TITLE = ["Создание торговых поручений РОСТ, версия 1.21", "Один запуск с формы за раз, время цены в таблице",
         "Проверка на стенде разработки: два клиента, стакан 1 с, кеш цены 60 с"]
FINAL = ["Итог проверки 1.21",
         "Поручения и статусы портфелей совпали с версией 1.16: 320 из 320",
         "Во время любого запуска кнопки недоступны у всех открытых форм",
         "Колонка \"Цена получена\" совпадает с ответом стакана (до 1 с)",
         "При ошибках итог \"Завершено с ошибками, см. лог\""]


def shot(suffix):
    return glob.glob(os.path.join(SHOTS, "*-%s.png" % suffix))[0]


def text_slide(lines, path):
    img = Image.new("RGB", (W, H), (32, 120, 88))
    draw = ImageDraw.Draw(img)
    y = 230
    for i, line in enumerate(lines):
        font = ImageFont.truetype(FONT_BOLD if i == 0 else FONT, 44 if i == 0 else 30)
        width = draw.textlength(line, font=font)
        draw.text(((W - width) / 2, y), line, fill="white", font=font)
        y += 80 if i == 0 else 56
    img.save(path)


def frame(suffix, caption, path, band=(0.70, 0.84)):
    src = Image.open(shot(suffix)).convert("RGB")
    sw, sh = src.size
    img = Image.new("RGB", (W, H), (245, 245, 245))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, W, CAPTION_H], fill=(32, 120, 88))
    font = ImageFont.truetype(FONT, 25)
    draw.text((20, (CAPTION_H - 30) / 2), caption, fill="white", font=font)

    # Группа "Цены в работе" - нижняя часть формы (доли высоты скриншота формы 1161x628).
    top, bottom = int(sh * band[0]), int(sh * band[1])
    zoom = src.crop((0, top, sw, bottom))
    zoom_w = W - 20
    zoom = zoom.resize((zoom_w, int(zoom.height * zoom_w / zoom.width)), Image.LANCZOS)

    full_h = H - CAPTION_H - zoom.height - 20
    full = src.resize((int(sw * full_h / sh), full_h), Image.LANCZOS)
    img.paste(full, ((W - full.width) // 2, CAPTION_H + 5))
    y_zoom = CAPTION_H + 10 + full_h
    img.paste(zoom, (10, y_zoom))
    draw.rectangle([9, y_zoom - 1, 10 + zoom.width, y_zoom + zoom.height], outline=(32, 120, 88), width=3)
    img.save(path)


def main():
    # Каталог кадров не удаляется целиком: он может быть текущим каталогом другого процесса.
    os.makedirs(FRAMES, exist_ok=True)
    for name in os.listdir(FRAMES):
        os.remove(os.path.join(FRAMES, name))
    items = []
    path = os.path.join(FRAMES, "00.png")
    text_slide(TITLE, path)
    items.append((path, 4))
    for i, item in enumerate(PLAN, 1):
        suffix, seconds, caption = item[:3]
        path = os.path.join(FRAMES, "%02d.png" % i)
        frame(suffix, caption, path, *item[3:])
        items.append((path, seconds))
    path = os.path.join(FRAMES, "%02d.png" % (len(PLAN) + 1))
    text_slide(FINAL, path)
    items.append((path, 6))

    concat = os.path.join(FRAMES, "list.txt")
    with open(concat, "w", encoding="utf-8") as handle:
        for path, seconds in items:
            handle.write("file '%s'\nduration %s\n" % (path.replace("\\", "/"), seconds))
        handle.write("file '%s'\n" % items[-1][0].replace("\\", "/"))
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", concat,
                    "-vf", "fps=25,format=yuv420p", "-c:v", "libx264", "-preset", "medium", "-crf", "20", OUT],
                   check=True)
    print("ok", OUT, sum(s for _, s in items), "s")


if __name__ == "__main__":
    main()
