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
    URLSearchParams, setInterval() {},
    fetch: () => new Promise(() => {}),
  });
  vm.runInContext(fs.readFileSync(path.join(__dirname, '../../apps/web/app.js'), 'utf8'), context);
  return {context, element};
}

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
  vm.runInContext('data = {sessions: []}; showTime();', context);
  const html = element('dialog-content').innerHTML;
  assert.match(html, /name="session_start"/);
  assert.match(html, /name="session_end"/);
  assert.match(html, /퇴근 예정 시각은 저장할 수 없습니다/);
  assert.match(html, /24시간제/);
  const summary = vm.runInContext("manualTimeSummary('2026-10-27T09:00', '2026-10-27T18:00')", context);
  assert.match(summary, /09:00.*18:00/);
});
