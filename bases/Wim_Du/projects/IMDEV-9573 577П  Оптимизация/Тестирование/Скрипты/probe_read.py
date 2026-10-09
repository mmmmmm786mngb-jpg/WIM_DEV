# -*- coding: utf-8 -*-
"""Время ПолучитьОбъект() документа 577-П по номеру (чтение всех табличных частей из базы)."""
import os, sys, time
import stand
sys.stdout.reconfigure(encoding="utf-8")
c = stand.connect()
ref = stand.doc_by_number(c, sys.argv[1])
t = time.time(); obj = ref.ПолучитьОбъект(); print(f"ПолучитьОбъект {time.time()-t:.1f} с, Раздел7={obj.Раздел7.Количество()}", flush=True)
sys.stdout.flush(); os._exit(0)
