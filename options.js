document.addEventListener('DOMContentLoaded', async () => {
  await window.I18N.initI18n();

  const langSelect = document.getElementById('langSelect');
  const urlInput = document.getElementById('homarrUrl');
  const keyInput = document.getElementById('apiKey');
  const boardSelect = document.getElementById('boardId');
  const saveBtn = document.getElementById('saveBtn');
  const testBtn = document.getElementById('testBtn');
  const status = document.getElementById('status');
  let statusTimer = null; // 状态栏自动复位的定时器（声明须在 showStatus 被调用之前）

  // ── Host 权限：按用户填写的服务器地址动态申请（MV3 跨源 fetch 必需） ──
  function originPatternOf(baseUrl) {
    try {
      const u = new URL(baseUrl);
      if (u.protocol !== 'http:' && u.protocol !== 'https:') return null;
      return u.origin + '/*';
    } catch (e) {
      return null;
    }
  }

  // 浏览器要求 permissions.request 在用户手势中调用，因此只在按钮点击流程里使用。
  // 先 contains 再 request：已授权过就直接复用，浏览器不会再次弹窗。
  async function ensureHostPermission(baseUrl) {
    const pattern = originPatternOf(baseUrl);
    if (!pattern) return false;
    const granted = await chrome.permissions.contains({ origins: [pattern] });
    if (granted) return true;
    return await chrome.permissions.request({ origins: [pattern] });
  }

  // 更换服务器地址并保存成功后，清掉旧地址的残留授权（仅在保存流程调用）
  async function dropStalePermissions(currentPattern) {
    try {
      const all = await chrome.permissions.getAll();
      const stale = (all.origins || []).filter(p => p !== currentPattern);
      if (stale.length) await chrome.permissions.remove({ origins: stale });
    } catch (e) {
      // 清理失败不影响主流程
    }
  }

  // Load saved settings
  const stored = await chrome.storage.local.get({
    lang: 'auto',
    homarrUrl: '',
    apiKey: '',
    boardId: ''
  });

  langSelect.value = stored.lang;
  urlInput.value = stored.homarrUrl;
  keyInput.value = stored.apiKey;

  // Populate boards if we have connection info
  if (stored.homarrUrl && stored.apiKey) {
    const pattern = originPatternOf(stored.homarrUrl);
    if (pattern && !(await chrome.permissions.contains({ origins: [pattern] }))) {
      // 升级到按需授权版本后，旧安装可能还没有对应授权（也可能被用户在
      // chrome://extensions 里手动撤销），此时不会有弹窗，提示用户重新保存
      showStatus(t('options_perm_hint'), 'error');
    }
    await loadBoards(stored.homarrUrl, stored.apiKey, stored.boardId);
  } else {
    boardSelect.innerHTML = `<option value="">${t('options_fill_first')}</option>`;
  }

  // Auto-reload boards when URL or key changes (on blur)
  const refreshBoards = async () => {
    const url = urlInput.value.trim();
    const key = keyInput.value.trim();
    if (url && key) {
      const pattern = originPatternOf(url);
      if (pattern && !(await chrome.permissions.contains({ origins: [pattern] }))) {
        showStatus(t('options_perm_hint'), 'error');
        return;
      }
      await loadBoards(url, key, boardSelect.value);
    }
  };
  urlInput.addEventListener('blur', refreshBoards);
  keyInput.addEventListener('blur', refreshBoards);

  // Language change → save + reload page to apply
  langSelect.addEventListener('change', async () => {
    await chrome.storage.local.set({ lang: langSelect.value });
    location.reload();
  });

  // Save
  saveBtn.addEventListener('click', async () => {
    const settings = {
      lang: langSelect.value,
      homarrUrl: urlInput.value.trim().replace(/\/+$/, ''),
      apiKey: keyInput.value.trim(),
      boardId: boardSelect.value
    };

    if (!settings.homarrUrl || !settings.apiKey) {
      showStatus(t('options_error_fill'), 'error');
      return;
    }

    // 先申请新地址的授权（必须在用户手势内），成功后再清理旧地址的残留授权。
    // 顺序不能颠倒：否则用户拒绝授权时，当前仍在使用的旧地址权限已被误删，
    // 会出现「配置还是旧地址、但权限已丢」的静默失效状态。
    const granted = await ensureHostPermission(settings.homarrUrl);
    if (!granted) {
      showStatus(t('options_perm_denied'), 'error');
      return;
    }

    const pattern = originPatternOf(settings.homarrUrl);
    if (pattern) await dropStalePermissions(pattern);

    await chrome.storage.local.set(settings);
    showStatus(t('options_saved'), 'success');
  });

  // Test connection
  testBtn.addEventListener('click', async () => {
    const url = urlInput.value.trim().replace(/\/+$/, '');
    const key = keyInput.value.trim();

    if (!url || !key) {
      showStatus(t('options_error_fill'), 'error');
      return;
    }

    showStatus(t('options_testing'), 'loading');

    // 「测试连接」只申请、不清理：用户拿新地址试一下时，
    // 不应把当前已保存地址的授权拿走（存储里的地址仍然是旧的）
    const granted = await ensureHostPermission(url);
    if (!granted) {
      showStatus(t('options_perm_denied'), 'error');
      return;
    }

    try {
      const res = await fetch(url + '/api/boards', {
        headers: { 'ApiKey': key }
      });

      if (!res.ok) {
        const data = await res.json().catch(() => null);
        throw new Error(data?.message || `HTTP ${res.status}`);
      }

      const boards = await res.json();
      showStatus(t('options_test_success', [String(boards.length)]), 'success');

      // 测试连接成功即视为连接可用，顺手把面板列表填进下拉。
      // 首次配置时输入框的 blur 刷新会因尚未授权而提前返回（options_perm_hint），
      // 下拉只能保持「请先填写服务器地址和 API Key」，必须由这里补上。
      await loadBoards(url, key, boardSelect.value);
    } catch (err) {
      showStatus(t('options_test_failed', [err.message]), 'error');
    }
  });

  // Load boards into select
  async function loadBoards(baseUrl, apiKey, selectedId) {
    try {
      const res = await fetch(baseUrl.replace(/\/+$/, '') + '/api/boards', {
        headers: { 'ApiKey': apiKey }
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const boards = await res.json();
      boardSelect.innerHTML = `<option value="">${t('options_auto_home')}</option>`;
      for (const b of boards) {
        const opt = document.createElement('option');
        opt.value = b.id;
        opt.textContent = b.name + (b.isHome ? t('popup_home_suffix') : '');
        if (b.id === selectedId) opt.selected = true;
        boardSelect.appendChild(opt);
      }
    } catch (err) {
      boardSelect.innerHTML = `<option value="">${t('options_load_failed', [err.message])}</option>`;
    }
  }

  function showStatus(msgText, type) {
    status.textContent = msgText;
    status.className = 'status ' + type;
    if (statusTimer) clearTimeout(statusTimer);
    if (type === 'success') {
      statusTimer = setTimeout(() => { status.className = 'status'; }, 3000);
    }
  }
});
