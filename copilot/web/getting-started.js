/* First-run guidance uses real controls and checks, never simulated readiness. */
(() => {
  const $ = id => document.getElementById(id);
  const en = () => document.documentElement.lang === "en";
  const word = (english, russian) => en() ? english : russian;
  let current = {}, recording = false, starting = false;
  const labels = {
    "getting-started-open": ["Getting started", "Начать работу"],
    "getting-started-heading": ["Start using MeetOnTrack", "Начать работу с MeetOnTrack"],
    "getting-started-close": ["Close", "Закрыть"],
    "getting-started-intro": ["Start a call, see both sides in the transcript, then ask a question. Recording and local speech recognition need no paid API key. AI answers use the AI tool you choose below and its account limits.", "Начните звонок, увидьте обе стороны в стенограмме и задайте вопрос. Для записи и локальной расшифровки платный ключ не нужен. Ответы ИИ используют выбранный ниже инструмент ИИ и лимиты его аккаунта."],
    "startup-audio-heading": ["1. Prepare recording", "1. Подготовьте запись"],
    "startup-recorder": ["Open recorder / finish setup", "Открыть запись / закончить настройку"],
    "startup-ai-heading": ["2. Check AI answers", "2. Проверьте ответы ИИ"],
    "startup-ai-help": ["Choose the AI tool, model, effort and speed once. Every AI task uses this choice. The lists come from the tools installed on this computer and your plan. Check AI then sends a short test for each task, without meeting data, using a small part of your allowance.", "Выберите инструмент ИИ, модель, уровень рассуждений и скорость один раз. Все задачи ИИ используют этот выбор. Списки берутся из установленных на компьютере инструментов и вашего тарифа. Проверка ИИ отправит короткий тест для каждой задачи, без встреч и документов, и использует небольшую часть лимита."],
    "startup-ai-check": ["Check AI", "Проверить ИИ"],
    "ai-refresh": ["Refresh lists", "Обновить списки"],
    "startup-ai-login": ["Tool missing or unavailable? Install it, sign in there, then press Refresh lists.", "Инструмента нет или он недоступен? Установите его, войдите в него и нажмите «Обновить списки»."],
    "startup-context-heading": ["3. Add your context", "3. Добавьте свой контекст"],
    "startup-context-help": ["Connect a folder on your computer (Git is optional), or Google Drive. Files stay at the source; search uses current data when you ask. Calendar and Gmail can be enabled separately.", "Подключите папку на компьютере (Git не нужен) или Google Drive. Файлы остаются у источника; поиск читает актуальные данные при запросе. Календарь и почта включаются отдельно."],
    "startup-context": ["Connect context sources", "Подключить источники контекста"],
    "startup-google": ["Connect Google", "Подключить Google"],
    "startup-example-title": ["Example: a question with project context", "Пример: вопрос с контекстом проекта"],
    "startup-example-source": ["Example source, project.md: “The pilot supports CSV export.”", "Пример источника, project.md: «Пилот поддерживает экспорт CSV»."],
    "startup-example-question": ["During the call you ask: Can we promise PDF export?", "Во время звонка вы спрашиваете: Можем обещать экспорт PDF?"],
    "startup-example-answer": ["An answer grounded in that document: Only CSV is confirmed in project.md. PDF support needs checking. This is an illustrative example; connect your own sources for real answers.", "Ответ на основании документа: В project.md подтвержден только CSV. Поддержку PDF нужно уточнить. Это учебный пример; для реальных ответов подключите свои источники."],
    "context-folders-title": ["Folders on this computer", "Папки на этом компьютере"],
    "context-folders-help": ["Connect a project/documents folder, not the whole disk. Only its path is saved; files are read in place when AI searches, not uploaded or copied into this app. Up to 10 folders, active across meetings until disconnected. Matching excerpts go to your AI. Current search supports UTF-8 text, Markdown, CSV and source code; PDF/Office files are not read. Hidden files, credential filenames and symlinks are skipped. Search is bounded, not exhaustive.", "Подключите папку проекта или документов, не весь диск. Сохраняется только путь: при поиске ИИ файлы читаются на месте, не загружаются и не копируются в приложение. До 10 папок, действуют во всех встречах до отключения. Найденные фрагменты передаются вашему ИИ. Пока поиск читает UTF-8 текст, Markdown, CSV и исходный код; PDF/Office не читаются. Скрытые файлы, файлы с именами ключей/паролей и символические ссылки пропускаются. Поиск ограничен, не исчерпывающий."],
    "context-folder-add": ["Connect folder (read-only)", "Подключить папку (только чтение)"],
    "context-folder-choose": ["Choose folder…", "Выбрать папку…"],
    "context-folder-path-label": ["Or enter its absolute path", "Или укажите полный путь"],
    "context-google-open": ["Google Drive · connect / manage", "Google Drive · подключить / настроить"]
  };
  const errorText = text => {
    if (en()) return String(text).replace(/^AI_(?:LIMIT|LOGIN|UPDATE|MODEL|MISSING|NETWORK|FAILED|CHOICE|UNAVAILABLE):\s*/, "");
    const messages = {
      AI_LIMIT: "Лимит аккаунта ИИ исчерпан. Проверьте тариф или дождитесь сброса лимита, затем повторите запрос. Запись звука работает независимо.",
      AI_LOGIN: "Нужно войти в выбранный инструмент ИИ и повторить проверку. Запись звука работает независимо.",
      AI_UPDATE: "Инструмент ИИ устарел для выбранной модели. Обновите его или выберите другую модель, затем снова проверьте ИИ. Запись звука работает независимо.",
      AI_MODEL: "Провайдер ИИ отклонил выбранную модель. Возможно, ваш тариф ее не включает. Выберите другую модель в разделе «Начать работу». Запись звука работает независимо.",
      AI_MISSING: "Выбранный инструмент ИИ не установлен. Установите его и войдите или выберите другой. Для локальной записи и расшифровки ИИ не нужен.",
      AI_CHOICE: "Для этой задачи не выбраны инструмент и модель ИИ. Выберите их в разделе «Начать работу» и повторите. Запись звука работает независимо.",
      AI_NETWORK: "ИИ не ответил. Проверьте интернет и повторите запрос. Запись звука работает независимо.",
      AI_FAILED: "Запрос к ИИ завершился ошибкой. Проверьте доступ в разделе «Начать работу», затем повторите вопрос."
    };
    const code = String(text).split(":")[0];
    if (code === "AI_UNAVAILABLE") return "Выбранный ИИ сейчас недоступен: " + String(text).slice(code.length + 1).trim();
    return messages[code] || text;
  };
  async function api(path, data) {
    const response = await fetch(path, data === undefined ? {cache:"no-store"} : {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(data)});
    const result = await response.json();
    if (!response.ok || !result.ok) throw new Error(errorText(result.error || `HTTP ${response.status}`));
    return result;
  }
  function show() {
    $("getting-started").hidden = false;
    $("getting-started-open").setAttribute("aria-expanded", "true");
    void load();
  }
  function render() {
    for (const [id, texts] of Object.entries(labels)) $(id).textContent = texts[en() ? 0 : 1];
    $("startup-record").textContent = recording ? word("Recording is active", "Запись идет") : starting ? word("Waiting for recording…", "Жду начала записи…") : word("Start recording now", "Начать запись сейчас");
    $("startup-record").disabled = recording || starting || current.capture_installed === false;
    $("startup-audio-status").textContent = !current.capture_installed
      ? word("Recorder not found. Install MeetOnTrack from meetontrack.com.", "Приложение для записи не найдено. Запустите установщик с meetontrack.com.")
      : current.live_enabled
        ? word("Live transcription is enabled. Open the recorder to check permissions and model downloads. Start a call or use Start recording now.", "Расшифровка включена. В окне записи проверьте разрешения и загрузку моделей. Начните звонок или нажмите «Начать запись сейчас».")
        : word("Live transcription is off. Open the recorder, finish setup and enable it to get help during calls.", "Расшифровка во время звонка выключена. Откройте запись, закончите настройку и включите ее для помощи во время разговора.");
    const ai = current.ai || {};
    $("startup-ai-status").textContent = ai.state === "ready" ? word("AI answered successfully for every task. Account limits still apply.", "ИИ успешно ответил для всех задач. Лимиты аккаунта продолжают действовать.")
      : ai.state === "checking" ? word("Checking account and model access…", "Проверяю аккаунт и доступ к модели…")
      : ai.state === "partial" ? word("AI answered. Some tasks are unavailable with this choice; see the list below.", "ИИ ответил. Некоторые задачи недоступны с этим выбором, см. список ниже.")
      : ai.state === "needs_choice" ? word("Choose the AI tool and model, then check again.", "Выберите инструмент и модель ИИ и повторите проверку.")
      : ai.state === "error" ? errorText(ai.message) : word("Access has not been checked yet.", "Доступ еще не проверен.");
    renderAI();
    $("context-folder-list").replaceChildren(...(current.folders || []).map(doc => {
      const li = document.createElement("li"), remove = document.createElement("button");
      li.append(document.createTextNode(`${doc.name} — ${doc.path} `));
      remove.type = "button"; remove.className = "quiet-button"; remove.textContent = word("Disconnect", "Отключить");
      remove.addEventListener("click", async () => {
        remove.disabled = true;
        try {current.folders = (await api("/api/context-folders/remove", {id:doc.id})).folders; render();}
        catch(error) {$("context-folder-message").textContent = error.message; remove.disabled = false;}
      }); li.append(remove); return li;
    }));
  }
  /* The one AI choice, used by every task. Every option comes from the provider; nothing is preselected. */
  const purposes = {
    live_analysis: ["Live analysis and chat", "Анализ и чат во время звонка"],
    live_translation: ["Live translation", "Перевод во время звонка"],
    frame_relevance: ["Screenshot relevance", "Отбор снимков экрана"],
    summary_rewrite: ["Summary rewrite", "Переписывание итога"],
    summary: ["Meeting summary", "Итог встречи"],
    speaker_names: ["Speaker names", "Имена спикеров"]
  };
  let aiState = {providers: [], purposes: {}}, draft = null, edited = false;  // edited: the person changed the draft
  const options = {};
  const node = (tag, text) => {const item = document.createElement(tag); if (text) item.textContent = text; return item;};
  function picker(label, choices, value, change) {
    const wrap = node("label", label), list = node("select");
    for (const [id, name, disabled] of choices) {const option = node("option", name); option.value = id; option.disabled = Boolean(disabled); list.append(option);}
    list.value = value; list.addEventListener("change", () => change(list.value)); wrap.append(list); return wrap;
  }
  async function providerOptions(provider, refresh = false) {
    if (refresh || !options[provider]) {
      options[provider] = {state: "loading"};
      try {options[provider] = (await api(`/api/ai/options?provider=${encodeURIComponent(provider)}${refresh ? "&refresh=1" : ""}`)).options;}
      catch (error) {options[provider] = {state: "unavailable", reason: error.message};}
    }
    return options[provider];
  }
  function aiCard() {
    const status = aiState.choice || {};
    if (!edited) draft = {provider: "", model: "", effort: "", speed: "", ...(status.choice || {})};
    const box = node("fieldset"); box.className = "ai-purpose"; box.append(node("legend", word("AI for every task", "ИИ для всех задач")));
    const redraw = () => renderAI(), edit = () => {edited = true; renderAI();};
    box.append(picker(word("AI tool", "Инструмент ИИ"), [["", word("Choose…", "Выберите…")], ...aiState.providers.map(item => [item.provider, item.label])],
      draft.provider, value => {Object.assign(draft, {provider: value, model: "", effort: "", speed: ""}); edit();}));
    const found = draft.provider ? options[draft.provider] : null;
    if (draft.provider && !found) void providerOptions(draft.provider).then(redraw);
    let ready = false;
    if (found?.state === "loading" || (draft.provider && !found)) box.append(node("p", word("Reading what this tool offers…", "Читаю, что предлагает инструмент…")));
    else if (found?.state === "unavailable") box.append(node("p", word("Unavailable: ", "Недоступно: ") + found.reason));
    else if (found) {
      const model = found.models.find(item => item.id === draft.model && !item.problem);
      const name = item => item.problem ? `${item.label} (${item.problem})` : item.image === true ? item.label : `${item.label} (${word("no screenshots", "без снимков экрана")})`;
      box.append(picker(word("Model", "Модель"), [["", word("Choose…", "Выберите…")], ...found.models.map(item => [item.id, name(item), item.problem])],
        model ? draft.model : "", value => {Object.assign(draft, {model: value, effort: "", speed: ""}); edit();}));
      if (model?.efforts.length) box.append(picker(word("Effort", "Уровень рассуждений"), [["", word("Choose…", "Выберите…")], ...model.efforts.map(item => [item, item])],
        draft.effort, value => {draft.effort = value; edit();}));
      if (model?.speeds.length) box.append(picker(word("Speed", "Скорость"), [["", word("Choose…", "Выберите…")], ["standard", word("Standard", "Обычная")], ...model.speeds.map(item => [item.id, item.label])],
        draft.speed, value => {draft.speed = value; edit();}));
      if (model && !model.efforts.length) box.append(node("p", word("This model has no effort levels.", "У этой модели нет уровней рассуждений.")));
      if (model && !model.speeds.length) box.append(node("p", word("Speed: ", "Скорость: ") + model.speed_reason));
      if (found.plan) box.append(node("p", word("Plan: ", "Тариф: ") + found.plan));
      ready = Boolean(model) && (!model.efforts.length || draft.effort) && (!model.speeds.length || draft.speed);
    }
    const save = node("button", word("Save", "Сохранить")); save.type = "button"; save.className = "quiet-button"; save.disabled = !ready;
    save.addEventListener("click", async () => {
      save.disabled = true;
      try {await api("/api/ai/choice", {choice: draft}); await loadAI(true); $("ai-choice-message").textContent = word("Saved.", "Сохранено.");}
      catch (error) {$("ai-choice-message").textContent = error.message; redraw();}
    });
    box.append(save);
    const speedName = speed => speed === "standard" ? word("standard speed", "обычная скорость") : speed;
    const state = status.state === "ready" ? word("Saved: ", "Сохранено: ") + [status.choice.model, status.choice.effort, speedName(status.choice.speed)].filter(Boolean).join(", ")
      : status.state === "unavailable" ? word("Saved choice is unavailable: ", "Сохраненный выбор недоступен: ") + status.reason
      : status.choice ? word("Choice is not complete: ", "Выбор не закончен: ") + status.reason
      : word("Not chosen yet. AI does not run until you choose.", "Еще не выбрано. ИИ не работает, пока вы не выберете.");
    const line = node("p", state); line.setAttribute("role", "status"); box.append(line);
    // Each task with this choice: ready, unavailable with the reason, or the Check AI result.
    const tasks = node("ul");
    for (const [purpose, names] of Object.entries(purposes)) {
      const task = aiState.purposes[purpose] || {}, checked = (aiState.check?.purposes || {})[purpose];
      const text = task.state && task.state !== "ready" ? (task.state === "unavailable" ? word("unavailable: ", "недоступно: ") + task.reason : task.reason)
        : !checked || checked.state === "unchecked" ? word("not checked yet", "еще не проверено")
        : checked.state === "ready" ? word("ok", "работает") + (checked.message && !checked.message.startsWith("AI answered successfully") ? ". " + checked.message : "")
        : errorText(checked.message);
      tasks.append(node("li", `${word(...names)}: ${text}`));
    }
    box.append(tasks);
    return box;
  }
  function renderAI() {$("ai-card").replaceChildren(aiCard());}
  async function loadAI(saved) {try {aiState = await api("/api/ai"); if (aiState.check) current.ai = aiState.check; if (saved) edited = false; renderAI(); render();} catch (error) {$("ai-choice-message").textContent = error.message;}}
  $("ai-refresh").onclick = async () => {
    $("ai-refresh").disabled = true;
    try {await Promise.all(Object.keys(options).map(provider => providerOptions(provider, true))); await loadAI(true);}
    finally {$("ai-refresh").disabled = false;}
  };
  async function load() {try {current = await api("/api/getting-started"); render(); void loadAI();} catch(error) {$("startup-message").textContent = error.message;}}
  $("getting-started-open").onclick = show;
  $("getting-started-close").onclick = () => {$("getting-started").hidden = true; $("getting-started-open").setAttribute("aria-expanded","false"); localStorage.setItem("meetontrack-started", "1");};
  $("startup-context").onclick = () => $("repo-button").click();
  $("startup-google").onclick = () => {$("settings-open").click(); $("google-context-settings").open = true; $("google-context-settings").scrollIntoView({block:"nearest"});};
  $("startup-recorder").onclick = async () => {try {await api("/api/getting-started/open-recorder",{}); $("startup-message").textContent = word("Recorder opened. Finish setup there, then return here.", "Окно записи открыто. Завершите настройку там и вернитесь сюда.");} catch(error) {$("startup-message").textContent = error.message;}};
  $("startup-record").onclick = async () => {
    starting = true; render();
    try {await api("/api/getting-started/start-recording",{}); $("startup-message").textContent = word("Start requested. Waiting for audio confirmation…", "Начало запрошено. Жду подтверждения записи звука…");}
    catch(error) {starting = false; $("startup-message").textContent = error.message; render();}
    setTimeout(() => {if(starting && !recording) {starting=false; $("startup-message").textContent=word("Recording has not been confirmed. Open the recorder and check permissions.","Начало записи не подтверждено. Откройте окно записи и проверьте разрешения."); render();}},15000);
  };
  $("startup-ai-check").onclick = async () => {
    $("startup-ai-check").disabled = true; current.ai={state:"checking"}; render();
    try {current.ai=(await api("/api/getting-started/check-ai",{})).ai;}
    catch(error) {current.ai={state:"error",message:error.message};}
    finally {$("startup-ai-check").disabled=false; render(); void loadAI();}
  };
  $("context-google-open").onclick = () => { $("project-dialog").close(); $("startup-google").click(); };
  $("context-folder-choose").onclick = async () => {
    $("context-folder-choose").disabled = true;
    try {
      const result = await api("/api/context-folders/choose", {});
      if(result.path) { $("context-folder-path").value = result.path; $("context-folder-add").focus(); }
    } catch(error) { $("context-folder-message").textContent = error.message; }
    finally { $("context-folder-choose").disabled = false; }
  };
  $("context-folder-add").onclick = async () => {
    $("context-folder-add").disabled = true;
    try {
      current.folders = (await api("/api/context-folders/add", {path:$("context-folder-path").value})).folders;
      $("context-folder-path").value = "";
      $("context-folder-message").textContent = word("Connected. The next AI search will read current files in this folder.", "Подключено. Следующий поиск ИИ прочитает актуальные файлы в этой папке."); render();
    } catch(error) { $("context-folder-message").textContent = error.message; }
    finally { $("context-folder-add").disabled = false; }
  };
  // Anything that stops the app from doing its job gets a red banner above everything, with the one
  // button that fixes it, also during a recording (owner decision 2026-10-21: a call was recorded with
  // no speech recognition chosen and only a small grey label said so).
  const blockerState = {setup: null, speech: null, health: null, live: null, aiFailure: ""};
  let blockerSignature = "";
  function openStep(id) {show(); $(id).scrollIntoView({block: "start"});}
  async function openRecorder() {try {await api("/api/getting-started/open-recorder", {});} catch (error) {openStep("startup-audio-heading");}}
  function blockers() {
    const {setup, speech, health, live, aiFailure} = blockerState, found = [];
    if (setup?.capture_installed === false) found.push([word("The recorder is not installed. Calls are not recorded.", "Приложение для записи не установлено. Звонки не записываются."), word("How to install", "Как установить"), () => openStep("startup-audio-heading")]);
    else if (setup?.capture_running === false) found.push([word("The recorder is not running. Calls are not recorded.", "Приложение для записи не запущено. Звонки не записываются."), word("Start the recorder", "Запустить запись"), openRecorder]);
    if (health?.state === "action_required" && health.reason === "audio_track_stalled") found.push([word("Sound is not being recorded. Check the microphone and system audio permissions in the recorder.", "Звук не записывается. Проверьте разрешения на микрофон и системный звук в окне записи."), word("Open the recorder", "Открыть окно записи"), openRecorder]);
    if (health?.state === "action_required" && ["recognition_retries_exhausted", "recognition_resume_failed"].includes(health.reason) || live?.status === "error" && health?.capture?.audio_recording) found.push([word("Live transcription stopped and did not restart. There is no AI help during the call.", "Расшифровка во время звонка остановилась и не восстановилась. Подсказок ИИ во время звонка не будет."), word("Resume transcription", "Возобновить расшифровку"), () => $("recognition-resume").click()]);
    if (speech?.state === "needs_choice") found.push([word("Speech recognition is not set up. Calls are recorded, but there is no transcript and no AI help.", "Распознавание речи не настроено. Звонок записывается, но стенограммы и подсказок ИИ не будет."), word("Set up speech recognition", "Настроить распознавание"), () => openStep("speech-step")]);
    else if (speech?.state === "unavailable") found.push([word("Speech recognition does not work: ", "Распознавание речи не работает: ") + speech.reason + word(". There is no transcript and no AI help.", ". Стенограммы и подсказок ИИ не будет."), word("Fix speech recognition", "Исправить распознавание"), () => openStep("speech-step")]);
    // A choice that transcribes after the call can still be one the live recognizer cannot run.
    else if (live?.status === "unavailable") found.push([word("Live transcript is off: ", "Расшифровка во время звонка выключена: ") + (live.status_reason || "?") + word(". There is no AI help during the call.", ". Подсказок ИИ во время звонка не будет."), word("Fix speech recognition", "Исправить распознавание"), () => openStep("speech-step")]);
    const ai = setup?.ai || {};
    if (ai.state === "needs_choice") found.push([word("AI is not chosen. There is no AI help during calls.", "ИИ не выбран. Подсказок ИИ во время звонка не будет."), word("Choose AI", "Выбрать ИИ"), () => openStep("startup-ai-heading")]);
    else if (ai.state === "error") found.push([word("AI check failed: ", "Проверка ИИ не прошла: ") + errorText(ai.message || ""), word("Fix AI", "Исправить ИИ"), () => openStep("startup-ai-heading")]);
    else if (aiFailure) found.push([word("AI help failed: ", "Подсказки ИИ не работают: ") + errorText(aiFailure), word("Fix AI", "Исправить ИИ"), () => openStep("startup-ai-heading")]);
    return found;
  }
  function renderBlockers() {
    const found = blockers(), signature = JSON.stringify(found.map(([text, label]) => [text, label]));
    if (signature === blockerSignature) return;  // keeps the button under the pointer between polls
    blockerSignature = signature;
    $("blocker-banner").replaceChildren(...found.map(([text, label, fix]) => {
      const row = document.createElement("div"), strong = document.createElement("strong"), button = document.createElement("button");
      row.className = "blocker"; strong.textContent = text; button.type = "button"; button.textContent = label; button.onclick = fix;
      row.append(strong, button);
      return row;
    }));
    $("blocker-banner").hidden = !found.length;
  }
  async function refreshBlockers() {
    const [setup, speech] = await Promise.allSettled([api("/api/getting-started"), api("/api/stt")]);
    blockerState.setup = setup.status === "fulfilled" ? setup.value : null;
    blockerState.speech = speech.status === "fulfilled" ? speech.value.choice : null;
    renderBlockers();
  }
  window.renderGettingStartedStatus = data => {
    blockerState.health = data.recording_health || null;
    blockerState.live = data.transcript || null;
    blockerState.aiFailure = data.copilot?.error || (data.copilot?.analysis?.state === "error" ? data.copilot.analysis.message : "");
    renderBlockers();
    const wasRecording = recording;
    recording = Boolean(data.recording_health?.audio_recording);
    if(recording && starting) {starting=false; $("startup-message").textContent=word("Audio recording confirmed.","Запись звука подтверждена.");}
    if(wasRecording!==recording) render();
  };
  new MutationObserver(() => {render(); renderBlockers();}).observe(document.documentElement,{attributes:true,attributeFilter:["lang"]});
  window.addEventListener("focus", () => {if(!$("getting-started").hidden) void load(); void refreshBlockers();});
  void refreshBlockers();
  setInterval(refreshBlockers, 15000);
  $("repo-button").addEventListener("click", load);
  render();
  if(!localStorage.getItem("meetontrack-started")) show(); else void load();
})();
