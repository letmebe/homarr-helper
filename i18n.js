// i18n.js — HTML 国际化属性处理器
// 等待 i18n-core 初始化后，处理 data-i18n / data-i18n-title / data-i18n-placeholder

(function () {
  async function processAttributes() {
    await window.I18N.initI18n();

    // 设置文本内容
    document.querySelectorAll('[data-i18n]').forEach(el => {
      const text = window.t(el.getAttribute('data-i18n'));
      if (text) el.textContent = text;
    });

    // 设置 title 属性
    document.querySelectorAll('[data-i18n-title]').forEach(el => {
      const text = window.t(el.getAttribute('data-i18n-title'));
      if (text) el.title = text;
    });

    // 设置 placeholder 属性
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
      const text = window.t(el.getAttribute('data-i18n-placeholder'));
      if (text) el.placeholder = text;
    });

    // 设置 <title> 标签
    const titleEl = document.querySelector('title[data-i18n]');
    if (titleEl) {
      document.title = window.t(titleEl.getAttribute('data-i18n'));
    }
  }

  document.addEventListener('DOMContentLoaded', processAttributes);
})();
