/* 보고 편집은 메모리에서 수행하고 명시적으로 로컬 API에 저장한다. PNG는 Canvas로 생성한다. */
(() => {
  'use strict';
  const MAX_ROWS = 100;
  const REPORT_VERSION = '0.03';
  const model = {
    date: '',
    daily: [],
    planned: [],
    note: ''
  };
  const priorityLabels = {
    P1: '높음',
    P2: '보통',
    P3: '낮음'
  };
  const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  } [c]));
  const duration = value => value === null || value === '' ? '미입력' :
    `${Math.floor(Number(value) / 60) ? `${Math.floor(Number(value) / 60)}시간 ` : ''}${Number(value) % 60 || Number(value) === 0 ? `${Number(value) % 60}분` : ''}`
    .trim();
  const totalMinutes = () => model.daily.reduce((sum, row) => sum + (Number.isFinite(Number(row
    .minutes)) ? Number(row.minutes) : 0), 0);
  const dateValid = value => /^\d{4}-\d{2}-\d{2}$/.test(value) && Number.isFinite(Date.parse(
      `${value}T12:00:00Z`)) && new Date(`${value}T12:00:00Z`).toISOString().slice(0, 10) ===
    value;
  const weekday = value => '일월화수목금토' [new Date(`${value}T12:00:00Z`).getUTCDay()];
  let previewURL = '';
  let generation = 0;
  let timer;

  function validationMessage() {
    if (!dateValid(model.date)) return '보고 날짜를 확인해주세요.';
    if (model.daily.some(row => !row.title.trim()) || model.planned.some(row => !row.title
    .trim())) return '각 업무의 제목을 입력해주세요.';
    if (model.daily.some(row => row.minutes !== null && (!Number.isInteger(Number(row.minutes)) ||
        Number(row.minutes) < 0 || Number(row.minutes) > 1440)))
    return '소요시간은 0~1440 사이의 정수 분으로 입력해주세요.';
    if (model.planned.some(row => row.estimated_minutes !== null && (!Number.isInteger(row.estimated_minutes) || row.estimated_minutes < 0 || row.estimated_minutes > 525600))) return '예상 소요시간은 0~525600 사이의 정수 분으로 입력해주세요.';
    if (model.planned.some(row => !Number.isInteger(row.progress) || row.progress < 0 || row.progress > 100)) return '진행도는 0~100 사이의 정수로 입력해주세요.';
    return '';
  }

  function editorRow(row, index, group) {
    const prefix = group === 'daily' ? '진행' : '예정';
    const field = (key, label, input) => `<label class="report-field">${label}${input}</label>`;
    const attrs = key =>
      `data-report-group="${group}" data-report-index="${index}" data-report-field="${key}"`;
    return `<fieldset class="report-edit-row"><legend>${prefix} ${String(index + 1).padStart(2, '0')}</legend><div class="report-edit-title"><input ${attrs('title')} value="${escape(row.title)}" maxlength="64" aria-label="${prefix} ${index + 1} 업무명" placeholder="업무명"><button type="button" class="report-remove" data-report-action="remove" data-group="${group}" data-index="${index}" aria-label="${prefix} ${index + 1} 삭제">×</button></div><textarea class="report-detail-input" ${attrs('detail')} maxlength="2000" rows="2" aria-label="${prefix} ${index + 1} 상세내용" placeholder="결과나 다음 행동을 한 줄에 하나씩 적어주세요">${escape(row.detail)}</textarea><div class="report-edit-fields">${group === 'daily' ? field('minutes', '소요시간 (분)', `<input type="number" min="0" max="1440" step="1" inputmode="numeric" ${attrs('minutes')} value="${row.minutes === null ? '' : escape(row.minutes)}" aria-label="진행 ${index + 1} 소요시간 (분)" placeholder="미입력">`) + field('status', '진행 상태', `<select ${attrs('status')} aria-label="진행 ${index + 1} 상태">${['완료', '진행 중'].map(value => `<option ${row.status === value ? 'selected' : ''}>${value}</option>`).join('')}</select>`) : field('priority', '우선순위', `<select ${attrs('priority')} aria-label="예정 ${index + 1} 우선순위">${Object.entries(priorityLabels).map(([key, value]) => `<option value="${key}" ${row.priority === key ? 'selected' : ''}>${key} · ${value}</option>`).join('')}</select>`) + field('estimated_minutes', '예상 소요시간 (분)', `<input type="number" min="0" max="525600" step="1" ${attrs('estimated_minutes')} value="${escape(row.estimated_minutes ?? '')}" aria-label="예정 ${index + 1} 예상 소요시간 (분)" placeholder="미입력">`) + field('progress', '진행도 (%)', `<input type="number" min="0" max="100" step="1" required ${attrs('progress')} value="${escape(row.progress)}" aria-label="예정 ${index + 1} 진행도 (%)">`)}</div></fieldset>`;
  }

  function reportMessage() {
    if (!dateValid(model.date)) return '';
    const rows = model.daily.filter(row => row.title.trim());
    if (!rows.length) return '';
    const [year, month, day] = model.date.split('-');
    const lines = [`${year.slice(-2)}.${Number(month)}.${Number(day)} 진행 업무 보고드립니다.`];
    rows.forEach((row, index) => {
      lines.push(`${index + 1}. ${row.title.trim()}`);
      for (const detail of (row.detail || '').split(/\r?\n/).map(line => line.trim()).filter(Boolean)) {
        lines.push(`    - ${detail.replace(/^[-•]\s+/, '')}`);
      }
    });
    return lines.join('\n');
  }

  function messagePanel() {
    const message = reportMessage();
    return `<section class="report-text-message" aria-label="텍스트 업무보고"><div class="card-heading"><h3>텍스트 보고 메시지</h3><button type="button" class="button button-outline" data-report-action="copy-message" ${message?'':'disabled'}>메시지 복사</button></div><textarea id="report-message" readonly rows="12" aria-label="텍스트 업무보고 메시지" spellcheck="false" placeholder="일일 진행사항에 업무를 입력하면 보고 메시지가 생성됩니다.">${escape(message)}</textarea><p class="report-local-note">보고 날짜와 일일 진행사항만 반영합니다.</p><p id="report-copy-status" role="status" aria-live="polite"></p></section>`;
  }

  function updateMessage() {
    const message = reportMessage();
    const output = document.getElementById('report-message');
    if (output) output.value = message;
    const button = document.querySelector('[data-report-action="copy-message"]');
    if (button) button.disabled = !message;
    const status = document.getElementById('report-copy-status');
    if (status) status.textContent = '';
  }

  async function copyMessage() {
    const message = reportMessage();
    if (!message) return;
    const status = document.getElementById('report-copy-status');
    try {
      await navigator.clipboard.writeText(message);
      if (status?.isConnected) status.textContent = '보고 메시지를 복사했습니다.';
    } catch (error) {
      const output = document.getElementById('report-message');
      output?.focus();
      output?.select();
      if (status?.isConnected) status.textContent = '선택한 메시지를 Ctrl+C 또는 복사 메뉴로 복사해주세요.';
    }
  }

  function render() {
    return `<section class="report-workbench" id="report-workbench"><div class="report-editor"><div class="report-editor-heading"><div><div class="eyebrow">ONE-PAGE DAILY REPORT</div><h2>오늘의 일을 한 장에.</h2><p>내용을 바꾸면 오른쪽 이미지에 반영됩니다.</p></div><span class="tag green">PNG</span></div><label class="report-date-label">보고 날짜<input type="date" data-report-field="date" value="${escape(model.date)}" aria-label="보고 날짜"></label><section class="report-edit-section"><div class="card-heading"><h3>01. 일일 진행사항</h3><span class="report-total" id="report-total">합계 ${duration(totalMinutes())}</span></div>${model.daily.map((row, index) => editorRow(row, index, 'daily')).join('')}<button type="button" class="report-add" data-report-action="add" data-group="daily" ${model.daily.length >= MAX_ROWS ? 'disabled' : ''}>＋ 진행사항 추가 <span>최대 ${MAX_ROWS}개</span></button></section><section class="report-edit-section"><div class="card-heading"><h3>02. 진행 예정사항</h3><span class="subtle-label">P1 → P2 → P3</span></div>${model.planned.map((row, index) => editorRow(row, index, 'planned')).join('')}<button type="button" class="report-add" data-report-action="add" data-group="planned" ${model.planned.length >= MAX_ROWS ? 'disabled' : ''}>＋ 예정사항 추가 <span>최대 ${MAX_ROWS}개</span></button></section><label class="report-note-label">공유·확인사항<textarea data-report-field="note" maxlength="240" rows="3" aria-label="공유 및 확인사항">${escape(model.note)}</textarea></label><p class="report-local-note">보고서 저장을 누르면 로컬 암호화 저장소에 보관합니다. 편집 후 저장해주세요.</p></div><aside class="report-image-panel" aria-label="일일 보고 이미지 미리보기"><div class="report-preview-heading"><span>한 장 미리보기</span><span>1200px · PNG</span></div><div class="report-preview-paper"><img id="report-preview" alt="일일 진행사항·소요시간, 예정사항·우선순위·예상시간·진행도와 whoiam 워터마크가 담긴 일일 보고 이미지" ${previewURL ? `src="${previewURL}"` : ''}></div><p class="report-validation" id="report-validation" role="status" aria-live="polite"></p><button class="button button-primary report-download" data-report-action="download">PNG 이미지 저장 <span>↓</span></button><button class="button button-outline report-download" data-report-action="preview">크게 보기</button><p class="report-local-note">시간은 직접 입력한 업무 소요시간의 합계입니다.<br>예상 소요시간과 진행도는 직접 입력한 계획 값입니다.</p>${messagePanel()}</aside></section>`;
  }

  function mount() {
    const root = document.getElementById('report-workbench');
    if (!root) return;
    root.addEventListener('input', event => {
      const input = event.target.closest('[data-report-field]');
      if (!input) return;
      const key = input.dataset.reportField;
      if (input.dataset.reportGroup) {
        const row = model[input.dataset.reportGroup][Number(input.dataset.reportIndex)];
        row[key] = ['minutes', 'estimated_minutes', 'progress'].includes(key) ? (input.value === '' ? null : Number(input.value)) :
          input.value;
      } else model[key] = input.value;
      document.dispatchEvent(new CustomEvent('whoiam-report-change'));
      document.getElementById('report-total').textContent = `합계 ${duration(totalMinutes())}`;
      updateMessage();
      clearTimeout(timer);
      timer = setTimeout(updatePreview, 160);
    });
    updatePreview();
  }

  function wrap(ctx, value, width) {
    const lines = [];
    for (const paragraph of String(value || '').split('\n')) {
      let line = '';
      for (const char of Array.from(paragraph)) {
        if (line && ctx.measureText(line + char).width > width) {
          lines.push(line);
          line = char;
        } else line += char;
      }
      lines.push(line);
    }
    return lines;
  }

  function paint() {
    const canvas = document.createElement('canvas');
    canvas.width = 1200;
    const ctx = canvas.getContext('2d');
    if (!ctx) throw new Error('Canvas is unavailable.');
    const font = '"Malgun Gothic", "Apple SD Gothic Neo", system-ui, sans-serif';
    const setFont = (size = 22, weight = 400) => {
      ctx.font = `${weight >= 600 ? 'bold' : 'normal'} ${size}px ${font}`;
    };
    const prepareRows = (rows, columns) => rows.map(row => {
      setFont(23, 650);
      const title = wrap(ctx, row.title, columns[1] - 38);
      setFont(19);
      const detail = row.detail ? wrap(ctx, row.detail, columns[1] - 38) : [];
      return {
        ...row,
        titleLines: title,
        detailLines: detail,
        height: Math.max(102, 34 + title.length * 31 + detail.length * 27)
      };
    });
    const dailyColumns = [56, 600, 168, 232];
    const plannedColumns = [56, 574, 178, 248];
    const daily = prepareRows(model.daily, dailyColumns);
    const planned = prepareRows([...model.planned].sort((a, b) => a.priority.localeCompare(b
      .priority)), plannedColumns);
    setFont(21);
    const noteLines = wrap(ctx, model.note.trim() || '별도 공유사항이 없습니다.', 1000);
    const dailyHeight = Math.max(102, daily.reduce((sum, row) => sum + row.height, 0));
    const plannedHeight = Math.max(102, planned.reduce((sum, row) => sum + row.height, 0));
    const bodyEnd = 408 + 91 + dailyHeight + 54 + 91 + plannedHeight + 44 + 68 + noteLines
      .length * 30 + 32;
    const height = Math.max(1600, bodyEnd + 150);
    if (height > 30000) throw new Error('한 장 이미지의 높이 한도에 도달했습니다. 상세내용을 줄여주세요.');
    canvas.height = height;
    // Canvas 크기를 바꾸면 그리기 상태가 초기화된다.
    ctx.textBaseline = 'top';
    const C = {
      ink: '#233d33',
      muted: '#7b897f',
      line: '#dce4da',
      pale: '#f0f4ed',
      green: '#214e42'
    };
    const text = (value, x, y, size = 22, weight = 400, color = C.ink) => {
      setFont(size, weight);
      ctx.fillStyle = color;
      ctx.fillText(String(value), x, y);
    };
    const line = (x, y, width, color = C.line) => {
      ctx.fillStyle = color;
      ctx.fillRect(x, y, width, 1);
    };
    const rounded = (x, y, w, h, radius, color) => {
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.roundRect(x, y, w, h, radius);
      ctx.fill();
    };
    const pill = (label, x, y, width, color, background) => {
      rounded(x, y, width, 35, 6, background);
      setFont(17, 650);
      ctx.fillStyle = color;
      ctx.fillText(label, x + (width - ctx.measureText(label).width) / 2, y + 7);
    };

    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = C.green;
    ctx.fillRect(0, 0, 1200, 12);
    text('WHOIAM  /  DAILY WORK REPORT', 72, 55, 17, 650, C.muted);
    text('일일 업무보고', 72, 100, 53, 750);
    const dateLabel = `${model.date.replaceAll('-', '.')}  ${weekday(model.date)}요일`;
    text(dateLabel, 75, 175, 22, 450, C.muted);
    text('업무의 진행과 다음 한 걸음', 795, 175, 19, 450, C.muted);
    rounded(72, 237, 1056, 116, 12, C.pale);
    const completed = model.daily.filter(row => row.status === '완료').length;
    const metrics = [
      ['입력한 소요시간 합계', duration(totalMinutes())],
      ['오늘 진행한 업무', `${model.daily.length}건 · 완료 ${completed}건`],
      ['다음 예정 업무', `${model.planned.length}건`]
    ];
    metrics.forEach(([label, value], index) => {
      const x = 98 + index * 352;
      text(label, x, 257, 17, 450, C.muted);
      text(value, x, 290, 29, 700);
      if (index < 2) {
        ctx.fillStyle = '#d9e2d3';
        ctx.fillRect(x + 309, 262, 1, 62);
      }
    });

    function table(y, number, title, rows, columns, headers, isPlan) {
      text(number, 72, y, 20, 650, '#90a082');
      text(title, 120, y - 3, 28, 700);
      text(`${rows.length}개 업무`, 1030, y + 5, 17, 450, C.muted);
      y += 47;
      ctx.fillStyle = C.pale;
      ctx.fillRect(72, y, 1056, 44);
      let x = 72;
      headers.forEach((header, index) => {
        text(header, x + (index === 0 ? 16 : 19), y + 12, 17, 600, '#667e5e');
        x += columns[index];
      });
      y += 44;
      if (!rows.length) {
        text('등록된 업무가 없습니다.', 98, y + 39, 21, 400, C.muted);
        line(72, y + 101, 1056);
        return y + 102;
      }
      rows.forEach((row, index) => {
        if (index % 2 === 1) {
          ctx.fillStyle = '#fafbf8';
          ctx.fillRect(72, y, 1056, row.height);
        }
        let x = 72;
        text(String(index + 1).padStart(2, '0'), x + 16, y + 28, 17, 450, '#a1ad98');
        x += columns[0];
        let textY = y + 23;
        row.titleLines.forEach(value => {
          text(value, x + 19, textY, 23, 650);
          textY += 31;
        });
        row.detailLines.forEach(value => {
          text(value, x + 19, textY + 4, 19, 400, C.muted);
          textY += 27;
        });
        x += columns[1];
        if (isPlan) {
          const colors = {
            P1: ['#934747', '#fbe4e4'],
            P2: ['#826315', '#fff2c7'],
            P3: ['#3f648c', '#e2edfb']
          };
          pill(`${row.priority} · ${priorityLabels[row.priority]}`, x + 18, y + 26, 122, ...
            colors[row.priority]);
          x += columns[2];
          text(row.estimated_minutes === null ? '예상 미입력' : `예상 ${row.estimated_minutes}분`, x + 19, y + 24, 20, 600);
          text(`진행도 ${row.progress}%`, x + 19, y + 53, 19, 400, C.muted);
        } else {
          pill(row.status, x + 17, y + 26, 112, row.status === '완료' ? '#4f7759' : '#a8793e',
            row.status === '완료' ? '#eaf1e5' : '#faf1e3');
          x += columns[2];
          text(duration(row.minutes), x + 19, y + 29, 22, 600, row.minutes === null ? C
            .muted : C.ink);
        }
        line(72, y + row.height - 1, 1056);
        // 긴 표에서도 열을 구분할 수 있도록 세로 구분선을 그린다.
        let boundary = 72;
        columns.slice(0, -1).forEach(width => {
          boundary += width;
          ctx.fillStyle = '#e9eee5';
          ctx.fillRect(boundary, y, 1, row.height);
        });
        y += row.height;
      });
      return y;
    }

    let y = table(408, '01', '일일 진행사항', daily, dailyColumns, ['#', '진행사항 · 결과', '상태', '소요시간'],
      false);
    y = table(y + 54, '02', '진행 예정사항', planned, plannedColumns, ['#', '예정 업무 · 다음 행동', '우선순위',
      '예상시간 / 진행도'
    ], true);
    y += 44;
    text('공유·확인사항', 72, y, 23, 650);
    y += 43;
    noteLines.forEach(value => {
      text(value, 72, y, 21, 400, C.muted);
      y += 30;
    });
    const footerY = canvas.height - 108;
    line(72, footerY, 1056);
    text('소요시간·예상시간·진행도: 직접 입력 기준', 72, footerY + 27, 15, 400, '#8b9983');
    // 워터마크를 이미지 픽셀에 포함한다.
    const attribution = '오동걸 업무비서 whoiam';
    const versionCredit = `버전 ${REPORT_VERSION} · powered by codex`;
    setFont(14, 500);
    text(attribution, 1128 - ctx.measureText(attribution).width, footerY + 24, 14, 500,
    '#858c82');
    setFont(12, 400);
    text(versionCredit, 1128 - ctx.measureText(versionCredit).width, footerY + 46, 12, 400,
      '#9a9f96');
    return canvas;
  }

  async function makeImage() {
    const message = validationMessage();
    if (message) throw new Error(message);
    if (document.fonts) await document.fonts.ready;
    return paint().toDataURL('image/png');
  }

  function setValidation(message) {
    const element = document.getElementById('report-validation');
    if (element) element.textContent = message;
    document.querySelectorAll('[data-report-action="download"], [data-report-action="preview"]')
      .forEach(button => {
        button.disabled = Boolean(message);
      });
  }

  async function updatePreview() {
    const ticket = ++generation;
    try {
      const url = await makeImage();
      if (ticket !== generation) return;
      previewURL = url;
      const image = document.getElementById('report-preview');
      if (image) {
        image.src = url;
        image.hidden = false;
      }
      setValidation('');
    } catch (error) {
      if (ticket !== generation) return;
      const image = document.getElementById('report-preview');
      if (image) image.hidden = true;
      setValidation(error.message || '이미지를 준비하지 못했습니다.');
    }
  }

  async function preview() {
    try {
      previewURL = await makeImage();
      let dialog = document.getElementById('report-image-dialog');
      if (!dialog) {
        dialog = document.createElement('dialog');
        dialog.id = 'report-image-dialog';
        dialog.setAttribute('aria-label', '일일 업무보고 한 장 이미지');
        dialog.addEventListener('click', event => {
          if (event.target === dialog) dialog.close();
        });
        document.body.append(dialog);
      }
      dialog.innerHTML =
        `<div class="report-modal-toolbar"><strong>일일 업무보고</strong><div><button class="button button-primary" data-report-action="download">PNG 저장 ↓</button><button class="button button-outline" data-report-action="close-preview">닫기</button></div></div><img src="${previewURL}" alt="일일 업무보고 전체 이미지">`;
      if (!dialog.open) dialog.showModal();
    } catch (error) {
      setValidation(error.message || '이미지를 준비하지 못했습니다.');
    }
  }

  async function download(button) {
    button.disabled = true;
    try {
      const url = await makeImage();
      const link = document.createElement('a');
      link.href = url;
      link.download = `WHOIAM_daily-report_${model.date}.png`;
      document.body.append(link);
      link.click();
      link.remove();
    } catch (error) {
      setValidation(error.message || '이미지를 저장하지 못했습니다.');
    } finally {
      button.disabled = Boolean(validationMessage());
    }
  }

  function handleAction(button) {
    const action = button.dataset.reportAction;
    if (!action) return false;
    if (action === 'preview') preview();
    if (action === 'download') download(button);
    if (action === 'copy-message') copyMessage();
    if (action === 'close-preview') document.getElementById('report-image-dialog')?.close();
    if (action === 'add' || action === 'remove') {
      const group = button.dataset.group;
      if (!['daily', 'planned'].includes(group)) return true;
      if (action === 'remove') model[group].splice(Number(button.dataset.index), 1);
      else if (model[group].length < MAX_ROWS) model[group].push(group === 'daily' ? {
        title: '',
        detail: '',
        minutes: null,
        status: '진행 중'
      } : {
        title: '',
        detail: '',
        priority: 'P2',
        estimated_minutes: null,
        progress: 0
      });
      document.dispatchEvent(new CustomEvent('whoiam-report-change'));
      const current = document.getElementById('report-workbench');
      if (current) {
        current.outerHTML = render();
        mount();
      }
    }
    return true;
  }

  function load(value) {
    generation += 1;
    clearTimeout(timer);
    model.date = value.date || '';
    model.daily = structuredClone(value.daily || []);
    model.planned = structuredClone(value.planned || []).map(row => ({...row, estimated_minutes: row.estimated_minutes ?? null, progress: row.progress ?? 0}));
    model.note = value.note || '';
    previewURL = '';
  }

  function getModel() {
    const message = validationMessage();
    if (message) throw new Error(message);
    return structuredClone({
      date: model.date,
      daily: model.daily,
      planned: model.planned,
      note: model.note
    });
  }
  window.WhoiamReport = Object.freeze({
    render,
    mount,
    preview,
    handleAction,
    load,
    getModel,
    reportMessage
  });
})();
