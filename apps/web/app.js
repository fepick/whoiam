/* 로컬 API와 연결하는 업무 콘솔. 브라우저 영구 저장소는 사용하지 않는다. */
const paths = {
  home: 'M3 10.5 12 3l9 7.5M5 9v11h5v-6h4v6h5V9',
  tasks: 'M9 5h10v16H5V5h4M9 3h6v4H9zM8 12l2 2 5-5M8 18h8',
  box: 'm3 7 9-4 9 4v10l-9 4-9-4zM3 7l9 4 9-4M12 11v10M7.5 5l9 4',
  records: 'M5 3h10l4 4v14H5zM14 3v5h5M8 12h8M8 16h8',
  settings: 'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8M9.5 3h5l.6 2.5 2.2 1.3 2.5-.7 2.5 4.3-1.8 1.8v2.6l1.8 1.8-2.5 4.3-2.5-.7-2.2 1.3-.6 2.5h-5L8.9 21l-2.2-1.3-2.5.7-2.5-4.3 1.8-1.8v-2.6l-1.8-1.8L4.2 5.6l2.5.7 2.2-1.3z',
  arrow: 'M5 12h14m-5-5 5 5-5 5',
  chevron: 'm9 5 7 7-7 7',
  calendar: 'M4 5h16v16H4zM8 3v4M16 3v4M4 10h16M8 14h2M14 14h2',
  check: 'm5 12 4 4L19 6',
  clock: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18M12 7v5l3 2',
  truck: 'M3 5h11v12H3zM14 9h4l3 4v4h-7M5 17a2 2 0 1 0 4 0 2 2 0 0 0-4 0M15 17a2 2 0 1 0 4 0 2 2 0 0 0-4 0',
  receipt: 'M6 3h12v18l-3-2-3 2-3-2-3 2zM9 8h6M9 12h6',
  chip: 'M6 6h12v12H6zM9 9h6v6H9zM9 3v3M15 3v3M9 18v3M15 18v3M3 9h3M3 15h3M18 9h3M18 15h3',
  report: 'M5 3h10l4 4v14H5zM14 3v5h5M8 12h8M8 16h5',
  plus: 'M12 5v14M5 12h14',
  close: 'm6 6 12 12M6 18 18 6',
  phone: 'M7 2h10v20H7zM10 18h4',
  desktop: 'M3 4h18v13H3zM12 17v4M8 21h8',
  command: 'm8 8 4 4-4 4M15 16h3',
  mic: 'M9 5a3 3 0 0 1 6 0v7a3 3 0 0 1-6 0zM6 10v2a6 6 0 0 0 12 0v-2M12 18v4M9 22h6',
  lock: 'M5 10h14v11H5zM8 10V7a4 4 0 0 1 8 0v3M12 14v3',
  shield: 'm12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6zM8 12l3 3 5-6',
  bell: 'M6 10a6 6 0 0 1 12 0v5l2 3H4l2-3zM10 21h4',
  info: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18M12 11v5M12 7v.2',
  search: 'M10 3a7 7 0 1 0 0 14 7 7 0 0 0 0-14m5 12 6 6',
  flag: 'M5 22V3h13l-3 5 3 5H5',
  folder: 'M3 6h7l2 2h9v12H3z',
};
const icon = (name, cls = '') =>
  `<svg class="${cls}" viewBox="0 0 24 24" aria-hidden="true"><path d="${paths[name] || paths.box}"/></svg>`;
const navItems = [
  ['home', '홈', 'home'],
  ['tasks', '업무', 'tasks'],
  ['materials', '물품', 'box'],
  ['records', '기록', 'records'],
  ['settings', '설정', 'settings']
];
const state = {
  page: 'home',
  materialTab: 'purchases',
  recordTab: 'time',
  taskTab: 'all',
  taskMode: 'list',
  taskCategory: '',
  draggedTask: '',
  compact: false,
  busy: false
};
let data = null;
let connection = {
  locked: true,
  demo: false,
  csrf: '',
  error: ''
};
let currentReport = '';
let reportDirty = false;
let pendingRequest = null;
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;',
  "'": '&#39;'
} [c]));
const duration = minutes => `${Math.floor(minutes / 60)}시간 ${minutes % 60}분`;
const money = amount => `${Number(amount).toLocaleString('ko-KR')}원`;
const labels = {
  todo: '예정',
  in_progress: '진행 중',
  done: '완료',
  archived: '보관',
  ordered: '주문',
  shipping: '배송 중',
  partial: '일부 수령',
  received: '수령 완료',
  cancelled: '취소'
};
const button = (action, label, id = '', style = 'button-outline') =>
  `<button type="button" class="button ${style}" data-action="${action}" data-id="${esc(id)}">${label}</button>`;
const empty = text => `<p class="empty-hint">${esc(text)}</p>`;
const field = (label, name, value = '', type = 'text', extra = '') =>
  type === 'datetime-local' ? dateTimeField(label, name, value, extra) :
  `<label class="entry-field">${label}<input name="${name}" type="${type}" value="${esc(value)}" ${extra}></label>`;
const area = (label, name, value = '', max = 240) =>
  `<label class="entry-field">${label}<textarea name="${name}" rows="3" maxlength="${max}">${esc(value)}</textarea></label>`;
const select = (label, name, options, selected = '') =>
  `<label class="entry-field">${label}<select name="${name}">${options.map(([value, title])=>`<option value="${esc(value)}" ${String(value)===String(selected)?'selected':''}>${esc(title)}</option>`).join('')}</select></label>`;
const priorities = [
  ['P1', 'P1 · 높음'],
  ['P2', 'P2 · 보통'],
  ['P3', 'P3 · 낮음']
];
const itemOptions = () => [
  ['', '재고 연결 안 함'], ...data.items.map(item => [item.id,
    `${item.name} · ${item.quantity}${item.unit}`
  ])
];
const localTime = iso => iso ? new Date(iso).toLocaleString('ko-KR', {
  timeZone: 'Asia/Seoul',
  hour12: false
}) : '진행 중';
const localInput = iso => iso ? new Date(new Date(iso).getTime() + 9 * 3600000).toISOString().slice(
  0, 16) : '';
const zoned = value => value ? `${value}:00+09:00` : '';

function normalizeClock(value) {
  const raw = value.trim();
  if (!raw) return '';
  const match = /^(\d{1,2}):(\d{2})$/.exec(raw) || /^(\d{1,2})(\d{2})$/.exec(raw);
  if (!match || Number(match[1]) > 23 || Number(match[2]) > 59) return null;
  return `${match[1].padStart(2, '0')}:${match[2]}`;
}

function dateTimeField(label, name, value = '', extra = '') {
  const [date = '', time = ''] = String(value || '').split('T');
  const required = /\brequired\b/.test(extra);
  return `<fieldset class="datetime-field" data-required="${required}"><legend>${esc(label)} · 24시간제</legend><input type="hidden" ${name ? `name="${esc(name)}"` : ''} value="${esc(value)}" ${extra}><div class="datetime-parts"><label class="entry-field">날짜<input type="date" data-time-part="date" value="${esc(date)}" aria-label="${esc(label)} 날짜" ${required || time ? 'required' : ''}></label><label class="entry-field">시각<input type="text" data-time-part="clock" value="${esc(time)}" aria-label="${esc(label)} 시각 (24시간제)" inputmode="numeric" placeholder="09:00" maxlength="5" autocomplete="off" ${required || date ? 'required' : ''}></label></div><small>00:00~23:59 · 0900처럼 입력할 수도 있습니다.</small></fieldset>`;
}

function setDateTimeValue(hidden, value) {
  hidden.value = value;
  const group = hidden.closest?.('.datetime-field');
  if (!group) return;
  const [date = '', clock = ''] = value.split('T');
  group.querySelector('[data-time-part="date"]').value = date;
  group.querySelector('[data-time-part="clock"]').value = clock;
}

function updateDateTime(event) {
  if (!event.target.matches('[data-time-part]')) return;
  const group = event.target.closest('.datetime-field');
  const date = group.querySelector('[data-time-part="date"]');
  const clock = group.querySelector('[data-time-part="clock"]');
  const hidden = group.querySelector('input[type="hidden"]');
  const normalized = normalizeClock(clock.value);
  clock.setCustomValidity(normalized === null ? '시각을 00:00~23:59로 입력해주세요.' : '');
  date.required = group.dataset.required === 'true' || Boolean(clock.value);
  clock.required = group.dataset.required === 'true' || Boolean(date.value);
  if (event.type !== 'input' && normalized !== null) clock.value = normalized;
  hidden.value = date.value || clock.value ? `${date.value}T${normalized ?? clock.value}` : '';
  hidden.dispatchEvent(new Event('input', {bubbles: true}));
}
// 보고 편집기의 input 처리보다 먼저 날짜·시각을 하나의 값으로 합친다.
document.addEventListener('input', updateDateTime, true);
document.addEventListener('change', updateDateTime, true);
document.addEventListener('focusout', updateDateTime, true);
window.WhoiamTime = {field: dateTimeField};

