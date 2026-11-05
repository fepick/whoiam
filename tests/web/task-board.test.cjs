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
  assert.match(html, /진행도 0%/);
  assert.match(html, /예상 미입력/);
  vm.runInContext("state.taskMode='list'", context);
  html = vm.runInContext('tasksView()', context);
  assert.match(html, /Board/);
  assert.doesNotMatch(html, /Firmware|kanban-card/);
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
