# -*- coding: utf-8 -*-
"""Графики отчета о тестировании IMDEV-9744 на Т-1 (PNG для docx).

Цифры - из лога обработки замеров Т-1/МО/ЗамерБлокировок/Замер_блокировок_МО_ФО_20261030_1407.txt
(сравнение версий, серии отправки) и замеров ПРОД до 21.10 (лог диагностики МО от 28.10).

    python build_t1_report_charts.py <каталог для PNG>
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

V142 = "#2a78d6"   # категориальный слот 1
V143 = "#eb6834"   # категориальный слот 2
BASE = "#b8b7b0"   # нейтральный для неизменной части
INK = "#0b0b0b"
INK2 = "#52514e"
GRID = "#e4e3df"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
    "figure.dpi": 200, "savefig.bbox": "tight", "savefig.facecolor": "white",
})

# Шаги сравнения версий: номер шага, версия, режим, Заполнить, Опубликовать (секунды, 200 мандатов)
RUNS = [
    (1, "1.42", "без", 5.1, 182.4), (2, "1.43", "без", 6.5, 184.1), (3, "1.43", "без", 11.7, 255.7),
    (4, "1.42", "без", 5.0, 170.2), (5, "1.43", "с", 6.7, 297.3), (6, "1.42", "с", 4.7, 324.2),
    (7, "1.42", "с", 4.6, 285.2), (8, "1.43", "с", 3.8, 231.2),
]


def color(version):
    return V142 if version == "1.42" else V143


def bars(ax, x, heights, colors, labels, fmt="{:.0f}"):
    rects = ax.bar(x, heights, width=0.62, color=colors, edgecolor="white", linewidth=2)
    for rect, value, label in zip(rects, heights, labels):
        ax.text(rect.get_x() + rect.get_width() / 2, rect.get_height() + max(heights) * 0.015, fmt.format(value).replace(".", ","),
                ha="center", va="bottom", color=INK, fontsize=9)
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontsize=8.5)
    return rects


def legend(target):
    """Легенда под графиком в одну строку: не перекрывает столбцы и подписи значений."""
    from matplotlib.patches import Patch
    target.legend(handles=[Patch(color=V142, label="1.42 (по мандату)"), Patch(color=V143, label="1.43 (пакетом)")],
                  frameon=False, loc="lower center", bbox_to_anchor=(0.5, -0.02), ncol=2, fontsize=9,
                  bbox_transform=target.transFigure if hasattr(target, "transFigure") else None)


def chart_versions(out):
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.6), sharey=True)
    for ax, mode, title in ((axes[0], "без", "Без блокировок"), (axes[1], "с", "С блокировками 28.10 (200 шт.)")):
        rows = [r for r in RUNS if r[2] == mode]
        bars(ax, range(len(rows)), [r[4] for r in rows], [color(r[1]) for r in rows],
             ["шаг %d\n%s" % (r[0], r[1]) for r in rows])
        ax.set_title(title, loc="left", color=INK, fontsize=10.5)
        ax.grid(axis="x", visible=False)
    axes[0].set_ylabel("Опубликовать, с")
    axes[0].set_ylim(0, 370)
    axes[0].annotate("в этом шаге и чтение МО\n(Заполнить) шло 11,7 с\nвместо 5 с - нагрузка сервера",
                     xy=(2, 255.7), xytext=(0.15, 300), fontsize=8, color=INK2,
                     arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    legend(fig)
    fig.savefig(os.path.join(out, "01_versions.png"))
    plt.close(fig)


def chart_averages(out):
    fig, ax = plt.subplots(figsize=(6.8, 3.4))
    groups = ["Без блокировок\n(все 4 шага)", "Без блокировок\n(без шага 3)", "С блокировками"]
    v142 = [176.3, 176.3, 304.7]
    v143 = [219.9, 184.1, 264.3]
    width = 0.34
    for i, (a, b) in enumerate(zip(v142, v143)):
        for dx, value, col in ((-width / 2 - 0.02, a, V142), (width / 2 + 0.02, b, V143)):
            ax.bar(i + dx, value, width=width, color=col, edgecolor="white", linewidth=2)
            ax.text(i + dx, value + 5, "%.0f" % value, ha="center", va="bottom", fontsize=9, color=INK)
    ax.set_xticks(range(len(groups)))
    ax.set_xticklabels(groups, fontsize=9)
    ax.set_ylabel("Опубликовать, с (среднее)")
    ax.set_ylim(0, 350)
    ax.grid(axis="x", visible=False)
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    legend(fig)
    fig.savefig(os.path.join(out, "02_averages.png"))
    plt.close(fig)


def chart_fill(out):
    rows = [r for r in RUNS if r[2] == "без"]
    fig, ax = plt.subplots(figsize=(6.0, 2.8))
    bars(ax, range(len(rows)), [r[3] for r in rows], [color(r[1]) for r in rows],
         ["шаг %d\n%s" % (r[0], r[1]) for r in rows], fmt="{:.1f}")
    ax.set_ylabel("Заполнить, с")
    ax.set_ylim(0, 14)
    ax.grid(axis="x", visible=False)
    ax.set_title("Чтение данных МО: код одинаковый в обеих версиях", loc="left", color=INK, fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(out, "03_fill.png"))
    plt.close(fig)


def chart_per_block(out):
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    groups = ["Создание нового\nпоручения", "Повтор\nсуществующего"]
    per_mandate = [676.5, 735.7]
    packet = [427.4, 412.8]
    width = 0.34
    for i, (a, b) in enumerate(zip(per_mandate, packet)):
        for dx, value, col in ((-width / 2 - 0.02, a, V142), (width / 2 + 0.02, b, V143)):
            ax.bar(i + dx, value, width=width, color=col, edgecolor="white", linewidth=2)
            ax.text(i + dx, value + 12, "%.0f мс" % value, ha="center", va="bottom", fontsize=9, color=INK)
        ax.text(i, max(a, b) + 85, "-%d%%" % round((1 - b / a) * 100), ha="center", fontsize=10, color=INK,
                fontweight="bold")
    ax.set_xticks(range(len(groups)))
    ax.set_xticklabels(groups, fontsize=9)
    ax.set_ylabel("мс на одну блокировку")
    ax.set_ylim(0, 900)
    ax.grid(axis="x", visible=False)
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    legend(fig)
    fig.savefig(os.path.join(out, "04_per_block.png"))
    plt.close(fig)


def chart_estimate(out):
    fig, ax = plt.subplots(figsize=(7.4, 2.4))
    base = 41
    blocks = {"1.42": 19399 * 0.6765 / 5 / 60, "1.43": 19399 * 0.4274 / 5 / 60}
    for y, version in enumerate(("1.43", "1.42")):
        ax.barh(y, base, color=BASE, edgecolor="white", linewidth=2, height=0.55)
        ax.barh(y, blocks[version], left=base, color=color(version), edgecolor="white", linewidth=2, height=0.55)
        ax.text(base / 2, y, "выгрузка без блокировок ~41", ha="center", va="center", fontsize=8.5, color=INK)
        ax.text(base + blocks[version] / 2, y, "блокировки ~%.0f" % blocks[version], ha="center", va="center",
                fontsize=8.5, color="white")
        ax.text(base + blocks[version] + 1, y, "~%.0f мин" % (base + blocks[version]), va="center", fontsize=9.5,
                color=INK, fontweight="bold")
    ax.set_yticks([0, 1])
    ax.set_yticklabels(["1.43", "1.42"])
    ax.set_xlabel("минут, 5 потоков, 19 399 блокировок")
    ax.set_xlim(0, 100)
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    fig.savefig(os.path.join(out, "05_estimate.png"))
    plt.close(fig)


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    chart_versions(out)
    chart_averages(out)
    chart_fill(out)
    chart_per_block(out)
    chart_estimate(out)
    print("ok", out)


if __name__ == "__main__":
    main()