async function api(path, body) {
  const options = {
    credentials: 'same-origin',
    cache: 'no-store'
  };
  if (body !== undefined) Object.assign(options, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Whoiam-CSRF': connection.csrf
    },
    body: JSON.stringify(body)
  });
  const response = await fetch(`/api/${path}`, options);
  const result = await response.json().catch(() => ({
    error: '로컬 서버 응답을 확인해주세요.'
  }));
  if (!response.ok) {
    if (response.status === 423 || response.status === 401) {
      connection.locked = true;
      data = null;
      clearPrivateView();
      render();
    }
    throw new Error(result.error || '처리하지 못했습니다.');
  }
  return result;
}

function clearPrivateView() {
  state.draggedTask = '';
  state.taskCategory = '';
  currentReport = '';
  reportDirty = false;
  pendingRequest = null;
  window.WhoiamReport.load({
    date: '',
    daily: [],
    planned: [],
    note: ''
  });
  const dialog = document.getElementById('flow-dialog');
  if (dialog.open) dialog.close();
  document.getElementById('dialog-content').innerHTML = '';
  document.getElementById('report-image-dialog')?.remove();
}
async function refresh(show = true) {
  connection = {
    ...connection,
    ...await api('status'),
    error: ''
  };
  if (connection.locked) {
    data = null;
    clearPrivateView();
  } else data = await api('snapshot');
  if (show) render();
}
async function run(name, payload = {}) {
  if (state.busy) throw new Error('이전 작업을 처리 중입니다.');
  state.busy = true;
  document.body.classList.add('saving');
  const fingerprint = JSON.stringify({
    name,
    data: payload
  });
  if (pendingRequest && pendingRequest.fingerprint !== fingerprint) {
    state.busy = false;
    document.body.classList.remove('saving');
    throw new Error('응답이 확인되지 않은 이전 작업을 같은 입력으로 다시 실행해주세요.');
  }
  const request = pendingRequest?.request || {
    name,
    data: payload,
    request_id: crypto.randomUUID()
  };
  pendingRequest = {
    fingerprint,
    request
  };
  try {
    let result;
    try {
      result = await api('commands', request);
    } catch (error) {
      if (error instanceof TypeError) result = await api('commands', request);
      else {
        pendingRequest = null;
        throw error;
      }
    }
    pendingRequest = null;
    try {
      await refresh(false);
    } catch (error) {
      connection.error = '저장은 완료됐지만 목록을 갱신하지 못했습니다. 다시 연결해주세요.';
      toast(connection.error);
    }
    return result.result;
  } finally {
    state.busy = false;
    document.body.classList.remove('saving');
  }
}

function toast(message) {
  const element = document.getElementById('toast');
  element.textContent = message;
  element.classList.add('show');
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => element.classList.remove('show'), 5000);
}

function header(kicker, title, description, extra = '') {
  return `<div class="page-header"><div><div class="eyebrow">${kicker}</div><h1>${title}</h1><p>${description}</p></div>${extra}</div>`;
}

function navMarkup() {
  return navItems.map(([id, title, glyph], index) =>
    `<button class="nav-item ${state.page===id?'active':''}" data-nav="${id}" ${state.page===id?'aria-current="page"':''}>${icon(glyph)}<span>${title}</span><span class="nav-index">${String(index+1).padStart(2,'0')}</span></button>`
  ).join('');
}

function commandBox() {
  return `<form class="command-box" id="command-form"><span class="command-symbol">${icon('command')}</span><input name="command" required maxlength="100" aria-label="명령" placeholder="출근, 퇴근, 오늘 할 일, 재고, 배송, 보고" autocomplete="off"><button class="icon-button" type="submit" aria-label="명령 실행">${icon('arrow')}</button></form>`;
}

function taskRow(task) {
  return `<div class="task-row ${task.status==='done'?'done':''}"><button class="task-check" data-action="toggle-task" data-id="${esc(task.id)}" aria-label="${esc(task.title)} 완료 전환" aria-pressed="${task.status==='done'}">${task.status==='done'?icon('check'):''}</button><div class="task-content"><div class="task-title">${esc(task.title)}</div><div class="task-detail">${esc(task.detail)}</div><div class="task-meta"><span class="tag priority-tag" data-priority="${esc(task.priority)}">${esc(task.priority)}</span><span>${esc(task.category)}</span><span>${esc(task.due||'예정일 미정')}</span><span>예상 ${task.estimated_minutes == null ? '미입력' : `${esc(task.estimated_minutes)}분`}</span><span>진행도 ${esc(task.progress ?? (task.status==='done'?100:0))}%</span></div></div><div class="row-actions">${button('log-task','시간 기록',task.id)}${button('edit-task','수정',task.id)}</div></div>`;
}

function weeklyCard() {
  const a = data.attendance;
  return `<section class="card weekly-card"><div class="card-heading"><h2>이번 주 근무</h2><span class="subtle-label">${esc(a.week_start)}부터</span></div><div class="hours">${Math.floor(a.week_minutes/60)}<small class="time-unit">시간</small>${a.week_minutes%60}<small>분</small></div><div class="hours-limit">알림 기준 ${duration(a.limit_minutes)}${a.provisional?' · 근무 중 잠정 합계':''}</div><div class="progress-track"><span style="width:${Math.min(100,a.week_minutes/a.limit_minutes*100)}%"></span></div><p class="weekly-note">${icon('shield')}${a.over_limit?'설정한 기준을 넘었습니다. 기록을 확인해주세요.':`남은 기준 시간 ${duration(a.remaining_minutes)}`}</p></section>`;
}

function alertList() {
  return data.alerts.length ? data.alerts.map(alert =>
    `<button class="notice-item notice-button" data-action="navigate-target" data-id="${esc(alert.target)}"><span class="notice-dot amber"></span><div><strong>${esc(alert.title)}</strong><p>${esc(alert.detail)}</p></div>${icon('chevron')}</button>`
  ).join('') : empty('현재 확인할 항목이 없습니다.');
}

function homeView() {
  const a = data.attendance;
  const active = a.active;
  const resting = active?.breaks.at(-1)?.end === null;
  return `${header('YOUR DAILY FLOW','오늘도, 차곡차곡.','일과 물품, 기록을 한 흐름으로 연결하세요.',`<span class="date-chip">${icon('calendar')}${esc(data.today)}</span>`)}<div class="home-layout"><section class="day-panel"><div class="day-panel-top"><span class="eyebrow">${active?'WORK IN PROGRESS':'A FRESH START'}</span><span class="state-pill"><span class="node-dot"></span>${active?(resting?'휴게 중':'근무 중'):'업무 시작 전'}</span></div><div><h2>${active?'지금의 일을<br><em>차곡차곡 기록하세요.</em>':'오늘의 일을<br><em>가볍게 시작하세요.</em>'}</h2><p class="day-panel-caption">${active?`${esc(localTime(active.start))} 출근`:'출근을 기록하고 오늘 챙길 일을 확인하세요.'}</p></div><div class="day-panel-actions">${button(active?'finish':'start',active?'퇴근하기':'출근하기','','button-lime')}${active?button(resting?'break-end':'break-start',resting?'업무 재개':'휴게 시작','','button-quiet'):''}</div></section>${weeklyCard()}<section class="card today-tasks"><div class="card-heading"><h2>오늘의 할 일 <span class="counter">${data.today_tasks.length}</span></h2>${button('new-task','업무 추가')}</div>${data.today_tasks.length?data.today_tasks.map(taskRow).join(''):empty('오늘 예정된 미완료 업무가 없습니다.')}</section><section class="card attention-card"><div class="card-heading"><h2>한번 확인해주세요 <span class="counter">${data.alerts.length}</span></h2>${icon('bell')}</div>${alertList()}</section></div>${commandBox()}`;
}

