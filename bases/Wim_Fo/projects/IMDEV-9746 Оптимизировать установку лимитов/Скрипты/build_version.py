# -*- coding: utf-8 -*-
"""IMDEV-9746. Сборка версии обработки распространения правил из папки версии против разработческой ФО (-Checks off).

    python build_version.py УСКОРЕНО_1_17   -> УСКОРЕНО_1_17/внРаспространениеПравилСОдногоКлиентаНаСписокКлиентов.epf
"""
import json
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")
TASK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAME = "внРаспространениеПравилСОдногоКлиентаНаСписокКлиентов"
REGISTRY = r"C:\1c\Cursor_1c\WIM_DEV\.v8-project.json"
BUILD = os.path.join(os.path.expanduser("~"), ".claude", "skills", "epf-build", "scripts", "epf-build.ps1")
V8 = r"C:\Program Files\1cv8\8.3.27.2214\bin"


def main(folder):
    with open(REGISTRY, encoding="utf-8-sig") as f:
        db = next(d for d in json.load(f)["databases"] if d["id"] == "wim_fo")
    src = os.path.join(TASK, folder, NAME + "_epf", NAME + ".xml")
    out = os.path.join(TASK, folder, NAME + ".epf")
    cmd = ["powershell.exe", "-NoProfile", "-File", BUILD, "-V8Path", V8, "-InfoBaseServer", db["server"],
           "-InfoBaseRef", db["ref"], "-SourceFile", src, "-OutputFile", out, "-Checks", "off"]
    if db.get("user"):
        cmd += ["-UserName", db["user"], "-Password", db.get("password", "")]
    result = subprocess.run(cmd, capture_output=True)
    print((result.stdout or b"").decode("utf-8", errors="replace").strip()[-500:])
    sys.exit(result.returncode)


if __name__ == "__main__":
    main(sys.argv[1])
