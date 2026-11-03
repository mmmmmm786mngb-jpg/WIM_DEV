# -*- coding: utf-8 -*-
"""IMDEV-9746. Сборка стендовой обработки T9746_СтендРаспространения из epf_src против разработческой ФО (wim_fo).

Проверка перед сборкой отключена (-Checks off): временная база-заглушка не знает метаданных ФО.
Компиляция модуля проверяется прогоном сценариев стенда на разработческой базе.

    python build_epf.py      -> epf/T9746_СтендРаспространения.epf
"""
import json
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
NAME = "T9746_СтендРаспространения"
REGISTRY = r"C:\1c\Cursor_1c\WIM_DEV\.v8-project.json"
BUILD = os.path.join(os.path.expanduser("~"), ".claude", "skills", "epf-build", "scripts", "epf-build.ps1")
V8 = r"C:\Program Files\1cv8\8.3.27.2214\bin"


def main():
    with open(REGISTRY, encoding="utf-8-sig") as f:
        db = next(d for d in json.load(f)["databases"] if d["id"] == "wim_fo")
    out_dir = os.path.join(HERE, "epf")
    os.makedirs(out_dir, exist_ok=True)
    cmd = ["powershell.exe", "-NoProfile", "-File", BUILD, "-V8Path", V8, "-InfoBaseServer", db["server"],
           "-InfoBaseRef", db["ref"], "-SourceFile", os.path.join(HERE, "epf_src", NAME + ".xml"),
           "-OutputFile", os.path.join(out_dir, NAME + ".epf"), "-Checks", "off"]
    if db.get("user"):
        cmd += ["-UserName", db["user"], "-Password", db.get("password", "")]
    result = subprocess.run(cmd, capture_output=True)
    for stream in (result.stdout, result.stderr):
        text = stream.decode("utf-8", errors="replace") if stream else ""
        if "\ufffd" in text:
            text = stream.decode("cp866", errors="replace")
        print(text.strip())
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
