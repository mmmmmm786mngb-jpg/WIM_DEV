# IMDEV-7330 documentation

- [imdev7330_ndfl_formation_research.md](imdev7330_ndfl_formation_research.md) — изыскания: обработка «Формирование начислений НДФЛ», схема вызовов, тяжёлые запросы, документ «Начисление НДФЛ по портфелю».
- [imdev7330_ndfl_formation_processing_optimization.html](imdev7330_ndfl_formation_processing_optimization.html) — план оптимизаций при создании документов из обработки: пакетный поиск по портфелям, кэш в Соответствие, запрос НКД.
- [imdev7330_ndfl_repeated_queries_rasschitatndfl.html](imdev7330_ndfl_repeated_queries_rasschitatndfl.html) — повторные вызовы запросов внутри `РассчитатьНДФЛ`.
- [imdev7330_ndfl_mass_precalc_oborots.html](imdev7330_ndfl_mass_precalc_oborots.html) — план разработки массового предрасчёта `ОбщиеОбороты` по массиву портфелей: технический документ-контейнер, новый параметр `РассчитатьНДФЛ(ПараметрыРасчета)`, кэш `Портфель → ТаблицаОборотов`, точки вставки кода в обработку и в документ (расширение `NDFL_RDU`).
- [../ПрмерыОПТИМИЗАЦИИ.md](../ПрмерыОПТИМИЗАЦИИ.md) — черновик идей по тексту запроса НКД (объединение оборотов, ВТ, индексы).
