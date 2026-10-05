set -u
cd "/c/1c/Claude_1C/TestProject/Wim_Fo/projects/IMDEV-9530  Замеры ФО/Тестирование/Стенд_замеры"
python -u run_full_tests.py start
for step in A_meas A_base; do
  for i in 1 2 3; do
    out=$(python -u run_full_tests.py $step 2>&1 | tail -3); echo "$out"
    if echo "$out" | grep -q "код 0"; then break; fi
    python -c "
import json;p='results/current_full.json';s=json.load(open(p,encoding='utf-8'));s.setdefault('сбои',[]).append({k:v for k,v in s['тесты'].pop().items() if k!='вывод'});json.dump(s,open(p,'w',encoding='utf-8'),ensure_ascii=False);print('повтор')"
  done
done
for step in B C packets E P U collect; do python -u run_full_tests.py $step 2>&1 | grep -v "до:\|после:\|место хранения" | tail -8; done
python build_report_full.py 2>&1 | grep -v "^OK"
python build_report_full.py 2>&1 | grep -c "^OK"
