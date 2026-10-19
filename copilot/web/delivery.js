/* Explicit delivery consent. Secrets are never returned to the browser or stored here. */
(() => {
  const $ = id => document.getElementById(id);
  const ru = () => document.documentElement.lang === "ru";
  const words = {
    heading:["Report storage and delivery","Хранение и доставка отчетов"],
    local:["Recordings and reports stay on this computer. Cloud connections are optional.","Записи и отчеты сохраняются на компьютере. Облачные сервисы подключать необязательно."],
    google:["Google — optional, your own OAuth client","Google — необязательно, свой OAuth-клиент"], account:["Account for Gmail and Google Drive","Аккаунт для Gmail и Google Drive"],
    accountHelp:["Use your own Google Cloud project and OAuth client. MeetOnTrack does not provide a shared Google app. Connecting does not enable delivery; context search is separate.","Используется ваш собственный проект Google Cloud и OAuth-клиент, не общее приложение MeetOnTrack. Подключение не включает отправку; поиск контекста настраивается отдельно."],
    googleGuide:["How to prepare your Google connection","Как подготовить подключение Google"],
    googleStep1:["In your own Google Cloud project, enable Gmail API for email and/or Google Drive API for uploads. For context search, also enable Calendar, Docs and Sheets APIs. Configure the consent screen; in Testing mode add your account as a test user. Testing authorizations may expire after 7 days and need reconnecting.","В своем проекте Google Cloud включите Gmail API для почты и/или Google Drive API для загрузки файлов. Для поиска контекста также включите Calendar, Docs и Sheets API. Настройте экран согласия; в режиме Testing добавьте себя как тестового пользователя. В этом режиме авторизация может истекать через 7 дней и требовать повторного входа."],
    googleStep2:["Create an OAuth client of type Desktop app and download its JSON configuration. An API key alone cannot authorize access to your mailbox or Drive.","Создайте OAuth-клиент типа Desktop app и скачайте его JSON-конфигурацию. Одного API-ключа недостаточно для доступа к почте или Drive."],
    googleStep3:["Choose the downloaded JSON here and import it. Enter your Google email, select permissions and click Connect Google. Complete consent in your browser, then check the account. Turn on delivery or context search separately when you want to use them.","Выберите скачанный JSON здесь и импортируйте его. Укажите свой адрес Google, выберите разрешения и нажмите «Подключить Google». Подтвердите доступ в браузере, затем проверьте аккаунт. Отправку отчетов и поиск контекста включайте отдельно, когда они понадобятся."],
    oauthFile:["Your Google OAuth JSON file","Ваш JSON-файл Google OAuth"],
    oauthImport:["Import my OAuth JSON","Импортировать мой OAuth JSON"],
    oauthImportHelp:["Desktop app credentials only, up to 16 KB. Stored in this computer's protected credential store, not sent to MeetOnTrack servers. Import selects this connection and turns off existing Google delivery until you enable it again.","Только учетные данные Desktop app, до 16 КБ. Сохраняются в защищенном хранилище компьютера, не отправляются на сервер MeetOnTrack. Импорт выбирает это подключение и отключает прежнюю доставку через Google до вашего повторного включения."],
    oauthImported:["OAuth client imported. Now choose permissions and connect your account.","OAuth-клиент импортирован. Теперь выберите разрешения и подключите аккаунт."],
    oauthEmail:["Google email to connect","Адрес Google для подключения"],
    oauthPermissions:["Permissions to request from Google","Какие разрешения запросить у Google"],
    oauthMail:["Send email through Gmail","Отправка писем через Gmail"],
    oauthDrive:["Save reports in my Drive folder (Google grants full Drive access)","Сохранение отчетов в моей папке Drive (Google предоставляет полный доступ к Drive)"],
    oauthContext:["Read Gmail, Calendar and Drive for optional context search","Чтение Gmail, Calendar и Drive для необязательного поиска контекста"],
    oauthConsentHelp:["Granting permissions does not enable automatic email, uploads or context search. Reconnect to change permissions. To switch accounts or replace a connected client, disconnect first.","Выдача разрешений не включает автоматическую отправку, загрузку или поиск контекста. Для изменения разрешений подключитесь заново. Перед сменой аккаунта или подключенного клиента сначала отключите его."],
    oauthOpen:["Continue sign-in in Google","Продолжить вход в Google"],
    oauthOwn:["My OAuth client","Мой OAuth-клиент"],
    googleDocs:["Google: desktop OAuth setup","Google: настройка OAuth для настольного приложения"],
    connect:["Connect Google","Подключить Google"], checkGoogle:["Check account","Проверить аккаунт"], disconnect:["Disconnect from MeetOnTrack","Отключить от MeetOnTrack"],
    mail:["Email after a meeting","Письмо после встречи"], autoMail:["Email reports automatically","Автоматически отправлять отчет по почте"],
    provider:["Send using","Способ отправки"], recipient:["Report recipient","Получатель отчета"],
    attachment:["The PDF is attached to the email. Google Drive is not required.","PDF прикладывается к письму. Google Drive для этого не нужен."],
    host:["SMTP server","SMTP-сервер"], port:["Port","Порт"], security:["Connection security","Защита соединения"],
    username:["SMTP username","Логин SMTP"], sender:["Sender address","Адрес отправителя"], password:["SMTP password or app password","Пароль SMTP или пароль приложения"],
    smtpHelp:["Use your mail provider's SMTP server, port and TLS settings, username and password (or app password). No Google Cloud project is needed. Check the connection, choose a recipient, then enable email and save.","Укажите SMTP-сервер, порт и TLS из инструкции своего почтового сервиса, логин и пароль (или пароль приложения). Google Cloud не нужен. Проверьте подключение, укажите получателя, затем включите отправку и сохраните настройки."],
    smtpGoogleHelp:["For Gmail SMTP, use an app password if your account supports it; it requires 2-Step Verification. Your usual Google password is not a substitute.","Для Gmail SMTP нужен пароль приложения, если он доступен вашему аккаунту; для него требуется двухэтапная аутентификация. Обычный пароль Google его не заменяет."],
    smtpGoogleDocs:["Google: app passwords and restrictions","Google: пароли приложений и ограничения"],
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
    googleMissing:["Google is not set up on this computer. See the setup details below, or use SMTP without Google Cloud.","Google на этом компьютере не настроен. Раскройте инструкцию ниже или используйте SMTP без Google Cloud."],
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
    google_desktop_json_required:["Choose the JSON for a Desktop app OAuth client, not a service account or web client.","Выберите JSON OAuth-клиента Desktop app, не сервисного аккаунта и не веб-клиента."],
    google_invalid_client:["Invalid Google client JSON. Download the Desktop app credentials again.","Некорректный JSON Google. Скачайте учетные данные Desktop app заново."],
    google_invalid_endpoint:["This JSON contains an unexpected authorization endpoint and was rejected.","JSON содержит посторонний адрес авторизации и отклонен."],
    google_client_required:["Import your OAuth JSON first.","Сначала импортируйте свой OAuth JSON."],
    google_permissions_required:["Select at least one Google permission.","Выберите хотя бы одно разрешение Google."],
    google_disconnect_before_replace:["Disconnect the current Google account before replacing it.","Отключите текущий Google-аккаунт перед его заменой."],
    google_login_cancelling:["The previous sign-in is closing. Try again shortly.","Предыдущая попытка входа закрывается. Повторите через несколько секунд."],
    google_consent_denied:["Google access was declined. No delivery was enabled.","Доступ Google отклонен. Отправка не включена."],
    google_dependency_missing:["Google connection component is missing. Reinstall the current MeetOnTrack package.","Не установлен компонент подключения Google. Переустановите текущий пакет MeetOnTrack."],
    google_refresh_token_missing:["Google did not grant persistent access. Reconnect and approve access.","Google не предоставил постоянный доступ. Подключитесь заново и подтвердите разрешения."],
    google_login_failed:["Google sign-in failed. Check your client, enabled APIs and test-user access, then reconnect.","Вход в Google не завершен. Проверьте OAuth-клиент, включенные API и доступ тестового пользователя, затем подключитесь заново."],
    oauth_file_required:["Choose a JSON file no larger than 16 KB.","Выберите JSON-файл не больше 16 КБ."],
    account_mismatch:["Account mismatch. Delivery stopped for safety.","Аккаунт не совпадает. Отправка остановлена для безопасности."],
    invalid_email:["Enter a valid email address.","Введите корректный адрес почты."],
    recipient_required:["Enter the report recipient.","Укажите получателя отчета."],
    drive_folder_required:["Choose a Google Drive folder.","Укажите папку Google Drive."],
    invalid_drive_folder:["Enter a Google Drive folder link or ID.","Введите ссылку или ID папки Google Drive."],
    smtp_settings_required:["Enter SMTP server, username and sender.","Укажите SMTP-сервер, логин и отправителя."],
    smtp_password_required:["Enter the SMTP password or app password required by your provider.","Введите пароль SMTP или пароль приложения, который требует ваш почтовый сервис."],
    smtp_auth_failed:["SMTP rejected the login. Check the username, password and provider's authentication requirements.","SMTP отклонил вход. Проверьте логин, пароль и требования почтового сервиса к авторизации."],
    google_login_timeout:["Google sign-in timed out. Start connecting again when ready.","Время ожидания входа в Google истекло. Начните подключение заново, когда будете готовы."],
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
    const emptyAccount = $("delivery-profile").querySelector('option[value=""]');
    if(emptyAccount) emptyAccount.textContent = text("noAccount");
    const ownAccount = $("delivery-profile").querySelector('option[value="custom"]');
    if(ownAccount && !state.own_google?.account) ownAccount.textContent = text("oauthOwn");
    if(state.profiles && !state.profiles.length) $("delivery-account-status").textContent = text("googleMissing");
  }
  function render(data) {
    state = data;
    $("delivery-google-login-link").hidden = true;
    $("delivery-google-login-link").removeAttribute("href");
    $("delivery-profile").replaceChildren(new Option(text("noAccount"), ""), ...(data.profiles || []).map(p => new Option(p.email || text("oauthOwn"), p.id)));
    $("delivery-profile").value = data.google_profile || "";
    $("delivery-own-google").hidden = data.google_profile !== "custom";
    $("delivery-account-status").textContent = data.google_profile === "custom"
      ? text(data.own_google?.state || "authorization_required") + (data.own_google?.account ? ": " + data.own_google.account : "")
      : text(data.profiles?.length ? "noAccount" : "googleMissing");
    $("delivery-google-email").value = data.own_google?.account || "";
    for(const permission of ["mail","drive","context"]) $("delivery-oauth-"+permission).checked = Boolean(data.own_google?.permissions?.includes(permission));
    $("delivery-local-path").textContent = data.local_reports || "";
    for(const channel of ["email","drive","telegram"]) $(`delivery-${channel}-enabled`).checked = Boolean(data[`${channel}_enabled`]);
    $("delivery-telegram-enabled").disabled = !data.telegram_configured;
    $("delivery-provider").value = data.email_provider || "smtp";
    $("delivery-recipient").value = data.email_to || "";
    $("delivery-drive-folder").value = data.drive_folder_id || "";
    const smtp = data.smtp || {};
    for(const [field,key] of Object.entries({host:"host",port:"port",security:"security",user:"username",from:"from"})) $(`delivery-smtp-${field}`).value = smtp[key] || (field === "port" ? 587 : field === "security" ? "starttls" : "");
    $("delivery-smtp-password").value = "";
    $("delivery-smtp").hidden = $("delivery-provider").value !== "smtp";
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
  $("delivery-profile").addEventListener("change", () => {$("delivery-own-google").hidden = $("delivery-profile").value !== "custom";});
  $("delivery-google-import").addEventListener("click", event => void action(event.currentTarget, async () => {
    const input=$("delivery-oauth-json"), file=input.files?.[0];
    try {
      if(!file || file.size > 16384) throw new Error("oauth_file_required");
      let client;
      try { client=JSON.parse(await file.text()); } catch { throw new Error("google_invalid_client"); }
      render((await api("/api/delivery/google/import", {client})).settings);
      $("delivery-settings-status").textContent=text("oauthImported");
    } finally {input.value="";}
  }));
  $("settings-open").addEventListener("click", async () => {try {render((await api("/api/delivery/settings")).settings);} catch(error) {$("delivery-settings-status").textContent=text(error.message);}});
  for(const operation of ["connect","check"]) $("delivery-google-"+operation).addEventListener("click", event => void action(event.currentTarget, async () => {
    // Connect/check selects only the account, never saves unsaved delivery toggles.
    state = (await api("/api/delivery/settings", {google_profile:$("delivery-profile").value})).settings;
    const data = await api("/api/delivery/google/"+operation, {account:$("delivery-google-email").value,
      permissions:["mail","drive","context"].filter(p=>$("delivery-oauth-"+p).checked)});
    $("delivery-account-status").textContent = text(data.account.state) + (data.account.account ? ": " + data.account.account : "");
    const link=$("delivery-google-login-link");
    link.hidden=!data.account.authorization_url;
    if(data.account.authorization_url) {
      const url=new URL(data.account.authorization_url);
      if(url.origin!=="https://accounts.google.com") throw new Error("google_invalid_endpoint");
      link.href=url.href;
      window.open(url.href, "_blank", "noopener,noreferrer");
    } else {link.removeAttribute("href");}
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
