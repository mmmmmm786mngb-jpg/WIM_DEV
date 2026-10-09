# -*- coding: utf-8 -*-
"""Добавляет в заимствованную форму 577-П расширения T9573_Списки динамические списки разделов 1-11.

python build_lists.py
Для каждого раздела N: реквизит формы СписокРазделN (динамический список, произвольный запрос к табличной части
РазделN документа с отбором по &Ссылка, динамическое считывание, ключ Ссылка + НомерСтроки) и таблица СписокРазделN
сразу после исходной таблицы РазделN, колонки в том же порядке. Исходные таблицы скрывает код модуля формы.
Повторный запуск сначала убирает ранее добавленные списки.
"""
import os
import re
import sys
import uuid

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
FORM = os.path.join(HERE, "..", "Расширения", "T9573_Списки", "Documents", "РО_XBRL6_1_ОтчетПоВнутреннемуУчету_577П",
                    "Forms", "ФормаДокумента", "Ext", "Form.xml")
DOC = "РО_XBRL6_1_ОтчетПоВнутреннемуУчету_577П"


class Ids:
    def __init__(self, start):
        self.n = start

    def __call__(self):
        self.n += 1
        return self.n


def table_xml(n, fields, ids, ind):
    name = f"СписокРаздел{n}"
    t = ind
    lines = [
        f'{t}<Table name="{name}" id="{ids()}">',
        f"{t}\t<DataPath>{name}</DataPath>",
        f"{t}\t<ReadOnly>true</ReadOnly>",
        f'{t}\t<ContextMenu name="{name}КонтекстноеМеню" id="{ids()}"/>',
        f'{t}\t<AutoCommandBar name="{name}КоманднаяПанель" id="{ids()}"/>',
        f'{t}\t<ExtendedTooltip name="{name}РасширеннаяПодсказка" id="{ids()}"/>',
        f'{t}\t<SearchStringAddition name="{name}СтрокаПоиска" id="{ids()}"/>',
        f'{t}\t<ViewStatusAddition name="{name}СостояниеПросмотра" id="{ids()}"/>',
        f'{t}\t<SearchControlAddition name="{name}УправлениеПоиском" id="{ids()}"/>',
        f"{t}\t<ChildItems>",
    ]
    for f in fields:
        lines += [
            f'{t}\t\t<InputField name="{name}{f}" id="{ids()}">',
            f"{t}\t\t\t<DataPath>{name}.{f}</DataPath>",
            f'{t}\t\t\t<ContextMenu name="{name}{f}КонтекстноеМеню" id="{ids()}"/>',
            f'{t}\t\t\t<ExtendedTooltip name="{name}{f}РасширеннаяПодсказка" id="{ids()}"/>',
            f"{t}\t\t</InputField>",
        ]
    lines += [f"{t}\t</ChildItems>", f"{t}</Table>"]
    return "\n".join(lines)


def attribute_xml(n, fields, attr_id):
    name = f"СписокРаздел{n}"
    select = ",\n".join([f"\tРаздел{n}.Ссылка КАК Ссылка"] + [f"\tРаздел{n}.{f} КАК {f}" for f in fields])
    query = (f"ВЫБРАТЬ\n{select}\nИЗ\n\tДокумент.{DOC}.Раздел{n} КАК Раздел{n}\nГДЕ\n"
             f"\tРаздел{n}.Ссылка = &amp;Ссылка")
    u = [str(uuid.uuid4()) for _ in range(4)]
    return f"""		<Attribute name="{name}" id="{attr_id}">
			<Type>
				<v8:Type>cfg:DynamicList</v8:Type>
			</Type>
			<Settings xsi:type="DynamicList">
				<ManualQuery>true</ManualQuery>
				<DynamicDataRead>true</DynamicDataRead>
				<QueryText>{query}</QueryText>
				<KeyType>RowKey</KeyType>
				<KeyField>Ссылка</KeyField>
				<KeyField>НомерСтроки</KeyField>
				<AutoSaveUserSettings>false</AutoSaveUserSettings>
				<ListSettings>
					<dcsset:filter>
						<dcsset:viewMode>Normal</dcsset:viewMode>
						<dcsset:userSettingID>{u[0]}</dcsset:userSettingID>
					</dcsset:filter>
					<dcsset:order>
						<dcsset:item xsi:type="dcsset:OrderItemField">
							<dcsset:field>НомерСтроки</dcsset:field>
							<dcsset:orderType>Asc</dcsset:orderType>
						</dcsset:item>
						<dcsset:viewMode>Normal</dcsset:viewMode>
						<dcsset:userSettingID>{u[1]}</dcsset:userSettingID>
					</dcsset:order>
					<dcsset:conditionalAppearance>
						<dcsset:viewMode>Normal</dcsset:viewMode>
						<dcsset:userSettingID>{u[2]}</dcsset:userSettingID>
					</dcsset:conditionalAppearance>
					<dcsset:itemsViewMode>Normal</dcsset:itemsViewMode>
					<dcsset:itemsUserSettingID>{u[3]}</dcsset:itemsUserSettingID>
				</ListSettings>
			</Settings>
		</Attribute>"""


