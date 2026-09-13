---
name: 1c-query-optimization
description: "Продвинутая оптимизация запросов 1С: временные таблицы, соединения вместо подзапросов, агрегаты, СКД, большие выборки. Используй когда запрос медленный, многошаговый или читает большие регистры"
---

# 1C Query Optimization Skill (Advanced Patterns)

Продвинутые паттерны оптимизации запросов. Синтаксис языка и типовые ловушки - скилл `composing-1c-queries` (в том числе `references/optimization-and-pitfalls.md`). Правила `query-optimization-tips.md` и `anti_patterns.md` из набора Desko77 в этот репозиторий не ставились.

## Validate Query via AI-EDT

Если сервер AI-EDT подключен (инструменты `ai-edt` доступны), проверяй оптимизированный запрос через `validate_query` - убедись, что после рефакторинга нет синтаксических/семантических ошибок. Для запросов СКД: `dcsMode=true`.

## When to Use

Invoke this skill when:
- Working with complex multi-step data processing
- Optimizing joins and subqueries
- Implementing DCS reports
- Processing large datasets in portions

## Temporary Tables - When to Use

Use temporary tables for:
- Complex multi-step data processing
- Joining data from multiple sources
- Reusing intermediate results

### Join vs Subquery (basic choice)

```bsl
// PREFERRED: Join (usually faster)
"ВЫБРАТЬ
|	Заказы.Ссылка КАК Заказ,
|	Контрагенты.ИНН КАК ИНН
|ИЗ
|	Документ.ЗаказКлиента КАК Заказы
|		ЛЕВОЕ СОЕДИНЕНИЕ Справочник.Контрагенты КАК Контрагенты
|		ПО Заказы.Контрагент = Контрагенты.Ссылка"

// AVOID: Subquery in SELECT (N+1 problem)
"ВЫБРАТЬ
|	Заказы.Ссылка КАК Заказ,
|	(ВЫБРАТЬ К.ИНН ИЗ Справочник.Контрагенты КАК К
|	 ГДЕ К.Ссылка = Заказы.Контрагент) КАК ИНН
|ИЗ
|	Документ.ЗаказКлиента КАК Заказы"
```

### Avoid Aggregation in Subqueries

```bsl
// SLOW: Subquery with aggregation
"ВЫБРАТЬ
|	Номенклатура.Ссылка,
|	(ВЫБРАТЬ СУММА(Остатки.Количество) ...) КАК Остаток
|ИЗ
|	Справочник.Номенклатура КАК Номенклатура"

// FAST: Join with pre-aggregated data
"ВЫБРАТЬ
|	Номенклатура.Ссылка КАК Номенклатура,
|	ЕСТЬNULL(Остатки.КоличествоОстаток, 0) КАК Остаток
|ИЗ
|	Справочник.Номенклатура КАК Номенклатура
|		ЛЕВОЕ СОЕДИНЕНИЕ РегистрНакопления.ТоварыНаСкладах.Остатки КАК Остатки
|		ПО Номенклатура.Ссылка = Остатки.Номенклатура"
```

---

**Reference**: [ITS Query Optimization Standards](https://its.1c.ru/db/v8std/browse/13/-1/26/28)