function tasksView() {
  const tasks = data.tasks.filter(task => matchesCategory(task) && (state.taskTab === 'all' ? task.status !== 'archived' :
    state.taskTab === 'archived' ? task.status === 'archived' : state.taskTab === 'done' ? task
    .status === 'done' : !['done', 'archived'].includes(task
      .status)));
  const categories = [...new Set(data.tasks.map(task => task.category || ''))];
  if (state.taskCategory && !categories.includes(state.taskCategory.slice(9))) categories.push(state.taskCategory.slice(9));
  categories.sort((a, b) => a.localeCompare(b, 'ko'));
  const logs = data.logs.filter(log => !state.taskCategory || matchesCategory(data.tasks.find(task => task.id === log.task_id)));
  return `${header('TASKS & PLANS','업무와 소요시간','상태를 옮겨 진행을 정리하고, 실제 소요시간을 기록하세요.')}
    <div class="toolbar task-toolbar"><div class="tabs" aria-label="업무 상태 필터">${[['all','전체'],['todo','진행'],['done','완료'],['archived','보관']].map(([id,label])=>`<button data-task-tab="${id}" class="${state.taskTab===id?'active':''}" aria-pressed="${state.taskTab===id}">${label}</button>`).join('')}</div>${button('new-task','＋ 업무 추가','','button-primary')}</div>
    <div class="toolbar task-controls">${select('분류','task-category',[['','모든 분류'],...categories.map(category=>[`category:${category}`,category||'미분류'])],state.taskCategory)}<div class="tabs view-tabs" aria-label="업무 보기 모드">${[['list','리스트'],['kanban','칸반']].map(([mode,title])=>`<button data-task-mode="${mode}" class="${state.taskMode===mode?'active':''}" aria-pressed="${state.taskMode===mode}">${title}</button>`).join('')}</div><span class="subtle-label">${tasks.length}개 업무</span></div>
    ${state.taskMode==='kanban'?kanbanBoard(tasks):`<section class="card wide-card">${tasks.length?tasks.map(taskRow).join(''):empty('조건에 맞는 업무가 없습니다.')}</section>`}
    <section class="card wide-card"><div class="card-heading"><h2>오늘 입력한 업무 기록${state.taskCategory?' · 선택한 분류':''}</h2><span>${duration(logs.reduce((sum,row)=>sum+row.minutes,0))}</span></div>${logs.length?logs.map(log=>`<div class="timeline-item"><span>${log.minutes}분</span><div><strong>${esc(log.title)}</strong><small>${esc(log.note)}</small></div>${button('edit-log','정정',log.id)}</div>`).join(''):empty('조건에 맞는 시간 기록이 없습니다.')}</section>${commandBox()}`;
}

function matchesCategory(task) {
  return !state.taskCategory || Boolean(task && `category:${task.category || ''}` === state.taskCategory);
}

function kanbanCard(task) {
  const minutes = data.logs.filter(log => log.task_id === task.id).reduce((sum, log) => sum + log.minutes, 0);
  return `<article class="kanban-card" data-priority="${esc(task.priority)}" draggable="true" data-task-card="${esc(task.id)}" aria-label="${esc(task.title)}">
    <div class="kanban-card-top"><span class="tag priority-tag" data-priority="${esc(task.priority)}">${esc(task.priority)}</span><span>${esc(task.category || '미분류')}</span><span class="drag-hint" aria-hidden="true">⠿</span></div>
    <h3>${esc(task.title)}</h3><p class="task-detail">${esc(task.detail)}</p>
    <div class="kanban-card-body"><div class="kanban-meta"><span>예정일 ${esc(task.due || '미정')}</span><span>예상 ${task.estimated_minutes == null ? '미입력' : `${esc(task.estimated_minutes)}분`}</span><span>진행도 ${esc(task.progress ?? (task.status==='done'?100:0))}%</span><strong>오늘 기록 ${duration(minutes)}</strong></div>
    <div class="kanban-actions">${button('log-task','시간 기록',task.id)}${button('edit-task','수정',task.id)}</div></div></article>`;
}

function kanbanBoard(tasks) {
  const statuses = state.taskTab === 'archived' ? ['todo','in_progress','done','archived'] : ['todo','in_progress','done'];
  return `<p class="subtle-label">카드를 다른 열로 드래그해 이동하세요. 터치·키보드에서는 수정 버튼을 사용하세요. 소요시간은 별도로 기록합니다.</p><div class="kanban-board" aria-label="업무 칸반 보드">${statuses.map(status=>{
    const cards = tasks.filter(task=>task.status===status);
    return `<section class="kanban-column" data-drop-status="${status}" aria-label="${labels[status]}"><div class="kanban-heading"><h2>${labels[status]}</h2><span class="counter">${cards.length}</span></div><div class="kanban-cards">${cards.map(kanbanCard).join('')||'<p class="kanban-empty">이곳으로 업무를 옮기세요</p>'}</div></section>`;
  }).join('')}</div>`;
}

async function moveTask(id, status) {
  const task = data?.tasks.find(task => task.id === id);
  if (!task || !['todo','in_progress','done','archived'].includes(status) || task.status === status) return;
  try {
    await run('tasks.save', {id, status});
    render();
    toast(`${labels[status]} 상태로 저장했습니다.`);
  } catch (error) {
    render();
    toast(error.message || '상태를 저장하지 못했습니다. 다시 시도해주세요.');
  }
}

document.addEventListener('dragstart', event => {
  const card = event.target.closest('[data-task-card]');
  if (!card) return;
  if (state.busy || event.target.closest('button,select,input,a')) { event.preventDefault(); return; }
  state.draggedTask = card.dataset.taskCard;
  event.dataTransfer.setData('text/plain', state.draggedTask);
  event.dataTransfer.effectAllowed = 'move';
  card.classList.add('dragging');
});
document.addEventListener('dragover', event => {
  const column = event.target.closest('[data-drop-status]');
  if (!column || !state.draggedTask || state.busy) return;
  event.preventDefault();
  event.dataTransfer.dropEffect = 'move';
  document.querySelectorAll('.kanban-column.drop-target').forEach(node => node.classList.remove('drop-target'));
  column.classList.add('drop-target');
});
function clearTaskDrag() {
  state.draggedTask = '';
  document.querySelectorAll('.dragging,.drop-target').forEach(node => node.classList.remove('dragging','drop-target'));
}
document.addEventListener('dragend', clearTaskDrag);
document.addEventListener('drop', event => {
  const column = event.target.closest('[data-drop-status]');
  if (!column || !state.draggedTask) return;
  event.preventDefault();
  const id = state.draggedTask;
  clearTaskDrag();
  void moveTask(id, column.dataset.dropStatus);
});

function purchasesView() {
  return `<div class="material-stats"><section class="card stat-card"><span>진행 중인 주문</span><div class="stat-number">${data.orders.filter(o=>!['received','cancelled'].includes(o.status)).length}<small>건</small></div></section><section class="card stat-card"><span>예정일 확인</span><div class="stat-number">${data.orders.filter(o=>!['received','cancelled'].includes(o.status)&&o.eta&&o.eta<=data.today).length}<small>건</small></div></section><section class="card stat-card"><span>증빙 수집 대기</span><div class="stat-number">${data.orders.filter(o=>o.status!=='cancelled'&&(!o.statement_ref||!o.receipt_ref)).length}<small>건</small></div></section></div><section class="card wide-card"><div class="card-heading"><h2>구매 내역</h2><span class="subtle-label">판매처 결제 후 수동 등록</span></div><div class="table-wrap"><table class="data-table"><thead><tr><th>물품 · 메모</th><th>판매처 · 금액</th><th>도착 예정</th><th>상태</th><th></th></tr></thead><tbody>${data.orders.map(order=>`<tr><td><strong>${esc(order.lines.map(line=>line.name).join(', '))}</strong><div class="task-detail">${esc(order.memo)}</div></td><td>${esc(order.supplier)}<div class="task-detail">${money(order.amount)}</div></td><td>${esc(order.eta||'미정')}</td><td><span class="table-status ${order.status==='received'?'green':'amber'}">${esc(labels[order.status])}</span><div class="task-detail">명세서 ${order.statement_ref?'✓':'대기'} · 전표 ${order.receipt_ref?'✓':'대기'}</div></td><td>${button('order-detail','상세',order.id)}</td></tr>`).join('')}</tbody></table></div>${!data.orders.length?empty('구매한 물품을 등록해 배송과 증빙을 관리하세요.'):''}</section>`;
}

function stockView() {
  return `<div class="toolbar">${button('new-item','＋ 품목 등록')}${button('move-stock','입출고 기록')}${button('new-bom','BOM 버전 등록')}${button('assemble','BOM 조립','','button-primary')}</div><section class="card wide-card"><div class="card-heading"><h2>재고</h2><span>${data.items.length}종</span></div><div class="table-wrap"><table class="data-table"><thead><tr><th>품목 · 품번</th><th>남은 수량</th><th>보관 위치</th><th>최소 수량</th><th></th></tr></thead><tbody>${data.items.map(item=>`<tr><td><strong>${esc(item.name)}</strong><div class="task-detail">${esc(item.part_number)} · ${esc(item.note)}</div></td><td><span class="table-status ${item.quantity<item.minimum?'amber':'green'}">${item.quantity} ${esc(item.unit)}</span></td><td>${esc(item.location||'미지정')}</td><td>${item.minimum}</td><td>${button('edit-item','수정',item.id)} ${button('adjust-stock','실사',item.id)}</td></tr>`).join('')}</tbody></table></div>${!data.items.length?empty('품목을 등록한 뒤 입고 수량을 기록하세요.'):''}</section><section class="card wide-card"><div class="card-heading"><h2>최근 입출고</h2><span>원장 기준</span></div>${data.inventory.movements.slice(-12).reverse().map(move=>`<div class="timeline-item"><span>${move.delta>0?'+':''}${move.delta}</span><div><strong>${esc(data.items.find(i=>i.id===move.item_id)?.name||'품목')}</strong><small>${esc(move.reason)} · ${esc(localTime(move.at))}</small></div></div>`).join('')||empty('입출고 기록이 없습니다.')}</section><section class="card wide-card"><div class="card-heading"><h2>조립 이력</h2></div>${data.inventory.assemblies.slice(-8).reverse().map(row=>`<div class="timeline-item"><span>${row.quantity}대</span><div><strong>${esc(row.bom.name)} · ${esc(row.bom.version)}</strong><small>${esc(row.note)} · ${esc(localTime(row.at))}</small></div></div>`).join('')||empty('BOM 조립 이력이 없습니다.')}</section>`;
}

