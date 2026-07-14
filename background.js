// Homarr Helper - Background Service Worker
// 响应 popup 发来的 API 请求

// ── 监听来自 popup 的消息 ──
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === 'addToHomarr') {
    handleAdd(msg.data).then(sendResponse).catch(err => {
      sendResponse({ error: err.message });
    });
    return true; // keep channel open for async response
  }
  if (msg.type === 'getSettings') {
    getSettings().then(sendResponse);
    return true;
  }
  if (msg.type === 'getBoards') {
    fetchBoards(msg.data).then(sendResponse).catch(err => {
      sendResponse({ error: err.message });
    });
    return true;
  }
});

// ── 核心：创建应用并添加到面板 ──
async function handleAdd(data) {
  const settings = await getSettings();

  if (!settings.homarrUrl || !settings.apiKey) {
    throw new Error('请先在设置中填写服务器地址和 API Key');
  }

  // 1. 创建应用
  const appPayload = {
    name: (data.name || 'Untitled').slice(0, 64),
    description: data.description || '',
    iconUrl: data.iconUrl || '',
    href: data.href || '',
    pingUrl: data.pingUrl || ''
  };

  const appResult = await apiCall(settings, 'POST', '/api/apps', appPayload);

  // 2. 添加到面板
  await apiCall(settings, 'POST', '/api/boards/items', {
    boardId: data.boardId,
    kind: 'app',
    options: { appId: appResult.appId },
    integrationIds: []
  });

  // 3. 记住上次使用的面板
  await chrome.storage.local.set({ lastUsedBoardId: data.boardId });

  return { success: true, appId: appResult.appId };
}

// ── 获取面板列表 ──
async function fetchBoards(data) {
  const settings = await getSettings();
  if (!settings.homarrUrl || !settings.apiKey) {
    throw new Error('未配置服务器');
  }
  const boards = await apiCall(settings, 'GET', '/api/boards');
  return { boards };
}

// ── API 请求 ──
async function apiCall(settings, method, path, body) {
  const url = settings.homarrUrl.replace(/\/+$/, '') + path;
  const opts = {
    method,
    headers: {
      'ApiKey': settings.apiKey,
      'Content-Type': 'application/json'
    }
  };
  if (body) opts.body = JSON.stringify(body);

  const res = await fetch(url, opts);
  const data = await res.json().catch(() => null);

  if (!res.ok) {
    const msg = (data && data.message) ? data.message : `HTTP ${res.status}`;
    throw new Error(msg);
  }
  return data;
}

// ── 读取设置 ──
async function getSettings() {
  const stored = await chrome.storage.local.get({
    homarrUrl: '',
    apiKey: '',
    boardId: ''
  });
  // 优先用上次使用的面板
  if (!stored.boardId) {
    const extra = await chrome.storage.local.get('lastUsedBoardId');
    if (extra.lastUsedBoardId) stored.boardId = extra.lastUsedBoardId;
  }
  return stored;
}

// ── 首次安装时打开设置页 ──
chrome.runtime.onInstalled.addListener((details) => {
  if (details.reason === 'install') {
    chrome.runtime.openOptionsPage();
  }
});

// ── 右键菜单快捷入口 ──
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: 'homarr-options',
    title: 'Homarr Helper 设置',
    contexts: ['action']
  });
});

chrome.contextMenus.onClicked.addListener((info) => {
  if (info.menuItemId === 'homarr-options') {
    chrome.runtime.openOptionsPage();
  }
});
