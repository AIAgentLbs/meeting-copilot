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
    "startup-ai-help": ["Choose the AI tool, model, effort and speed for each task. The lists come from the tools installed on this computer and your plan. Check AI then sends a short test for each choice, without meeting data, using a small part of your allowance.", "Выберите для каждой задачи инструмент ИИ, модель, уровень рассуждений и скорость. Списки берутся из установленных на компьютере инструментов и вашего тарифа. Проверка ИИ отправит короткий тест для каждого выбора, без встреч и документов, и использует небольшую часть лимита."],
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
    "context-google-open": ["Google Drive · connect / manage", "Google Drive · подключить / настроить"],
    "assistant-problem-fix": ["Check AI / fix access", "Проверить ИИ / восстановить доступ"]
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
      : ai.state === "needs_choice" ? word("Choose a tool and model for every task, then check again.", "Выберите инструмент и модель для каждой задачи и повторите проверку.")
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
  /* AI choice per task. Every option comes from the provider; nothing is preselected. */
  const purposes = {
    live_analysis: ["Live analysis and chat", "Анализ и чат во время звонка"],
    live_translation: ["Live translation", "Перевод во время звонка"],
    frame_relevance: ["Screenshot relevance", "Отбор снимков экрана"],
    summary_rewrite: ["Summary rewrite", "Переписывание итога"],
    summary: ["Meeting summary", "Итог встречи"],
    speaker_names: ["Speaker names", "Имена спикеров"]
  };
  const needsImage = new Set(["frame_relevance"]);
  let aiState = {providers: [], purposes: {}}, drafts = {};
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
  function purposeRow(purpose) {
    const status = aiState.purposes[purpose] || {}, checked = (aiState.check?.purposes || {})[purpose];
    const draft = drafts[purpose] ||= {provider: "", model: "", effort: "", speed: "", ...(status.choice || {})};
    const box = node("fieldset"); box.className = "ai-purpose"; box.append(node("legend", word(...purposes[purpose])));
    const redraw = () => renderAI();
    box.append(picker(word("AI tool", "Инструмент ИИ"), [["", word("Choose…", "Выберите…")], ...aiState.providers.map(item => [item.provider, item.label])],
      draft.provider, value => {Object.assign(draft, {provider: value, model: "", effort: "", speed: ""}); redraw();}));
    const found = draft.provider ? options[draft.provider] : null;
    if (draft.provider && !found) void providerOptions(draft.provider).then(redraw);
    let ready = false;
    if (found?.state === "loading" || (draft.provider && !found)) box.append(node("p", word("Reading what this tool offers…", "Читаю, что предлагает инструмент…")));
    else if (found?.state === "unavailable") box.append(node("p", word("Unavailable: ", "Недоступно: ") + found.reason));
    else if (found) {
      // A model is offered only when discovery says it can do this task; otherwise it shows why not.
      const why = item => item.problem || (needsImage.has(purpose) && item.image !== true
        ? (item.image === false ? word("does not accept images", "не принимает изображения") : word("image input not reported", "прием изображений не указан")) : "");
      const model = found.models.find(item => item.id === draft.model && !why(item));
      box.append(picker(word("Model", "Модель"), [["", word("Choose…", "Выберите…")], ...found.models.map(item => [item.id, why(item) ? `${item.label} (${why(item)})` : item.label, why(item)])],
        model ? draft.model : "", value => {Object.assign(draft, {model: value, effort: "", speed: ""}); redraw();}));
      if (model?.efforts.length) box.append(picker(word("Effort", "Уровень рассуждений"), [["", word("Choose…", "Выберите…")], ...model.efforts.map(item => [item, item])],
        draft.effort, value => {draft.effort = value; redraw();}));
      if (model?.speeds.length) box.append(picker(word("Speed", "Скорость"), [["", word("Choose…", "Выберите…")], ["standard", word("Standard", "Обычная")], ...model.speeds.map(item => [item.id, item.label])],
        draft.speed, value => {draft.speed = value; redraw();}));
      if (model && !model.efforts.length) box.append(node("p", word("This model has no effort levels.", "У этой модели нет уровней рассуждений.")));
      if (model && !model.speeds.length) box.append(node("p", word("Speed: ", "Скорость: ") + model.speed_reason));
      if (found.plan) box.append(node("p", word("Plan: ", "Тариф: ") + found.plan));
      ready = Boolean(model) && (!model.efforts.length || draft.effort) && (!model.speeds.length || draft.speed);
    }
    const save = node("button", word("Save", "Сохранить")); save.type = "button"; save.className = "quiet-button"; save.disabled = !ready;
    save.addEventListener("click", async () => {
      save.disabled = true;
      try {await api("/api/ai/choice", {purpose, choice: draft}); await loadAI(); $("ai-choice-message").textContent = word("Saved.", "Сохранено.");}
      catch (error) {$("ai-choice-message").textContent = error.message; redraw();}
    });
    box.append(save);
    const speedName = speed => speed === "standard" ? word("standard speed", "обычная скорость") : speed;
    const state = status.state === "ready" ? word("Ready to use: ", "Готово к работе: ") + [status.choice.model, status.choice.effort, speedName(status.choice.speed)].filter(Boolean).join(", ")
      : status.state === "unavailable" ? word("Saved choice is unavailable: ", "Сохраненный выбор недоступен: ") + status.reason
      : status.choice ? word("Choice is not complete: ", "Выбор не закончен: ") + status.reason
      : word("Not chosen yet. AI does not run for this task until you choose.", "Еще не выбрано. ИИ не работает для этой задачи, пока вы не выберете.");
    const line = node("p", state); line.setAttribute("role", "status"); box.append(line);
    if (checked && status.state === "ready") box.append(node("p", checked.state === "ready" ? word("Check passed, model reported: ", "Проверка пройдена, модель: ") + checked.model
      : checked.state === "unchecked" ? word("Not checked with this choice yet.", "С этим выбором проверки еще не было.") : errorText(checked.message)));
    return box;
  }
  function renderAI() {$("ai-purposes").replaceChildren(...Object.keys(purposes).map(purposeRow));}
  async function loadAI() {try {aiState = await api("/api/ai"); if (aiState.check) current.ai = aiState.check; drafts = {}; renderAI(); render();} catch (error) {$("ai-choice-message").textContent = error.message;}}
  $("ai-refresh").onclick = async () => {
    $("ai-refresh").disabled = true;
    try {await Promise.all(Object.keys(options).map(provider => providerOptions(provider, true))); await loadAI();}
    finally {$("ai-refresh").disabled = false;}
  };
  async function load() {try {current = await api("/api/getting-started"); render(); void loadAI();} catch(error) {$("startup-message").textContent = error.message;}}
  $("getting-started-open").onclick = show;
  $("getting-started-close").onclick = () => {$("getting-started").hidden = true; $("getting-started-open").setAttribute("aria-expanded","false"); localStorage.setItem("meetontrack-started", "1");};
  $("assistant-problem-fix").onclick = show;
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
  window.renderGettingStartedStatus = data => {
    const wasRecording = recording;
    recording = Boolean(data.recording_health?.audio_recording);
    if(recording && starting) {starting=false; $("startup-message").textContent=word("Audio recording confirmed.","Запись звука подтверждена.");}
    const error=data.copilot?.error || (data.copilot?.analysis?.state==="error" ? data.copilot.analysis.message : "");
    $("assistant-problem").hidden=!error; $("assistant-problem-text").textContent=errorText(error);
    if(wasRecording!==recording) render();
  };
  new MutationObserver(render).observe(document.documentElement,{attributes:true,attributeFilter:["lang"]});
  window.addEventListener("focus", () => {if(!$("getting-started").hidden) void load();});
  $("repo-button").addEventListener("click", load);
  render();
  if(!localStorage.getItem("meetontrack-started")) show(); else void load();
})();
