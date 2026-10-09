# -*- coding: utf-8 -*-
"""Круговые диаграммы времени заполнения 577-П на DR.

python pie_time.py
1) p577_dr_month_time_pie.png - июнь целиком, заполнение по ссылке + Прочитать() (замер 09.10.2026);
2) p577_dr_21days_compare_pie.png - 01-21.06: текущая кнопка (замер) и заполнение по ссылке (оценка).
Оценка на 21 день: расчет - из замера за 21 день (код расчета тот же), запись и Прочитать() - из замера за месяц
пропорционально числу строк.
"""
import math
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "Документация")
plt.rcParams["font.family"] = "Segoe UI"

SURFACE, INK, MUTED = "#fcfcfb", "#0b0b0b", "#52514e"
COLORS = {
    "Расчет: раздел 9": "#2a78d6",
    "Расчет: раздел 7": "#eb6834",
    "Расчет: раздел 5": "#1baf7a",
    "Расчет: раздел 6": "#eda100",
    "Расчет: прочие разделы": "#e87ba4",
    "Копирование в форму": "#008300",
    "Передача формы на клиент": "#4a3aa7",
    "Запись документа": "#e34948",
    "Загрузка в форму и передача на клиент": "#4a3aa7",
}

ROWS_21, ROWS_MONTH = 6_743_024, 9_738_405
OLD_21 = {
    "Расчет: раздел 9": 1476.77, "Расчет: раздел 7": 885.75, "Расчет: раздел 5": 739.01,
    "Расчет: раздел 6": 273.83, "Расчет: прочие разделы": 130.89,
    "Копирование в форму": 1255.27, "Передача формы на клиент": 1445.30,
}
MONTH_CALC = 6068.41
MONTH = {
    "Расчет: раздел 9": 2632.10, "Расчет: раздел 7": 1750.31, "Расчет: раздел 5": 1082.25,
    "Расчет: раздел 6": 439.19,
    "Расчет: прочие разделы": MONTH_CALC - 2632.10 - 1750.31 - 1082.25 - 439.19 + 16.02,
    "Запись документа": 5269.73,
    "Загрузка в форму и передача на клиент": 12715.40,
}
K = ROWS_21 / ROWS_MONTH
NEW_21 = {k: v for k, v in OLD_21.items() if k.startswith("Расчет")}
NEW_21["Запись документа"] = 5269.73 * K
NEW_21["Загрузка в форму и передача на клиент"] = 12715.40 * K
NEW_21["Расчет: прочие разделы"] += 16.02 * K


def num(x, digits=0):
    s = f"{x:,.{digits}f}".replace(",", " ").replace(".", ",")
    return s


def dur(sec):
    m = round(sec / 60)
    return f"{m // 60} ч {m % 60:02d} мин" if m >= 60 else f"{m} мин"


def donut(ax, data, center_big, center_small, label_pos=None, radius=1.0, fs=12):
    label_pos = label_pos or {}
    names = list(data)
    vals = [data[n] for n in names]
    total = sum(vals)
    wedges, _ = ax.pie(vals, colors=[COLORS[n] for n in names], startangle=90, counterclock=False,
                       radius=radius, wedgeprops=dict(width=0.38 * radius, edgecolor=SURFACE, linewidth=2.5))
    for w, n, v in zip(wedges, names, vals):
        ang = math.radians((w.theta1 + w.theta2) / 2)
        x0, y0 = 0.81 * radius * math.cos(ang), 0.81 * radius * math.sin(ang)
        lx, ly = label_pos.get(n, (1.32 * radius * math.cos(ang), 1.22 * radius * math.sin(ang)))
        ha = "left" if lx >= 0 else "right"
        text = f"{n}\n{num(v / total * 100, 1)}% · {dur(v)}"
        ax.annotate(text, xy=(x0, y0), xytext=(lx, ly), ha=ha, va="center", fontsize=fs, color=INK,
                    arrowprops=dict(arrowstyle="-", color="#52514e", lw=1, shrinkA=2, shrinkB=0))
    ax.text(0, 0.10 * radius, center_big, ha="center", va="center", fontsize=30 * radius ** 0.5,
            fontweight="bold", color=INK)
    ax.text(0, -0.17 * radius, center_small, ha="center", va="center", fontsize=13, color=MUTED)
    ax.set_aspect("equal")
    return total


