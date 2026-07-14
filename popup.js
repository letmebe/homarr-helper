document.addEventListener('DOMContentLoaded', async () => {
  const formEl = document.getElementById('form');
  const actionsEl = document.getElementById('actions');
  const noticeEl = document.getElementById('notice');
  const statusEl = document.getElementById('status');

  const nameInput = document.getElementById('appName');
  const urlInput = document.getElementById('appUrl');
  const iconInput = document.getElementById('appIcon');
  const iconPreview = document.getElementById('iconPreview');
  const boardSelect = document.getElementById('boardSelect');
  const addBtn = document.getElementById('addBtn');
  const cancelBtn = document.getElementById('cancelBtn');
  const settingsBtn = document.getElementById('settingsBtn');
  const configLink = document.getElementById('configLink');

  const t = chrome.i18n.getMessage.bind(chrome.i18n);

  // ── 打开设置页 ──
  const openSettings = () => chrome.runtime.openOptionsPage();
  settingsBtn.addEventListener('click', openSettings);
  configLink.addEventListener('click', openSettings);
  cancelBtn.addEventListener('click', () => window.close());

  // ── 图标预览联动 ──
  iconInput.addEventListener('input', () => {
    iconPreview.src = iconInput.value || '';
  });

  // ── 检查配置 ──
  const settings = await chrome.runtime.sendMessage({ type: 'getSettings' });

  if (!settings.homarrUrl || !settings.apiKey) {
    formEl.style.display = 'none';
    actionsEl.style.display = 'none';
    noticeEl.style.display = 'block';
    return;
  }

  // ── 获取当前标签页信息 ──
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

  if (!tab || !tab.url || !tab.url.startsWith('http')) {
    formEl.style.display = 'none';
    actionsEl.style.display = 'none';
    noticeEl.style.display = 'block';
    noticeEl.textContent = t('popup_notice_unusable');
    return;
  }

  // 预填基本信息
  nameInput.value = tab.title || '';
  urlInput.value = tab.url;

  // ── 提取 favicon ──
  let favicon = tab.favIconUrl || '';
  try {
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => {
        const selectors = [
          'link[rel="apple-touch-icon"]',
          'link[rel="apple-touch-icon-precomposed"]',
          'link[rel="icon"][type="image/png"]',
          'link[rel="icon"][type="image/svg+xml"]',
          'link[rel="icon"]',
          'link[rel="shortcut icon"]'
        ];
        for (const sel of selectors) {
          const el = document.querySelector(sel);
          if (el && el.href) return el.href;
        }
        return null;
      }
    });
    if (results[0] && results[0].result) {
      favicon = results[0].result;
    }
  } catch (e) {
    // 某些页面无法注入脚本
  }

  // 最终 fallback
  if (!favicon) {
    try { favicon = new URL('/favicon.ico', tab.url).href; } catch {}
  }

  iconInput.value = favicon;
  iconPreview.src = favicon;

  // ── 加载面板列表 ──
  try {
    const resp = await chrome.runtime.sendMessage({ type: 'getBoards', data: {} });
    if (resp.error) throw new Error(resp.error);

    const boards = resp.boards;
    boardSelect.innerHTML = '';

    // 确定默认选中：设置中的 boardId > lastUsedBoardId > isHome > 第一个
    const defaultBoardId = settings.boardId || settings.lastUsedBoardId || '';

    for (const b of boards) {
      const opt = document.createElement('option');
      opt.value = b.id;
      opt.textContent = b.name + (b.isHome ? t('popup_home_suffix') : '');
      boardSelect.appendChild(opt);
    }

    // 选中默认面板
    if (defaultBoardId) {
      boardSelect.value = defaultBoardId;
    } else {
      // 自动选首页面板
      const home = boards.find(b => b.isHome);
      if (home) boardSelect.value = home.id;
    }
  } catch (err) {
    boardSelect.innerHTML = `<option value="">${t('popup_load_failed')}</option>`;
  }

  // 显示表单
  formEl.style.display = 'block';
  actionsEl.style.display = 'flex';

  // 聚焦到名称输入框
  nameInput.focus();
  nameInput.select();

  // ── 提交添加 ──
  addBtn.addEventListener('click', async () => {
    const name = nameInput.value.trim();
    const href = urlInput.value.trim();
    const iconUrl = iconInput.value.trim();
    const boardId = boardSelect.value;

    if (!name) { showStatus(t('popup_error_no_name'), 'error'); return; }
    if (!href) { showStatus(t('popup_error_no_url'), 'error'); return; }
    if (!boardId) { showStatus(t('popup_error_no_board'), 'error'); return; }

    addBtn.disabled = true;
    showStatus(t('popup_adding'), 'loading');

    try {
      const resp = await chrome.runtime.sendMessage({
        type: 'addToHomarr',
        data: {
          name,
          description: '',
          iconUrl: iconUrl || '',
          href,
          pingUrl: '',
          boardId
        }
      });

      if (resp.error) throw new Error(resp.error);

      showStatus(t('popup_success'), 'success');
      setTimeout(() => window.close(), 1200);
    } catch (err) {
      showStatus(t('popup_failed', [err.message]), 'error');
      addBtn.disabled = false;
    }
  });

  // Enter 键提交
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !addBtn.disabled) {
      addBtn.click();
    }
  });

  function showStatus(msgText, type) {
    statusEl.textContent = msgText;
    statusEl.className = 'status ' + type;
  }
});
