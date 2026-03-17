Перем DataTypeEnum Экспорт;
Перем ParameterDirectionEnum Экспорт;
Перем CommandTypeEnum Экспорт;



Процедура ЗаполнитьСтруктурыАДО()
	
	DataTypeEnum = Новый Структура();
	DataTypeEnum.Вставить("adVarBinary", 204);
	DataTypeEnum.Вставить("AdArray",  "8192"); //  0x2000 A flag value, always combined with another data type constant, that indicates an array of that other data type.  
	DataTypeEnum.Вставить("adBigInt",  20); //  Indicates an eight-byte signed integer (DBTYPE_I8). 
	DataTypeEnum.Вставить("adBinary",  128); //  Indicates a binary value (DBTYPE_BYTES). 
	DataTypeEnum.Вставить("adBoolean",  11); //  Indicates a boolean value (DBTYPE_BOOL). 
	DataTypeEnum.Вставить("adBSTR",  8); //  Indicates a null-terminated character string (Unicode) (DBTYPE_BSTR). 
	DataTypeEnum.Вставить("adChapter",  136); //  Indicates a four-byte chapter value that identifies rows in a child rowset (DBTYPE_HCHAPTER). 
	DataTypeEnum.Вставить("adChar",  129); //  Indicates a string value (DBTYPE_STR). 
	DataTypeEnum.Вставить("adCurrency",  6); //  Indicates a currency value (DBTYPE_CY). Currency is a fixed-point number with four digits to the right of the decimal point. It is stored in an eight-byte signed integer scaled by 10,000. 
	DataTypeEnum.Вставить("adDate",  7); //  Indicates a date value (DBTYPE_DATE). A date is stored as a double, the whole part of which is the number of days since December 30, 1899, and the fractional part of which is the fraction of a day. 
	DataTypeEnum.Вставить("adDBDate",  133); //  Indicates a date value (yyyymmdd) (DBTYPE_DBDATE). 
	DataTypeEnum.Вставить("adDBTime",  134); //  Indicates a time value (hhmmss) (DBTYPE_DBTIME). 
	DataTypeEnum.Вставить("adDBTimeStamp",  135); //  Indicates a date/time stamp (yyyymmddhhmmss plus a fraction in billionths) (DBTYPE_DBTIMESTAMP). 
	DataTypeEnum.Вставить("adDecimal",  14); //  Indicates an exact numeric value with a fixed precision and scale (DBTYPE_DECIMAL). 
	DataTypeEnum.Вставить("adDouble",  5); //  Indicates a double-precision floating-point value (DBTYPE_R8). 
	DataTypeEnum.Вставить("adEmpty",  0); //  Specifies no value (DBTYPE_EMPTY). 
	DataTypeEnum.Вставить("adError",  10); //  Indicates a 32-bit error code (DBTYPE_ERROR). 
	DataTypeEnum.Вставить("adFileTime",  64); //  Indicates a 64-bit value representing the number of 100-nanosecond intervals since January 1, 1601 (DBTYPE_FILETIME). 
	DataTypeEnum.Вставить("adGUID",  72); //  Indicates a globally unique identifier (GUID) (DBTYPE_GUID). 
	DataTypeEnum.Вставить("adIDispatch",  9); //  
	
	DataTypeEnum.Вставить("adInteger", 3); // 
	DataTypeEnum.Вставить("adIUnknown",  13);
	DataTypeEnum.Вставить("adLongVarBinary", 205);
	DataTypeEnum.Вставить("adLongVarChar", 201);
	DataTypeEnum.Вставить("adLongVarWChar", 203);
	DataTypeEnum.Вставить("adNumeric", 131);
	DataTypeEnum.Вставить("adPropVariant",  138); //  Indicates an Automation PROPVARIANT (DBTYPE_PROP_VARIANT). 
	DataTypeEnum.Вставить("adSingle",  4); //  Indicates a single-precision floating-point value (DBTYPE_R4). 
	DataTypeEnum.Вставить("adSmallInt",  2); //  Indicates a two-byte signed integer (DBTYPE_I2). 
	DataTypeEnum.Вставить("adTinyInt",  16); // Indicates a one-byte signed integer (DBTYPE_I1). 
	DataTypeEnum.Вставить("adUnsignedBigInt",  21); //  Indicates an eight-byte unsigned integer (DBTYPE_UI8). 
	DataTypeEnum.Вставить("adUnsignedInt",  19); // Indicates a four-byte unsigned integer (DBTYPE_UI4). 
	DataTypeEnum.Вставить("adUnsignedSmallInt",  18); // Indicates a two-byte unsigned integer (DBTYPE_UI2). 
	DataTypeEnum.Вставить("adUnsignedTinyInt",  17); // Indicates a one-byte unsigned integer (DBTYPE_UI1). 
	DataTypeEnum.Вставить("adUserDefined",  132); // Indicates a user-defined variable (DBTYPE_UDT). 
	DataTypeEnum.Вставить("adVarBinary",  204); // Indicates a binary value. 
	DataTypeEnum.Вставить("adVarChar",  200); // Indicates a string value. 
	DataTypeEnum.Вставить("adVariant",  12); // Indicates an Automation Variant (DBTYPE_VARIANT). 
	DataTypeEnum.Вставить("adVarNumeric",   139); //  Indicates a numeric value. 
	DataTypeEnum.Вставить("adVarWChar",   202); //  Indicates a null-terminated Unicode character string. 
	DataTypeEnum.Вставить("adWChar",   130); //  Indicates a null-terminated Unicode character string (DBTYPE_WSTR). 
	
	ParameterDirectionEnum = Новый Структура();
	ParameterDirectionEnum.Вставить("adParamInput", 1);  // Default. Indicates that the parameter represents an input parameter.
	ParameterDirectionEnum.Вставить("adParamInputOutput",  3);  // Indicates that the parameter represents both an input and output parameter. 
	ParameterDirectionEnum.Вставить("adParamOutput",  2);  // Indicates that the parameter represents an output parameter.  
	ParameterDirectionEnum.Вставить("adParamReturnValue",  4);  // Indicates that the parameter represents a return value. 
	ParameterDirectionEnum.Вставить("adParamUnknown",  0);  // 
	
	CommandTypeEnum = Новый Структура();
	CommandTypeEnum.Вставить("adCmdUnspecified",   -1);  //  Does not specify the command type argument. 
	CommandTypeEnum.Вставить("adCmdText",   1);  //  Evaluates CommandText as a textual definition of a command or stored procedure call. 
	CommandTypeEnum.Вставить("adCmdTable",   2);  //  Evaluates CommandText as a table name whose columns are all returned by an internally generated SQL query. 
	CommandTypeEnum.Вставить("adCmdStoredProc",   4);  //  Evaluates CommandText as a stored procedure name. 
	CommandTypeEnum.Вставить("adCmdUnknown",   8);  //  Default. Indicates that the type of command in the CommandText property is not known. 
	CommandTypeEnum.Вставить("adCmdFile",   256);  //  Evaluates CommandText as the file name of a persistently stored Recordset. Used with Recordset.Open or Requery only. 
	CommandTypeEnum.Вставить("adCmdTableDirect",   512);  //  
	