function materialsView() {
  return `${header('PURCHASES & INVENTORY','물품 관리','구매부터 사용까지, 물품의 흐름을 기록하세요.')}<div class="toolbar"><div class="tabs"><button data-material="purchases" class="${state.materialTab==='purchases'?'active':''}">구매</button><button data-material="stock" class="${state.materialTab==='stock'?'active':''}">재고</button></div>${state.materialTab==='purchases'?button('new-order','＋ 구매 등록','','button-primary'):''}</div>${state.materialTab==='stock'?stockView():purchasesView()}`;
}

function timeView() {
  const a = data.attendance;
  return `<div class="records-grid">${weeklyCard()}<section class="card"><div class="card-heading"><h2>오늘의 근무</h2><span>${duration(a.today_minutes)}</span></div><div class="week-bars">${a.daily.map((row,index)=>`<div class="week-bar ${row.date===data.today?'current':''}"><span class="bar-label">${(row.minutes/60).toFixed(1)}h</span><div class="bar" style="height:${Math.min(100,row.minutes/720*100)}%"></div></div>`).join('')}</div><div class="week-days">${['월','화','수','목','금','토','일'].map(label=>`<span>${label}</span>`).join('')}</div><div class="row-actions">${button('manual-time','근무 수동 입력')}${button('attendance-history','변경 이력')}${button('payroll','급여 대조')}</div></section></div><section class="card wide-card"><div class="card-heading"><h2>출퇴근 기록</h2><span class="subtle-label">휴게는 명시적으로 입력한 구간만 차감</span></div>${data.sessions.map(session=>`<div class="timeline-item"><div><strong>${esc(localTime(session.start))} → ${session.end?esc(localTime(session.end)):'근무 중'}</strong><small>${session.source==='manual'||session.corrections.length?'수동 입력':'출퇴근 기록'} · 휴게 ${session.breaks.length}구간 · 정정 ${session.corrections.length}회</small></div>${button('correct-time','정정',session.id)}</div>`).join('')||empty('출근을 기록하면 이곳에 표시됩니다.')}</section><section class="card wide-card"><div class="card-heading"><h2>급여 입금 대조</h2>${button('payroll','월별 입력')}</div>${data.payroll.map(row=>`<div class="timeline-item"><span>${esc(row.month)}</span><div><strong>예상 ${money(row.expected_net)} / 입금 ${row.received_net===null?'미확인':money(row.received_net)}</strong><small>${row.difference===null?'입금 확인 대기':`차이 ${money(row.difference)}`} · ${esc(row.note)}</small></div>${button('payroll','수정',row.month)}</div>`).join('')||empty('예상 실수령액과 실제 입금액을 직접 입력해 비교하세요.')}</section>`;
}

function reportView() {
  if (!currentReport && !reportDirty) {
    const report = data.reports.find(r => r.date === data.today);
    window.WhoiamReport.load(report || {
      date: data.today,
      daily: [],
      planned: [],
      note: ''
    });
    currentReport = report?.id || '';
  }
  return `<div class="toolbar"><div class="row-actions">${select('저장된 보고서','saved-report',[['','새 보고서'],...data.reports.map(r=>[r.id,r.date])],currentReport)}${button('generate-report','업무 로그로 초안 생성')}</div>${button('save-report','보고서 저장','','button-primary')}</div>${window.WhoiamReport.render()}`;
}

function recordsView() {
  return `${header('TIME & DAILY LOG','나의 기록','근무시간과 직접 기록한 업무 소요시간을 구분합니다.')}<div class="toolbar"><div class="tabs">${[['time','근무'],['report','일일 보고']].map(([id,label])=>`<button data-record="${id}" class="${state.recordTab===id?'active':''}">${label}</button>`).join('')}</div></div>${state.recordTab==='time'?timeView():reportView()}`;
}

function settingsView() {
  return `${header('PREFERENCES','작업 공간 설정','근무 기준과 로컬 보관함을 관리하세요.')}<div class="settings-grid"><section class="card"><div class="card-heading"><h2>기본 설정</h2></div><form data-form="settings">${field('주간 근무 알림 기준 (시간)','weekly_hours',data.settings.weekly_limit/60,'number','min="1" max="168" step="0.5" required')}${select('화면 알림','notifications',[['true','켜짐'],['false','꺼짐']],String(data.settings.notifications))}<p class="subtle-label">시간대 Asia/Seoul · 월요일부터 일요일까지 합산</p><button class="button button-primary" type="submit">설정 저장</button></form></section><section class="card vault-card"><span class="vault-icon">${icon('lock')}</span><span class="eyebrow">LOCAL & ENCRYPTED</span><h2>민감정보 보관함</h2><p>${connection.demo?'가상 데이터 · 서버 종료 시 삭제':'OS 키 저장소와 분리된 인증 암호화 저장'}</p><div class="row-actions">${button('new-secret','정보 등록')}${button('lock','작업 공간 잠금')}</div></section></div><section class="card wide-card"><div class="card-heading"><h2>보관함 목록</h2><span class="subtle-label">원문 조회는 제공하지 않습니다</span></div>${data.vault.map(entry=>`<div class="timeline-item"><div><strong>${esc(entry.alias)}</strong><small>${esc(entry.kind)} · ${esc(entry.hint)}</small></div>${button('delete-secret','삭제',entry.id)}</div>`).join('')||empty('저장된 민감정보가 없습니다.')}</section>${personalSettings()}`;
}

function personalSettings() {
  const backup = connection.backup || {};
  const profileLabel = {
    production: '운영',
    development: '개발',
    test: '테스트',
    demo: '임시 데모'
  } [connection.profile] || '로컬';
  return `<section class="card wide-card"><div class="card-heading"><h2>개인 실사용 관리</h2><span class="tag">${profileLabel} 프로필</span></div><p class="subtle-label">${connection.demo?'임시 데모에서는 운영 파일과 키를 사용하지 않습니다.':'운영 데이터와 OS 키는 실행 프로필별로 분리됩니다.'}</p><div class="setting-row"><div><strong>암호화 백업</strong><p>${backup.error?'최근 백업에 실패했습니다. 저장 공간과 폴더 권한을 확인해주세요.':backup.last_created?`최근 백업 ${esc(localTime(backup.last_created))}`:'저장소를 해제하면 최초 백업을 만듭니다.'}</p></div><span>변경 후 최대 약 5분</span></div><p class="subtle-label">잠금·종료 전 변경분도 백업합니다. 최근 자동 백업 30개를 보관하며 수동·복원 전 백업은 자동 삭제하지 않습니다.</p><div class="row-actions">${backup.available?button('backup-now','지금 백업')+button('backup-list','백업·복원'):''}${!connection.demo&&['production','development'].includes(connection.profile)?button('startup-settings','로그인 자동 실행'):''}${button('shutdown','앱 종료')}</div><p class="subtle-label" style="margin-top:16px">다른 PC에서 복구하려면 별도 복구 파일과 복구 암호도 필요합니다. 복구 파일은 앱을 종료한 뒤 관리 CLI로 생성합니다.</p></section>`;
}
let backupRevision = 0;
async function personalAction(action, id) {
  if (action === 'backup-now') {
    await api('backups', {});
    await refresh();
    toast('암호화 백업을 만들고 검증했습니다.');
    return true;
  }
  if (action === 'backup-list') {
    const result = await api('backups');
    backupRevision = result.revision;
    showDialog('암호화 백업·복원',
      `<p>복원 전 현재 데이터를 안전 백업으로 남깁니다. 다른 저장소·프로필의 백업은 복원하지 않습니다.</p>${result.backups.map(row=>`<div class="receipt-line"><strong>${esc(localTime(row.created_at))}</strong><p>${row.reason==='automatic'?'자동 백업':row.reason==='before-restore'?'복원 전 안전 백업':'수동 백업'} · ${(row.size/1024/1024).toFixed(2)}MB</p>${button('restore-backup','이 시점으로 복원',row.id)} <a class="button button-outline" href="/api/backups/${esc(row.id)}" download>암호화 백업 파일 저장</a></div>`).join('')||empty('백업이 없습니다.')}${button('close','닫기')}`
    );
    return true;
  }
  if (action === 'restore-backup') {
    if (!confirm('현재 업무 데이터를 선택한 시점으로 되돌릴까요? 현재 데이터는 안전 백업으로 보존합니다.')) return true;
    await api('backups/restore', {
      id,
      revision: backupRevision,
      confirmation: 'restore'
    });
    clearPrivateView();
    await refresh();
    toast('복원을 완료했습니다. 현재 데이터는 복원 전 안전 백업에서 되돌릴 수 있습니다.');
    return true;
  }
  if (action === 'startup-settings') {
    const result = await api('autostart');
    showDialog('로그인 자동 실행',
      `<p>현재 사용자로 Windows에 로그인하면 이 프로필의 앱을 실행합니다. 관리자 권한이나 로그인 암호를 저장하지 않습니다.</p><p>현재 상태: <strong>${result.enabled?'켜짐':'꺼짐'}</strong></p>${button(result.enabled?'disable-startup':'enable-startup',result.enabled?'자동 실행 끄기':'자동 실행 켜기','','button-primary')}${button('close','닫기')}`
    );
    return true;
  }
  if (action === 'enable-startup' || action === 'disable-startup') {
    await api('autostart', {
      enabled: action === 'enable-startup'
    });
    closeDialog();
    toast('로그인 자동 실행 설정을 저장했습니다.');
    return true;
  }
  if (action === 'shutdown') {
    if (!confirm('저장한 변경분을 백업하고 앱을 종료할까요? 저장하지 않은 보고 편집 내용은 사라집니다.')) return true;
    await api('shutdown', {});
    clearPrivateView();
    connection.locked = true;
    data = null;
    connection.error = '앱을 종료했습니다. 다시 사용하려면 실행 명령 또는 로그인 자동 실행을 이용해주세요.';
    render();
    return true;
  }
  return false;
}

