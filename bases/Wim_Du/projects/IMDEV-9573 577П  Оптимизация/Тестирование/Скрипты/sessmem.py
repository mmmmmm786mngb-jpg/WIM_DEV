# -*- coding: utf-8 -*-
"""Память серверных вызовов сеансов веб-клиента WIM_DU по данным агента кластера.

python sessmem.py <секунд> <файл.csv>
Раз в 0,5 с пишет по каждому сеансу WebClient: MemoryCurrent (память текущего вызова),
MemoryLast5Min, MemoryAll. Пик MemoryCurrent за прогон = пик памяти вызова.
"""
import csv
import os
import sys
import time

import win32com.client


def main():
    seconds, out = float(sys.argv[1]), sys.argv[2]
    agent = win32com.client.Dispatch("V83.COMConnector").ConnectAgent("tcp://localhost:1540")
    cluster = agent.GetClusters()[0]
    agent.Authenticate(cluster, "", "")
    end = time.time() + seconds
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["time", "session", "app", "mem_current", "mem_5min", "mem_all", "cpu_current", "duration_current"])
        while time.time() < end:
            t = time.strftime("%H:%M:%S")
            for s in agent.GetSessions(cluster):
                if s.InfoBase.Name.upper() != "WIM_DU" or s.AppID != "WebClient":
                    continue
                w.writerow([t, s.SessionID, s.AppID, s.MemoryCurrent, s.MemoryLast5Min, s.MemoryAll,
                            s.CPUTimeCurrent, s.DurationCurrent])
            f.flush()
            time.sleep(0.5)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("ERROR", exc)
    sys.stdout.flush()
    os._exit(0)
