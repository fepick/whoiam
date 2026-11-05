const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {test} = require('node:test');

function application() {
  const context = vm.createContext({
    document: {addEventListener() {}, getElementById: () => ({addEventListener() {}})},
    window: {addEventListener() {}}, location: {hash: ''},
    URLSearchParams, setInterval() {}, fetch: () => new Promise(() => {}),
  });
  vm.runInContext(fs.readFileSync(path.join(__dirname, '../../apps/web/app.js'), 'utf8'), context);
  vm.runInContext(`data = {tasks: [
    {id:'a', title:'Board', category:'HW', status:'todo', priority:'P1'},
    {id:'b', title:'Firmware', category:'SW', status:'done', priority:'P2'}
  ], logs:[{task_id:'a', title:'Board', minutes:30}, {task_id:'b', title:'Firmware', minutes:60}]};`, context);
  return context;
}

test('리스트 메모는 입력 줄마다 점 목록으로 구분하고 HTML을 이스케이프한다',()=>{
  const context=application();
  context.detail='첫 줄\r\n\n- 둘째 줄\n• 셋째 줄\n<script>fake</script>';
  const html=vm.runInContext('taskRow({...data.tasks[0],detail})',context);
  assert.match(html,/<ul class="task-detail-lines"><li>첫 줄<\/li><li>둘째 줄<\/li><li>셋째 줄<\/li><li>&lt;script&gt;fake&lt;\/script&gt;<\/li><\/ul>/);
  assert.doesNotMatch(html,/<script>/);
  assert.equal(vm.runInContext("taskDetailLines('  \\n ')",context),'');
});

test('분류 필터는 두 보기와 기록 합계에 적용된다', () => {
  const context = application();
  vm.runInContext("state.taskCategory='category:HW'; state.taskMode='kanban';", context);
  let html = vm.runInContext('tasksView()', context);
  assert.match(html, /data-task-card="a"/);
  assert.doesNotMatch(html, /data-task-card="b"|Firmware/);
  assert.match(html, /0시간 30분/);
  assert.doesNotMatch(html, /data-task-status|<select[^>]*상태/);
  assert.doesNotMatch(html, /진행도 0%|예상 미입력|kanban-meta/);
  assert.match(html, /data-action="task-detail"/);
  vm.runInContext("state.taskMode='list'", context);
  html = vm.runInContext('tasksView()', context);
  assert.match(html, /Board/);
  assert.doesNotMatch(html, /Firmware|kanban-card/);
});

test('우선순위·예정일·분류·상태를 함께 적용하고 관련 시간 기록만 합산한다',()=>{
  const context=application();
  vm.runInContext(`data.today='2026-11-06';data.tasks[0].due='2026-11-06';data.tasks[1].due='2026-11-07';
    state.taskPriority='P1';state.taskDate='today';state.taskCategory='category:HW';`,context);
  let html=vm.runInContext('tasksView()',context);
  assert.match(html,/Board/);
  assert.doesNotMatch(html,/Firmware/);
  assert.match(html,/0시간 30분/);
  assert.match(html,/name="task-priority"/);
  assert.match(html,/name="task-date"/);
  vm.runInContext("state.taskTab='done'",context);
  html=vm.runInContext('tasksView()',context);
  assert.match(html,/조건에 맞는 업무가 없습니다/);
  vm.runInContext("state.taskTab='all';state.taskMode='kanban'",context);
  html=vm.runInContext('tasksView()',context);
  assert.match(html,/data-task-card="a"/);
  assert.doesNotMatch(html,/data-task-card="b"/);
});

