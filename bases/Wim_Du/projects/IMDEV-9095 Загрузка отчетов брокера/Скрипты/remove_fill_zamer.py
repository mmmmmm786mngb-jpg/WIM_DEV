#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path

form_path = list(Path(__file__).resolve().parents[1].joinpath("Обработки").rglob("Form/Module.bsl"))[0]

NEW_FILL = """&НаСервере
Процедура ЗаполнитьВсёНаСервере()
	
	ТекОбъект = РеквизитФормыВЗначение("Объект");
	ТекОбъект.ЗаполнитьТаблицуНКД();
	ТекОбъект.ЗаполнитьТаблицуПогашение();
	ТекОбъект.ЗаполнитьТаблицуДивиденды();
	ЗначениеВРеквизитФормы(ТекОбъект, "Объект");

КонецПроцедуры"""

text = form_path.read_text(encoding="utf-8")
start = text.find("&НаСервере\nПроцедура ЗаполнитьВсёНаСервере")
end = text.find("КонецПроцедуры", start) + len("КонецПроцедуры")
text = text[:start] + NEW_FILL + text[end:]
form_path.write_text(text, encoding="utf-8")
print("Fill zamer removed:", form_path)
