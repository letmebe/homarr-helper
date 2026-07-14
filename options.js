document.addEventListener('DOMContentLoaded', async () => {
  await window.I18N.initI18n();

  const langSelect = document.getElementById('langSelect');
  const urlInput = document.getElementById('homarrUrl');
  const keyInput = document.getElementById('apiKey');
  const boardSelect = document.getElementById('boardId');
  const saveBtn = document.getElementById('saveBtn');
  const testBtn = document.getElementById('testBtn');
  const status = document.getElementById('status');

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
    await loadBoards(stored.homarrUrl, stored.apiKey, stored.boardId);
  } else {
    boardSelect.innerHTML = `<option value="">${t('options_fill_first')}</option>`;
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
    if (type === 'success') {
      setTimeout(() => { status.className = 'status'; }, 3000);
    }
  }
});
