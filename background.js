// Homarr Helper - Background Service Worker
// 响应 popup 发来的 API 请求

// 初始化 i18n（加载语言资源）
importScripts('i18n-core.js');
const _bgInit = self.I18N.initI18n();

// ── 监听来自 popup 的消息 ──
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === 'addToHomarr') {
    handleAdd(msg.data).then(sendResponse).catch(err => {
      sendResponse({ error: err.message });
    });
    return true;
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
  await _bgInit;
  const settings = await getSettings();

  if (!settings.homarrUrl || !settings.apiKey) {
    throw new Error(t('bg_error_no_config'));
  }

  const appPayload = {
    name: (data.name || 'Untitled').slice(0, 64),
    description: data.description || '',
    iconUrl: data.iconUrl || '',
    href: data.href || '',
    pingUrl: data.pingUrl || ''
  };

  const appResult = await apiCall(settings, 'POST', '/api/apps', appPayload);

  await apiCall(settings, 'POST', '/api/boards/items', {
    boardId: data.boardId,
    kind: 'app',
    options: { appId: appResult.appId },
    integrationIds: []
  });

  await chrome.storage.local.set({ lastUsedBoardId: data.boardId });

  return { success: true, appId: appResult.appId };
}

// ── 获取面板列表 ──
async function fetchBoards(data) {
  await _bgInit;
  const settings = await getSettings();
  if (!settings.homarrUrl || !settings.apiKey) {
    throw new Error(t('bg_error_no_server'));
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
    const message = (data && data.message) ? data.message : `HTTP ${res.status}`;
    throw new Error(message);
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
  _bgInit.then(() => {
    chrome.contextMenus.create({
      id: 'homarr-options',
      title: t('bg_context_menu'),
      contexts: ['action']
    });
  });
});

chrome.contextMenus.onClicked.addListener((info) => {
  if (info.menuItemId === 'homarr-options') {
    chrome.runtime.openOptionsPage();
  }
});
