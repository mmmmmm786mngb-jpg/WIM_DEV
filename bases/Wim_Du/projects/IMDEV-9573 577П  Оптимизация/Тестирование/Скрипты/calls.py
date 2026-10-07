# Разбивает выборку sessmem.py на серверные вызовы: начало, конец, длительность, пик MemoryCurrent, CPU.
import csv, sys
sys.stdout.reconfigure(encoding="utf-8")
def calls(path, min_ms=1000):
    r = list(csv.DictReader(open(path, encoding="utf-8")))
    out = []; cur = None
    for x in r:
        d = int(x["duration_current"])
        if d > 0:
            if cur is None or d < cur["dur"]:
                cur = {"start": x["time"], "end": x["time"], "dur": 0, "peak": 0, "cpu": 0}; out.append(cur)
            cur.update(end=x["time"], dur=d, cpu=int(x["cpu_current"]))
            cur["peak"] = max(cur["peak"], int(x["mem_current"]))
        else:
            cur = None
    return [c for c in out if c["dur"] >= min_ms]
if __name__ == "__main__":
    for p in sys.argv[1:]:
        print("==", p)
        for c in calls(p):
            print(f"  {c['start']}-{c['end']} dur {c['dur']/1000:.1f}s peak {c['peak']/2**20:.0f} MB cpu {c['cpu']/1000:.1f}s")
