(async () => {
  const content = document.getElementById('content');
  const loadingText = document.getElementById('loadingText');

  // Initialize i18n
  await window.I18N.initI18n();

  function showError(msg) {
    content.style.visibility = 'visible';
    content.innerHTML = `
      <div class="error-box">
        <div class="logo" style="width:36px;height:36px;margin:0 auto 12px;"></div>
        <div class="msg">${msg}</div>
        <a href="#" id="openSettings">${t('newtab_open_settings')}</a>
      </div>
    `;
    document.getElementById('openSettings').addEventListener('click', (e) => {
      e.preventDefault();
      chrome.runtime.openOptionsPage();
    });
  }

  function showPlaceholder() {
    content.style.visibility = 'visible';
    content.innerHTML = `
      <div class="logo"></div>
      <h2>Homarr Helper</h2>
      <p>${t('newtab_no_url')}</p>
      <a href="#" id="openSettings">${t('newtab_open_settings')}</a>
    `;
    document.getElementById('openSettings').addEventListener('click', (e) => {
      e.preventDefault();
      chrome.runtime.openOptionsPage();
    });
  }

  try {
    const settings = await chrome.storage.local.get({ homarrUrl: '' });

    if (!settings.homarrUrl) {
      // No Homarr URL configured — show placeholder
      showPlaceholder();
      return;
    }

    // Redirect to Homarr
    const targetUrl = settings.homarrUrl;
    loadingText.textContent = t('newtab_redirecting');

    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tabs && tabs.length > 0) {
      await chrome.tabs.update(tabs[0].id, { url: targetUrl });
    } else {
      window.location.href = targetUrl;
    }

  } catch (err) {
    console.error('[HomarrHelper newtab] error:', err);
    showError(t('newtab_error') + ': ' + err.message);
  }
})();
