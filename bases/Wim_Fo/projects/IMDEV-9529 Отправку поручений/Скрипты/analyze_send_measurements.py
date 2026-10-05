"""Анализ замеров ключевой операции "Отправка" (выгрузка оценки производительности БСП в xlsx).

Запуск: python analyze_send_measurements.py [путь_к_xlsx]
По умолчанию читает ../ЗамерыОтправкиФО_розн_сентябрь2026.xlsx.
Вес замера = число поручений, переданных в Распорядители.Отправка.
"""
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent.parent / "ЗамерыОтправкиФО_розн_сентябрь2026.xlsx"
df = pd.read_excel(path)
df["t"] = df["Время выполнения в секундах"].astype(float)
df["w"] = df["Вес замера"].astype(float)
df["dt"] = pd.to_datetime(df["Дата записи локальная"], dayfirst=True)
df["ver"] = df["Комментарий"].str.extract(r'КонфВер":"([^"]+)')[0]


def fit(frame):
    a = np.vstack([np.ones(len(frame)), frame.w]).T
    return np.linalg.lstsq(a, frame.t, rcond=None)[0]


print(f"Замеров {len(df)}, период {df.dt.min():%d.%m.%Y} - {df.dt.max():%d.%m.%Y}, "
      f"рабочих дней {df.dt.dt.date.nunique()}, с ошибкой {(df['Выполнен с ошибкой'] != 'Нет').sum()}")
print(f"Время всего {df.t.sum():.0f} с, поручений {df.w.sum():.0f}")
print("Квантили времени, с:", df.t.quantile([.5, .75, .9, .95, .99]).round(3).to_dict())

bins = [0, 1, 2, 5, 10, 20, 50, 100, 1000, 10000]
print(df.groupby(pd.cut(df.w, bins), observed=True)["t"].agg(["count", "median", "mean", "max", "sum"]).round(3))

c0, c1 = fit(df[df.w <= 50])
print(f"Модель (до 50 поручений): t = {c0:.3f} + {c1 * 1000:.1f} мс * поручений")

big = df[df.w > 100]
print(f"Массовые отправки (>100): {len(big)} шт, {big.t.sum():.0f} с = {100 * big.t.sum() / df.t.sum():.0f}% времени, "
      f"{big.w.sum():.0f} поручений = {100 * big.w.sum() / df.w.sum():.0f}%; "
      f"мс на поручение медиана {(big.t / big.w * 1000).median():.1f}")

for ver, g in df.groupby("ver"):
    a0, a1 = fit(g[g.w <= 50])
    print(f"Версия {ver}: {len(g)} замеров {g.dt.min():%d.%m}-{g.dt.max():%d.%m}, медиана при 1 поручении "
          f"{g[g.w == 1].t.median():.3f} с, модель {a0:.3f} + {a1 * 1000:.1f} мс * поручений")