def month_chart():
    fig, ax = plt.subplots(figsize=(10, 9.4), facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    pos = {
        "Расчет: раздел 9": (0.95, 1.12),
        "Расчет: раздел 7": (1.22, 0.62),
        "Расчет: раздел 5": (1.25, 0.32),
        "Расчет: раздел 6": (1.25, -0.02),
        "Расчет: прочие разделы": (1.22, -0.42),
        "Запись документа": (1.0, -1.18),
        "Загрузка в форму и передача на клиент": (-0.9, -1.22),
    }
    total = donut(ax, MONTH, f"{num(sum(MONTH.values()) / 3600, 1)} ч", f"{num(sum(MONTH.values()))} с", pos)
    ax.set_xlim(-2.0, 2.0)
    ax.set_ylim(-1.5, 1.45)
    ax.axis("off")
    fig.suptitle("Заполнение 577-П на DR за июнь 2026: из чего складывается время\n"
                 "9,74 млн строк, релиз 1.5.30.3, заполнение по ссылке, затем Прочитать()",
                 fontsize=15, color=INK, y=0.97)
    calc = MONTH_CALC
    fig.text(0.5, 0.035,
             f"Расчет {num(calc / total * 100, 0)}% ({dur(calc)}), запись {num(5269.73 / total * 100, 0)}% "
             f"({dur(5269.73)}), Прочитать() {num(12715.40 / total * 100, 0)}% ({dur(12715.40)}).\n"
             "Прочие разделы: 3, 8, 4, 1, 11, 2, 10, сведения УК и служебные вызовы.",
             ha="center", fontsize=11.5, color=MUTED)
    path = os.path.join(OUT, "p577_dr_month_time_pie.png")
    fig.savefig(path, dpi=110, facecolor=SURFACE)
    print(path, round(total))


def compare_chart():
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(19, 10.2), facecolor=SURFACE)
    t_old, t_new = sum(OLD_21.values()), sum(NEW_21.values())
    r_old = math.sqrt(t_old / t_new)
    pos_old = {
        "Расчет: раздел 9": (0.55, 1.0),
        "Расчет: раздел 7": (0.95, 0.15),
        "Расчет: раздел 5": (0.8, -0.55),
        "Расчет: раздел 6": (0.3, -0.95),
        "Расчет: прочие разделы": (-0.45, -1.0),
        "Копирование в форму": (-0.95, -0.35),
        "Передача формы на клиент": (-0.8, 0.85),
    }
    pos_new = {
        "Расчет: раздел 9": (1.05, 1.08),
        "Расчет: раздел 7": (1.25, 0.68),
        "Расчет: раздел 5": (1.3, 0.3),
        "Расчет: раздел 6": (1.3, -0.04),
        "Расчет: прочие разделы": (1.25, -0.42),
        "Запись документа": (1.0, -1.15),
        "Загрузка в форму и передача на клиент": (-0.95, -1.2),
    }
    for ax in (a1, a2):
        ax.set_facecolor(SURFACE)
        ax.set_xlim(-2.0, 2.15)
        ax.set_ylim(-1.45, 1.4)
        ax.axis("off")
    donut(a1, OLD_21, f"{num(t_old / 3600, 1)} ч", f"{num(t_old)} с", pos_old, radius=r_old, fs=11.5)
    donut(a2, NEW_21, f"≈{num(t_new / 3600, 1)} ч", f"≈{num(t_new, 0)} с", pos_new, fs=11.5)
    a1.set_title("Текущая кнопка «Заполнить» (замер)", fontsize=14, color=INK, pad=4)
    a2.set_title("Заполнение по ссылке, затем Прочитать() (оценка)", fontsize=14, color=INK, pad=4)
    fig.suptitle("Заполнение 577-П на DR за 01-21.06.2026: текущая кнопка и заполнение по ссылке\n"
                 "6,74 млн строк, релиз 1.5.30.3; площадь круга пропорциональна общему времени",
                 fontsize=15, color=INK, y=0.975)
    fig.text(0.5, 0.03,
             "Оценка справа: расчет взят из замера за 21 день (код расчета в обоих вариантах один), запись и Прочитать() "
             "пересчитаны из замера за месяц\nпропорционально числу строк (6,74 из 9,74 млн); это оценка сверху, "
             "фактически может быть на 10-20% меньше. В замер текущей кнопки запись документа не входит:\n"
             "ее пользователь выполняет отдельно кнопкой «Записать».",
             ha="center", fontsize=11, color=MUTED)
    path = os.path.join(OUT, "p577_dr_21days_compare_pie.png")
    fig.savefig(path, dpi=110, facecolor=SURFACE)
    print(path, round(t_old), round(t_new), {k: round(v) for k, v in NEW_21.items()})


if __name__ == "__main__":
    month_chart()
    compare_chart()
