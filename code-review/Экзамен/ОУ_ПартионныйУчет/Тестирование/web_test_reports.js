// Web-client test: form both reports and verify data for current month
const results = [];
const shotDir = 'C:/1c/Cursor_1c/WIM_DEV/code-review/Экзамен/ОУ_ПартионныйУчет/Тестирование/reports/';

function ok(name, detail, extra) {
  results.push(Object.assign({ name, status: 'PASS', detail }, extra || {}));
  console.log('[OK] ' + name + ': ' + detail);
}
function fail(name, detail, extra) {
  results.push(Object.assign({ name, status: 'FAIL', detail }, extra || {}));
  console.log('[FAIL] ' + name + ': ' + detail);
}

async function saveShot(name) {
  const buf = await screenshot();
  writeFileSync(shotDir + name + '.png', buf);
}

function hasBusinessData(report) {
  const text = JSON.stringify(report || {});
  // Must see quantity/cost columns or known item, not only period params
  if (/WebReport Goods|Количество|Сумма продажи|Себестоимость|Валовая|Стоимость|Партия/i.test(text)) {
    // Empty September still has headers - require numeric-looking values or item name
    if (/WebReport Goods/.test(text)) return true;
    if (report.data && report.data.length > 0) {
      return report.data.some(row => {
        const vals = Object.values(row || {}).join(' ');
        return /\d/.test(vals) && !/Параметры|Период:/i.test(vals);
      });
    }
    if (report.rows && report.rows.length > 0) {
      return report.rows.some(r => {
        const line = Array.isArray(r) ? r.join(' ') : String(r);
        return /WebReport Goods|\d{1,}/.test(line) && !/^Параметры/.test(line);
      });
    }
    if (report.totals && Object.keys(report.totals).length > 0) {
      return Object.values(report.totals).some(v => v && String(v).replace(/\s/g, '') !== '' && /\d/.test(String(v)));
    }
  }
  return false;
}

async function openAndForm(commandTitle) {
  await navigateSection('Оперативный учет');
  const form = await openCommand(commandTitle);
  console.log('opened:', form.title);
  console.log('reportSettings:', JSON.stringify(form.reportSettings || null));
  console.log('buttons:', JSON.stringify((form.buttons || []).map(b => b.name || b)));

  // Try widen period to this year if sales report
  if (/Продажи/i.test(commandTitle)) {
    try {
      await fillFields({ 'Период': 'Этот год' });
      console.log('period set to Этот год');
    } catch (e) {
      console.log('period fill skip:', e.message || e);
      try {
        await clickElement('Период');
        await wait(1);
        const st = await getFormState();
        console.log('after period click buttons/fields:', JSON.stringify({
          buttons: (st.buttons || []).map(b => b.name || b).slice(0, 20),
          fields: (st.fields || []).map(f => f.name || f.label).slice(0, 20),
          submenu: st.submenu || null
        }));
      } catch (e2) {
        console.log('period pick skip:', e2.message || e2);
      }
    }
  }

  await clickElement('Сформировать');
  await wait(7);
  const report = await readSpreadsheet();
  console.log('spreadsheet keys:', Object.keys(report || {}));
  console.log('headers:', JSON.stringify(report.headers || null));
  console.log('total:', report.total);
  console.log('data0:', JSON.stringify((report.data || []).slice(0, 3)));
  console.log('rows0:', JSON.stringify((report.rows || []).slice(0, 8)));
  console.log('totals:', JSON.stringify(report.totals || null));
  return report;
}

await wait(2);
const pageState = await getPageState();
ok('Web client loaded', JSON.stringify(pageState.sections || []));

// --- Sales report ---
const sales = await openAndForm('Продажи за период');
await saveShot('web_report_sales');
if (hasBusinessData(sales)) {
  ok('Client report ProdazhiZaPeriod', 'formed with data; ' + JSON.stringify({
    title: sales.title,
    headers: sales.headers,
    total: sales.total,
    sample: (sales.data || sales.rows || []).slice(0, 5),
    totals: sales.totals || null
  }));
} else {
  fail('Client report ProdazhiZaPeriod', 'opened/formed but no business data detected: ' + JSON.stringify(sales).slice(0, 1500));
}

try { await closeForm({ save: false }); } catch (_) {}
await wait(1);

// --- Stock report ---
const stock = await openAndForm('Остатки товаров по партиям');
await saveShot('web_report_stock');
if (hasBusinessData(stock)) {
  ok('Client report OstatkiTovarovPoPartiyam', 'formed with data; ' + JSON.stringify({
    title: stock.title,
    headers: stock.headers,
    total: stock.total,
    sample: (stock.data || stock.rows || []).slice(0, 5),
    totals: stock.totals || null
  }));
} else {
  fail('Client report OstatkiTovarovPoPartiyam', 'opened/formed but no business data detected: ' + JSON.stringify(stock).slice(0, 1500));
}

const passed = results.filter(r => r.status === 'PASS').length;
const failed = results.filter(r => r.status === 'FAIL').length;
writeFileSync(shotDir + 'web_reports_test.json', JSON.stringify({ passed, failed, results }, null, 2), 'utf8');
console.log('RESULT passed=' + passed + ' failed=' + failed);
if (failed > 0) throw new Error('Failed checks: ' + failed);
