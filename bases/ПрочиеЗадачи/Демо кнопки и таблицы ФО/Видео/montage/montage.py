# -*- coding: utf-8 -*-
"""Монтаж ролика ~2 мин из записи экрана session_raw.mkv по отметкам markers.txt.

Каждый отрезок: вырезка из записи, ускорение, подпись внизу кадра, своя фраза озвучки (<id>.mp3),
дополненная тишиной до длины отрезка. Титул и финал - слайды. Отрезки склеиваются concat.
"""
import os, subprocess, sys

sys.stdout.reconfigure(encoding="utf-8")
FF = r"C:\Users\Acer\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Essentials_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0-essentials_build\bin\ffmpeg.exe"
HERE = os.path.dirname(os.path.abspath(__file__))
VIDEO_DIR = os.path.dirname(HERE)
RAW = os.path.join(VIDEO_DIR, "session_raw.mkv")
FIXED = os.path.join(HERE, "session_fixed.mkv")
OUT = os.path.join(VIDEO_DIR, "Доработка 1С с AI-агентом - 2 минуты.mp4")
W, H, FPS = 1630, 1030, 25
FONT = "C\\:/Windows/Fonts/arial.ttf"
FONT_B = "C\\:/Windows/Fonts/arialbd.ttf"

# (id, начало, конец, ускорение, подпись) - секунды записи; None вместо начала - слайд
SEGMENTS = [
    ("s1", None, 6.0, None, ("Доработка 1С с AI-агентом",
                             "От запроса до проверки в веб-клиенте. База ФО, тестовая копия")),
    ("s2", 30, 48, 1.5, "Задача: кнопка «Итог в сообщение» для таблицы товаров"),
    ("s3", 48, 116, 5.5, "Правка кода: команда, кнопка и обработчик в модуле формы (ускорено)"),
    ("s4", 116, 169, 5, "Сборка обработки и обновление в базе ФО (ускорено x5)"),
    ("s5", 169, 228, 2.5, "Встроенный браузер: веб-клиент ФО, запуск обработки (ускорено)"),
    ("s6", 228, 252, 1.5, "Заполняем пример и нажимаем новую кнопку"),
    ("s7", 252, 282, 1.5, "Сообщение: 7 строк, сумма 119 670,00 - совпадает с расчетом"),
    ("s8", 282, 340, 5, "Выход из 1С через меню и отчет о результате (ускорено x5)"),
    ("s9", None, 7.0, None, ("Доработка готова и проверена",
                             "Код, сборка, обновление в базе и тест в браузере выполнил агент")),
]


def run(args):
    r = subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-y"] + args)
    if r.returncode:
        raise SystemExit("ffmpeg failed: " + " ".join(args[-1:]))


def text_file(name, text):
    path = os.path.join(HERE, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path.replace("\\", "/").replace(":", "\\:")


def audio_filter(dur):
    return f"[1:a]adelay=400|400,apad,atrim=0:{dur:.3f},aresample=48000[a]"


def build_slide(sid, dur, title, subtitle):
    t = text_file(sid + "_t.txt", title)
    s = text_file(sid + "_s.txt", subtitle)
    vf = (f"drawtext=fontfile='{FONT_B}':textfile='{t}':fontcolor=white:fontsize=64:"
          f"x=(w-text_w)/2:y=h/2-90,"
          f"drawtext=fontfile='{FONT}':textfile='{s}':fontcolor=0xC9D6F0:fontsize=34:"
          f"x=(w-text_w)/2:y=h/2+10")
    out = os.path.join(HERE, sid + ".mp4")
    run(["-f", "lavfi", "-i", f"color=c=0x1F2A44:s={W}x{H}:r={FPS}:d={dur}",
         "-i", os.path.join(HERE, sid + ".mp3"),
         "-filter_complex", f"[0:v]{vf}[v];{audio_filter(dur)}",
         "-map", "[v]", "-map", "[a]", "-t", f"{dur:.3f}",
         "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-ac", "2", out])
    return out, dur


def build_clip(sid, start, end, speed, caption):
    dur = (end - start) / speed
    c = text_file(sid + "_c.txt", caption)
    vf = (f"[0:v]trim=start={start}:end={end},setpts=(PTS-STARTPTS)/{speed},fps={FPS},"
          f"drawtext=fontfile='{FONT}':textfile='{c}':fontcolor=white:fontsize=34:"
          f"box=1:boxcolor=0x1F2A44@0.85:boxborderw=18:x=(w-text_w)/2:y=h-text_h-40[v]")
    out = os.path.join(HERE, sid + ".mp4")
    run(["-i", FIXED, "-i", os.path.join(HERE, sid + ".mp3"),
         "-filter_complex", f"{vf};{audio_filter(dur)}",
         "-map", "[v]", "-map", "[a]", "-t", f"{dur:.3f}",
         "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-ac", "2", out])
    return out, dur


def main():
    if not os.path.exists(FIXED):
        run(["-i", RAW, "-c", "copy", FIXED])
    parts, total = [], 0.0
    for sid, start, end, speed, caption in SEGMENTS:
        if start is None:
            path, dur = build_slide(sid, end, *caption)
        else:
            path, dur = build_clip(sid, start, end, speed, caption)
        parts.append(path)
        total += dur
        print(f"{sid}: {dur:.1f} s")
    lst = os.path.join(HERE, "concat.txt")
    with open(lst, "w", encoding="utf-8") as f:
        for p in parts:
            f.write("file '" + p.replace("\\", "/") + "'\n")
    run(["-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", "-movflags", "+faststart", OUT])
    print(f"total {total:.1f} s -> {OUT}")


if __name__ == "__main__":
    main()
