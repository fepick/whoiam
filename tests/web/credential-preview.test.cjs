const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {test} = require('node:test');

function application() {
  const elements = new Map(), timers = new Map(), events = new Map();
  const element = id => {
    if (!elements.has(id)) elements.set(id, {
      innerHTML:'', textContent:'', open:false, addEventListener() {}, remove() {},
      showModal() {this.open=true;}, close() {this.open=false;},
      replaceChildren() {this.innerHTML='';},
    });
    return elements.get(id);
  };
  const document = {hidden:false, addEventListener:(key, fn)=>events.set(key,fn), getElementById:element};
  const context = vm.createContext({document,
    window:{addEventListener:(key,fn)=>events.set(key,fn),WhoiamReport:{load() {}}},
    location:{hash:''},URLSearchParams,setInterval() {},
    setTimeout:(fn,ms)=>{timers.set(fn,ms);return fn;},clearTimeout:id=>timers.delete(id),
    fetch:()=>new Promise(()=>{}),
  });
  vm.runInContext(fs.readFileSync(path.join(__dirname,'../../apps/web/app.js'),'utf8'),context);
  vm.runInContext("data={vault:[{id:'fake',kind:'credential',alias:'Sample'}]};connection.locked=false;",context);
  return {context,elements,element,timers,events,document};
}

test('로그인 원문은 텍스트로 표시하고 30초 후 대화상자를 비운다', async()=>{
  const {context,element,timers}=application();
  vm.runInContext("api=async()=>({username:'<img src=x>',password:'  synthetic-only  '})",context);
  await vm.runInContext("showCredential('fake')",context);
  assert.equal(element('credential-username').textContent,'<img src=x>');
  assert.equal(element('credential-password').textContent,'  synthetic-only  ');
  assert.doesNotMatch(element('credential-preview').innerHTML,/synthetic-only|<img/);
  assert.doesNotMatch(vm.runInContext('JSON.stringify(data)',context),/synthetic-only/);
  assert.equal([...timers.values()][0],30000);
  [...timers.keys()][0]();
  assert.equal(element('flow-dialog').open,false);
  assert.equal(element('dialog-content').innerHTML,'');
  assert.equal(timers.size,0);
});

test('조회 응답 전에 닫기·창 이동·잠금·탭 숨김 시 늦은 원문을 표시하지 않는다',async()=>{
  for (const action of ['close','blur','lock','hidden','pagehide']) {
    const app=application();const {context,elements,element,events}=app;
    vm.runInContext('api=()=>new Promise(resolve=>globalThis.complete=resolve)',context);
    const pending=vm.runInContext("showCredential('fake')",context);
    if(action==='close')vm.runInContext('closeDialog()',context);
    if(action==='lock')vm.runInContext('connection.locked=true;clearPrivateView()',context);
    if(action==='hidden'){app.document.hidden=true;events.get('visibilitychange')();}
    if(['blur','pagehide'].includes(action))events.get(action)();
    context.complete({username:'fake',password:'synthetic-only'});
    await pending;
    assert.equal(elements.has('credential-password'),false,action);
    assert.equal(element('flow-dialog').open,false,action);
  }
});

test('결제수단 참조와 개인정보도 한 건씩 텍스트로 표시한다', async()=>{
  for (const [kind,values] of [
    ['payment-method',{issuer:'가상 카드사',last_four:'1234',token:'<fake-token>'}],
    ['person',{name:'가상 사용자',email:'fake@example.invalid',phone:'000',address:'<가상 주소>'}],
  ]) {
    const {context,element}=application();
    context.kind=kind; context.values=values;
    vm.runInContext('data.vault[0].kind=kind;api=async()=>values;',context);
    await vm.runInContext("showCredential('fake')",context);
    for (const [key,value] of Object.entries(values)) assert.equal(element(`credential-${key}`).textContent,value);
    assert.doesNotMatch(element('credential-preview').innerHTML,/<fake-token>|<가상 주소>/);
  }
});

test('보관함은 별칭·마스킹 검색과 유형 필터를 조합하고 10건씩 표시한다',()=>{
  const {context}=application();
  vm.runInContext(`data.vault=Array.from({length:23},(_,i)=>({id:String(i),kind:i===22?'person':'credential',alias:'Sample '+String(i).padStart(2,'0'),hint:'••••'}));`,context);
  let html=vm.runInContext('vaultResults()',context);
  assert.equal((html.match(/data-action="reveal-secret"/g)||[]).length,10);
  assert.match(html,/1\/3쪽/);
  vm.runInContext('state.vaultPage=2',context);
  html=vm.runInContext('vaultResults()',context);
  assert.equal((html.match(/data-action="reveal-secret"/g)||[]).length,3);
  vm.runInContext("state.vaultKind='person';state.vaultQuery='sample 22';",context);
  html=vm.runInContext('vaultResults()',context);
  assert.match(html,/Sample 22/);
  assert.doesNotMatch(html,/Sample 21/);
  assert.match(html,/1\/1쪽/);
  vm.runInContext("state.vaultQuery='<missing>';",context);
  assert.match(vm.runInContext('vaultResults()',context),/조건에 맞는 항목이 없습니다/);
});
