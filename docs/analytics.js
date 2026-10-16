/* Public website analytics only. Never load this in the local meeting UI. */
(() => {
  'use strict';
  if (!['meetontrack.com', 'www.meetontrack.com'].includes(location.hostname)) return;
  const key = 'meetontrack.analytics.v1';
  let choice;
  try { choice = localStorage.getItem(key); } catch (_) { /* Storage may be blocked. */ }
  let started = false;
  let config;
  const configUrl = new URL('analytics-config.json', document.currentScript.src);
  const ready = fetch(configUrl).then(r => r.ok ? r.json() : {}).catch(() => ({}));
  const ru = document.documentElement.lang === 'ru';
  const region = document.createElement('section');
  region.className = 'analytics-consent';
  region.setAttribute('aria-label', ru ? 'Настройки аналитики' : 'Analytics choices');
  region.hidden = true;
  const text = document.createElement('p');
  text.textContent = ru
    ? 'Разрешить аналитику сайта Umami и Google Analytics? Она помогает оценивать посещения и установку. Записи встреч не собираются. Можно отказаться или изменить выбор внизу страницы.'
    : 'Allow Umami and Google Analytics for website visits and install clicks? Meeting recordings are not collected. You can reject or change your choice in the footer.';
  region.append(text);
  for (const [value, label] of [
    ['denied', ru ? 'Без аналитики' : 'Reject analytics'],
    ['granted', ru ? 'Разрешить аналитику' : 'Allow analytics'],
  ]) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'button small';
    button.textContent = label;
    button.addEventListener('click', () => choose(value));
    region.append(button);
  }
  document.body.append(region);
  document.querySelectorAll('[data-analytics-settings]').forEach(button => {
    button.addEventListener('click', () => {
      region.hidden = false;
      region.querySelector('button').focus();
    });
  });
  function safeOrigin(value) {
    try { return new URL(value).origin; } catch (_) { return ''; }
  }
  function script(src) {
    const el = document.createElement('script');
    el.async = true;
    el.src = src;
    el.dataset.siteAnalytics = 'true';
    return el;
  }
  async function start() {
    config = await ready;
    if (choice !== 'granted' || started) return;
    started = true;
    if (/^G-[A-Z0-9]+$/.test(config.ga4 || '')) {
      window.dataLayer = window.dataLayer || [];
      window.gtag = function () { window.dataLayer.push(arguments); };
      window.gtag('consent', 'default', {
        analytics_storage: 'granted', ad_storage: 'denied',
        ad_user_data: 'denied', ad_personalization: 'denied',
      });
      window.gtag('js', new Date());
      window.gtag('config', config.ga4, {
        send_page_view: false, allow_google_signals: false,
        allow_ad_personalization_signals: false,
        page_location: location.origin + location.pathname,
        page_referrer: safeOrigin(document.referrer),
      });
      document.head.append(script('https://www.googletagmanager.com/gtag/js?id=' + config.ga4));
      window.gtag('event', 'page_view', {
        page_location: location.origin + location.pathname,
        page_referrer: safeOrigin(document.referrer),
      });
    }
    if (/^[0-9a-f-]{36}$/i.test(config.umamiWebsiteId || '') &&
        config.umamiScript === 'https://web-analytics.aiagentlbs.app/script.js') {
      const el = script(config.umamiScript);
      el.dataset.websiteId = config.umamiWebsiteId;
      el.dataset.autoTrack = 'false';
      el.dataset.domains = 'meetontrack.com,www.meetontrack.com';
      el.onload = () => {
        if (choice === 'granted') window.umami?.track(props => ({
          ...props, url: location.pathname, referrer: safeOrigin(document.referrer),
        }));
      };
      document.head.append(el);
    }
  }
  function choose(value) {
    choice = value;
    try { localStorage.setItem(key, value); } catch (_) { /* Keep the in-memory choice. */ }
    region.hidden = true;
    if (value === 'granted') { start(); return; }
    if (!started) return;
    if (config?.ga4) window['ga-disable-' + config.ga4] = true;
    for (const entry of document.cookie.split(';')) {
      const name = entry.trim().split('=')[0];
      if (!/^_ga(?:_|$)/.test(name)) continue;
      for (const domain of ['', '; Domain=' + location.hostname, '; Domain=.meetontrack.com']) {
        document.cookie = name + '=; Max-Age=0; Path=/' + domain + '; SameSite=Lax; Secure';
      }
    }
    // A reload removes already-loaded vendors and their listeners after revocation.
    location.reload();
  }
  document.addEventListener('click', event => {
    if (choice !== 'granted') return;
    const target = event.target.closest('[data-copy],a[href^="mailto:"]');
    if (!target) return;
    const name = target.matches('[data-copy]') ? 'install_click' : 'contact_click';
    const data = name === 'install_click'
      ? { platform: target.dataset.copy === 'windows-install-command' ? 'windows' : 'macos' }
      : {};
    window.gtag?.('event', name, data);
    window.umami?.track(name, data);
  });
  if (choice === 'granted') start();
  else if (choice !== 'denied') region.hidden = false;
})();
