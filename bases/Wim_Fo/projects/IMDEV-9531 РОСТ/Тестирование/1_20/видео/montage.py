# -*- coding: utf-8 -*-
"""Ролик ручной проверки 1.20 (таблица "Цены в работе") из скриншотов клиента тестирования.

Кадры сняты с формы на dev ФО (клиент на отдельном рабочем столе, поэтому запись экрана недоступна). Каждый кадр:
подпись сверху, форма целиком, ниже увеличенная группа "Цены в работе". Сборка: Pillow -> PNG, ffmpeg concat -> mp4.

    python montage.py
"""
import glob
import os
import shutil
import subprocess

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
SHOTS = r"C:\Users\Acer\.claude\projects\C--1c-Claude-1C-TestProject\a1d99005-935a-4f9b-9ae0-fc8de503f78a\tool-results"
FRAMES = os.path.join(HERE, "кадры")
OUT = os.path.join(HERE, "Цены в работе 1.20.mp4")
FONT = r"C:\Windows\Fonts\arial.ttf"
FONT_BOLD = r"C:\Windows\Fonts\arialbd.ttf"
W, H = 1280, 720
CAPTION_H = 64
FFMPEG = glob.glob(os.path.join(os.environ["LOCALAPPDATA"], "Microsoft", "WinGet", "Packages",
                                "Gyan.FFmpeg.Essentials*", "*", "bin", "ffmpeg.exe"))[0]

# (суффикс файла скриншота, секунды, подпись)
PLAN = [
    ("u1fppv", 4, "Форма обработки 1.20: внизу новая группа \"Цены в работе\", пока пустая"),
    ("4x73dv", 4, "Закладка \"Расторжение\": получен список на продажу - 50 портфелей, 2 бумаги, 100 строк"),
    ("msn5rl", 4, "Нажата \"Создать поручения (продажа)\": форма не блокируется, кнопка недоступна до конца"),
    ("aaid2m", 4, "Первое поручение: цена бумаги запрошена в стакане биржи (\"Откуда\" = биржа)"),
    ("pw70lc", 4, "Дальше цена берется из кеша (60 с): возраст цены растет, считаются поручения по ней"),
    ("jjwrja", 2.5, "Создано 46 поручений: обе бумаги по цене из кеша"),
    ("7eunct", 2.5, "Создано 67 поручений"),
    ("hmr4df", 2.5, "Создано 78 поручений"),
    ("lmjua7", 3, "Создано 99 поручений: по каждой бумаге один запрос в стакан на весь запуск"),
    ("ulngod", 4, "Все 100 поручений созданы: идет проверка лимитов и отправка"),
    ("iw4mf8", 5, "Поручения отправлены, итог 100. Кнопка снова доступна, список обновлен, цены остались на форме"),
]
TITLE = ["Создание торговых поручений РОСТ, версия 1.20", "Таблица \"Цены в работе\" на форме",
         "Проверка на стенде разработки: продажа 100 поручений, стакан 1 с, кеш цены 60 с"]
FINAL = ["Итог проверки 1.20",
         "Поручения и статусы портфелей совпали с версией 1.16: 320 из 320",
         "Продажа 100 поручений: 28 с вместо 134 с, 2 запроса к стакану вместо 100",
         "Регламентная покупка работает как раньше, таблица - для запусков с формы"]


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


def frame(suffix, caption, path):
    src = Image.open(shot(suffix)).convert("RGB")
    sw, sh = src.size
    img = Image.new("RGB", (W, H), (245, 245, 245))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, W, CAPTION_H], fill=(32, 120, 88))
    font = ImageFont.truetype(FONT, 25)
    draw.text((20, (CAPTION_H - 30) / 2), caption, fill="white", font=font)

    # Группа "Цены в работе" - нижняя часть формы (доли высоты скриншота формы 1161x628).
    top, bottom = int(sh * 0.70), int(sh * 0.84)
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
    if os.path.exists(FRAMES):
        shutil.rmtree(FRAMES)
    os.makedirs(FRAMES)
    items = []
    path = os.path.join(FRAMES, "00.png")
    text_slide(TITLE, path)
    items.append((path, 4))
    for i, (suffix, seconds, caption) in enumerate(PLAN, 1):
        path = os.path.join(FRAMES, "%02d.png" % i)
        frame(suffix, caption, path)
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
