//Если Строка(ПараметрыСеанса.ТекущийПользователь) = "имя пользователя" Тогда 
//	Строка = ЗначениеВСтрокуВнутр(Новый Структура("Настройки, Параметры", Настройки, Параметры));
//	Файл = Новый ТекстовыйДокумент;
//	Файл.УстановитьТекст(Строка);
//	Файл.Записать("\\corp\applications\VTBAM\1C\test\tmp_Ext\НастройкиАлг.txt");
//КонецЕсли;

&НаКлиенте
Процедура Рассчитать(Команда)
	Перем ТабличныйДокумент;
	
	РассчитатьНаСервере(ТабличныйДокумент);
	ТабличныйДокумент.Показать();
КонецПроцедуры

&НаСервере
Процедура РассчитатьНаСервере(ТабличныйДокумент)
	
	Файл = Новый ТекстовыйДокумент;
	//Файл.Прочитать("\\corp\applications\VTBAM\1C\test\tmp_Ext\НастройкиАлг.txt");
	//Строка = Файл.ПолучитьТекст();
	Настройки = Новый Структура;
	Настройки.Вставить("ЗаголовокНастроек","Периодичность:Год, Дата начала расчета:ДатаВводаСредствВДУ");
	Значения = Новый Структура; 
	Значения.Вставить("ДатаНачалаРасчета","ДатаВводаСредствВДУ");
	Значения.Вставить("ЗаУспех",Истина);
	Значения.Вставить("Периодичность",Перечисления.Периодичность.Год);
	Значения.Вставить("ТаблицаКоэффициентов","AQH1AwAAAAAAAO+7v3siIyIsYWNmNjE5MmUtODFjYS00NmVmLTkzYTYtNWE2OTY4Yjc4NjYzLA0KezksDQp7NSwNCnswLCJMaW5lTnVtYmVyIiwNCnsiUGF0dGVybiIsDQp7Ik4iLDUsMCwxfQ0KfSwiIiwyMH0sDQp7MSwi0JzQuNC90JPRgNCw0L3QuNGG0LAiLA0KeyJQYXR0ZXJuIiwNCnsiTiIsMTgsMiwxfQ0KfSwiIiwyMH0sDQp7Miwi0JzQsNC60YHQk9GA0LDQvdC40YbQsCIsDQp7IlBhdHRlcm4iLA0KeyJOIiwxOCwyLDF9DQp9LCIiLDIwfSwNCnszLCLQmtC+0Y3RhNGE0LjRhtC40LXQvdGCIiwNCnsiUGF0dGVybiIsDQp7Ik4iLDcsNCwxfQ0KfSwiIiwyMH0sDQp7NCwiU291cmNlTGluZU51bWJlciIsDQp7IlBhdHRlcm4iLA0KeyJOIn0NCn0sIiIsMjB9DQp9LA0KezIsNSwwLDAsMSwxLDIsMiwzLDMsNCw0LA0KezEsNywNCnsyLDAsNSwNCnsiTiIsMX0sDQp7Ik4iLDAuMDF9LA0KeyJOIiw3NTAwMDAwMDAwMH0sDQp7Ik4iLDF9LA0KeyJOIiwwfSwwfSwNCnsyLDEsNSwNCnsiTiIsMn0sDQp7Ik4iLDc1MDAwMDAwMDAwLjAxfSwNCnsiTiIsMTUwMDAwMDAwMDAwfSwNCnsiTiIsMC44fSwNCnsiTiIsMH0sMH0sDQp7MiwyLDUsDQp7Ik4iLDN9LA0KeyJOIiwxNTAwMDAwMDAwMDAuMDF9LA0KeyJOIiwyNTAwMDAwMDAwMDB9LA0KeyJOIiwwLjY0fSwNCnsiTiIsMH0sMH0sDQp7MiwzLDUsDQp7Ik4iLDR9LA0KeyJOIiwyNTAwMDAwMDAwMDAuMDF9LA0KeyJOIiw0MDAwMDAwMDAwMDB9LA0KeyJOIiwwLjQ4fSwNCnsiTiIsMH0sMH0sDQp7Miw0LDUsDQp7Ik4iLDV9LA0KeyJOIiw0MDAwMDAwMDAwMDAuMDF9LA0KeyJOIiw2MDAwMDAwMDAwMDB9LA0KeyJOIiwwLjM2fSwNCnsiTiIsMH0sMH0sDQp7Miw1LDUsDQp7Ik4iLDZ9LA0KeyJOIiw2MDAwMDAwMDAwMDAuMDF9LA0KeyJOIiwxMDAwMDAwMDAwMDAwMDAwfSwNCnsiTiIsMC4yN30sDQp7Ik4iLDB9LDB9LA0KezIsNiw1LA0KeyJOIiw3fSwNCnsiTiIsMH0sDQp7Ik4iLDB9LA0KeyJOIiwwfSwNCnsiTiIsMH0sMH0NCn0sNCw2fSwNCnswLDB9DQp9DQp9");
	Значения.Вставить("ТипДня","КалендарныйТип");
	Значения.Вставить("ТипПериода","Календарный");
	Настройки.Вставить("Значения",Значения);
	Параметрырасчет = Новый Структура;
	Параметрырасчет.Вставить("Дата",ТекущаяДата());
	Параметрырасчет.Вставить("ДоговорДУ",Справочники.ДоговорДУ.НайтиПоНаименованию("ДУ 2760 Росвоенипотека ФГКУ"));
	Параметрырасчет.Вставить("ВалютаДокумента",Справочники.Валюты.RUB);
	Параметрырасчет.Вставить("Контрагент",Справочники.Контрагенты.НайтиПоНаименованию("АО ВИМ Инвестиции"));
	Параметрырасчет.Вставить("ДоговорКонтрагента",Справочники.ДоговорыКонтрагентов.НайтиПоНаименованию("Вознаграждение ДУ 2760"));
	Параметрырасчет.Вставить("Дневной",Ложь);
	
	//Структура = ЗначениеИзСтрокиВнутр(Строка);
	ОбработкаОбъект = РеквизитФормыВЗначение("Объект");
	Результат = ОбработкаОбъект.РезультатРасчета(Настройки, Параметрырасчет);
	Сообщить("" + Результат.СуммаВознаграждения);
	
	СтруктураСправка = Результат.СправкаРасчет.Получить();
	
	ТабДокумент = Новый ТабличныйДокумент;
	ТабДокумент.Вывести(СтруктураСправка.ШапкаРасчет);
	ТабДокумент.Вывести(СтруктураСправка.ТелоРасчет); 
	ТабДокумент.Вывести(СтруктураСправка.ПодвалРасчет);
	
	ТабличныйДокумент = ТабДокумент;	
КонецПроцедуры