function render() {
  document.getElementById('desktop-nav').innerHTML = navMarkup();
  document.getElementById('mobile-nav').innerHTML = navMarkup();
  document.getElementById('breadcrumb-current').textContent = navItems.find(row => row[0] === state
    .page)[1];
  document.getElementById('view-toggle').innerHTML = icon(state.compact ? 'desktop' : 'phone');
  document.querySelector('.workspace-footer').innerHTML =
    `<span><span class="tiny-dot"></span>${connection.demo?'임시 데모 · 가상 데이터만 사용하세요':connection.locked?'로컬 작업 공간 · 잠김':'로컬 암호화 저장 · 외부 전송 없음'}</span><span>whoiam · v0.03</span>`;
  document.querySelector('.device-status').innerHTML =
    `<span class="node-dot"></span>${esc({production:'운영',development:'개발',test:'테스트',demo:'임시 데모'}[connection.profile] || (connection.demo?'임시 데모':'로컬 장치'))}`;
  const main = document.getElementById('main-content');
  if (connection.error) main.innerHTML =
    `${header('LOCAL WORKSPACE','로컬 서버에 연결해주세요.','실제 기능은 Python 로컬 서버에서 실행됩니다.')}<section class="card wide-card"><p>${esc(connection.error)}</p><pre>python -m apps.server --demo=True</pre><p>가상 데이터로 기능을 확인하거나, 데모 옵션 없이 실행해 OS 보안 저장소를 연결할 수 있습니다.</p>${button('retry','다시 연결')}</section>`;
  else if (connection.locked || !data) main.innerHTML =
    `${header('LOCAL & PRIVATE','작업 공간이 잠겨 있습니다.','현재 OS 계정의 보안 키 저장소로 잠금을 해제합니다.')}<section class="card wide-card"><p>잠금을 해제하면 로컬 업무 기록을 사용할 수 있습니다.</p>${button('unlock','잠금 해제','','button-primary')}</section>`;
  else {
    const views = {
      home: homeView,
      tasks: tasksView,
      materials: materialsView,
      records: recordsView,
      settings: settingsView
    };
    main.innerHTML = views[state.page]();
    if (state.page === 'records' && state.recordTab === 'report') window.WhoiamReport.mount();
  }
  document.title = `${navItems.find(row=>row[0]===state.page)[1]} · WHOIAM 업무 콘솔`;
}

function navigate(page) {
  state.page = navItems.some(row => row[0] === page) ? page : 'home';
  location.hash = state.page;
  render();
  window.scrollTo({
    top: 0,
    behavior: 'instant'
  });
}

function navigateTarget(target) {
  if (target === 'stock' || target === 'purchases') {
    state.materialTab = target;
    navigate('materials');
  } else if (target === 'report' || target === 'time') {
    state.recordTab = target;
    navigate('records');
  } else navigate(target);
}

function closeDialog() {
  const d = document.getElementById('flow-dialog');
  if (d.open) d.close();
  document.getElementById('dialog-content').innerHTML = '';
}

function showDialog(title, content, form = '', id = '') {
  document.getElementById('dialog-content').innerHTML =
    `<div class="dialog-header"><h2 id="dialog-title">${esc(title)}</h2><button type="button" class="icon-button" data-action="close" aria-label="닫기">${icon('close')}</button></div><div class="dialog-content">${form?`<form data-form="${form}" data-id="${esc(id)}">${content}<p class="form-error" role="alert"></p><div class="dialog-actions">${button('close','취소')}<button type="submit" class="button button-primary">저장</button></div></form>`:content}</div>`;
  const dialog = document.getElementById('flow-dialog');
  if (!dialog.open) dialog.showModal();
}

function purchaseLine() {
  return `<fieldset class="purchase-line"><legend>주문 품목</legend>${select('재고 품목 연결','item_id',itemOptions())}${field('판매처 상품명','name','','text','required maxlength="100"')}${field('주문 수량 (포장 단위)','quantity',1,'number','required min="1" step="1"')}${field('포장당 재고 수량','units_per_pack',1,'number','required min="1" step="1"')}${button('remove-line','이 품목 제거')}</fieldset>`;
}

function bomLine() {
  return `<fieldset class="bom-line">${select('소자','item_id',data.items.map(item=>[item.id,item.name]))}${field('보드당 소모 수량','quantity',1,'number','required min="1" step="1"')}${button('remove-line','소자 제거')}</fieldset>`;
}

function taskEstimateFields(task) {
  return `${field('예상 소요시간 (분)','estimated_minutes',task.estimated_minutes ?? '', 'number','min="0" max="525600" step="1" placeholder="미입력"')}${field('진행도 (%)','progress',task.progress ?? (task.status==='done'?100:0),'number','required min="0" max="100" step="1"')}<p class="subtle-label">예상시간과 진행도는 직접 입력한 값이며, 상태 이동이나 시간 기록으로 자동 계산하지 않습니다.</p>`;
}

function showTask(id = '') {
  const t = data.tasks.find(t => t.id === id) || {
    priority: 'P2',
    status: 'todo',
    due: data.today
  };
  showDialog(id ? '업무 수정' : '업무 추가',
    `${field('업무명','title',t.title,'text','required maxlength="64"')}${area('메모','detail',t.detail)}${field('분류','category',t.category,'text','maxlength="32"')}${select('우선순위','priority',priorities,t.priority)}${field('예정일','due',t.due,'date')}${taskEstimateFields(t)}${select('상태','status',Object.entries(labels).filter(([key])=>['todo','in_progress','done','archived'].includes(key)),t.status)}`,
    'task', id);
}

function showOrder(id) {
  const order = data.orders.find(o => o.id === id);
  showDialog('구매 상세',
    `<p><strong>${esc(order.supplier)}</strong> · ${esc(order.order_number)} · ${money(order.amount)}</p><form data-form="order-update" data-id="${esc(id)}">${field('도착 예정일','eta',order.eta,'date')}${area('사용 목적 · 메모','memo',order.memo)}${!order.lines.some(l=>l.received)?select('처리 상태','status',[['ordered','주문'],['shipping','배송 중'],['cancelled','취소']],order.status):''}<button class="button button-primary" type="submit">배송·메모 저장</button></form><h3>분할 수령</h3>${order.lines.map(line=>`<div class="receipt-line"><strong>${esc(line.name)}</strong><p>주문 ${line.quantity} / 수령 ${line.received} · 포장당 ${line.units_per_pack}${line.item_id?'개 입고':' · 재고 연결 없음'}</p>${order.status!=='cancelled'&&line.received<line.quantity?`<form data-form="receive" data-id="${esc(id)}" data-line="${esc(line.id)}">${field('이번에 받은 포장 수량','quantity',line.quantity-line.received,'number',`min="1" max="${line.quantity-line.received}" step="1" required`)}<button class="button button-primary" type="submit">수령·입고</button></form>`:''}</div>`).join('')}<h3>구매 증빙</h3>${[['statement','거래명세서','statement_ref'],['card-receipt','카드매출전표','receipt_ref']].map(([kind,title,key])=>`<label class="entry-field">${title}${order[key]?`<a href="/api/documents/${esc(order[key])}">저장된 파일 다운로드</a>`:'수집 대기'}<input type="file" accept="application/pdf,image/png,image/jpeg" data-upload="${kind}" data-order="${esc(id)}"></label>`).join('')}<p class="subtle-label">PDF·PNG·JPEG, 파일당 5MB 이하 · 암호화 저장</p><p class="form-error" role="alert"></p>${button('close','닫기')}`
  );
}

