/* Explicit delivery consent. Secrets are never returned to the browser or stored here. */
(() => {
  const $ = id => document.getElementById(id);
  const ru = () => document.documentElement.lang === "ru";
  const words = {
    heading:["Report storage and delivery","Хранение и доставка отчетов"],
    local:["Recordings and reports stay on this computer. Cloud connections are optional.","Записи и отчеты сохраняются на компьютере. Облачные сервисы подключать необязательно."],
    google:["Google account","Аккаунт Google"], account:["Account for Gmail and Google Drive","Аккаунт для Gmail и Google Drive"],
    accountHelp:["Connecting does not enable delivery. Context search is a separate permission.","Подключение аккаунта само по себе не включает отправку. Поиск контекста настраивается отдельно."],
    connect:["Connect Google","Подключить Google"], checkGoogle:["Check account","Проверить аккаунт"], disconnect:["Disconnect from MeetOnTrack","Отключить от MeetOnTrack"],
    mail:["Email after a meeting","Письмо после встречи"], autoMail:["Email reports automatically","Автоматически отправлять отчет по почте"],
    provider:["Send using","Способ отправки"], recipient:["Report recipient","Получатель отчета"],
    attachment:["The PDF is attached to the email. Google Drive is not required.","PDF прикладывается к письму. Google Drive для этого не нужен."],
    host:["SMTP server","SMTP-сервер"], port:["Port","Порт"], security:["Connection security","Защита соединения"],
    username:["SMTP username","Логин SMTP"], sender:["Sender address","Адрес отправителя"], password:["SMTP app password","Пароль приложения SMTP"],
    checkSmtp:["Check SMTP without sending email","Проверить SMTP без отправки письма"],
    autoDrive:["Save reports to Google Drive automatically","Автоматически сохранять отчет на Google Drive"],
    folder:["Google Drive folder link or ID","Ссылка или ID папки Google Drive"],
    autoTelegram:["Send to connected Telegram","Отправлять в подключенный Telegram"],
    consent:["Turning a channel off stops new sends and pending retries, not messages already sent. Enabling it does not backfill old meetings; send those from History.","Выключение канала останавливает новые отправки и ожидающие повторы, но не отзывает уже отправленное. После включения старые встречи автоматически не рассылаются: их можно отправить из истории."],
    save:["Save delivery settings","Сохранить настройки доставки"], saved:["Settings saved. No email was sent.","Настройки сохранены. Письмо не отправлялось."],
    noAccount:["Not connected","Не подключен"], sending:["Sending…","Отправляю…"],
    connected:["Connected","Подключено"], connecting:["Complete sign-in in your browser, then check the account.","Завершите вход в браузере, затем проверьте аккаунт."],
    done:["Delivery confirmed","Отправка подтверждена"], retry:["Retry email delivery","Повторить отправку письма"],
    resend:["Send email again","Отправить письмо еще раз"], retryDrive:["Retry Google Drive upload","Повторить загрузку на Google Drive"],
    retryTelegram:["Retry Telegram delivery","Повторить отправку в Telegram"],
    confirm:["Send this report again? It may already be in the recipient's inbox.","Отправить отчет еще раз? Он уже мог попасть в ящик получателя."],
    email:["Email","Почта"], drive:["Google Drive","Google Drive"], telegram:["Telegram","Telegram"],
    disabled:["Disabled or not connected","Выключено или не подключено"], sent:["Sent","Отправлено"],
    failed:["Not delivered. Check settings and retry.","Не доставлено. Проверьте настройки и повторите отправку."],
    unknown:["Delivery outcome unknown. Check your mailbox before retrying.","Результат отправки неизвестен. Проверьте почту перед повтором."],
    passwordSaved:["Password saved in the OS credential store. Leave blank to keep it.","Пароль сохранен в защищенном хранилище ОС. Оставьте поле пустым, чтобы сохранить его."],
    passwordHelp:["Stored in macOS Keychain / Windows DPAPI, not in settings or logs.","Хранится в macOS Keychain / Windows DPAPI, не в настройках или журналах."],
    telegramReady:["Uses the existing Telegram connection.","Используется существующее подключение Telegram."],
    telegramMissing:["Telegram is not connected on this computer. Email and local reports work independently.","Telegram не подключен на этом компьютере. Почта и локальные отчеты работают независимо."],
    googleMissing:["No named Google connector is configured on this computer. SMTP and local reports remain available.","На этом компьютере не настроен именованный Google-профиль. SMTP и локальные отчеты доступны независимо."],
    error:["Could not complete the operation. Check the connection and try again.","Не удалось выполнить действие. Проверьте подключение и повторите."],
  };
  const errors = {
    attachment_outside_working_directory:["Attachment directory error. Update MeetOnTrack and retry.","Ошибка папки вложения. Обновите MeetOnTrack и повторите."],
    permission_missing:["Google permission is missing. Reconnect the account.","Не хватает разрешений Google. Подключите аккаунт заново."],
    authorization_expired:["Authorization expired. Reconnect Google.","Авторизация истекла. Подключите Google заново."],
    authorization_required:["Sign in to the selected Google account.","Войдите в выбранный Google-аккаунт."],
    authorization_missing:["Connect Google in settings.","Подключите Google в настройках."],
    google_not_connected:["Select a Google account and save settings.","Выберите Google-аккаунт и сохраните настройки."],
    google_connector_missing:words.googleMissing,
    account_mismatch:["Account mismatch. Delivery stopped for safety.","Аккаунт не совпадает. Отправка остановлена для безопасности."],
    invalid_email:["Enter a valid email address.","Введите корректный адрес почты."],
    recipient_required:["Enter the report recipient.","Укажите получателя отчета."],
    drive_folder_required:["Choose a Google Drive folder.","Укажите папку Google Drive."],
    invalid_drive_folder:["Enter a Google Drive folder link or ID.","Введите ссылку или ID папки Google Drive."],
    smtp_settings_required:["Enter SMTP server, username and sender.","Укажите SMTP-сервер, логин и отправителя."],
    smtp_password_required:["Enter the SMTP app password.","Введите пароль приложения SMTP."],
    smtp_auth_failed:["SMTP rejected the login. Check the username and app password.","SMTP отклонил вход. Проверьте логин и пароль приложения."],
    smtp_connection_failed:["SMTP connection failed. Check server, port and TLS settings.","Не удалось подключиться к SMTP. Проверьте сервер, порт и TLS."],
    credential_store_unavailable:["OS credential store unavailable. The password was not saved.","Хранилище паролей ОС недоступно. Пароль не сохранен."],
    channel_disabled:["Enable and configure this channel in Settings first.","Сначала настройте и включите этот канал в настройках."],
    delivery_busy:["Another delivery is running. Wait for it to finish.","Другая отправка еще идет. Дождитесь ее завершения."],
    meeting_not_finished:["Wait for recording and processing to finish.","Дождитесь завершения записи и обработки."],
    report_not_ready:["The report is not ready yet.","Отчет еще не готов."],
    resend_confirmation_required:words.confirm,
    timeout_outcome_unknown:words.unknown, invalid_response:words.unknown,
    missing_send_acknowledgement:words.unknown, smtp_outcome_unknown:words.unknown,
    attachment_too_large:["PDF exceeds the email limit. Use the Google Drive copy.","PDF превышает лимит письма. Используйте копию на Google Drive."],
  };
  const text = key => (words[key] || errors[key] || words.error)[ru() ? 1 : 0];
  let state = {}, busy = false;
  async function api(path, body) {
    const response = await fetch(path, body === undefined ? {cache:"no-store"} : {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body)});
    const result = await response.json();
    if(!response.ok || !result.ok) throw new Error(result.error || "error");
    return result;
  }
  function labels() {
    document.querySelectorAll("[data-delivery-text]").forEach(node => node.textContent = text(node.dataset.deliveryText));
    $("delivery-password-help").textContent = text(state.smtp_password_saved ? "passwordSaved" : "passwordHelp");
    $("delivery-telegram-help").textContent = text(state.telegram_configured ? "telegramReady" : "telegramMissing");
  }
  function render(data) {
    state = data;
    $("delivery-profile").replaceChildren(new Option(text("noAccount"), ""), ...(data.profiles || []).map(p => new Option(p.email, p.id)));
    $("delivery-profile").value = data.google_profile || "";
    $("delivery-local-path").textContent = data.local_reports || "";
    for(const channel of ["email","drive","telegram"]) $(`delivery-${channel}-enabled`).checked = Boolean(data[`${channel}_enabled`]);
    $("delivery-telegram-enabled").disabled = !data.telegram_configured;
    $("delivery-provider").value = data.email_provider || "gmail";
    $("delivery-recipient").value = data.email_to || "";
    $("delivery-drive-folder").value = data.drive_folder_id || "";
    const smtp = data.smtp || {};
    for(const [field,key] of Object.entries({host:"host",port:"port",security:"security",user:"username",from:"from"})) $(`delivery-smtp-${field}`).value = smtp[key] || (field === "port" ? 587 : field === "security" ? "starttls" : "");
    $("delivery-smtp-password").value = "";
    $("delivery-smtp").hidden = data.email_provider !== "smtp";
    if(!data.profiles?.length) $("delivery-account-status").textContent = text("googleMissing");
    labels();
  }
  function payload() {
    return {email_enabled:$("delivery-email-enabled").checked, drive_enabled:$("delivery-drive-enabled").checked,
      telegram_enabled:$("delivery-telegram-enabled").checked, email_to:$("delivery-recipient").value,
      email_provider:$("delivery-provider").value, google_profile:$("delivery-profile").value,
      drive_folder_id:$("delivery-drive-folder").value, smtp_password:$("delivery-smtp-password").value,
      smtp:{host:$("delivery-smtp-host").value,port:$("delivery-smtp-port").value,security:$("delivery-smtp-security").value,
        username:$("delivery-smtp-user").value,from:$("delivery-smtp-from").value}};
  }
  async function save() { const result = await api("/api/delivery/settings", payload()); render(result.settings); $("delivery-settings-status").textContent = text("saved"); }
  async function action(button, fn) {
    if(busy) return;
    busy = true; button.disabled = true;
    try { await fn(); } catch(error) { $("delivery-settings-status").textContent = text(error.message); }
    finally {busy = false; button.disabled = false;}
  }
  $("delivery-settings-form").addEventListener("submit", event => {event.preventDefault(); void action($("delivery-save"), save);});
  $("delivery-provider").addEventListener("change", () => {$("delivery-smtp").hidden = $("delivery-provider").value !== "smtp";});
  $("settings-open").addEventListener("click", async () => {try {render((await api("/api/delivery/settings")).settings);} catch(error) {$("delivery-settings-status").textContent=text(error.message);}});
  for(const operation of ["connect","check"]) $("delivery-google-"+operation).addEventListener("click", event => void action(event.currentTarget, async () => {
    // Connect/check selects only the account, never saves unsaved delivery toggles.
    state = (await api("/api/delivery/settings", {google_profile:$("delivery-profile").value})).settings;
    const data = await api("/api/delivery/google/"+operation, {});
    $("delivery-account-status").textContent = text(data.account.state) + (data.account.account ? ": " + data.account.account : "");
  }));
  $("delivery-google-disconnect").addEventListener("click", event => void action(event.currentTarget, async () => {render((await api("/api/delivery/google/disconnect", {})).settings); $("delivery-account-status").textContent=text("noAccount");}));
  $("delivery-smtp-check").addEventListener("click", event => void action(event.currentTarget, async () => {const draft=payload(); const data=await api("/api/delivery/smtp/check", {smtp:draft.smtp,smtp_password:draft.smtp_password}); $("delivery-settings-status").textContent=text(data.account.state);}));
  window.deliveryControls = meeting => {
    const root = document.createElement("section"); root.className="delivery-retry-controls";
    const status = document.createElement("p"); status.setAttribute("role","status");
    const error = meeting.report?.mail_error?.reason;
    if(error) status.textContent=text(error);
    root.append(status);
    for(const [channel,field,key] of [["email","mail_status","retry"],["drive","drive_status","retryDrive"],["telegram","telegram_status","retryTelegram"]]) {
      const button=document.createElement("button"); button.type="button"; button.className="quiet-button";
      const prior=meeting.report?.[field];
      button.textContent = text(channel === "email" && prior === "sent" ? "resend" : key);
      button.disabled = !meeting.report?.pdf;
      button.addEventListener("click", async () => {
        const confirm = ["sent","uploaded","unknown"].includes(meeting.report?.[field]);
        if(confirm && !window.confirm(text("confirm"))) return;
        root.querySelectorAll("button").forEach(b => b.disabled=true);
        status.textContent=text("sending");
        try {
          const request_id=crypto.randomUUID();
          let job=(await api("/api/delivery/retry", {meeting_id:meeting.meeting_id, channels:[channel], request_id, confirm})).job;
          const deadline=Date.now()+300000;
          while(job.state === "sending") {if(Date.now()>deadline) throw new Error("timeout_outcome_unknown"); await new Promise(resolve=>setTimeout(resolve,1500)); job=(await api("/api/delivery/job")).job; if(job.request_id!==request_id) throw new Error("delivery_busy");}
          if(job.error) throw new Error(job.error);
          const delivered=job.report?.[field];
          status.textContent=["sent","uploaded"].includes(delivered) ? text("done") : text(job.report?.mail_error?.reason || "failed");
          if(job.report) meeting.report={...meeting.report,...job.report};
          root.dispatchEvent(new CustomEvent("delivery-complete", {bubbles:true, detail:meeting}));
          if(channel === "email" && delivered === "sent") button.textContent=text("resend");
        } catch(error) {status.textContent=text(error.message);}
        finally {root.querySelectorAll("button").forEach(b=>b.disabled=false);}
      }); root.append(button);
    }
    return root;
  };
  new MutationObserver(labels).observe(document.documentElement,{attributes:true,attributeFilter:["lang"]});
  labels();
})();
