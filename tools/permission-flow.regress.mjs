// 权限流程回归测试：验证「已授权不再弹窗」「拒绝授权不误删旧权限」两条关键性质
//
// 用法（Windows / Git Bash，需先关掉占用同一端口的一切进程）：
//   1) 启动带扩展的无头 Edge：
//      msedge.exe --headless=new --disable-gpu --remote-debugging-port=9242 \
//        --user-data-dir=<临时目录> --load-extension=<本仓库绝对路径> about:blank
//   2) PORT=9242 node tools/permission-flow.regress.mjs
//   期望输出：RESULT: 10 passed, 0 failed, 0 exceptions
const PORT = process.env.PORT || '9240';
const BASE = `http://127.0.0.1:${PORT}`;

async function listTargets() {
  return await (await fetch(`${BASE}/json/list`)).json();
}
function connect(wsUrl) {
  return new Promise((res, rej) => {
    const ws = new WebSocket(wsUrl);
    ws.onopen = () => res(ws);
    ws.onerror = () => rej(new Error('ws error'));
  });
}
let idc = 0;
function send(ws, method, params = {}, timeoutMs = 15000) {
  const id = ++idc;
  return new Promise((res, rej) => {
    const to = setTimeout(() => rej(new Error(`timeout ${method}`)), timeoutMs);
    const onMsg = (ev) => {
      const m = JSON.parse(ev.data);
      if (m.id === id) {
        clearTimeout(to);
        ws.removeEventListener('message', onMsg);
        m.error ? rej(new Error(method + ' -> ' + JSON.stringify(m.error))) : res(m.result);
      }
    };
    ws.addEventListener('message', onMsg);
    ws.send(JSON.stringify({ id, method, params }));
  });
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function waitTarget(pred, tries = 30) {
  for (let i = 0; i < tries; i++) {
    const t = (await listTargets()).find(pred);
    if (t) return t;
    await sleep(500);
  }
  return null;
}

const sw = await waitTarget((t) => t.type === 'service_worker' && t.url.includes('chrome-extension://'));
if (!sw) { console.log('FAIL: 未找到扩展 service worker'); process.exit(1); }

const swConn = await connect(sw.webSocketDebuggerUrl);
await send(swConn, 'Runtime.enable');
await send(swConn, 'Runtime.evaluate', { expression: 'chrome.runtime.openOptionsPage();' });

const opt = await waitTarget((t) => t.url.includes('chrome-extension://') && t.url.includes('options.html'));
if (!opt) { console.log('FAIL: 设置页未打开'); process.exit(1); }
const ws = await connect(opt.webSocketDebuggerUrl);
await send(ws, 'Runtime.enable');

const exceptions = [];
ws.addEventListener('message', (ev) => {
  const m = JSON.parse(ev.data);
  if (m.method === 'Runtime.exceptionThrown') {
    exceptions.push(m.params.exceptionDetails?.exception?.description || 'unknown');
  }
});

const ev = async (expression, userGesture = false) => {
  const r = await send(ws, 'Runtime.evaluate', {
    expression, awaitPromise: true, returnByValue: true, userGesture
  });
  if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || 'eval error');
  return r.result?.value;
};

const dom = await ev(`JSON.stringify({
  url: !!document.getElementById('homarrUrl'),
  save: !!document.getElementById('saveBtn'),
  test: !!document.getElementById('testBtn'),
  status: !!document.getElementById('status')
})`);
console.log('设置页 DOM:', dom);

// 埋点：统计 request / remove / storage.set 的调用
const INSTRUMENT = `
  window.__t = { request: 0, remove: [], getAll: 0, set: [] };
  const P = chrome.permissions;
  const _req = P.request.bind(P), _rem = P.remove.bind(P), _all = P.getAll.bind(P);
  P.request  = async (p) => { window.__t.request++;  return window.__REQ_RESULT; };
  P.remove   = async (p) => { window.__t.remove.push(...(p.origins||[])); return _rem(p); };
  P.getAll   = async ()     => { window.__t.getAll++; return { origins: window.__STALE, permissions: [] }; };
  const S = chrome.storage.local;
  const _set = S.set.bind(S);
  S.set = async (o) => { window.__t.set.push(Object.keys(o).join(',')); return _set(o); };
  'instrumented';
`;
await ev(INSTRUMENT);
await ev(`window.__REQ_RESULT = true; window.__STALE = ['http://192.168.1.99:7575/*']; 'ok'`);