function showTime(id = '', version = null) {
  const session = version || data.sessions.find(s => s.id === id);
  const breaks = session ? session.breaks : [defaultLunch(data.today)];
  showDialog(version ? '이력으로 근무 다시 입력' : id ? '근무 기록 정정' : '근무 수동 입력',
    `<p class="subtle-label">수동 입력이 우선합니다. 겹치는 기존 근무 기록 전체는 이력으로 보관하고 지금 입력한 근무·휴게로 대체합니다. 기본 휴게는 12:00~13:00이며 출퇴근에 걸쳐도 근무와 겹치는 시간만 차감합니다. 아직 지나지 않은 퇴근 예정 시각은 저장할 수 없습니다.</p>${field('출근 시각 (한국 시간)','session_start',localInput(session?.start),'datetime-local','required')}${field('퇴근 시각 (한국 시간)','session_end',localInput(session?.end),'datetime-local','required')}<p id="manual-time-preview" class="subtle-label" role="status" aria-live="polite">${esc(manualTimeSummary(localInput(session?.start),localInput(session?.end),id))}</p><div id="manual-breaks">${breaks.map(interval=>breakLine(interval,!session)).join('')}</div>${button('add-break','휴게 구간 추가')}${area('입력·정정 사유','reason',version?'이력에서 다시 입력':'')}`,
    'time', id);
}

function manualOverlaps(start, end, id = '') {
  const left = Date.parse(zoned(start));
  const right = Date.parse(zoned(end));
  if (!Number.isFinite(left) || !Number.isFinite(right) || right <= left) return [];
  return (data?.sessions || []).filter(session => session.id !== id && left < (session.end ? Date
    .parse(session.end) : Date.now()) && right > Date.parse(session.start));
}

function manualTimeSummary(start, end, id = '') {
  const label = value => value ? value.replace('T', ' ') : '미입력';
  const count = manualOverlaps(start, end, id).length;
  return `입력 시각 확인 (한국 시간 · 24시간제): ${label(start)} → ${label(end)}${count ? ` · 겹치는 기존 기록 ${count}건을 이력에 보관하고 수동 값으로 대체합니다.` : ''}`;
}

document.addEventListener('input', event => {
  const form = event.target.closest('form[data-form="time"]');
  if (!form) return;
  const line = event.target.closest('.break-line');
  if (line) delete line.dataset.defaultLunch;
  if (['session_start', 'session_end'].includes(event.target.name)) syncDefaultLunch(form);
  const preview = form.querySelector('#manual-time-preview');
  if (preview) preview.textContent = manualTimeSummary(form.elements.namedItem('session_start')
    .value, form.elements.namedItem('session_end').value, form.dataset.id);
});

function showAttendanceHistory() {
  const history = data.attendance_history || [];
  showDialog('근무 변경 이력',
    `<p>이 기록은 현재 근무 합계에서 제외됩니다. 다시 입력하면 현재 기록보다 우선 적용됩니다.</p>${history.map(version=>`<div class="receipt-line"><strong>${esc(localTime(version.start))} → ${version.end?esc(localTime(version.end)):'종료 미기록'}</strong><p>${version.kind==='replaced'?'수동 입력으로 대체':'정정 전 기록'} · ${esc(localTime(version.at))}</p><p>${esc(version.reason)}</p><p class="subtle-label">${version.breaks.map(interval=>`휴게 ${esc(localTime(interval.start))} → ${interval.end?esc(localTime(interval.end)):'종료 미기록'}`).join('<br>')||'휴게 없음'}</p>${button('reuse-attendance','이 기록으로 다시 입력',version.id)}</div>`).join('')||empty('보관된 변경 이력이 없습니다.')}${button('close','닫기')}`
  );
}

function defaultLunch(date) {
  return {
    start: zoned(`${date}T12:00`),
    end: zoned(`${date}T13:00`)
  };
}

function syncDefaultLunch(form) {
  const date = (form.elements.namedItem('session_start').value || form.elements.namedItem(
    'session_end').value).slice(0, 10);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) return;
  form.querySelectorAll('.break-line[data-default-lunch="true"]').forEach(line => {
    setDateTimeValue(line.querySelector('[name="start"]'), `${date}T12:00`);
    setDateTimeValue(line.querySelector('[name="end"]'), `${date}T13:00`);
  });
}

function breakLine(interval, automatic = false) {
  return `<fieldset class="break-line" ${automatic?'data-default-lunch="true"':''}>${field('휴게 시작','start',localInput(interval.start),'datetime-local','required')}${field('휴게 종료','end',localInput(interval.end),'datetime-local','required')}${button('remove-line','휴게 제거')}</fieldset>`;
}

function showSecret(kind = 'credential') {
  const values = kind === 'credential' ?
    `${field('로그인 ID','username','','text','autocomplete="off" maxlength="2000"')}${field('비밀번호','password','','password','required autocomplete="new-password" maxlength="2000"')}` :
    kind === 'payment-method' ?
    `${field('카드사','issuer')}${field('끝 네 자리','last_four','','text','required pattern="[0-9]{4}" maxlength="4" inputmode="numeric"')}${field('결제 서비스 참조 토큰','token','','password','autocomplete="off"')}` :
    `${field('이름','name')}${field('이메일','email','','email')}${field('연락처','phone')}${area('주소','address','',2000)}`;
  showDialog('민감정보 등록',
    `${select('유형','secret-kind',[['credential','로그인 정보'],['payment-method','결제수단 참조'],['person','개인정보']],kind)}${field('구분용 별칭','alias','','text','required maxlength="64"')}<input type="hidden" name="kind" value="${kind}">${values}<p class="subtle-label">목록에는 별칭과 마스킹만 표시합니다. 전체 카드번호·CVC·PIN은 입력하지 않습니다.</p>`,
    'secret');
}

function showAssembly() {
  if (!data.inventory.boms.length) throw new Error('BOM 버전을 먼저 등록해주세요.');
  showDialog('BOM 조립 소모',
    `${select('BOM 버전','bom_id',data.inventory.boms.map(b=>[b.id,`${b.name} · ${b.version}`]))}${field('조립할 보드 수','quantity',1,'number','required min="1" step="1"')}<div id="assembly-losses"></div>${area('조립 메모','note')}<button class="button button-outline" type="button" data-action="preview-assembly">소요량 미리보기</button><div id="assembly-preview"></div>`,
    'assembly');
  renderLosses();
}

function renderLosses() {
  const form = document.querySelector('[data-form="assembly"]');
  const bom = data.inventory.boms.find(b => b.id === form.elements.bom_id.value);
  document.getElementById('assembly-losses').innerHTML =
    `<h3>소자별 추가 손실 (개)</h3>${bom.lines.map(line=>field(esc(line.name),`loss-${line.item_id}`,0,'number','min="0" step="1"')).join('')}`;
  document.getElementById('assembly-preview').innerHTML = '';
}

