// IMDEV-9434 smoke on WIM_DU
const results = [];
function ok(n, d) { results.push({name:n,status:'PASS',detail:d}); console.log('[OK]', n, ':', d); }
function fail(n, d) { results.push({name:n,status:'FAIL',detail:d}); console.log('[FAIL]', n, ':', d); }

await wait(4);
const page = await getPageState();
ok('Web session', JSON.stringify((page.sections||[]).map(s=>s.name)));

let form = null;
const trySecs = ['Сервис', 'Сервисные операции', 'Администрирование'];
for (const sec of trySecs) {
  try {
    const nav = await navigateSection(sec);
    await wait(1);
    console.log('SEC', sec, JSON.stringify(nav.commands||[]).slice(0,500));
    try {
      form = await openCommand('Групповое перезаполнение документов');
      ok('Open processing', 'section=' + sec + '; title=' + (form.title||''));
      break;
    } catch (e) {
      console.log('open fail in', sec, e.message||e);
    }
  } catch (e) {
    console.log('nav fail', sec, e.message||e);
  }
}
if (!form) {
  fail('Open processing', 'not found');
} else {
  const btnNames = (form.buttons||[]).map(b => String(b.name||b||''));
  if (btnNames.some(b => /Перезаполнить/i.test(b))) ok('Button present', 'Перезаполнить');
  else fail('Button present', JSON.stringify(btnNames));

  const vid = (form.fields||[]).find(f => (f.name||'') === 'ВидДокумента');
  ok('Form field VidDokumenta', vid ? String(vid.value) : 'missing');

  const buf = await screenshot();
  writeFileSync('C:/1c/Cursor_1c/WIM_DEV/bases/Wim_Du/projects/IMDEV-9434 ГруппПерезаполнение/Тестирование/reports/im9434_form_wim_du.png', buf);

  try {
    await clickElement('Перезаполнить');
    await wait(2);
    fail('Period guard', 'expected block, got success');
  } catch (e) {
    const msg = String(e.message||e);
    if (/период/i.test(msg)) ok('Period guard', msg.slice(0,350));
    else fail('Period guard', msg.slice(0,500));
  }
}

const passed = results.filter(r=>r.status==='PASS').length;
const failed = results.filter(r=>r.status==='FAIL').length;
writeFileSync('C:/1c/Cursor_1c/WIM_DEV/bases/Wim_Du/projects/IMDEV-9434 ГруппПерезаполнение/Тестирование/reports/im9434_wim_du_smoke.json', JSON.stringify({passed,failed,results},null,2), 'utf8');
console.log('RESULT passed=' + passed + ' failed=' + failed);
if (failed > 0) throw new Error('failed ' + failed);