test('예정일 필터는 오늘 이전·미정·기간 양끝과 월~일 주간 경계를 구분한다',()=>{
  const context=application();
  const matches=(due)=>{context.due=due;return vm.runInContext('matchesTaskFilters({due})',context);};
  vm.runInContext("data.today='2027-01-03';state.taskDate='week'",context);
  assert.equal(matches('2026-12-28'),true);
  assert.equal(matches('2027-01-03'),true);
  assert.equal(matches('2026-12-27'),false);
  assert.equal(matches('2027-01-04'),false);
  assert.equal(matches(''),false);
  vm.runInContext("state.taskDate='overdue'",context);
  assert.equal(matches('2027-01-02'),true);
  assert.equal(matches('2027-01-03'),false);
  vm.runInContext("state.taskDate='undated'",context);
  assert.equal(matches(''),true);
  assert.equal(matches('2027-01-03'),false);
  vm.runInContext("state.taskDate='range';state.taskDateFrom='2027-01-02';state.taskDateTo='2027-01-04'",context);
  assert.equal(matches('2027-01-02'),true);
  assert.equal(matches('2027-01-04'),true);
  assert.equal(matches('2027-01-05'),false);
  assert.equal(matches(''),false);
  vm.runInContext("state.taskDateFrom=''",context);
  assert.equal(matches('2026-12-01'),true);
  vm.runInContext("state.taskDateTo=''",context);
  assert.equal(matches('2027-02-01'),true);
});

test('상태 이동은 상태만 저장하고 실패하면 기존 상태를 유지한다', async () => {
  const context = application();
  vm.runInContext("render=()=>{}; toast=()=>{}; run=async (command,payload)=>{globalThis.saved={command,payload};};", context);
  await vm.runInContext("moveTask('a','in_progress')", context);
  assert.equal(JSON.stringify(context.saved), JSON.stringify({command:'tasks.save',payload:{id:'a',status:'in_progress'}}));
  vm.runInContext("run=async()=>{throw new Error('offline');};", context);
  await vm.runInContext("moveTask('a','done')", context);
  assert.equal(vm.runInContext('data.tasks[0].status', context),'todo');
});

test('칸반 보관 버튼은 확인창 없이 보관 상태만 저장한다', async()=>{
  const context=application();
  const html=vm.runInContext("kanbanCard(data.tasks[0])",context);
  assert.match(html,/data-action="archive-task" data-id="a"/);
  assert.doesNotMatch(vm.runInContext("kanbanCard({...data.tasks[0],status:'archived'})",context),/data-action="archive-task"/);
  vm.runInContext("render=()=>{};toast=()=>{};run=async(command,payload)=>{globalThis.saved={command,payload};data.tasks[0].status=payload.status;};",context);
  await vm.runInContext("act('archive-task','a')",context);
  assert.equal(JSON.stringify(context.saved),JSON.stringify({command:'tasks.save',payload:{id:'a',status:'archived'}}));
  vm.runInContext("state.taskMode='kanban'",context);
  assert.doesNotMatch(vm.runInContext('tasksView()',context),/data-task-card="a"/);
});

test('칸반은 제목·분류·우선순위·네 버튼만 표시하고 내용 팝업에서 상세를 보여준다',async()=>{
  const context=application();
  vm.runInContext("Object.assign(data.tasks[0],{detail:'메모 첫 줄\\n<script>fake</script>',due:'2026-11-06',estimated_minutes:120,progress:45})",context);
  const card=vm.runInContext('kanbanCard(data.tasks[0])',context);
  assert.match(card,/Board/);
  assert.match(card,/HW/);
  for(const action of ['archive-task','log-task','edit-task','task-detail']) assert.match(card,new RegExp(`data-action="${action}"`));
  assert.equal((card.match(/<button /g)||[]).length,4);
  assert.doesNotMatch(card,/메모 첫 줄|2026-11-06|120분|45%|오늘 기록/);
  vm.runInContext('showDialog=(title,content)=>{globalThis.preview={title,content};}',context);
  await vm.runInContext("act('task-detail','a')",context);
  assert.equal(context.preview.title,'Board');
  assert.match(context.preview.content,/<li>메모 첫 줄<\/li>/);
  assert.match(context.preview.content,/2026-11-06|120분|45%/);
  assert.match(context.preview.content,/0시간 30분/);
  assert.match(context.preview.content,/&lt;script&gt;fake&lt;\/script&gt;/);
  assert.doesNotMatch(context.preview.content,/<script>/);
});
