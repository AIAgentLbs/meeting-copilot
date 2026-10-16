/* Release metadata only. Never executes an installer or interrupts capture. */
(() => {
  const find = id => document.getElementById(id);
  const copy = {
    en: {
      heading: "MeetOnTrack updates", help: "Checks published releases once a day. No meeting content or usage statistics are sent.",
      enabled: "Notify me about new versions", check: "Check for updates", checking: "Checking published releases…",
      unknown: "Installed version could not be identified. Reinstall from the official download to enable update checks.",
      error: "Could not check for updates. Try again when online. Recording is unaffected.",
      current: "Installed: {version} · {channel}", fresh: "No newer version found for this platform.", unchecked: "Not checked yet.",
      available: "Version {version} available", notes: "No release notes were provided.",
      link: "Open release and installation instructions", dismiss: "Dismiss notification",
      safe: "Opening the release does not install it. Finish your call before installing; recording will not be restarted automatically.",
      stable: "Stable channel", beta: "Beta channel", saveError: "Could not save the setting. Please try again."
    },
    ru: {
      heading: "Обновления MeetOnTrack", help: "Раз в день проверяет опубликованные релизы. Содержимое встреч и статистика использования не отправляются.",
      enabled: "Уведомлять о новых версиях", check: "Проверить обновления", checking: "Проверяю опубликованные релизы…",
      unknown: "Не удалось определить установленную версию. Переустановите приложение с официального сайта для проверки обновлений.",
      error: "Не удалось проверить обновления. Повторите при подключении к интернету. На запись это не влияет.",
      current: "Установлена: {version} · {channel}", fresh: "Более новой версии для этой платформы нет.", unchecked: "Проверка ещё не выполнялась.",
      available: "Доступна версия {version}", notes: "Описание изменений не опубликовано.",
      link: "Открыть релиз и инструкцию по установке", dismiss: "Скрыть уведомление",
      safe: "Открытие релиза ничего не устанавливает. Устанавливайте после звонка: автоматического перезапуска записи не будет.",
      stable: "Стабильные версии", beta: "Бета-версии", saveError: "Не удалось сохранить настройку. Попробуйте ещё раз."
    }
  };
  let state = {}, actionError = false;
  function render(data = state) {
    state = data;
    const text = copy[document.documentElement.lang === "ru" ? "ru" : "en"];
    for (const [id, key] of Object.entries({"updates-heading": "heading", "updates-help": "help", "updates-enabled-label": "enabled", "updates-safe-install": "safe", "updates-link": "link", "updates-dismiss": "dismiss"})) find(id).textContent = text[key];
    find("updates-enabled").checked = data.enabled !== false;
    find("updates-check").disabled = Boolean(data.checking || !data.version);
    find("updates-check").textContent = text[data.checking ? "checking" : "check"];
    const identity = text.current.replace("{version}", data.version || "—").replace("{channel}", text[data.channel === "technical-beta" ? "beta" : "stable"]);
    const status = !data.version ? text.unknown : data.checking ? text.checking : data.error ? text.error : !data.checked_at ? text.unchecked : !data.latest ? text.fresh : "";
    find("updates-status").textContent = `${identity}. ${actionError ? text.saveError : status}`;
    const latest = data.latest;
    const url = latest?.url || "";
    const trusted = /^https:\/\/github\.com\/AIAgentLbs\/meeting-copilot\/releases\/tag\/(?:windows-)?v\d+\.\d+\.\d+$/.test(url);
    find("updates-release").hidden = !latest || !trusted;
    find("updates-notice").hidden = !data.notify || !trusted;
    if (latest && trusted) {
      const label = text.available.replace("{version}", latest.version);
      find("updates-notice").textContent = label;
      find("updates-version").textContent = label;
      // Release notes are untrusted text, never HTML.
      find("updates-notes").textContent = latest.notes || text.notes;
      find("updates-link").href = url;
      find("updates-dismiss").hidden = !data.notify;
    } else {
      find("updates-link").removeAttribute("href");
      find("updates-notes").textContent = "";
    }
  }
  async function action(path, payload) {
    try {
      const response = await fetch(path, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(payload), signal: AbortSignal.timeout(12000)});
      if (!response.ok) throw new Error("request failed");
      const data = await response.json();
      actionError = false;
      render(data.updates);
    } catch (_) { actionError = true; render(); }
  }
  find("updates-notice").addEventListener("click", () => {
    find("settings-open").click();
    find("updates-settings").focus();
    find("updates-settings").scrollIntoView({block: "nearest"});
  });
  find("updates-check").addEventListener("click", () => void action("/api/updates/check", {}));
  find("updates-enabled").addEventListener("change", event => void action("/api/updates/settings", {enabled: event.target.checked}));
  find("updates-dismiss").addEventListener("click", () => void action("/api/updates/settings", {dismiss: state.latest?.version}));
  new MutationObserver(() => render()).observe(document.documentElement, {attributes: true, attributeFilter: ["lang"]});
  window.renderReleaseUpdates = render;
  render();
})();
