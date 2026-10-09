# Выход с кодом 0, когда в выборке sessmem.py завершился вызов приложения <app> длительностью >= <сек> после <ЧЧ:ММ:СС>.
import sys, calls
path, app, min_s, after = sys.argv[1], sys.argv[2], float(sys.argv[3]), sys.argv[4]
rows = open(path, encoding="utf-8").read().splitlines()
last = {}
for line in rows[1:]:
    p = line.split(",")
    last[p[1]] = p
for c in calls.calls(path, int(min_s * 1000)):
    if c["app"] == app and c["start"] >= after and last.get(c["session"], ["", "", "", "", "", "", "", "1"])[7] == "0":
        print(c); sys.exit(0)
sys.exit(1)
