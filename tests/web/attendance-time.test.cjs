// 실제 브라우저나 운영 저장소 없이 웹의 시각 변환과 안내를 검증한다.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {test} = require('node:test');

function application() {
  const elements = new Map();
  const element = id => {
    if (!elements.has(id)) elements.set(id, {
      innerHTML: '', open: false, addEventListener() {},
      showModal() {this.open = true;}, setAttribute() {},
    });
    return elements.get(id);
  };
  const context = vm.createContext({
    document: {addEventListener() {}, getElementById: element},
    window: {addEventListener() {}}, location: {hash: ''},
    URLSearchParams, setInterval() {}, clearTimeout() {},
    fetch: () => new Promise(() => {}),
  });
  vm.runInContext(fs.readFileSync(path.join(__dirname, '../../apps/web/app.js'), 'utf8'), context);
  return {context, element};
}

test('24시간 입력은 숫자 입력을 정규화하고 범위를 검사한다', () => {
  const {context} = application();
  for (const [input, expected] of [['900','09:00'], ['0900','09:00'], ['0:00','00:00'], ['1200','12:00'], ['2359','23:59'], ['24:00',null], ['1260',null], ['오후 1:00',null], ['', '']]) {
    assert.equal(vm.runInContext(`normalizeClock(${JSON.stringify(input)})`, context), expected);
  }
  const html = vm.runInContext("dateTimeField('ETA', 'eta', '2026-10-30T18:30')", context);
  assert.doesNotMatch(html, /type="(?:time|datetime-local)"/);
  assert.match(html, /data-time-part="clock"[^>]*value="18:30"/);
});

test('오전·오후·정오·자정 시각을 24시간제 한국 시간으로 전달한다', () => {
  const {context} = application();
  for (const [utc, local] of [
    ['2026-10-27T00:00:00+00:00', '2026-10-27T09:00'],
    ['2026-10-27T09:00:00+00:00', '2026-10-27T18:00'],
    ['2026-10-27T03:00:00+00:00', '2026-10-27T12:00'],
    ['2026-10-26T15:00:00+00:00', '2026-10-27T00:00'],
  ]) {
    assert.equal(vm.runInContext(`localInput(${JSON.stringify(utc)})`, context), local);
    assert.equal(vm.runInContext(`zoned(${JSON.stringify(local)})`, context), `${local}:00+09:00`);
  }
});

test('수동 입력에 실제 근무 안내와 24시간제 확인란을 표시한다', () => {
  const {context, element} = application();
  vm.runInContext('data = {sessions: [], today:"2026-10-27"}; showTime();', context);
  const html = element('dialog-content').innerHTML;
  assert.match(html, /name="session_start"/);
  assert.match(html, /name="session_end"/);
  assert.match(html, /퇴근 예정 시각은 저장할 수 없습니다/);
  assert.match(html, /24시간제/);
  assert.match(html, /수동 입력이 우선/);
  assert.match(html, /value="2026-10-27T12:00"/);
  assert.match(html, /value="2026-10-27T13:00"/);
  const summary = vm.runInContext("manualTimeSummary('2026-10-27T09:00', '2026-10-27T18:00')", context);
  assert.match(summary, /09:00.*18:00/);
});

test('산정 규칙을 켜면 수동 입력은 추가 휴게만 받고 기존 야근 선택을 유지한다',()=>{
  const {context,element}=application();
  vm.runInContext(`data={sessions:[],today:'2026-11-06',attendance_rules:{enabled:true}};showTime();`,context);
  let html=element('dialog-content').innerHTML;
  assert.doesNotMatch(html,/data-default-lunch="true"/);
  assert.match(html,/추가 휴게만/);
  assert.match(html,/name="overtime"/);
  vm.runInContext(`data.sessions=[{id:'fake',start:'2026-11-06T08:00:00+09:00',end:'2026-11-06T18:00:00+09:00',breaks:[],overtime:true}];showTime('fake');`,context);
  html=element('dialog-content').innerHTML;
  assert.match(html,/<option value="true" selected/);
});

test('겹친 기록을 안내하고 자기 자신과 맞닿은 구간은 제외한다', () => {
  const {context} = application();
  vm.runInContext(`data={sessions:[
    {id:'a',start:'2026-10-27T10:00:00+09:00',end:'2026-10-27T17:00:00+09:00'},
    {id:'b',start:'2026-10-27T18:00:00+09:00',end:'2026-10-27T19:00:00+09:00'}
  ]};`, context);
  assert.equal(vm.runInContext("manualOverlaps('2026-10-27T09:00','2026-10-27T18:00').length", context), 1);
  assert.equal(vm.runInContext("manualOverlaps('2026-10-27T09:00','2026-10-27T18:00','a').length", context), 0);
  assert.match(vm.runInContext("manualTimeSummary('2026-10-27T09:00','2026-10-27T18:00')", context), /기존 기록 1건.*대체/);
});

test('보관된 근무 이력을 새로운 수동 입력으로 불러온다', () => {
  const {context, element} = application();
  vm.runInContext(`data={sessions:[],attendance_history:[{
    id:'replaced:a',original_id:'a',start:'2026-10-27T00:00:00+00:00',
    end:'2026-10-27T09:00:00+00:00',breaks:[],at:'2026-10-27T11:00:00+00:00',
    reason:'가상 정정',kind:'replaced'
  }]};showAttendanceHistory();`, context);
  assert.match(element('dialog-content').innerHTML, /이 기록으로 다시 입력/);
  vm.runInContext("showTime('',data.attendance_history[0]);", context);
  assert.match(element('dialog-content').innerHTML, /data-form="time" data-id=""/);
  assert.match(element('dialog-content').innerHTML, /value="2026-10-27T09:00"/);
  assert.doesNotMatch(element('dialog-content').innerHTML, /data-default-lunch/);
});

test('기본 점심 휴게 날짜를 출근 날짜에 맞추고 직접 수정한 휴게는 보존한다', () => {
  const {context} = application();
  const start = {value:'2026-10-26T09:00'};
  const end = {value:''};
  const breakStart = {value:'2026-10-27T12:00'};
  const breakEnd = {value:'2026-10-27T13:00'};
  const line = {dataset:{defaultLunch:'true'}, querySelector:selector=>selector==='[name="start"]'?breakStart:breakEnd};
  context.form = {
    elements:{namedItem:name=>name==='session_start'?start:end},
    querySelectorAll:()=>line.dataset.defaultLunch==='true'?[line]:[],
  };
  vm.runInContext('syncDefaultLunch(form)', context);
  assert.equal(breakStart.value,'2026-10-26T12:00');
  assert.equal(breakEnd.value,'2026-10-26T13:00');
  delete line.dataset.defaultLunch;
  breakStart.value='2026-10-26T12:15';
  start.value='2026-10-25T09:00';
  vm.runInContext('syncDefaultLunch(form)', context);
  assert.equal(breakStart.value,'2026-10-26T12:15');
});
