const seedPath = 'C:\\1c\\Cursor_1c\\WIM_DEV\\bases\\Wim_Pif\\projects\\nominee-owners-load\\Тестирование\\reports\\web_seed.json';
const outDir = 'C:\\1c\\Cursor_1c\\WIM_DEV\\bases\\Wim_Pif\\projects\\nominee-owners-load\\Тестирование\\reports\\';
const seed = JSON.parse(readFileSync(seedPath, 'utf8'));
const EPF = seed.epf;

const form = await openFile(EPF);
console.log('OPEN title=' + form.title);

const page = getPage();
await page.setViewportSize({ width: 1680, height: 980 });
await wait(1);

try {
  const chooserP = page.waitForEvent('filechooser', { timeout: 15000 });
  await clickElement('Выбрать файл');
  const dlg = await page.waitForSelector('#fileSelectDialogOk', { timeout: 5000 }).catch(() => null);
  if (dlg) {
    try { await page.click('a.underline.pointer'); } catch (e) {}
  }
  const chooser = await chooserP;
  await chooser.setFiles(seed.xlsx);
  await wait(1);
  if (dlg) { await page.click('#fileSelectDialogOk'); }
  await wait(2);
} catch (e) {
  console.log('FILE=' + e);
}

try {
  await clickElement('Прочитать файл');
  await wait(4);
} catch (e) {
  console.log('READ=' + e);
}

try {
  await fillFields({ 'Фонд': seed.fund });
  await wait(1);
} catch (e) {
  console.log('FUND=' + e);
}

const buf1 = await screenshot();
writeFileSync(outDir + 'form_layout_header.png', buf1);
console.log('SHOT1=form_layout_header.png');

try {
  await clickElement('Сопоставить');
  await wait(4);
} catch (e) {
  console.log('MATCH=' + e);
}

try {
  await clickElement('Строки файла');
  await wait(1);
} catch (e) {}

const buf2 = await screenshot();
writeFileSync(outDir + 'form_layout_rows.png', buf2);
console.log('SHOT2=form_layout_rows.png');

await clickElement('Протокол');
await wait(2);

const buf3 = await screenshot();
writeFileSync(outDir + 'form_layout_protocol.png', buf3);
console.log('SHOT3=form_layout_protocol.png');

const size = await page.evaluate(() => {
  const interesting = [];
  const nodes = document.querySelectorAll('div, table, form');
  for (const el of nodes) {
    const r = el.getBoundingClientRect();
    if (r.width < 200 || r.height < 40) continue;
    const cls = (el.className && el.className.toString) ? el.className.toString() : '';
    if (r.width >= 600 && r.height >= 80) {
      interesting.push({
        tag: el.tagName,
        cls: cls.slice(0, 80),
        w: Math.round(r.width),
        h: Math.round(r.height),
        t: Math.round(r.top),
        l: Math.round(r.left)
      });
    }
  }
  interesting.sort((a, b) => b.w - a.w);
  return {
    inner: { w: window.innerWidth, h: window.innerHeight },
    boxes: interesting.slice(0, 18)
  };
});
console.log('SIZE=' + JSON.stringify(size));
console.log('LAYOUT_SHOTS_OK=true');