function assemblyPayload(form) {
  const values = new FormData(form);
  const losses = {};
  for (const [key, value] of values)
    if (key.startsWith('loss-')) losses[key.slice(5)] = Number(value);
  return {
    bom_id: values.get('bom_id'),
    quantity: Number(values.get('quantity')),
    losses,
    note: values.get('note')
  };
}
async function act(action, id) {
  if (await personalAction(action, id)) return;
  if (action === 'close') {
    closeDialog();
    return;
  }
  if (action === 'retry') {
    await boot();
    return;
  }
  if (action === 'unlock') {
    await api('unlock', {});
    await refresh();
    return;
  }
  if (action === 'lock') {
    if (reportDirty && !confirm('저장하지 않은 보고서 편집 내용이 있습니다. 잠글까요?')) return;
    await api('lock', {});
    await refresh();
    return;
  }
  if (!data) throw new Error('먼저 작업 공간의 잠금을 해제해주세요.');
  if (action === 'navigate-target') {
    navigateTarget(id);
    return;
  }
  if (action === 'start') {
    const result = await run('core.start');
    render();
    showDialog('출근을 기록했습니다.',
      `<p>오늘 먼저 챙길 일 ${result.tasks.length}건</p>${result.tasks.map(task=>`<div class="flow-item">${icon('tasks')}<div><strong>${esc(task.title)}</strong><p>${esc(task.priority)} · ${esc(task.detail)}</p></div></div>`).join('')||empty('예정된 미완료 업무가 없습니다.')}<h3>확인할 항목</h3>${alertList()}${button('close','확인')}`
    );
    return;
  }
  if (action === 'finish') {
    showDialog('퇴근 전 확인',
      `<p>오늘 근무 ${duration(data.attendance.today_minutes)} · 주간 ${duration(data.attendance.week_minutes)}</p>${alertList()}<p>퇴근 시 실제 기록으로 일일 업무보고 초안을 생성합니다.</p>${button('confirm-finish','퇴근 기록·보고서 생성','','button-primary')}${button('close','돌아가기')}`
    );
    return;
  }
  if (action === 'confirm-finish') {
    const result = await run('core.finish');
    closeDialog();
    if (result.report) {
      loadReport(result.report);
      navigateTarget('report');
    } else navigateTarget('time');
    toast(result.message);
    return;
  }
  if (action === 'break-start' || action === 'break-end') {
    await run(action === 'break-start' ? 'attendance.break_start' : 'attendance.break_end');
    render();
    return;
  }
  if (action === 'new-task' || action === 'edit-task') {
    showTask(id);
    return;
  }
  if (action === 'toggle-task') {
    const task = data.tasks.find(t => t.id === id);
    await run('tasks.save', {
      id,
      status: task.status === 'done' ? 'todo' : 'done'
    });
    render();
    return;
  }
  if (action === 'log-task') {
    const task = data.tasks.find(t => t.id === id);
    showDialog(`${task.title} · 소요시간`,
      `${taskEstimateFields(task)}${field('기록 날짜','date',data.today,'date','required')}${field('소요시간 (분)','minutes','','number','required min="0" max="1440" step="1"')}${select('진행 상태','status',[['in_progress','진행 중'],['done','완료']],task.status==='done'?'done':'in_progress')}${area('수행 결과 · 메모','note')}`,
      'task-log', id);
    return;
  }
  if (action === 'edit-log') {
    const log = data.logs.find(l => l.id === id);
    showDialog('소요시간 정정',
      `${field('소요시간 (분)','minutes',log.minutes,'number','required min="0" max="1440" step="1"')}${area('결과 · 메모','note',log.note)}`,
      'edit-log', id);
    return;
  }
  if (action === 'new-item' || action === 'edit-item') {
    const item = data.items.find(i => i.id === id) || {
      minimum: 0,
      unit: '개'
    };
    showDialog(id ? '품목 수정' : '품목 등록',
      `${field('알아보기 쉬운 품목명','name',item.name,'text','required maxlength="100"')}${field('제조사 품번','part_number',item.part_number)}${field('단위','unit',item.unit,'text','required maxlength="16"')}${field('보관 위치','location',item.location)}${field('최소 수량','minimum',item.minimum,'number','required min="0" step="1"')}${area('메모','note',item.note)}`,
      'item', id);
    return;
  }
  if (action === 'move-stock') {
    if (!data.items.length) throw new Error('품목을 먼저 등록해주세요.');
    showDialog('입출고 기록',
      `${select('품목','item_id',data.items.map(i=>[i.id,i.name]))}${field('증감 수량 · 출고는 음수','delta','','number','required step="1"')}${area('사용처 · 변경 사유','reason')}`,
      'move');
    return;
  }
  if (action === 'adjust-stock') {
    const item = data.items.find(i => i.id === id);
    showDialog('실사 재고 조정',
      `${field('실제로 센 수량','quantity',item.quantity,'number','required min="0" step="1"')}${area('조정 사유','reason')}`,
      'adjust', id);
    return;
  }
  if (action === 'new-order') {
    showDialog('구매 내역 등록',
      `${field('판매처','supplier','','text','required maxlength="100"')}${field('주문번호','order_number')}${field('프로젝트','project')}${area('어디에 사용할 물품인가요?','memo')}${field('도착 예정일','eta','','date')}${field('주문 금액 (원)','amount',0,'number','required min="0" step="1"')}<div id="purchase-lines">${purchaseLine()}</div>${button('add-purchase-line','주문 품목 추가')}`,
      'order');
    return;
  }
  if (action === 'order-detail') {
    showOrder(id);
    return;
  }
  if (action === 'add-purchase-line') {
    document.getElementById('purchase-lines').insertAdjacentHTML('beforeend', purchaseLine());
    return;
  }
  if (action === 'new-bom') {
    if (!data.items.length) throw new Error('재고 품목을 먼저 등록해주세요.');
    showDialog('BOM 새 버전 등록',
      `${field('보드·제품명','name','','text','required maxlength="100"')}${field('버전','version','','text','required maxlength="32"')}<div id="bom-lines">${bomLine()}</div>${button('add-bom-line','소자 추가')}`,
      'bom');
    return;
  }
  if (action === 'add-bom-line') {
    document.getElementById('bom-lines').insertAdjacentHTML('beforeend', bomLine());
    return;
  }
  if (action === 'assemble') {
    showAssembly();
    return;
  }
  if (action === 'preview-assembly') {
    const preview = await run('inventory.preview', assemblyPayload(document.querySelector(
      '[data-form="assembly"]')));
    document.getElementById('assembly-preview').innerHTML =
      `<table class="data-table"><thead><tr><th>소자</th><th>필요</th><th>재고</th><th>부족</th></tr></thead><tbody>${preview.lines.map(line=>`<tr><td>${esc(line.name)}</td><td>${line.required}</td><td>${line.available}</td><td>${line.shortage}</td></tr>`).join('')}</tbody></table><p>${preview.can_assemble?'조립할 수 있습니다. 저장하면 재고가 차감됩니다.':'재고가 부족합니다. 차감하지 않았습니다.'}</p>`;
    return;
  }
  if (action === 'manual-time' || action === 'correct-time') {
    showTime(id);
    return;
  }
  if (action === 'attendance-history') {
    showAttendanceHistory();
    return;
  }
  if (action === 'reuse-attendance') {
    const version = (data.attendance_history || []).find(row => row.id === id);
    if (!version) throw new Error('이력 목록을 다시 불러와주세요.');
    showTime('', version);
    return;
  }
  if (action === 'add-break') {
    const form = document.querySelector('form[data-form="time"]');
    const date = (form.elements.namedItem('session_start').value || form.elements.namedItem(
      'session_end').value || data.today).slice(0, 10);
    document.getElementById('manual-breaks').insertAdjacentHTML('beforeend', breakLine(
      defaultLunch(date), true));
    return;
  }
  if (action === 'payroll') {
    const row = data.payroll.find(row => row.month === (id || data.today.slice(0, 7))) || {
      month: data.today.slice(0, 7),
      expected_net: 0,
      received_net: null,
      note: ''
    };
    showDialog('급여 입금 대조',
      `${field('대상 월','month',row.month,'month','required')}${field('예상 실수령액 (원)','expected_net',row.expected_net,'number','required min="0" step="1"')}${field('실제 입금액 · 미확인은 공란','received_net',row.received_net??'','number','min="0" step="1"')}${area('대조 메모','note',row.note)}`,
      'payroll');
    return;
  }
  if (action === 'new-secret') {
    showSecret();
    return;
  }
  if (action === 'delete-secret') {
    if (confirm('이 민감정보 항목을 삭제할까요?')) {
      await run('sensitive.remove', {
        id
      });
      render();
    }
    return;
  }
  if (action === 'generate-report') {
    if ((reportDirty || currentReport) && !confirm(
        '이 날짜의 보고서를 실제 업무 로그로 다시 생성할까요? 수동 편집 내용은 대체됩니다.')) return;
    const report = await run('reporting.generate', {
      date: window.WhoiamReport.getModel().date || data.today
    });
    loadReport(report);
    render();
    toast('실제 업무 로그로 보고 초안을 생성했습니다.');
    return;
  }
  if (action === 'save-report') {
    const report = await run('reporting.save', {
      ...window.WhoiamReport.getModel(),
      ...(currentReport ? {
        id: currentReport
      } : {})
    });
    loadReport(report);
    render();
    toast('보고서를 암호화 저장했습니다.');
    return;
  }
}

