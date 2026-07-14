// i18n-core.js — 国际化核心模块
// 加载语言资源，支持用户手动切换语言，默认跟随浏览器
// 兼容 extension pages (window) 和 service workers (self)

(function () {
  const scope = typeof window !== 'undefined' ? window : self;
  const caches = {};
  let currentLang = null;

  async function loadLocale(locale) {
    if (caches[locale]) return caches[locale];
    const res = await fetch(chrome.runtime.getURL(`_locales/${locale}/messages.json`));
    caches[locale] = await res.json();
    return caches[locale];
  }

  function t(key, substitutions) {
    if (!currentLang) return key;
    const messages = caches[currentLang] || {};
    const entry = messages[key];
    if (!entry) return key;
    let text = entry.message;
    if (substitutions) {
      substitutions.forEach((val, i) => {
        text = text.replace(new RegExp(`\$${i + 1}\$`, 'g'), val);
      });
    }
    return text;
  }

  async function initI18n() {
    const { lang = 'auto' } = await chrome.storage.local.get({ lang: 'auto' });

    let locale;
    if (lang === 'auto') {
      const browserLang = (chrome.i18n.getUILanguage() || 'en').replace(/-/g, '_');
      const prefix = browserLang.split('_')[0];
      if (caches[browserLang]) locale = browserLang;
      else if (caches[prefix]) locale = prefix;
      else locale = 'en';
    } else {
      locale = lang;
    }

    await loadLocale(locale);
    currentLang = locale;
  }

  function getCurrentLang() {
    return currentLang;
  }

  scope.I18N = { t, initI18n, getCurrentLang, loadLocale };
  scope.t = t;
})();
