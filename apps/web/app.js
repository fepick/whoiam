/* Static interface prototype. No network calls, credentials or persistence. */
const paths = {
  home:'M3 10.5 12 3l9 7.5M5 9v11h5v-6h4v6h5V9',
  tasks:'M9 5h10v16H5V5h4M9 3h6v4H9zM8 12l2 2 5-5M8 18h8',
  box:'m3 7 9-4 9 4v10l-9 4-9-4zM3 7l9 4 9-4M12 11v10M7.5 5l9 4',
  records:'M5 3h10l4 4v14H5zM14 3v5h5M8 12h8M8 16h8',
  settings:'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8M9.5 3h5l.6 2.5 2.2 1.3 2.5-.7 2.5 4.3-1.8 1.8v2.6l1.8 1.8-2.5 4.3-2.5-.7-2.2 1.3-.6 2.5h-5L8.9 21l-2.2-1.3-2.5.7-2.5-4.3 1.8-1.8v-2.6l-1.8-1.8L4.2 5.6l2.5.7 2.2-1.3z',
  arrow:'M5 12h14m-5-5 5 5-5 5', chevron:'m9 5 7 7-7 7',
  calendar:'M4 5h16v16H4zM8 3v4M16 3v4M4 10h16M8 14h2M14 14h2',
  check:'m5 12 4 4L19 6', clock:'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18M12 7v5l3 2',
  truck:'M3 5h11v12H3zM14 9h4l3 4v4h-7M5 17a2 2 0 1 0 4 0 2 2 0 0 0-4 0M15 17a2 2 0 1 0 4 0 2 2 0 0 0-4 0',
  receipt:'M6 3h12v18l-3-2-3 2-3-2-3 2zM9 8h6M9 12h6',
  chip:'M6 6h12v12H6zM9 9h6v6H9zM9 3v3M15 3v3M9 18v3M15 18v3M3 9h3M3 15h3M18 9h3M18 15h3',
  report:'M5 3h10l4 4v14H5zM14 3v5h5M8 12h8M8 16h5',
  plus:'M12 5v14M5 12h14', close:'m6 6 12 12M6 18 18 6',
  phone:'M7 2h10v20H7zM10 18h4', desktop:'M3 4h18v13H3zM12 17v4M8 21h8',
  command:'m8 8 4 4-4 4M15 16h3', mic:'M9 5a3 3 0 0 1 6 0v7a3 3 0 0 1-6 0zM6 10v2a6 6 0 0 0 12 0v-2M12 18v4M9 22h6',
  lock:'M5 10h14v11H5zM8 10V7a4 4 0 0 1 8 0v3M12 14v3',
  shield:'m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6zM8 12l3 3 5-6',
  bell:'M6 10a6 6 0 0 1 12 0v5l2 3H4l2-3zM10 21h4',
  info:'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18M12 11v5M12 7v.2',
  search:'M10 3a7 7 0 1 0 0 14 7 7 0 0 0 0-14m5 12 6 6',
  flag:'M5 22V3h13l-3 5 3 5H5', folder:'M3 6h7l2 2h9v12H3z',
};
const icon = (name, cls='') => `<svg class="${cls}" viewBox="0 0 24 24" aria-hidden="true"><path d="${paths[name] || paths.box}"/></svg>`;
const navItems = [['home','홈','home'],['tasks','업무','tasks'],['materials','물품','box'],['records','기록','records'],['settings','설정','settings']];
const state = { page:'home', materialTab:'purchases', recordTab:'time', taskTab:'all', started:false, compact:false };
const sampleTasks = [
  {title:'A보드 전원부 측정',detail:'출력 리플과 부하 응답 확인',category:'하드웨어',due:'오늘 마감',urgent:true,done:false},
  {title:'UART 수신 오류 수정',detail:'DMA 버퍼 경계 조건 재확인',category:'임베디드',due:'진행 중',done:false},
  {title:'컨트롤 보드 Rev.A 조립',detail:'PBA 10대 · 자재 수량 확인',category:'하드웨어',due:'오후 예정',done:false},
  {title:'개발 환경 정리',detail:'테스트 펌웨어와 측정 장비 준비',category:'공통',due:'완료',done:true},
];
const navMarkup = () => navItems.map(([id,label,glyph],i) => `<button class="nav-item ${state.page===id?'active':''}" data-nav="${id}" ${state.page===id?'aria-current="page"':''}>${icon(glyph)}<span>${label}</span><span class="nav-index">${state.page===id?'↗':String(i+1).padStart(2,'0')}</span></button>`).join('');
function pageHeader(eyebrow,title,subtitle,extra='') { return `<div class="page-header"><div><div class="eyebrow">${eyebrow}</div><h1>${title}</h1><p>${subtitle}</p></div>${extra}</div>`; }
function taskRow(task,index,full=false) {
  return `<div class="task-row ${task.done?'done':''}"><button class="task-check" data-task="${index}" aria-label="${task.title} ${task.done?'완료 취소':'완료 표시'}" aria-pressed="${task.done}">${task.done?icon('check'):''}</button><div class="task-content"><div class="task-title">${task.title}</div><div class="task-detail">${task.detail}</div>${full?`<div class="task-meta"><span class="tag">${task.category}</span><span class="subtle-label">개인 업무</span></div>`:''}</div>${task.urgent?'<span class="tag amber">오늘 마감</span>':`<span class="task-due">${task.due}</span>`}</div>`;
}
function weeklyCard() { return `<section class="card weekly-card"><div class="card-heading"><h2>이번 주 근무</h2><span class="subtle-label">10.19 — 10.23</span></div><div class="hours">32<small class="time-unit">시간</small>40<small>분</small></div><div class="hours-limit">주간 기준 52시간</div><div class="progress-track" role="meter" aria-label="이번 주 근무시간" aria-valuenow="32.67" aria-valuemin="0" aria-valuemax="52"><span></span></div><div class="progress-labels"><span>0h</span><span>26h</span><span>52h</span></div><p class="weekly-note">${icon('shield')}이번 주는 여유 있게 진행 중이에요.</p></section>`; }
function commandBox() { return `<form class="command-box" id="command-form"><span class="command-symbol">${icon('command')}</span><input id="command-input" aria-label="빠른 명령" placeholder="무엇을 도와드릴까요? 예: 출근, 퇴근, 오늘 할 일" autocomplete="off"><span class="command-shortcut">↵</span><button class="icon-button" type="button" data-notice="음성 명령은 이후 연결할 수 있어요." aria-label="음성 명령 안내">${icon('mic')}</button><button class="icon-button" type="submit" aria-label="명령 보기">${icon('arrow')}</button></form>`; }
function homeView() {
  return `${pageHeader('YOUR DAILY FLOW','오늘도, 차곡차곡.','일과 물품, 기록을 한 흐름으로 연결하세요.',`<span class="date-chip">${icon('calendar')}10월 23일 · 금요일</span>`)}
  <div class="home-layout">
    <section class="day-panel"><div class="day-panel-top"><span class="eyebrow">${state.started?'WORK IN PROGRESS':'A FRESH START'}</span><span class="state-pill"><span class="node-dot"></span>${state.started?'근무 중':'업무 시작 전'}</span></div><div><h2>${state.started?'지금은, 집중할 시간.<br><em>오늘의 한 걸음을 채워보세요.</em>':'오늘의 일을<br><em>가볍게 시작하세요.</em>'}</h2><p class="day-panel-caption">${state.started?'09:00 출근 · 오늘의 할 일이 준비되어 있어요.':'출근을 기록하고 오늘 챙길 일을 확인하세요.'}</p></div><div class="day-panel-actions"><button class="button button-lime" data-flow="${state.started?'finish':'start'}">${state.started?'퇴근하기':'출근하기'}${icon('arrow')}</button><button class="text-button" data-nav="tasks">오늘 일정 보기${icon('chevron')}</button></div></section>
    ${weeklyCard()}
    <section class="card today-tasks"><div class="card-heading"><h2>오늘의 할 일 <span class="counter">${sampleTasks.filter(t=>t.done).length} / 4</span></h2><button class="text-button" data-nav="tasks">전체 보기${icon('chevron')}</button></div>${sampleTasks.map((t,i)=>taskRow(t,i)).join('')}</section>
    <section class="card attention-card"><div class="card-heading"><h2>한번 확인해주세요 <span class="counter">02</span></h2>${icon('bell')}</div><button class="notice-item notice-button" data-material="purchases" aria-label="배송 예정 물품 보기"><span class="notice-icon">${icon('truck')}</span><div><strong>오늘 도착 예정인 물품이 있어요</strong><p>칩 저항 외 2건 · 수령 후 입고 확인</p></div>${icon('chevron')}</button><button class="notice-item notice-button" data-material="purchases" aria-label="미수집 증빙 보기"><span class="notice-icon sage">${icon('receipt')}</span><div><strong>아직 챙기지 못한 구매 증빙</strong><p>거래명세서 1건이 남아 있어요</p></div>${icon('chevron')}</button></section>
    <section class="card summary-strip" aria-label="물품 요약"><div class="summary-item"><span>진행 중인 구매</span><strong>03</strong><small>건</small></div><div class="summary-item"><span>재고 확인</span><strong>02</strong><small>종</small></div><div class="summary-item"><span>남은 업무</span><strong>${String(sampleTasks.filter(t=>!t.done).length).padStart(2,'0')}</strong><small>개</small></div></section>
  </div>
  <section class="quick-section"><div class="section-label"><h2>자주 하는 일</h2><span>필요한 화면으로 바로 이동하세요</span></div><div class="quick-grid"><button class="quick-card" data-material="purchases">${icon('box')}<span>구매 내역</span>${icon('arrow','arrow')}</button><button class="quick-card" data-material="stock">${icon('chip')}<span>재고 확인</span>${icon('arrow','arrow')}</button><button class="quick-card" data-record="time">${icon('clock')}<span>근무 기록</span>${icon('arrow','arrow')}</button><button class="quick-card" data-record="report">${icon('report')}<span>일일 보고</span>${icon('arrow','arrow')}</button></div></section>${commandBox()}`;
}
function tasksView() {
  const filtered = sampleTasks.map((task,index)=>({task,index})).filter(({task})=>state.taskTab==='all'||(state.taskTab==='done'?task.done:!task.done));
  return `${pageHeader('TASKS & PLANS','오늘 할 일','해야 할 일은 분명하게, 끝낸 일은 가볍게.')}<div class="toolbar"><div class="tabs" role="group" aria-label="업무 상태"><button data-task-tab="all" class="${state.taskTab==='all'?'active':''}">전체 4</button><button data-task-tab="todo" class="${state.taskTab==='todo'?'active':''}">진행</button><button data-task-tab="done" class="${state.taskTab==='done'?'active':''}">완료</button></div><button class="button button-primary" data-flow="new-task">${icon('plus')}업무 추가</button></div><section class="card wide-card task-full"><div class="list-section-title"><h2>10월 23일, 금요일</h2><span>${filtered.length}개 업무</span></div>${filtered.map(({task,index})=>taskRow(task,index,true)).join('')}</section><section class="card wide-card"><div class="list-section-title"><h2>다음에 할 일</h2><span>예정</span></div><div class="task-row"><span class="task-check"></span><div class="task-content"><div class="task-title">컨트롤 보드 Rev.B 회로 검토</div><div class="task-detail">전원부 수정 사항과 커넥터 핀맵 정리</div></div><span class="task-due">다음 주</span></div></section>${commandBox()}`;
}
const purchases = [
  ['chip','칩 저항 10kΩ · 0603','A보드 풀업 저항 / 1팩 100개','전자부품몰','10.23','배송 중','amber','거래명세서 대기'],
  ['chip','STM32 개발 보드','펌웨어 기능 검증용 / 2개','개발보드몰','10.23','배송 중','amber','증빙 수집 완료'],
  ['box','핀 헤더 2.54mm','테스트 지그 제작 / 20개','전자부품몰','10.22','수령 완료','','입고 확인 대기'],
  ['box','정전기 방지 매트','작업대 정비 / 1개','사무용품몰','10.21','처리 완료','gray','증빙 수집 완료'],
];
const stocks = [
  ['chip','칩 저항 10kΩ · 0603','부품함 A-01 · 저항','1,240','개','정상','','CTRL-PBA Rev.A'],
  ['chip','MLCC 100nF · 0603','부품함 A-03 · 커패시터','85','개','확인 필요','amber','최소 수량 100개'],
  ['chip','STM32 MCU · LQFP64','부품함 B-02 · 반도체','12','개','정상','','CTRL-PBA Rev.A'],
  ['box','핀 헤더 2.54mm','부품함 C-01 · 커넥터','8','개','확인 필요','amber','최소 수량 20개'],
];
function materialsView() {
  const stock = state.materialTab==='stock';
  return `${pageHeader('PURCHASES & INVENTORY','물품 관리','구매부터 사용까지, 물품의 흐름을 한눈에.')}<div class="toolbar"><div class="tabs" role="group" aria-label="물품 구분"><button data-material="purchases" class="${!stock?'active':''}">구매</button><button data-material="stock" class="${stock?'active':''}">재고</button></div><button class="button button-primary" data-flow="${stock?'stock-detail':'purchase-detail'}">${icon('plus')}${stock?'입출고 기록':'구매 등록'}</button></div><div class="material-stats"><section class="card stat-card"><span>${stock?'관리 품목':'진행 중인 주문'}</span><div class="stat-number">${stock?'24':'03'}<small>${stock?'종':'건'}</small></div><p>${stock?'소자 · 개발 장비 · 사무용품':'주문한 물품의 상태를 확인하세요'}</p></section><section class="card stat-card"><span>${stock?'재고 확인 필요':'오늘 도착 예정'}</span><div class="stat-number">02<small>${stock?'종':'건'}</small></div><p>${stock?'설정 수량보다 적은 품목':'도착 후 수령을 확인하세요'}</p></section><section class="card stat-card"><span>${stock?'이번 주 조립':'증빙 수집 대기'}</span><div class="stat-number">${stock?'10':'01'}<small>${stock?'대':'건'}</small></div><p>${stock?'CTRL-PBA · Rev.A':'거래명세서 확인이 필요해요'}</p></section></div>${stock?`<div class="stock-note">${icon('info')}MLCC 100nF와 핀 헤더의 남은 수량을 확인해주세요.</div>`:''}<section class="card wide-card"><div class="card-heading"><h2>${stock?'보관 중인 품목':'최근 구매 내역'}</h2><span class="count-pill">${stock?'전체 24종':'이번 달'}</span></div><div class="table-wrap"><table class="data-table"><thead><tr><th>품목 · 메모</th><th>${stock?'남은 수량':'판매처'}</th><th>${stock?'상태':'배송 예정'}</th><th>${stock?'사용처 · 기준':'처리 상태'}</th></tr></thead><tbody>${(stock?stocks:purchases).map(row=>`<tr><td><div class="part-name"><span class="part-icon">${icon(row[0])}</span><div><strong>${row[1]}</strong><span>${row[2]}</span></div></div></td><td class="${stock?'mono':''}">${row[3]}${stock?` <small>${row[4]}</small>`:''}</td><td>${stock?`<span class="table-status ${row[6]}">${row[5]}</span>`:`<span class="mono">${row[4]}</span>`}</td><td>${stock?`<span class="subtle-label">${row[7]}</span>`:`<span class="table-status ${row[6]}">${row[5]}</span><div class="task-detail">${row[7]}</div>`}</td></tr>`).join('')}</tbody></table></div></section>${stock?`<button class="quick-card" data-flow="bom" style="width:100%">${icon('chip')}<span>BOM으로 조립 소모 확인하기</span>${icon('arrow','arrow')}</button>`:''}`;
}
function reportPaper() { return window.WhoiamReport.render(); }
function recordsView() {
  const time = state.recordTab==='time';
  return `${pageHeader('TIME & DAILY LOG','나의 기록','쌓인 시간을 확인하고, 하루의 일을 정리하세요.')}<div class="toolbar"><div class="tabs" role="group" aria-label="기록 구분"><button data-record="time" class="${time?'active':''}">근무</button><button data-record="report" class="${!time?'active':''}">일일 보고</button></div><button class="button button-outline" data-flow="${time?'finish':'report'}">${icon(time?'clock':'report')}${time?'퇴근 흐름 보기':'보고서 미리 보기'}</button></div>${time?`<div class="records-grid"><section class="card"><div class="card-heading"><h2>주간 근무시간</h2><span class="subtle-label">10.19 — 10.23</span></div><div class="attendance-summary"><div><p class="subtle-label">이번 주 누적</p><div class="hours">32<small class="time-unit">시간</small>40<small>분</small></div></div><span class="tag green">기준 이내</span></div><div class="week-bars">${[8.2,8.1,8.3,8.1,0].map((h,i)=>`<div class="week-bar ${i===4?'current':''}"><span class="bar-label">${h?h.toFixed(1)+'h':'—'}</span><div class="bar" style="height:${h?Math.round(h/10*100):5}%"></div></div>`).join('')}</div><div class="week-days"><span>월</span><span>화</span><span>수</span><span>목</span><span>금</span></div><p class="weekly-note">${icon('info')}휴게시간을 제외한 예시입니다 · 주간 기준 52시간</p></section><section class="card"><div class="card-heading"><h2>오늘의 시간</h2><span class="subtle-label">예시</span></div><div class="timeline-item"><span>09:00</span><strong>출근</strong><small>업무 시작</small></div><div class="timeline-item"><span>12:00</span><strong>휴게 시작</strong><small>점심</small></div><div class="timeline-item"><span>13:00</span><strong>업무 재개</strong><small>휴게 1시간</small></div><div class="timeline-item"><span>18:10</span><strong>퇴근</strong><small>하루 마무리</small></div><div class="flow-time" style="margin:22px 0 0"><span>오늘의 근무시간</span><strong>8<small>시간</small> 10<small>분</small></strong></div></section></div>`:reportPaper()}`;
}
function settingsView() { return `${pageHeader('PREFERENCES','작업 공간 설정','내 방식에 맞게, 필요한 것만 연결하세요.')}<div class="settings-grid"><section class="card wide-card"><div class="card-heading"><h2>기본 설정</h2></div><div class="setting-row">${icon('clock')}<div><strong>근무 기준</strong><p>주간 합계와 휴게시간의 기준</p></div><span class="setting-value">주 52시간</span></div><div class="setting-row">${icon('calendar')}<div><strong>시간대</strong><p>출퇴근과 업무 일정에 적용</p></div><span class="setting-value">Asia / Seoul</span></div><div class="setting-row">${icon('bell')}<div><strong>확인 알림</strong><p>배송 · 증빙 · 재고 · 놓친 업무</p></div><span class="setting-value">켜짐</span></div><div class="setting-row">${icon('desktop')}<div><strong>연결 장치</strong><p>같은 메뉴로 사용하는 작업 화면</p></div><span class="setting-value">로컬 장치</span></div></section><section class="card vault-card"><span class="vault-icon">${icon('lock')}</span><span class="eyebrow">PRIVATE BY DESIGN</span><h2>민감한 정보는, 따로 안전하게.</h2><p>로그인 정보와 결제수단, 개인정보는<br>일반 업무 화면과 분리해서 관리합니다.</p><button class="button" data-flow="vault">${icon('shield')}보안 보관함 보기</button></section></div><section class="card wide-card"><div class="card-heading"><h2>이 화면에 대하여</h2><span class="count-pill">INTERFACE MOCKUP</span></div><p class="empty-hint" style="padding:0">메뉴 구성과 화면 흐름을 살펴보는 목업입니다. 실제 업무 기록이나 정보 저장, 외부 서비스 연결은 수행하지 않습니다.</p></section>`; }
function render() {
  document.getElementById('desktop-nav').innerHTML=navMarkup();
  document.getElementById('mobile-nav').innerHTML=navMarkup();
  document.getElementById('breadcrumb-current').textContent=navItems.find(n=>n[0]===state.page)[1];
  const views={home:homeView,tasks:tasksView,materials:materialsView,records:recordsView,settings:settingsView};
  document.getElementById('main-content').innerHTML=views[state.page]();
  if(state.page==='records' && state.recordTab==='report') window.WhoiamReport.mount();
  document.getElementById('view-toggle').innerHTML=icon(state.compact?'desktop':'phone');
  document.title=`${navItems.find(n=>n[0]===state.page)[1]} · WHOIAM 업무 콘솔`;
}
function navigate(page) { state.page=navItems.some(n=>n[0]===page)?page:'home'; location.hash=state.page; render(); window.scrollTo({top:0,behavior:'instant'}); }
function toast(message) { const el=document.getElementById('toast'); el.textContent=message; el.classList.add('show'); clearTimeout(toast.timer); toast.timer=setTimeout(()=>el.classList.remove('show'),2800); }
const flowItem=(glyph,title,detail,extra='')=>`<div class="flow-item">${icon(glyph)}<div><strong>${title}</strong><p>${detail}</p></div><span>${extra}</span></div>`;
function openFlow(type) {
  if(type==='report') {
    const dialog=document.getElementById('flow-dialog');
    if(dialog.open) dialog.close();
    state.recordTab='report'; navigate('records'); window.WhoiamReport.preview(); return;
  }
  const flows={
    start:{eyebrow:'START YOUR DAY',title:'오늘의 시작을 준비해요',intro:'출근과 함께 확인할 내용을 한곳에 모았어요.',body:`<div class="flow-time"><span>출근 시각</span><strong>09:00<small>예시</small></strong></div><h3 class="dialog-section-heading">${icon('tasks')}오늘 먼저 챙길 일</h3><div class="flow-list">${flowItem('flag','A보드 전원부 측정','출력 리플 · 부하 응답 확인','오늘 마감')}${flowItem('tasks','UART 수신 오류 수정','어제부터 이어서 진행할 업무','진행 중')}${flowItem('truck','주문한 소자 수령 확인','배송 예정 물품 2건','물품')}</div>`,action:'출근 후 화면 보기',target:'start-preview'},
    finish:{eyebrow:'WRAP UP YOUR DAY',title:'오늘도 수고하셨습니다.',intro:'놓친 일을 확인하고 하루의 기록을 정리해요.',body:`<div class="flow-time"><span>오늘의 근무시간</span><strong>8<small>시간</small> 10<small>분</small></strong></div><h3 class="dialog-section-heading">${icon('bell')}마무리 전에 확인해주세요</h3><div class="flow-list">${flowItem('chip','커넥터 입고 처리','수령한 물품의 입고 확인이 남았어요','확인 필요')}${flowItem('receipt','구매 거래명세서 확인','증빙 1건이 아직 모이지 않았어요','확인 필요')}</div><div class="mini-report"><strong>일일 업무보고</strong>오늘 한 일과 진행 중인 일, 다음 예정사항을<br>한 장의 보고서로 정리합니다.</div>`,action:'업무보고 초안 보기',target:'report'},
    report:{eyebrow:'DAILY WORK LOG',title:'오늘의 기록을 한 장에.',intro:'완료한 일과 다음 할 일이 자연스럽게 이어집니다.',body:`<div class="mini-report"><strong>오늘 한 일</strong>A보드 전원부 측정 및 UART 수신 조건 확인<br>테스트 펌웨어와 측정 장비 준비<strong>진행 중 · 확인 사항</strong>UART 장시간 수신 테스트 예정<br>커넥터 입고와 구매 증빙 확인 필요<strong>다음 예정사항</strong>컨트롤 보드 Rev.A 조립<br>Rev.B 회로 변경 사항 검토</div>`,action:'보고서 화면으로 이동',target:'report-page'},
    vault:{eyebrow:'LOCAL & PRIVATE',title:'보안 보관함',intro:'실제 민감정보는 이 목업에서 입력하거나 저장하지 않습니다.',body:`<div class="flow-time"><span>보관함 상태</span><strong style="font-size:18px">잠김 ${icon('lock')}</strong></div><div class="vault-detail"><div><span>로그인 정보</span><span>저장된 정보 없음</span></div><div><span>결제수단</span><span>저장된 정보 없음</span></div><div><span>개인정보</span><span>저장된 정보 없음</span></div></div>`,action:'확인',target:'close'},
    'new-task':{eyebrow:'TASK STRUCTURE',title:'업무를 기록하는 방식',intro:'업무 추가 화면에 들어갈 항목의 예시입니다.',body:`<div class="flow-list">${flowItem('tasks','무엇을 할 예정인가요?','업무 제목과 짧은 메모')}${flowItem('calendar','언제까지 할 일인가요?','예정일 · 마감 · 우선순위')}${flowItem('folder','어떤 작업과 관련되나요?','프로젝트 · 하드웨어 · 임베디드 · 소프트웨어')}</div>`,action:'확인',target:'close'},
    'purchase-detail':{eyebrow:'PURCHASE STRUCTURE',title:'구매 내역에 담을 것',intro:'이름보다 용도를 먼저 알아볼 수 있도록 정리합니다.',body:`<div class="flow-list">${flowItem('box','품목과 나만의 메모','상품명 · 품번 · 사용 목적 · 프로젝트')}${flowItem('truck','주문과 배송 상태','수량 · 판매처 · 도착 예정 · 수령 확인')}${flowItem('receipt','구매 증빙','거래명세서 · 카드매출전표 연결')}</div>`,action:'확인',target:'close'},
    'stock-detail':{eyebrow:'INVENTORY STRUCTURE',title:'수량이 바뀐 이유까지',intro:'입고, 사용, 조정의 흐름을 기록하는 화면입니다.',body:`<div class="flow-list">${flowItem('box','어떤 품목인가요?','품목 · 보관 위치 · 단위')}${flowItem('plus','얼마나 들어오거나 나갔나요?','입고 · 사용 · 조정 수량')}${flowItem('records','어디에 사용했나요?','프로젝트 · 조립 작업 · 짧은 메모')}</div>`,action:'확인',target:'close'},
    bom:{eyebrow:'BOM PREVIEW',title:'조립 수량만큼, 한 번에.',intro:'CTRL-PBA Rev.A · 10대 조립 시 필요한 소자 예시',body:`<div class="flow-list">${flowItem('chip','칩 저항 10kΩ','보드당 12개 × 10대','120개')}${flowItem('chip','MLCC 100nF','보드당 8개 × 10대','80개')}${flowItem('chip','STM32 MCU','보드당 1개 × 10대','10개')}</div><p class="dialog-intro">실제 재고 차감은 수행하지 않습니다.</p>`,action:'확인',target:'close'},
  };
  const flow=flows[type]||flows.start;
  document.getElementById('dialog-content').innerHTML=`<div class="dialog-header"><div><div class="eyebrow">${flow.eyebrow}</div><h2 id="dialog-title">${flow.title}</h2></div><button class="icon-button" data-dialog-action="close" aria-label="닫기">${icon('close')}</button></div><div class="dialog-content"><p class="dialog-intro">${flow.intro}</p>${flow.body}<div class="dialog-actions"><button class="button button-outline" data-dialog-action="close">닫기</button><button class="button button-primary" data-dialog-action="${flow.target}">${flow.action}${flow.target==='close'?'':icon('arrow')}</button></div><p class="dialog-footnote">화면 흐름 예시 · 실제 데이터는 기록되지 않습니다</p></div>`;
  const dialog=document.getElementById('flow-dialog'); if(!dialog.open)dialog.showModal();
}
document.addEventListener('click',event=>{
  const button=event.target.closest('button'); if(!button)return;
  if(window.WhoiamReport.handleAction(button))return;
  if(button.dataset.nav){navigate(button.dataset.nav);return;}
  if(button.dataset.material){state.materialTab=button.dataset.material;navigate('materials');return;}
  if(button.dataset.record){state.recordTab=button.dataset.record;navigate('records');return;}
  if(button.dataset.taskTab){state.taskTab=button.dataset.taskTab;render();return;}
  if(button.dataset.task!==undefined){sampleTasks[Number(button.dataset.task)].done=!sampleTasks[Number(button.dataset.task)].done;render();return;}
  if(button.dataset.flow){openFlow(button.dataset.flow);return;}
  if(button.dataset.notice){toast(button.dataset.notice);return;}
  if(button.dataset.dialogAction){
    const action=button.dataset.dialogAction;
    if(action==='report'){openFlow('report');return;}
    document.getElementById('flow-dialog').close();
    if(action==='start-preview'){state.started=true;navigate('home');toast('출근 후 화면 예시입니다. 실제 시간은 기록되지 않아요.');}
    if(action==='report-page'){state.recordTab='report';navigate('records');}
  }
});
document.getElementById('view-toggle').addEventListener('click',()=>{state.compact=!state.compact;document.body.classList.toggle('compact-mode',state.compact);const button=document.getElementById('view-toggle');button.setAttribute('aria-label',state.compact?'넓은 화면으로 보기':'작은 화면으로 보기');button.title=button.getAttribute('aria-label');render();});
document.addEventListener('submit',event=>{if(event.target.id!=='command-form')return;event.preventDefault();const command=document.getElementById('command-input').value.trim();if(command.includes('퇴근'))openFlow('finish');else if(command.includes('출근'))openFlow('start');else if(command.includes('재고')){state.materialTab='stock';navigate('materials');}else if(command.includes('구매')||command.includes('배송')){state.materialTab='purchases';navigate('materials');}else if(command.includes('보고')){state.recordTab='report';navigate('records');}else if(command.includes('업무')||command.includes('할 일'))navigate('tasks');else toast('출근, 퇴근, 오늘 할 일 같은 화면 흐름을 살펴보세요.');});
document.getElementById('flow-dialog').addEventListener('click',event=>{if(event.target===event.currentTarget){const rect=event.currentTarget.getBoundingClientRect();if(event.clientX<rect.left||event.clientX>rect.right||event.clientY<rect.top||event.clientY>rect.bottom)event.currentTarget.close();}});
window.addEventListener('hashchange',()=>{const page=location.hash.slice(1);if(navItems.some(n=>n[0]===page)&&page!==state.page){state.page=page;render();}});
if(navItems.some(n=>n[0]===location.hash.slice(1)))state.page=location.hash.slice(1);
render();