КонецПроцедуры

Процедура ОбработатьВыписки() Экспорт
	Перем Команда, КомандаКлиенты, Набор, НаборКлиенты, Соединение;
	
	МассивФайловНаПечать = Новый Массив;

	ВнешниеДанные.ADOConnect(Соединение, Команда, Набор, ПланыВидовХарактеристик.ВнешниеИсточники.Документооборот, 300, 600);
	
	
	Запрос = Новый Запрос;
	Запрос.Текст = 
	"ВЫБРАТЬ
	|	КодыЗагрузки.Код КАК КодКлиента,
	|	Выписка.ВладелецСчета.Код,
	|	Выписка.ВладелецСчета,
	|	Выписка.Ссылка,
	|	Выписка.Номер,
	|	Выписка.Дата
	|ИЗ
	|	Документ.Выписка КАК Выписка
	|		ВНУТРЕННЕЕ СОЕДИНЕНИЕ Справочник.КодыЗагрузки КАК КодыЗагрузки
	|		ПО Выписка.ВладелецСчета = КодыЗагрузки.Владелец
	|			И (КодыЗагрузки.Биржа = ЗНАЧЕНИЕ(Справочник.КлассификаторыЗагрузки.Клиенты))
	|ГДЕ
	|	Выписка.ДокументОснование.ВидОперацииД = ЗНАЧЕНИЕ(Справочник.ВидыОпераций.ОткрытиеСчетаДепо)
	|	И Выписка.Дата >= ДАТАВРЕМЯ(2011, 1, 27)";
	
	Выборка = Запрос.Выполнить().Выбрать();
	Пока Выборка.Следующий() Цикл
		
		Команда = Новый COMОбъект("ADODB.Command");
		Команда.CommandType = CommandTypeEnum.adCmdText;
		Команда.ActiveConnection = Соединение;
		Команда.CommandText = "SELECT DocumentNumber, DocumentDate FROM Documents WHERE TypeId = 27 AND IsActive=1 AND DocumentNumber IS NOT NULL AND ClientID = '" + СокрЛП(Выборка.КодКлиента)+"'";
		
		rs = Команда.Execute();
		
		Пока Не rs.EOF() Цикл
			
			Сообщить("Выписка № " + Выборка.Номер + " от " + Выборка.Дата + " получит номер " + rs.Fields("DocumentNumber").Value + " от " + rs.Fields("DocumentDate").Value);
			Выписка = Выборка.Ссылка.ПолучитьОбъект();
			Выписка.РучнойВвод = Истина;
			Выписка.Номер = СокрЛП(rs.Fields("DocumentNumber").Value);
			Выписка.ИсходящийНомер = Выписка.Номер;
			Выписка.Записать(РежимЗаписиДокумента.Запись);
			rs.MoveNext();
			
		КонецЦикла;
		
	КонецЦикла;
	
КонецПроцедуры

Процедура ПеренумероватьДокументы() Экспорт
	
	НумераторыОбъектов.ПеренумероватьДокументыЗаПериод(НачалоПериода, КонецПериода);
	
КонецПроцедуры

ЗаполнитьСтруктурыАДО();
ОбщегоНазначения.ЛогироватьИспользованиеОбъекта(ЭтотОбъект);
