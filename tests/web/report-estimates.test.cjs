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

test('진행사항의 신규 표시와 우선순위·진행도는 날짜와 저장 모델에 반영된다',()=>{
  const context=vm.createContext({window:{},structuredClone,clearTimeout(){}});
  vm.runInContext(fs.readFileSync(path.join(__dirname,'../../apps/web/report.js'),'utf8'),context);
  const report=context.window.WhoiamReport;
  const row={title:'가상 신규',detail:'',minutes:20,status:'진행 중',priority:'P1',progress:65,created_date:'2026-11-12'};
  report.load({date:'2026-11-12',daily:[row]});
  assert.match(report.render(),/new!/);
  assert.match(report.render(),/aria-label="진행 1 우선순위"/);
  assert.ok(report.render().includes('aria-label="진행 1 진행도 (%)"'));
  assert.ok(report.reportMessage().includes('[new!]'));
  assert.equal(report.getModel().daily[0].progress,65);
  report.load({date:'2026-11-13',daily:[row]});
  assert.doesNotMatch(report.render(),/new!/);
  for(const changes of [{priority:'P4'},{progress:101},{progress:0.5}]) {
    report.load({date:'2026-11-12',daily:[{...row,...changes}]});
    assert.throws(()=>report.getModel());
  }
});
