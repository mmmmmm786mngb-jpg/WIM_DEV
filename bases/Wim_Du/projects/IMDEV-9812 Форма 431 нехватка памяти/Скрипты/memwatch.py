# Опрос агента кластера раз в 0,25 с: память текущего вызова по сеансам WIM_DU и WIM_MO.
# python memwatch.py <файл.csv>   (останавливается снятием процесса)
import csv
import sys
import time

import win32com.client


def main():
    out = sys.argv[1]
    agent = win32com.client.Dispatch("V83.COMConnector").ConnectAgent("tcp://localhost:1540")
    cluster = agent.GetClusters()[0]
    agent.Authenticate(cluster, "", "")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["t", "ib", "session", "app", "mem_current", "duration_current"])
        while True:
            t = round(time.time(), 2)
            for s in agent.GetSessions(cluster):
                ib = s.InfoBase.Name.upper()
                if ib not in ("WIM_DU", "WIM_MO"):
                    continue
                w.writerow([t, ib, s.SessionID, s.AppID, s.MemoryCurrent, s.DurationCurrent])
            f.flush()
            time.sleep(0.25)


if __name__ == "__main__":
    main()
