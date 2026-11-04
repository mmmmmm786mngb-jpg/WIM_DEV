# -*- coding: utf-8 -*-
"""Графики отчета о тесте 1.16 и 1.17 на Т-1 (PNG для docx).

Цифры - из логов Т-1/Тест_распространения_9746_20261104_0755_ОБЫЧНЫЙ и _0754_РОЗНИЦА.

    python build_t1_report_charts.py <каталог для PNG>
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

V116 = "#2a78d6"
V117 = "#eb6834"
INK = "#0b0b0b"
INK2 = "#52514e"
GRID = "#e4e3df"
STEPS = ["#2a78d6", "#7fb0ea", "#eb6834", "#b8b7b0"]

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
    "figure.dpi": 200, "savefig.bbox": "tight", "savefig.facecolor": "white",
})

# Время вызова распространения по запускам, секунды: (запуск, 1.16, 1.17)
ORDINARY = [(1, 26.54, 3.40), (2, 22.66, 3.09), (3, 21.55, 2.84)]
RETAIL = [(1, 7.70, 5.27), (2, 7.89, 5.42), (3, 7.49, 5.40)]

# Шаги запуска с медианным временем: поиск новых клиентов, создание установок, итоговая рассылка, прочее
# (в рознице 1.16 прочее - в основном ожидание после постановки фонового задания записи версий)
STEP_NAMES = ["Поиск новых клиентов", "Создание установок", "Итоговые письма", "Ожидание задания и прочее"]
STEP_DATA = [
    ("Обычный ФО\n1.16", [0.11, 22.20, 0.28, 0.07]),
    ("Обычный ФО\n1.17", [0.11, 2.57, 0.34, 0.07]),
    ("Розница\n1.16", [0.22, 5.86, 0.65, 0.97]),
    ("Розница\n1.17", [0.06, 4.53, 0.70, 0.11]),
]


def num(value):
    return ("%.1f" % value).replace(".", ",")


def chart_runs(out):
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.6))
    for ax, title, data in ((axes[0], "Обычный ФО: 1 клиент на запуск", ORDINARY),
                            (axes[1], "Розница: 2 клиента на запуск", RETAIL)):
        x = list(range(len(data)))
        width = 0.36
        for shift, idx, color in ((-width / 2, 1, V116), (width / 2, 2, V117)):
            values = [row[idx] for row in data]
            rects = ax.bar([i + shift for i in x], values, width=width, color=color, edgecolor="white", linewidth=1.5)
            top = max(max(r[1] for r in data), max(r[2] for r in data))
            for rect, value in zip(rects, values):
                ax.text(rect.get_x() + rect.get_width() / 2, rect.get_height() + top * 0.015, num(value),
                        ha="center", va="bottom", color=INK, fontsize=8.5)
        ax.set_xticks(x)
        ax.set_xticklabels(["запуск %d" % row[0] for row in data], fontsize=9)
        ax.set_title(title, fontsize=10, color=INK, loc="left")
        ax.set_ylabel("секунд")
    fig.legend(handles=[Patch(color=V116, label="1.16 (рабочая)"), Patch(color=V117, label="1.17")],
               frameon=False, loc="lower center", bbox_to_anchor=(0.5, -0.06), ncol=2, fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(out, "01_runs.png"))
    plt.close(fig)


def chart_steps(out):
    fig, ax = plt.subplots(figsize=(9.2, 3.2))
    labels = [row[0] for row in STEP_DATA]
    y = list(range(len(STEP_DATA)))[::-1]
    for yi, (label, parts) in zip(y, STEP_DATA):
        left = 0
        for part, color in zip(parts, STEPS):
            ax.barh(yi, part, left=left, color=color, edgecolor="white", linewidth=1, height=0.6)
            left += part
        ax.text(left + 0.25, yi, num(left) + " с", va="center", color=INK, fontsize=9)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel("секунд, запуск с медианным временем")
    ax.grid(axis="y", visible=False)
    ax.legend(handles=[Patch(color=c, label=n) for c, n in zip(STEPS, STEP_NAMES)], frameon=False,
              loc="lower right", fontsize=8.5)
    fig.tight_layout()
    fig.savefig(os.path.join(out, "02_steps.png"))
    plt.close(fig)


if __name__ == "__main__":
    target = sys.argv[1]
    os.makedirs(target, exist_ok=True)
    chart_runs(target)
    chart_steps(target)
    print("ok", target)