const STUB_CONTAINS = (val) => `
  chrome.permissions.contains = async () => ${val};
  'stubbed contains=' + ${val};
`;

const clickSave = async (url) => {
  await ev(`(() => {
    document.getElementById('homarrUrl').value = ${JSON.stringify(url)};
    document.getElementById('apiKey').value = 'dummy-key';
    window.__t.request = 0; window.__t.remove = []; window.__t.set = [];
    document.getElementById('saveBtn').click();
    return 'clicked';
  })()`, true);
  await sleep(1200);
  return await ev(`JSON.stringify({
    status: document.getElementById('status').textContent.trim(),
    cls: document.getElementById('status').className,
    request: window.__t.request,
    remove: window.__t.remove,
    set: window.__t.set
  })`);
};

let pass = 0, fail = 0;
const check = (name, cond, detail) => {
  cond ? (pass++, console.log(`  ✅ ${name}`)) : (fail++, console.log(`  ❌ ${name}  -> ${detail}`));
};

// ── 用例 A：已授权 → 不应再调用 request（即不再弹窗） ──
console.log('\n[A] 地址已授权时点击保存');
await ev(STUB_CONTAINS(true));
let r = JSON.parse(await clickSave('http://192.168.1.10:7575'));
console.log('   ', r);
check('不再触发权限请求（无弹窗）', r.request === 0, `request=${r.request}`);
check('保存成功', r.set.length === 1 && /success/.test(r.cls), JSON.stringify(r));

// ── 用例 B：未授权 + 用户拒绝 → 不得删除旧权限、不得写入配置 ──
console.log('\n[B] 未授权且用户点了「拒绝」');
await ev(STUB_CONTAINS(false));
await ev(`window.__REQ_RESULT = false; 'deny'`);
r = JSON.parse(await clickSave('http://10.0.0.5:7575'));
console.log('   ', r);
check('发起了 1 次权限请求（弹窗 1 次）', r.request === 1, `request=${r.request}`);
check('没有误删仍在使用的旧地址权限', r.remove.length === 0, `remove=${JSON.stringify(r.remove)}`);
check('没有写入新配置', r.set.length === 0, `set=${JSON.stringify(r.set)}`);
check('给出了明确错误提示', r.status.length > 0 && /error/.test(r.cls), JSON.stringify(r));

// ── 用例 C：未授权 + 用户允许 → 写入配置并清理旧地址 ──
console.log('\n[C] 未授权且用户点了「允许」');
await ev(STUB_CONTAINS(false));
await ev(`window.__REQ_RESULT = true; 'allow'`);
r = JSON.parse(await clickSave('http://10.0.0.5:7575'));
console.log('   ', r);
check('发起了 1 次权限请求', r.request === 1, `request=${r.request}`);
check('保存成功', r.set.length === 1, JSON.stringify(r));
check('清理了旧地址的残留授权', r.remove.includes('http://192.168.1.99:7575/*'), JSON.stringify(r.remove));

// ── 用例 D：测试连接按钮不得撤销已保存地址的权限 ──
console.log('\n[D] 点击「测试连接」（试探一个新地址）');
await ev(STUB_CONTAINS(false));
await ev(`window.__REQ_RESULT = true; window.__t.request = 0; window.__t.remove = []; window.__t.set = []; 'reset'`);
await ev(`(() => {
  document.getElementById('homarrUrl').value = 'http://10.0.0.9:7575';
  document.getElementById('apiKey').value = 'dummy-key';
  document.getElementById('testBtn').click();
  return 'clicked';
})()`, true);
await sleep(1500);
const d = JSON.parse(await ev(`JSON.stringify({ request: window.__t.request, remove: window.__t.remove })`));
console.log('   ', d);
check('测试连接不删除任何已有权限', d.remove.length === 0, JSON.stringify(d.remove));

console.log(`\n页面异常数: ${exceptions.length}`);
exceptions.slice(0, 5).forEach((e) => console.log('  !', String(e).slice(0, 300)));
console.log(`\nRESULT: ${pass} passed, ${fail} failed, ${exceptions.length} exceptions`);
process.exit(fail === 0 && exceptions.length === 0 ? 0 : 2);
