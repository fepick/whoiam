const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const {test}=require('node:test');

function report() {
  const context=vm.createContext({window:{},structuredClone,clearTimeout(){}});
  vm.runInContext(fs.readFileSync(path.join(__dirname,'../../apps/web/report.js'),'utf8'),context);
  return context.window.WhoiamReport;
}

test('텍스트 보고는 선택한 날짜의 진행 업무만 번호와 세부 항목으로 만든다',()=>{
  const api=report();
  api.load({date:'2026-11-02',daily:[
    {title:'센서 검토',detail:'후보 선정 완료\r\n\n용액 특성 확인 필요',minutes:60,status:'진행 중'},
    {title:'납땜',detail:'- 배송 부품 제외 90% 완료',minutes:30,status:'진행 중'},
    {title:'배선 재단',detail:'',minutes:10,status:'완료'},
  ],planned:[{title:'제외할 예정 업무',detail:'예정 상세',priority:'P1'}],note:'제외할 공유사항'});
  assert.equal(api.reportMessage(),'26.11.2 진행 업무 보고드립니다.\n1. 센서 검토\n    - 후보 선정 완료\n    - 용액 특성 확인 필요\n2. 납땜\n    - 배송 부품 제외 90% 완료\n3. 배선 재단');
  assert.match(api.render(),/id="report-message"/);
});

test('빈 업무는 번호에서 제외하고 잘못된 날짜나 진행사항이 없으면 빈 메시지를 만든다',()=>{
  const api=report();
  api.load({date:'2026-01-01',daily:[{title:' ',detail:'입력 중'},{title:'가상 업무',detail:''}]});
  assert.equal(api.reportMessage(),'26.1.1 진행 업무 보고드립니다.\n1. 가상 업무');
  api.load({date:'2026-02-30',daily:[{title:'업무'}]});assert.equal(api.reportMessage(),'');
  api.load({date:'2026-11-02',daily:[],planned:[{title:'예정 업무'}]});assert.equal(api.reportMessage(),'');
  assert.match(api.render(),/data-report-action="copy-message" disabled/);
});

test('텍스트 보고의 HTML 문자는 편집 화면에서 실행되지 않도록 이스케이프한다',()=>{
  const api=report();api.load({date:'2026-11-02',daily:[{title:'<img src=x>',detail:'</textarea><script>fake</script>'}]});
  assert.match(api.reportMessage(),/<img src=x>/);
  assert.doesNotMatch(api.render(),/<script>fake<\/script>/);
  assert.match(api.render(),/&lt;\/textarea&gt;&lt;script&gt;fake/);
});