function loadReport(report) {
  window.WhoiamReport.load(report);
  currentReport = report.id || '';
  reportDirty = false;
}
document.addEventListener('click', event => {
  const target = event.target.closest('button');
  if (!target) return;
  if (window.WhoiamReport.handleAction(target)) return;
  if (target.dataset.nav) {
    navigate(target.dataset.nav);
    return;
  }
  if (target.dataset.material) {
    state.materialTab = target.dataset.material;
    navigate('materials');
    return;
  }
  if (target.dataset.record) {
    state.recordTab = target.dataset.record;
    navigate('records');
    return;
  }
  if (target.dataset.taskTab) {
    state.taskTab = target.dataset.taskTab;
    render();
    return;
  }
  if (target.dataset.taskMode) {
    state.taskMode = target.dataset.taskMode;
    render();
    return;
  }
  if (target.dataset.action === 'remove-line') {
    target.closest('fieldset').remove();
    return;
  }
  if (target.dataset.action) act(target.dataset.action, target.dataset.id).catch(error => toast(
    error.message || '서버 연결을 확인해주세요.'));
});
document.addEventListener('submit', async event => {
  const form = event.target;
  if (form.id !== 'command-form' && !form.dataset.form) return;
  event.preventDefault();
  try {
    if (form.id === 'command-form') {
      const command = new FormData(form).get('command').trim();
      if (command === '출근') {
        await act('start');
        return;
      }
      if (command === '퇴근') {
        await act('finish');
        return;
      }
      const result = await run('core.command', {
        text: command
      });
      if (result.navigate) navigateTarget(result.navigate);
      else render();
      return;
    }
    const values = Object.fromEntries(new FormData(form));
    const id = form.dataset.id;
    const type = form.dataset.form;
    if (type === 'task') {
      await run('tasks.save', {
        ...values,
        ...(id ? {
          id
        } : {}),
        estimated_minutes: values.estimated_minutes === '' ? null : Number(values.estimated_minutes),
        progress: Number(values.progress)
      });
    }
    if (type === 'task-log') {
      await run('tasks.log', {
        ...values,
        task_id: id,
        estimated_minutes: values.estimated_minutes === '' ? null : Number(values.estimated_minutes),
        progress: Number(values.progress),
        minutes: Number(values.minutes)
      });
    }
    if (type === 'edit-log') {
      await run('tasks.update_log', {
        ...values,
        id,
        minutes: Number(values.minutes)
      });
    }
    if (type === 'item') {
      await run('inventory.save', {
        ...values,
        ...(id ? {
          id
        } : {}),
        minimum: Number(values.minimum)
      });
    }
    if (type === 'move') {
      await run('inventory.move', {
        ...values,
        delta: Number(values.delta)
      });
    }
    if (type === 'adjust') {
      await run('inventory.adjust', {
        ...values,
        item_id: id,
        quantity: Number(values.quantity)
      });
    }
    if (type === 'bom') {
      const lines = Array.from(form.querySelectorAll('.bom-line'), line => ({
        item_id: line.querySelector('[name="item_id"]').value,
        quantity: Number(line.querySelector('[name="quantity"]').value)
      }));
      await run('inventory.bom', {
        name: values.name,
        version: values.version,
        lines
      });
    }
    if (type === 'assembly') {
      if (!confirm('조립 수량과 추가 손실만큼 재고를 차감할까요?')) return;
      await run('inventory.assemble', assemblyPayload(form));
    }
    if (type === 'order') {
      const lines = Array.from(form.querySelectorAll('.purchase-line'), line => Object
        .fromEntries(Array.from(line.querySelectorAll('input,select'), input => [input.name,
          ['quantity', 'units_per_pack'].includes(input.name) ? Number(input.value) :
          input.value
        ])));
      const {
        supplier,
        order_number,
        project,
        memo,
        eta,
        amount
      } = values;
      await run('purchasing.create', {
        supplier,
        order_number,
        project,
        memo,
        eta,
        amount: Number(amount),
        lines
      });
    }
    if (type === 'order-update') {
      await run('purchasing.update', {
        ...values,
        id
      });
    }
    if (type === 'receive') {
      await run('purchasing.receive', {
        id,
        line_id: form.dataset.line,
        quantity: Number(values.quantity)
      });
    }
    if (type === 'time') {
      const {
        session_start: start,
        session_end: end,
        reason
      } = values;
      const breaks = Array.from(form.querySelectorAll('.break-line'), line => ({
        start: zoned(line.querySelector('[name="start"]').value),
        end: zoned(line.querySelector('[name="end"]').value)
      }));
      const recorded = await run('attendance.record', {
        ...(id ? {
          id
        } : {}),
        start: zoned(start),
        end: zoned(end),
        breaks,
        reason
      });
      closeDialog();
      render();
      toast(recorded.replaces?.length ?
        `수동 근무를 저장했습니다. 겹친 기존 기록 ${recorded.replaces.length}건은 이력에 보관했습니다.` :
        '수동 근무를 저장했습니다.');
      return;
    }
    if (type === 'payroll') {
      await run('attendance.payroll', {
        ...values,
        expected_net: Number(values.expected_net),
        received_net: values.received_net === '' ? null : Number(values.received_net)
      });
    }
    if (type === 'secret') {
      delete values['secret-kind'];
      await run('sensitive.save', values);
    }
    if (type === 'settings') {
      await run('core.settings', {
        weekly_limit: Math.round(Number(values.weekly_hours) * 60),
        notifications: values.notifications === 'true'
      });
      render();
      toast('설정을 저장했습니다.');
      return;
    }
    if (type === 'order-update' || type === 'receive') {
      showOrder(id);
      render();
      return;
    }
    closeDialog();
    render();
    toast('저장했습니다.');
  } catch (error) {
    const node = form.querySelector('.form-error') || document.querySelector(
      '#dialog-content .form-error');
    if (node) node.textContent = error.message;
    else toast(error.message || '처리하지 못했습니다.');
  }
});
document.addEventListener('change', async event => {
  const input = event.target;
  if (input.name === 'task-category') {
    state.taskCategory = input.value;
    render();
    return;
  }
  if (input.name === 'secret-kind') {
    showSecret(input.value);
    return;
  }
  if (input.name === 'bom_id' && input.closest('[data-form="assembly"]')) {
    renderLosses();
    return;
  }
  if (input.name === 'item_id' && input.closest('.purchase-line')) {
    const item = data.items.find(i => i.id === input.value);
    if (item) input.closest('.purchase-line').querySelector('[name="name"]').value = item
      .name;
    return;
  }
  if (input.name === 'saved-report') {
    if (reportDirty && !confirm('저장하지 않은 편집 내용을 버리고 보고서를 전환할까요?')) {
      input.value = currentReport;
      return;
    }
    loadReport(data.reports.find(r => r.id === input.value) || {
      date: data.today,
      daily: [],
      planned: [],
      note: ''
    });
    render();
    return;
  }
  if (input.dataset.upload) {
    const file = input.files[0];
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) {
      toast('5MB 이하의 파일을 선택해주세요.');
      input.value = '';
      return;
    }
    try {
      const bytes = new Uint8Array(await file.arrayBuffer());
      let binary = '';
      for (let offset = 0; offset < bytes.length; offset += 32768) binary += String
        .fromCharCode(...bytes.subarray(offset, offset + 32768));
      await run('purchasing.document', {
        order_id: input.dataset.order,
        name: file.name,
        kind: input.dataset.upload,
        content: btoa(binary)
      });
      showOrder(input.dataset.order);
      render();
      toast('증빙을 암호화 저장했습니다.');
    } catch (error) {
      toast(error.message || '파일을 저장하지 못했습니다.');
    } finally {
      input.value = '';
    }
  }
});
document.addEventListener('whoiam-report-change', () => {
  reportDirty = true;
});
document.getElementById('view-toggle').addEventListener('click', () => {
  state.compact = !state.compact;
  document.body.classList.toggle('compact-mode', state.compact);
  document.getElementById('view-toggle').setAttribute('aria-label', state.compact ?
    '넓은 화면으로 보기' : '작은 화면으로 보기');
  render();
});
document.getElementById('flow-dialog').addEventListener('close', () => {
  document.getElementById('dialog-content').innerHTML = '';
});
window.addEventListener('hashchange', () => {
  const page = location.hash.slice(1);
  if (navItems.some(row => row[0] === page) && page !== state.page) {
    state.page = page;
    render();
  }
});
async function boot() {
  try {
    const access = new URLSearchParams(location.hash.slice(1)).get('access');
    if (access) {
      history.replaceState(null, '', '#home');
      await api('session', {
        token: access
      });
    }
    await refresh();
  } catch (error) {
    connection.error = '서버가 실행 중인지 확인해주세요. 정적 목업 주소에서는 실제 업무 API를 사용할 수 없습니다.';
    render();
  }
}
if (navItems.some(row => row[0] === location.hash.slice(1))) state.page = location.hash.slice(1);
async function poll() {
  if (state.busy || state.draggedTask) return;
  try {
    if (document.hidden || document.getElementById('flow-dialog').open) {
      const status = await api('status');
      connection = {
        ...connection,
        ...status
      };
      if (status.locked) {
        data = null;
        clearPrivateView();
        render();
      }
      return;
    }
    const previous = new Set((data?.alerts || []).map(row =>
      `${row.target}:${row.id||''}:${row.title}`));
    await refresh(false);
    if (connection.locked) {
      render();
      return;
    }
    const arrived = (data?.alerts || []).filter(row => !previous.has(
      `${row.target}:${row.id||''}:${row.title}`));
    if (arrived.length && data.settings.notifications) toast(`새 확인 항목 ${arrived.length}건이 있습니다.`);
    if (!(state.page === 'records' && state.recordTab === 'report') && !document
      .querySelector('form:focus-within')) render();
  } catch (error) {
    if (connection.locked) render();
  }
}
setInterval(poll, 60000);
document.addEventListener('visibilitychange', () => {
  if (!document.hidden) poll();
});
boot();
