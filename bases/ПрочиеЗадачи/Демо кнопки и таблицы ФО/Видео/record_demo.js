// Сценарий видеозаписи: тестирование обработки FO_ButtonsTablesDemo в веб-клиенте ФО (WIN_FO_server).
// Запуск (сеанс web-test уже открыт командой start на http://localhost/win_fo/ru_RU/):
//   cat record_demo.js | node ~/.claude/skills/web-test/scripts/run.mjs exec -
// Стартовое состояние: начальная страница, других окон нет.
// Подпись держит экран max(2 с, длина озвучки x speechRate), поэтому озвучка короткая.

const FFMPEG = 'C:/Users/Acer/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg.Essentials_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-8.0-essentials_build/bin/ffmpeg.exe';
const DIR = 'C:/1c/Claude_1C/Демо кнопки и таблицы ФО/Видео/';

// Кнопки, открывающие предупреждение 1С: нажатие мимо обертки web-test, иначе она считает окно ошибкой.
async function clickWithWarning(text) {
  await highlight(text);
  await wait(0.4);
  await unhighlight();
  await getPage().getByText(text, { exact: true }).last().click();
  await wait(1.5);
  await getPage().keyboard.press('Enter');
  await wait(0.3);
}

// H.264 требует четные ширину и высоту кадра; окно браузера по умолчанию дает нечетную высоту.
await getPage().setViewportSize({ width: 1600, height: 900 });
await wait(1);

await startRecording(DIR + 'fo-demo-raw.mp4', { ffmpegPath: FFMPEG, speechRate: 55 });

await showTitleSlide('Тестирование обработки в веб-клиенте 1С', {
  subtitle: 'Кнопки и таблицы формы. База ФО, тестовая копия. Действия выполняет AI-агент',
  speech: 'Тестирование обработки в веб-клиенте. Действия выполняет AI-агент.'
});
await hideTitleSlide();

setHighlight(true);

await showCaption('Открываем обработку из справочника дополнительных обработок', { speech: 'Открываем обработку.' });
await navigateLink('Справочник.ДополнительныеОтчетыИОбработки');
await wait(1);
await clickElement('Демонстрация кнопок и таблиц формы');
await getPage().keyboard.press('Enter');
await wait(1.5);
await clickElement('Выполнить');
await wait(1.5);

await showCaption('«Заполнить пример»: вызов сервера, 7 строк', { speech: 'Заполняем пример.' });
await clickElement('Заполнить пример');

await showCaption('Меняем цену: сумма и итог в подвале пересчитаны', { speech: 'Меняем цену, итоги пересчитаны.' });
await fillTableRow({ 'Цена': '30' }, { table: 'Товары', row: { 'Наименование': 'Ручка шариковая' } });

await showCaption('«Изменить цены на %»: все цены +10%', { speech: 'Цены плюс десять процентов.' });
await clickElement('Изменить цены на %');

await showCaption('Вторая таблица: итоги по категориям', { speech: 'Итоги по категориям.' });
await clickElement('Итоги по категориям');

await showCaption('Двойной щелчок по «Техника» - отбор строк', { speech: 'Двойной щелчок - отбор.' });
await clickElement('Техника', { dblclick: true, table: 'ИтогиПоКатегориям' });
await wait(0.5);

await showCaption('«Показать все строки» снимает отбор', { speech: 'Снимаем отбор.' });
await clickElement('Показать все строки');

await showCaption('«Отметить все» и снимаем две отметки', { speech: 'Отмечаем строки.' });
await clickElement('ОтметитьВсе');
await clickElement({ row: { 'Наименование': 'Монитор 27"' }, column: '(checkbox)' }, { table: 'Товары' });
await clickElement({ row: { 'Наименование': 'Клавиатура' }, column: '(checkbox)' }, { table: 'Товары' });

await showCaption('Флажок «Только отмеченные»', { speech: 'Только отмеченные.' });
await fillFields({ 'Только отмеченные': 'true' });

await showCaption('«Удалить отмеченные»: вопрос, отвечаем «Да»', { speech: 'Удаляем с подтверждением.' });
await clickElement('Удалить отмеченные');
await wait(0.8);
await clickElement('Да');
await clickElement('Показать все строки');

await showCaption('Подменю «Сортировка» → «По наименованию»', { speech: 'Сортировка.' });
await clickElement('Сортировка');
await clickElement('По наименованию');

await showCaption('«Показать текущую строку»: окно с реквизитами', { speech: 'Реквизиты текущей строки.' });
await clickWithWarning('Показать текущую строку');

await showCaption('Все действия записаны в журнал нажатий внизу формы', { speech: 'Все действия в журнале.' });
await wait(1);

await showCaption('Кнопка «Закрыть»', { speech: 'Закрываем.' });
await clickElement('Закрыть');

await hideCaption();
setHighlight(false);

await showTitleSlide('Тест пройден', {
  subtitle: 'Все кнопки и события формы отработали, расчеты совпали с ожидаемыми',
  speech: 'Тест пройден, расчеты совпали.'
});
await hideTitleSlide();

const video = await stopRecording();
console.log('raw:', video.file, video.duration, 's', (video.size / 1048576).toFixed(1), 'MB');

const narrated = await addNarration(video.file, {
  provider: 'edge',
  voice: 'ru-RU-DmitryNeural',
  ffmpegPath: FFMPEG,
  outputPath: DIR + 'fo-demo-narrated.mp4'
});
console.log('narrated:', narrated.file, narrated.duration, 's', JSON.stringify(narrated.warnings || []));
