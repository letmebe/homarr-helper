// i18n-core.js — 国际化核心模块
// 加载语言资源，支持用户手动切换语言，默认跟随浏览器
// 兼容 extension pages (window) 和 service workers (self)

(function () {
  const scope = typeof window !== 'undefined' ? window : self;
  const caches = {};
  let currentLang = null;

  // 扫描 _locales 目录，发现所有可用语言
  async function discoverLocales() {
    // 尝试常见语言列表来发现 _locales 中实际存在的语言
    const candidates = ['zh_CN', 'zh_TW', 'en', 'ja', 'ko', 'fr', 'de', 'es', 'pt_BR', 'ru', 'ar'];
    const found = [];
    await Promise.all(candidates.map(async (locale) => {
      try {
        const res = await fetch(chrome.runtime.getURL(`_locales/${locale}/messages.json`));
        if (res.ok) {
          caches[locale] = await res.json();
          found.push(locale);
        }
      } catch (e) { /* 不存在则跳过 */ }
    }));
    return found;
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
    // 先预加载所有可用语言
    const available = await discoverLocales();

    const { lang = 'auto' } = await chrome.storage.local.get({ lang: 'auto' });

    let locale;
    if (lang === 'auto') {
      const browserLang = (chrome.i18n.getUILanguage() || 'en').replace(/-/g, '_');
      const prefix = browserLang.split('_')[0];
      // 精确匹配 → 语言前缀匹配 → 英文兜底
      if (available.includes(browserLang)) locale = browserLang;
      else if (available.includes(prefix)) locale = prefix;
      else locale = 'en';
    } else {
      // 用户指定的语言，确保已加载
      if (!caches[lang]) {
        try {
          const res = await fetch(chrome.runtime.getURL(`_locales/${lang}/messages.json`));
          if (res.ok) caches[lang] = await res.json();
        } catch (e) { /* fallback to en */ }
      }
      locale = caches[lang] ? lang : 'en';
    }

    currentLang = locale;
  }

  function getCurrentLang() {
    return currentLang;
  }

  scope.I18N = { t, initI18n, getCurrentLang, discoverLocales };
  scope.t = t;
})();
