# Сборка обработки Верификация431 для Т-1.
# Модуль объекта = Верификация\object_template.bsl, в который вставляется область РасчетTWRПачками
# из модуля 1.08 (ОПТИМИЗИРОВАНО) без изменений, кроме размера пачки: он берется с формы проверки.
# Результат: Верификация\Верификация431.epf (сборка через dev WIM_DU).
import glob
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
TASK = os.path.dirname(HERE)
VER = os.path.join(TASK, "Верификация")


def region_108():
    p = glob.glob(os.path.join(TASK, "ОПТИМИЗИРОВАНО", "*_epf", "*", "Ext", "ObjectModule.bsl"))[0]
    s = open(p, encoding="utf-8-sig").read().replace("\r\n", "\n")
    i = s.index("#Область РасчетTWRПачками")
    j = s.index("#КонецОбласти", i) + len("#КонецОбласти")
    r = s[i:j]
    assert r.count("\tВозврат 500;") == 1
    return r.replace("\tВозврат 500;", "\tВозврат РазмерПачкиПроверки;")


def main():
    t = open(os.path.join(VER, "object_template.bsl"), encoding="utf-8").read()
    module = t.replace("%%REGION_108%%", region_108())
    out = os.path.join(VER, "src", "Верификация431", "Ext", "ObjectModule.bsl")
    open(out, "w", encoding="utf-8-sig", newline="\r\n").write(module)
    epf = os.path.join(VER, "Верификация431.epf")
    r = subprocess.run(["powershell.exe", "-NoProfile", "-File",
                        os.path.expanduser("~/.claude/skills/epf-build/scripts/epf-build.ps1"),
                        "-InfoBaseServer", "localhost", "-InfoBaseRef", "WIM_DU", "-Checks", "handlers",
                        "-SourceFile", os.path.join(VER, "src", "Верификация431.xml"), "-OutputFile", epf],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(r.stdout[-400:], r.stderr[-400:])
    print("epf", os.path.exists(epf))


if __name__ == "__main__":
    main()
