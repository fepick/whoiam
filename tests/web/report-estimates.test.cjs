const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {test} = require('node:test');

test('보고서 예상시간·진행도와 기존 ETA 보고서의 호환성을 검증한다', () => {
  const context = vm.createContext({window: {}, structuredClone, clearTimeout() {}});
  vm.runInContext(fs.readFileSync(path.join(__dirname, '../../apps/web/report.js'), 'utf8'), context);
  const report = context.window.WhoiamReport;
  const base = {date:'2026-10-30',daily:[],planned:[{title:'가상 업무',detail:'',priority:'P1',eta:'2026-11-01T09:00'}]};
  report.load(base);
  assert.equal(report.getModel().planned[0].estimated_minutes,null);
  assert.equal(report.getModel().planned[0].progress,0);
  assert.equal(report.getModel().planned[0].eta,base.planned[0].eta);
  assert.doesNotMatch(report.render(), /data-report-field="eta"/);
  assert.match(report.render(), /data-report-field="estimated_minutes"/);
  for (const changes of [{progress:101},{estimated_minutes:-1},{estimated_minutes:0.5}]) {
    report.load({...base,planned:[{...base.planned[0],...changes}]});
    assert.throws(()=>report.getModel());
  }
  report.load({...base,planned:[{...base.planned[0],estimated_minutes:120,progress:50}]});
  assert.equal(report.getModel().planned[0].progress,50);
});
