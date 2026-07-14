// i18n helper - processes data-i18n and data-i18n-* attributes in HTML
(function () {
  const msg = chrome.i18n.getMessage.bind(chrome.i18n);

  document.addEventListener('DOMContentLoaded', () => {
    // Set text content for elements with data-i18n
    document.querySelectorAll('[data-i18n]').forEach(el => {
      const key = el.getAttribute('data-i18n');
      const text = msg(key);
      if (text) el.textContent = text;
    });

    // Set title attribute for elements with data-i18n-title
    document.querySelectorAll('[data-i18n-title]').forEach(el => {
      const key = el.getAttribute('data-i18n-title');
      const text = msg(key);
      if (text) el.title = text;
    });

    // Set placeholder attribute for elements with data-i18n-placeholder
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
      const key = el.getAttribute('data-i18n-placeholder');
      const text = msg(key);
      if (text) el.placeholder = text;
    });

    // Set document title if <title> has data-i18n
    const titleEl = document.querySelector('title[data-i18n]');
    if (titleEl) {
      document.title = msg(titleEl.getAttribute('data-i18n'));
    }
  });
})();