WRITE_COMMANDS = [
    ("ПровестиИЗакрытьПоСсылке", "Провести и закрыть", True),
    ("ЗаписатьПоСсылке", "Записать", False),
    ("ПровестиПоСсылке", "Провести", False),
]


def add_write_commands(main_part, ids):
    """Команды записи по ссылке вместо стандартных: стандартная запись проверяет версию данных формы, а после
    заполнения по ссылке она устаревшая. Автозаполнение командной панели выключается, чтобы убрать стандартные
    кнопки записи; Заполнить и Выгрузить остаются явными кнопками."""
    main_part = re.sub(r"\n\t<Commands>.*?\n\t</Commands>", "", main_part, flags=re.S)
    main_part = re.sub(r"\n\t\t\t<Button name=\"T9573Сп\w+\" id=\"\d+\">.*?\n\t\t\t</Button>", "", main_part, flags=re.S)
    main_part = main_part.replace('<AutoCommandBar name="ФормаКоманднаяПанель" id="-1">\r\n\t\t<Autofill>false</Autofill>',
                                  '<AutoCommandBar name="ФормаКоманднаяПанель" id="-1">')
    main_part = main_part.replace('<AutoCommandBar name="ФормаКоманднаяПанель" id="-1">\n\t\t<Autofill>false</Autofill>',
                                  '<AutoCommandBar name="ФормаКоманднаяПанель" id="-1">')
    buttons, commands = [], []
    for n, (name, title, default) in enumerate(WRITE_COMMANDS, 1):
        bname = "T9573Сп" + name
        buttons.append("\n".join([
            f'\t\t\t<Button name="{bname}" id="{ids()}">',
            "\t\t\t\t<Type>CommandBarButton</Type>",
            *(["\t\t\t\t<DefaultButton>true</DefaultButton>"] if default else []),
            f"\t\t\t\t<CommandName>Form.Command.{name}</CommandName>",
            f'\t\t\t\t<ExtendedTooltip name="{bname}РасширеннаяПодсказка" id="{ids()}"/>',
            "\t\t\t</Button>"]))
        commands.append("\n".join([
            f'\t\t<Command name="{name}" id="{1000000 + n}">',
            "\t\t\t<Title>",
            "\t\t\t\t<v8:item>",
            "\t\t\t\t\t<v8:lang>ru</v8:lang>",
            f"\t\t\t\t\t<v8:content>{title}</v8:content>",
            "\t\t\t\t</v8:item>",
            "\t\t\t</Title>",
            f"\t\t\t<Action>{name}</Action>",
            "\t\t</Command>"]))
    bar = '<AutoCommandBar name="ФормаКоманднаяПанель" id="-1">'
    main_part = main_part.replace(bar, bar + "\n\t\t<Autofill>false</Autofill>", 1)
    main_part = main_part.replace("\t\t<ChildItems>\n\t\t\t<Button name=\"Заполнить\"",
                                  "\t\t<ChildItems>\n" + "\n".join(buttons) + "\n\t\t\t<Button name=\"Заполнить\"", 1)
    main_part = main_part.replace("\n\t</Attributes>", "\n\t</Attributes>\n\t<Commands>\n" + "\n".join(commands)
                                  + "\n\t</Commands>", 1)
    return main_part


def main():
    text = open(FORM, encoding="utf-8-sig").read()
    base_pos = text.index("\t<BaseForm")
    main_part, base_part = text[:base_pos], text[base_pos:]
    main_part = re.sub(r"\n\t+<Table name=\"СписокРаздел\d+\".*?\n\t+</Table>", "", main_part, flags=re.S)
    main_part = re.sub(r"\n\t\t<Attribute name=\"СписокРаздел\d+\".*?\n\t\t</Attribute>", "", main_part, flags=re.S)
    ids = Ids(1000100)
    attrs = []
    for n in range(1, 12):
        m = re.search(r"\n(\t+)<Table name=\"Раздел%d\" id=\"\d+\">.*?\n\1</Table>" % n, main_part, re.S)
        seg, ind = m.group(0), m.group(1)
        fields = []
        for f in re.findall(r"<DataPath>Объект\.Раздел%d\.(\w+)</DataPath>" % n, seg):
            f = "НомерСтроки" if f == "LineNumber" else f
            if f not in fields:
                fields.append(f)
        if "НомерСтроки" not in fields:
            fields.insert(0, "НомерСтроки")
        query_fields = [f for f in fields if f != "НомерСтроки"]
        main_part = main_part.replace(seg, seg + "\n" + table_xml(n, fields, ids, ind), 1)
        attrs.append(attribute_xml(n, ["НомерСтроки"] + query_fields, 1000010 + n))
        print(f"Раздел{n}: колонок {len(fields)}")
    main_part = main_part.replace("\n\t</Attributes>", "\n" + "\n".join(attrs) + "\n\t</Attributes>", 1)
    main_part = add_write_commands(main_part, ids)
    with open(FORM, "w", encoding="utf-8-sig", newline="\r\n") as f:
        f.write(main_part + base_part)
    print("ok, последний id элемента", ids.n)


if __name__ == "__main__":
    main()
