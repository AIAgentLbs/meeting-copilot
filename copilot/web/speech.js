/* Speech recognition choice: every list comes from the recorder's own discovery, nothing is preselected. */
(() => {
  const $ = id => document.getElementById(id);
  const en = () => document.documentElement.lang === "en";
  const word = (english, russian) => en() ? english : russian;
  const labels = {
    "speech-heading": ["Speech recognition", "Распознавание речи"],
    "speech-help": ["Choose the model that turns speech into text during and after calls. The list comes from the recorder on this computer.", "Выберите модель, которая превращает речь в текст во время звонка и после него. Список берется из приложения записи на этом компьютере."],
    "speech-check": ["Check speech recognition", "Проверить распознавание"],
    "speech-refresh": ["Refresh lists", "Обновить списки"],
    "speech-deferred-heading": ["Recordings waiting for a transcript", "Записи, ожидающие расшифровки"]
  };
  const tags = {
    live: ["live", "во время звонка"], lowest_latency: ["lowest delay", "минимальная задержка"],
    multilingual: ["multilingual", "много языков"], offline: ["works offline", "без интернета"],
    speakers: ["identifies speakers", "различает спикеров"]
  };
  const kinds = {
    needs_choice: ["no speech recognition chosen", "распознавание не выбрано"],
    unavailable: ["engine or model unavailable", "движок или модель недоступны"],
    network: ["no network", "нет сети"]
  };
  let options = null, state = {}, draft = null, message = "", polling = 0, loading = false, lastCheck = null;
  const node = (tag, text) => {const item = document.createElement(tag); if (text) item.textContent = text; return item;};
  async function api(path, data) {
    const response = await fetch(path, data === undefined ? {cache: "no-store"} : {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(data)});
    const result = await response.json();
    if (!response.ok || !result.ok) throw apiError(result, response);
    return result;
  }
  function picker(label, choices, value, change) {
    const wrap = node("label", label), list = node("select");
    for (const [id, name, disabled] of choices) {const option = node("option", name); option.value = id; option.disabled = Boolean(disabled); list.append(option);}
    list.value = value; list.addEventListener("change", () => change(list.value)); wrap.append(list); return wrap;
  }
  function field(label, value, change, type = "text", commit = null) {
    const wrap = node("label", label), input = node("input"); input.type = type; input.value = value; input.autocomplete = "off";
    // No redraw on input: keeps focus and the next click (Save) on the same element.
    input.addEventListener("input", () => change(input.value.trim()));
    if (commit) input.addEventListener("change", commit);  // blur or Enter: the typed value is final
    wrap.append(input); return wrap;
  }
  const unknown = value => value === null || value === undefined;
  const mb = bytes => `${Math.round(bytes / 1e6)} MB`;
  // Where reusable files were found, named for a person; the full path goes in the tooltip.
  const source = path => /FluidVoice/i.test(path) ? "FluidVoice"
    : /\/\.cache\//.test(path) ? word("another app that uses the same speech models", "другом приложении с теми же моделями речи")
    : word("an older MeetOnTrack version", "более старой версии MeetOnTrack");
  // Never a bare size: what is on this Mac, what is still to fetch, or that nothing is.
  function onMac(item) {
    if (item.downloaded === true) return word("on this Mac", "на этом Mac");
    if (item.downloaded !== false) return "";
    const fetch = unknown(item.download_bytes)
      ? (unknown(item.size_bytes) ? word("download size unknown", "размер загрузки неизвестен") : word(`download size about ${mb(item.size_bytes)}`, `размер загрузки около ${mb(item.size_bytes)}`))
      : word(`download size ${mb(item.download_bytes)}`, `размер загрузки ${mb(item.download_bytes)}`);
    const found = (item.found_elsewhere || [])[0];
    if (!found) return fetch;
    const already = word(`already on this Mac (found in ${source(found.path)})`, `уже есть на этом Mac (найдена в ${source(found.path)})`);
    if (item.download_bytes === 0) return `${already}, ${word("ready to use, nothing to download", "готова к работе, загружать ничего не нужно")}`;
    if (unknown(item.download_bytes)) return `${already}, ${fetch}`;
    return `${already}, ${word(`needs a small update (download ${mb(item.download_bytes)})`, `нужно небольшое обновление (загрузка ${mb(item.download_bytes)})`)}`;
  }
  const reusable = item => item.download_bytes === 0 && (item.found_elsewhere || []).length > 0;
  const fetchLabel = (item, download) => reusable(item) ? word("Use it", "Использовать") : download;
  const engineOf = id => (options?.engines || []).find(item => item.id === id);
  function factsOf(engine, model) {
    if (!engine || !model) return null;  // free-text engines: the template's facts hold for any typed id
    return engine.model_entry === "free_text" ? engine.model_template || {} : (engine.models || []).find(item => item.id === model) || null;
  }
  // The recorder's name for a model (`name_parts`), composed in the page's
  // language the way the Mac windows compose it. Language names come from
  // Intl.DisplayNames. The picker leaves the languages to describe().
  function modelName(parts, languages = true) {
    if (!parts?.base) return "";
    const name = parts.variant ? `${parts.base}, ${parts.variant}` : parts.base;
    if (!languages) return name;
    if (parts.language) {
      let spoken = parts.language;
      try {spoken = new Intl.DisplayNames([document.documentElement.lang || "en"], {type: "language"}).of(parts.language) || spoken;} catch {}
      return `${name} (${spoken})`;
    }
    return parts.language_count > 1 ? `${name} (${word(`${parts.language_count} languages`, `языков: ${parts.language_count}`)})` : name;
  }
  function describe(model) {
    const parts = (model.best_for || []).map(tag => word(...(tags[tag] || [tag, tag])));
    parts.push(model.language_entry === "free_text" ? word("any language code", "любой код языка") : word(`${(model.languages || []).length} languages`, `языков: ${(model.languages || []).length}`));
    if (onMac(model)) parts.push(onMac(model));
    return parts.join(", ");
  }
  function job(model) {return (state.downloads || []).find(item => item.model === model);}
  function progress(item) {
    if (!item) return "";
    if (item.state === "error") return word("Download failed: ", "Загрузка не удалась: ") + plainError(item.message);
    if (item.state === "done") return word("Downloaded.", "Загружено.");
    const files = item.total_files ? ` (${item.completed_files}/${item.total_files})` : "";
    return word("Downloading ", "Загрузка ") + `${Math.round((item.fraction || 0) * 100)}%${files}`;
  }
  function downloadButton(facts, model) {
    const running = (state.downloads || []).some(item => item.state === "running" && item.model === model);
    const button = node("button", fetchLabel(facts, word("Download", "Загрузить"))); button.type = "button"; button.className = "quiet-button";
    button.disabled = running; button.title = (facts.found_elsewhere || []).map(item => item.path).join("\n");
    button.addEventListener("click", async () => {
      button.disabled = true;
      try {await api("/api/stt/download", {model}); await refreshState(); poll();}
      catch (error) {message = plainError(error); render();}
    });
    return button;
  }
  // The language is asked only when the model cannot settle it: it detects languages ("auto") or knows just one.
  function implied(facts) {
    if (!facts) return "";
    if (facts.auto_detect === true) return "auto";
    const languages = facts.language_entry === "free_text" ? [] : facts.languages || [];
    return languages.length === 1 ? languages[0] : "";
  }
  // Saved as soon as the choice is complete: no Save button, no confirmation.
  async function choose(changes) {
    Object.assign(draft, changes); render();
    if (!draft.engine || !draft.model || !draft.language) return;
    try {await api("/api/stt/choice", {choice: {engine: draft.engine, model: draft.model, language: draft.language}}); message = ""; lastCheck = null; await load(false, true);}
    catch (error) {message = plainError(error); render();}
  }
  function choiceBox() {
    const box = node("fieldset"); box.className = "ai-purpose"; box.append(node("legend", word("Speech model", "Модель распознавания")));
    if (!options) {box.append(node("p", loading ? word("Reading what the recorder offers…", "Читаю, что предлагает приложение записи…") : "")); return box;}
    if (!options.ok) {box.append(node("p", word("Unavailable: ", "Недоступно: ") + plainError(options.error))); return box;}
    // An engine that only lacks its key stays selectable, so the key can be entered.
    const selectable = item => item.available || (item.needs_key && item.has_key === false);
    box.append(picker(word("Engine", "Движок"), [["", word("Choose…", "Выберите…")], ...options.engines.map(item => [item.id, item.available ? item.label : `${item.label} (${item.reason})`, !selectable(item)])],
      selectable(engineOf(draft.engine) || {}) ? draft.engine : "", value => choose({engine: value, model: "", language: ""})));
    const engine = engineOf(draft.engine);
    if (!engine || !selectable(engine)) return box;
    if (engine.needs_key && engine.has_key !== true) {
      let key = "";
      box.append(field(word("API key", "Ключ API"), "", value => {key = value;}, "password"));
      const save = node("button", word("Save key", "Сохранить ключ")); save.type = "button"; save.className = "quiet-button";
      save.addEventListener("click", async () => {
        try {await api("/api/stt/key", {engine: engine.id, key}); message = ""; await load(true);}
        catch (error) {message = plainError(error); render();}
      });
      box.append(save);
    }
    if (!engine.available) return box;
    // A failed listing (bad key, network) is told apart from an empty list.
    if (engine.listing?.error) box.append(node("p", plainError(engine.listing.error)));
    let facts;
    if (engine.model_entry === "free_text") {
      facts = engine.model_template || {};
      box.append(field(word("Model id", "Идентификатор модели"), draft.model, value => {draft.model = value;}, "text",
        () => choose({language: draft.language || implied(facts)})));
    } else {
      const usable = (engine.models || []).find(item => item.id === draft.model && item.available);
      box.append(picker(word("Model", "Модель"), [["", word("Choose…", "Выберите…")], ...(engine.models || []).map(item => [item.id, item.available ? `${modelName(item.name_parts, false) || item.label} · ${describe(item)}` : `${modelName(item.name_parts) || item.label} (${item.reason})`, !item.available])],
        usable ? draft.model : "", value => choose({model: value, language: implied(factsOf(engine, value))})));
      facts = usable || null;
    }
    if (!facts || (engine.model_entry !== "free_text" && !draft.model)) return box;
    if (facts.live_reason) box.append(node("p", facts.live_reason));
    if (engine.kind === "local" && facts.downloaded === false) {
      box.append(downloadButton(facts, draft.model));
      const line = progress(job(draft.model)); if (line) box.append(node("p", line));
    }
    if (!implied(facts)) {
      if (facts.language_entry === "free_text") {
        box.append(field(word("Language code", "Код языка"), draft.language, value => {draft.language = value;}, "text", () => choose({})));
      } else {
        box.append(picker(word("Language", "Язык"), [["", word("Choose…", "Выберите…")], ...(facts.languages || []).map(item => [item, item])],
          draft.language, value => choose({language: value})));
      }
    }
    return box;
  }
  function statusText() {
    const choice = state.choice;
    // The recorder's names for the engine and the model, never their ids.
    const engine = choice && engineOf(choice.engine);
    const named = choice ? [engine?.label, modelName(state.name_parts), choice.language].filter(Boolean).join(", ") : "";
    if (state.state === "ready") return word("Ready: ", "Готово: ") + named;
    if (state.state === "unavailable") return word("Saved choice is unavailable: ", "Сохраненный выбор недоступен: ") + state.reason;
    if (state.state === "needs_choice") return choice ? word("Choice is not complete: ", "Выбор не закончен: ") + state.reason
      : word("Not chosen yet. Recordings are kept and transcribed once you choose.", "Еще не выбрано. Записи сохраняются и будут расшифрованы после выбора.");
    return state.reason || "";
  }
  function checkText() {
    const check = lastCheck || state.check;  // the reply to Check (maybe an unsaved draft), else the stored choice's
    if (!check) return "";
    if (check.ok) return word("Check passed, model used: ", "Проверка пройдена, модель: ") + (modelName(check.model_used_name_parts) || check.model_used_name || "");
    const failed = (check.steps || []).find(step => !step.ok);
    return word("Check failed: ", "Проверка не пройдена: ") + plainError(check.error || failed?.detail);
  }
  function deferredItem(item) {
    const li = node("li", `${item.session} · ${word(...(kinds[item.kind] || [item.kind, item.kind]))}${item.reason ? ": " + item.reason : ""} `);
    const run = (state.retranscribe || []).find(entry => entry.session === item.session);
    const button = node("button", word("Transcribe again", "Расшифровать снова")); button.type = "button"; button.className = "quiet-button";
    button.disabled = run?.state === "running" || state.state !== "ready";
    button.addEventListener("click", async () => {
      button.disabled = true;
      try {await api("/api/stt/retranscribe", {session: item.session}); await refreshState(); poll();}
      catch (error) {message = plainError(error); render();}
    });
    li.append(button);
    if (run) li.append(node("span", " " + (run.state === "running" ? word("Transcribing…", "Расшифровка…") : run.state === "done" ? word("Done.", "Готово.") : word("Failed: ", "Ошибка: ") + (run.stderr || run.exit_code))));
    return li;
  }
  function render() {
    for (const [id, texts] of Object.entries(labels)) $(id).textContent = texts[en() ? 0 : 1];
    $("speech-status").textContent = statusText();
    if (draft) $("speech-choice").replaceChildren(choiceBox());
    $("speech-message").textContent = [message, checkText()].filter(Boolean).join(" ");
    const deferred = state.deferred || [];
    $("speech-deferred-heading").hidden = !deferred.length;
    $("speech-deferred").replaceChildren(...deferred.map(deferredItem));
  }
  async function refreshState() {
    try {
      const reply = await api("/api/stt");  // status nested under "choice", like /api/ai
      state = {...reply.choice, downloads: reply.downloads, retranscribe: reply.retranscribe, check: reply.check};
    } catch (error) {message = plainError(error);}
    render();
  }
  async function load(refresh = false, resetDraft = false) {
    loading = true; render();
    try {options = await api(`/api/stt/options${refresh ? "?refresh=1" : ""}`);} catch (error) {options = {ok: false, error: plainError(error)};}
    loading = false;
    await refreshState();
    if (!draft || resetDraft) {
      const stored = state.choice || {};
      draft = {engine: stored.engine || "", model: stored.model || "", language: stored.language || ""};
    }
    render();
    // A page opened mid-download or mid-run follows it to the end.
    if ([...(state.downloads || []), ...(state.retranscribe || [])].some(item => item.state === "running")) poll();
    // A migrated choice may lack only the language the model implies; its
    // picker is hidden for such a model, so complete it here.
    const missing = draft.engine && draft.model && !draft.language && implied(factsOf(engineOf(draft.engine), draft.model));
    if (missing) await choose({language: missing});
  }
  function poll() {
    if (polling) return;
    polling = setInterval(async () => {
      const before = (state.downloads || []).filter(item => item.state === "running").length;
      await refreshState();
      const busy = [...(state.downloads || []), ...(state.retranscribe || [])].some(item => item.state === "running");
      if (before && !(state.downloads || []).some(item => item.state === "running")) await load();
      if (!busy) {clearInterval(polling); polling = 0;}
    }, 1500);
  }
  $("speech-check").addEventListener("click", async () => {
    $("speech-check").disabled = true; message = word("Checking…", "Проверяю…"); render();
    const complete = draft && draft.engine && draft.model && draft.language;
    try {lastCheck = (await api("/api/stt/check", complete ? {choice: {engine: draft.engine, model: draft.model, language: draft.language}} : {})).check; message = "";}
    catch (error) {message = plainError(error);}
    $("speech-check").disabled = false;
    await refreshState();
  });
  $("speech-refresh").addEventListener("click", () => load(true));
  new MutationObserver(render).observe(document.documentElement, {attributes: true, attributeFilter: ["lang"]});
  // Discovery runs only when Getting started is open.
  new MutationObserver(() => {if (!$("getting-started").hidden && !options) void load();}).observe($("getting-started"), {attributes: true, attributeFilter: ["hidden"]});
  render();
  if (!$("getting-started").hidden) void load();
})();
