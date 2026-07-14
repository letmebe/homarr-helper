document.addEventListener('DOMContentLoaded', async () => {
  const urlInput = document.getElementById('homarrUrl');
  const keyInput = document.getElementById('apiKey');
  const boardSelect = document.getElementById('boardId');
  const saveBtn = document.getElementById('saveBtn');
  const testBtn = document.getElementById('testBtn');
  const status = document.getElementById('status');

  // Load saved settings
  const stored = await chrome.storage.local.get({
    homarrUrl: '',
    apiKey: '',
    boardId: ''
  });

  urlInput.value = stored.homarrUrl;
  keyInput.value = stored.apiKey;

  // Populate boards if we have connection info
  if (stored.homarrUrl && stored.apiKey) {
    await loadBoards(stored.homarrUrl, stored.apiKey, stored.boardId);
  } else {
    boardSelect.innerHTML = '<option value="">请先填写服务器地址和 API Key</option>';
  }

  // Auto-reload boards when URL or key changes (on blur)
  const refreshBoards = async () => {
    const url = urlInput.value.trim();
    const key = keyInput.value.trim();
    if (url && key) {
      await loadBoards(url, key, boardSelect.value);
    }
  };
  urlInput.addEventListener('blur', refreshBoards);
  keyInput.addEventListener('blur', refreshBoards);

  // Save
  saveBtn.addEventListener('click', async () => {
    const settings = {
      homarrUrl: urlInput.value.trim().replace(/\/+$/, ''),
      apiKey: keyInput.value.trim(),
      boardId: boardSelect.value
    };

    if (!settings.homarrUrl || !settings.apiKey) {
      showStatus('请填写服务器地址和 API Key', 'error');
      return;
    }

    await chrome.storage.local.set(settings);
    showStatus('设置已保存', 'success');
  });

  // Test connection
  testBtn.addEventListener('click', async () => {
    const url = urlInput.value.trim().replace(/\/+$/, '');
    const key = keyInput.value.trim();

    if (!url || !key) {
      showStatus('请先填写服务器地址和 API Key', 'error');
      return;
    }

    showStatus('测试中...', 'loading');

    try {
      const res = await fetch(url + '/api/boards', {
        headers: { 'ApiKey': key }
      });

      if (!res.ok) {
        const data = await res.json().catch(() => null);
        throw new Error(data?.message || `HTTP ${res.status}`);
      }

      const boards = await res.json();
      showStatus(`连接成功，发现 ${boards.length} 个面板`, 'success');
    } catch (err) {
      showStatus(`连接失败: ${err.message}`, 'error');
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
      boardSelect.innerHTML = '<option value="">自动 (首页面板)</option>';
      for (const b of boards) {
        const opt = document.createElement('option');
        opt.value = b.id;
        opt.textContent = b.name + (b.isHome ? ' (首页)' : '');
        if (b.id === selectedId) opt.selected = true;
        boardSelect.appendChild(opt);
      }
    } catch (err) {
      boardSelect.innerHTML = `<option value="">加载失败: ${err.message}</option>`;
    }
  }

  function showStatus(msg, type) {
    status.textContent = msg;
    status.className = 'status ' + type;
    if (type === 'success') {
      setTimeout(() => { status.className = 'status'; }, 3000);
    }
  }
});
