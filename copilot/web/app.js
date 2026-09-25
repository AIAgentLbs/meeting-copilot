const elements = {
  meetingTitle: document.querySelector("#meeting-title"),
  liveStatus: document.querySelector("#live-status"),
  repoStatus: document.querySelector("#repo-button"),
  archiveButton: document.querySelector("#archive-button"),
  archiveDialog: document.querySelector("#archive-dialog"),
  archiveDescription: document.querySelector("#archive-description"),
  archiveClose: document.querySelector("#archive-close"),
  archiveList: document.querySelector("#archive-list"),
  archiveDetail: document.querySelector("#archive-detail"),
  transcriptMeta: document.querySelector("#transcript-meta"),
  transcript: document.querySelector("#transcript"),
  frames: document.querySelector("#frames"),
  framesGrid: document.querySelector("#frames-grid"),
  frameCount: document.querySelector("#frame-count"),
  frameStatus: document.querySelector("#frame-status"),
  captureFrame: document.querySelector("#capture-frame"),
  copyDialog: document.querySelector("#copy-dialog"),
  speakerFilters: document.querySelector("#speaker-filters"),
  chat: document.querySelector("#chat"),
  chatLatest: document.querySelector("#chat-latest"),
  welcome: document.querySelector("#welcome"),
  copilotMeta: document.querySelector("#copilot-meta"),
  form: document.querySelector("#chat-form"),
  question: document.querySelector("#question"),
  send: document.querySelector("#send-button"),
  note: document.querySelector("#note-button"),
  help: document.querySelector("#composer-help"),
  refresh: document.querySelector("#refresh-button"),
  reset: document.querySelector("#reset-button"),
  analyze: document.querySelector("#analyze-button"),
  autoAnalysis: document.querySelector("#auto-analysis"),
  journal: document.querySelector("#journal"),
  journalList: document.querySelector("#journal-list"),
  journalCounts: {
    questions: document.querySelector("#questions-count"),
    objections: document.querySelector("#objections-count"),
    decisions: document.querySelector("#decisions-count"),
    notes: document.querySelector("#notes-count"),
    entities: document.querySelector("#entities-count"),
  },
  meetingChat: document.querySelector("#meeting-chat"),
  meetingChatList: document.querySelector("#meeting-chat-list"),
  meetingChatCount: document.querySelector("#meeting-chat-count"),
  composerWrap: document.querySelector("#composer-wrap"),
  analysisStatus: document.querySelector("#analysis-status"),
  repoDialog: document.querySelector("#repo-dialog"),
  projectDialog: document.querySelector("#project-dialog"),
  projectClose: document.querySelector("#project-close"),
  projectHelp: document.querySelector("#project-help"),
  projectOptions: document.querySelector("#project-options"),
  projectEditRepos: document.querySelector("#project-edit-repos"),
  repoSearch: document.querySelector("#repo-search"),
  repoList: document.querySelector("#repo-list"),
  repoSelectionCount: document.querySelector("#repo-selection-count"),
  repoSave: document.querySelector("#repo-save"),
  repoHelp: document.querySelector("#repo-help"),
};

const translations = {
  ru: {
    "meeting.connecting": "Подключение к записи...",
    "status.checking": "Проверка",
    "nav.repositories": "Контекст встречи",
    "nav.meetings": "История встреч",
    "language.label": "Язык интерфейса",
    "aria.transcript_view": "Вид левой панели",
    "aria.speaker_filter": "Фильтр участников",
    "aria.copilot_view": "Режим правой панели",
    "aria.journal_filter": "Фильтр журнала",
    "aria.workspace_filter": "Чат и сигналы встречи",
    "common.refresh": "Обновить",
    "common.close": "Закрыть",
    "common.cancel": "Отмена",
    "transcript.heading": "Ход созвона",
    "transcript.loading": "Получаю последние реплики",
    "transcript.tab": "Стенограмма",
    "transcript.copy": "Копировать диалог",
    "transcript.copied": "Диалог скопирован",
    "transcript.copy_empty": "Нет реплик для копирования",
    "transcript.copy_failed": "Не удалось скопировать",
    "frames.tab": "Кадры",
    "speaker.all": "Все",
    "speaker.me": "Я",
    "speaker.others": "Собеседники",
    "transcript.empty_title": "Жду стенограмму",
    "transcript.empty_text": "Meeting Copilot передаёт локальную расшифровку примерно раз в секунду.",
    "frames.local_note": "Кадры хранятся только локально вместе с записью.",
    "frames.capture": "Снять кадр сейчас",
    "frames.armed": "Съёмка готова.",
    "frames.ok": "Последний кадр: {time}.",
    "frames.error": "Ошибка съёмки: {error}",
    "copilot.heading": "Чат с контекстом",
    "copilot.meta": "Codex читает стенограмму и локальные Git-репозитории",
    "view.chat": "Чат",
    "view.journal": "Журнал",
    "view.meeting_chat": "Чат встречи",
    "copilot.reset": "Новый контекст",
    "welcome.title": "Спросите по ходу разговора",
    "welcome.text": "Ответ будет проверен по локальным источникам. Репозитории открываются только для чтения.",
    "suggestion.latest": "Что они только что сказали?",
    "suggestion.repos": "Проверь это по репозиториям",
    "suggestion.history": "Что мы решали раньше?",
    "suggestion.challenge": "Что здесь стоит оспорить?",
    "journal.all": "Все",
    "journal.questions": "Вопросы",
    "journal.objections": "Риски и возражения",
    "journal.decisions": "Решения",
    "journal.notes": "Мои заметки",
    "journal.entities": "Ссылки и сервисы",
    "meeting_chat.note": "Сообщения извлекаются из видимой панели Zoom Chat и сохраняются только локально.",
    "analysis.auto": "Автоанализ важных новых реплик",
    "analysis.now": "Анализ сейчас",
    "analysis.initial": "Автоанализ ещё не запускался",
    "composer.label": "Вопрос или заметка к текущему созвону",
    "composer.placeholder": "Спросите Copilot или запишите мысль по ходу разговора.",
    "composer.ask": "Спросить",
    "composer.help": "Enter спрашивает · ⌘Enter сохраняет заметку · Shift+Enter переносит строку",
    "repos.title": "Репозитории для контекста",
    "repos.description": "Выберите до 15 уже клонированных GitHub/GitLab-репозиториев. Файлы и Git остаются только для чтения.",
    "repos.search": "Имя, путь или remote URL",
    "repos.help": "Список берётся из локального каталога — клонирования и сетевых Git-команд нет.",
    "repos.save": "Сохранить набор",
    "note.button": "Заметка @ {time}",
    "age.none": "нет реплик",
    "age.now": "только что",
    "age.seconds": "{value} сек назад",
    "age.minutes": "{value} мин назад",
    "age.hours": "{value} ч назад",
    "status.waiting": "Ожидание записи",
    "status.live": "Созвон идёт",
    "status.finished": "Созвон завершён · контекст сохранён",
    "status.model_loading": "Загрузка модели",
    "status.model_missing": "Нет live-модели",
    "status.overloaded": "Live-расшифровка перегружена",
    "status.no_fresh": "Нет свежих реплик",
    "transcript.overloaded_meta": "Модель не успевает в реальном времени; аудиозапись продолжается. Последняя реплика: {age}",
    "transcript.latest_meta": "Последняя реплика: {age}",
    "transcript.failed": "Не удалось обновить стенограмму",
    "speaker.name_hint": "Имя определено по активной рамке Zoom",
    "frames.empty_title": "Кадров пока нет",
    "frames.empty_text": "Во время Zoom Meeting Copilot сохраняет окно примерно раз в 15 секунд.",
    "frames.alt_speaker": "Кадр Zoom, говорит {speaker}",
    "frames.alt": "Кадр Zoom",
    "frames.speaker_unknown": "Спикер не определён",
    "message.you": "Вы",
    "message.autoanalysis": "Автоанализ",
    "message.thinking": "Ищу в стенограмме и репозиториях",
    "message.latest": "К последнему ответу",
    "speaker.voice": "Спикер {value}",
    "speaker.voice_hint": "Голос различён локально по аудио; имя появится, когда Zoom покажет активного участника",
    "copilot.error": "Ошибка: {error}",
    "copilot.active": "Контекст Codex активен, репозитории доступны только для чтения",
    "copilot.disconnected": "Codex подключится после первого вопроса",
    "analysis.no_signal": "Проверено{when}: новых значимых сигналов нет",
    "analysis.signal": "Проверено{when}: новые сигналы добавлены в Журнал",
    "analysis.error": "Автоанализ не выполнен{when}: {error}",
    "analysis.error_default": "ошибка",
    "provider.other": "Другой Git remote",
    "repos.selected": "Выбраны · {count}",
    "repos.empty": "Ничего не найдено в локальном каталоге",
    "repos.selection_count": "{count} из {max}",
    "repos.loading": "Загружаю локальный каталог…",
    "repos.loaded": "Выбранные закреплены сверху. GitLab git.aiagentlbs.com: {count}. Никакого pull/fetch/clone не выполняется.",
    "repos.saving": "Сохраняю локальный набор…",
    "journal.empty_title": "Журнал пока пуст",
    "journal.empty_text": "Вопросы и важные блоки из ответов Copilot появятся здесь автоматически.",
    "journal.anchor_title": "Перейти к ближайшей реплике",
    "traffic.red": "Красный: риск или противоречие",
    "traffic.yellow": "Жёлтый: открытый вопрос",
    "traffic.green": "Зелёный: решение или обязательство",
    "meeting.no_title": "Без названия",
    "meeting_chat.empty_title": "Чат встречи пока не распознан",
    "meeting_chat.empty_text": "Откройте панель Zoom Chat: новые видимые сообщения сохранятся с именами участников.",
    "meeting_chat.participant": "Участник",
    "project.unknown": "Проект не определён",
    "project.all_scope": "Контекст: все {count} · выбрать проект",
    "project.manual_scope": "Проект: {project} · {count} · изменить",
    "project.repository_scope": "Контекст: {project} · изменить",
    "project.auto_scope": "Похоже, {project} · {count} · изменить",
    "project.all_hint": "Проект не выбран. Copilot ищет по всем выбранным репозиториям.",
    "project.manual_hint": "Вы выбрали контекст только для этой встречи.",
    "project.auto_hint": "Проект определён по названию или репликам. Вы можете изменить выбор.",
    "project.choose_title": "Контекст этой встречи",
    "project.choose_description": "Выберите проект или репозиторий. Выбор действует только для этой встречи и меняет поиск Copilot.",
    "project.loading": "Загружаю варианты…",
    "project.choose_help": "Сейчас поиск идёт по {count}. Можно оставить как есть или сузить контекст.",
    "project.no_meeting": "Начните запись, чтобы выбрать контекст встречи.",
    "project.group_modes": "Режим поиска",
    "project.group_projects": "Проекты",
    "project.group_repositories": "Отдельные репозитории",
    "project.auto": "Автоматически",
    "project.auto_detail": "Если проект не распознан — поиск по всем выбранным.",
    "project.all": "Все выбранные репозитории",
    "project.all_detail": "Искать по {count} без привязки к проекту.",
    "project.only_repo": "Только {name}",
    "project.selected": "Выбрано",
    "project.local_note": "Поиск идёт только по выбранным локальным репозиториям.",
    "project.edit_repos": "Изменить набор репозиториев",
    "project.saving": "Сохраняю выбор…",
    "ui.disconnected": "UI отключён",
    "help.codex": "Codex проверяет стенограмму и локальные источники",
    "note.saving": "Сохраняю заметку локально",
    "note.current": "текущий момент",
    "note.saved": "Заметка сохранена @ {time}",
    "analysis.searching": "Ищу важные сигналы",
    "analysis.checking": "Проверяю новые реплики",
    "frames.capturing": "Снимаю…",
    "archive.title": "Архив встреч",
    "archive.description": "Стенограммы, заметки, чат, кадры и отчёты хранятся локально.",
    "archive.count_description": "Записей: {count} · сгруппированы по дням. Материалы хранятся локально.",
    "archive.unknown_day": "Дата не указана",
    "archive.copy_dialog": "Копировать диалог",
    "archive.select_title": "Выберите встречу",
    "archive.select_text": "Здесь появятся её материалы и готовые отчёты.",
    "archive.empty": "Записей пока нет",
    "archive.utterances": "реплик",
    "archive.notes": "заметок",
    "archive.frames": "кадров",
    "archive.chat": "сообщений чата",
    "archive.audio": "Аудиозапись",
    "archive.no_transcript": "Стенограмма для этой старой записи не была сохранена.",
    "archive.summary": "Заметки и саммари",
    "archive.transcript": "Стенограмма",
    "archive.screenshots": "Скриншоты",
    "archive.meeting_chat": "Чат встречи",
    "archive.report": "Отчёт",
    "archive.generate": "Сформировать HTML и PDF",
    "archive.generating": "Формирую отчёт…",
    "archive.open_html": "Открыть HTML",
    "archive.open_pdf": "Открыть PDF",
    "archive.drive_uploaded": "Загружено в Google Drive",
    "archive.drive_auth": "Google Drive требует повторной авторизации",
    "archive.mail_sent": "Копия отправлена по почте",
    "archive.mail_pending": "Автоотправка почты ещё не настроена",
  },
  en: {
    "meeting.connecting": "Connecting to the recording...",
    "status.checking": "Checking",
    "nav.repositories": "Meeting context",
    "nav.meetings": "Meeting history",
    "language.label": "Interface language",
    "aria.transcript_view": "Left pane view",
    "aria.speaker_filter": "Speaker filter",
    "aria.copilot_view": "Right pane view",
    "aria.journal_filter": "Journal filter",
    "aria.workspace_filter": "Meeting chat and signals",
    "common.refresh": "Refresh",
    "common.close": "Close",
    "common.cancel": "Cancel",
    "transcript.heading": "Live meeting",
    "transcript.loading": "Loading the latest utterances",
    "transcript.tab": "Transcript",
    "transcript.copy": "Copy dialogue",
    "transcript.copied": "Dialogue copied",
    "transcript.copy_empty": "No utterances to copy",
    "transcript.copy_failed": "Could not copy",
    "frames.tab": "Frames",
    "speaker.all": "All",
    "speaker.me": "Me",
    "speaker.others": "Others",
    "transcript.empty_title": "Waiting for the transcript",
    "transcript.empty_text": "Meeting Copilot publishes the local transcript about once per second.",
    "frames.local_note": "Frames are stored only locally with the recording.",
    "frames.capture": "Capture frame now",
    "frames.armed": "Capture is armed.",
    "frames.ok": "Last frame: {time}.",
    "frames.error": "Capture error: {error}",
    "copilot.heading": "Context chat",
    "copilot.meta": "Codex reads the transcript and local Git repositories",
    "view.chat": "Chat",
    "view.journal": "Journal",
    "view.meeting_chat": "Meeting chat",
    "copilot.reset": "New context",
    "welcome.title": "Ask during the conversation",
    "welcome.text": "The answer will be checked against local sources. Repositories are opened read-only.",
    "suggestion.latest": "What did they just say?",
    "suggestion.repos": "Check this against my repositories",
    "suggestion.history": "What did we decide earlier?",
    "suggestion.challenge": "What should I challenge here?",
    "journal.all": "All",
    "journal.questions": "Questions",
    "journal.objections": "Risks & objections",
    "journal.decisions": "Decisions",
    "journal.notes": "My notes",
    "journal.entities": "Links and services",
    "meeting_chat.note": "Messages are extracted from the visible Zoom Chat panel and stored locally only.",
    "analysis.auto": "Auto-analyse important new utterances",
    "analysis.now": "Analyse now",
    "analysis.initial": "Auto-analysis has not run yet",
    "composer.label": "Question or note for the current meeting",
    "composer.placeholder": "Ask Copilot or capture a thought during the conversation.",
    "composer.ask": "Ask",
    "composer.help": "Enter asks · ⌘Enter saves a note · Shift+Enter adds a line",
    "repos.title": "Repositories for context",
    "repos.description": "Select up to 15 already cloned GitHub/GitLab repositories. Files and Git remain read-only.",
    "repos.search": "Name, path, or remote URL",
    "repos.help": "The list comes from the local catalog—no clone, pull, or fetch is performed.",
    "repos.save": "Save selection",
    "note.button": "Note @ {time}",
    "age.none": "no utterances",
    "age.now": "just now",
    "age.seconds": "{value}s ago",
    "age.minutes": "{value}m ago",
    "age.hours": "{value}h ago",
    "status.waiting": "Waiting for recording",
    "status.live": "Meeting live",
    "status.finished": "Meeting ended · context retained",
    "status.model_loading": "Loading model",
    "status.model_missing": "Live model missing",
    "status.overloaded": "Live transcription overloaded",
    "status.no_fresh": "No recent utterances",
    "transcript.overloaded_meta": "The model is behind real time; audio recording continues. Latest utterance: {age}",
    "transcript.latest_meta": "Latest utterance: {age}",
    "transcript.failed": "Could not refresh the transcript",
    "speaker.name_hint": "Name detected from Zoom's active-speaker frame",
    "frames.empty_title": "No frames yet",
    "frames.empty_text": "During Zoom calls, Meeting Copilot saves the window about every 15 seconds.",
    "frames.alt_speaker": "Zoom frame, {speaker} speaking",
    "frames.alt": "Zoom frame",
    "frames.speaker_unknown": "Speaker not identified",
    "message.you": "You",
    "message.autoanalysis": "Auto-analysis",
    "message.thinking": "Searching the transcript and repositories",
    "message.latest": "Jump to latest",
    "speaker.voice": "Speaker {value}",
    "speaker.voice_hint": "The voice was separated locally from audio; a name appears when Zoom shows the active participant",
    "copilot.error": "Error: {error}",
    "copilot.active": "Codex context is active; repositories are read-only",
    "copilot.disconnected": "Codex will connect after the first question",
    "analysis.no_signal": "Checked{when}: no new significant signals",
    "analysis.signal": "Checked{when}: new signals added to the Journal",
    "analysis.error": "Auto-analysis failed{when}: {error}",
    "analysis.error_default": "error",
    "provider.other": "Other Git remote",
    "repos.selected": "Selected · {count}",
    "repos.empty": "Nothing found in the local catalog",
    "repos.selection_count": "{count} of {max}",
    "repos.loading": "Loading the local catalog…",
    "repos.loaded": "Selected repositories are pinned. GitLab git.aiagentlbs.com: {count}. No pull, fetch, or clone is performed.",
    "repos.saving": "Saving the local selection…",
    "journal.empty_title": "The Journal is empty",
    "journal.empty_text": "Questions and important Copilot response blocks will appear here automatically.",
    "journal.anchor_title": "Jump to the nearest utterance",
    "traffic.red": "Red: risk or contradiction",
    "traffic.yellow": "Yellow: open question",
    "traffic.green": "Green: decision or commitment",
    "meeting.no_title": "Untitled meeting",
    "meeting_chat.empty_title": "Meeting chat has not been detected",
    "meeting_chat.empty_text": "Open the Zoom Chat panel; newly visible messages will be saved with participant names.",
    "meeting_chat.participant": "Participant",
    "project.unknown": "Project not identified",
    "project.all_scope": "Context: all {count} · choose project",
    "project.manual_scope": "Project: {project} · {count} · change",
    "project.repository_scope": "Context: {project} · change",
    "project.auto_scope": "Likely {project} · {count} · change",
    "project.all_hint": "No project is selected. Copilot searches all selected repositories.",
    "project.manual_hint": "You selected this context for this meeting only.",
    "project.auto_hint": "The project was inferred from the meeting title or transcript. You can change it.",
    "project.choose_title": "Context for this meeting",
    "project.choose_description": "Choose a project or repository. This affects Copilot search for this meeting only.",
    "project.loading": "Loading choices…",
    "project.choose_help": "Copilot currently searches {count}. Keep this scope or narrow it.",
    "project.no_meeting": "Start a recording to choose meeting context.",
    "project.group_modes": "Search mode",
    "project.group_projects": "Projects",
    "project.group_repositories": "Individual repositories",
    "project.auto": "Automatic",
    "project.auto_detail": "Search all selected repositories when no project is recognized.",
    "project.all": "All selected repositories",
    "project.all_detail": "Search {count} without choosing a project.",
    "project.only_repo": "Only {name}",
    "project.selected": "Selected",
    "project.local_note": "Search is limited to selected local repositories.",
    "project.edit_repos": "Change repository set",
    "project.saving": "Saving selection…",
    "ui.disconnected": "UI disconnected",
    "help.codex": "Codex is checking the transcript and local sources",
    "note.saving": "Saving the note locally",
    "note.current": "current moment",
    "note.saved": "Note saved @ {time}",
    "analysis.searching": "Searching for important signals",
    "analysis.checking": "Checking new utterances",
    "frames.capturing": "Capturing…",
    "archive.title": "Meeting archive",
    "archive.description": "Transcripts, notes, chat, frames and reports are stored locally.",
    "archive.count_description": "{count} recordings · grouped by day. Materials are stored locally.",
    "archive.unknown_day": "Date unavailable",
    "archive.copy_dialog": "Copy dialogue",
    "archive.select_title": "Select a meeting",
    "archive.select_text": "Its materials and generated reports appear here.",
    "archive.empty": "No recordings yet",
    "archive.utterances": "utterances",
    "archive.notes": "notes",
    "archive.frames": "frames",
    "archive.chat": "chat messages",
    "archive.audio": "Audio recording",
    "archive.no_transcript": "The transcript was not preserved for this older recording.",
    "archive.summary": "Notes and summary",
    "archive.transcript": "Transcript",
    "archive.screenshots": "Screenshots",
    "archive.meeting_chat": "Meeting chat",
    "archive.report": "Report",
    "archive.generate": "Generate HTML and PDF",
    "archive.generating": "Generating report…",
    "archive.open_html": "Open HTML",
    "archive.open_pdf": "Open PDF",
    "archive.drive_uploaded": "Uploaded to Google Drive",
    "archive.drive_auth": "Google Drive needs reauthorization",
    "archive.mail_sent": "Email copy sent",
    "archive.mail_pending": "Automatic email delivery is not configured yet",
  },
};

let uiLanguage = localStorage.getItem("meeting-copilot-language") === "en" ? "en" : "ru";

function t(key, variables = {}) {
  const template = translations[uiLanguage][key] || translations.ru[key] || key;
  return Object.entries(variables).reduce(
    (value, [name, replacement]) => value.replaceAll(`{${name}}`, String(replacement)),
    template,
  );
}

function repositoryCountLabel(count) {
  if (uiLanguage === "en") return `${count} ${count === 1 ? "repository" : "repositories"}`;
  const remainder = count % 100;
  const suffix = remainder >= 11 && remainder <= 14 ? "репозиториев"
    : count % 10 === 1 ? "репозиторий"
      : [2, 3, 4].includes(count % 10) ? "репозитория" : "репозиториев";
  return `${count} ${suffix}`;
}

function applyLanguage() {
  document.documentElement.lang = uiLanguage;
  document.querySelectorAll("[data-i18n]").forEach((node) => {
    node.textContent = t(node.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((node) => {
    node.placeholder = t(node.dataset.i18nPlaceholder);
  });
  document.querySelectorAll("[data-i18n-aria-label]").forEach((node) => {
    node.setAttribute("aria-label", t(node.dataset.i18nAriaLabel));
  });
  document.querySelectorAll("[data-language]").forEach((button) => {
    button.classList.toggle("active", button.dataset.language === uiLanguage);
    button.setAttribute("aria-pressed", String(button.dataset.language === uiLanguage));
  });
}

let sourceFilter = "all";
let transcriptSignature = "";
let renderedMessages = "";
let requestBusy = false;
let autoAnalysisPrimed = false;
let journalSignature = "";
let journalFilter = "questions";
let meetingChatSignature = "";
let repositoryCatalog = [];
let selectedRepositoryPaths = new Set();
let maxActiveRepositories = 15;
let projectChoices = [];
let projectSelection = "auto";
let projectMeetingId = "";
let transcriptView = "transcript";
let frameSignature = "";
let stateRequestInFlight = false;
let stateConnectionFailed = false;
let activeTranscript = null;
let noteBusy = false;
let chatPinnedToLatest = true;
let archiveMeetings = [];
let selectedArchiveMeeting = "";

const journalGroups = {
  questions: new Set(["QUESTION", "ASK"]),
  objections: new Set(["CONTRADICTION", "RISK"]),
  decisions: new Set(["DECISION", "COMMITMENT"]),
  notes: new Set(["NOTE"]),
  entities: new Set(["URL", "PRODUCT", "SERVICE"]),
};

const journalLabels = {
  ru: {
    QUESTION: "ВОПРОС",
    ASK: "ЧТО СПРОСИТЬ",
    CONTRADICTION: "ПРОТИВОРЕЧИЕ",
    RISK: "РИСК",
    DECISION: "РЕШЕНИЕ",
    COMMITMENT: "ОБЯЗАТЕЛЬСТВО",
    FACT: "ФАКТ",
    HISTORY: "ИСТОРИЯ",
    URL: "ССЫЛКА",
    PRODUCT: "ПРОДУКТ",
    SERVICE: "СЕРВИС",
    NOTE: "МОЯ ЗАМЕТКА",
  },
  en: {
    QUESTION: "QUESTION",
    ASK: "ASK",
    CONTRADICTION: "CONTRADICTION",
    RISK: "RISK",
    DECISION: "DECISION",
    COMMITMENT: "COMMITMENT",
    FACT: "FACT",
    HISTORY: "HISTORY",
    URL: "LINK",
    PRODUCT: "PRODUCT",
    SERVICE: "SERVICE",
    NOTE: "MY NOTE",
  },
};

function localTime(iso) {
  if (!iso) return "";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return new Intl.DateTimeFormat(uiLanguage === "ru" ? "ru-RU" : "en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(date);
}

function ageLabel(seconds) {
  if (seconds === null || seconds === undefined) return t("age.none");
  if (seconds < 10) return t("age.now");
  if (seconds < 60) return t("age.seconds", { value: seconds });
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return t("age.minutes", { value: minutes });
  return t("age.hours", { value: Math.floor(minutes / 60) });
}

function timecodeLabel(transcript) {
  if (!transcript?.started_at) return "--:--";
  const started = new Date(transcript.started_at);
  const anchor = transcript.live
    ? new Date()
    : new Date(transcript.latest_at || transcript.updated_at || transcript.started_at);
  if (Number.isNaN(started.getTime()) || Number.isNaN(anchor.getTime())) return "--:--";
  const total = Math.max(0, Math.floor((anchor.getTime() - started.getTime()) / 1000));
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const seconds = total % 60;
  return hours
    ? `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`
    : `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

function textNode(tag, className, text) {
  const node = document.createElement(tag);
  node.className = className;
  node.textContent = text;
  return node;
}

function readableAnswer(text) {
  return text
    .replace(/\*\*/g, "")
    .replace(/`/g, "")
    .replace(/\[([^\]]+)]\(([^)]+)\)/g, "$1\n$2");
}

function renderTranscript(transcript) {
  activeTranscript = transcript;
  elements.copyDialog.disabled = !transcript.segments.length;
  elements.note.textContent = t("note.button", { time: timecodeLabel(transcript) });
  elements.meetingTitle.textContent = transcript.display_meeting || transcript.meeting || "Встреча";
  elements.liveStatus.classList.toggle("live", Boolean(transcript.live));
  elements.liveStatus.classList.toggle("error", Boolean(transcript.error));
  if (transcript.error) {
    elements.liveStatus.lastChild.textContent = t("status.waiting");
  } else if (transcript.live) {
    elements.liveStatus.lastChild.textContent = t("status.live");
  } else if (transcript.status === "finished") {
    elements.liveStatus.lastChild.textContent = t("status.finished");
  } else if (transcript.status === "loading") {
    elements.liveStatus.lastChild.textContent = t("status.model_loading");
  } else if (transcript.status === "model_missing") {
    elements.liveStatus.lastChild.textContent = t("status.model_missing");
  } else if (transcript.status === "overloaded") {
    elements.liveStatus.lastChild.textContent = t("status.overloaded");
  } else {
    elements.liveStatus.lastChild.textContent = t("status.no_fresh");
  }

  const signature = `${sourceFilter}:${transcript.meeting_id}:${transcript.updated_at}:${transcript.segments.length}:${transcript.translation_revision || 0}`;
  if (signature === transcriptSignature) return;
  transcriptSignature = signature;

  elements.transcriptMeta.textContent = transcript.error
    ? transcript.error
    : transcript.status === "overloaded"
      ? t("transcript.overloaded_meta", { age: ageLabel(transcript.latest_age_seconds) })
      : t("transcript.latest_meta", { age: ageLabel(transcript.latest_age_seconds) });

  const nearBottom =
    elements.transcript.scrollHeight - elements.transcript.scrollTop - elements.transcript.clientHeight < 120;
  const fragment = document.createDocumentFragment();
  const filtered = transcript.segments.filter(
    (segment) => sourceFilter === "all" || segment.source === sourceFilter,
  );

  if (!filtered.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.append(
      textNode("strong", "", transcript.error ? t("transcript.failed") : t("transcript.empty_title")),
      textNode(
        "span",
        "",
        transcript.error || t("transcript.empty_text"),
      ),
    );
    fragment.append(empty);
  } else {
    for (const segment of filtered) {
      const row = document.createElement("article");
      row.className = `utterance ${segment.source}`;
      row.dataset.timestamp = segment.timestamp;
      const speaker = textNode(
        "div",
        "speaker",
        segment.source === "microphone"
          ? t("speaker.me")
          : (segment.speaker || (segment.voice_id
            ? t("speaker.voice", { value: segment.voice_id.replace(/^remote-/, "") })
            : t("speaker.others"))),
      );
      if (segment.speaker_confidence === "acoustic-diarization" || segment.voice_id) {
        speaker.title = ["visual-active-speaker", "visual-voice-map"].includes(segment.speaker_confidence)
          ? t("speaker.name_hint")
          : t("speaker.voice_hint");
      } else if (segment.speaker_confidence) {
        speaker.title = t("speaker.name_hint");
      }
      const body = document.createElement("div");
      body.className = "body";
      if (segment.translation_en) {
        body.append(
          textNode("p", "translation", segment.translation_en),
          textNode("p", "text original", segment.text),
        );
      } else {
        body.append(textNode("p", "text", segment.text));
      }
      body.append(textNode("time", "", localTime(segment.timestamp)));
      row.append(speaker, body);
      fragment.append(row);
    }
  }

  elements.transcript.replaceChildren(fragment);
  if (nearBottom || !elements.transcript.dataset.initialized) {
    elements.transcript.scrollTop = elements.transcript.scrollHeight;
    elements.transcript.dataset.initialized = "true";
  }
}

function renderFrames(frames) {
  elements.frameCount.textContent = String(frames.length);
  const signature = JSON.stringify(frames);
  if (signature === frameSignature) return;
  frameSignature = signature;
  const fragment = document.createDocumentFragment();
  if (!frames.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state frames-empty";
    empty.append(
      textNode("strong", "", t("frames.empty_title")),
      textNode("span", "", t("frames.empty_text")),
    );
    fragment.append(empty);
  } else {
    for (const frame of frames) {
      const link = document.createElement("a");
      link.className = "frame-card";
      link.href = frame.url;
      link.target = "_blank";
      link.rel = "noopener";
      const image = document.createElement("img");
      image.src = frame.url;
      image.loading = "lazy";
      image.alt = frame.speaker
        ? t("frames.alt_speaker", { speaker: frame.speaker })
        : t("frames.alt");
      const caption = document.createElement("div");
      caption.className = "frame-caption";
      caption.append(
        textNode("strong", "", frame.speaker || t("frames.speaker_unknown")),
        textNode("time", "", localTime(frame.captured_at)),
      );
      link.append(image, caption);
      fragment.append(link);
    }
  }
  elements.framesGrid.replaceChildren(fragment);
}

function renderFrameStatus(status) {
  const value = status || {};
  elements.frameStatus.classList.toggle("error", Boolean(value.last_error));
  if (value.last_error) {
    elements.frameStatus.textContent = t("frames.error", { error: value.last_error });
  } else if (value.last_success_at) {
    elements.frameStatus.textContent = t("frames.ok", { time: localTime(value.last_success_at) });
  } else {
    elements.frameStatus.textContent = t("frames.armed");
  }
}

function renderMessages(copilot) {
  const signature = JSON.stringify(copilot.messages);
  if (signature === renderedMessages && copilot.busy === requestBusy) return;
  const wasInitialized = elements.chat.dataset.initialized === "true";
  const oldScrollTop = elements.chat.scrollTop;
  const distanceFromBottom = elements.chat.scrollHeight
    - elements.chat.scrollTop
    - elements.chat.clientHeight;
  const shouldFollowLatest = !wasInitialized || chatPinnedToLatest || distanceFromBottom < 72;
  renderedMessages = signature;
  const fragment = document.createDocumentFragment();

  if (!copilot.messages.length && !requestBusy) {
    fragment.append(elements.welcome);
    elements.welcome.hidden = false;
  } else {
    elements.welcome.hidden = true;
    for (const message of copilot.messages) {
      const article = document.createElement("article");
      article.className = `message ${message.role} ${message.kind || "answer"}`;
      const label = message.role === "user"
        ? t("message.you")
        : message.kind === "insight" ? t("message.autoanalysis") : "Copilot";
      article.append(
        textNode("div", "message-label", label),
        textNode("p", "message-text", readableAnswer(message.text)),
      );
      fragment.append(article);
    }
    if (requestBusy || copilot.busy) {
      const thinking = document.createElement("article");
      thinking.className = "message assistant";
      thinking.append(
        textNode("div", "message-label", "Copilot"),
        textNode("p", "message-text thinking", t("message.thinking")),
      );
      fragment.append(thinking);
    }
  }
  elements.chat.replaceChildren(fragment);
  if (shouldFollowLatest) {
    elements.chat.scrollTop = elements.chat.scrollHeight;
    chatPinnedToLatest = true;
  } else {
    elements.chat.scrollTop = oldScrollTop;
  }
  elements.chat.dataset.initialized = "true";
  updateChatLatestButton();
  elements.copilotMeta.textContent = copilot.error
    ? t("copilot.error", { error: copilot.error })
    : copilot.connected
      ? t("copilot.active")
      : t("copilot.disconnected");

  const analysis = copilot.analysis || {};
  const when = analysis.at ? ` · ${localTime(analysis.at)}` : "";
  if (analysis.state === "no_signal") {
    elements.analysisStatus.textContent = t("analysis.no_signal", { when });
  } else if (analysis.state === "signal") {
    elements.analysisStatus.textContent = t("analysis.signal", { when });
  } else if (analysis.state === "error") {
    elements.analysisStatus.textContent = t("analysis.error", {
      when,
      error: analysis.message || t("analysis.error_default"),
    });
  } else {
    elements.analysisStatus.textContent = t("analysis.initial");
  }
}

function repositoryProvider(repo) {
  const remotes = repo.remotes || [];
  const remoteText = remotes
    .map((item) => `${item.name || ""} ${item.url || ""}`)
    .join(" ")
    .toLowerCase();
  if (remoteText.includes("git.aiagentlbs.com")) {
    return { key: "gitlab-aiagentlbs", label: "GitLab · git.aiagentlbs.com", rank: 0 };
  }
  if (remoteText.includes("github.com")) {
    return { key: "github", label: "GitHub", rank: 2 };
  }
  if (remoteText.includes("gitlab")) {
    return { key: "gitlab", label: "GitLab", rank: 1 };
  }
  return { key: "other", label: t("provider.other"), rank: 3 };
}

function renderRepositoryCatalog() {
  const query = elements.repoSearch.value.trim().toLowerCase();
  const fragment = document.createDocumentFragment();
  const visible = repositoryCatalog
    .filter((repo) => {
      const remote = (repo.remotes || []).map((item) => item.url || "").join(" ");
      return `${repo.name} ${repo.path} ${remote}`.toLowerCase().includes(query);
    })
    .sort((left, right) => {
      const leftSelected = selectedRepositoryPaths.has(left.path) ? 0 : 1;
      const rightSelected = selectedRepositoryPaths.has(right.path) ? 0 : 1;
      if (leftSelected !== rightSelected) return leftSelected - rightSelected;
      const providerRank = repositoryProvider(left).rank - repositoryProvider(right).rank;
      if (providerRank) return providerRank;
      return left.name.localeCompare(right.name, "ru", { sensitivity: "base" });
    });
  let previousGroup = "";
  for (const repo of visible) {
    const selected = selectedRepositoryPaths.has(repo.path);
    const provider = repositoryProvider(repo);
    const group = selected ? "selected" : provider.key;
    if (group !== previousGroup) {
      const heading = selected
        ? t("repos.selected", { count: selectedRepositoryPaths.size })
        : provider.label;
      fragment.append(textNode("div", "repo-group-title", heading));
      previousGroup = group;
    }
    const label = document.createElement("label");
    label.className = `repo-row${selected ? " selected" : ""}`;
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = selected;
    checkbox.disabled = !checkbox.checked && selectedRepositoryPaths.size >= maxActiveRepositories;
    checkbox.addEventListener("change", () => {
      if (checkbox.checked) selectedRepositoryPaths.add(repo.path);
      else selectedRepositoryPaths.delete(repo.path);
      renderRepositoryCatalog();
    });
    const text = document.createElement("span");
    text.className = "repo-row-text";
    const title = document.createElement("span");
    title.className = "repo-title";
    title.append(
      textNode("strong", "", repo.name),
      textNode("span", `repo-provider ${provider.key}`, provider.label),
    );
    text.append(
      title,
      textNode("span", "repo-path", repo.path),
    );
    const remote = (repo.remotes || [])[0]?.url;
    if (remote) text.append(textNode("span", "repo-remote", remote));
    label.append(checkbox, text);
    fragment.append(label);
  }
  if (!visible.length) {
    fragment.append(textNode("div", "repo-empty", t("repos.empty")));
  }
  elements.repoList.replaceChildren(fragment);
  elements.repoSelectionCount.textContent = t("repos.selection_count", {
    count: selectedRepositoryPaths.size,
    max: maxActiveRepositories,
  });
  elements.repoSave.disabled = selectedRepositoryPaths.size < 1 || selectedRepositoryPaths.size > maxActiveRepositories;
}

function renderProjectOptions() {
  const fragment = document.createDocumentFragment();
  let previousGroup = "";
  for (const choice of projectChoices) {
    const group = choice.kind === "project" ? "projects"
      : choice.kind === "repository" ? "repositories" : "modes";
    if (group !== previousGroup) {
      fragment.append(textNode("div", "project-group-title", t(`project.group_${group}`)));
      previousGroup = group;
    }
    const button = document.createElement("button");
    button.type = "button";
    button.className = `project-option${choice.value === projectSelection ? " selected" : ""}`;
    button.disabled = !projectMeetingId;
    const label = choice.kind === "auto" ? t("project.auto")
      : choice.kind === "all" ? t("project.all")
        : choice.kind === "repository" ? t("project.only_repo", { name: choice.name })
          : choice.name;
    const detail = choice.kind === "auto" ? t("project.auto_detail")
      : choice.kind === "all" ? t("project.all_detail", {
          count: repositoryCountLabel(choice.repositories.length),
        }) : choice.repositories.join(" · ");
    button.append(
      textNode("strong", "project-option-name", label),
      textNode("span", "project-option-detail", detail),
    );
    if (choice.value === projectSelection) {
      button.append(textNode("span", "project-option-selected", t("project.selected")));
    }
    button.addEventListener("click", () => void chooseProject(choice.value));
    fragment.append(button);
  }
  elements.projectOptions.replaceChildren(fragment);
}

async function openProjectDialog() {
  elements.projectHelp.textContent = t("project.loading");
  elements.projectHelp.classList.remove("error");
  elements.projectDialog.showModal();
  try {
    const response = await fetch("/api/projects", { cache: "no-store" });
    const data = await response.json();
    if (!response.ok || !data.ok) throw new Error(data.error || `HTTP ${response.status}`);
    projectMeetingId = data.meeting_id || "";
    projectChoices = data.choices || [];
    projectSelection = data.selection || "auto";
    const count = projectChoices.find((choice) => choice.kind === "all")?.repositories.length || 0;
    elements.projectHelp.textContent = projectMeetingId
      ? t("project.choose_help", { count: repositoryCountLabel(count) })
      : t("project.no_meeting");
    renderProjectOptions();
  } catch (error) {
    elements.projectHelp.textContent = String(error);
    elements.projectHelp.classList.add("error");
  }
}

async function chooseProject(selection) {
  elements.projectHelp.textContent = t("project.saving");
  elements.projectOptions.querySelectorAll("button").forEach((button) => { button.disabled = true; });
  try {
    await post("/api/project", { meeting_id: projectMeetingId, selection });
    projectSelection = selection;
    elements.projectDialog.close();
    autoAnalysisPrimed = "";
    await state();
  } catch (error) {
    elements.projectHelp.textContent = String(error);
    elements.projectHelp.classList.add("error");
    renderProjectOptions();
  }
}

async function openRepositoryDialog() {
  elements.repoHelp.textContent = t("repos.loading");
  elements.repoHelp.classList.remove("error");
  elements.repoDialog.showModal();
  try {
    const response = await fetch("/api/repositories", { cache: "no-store" });
    const data = await response.json();
    if (!response.ok || !data.ok) throw new Error(data.error || `HTTP ${response.status}`);
    repositoryCatalog = data.repositories || [];
    selectedRepositoryPaths = new Set(data.active_paths || []);
    maxActiveRepositories = data.max_active || 15;
    elements.repoSearch.value = "";
    const aiAgentLabsGitLab = repositoryCatalog.filter(
      (repo) => repositoryProvider(repo).key === "gitlab-aiagentlbs",
    ).length;
    elements.repoHelp.textContent = t("repos.loaded", { count: aiAgentLabsGitLab });
    renderRepositoryCatalog();
    elements.repoSearch.focus();
  } catch (error) {
    elements.repoHelp.textContent = String(error);
    elements.repoHelp.classList.add("error");
  }
}

async function saveRepositorySelection() {
  elements.repoSave.disabled = true;
  elements.repoHelp.textContent = t("repos.saving");
  elements.repoHelp.classList.remove("error");
  try {
    await post("/api/repositories", { paths: [...selectedRepositoryPaths] });
    elements.repoDialog.close();
    await state();
  } catch (error) {
    elements.repoHelp.textContent = String(error);
    elements.repoHelp.classList.add("error");
    elements.repoSave.disabled = false;
  }
}

function renderJournal(items) {
  for (const [group, categories] of Object.entries(journalGroups)) {
    if (elements.journalCounts[group]) {
      elements.journalCounts[group].textContent = String(
        items.filter((item) => categories.has(item.category)).length,
      );
    }
  }
  const signature = `${journalFilter}:${JSON.stringify(items)}`;
  if (signature === journalSignature) return;
  journalSignature = signature;
  const accepted = journalGroups[journalFilter];
  const visible = accepted ? items.filter((item) => accepted.has(item.category)) : items;
  const fragment = document.createDocumentFragment();

  if (!visible.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state journal-empty";
    empty.append(
      textNode("strong", "", t("journal.empty_title")),
      textNode("span", "", t("journal.empty_text")),
    );
    fragment.append(empty);
  } else {
    for (const item of visible) {
      const card = document.createElement("article");
      card.className = `journal-card ${item.category.toLowerCase()}`;
      const header = document.createElement("div");
      header.className = "journal-card-header";
      const kind = document.createElement("div");
      kind.className = "journal-kind-wrap";
      const signal = trafficSignal(item.category);
      if (signal) kind.append(trafficLight(signal));
      kind.append(textNode(
        "span",
        "journal-kind",
        journalLabels[uiLanguage][item.category] || item.category,
      ));
      header.append(kind);
      const timing = document.createElement("div");
      timing.className = "journal-timing";
      if (item.timecode && item.anchor_at) {
        const anchor = document.createElement("button");
        anchor.type = "button";
        anchor.className = "timecode-link";
        anchor.textContent = `@ ${item.timecode.replace(/^00:/, "")}`;
        anchor.title = t("journal.anchor_title");
        anchor.addEventListener("click", () => jumpToTranscript(item.anchor_at));
        timing.append(anchor);
      }
      timing.append(textNode("time", "", localTime(item.created_at)));
      header.append(timing);
      card.append(
        header,
        textNode("p", "journal-text", readableAnswer(item.text)),
        textNode("div", "journal-meeting", item.meeting || t("meeting.no_title")),
      );
      fragment.append(card);
    }
  }
  elements.journalList.replaceChildren(fragment);
}

function trafficSignal(category) {
  if (["RISK", "CONTRADICTION"].includes(category)) return "red";
  if (["QUESTION", "ASK"].includes(category)) return "yellow";
  if (["DECISION", "COMMITMENT"].includes(category)) return "green";
  return "";
}

function trafficLight(active) {
  const light = document.createElement("span");
  light.className = `traffic-light active-${active}`;
  light.setAttribute("role", "img");
  light.setAttribute("aria-label", t(`traffic.${active}`));
  light.title = t(`traffic.${active}`);
  for (const color of ["red", "yellow", "green"]) {
    light.append(textNode("i", color, ""));
  }
  return light;
}

function transcriptDialogue(transcript) {
  if (!transcript?.segments?.length) return "";
  const lines = transcript.segments.map((segment) => {
    const speaker = segment.source === "microphone"
      ? t("speaker.me")
      : (segment.speaker || (segment.voice_id
        ? t("speaker.voice", { value: segment.voice_id.replace(/^remote-/, "") })
        : t("speaker.others")));
    const spoken = `[${localTime(segment.timestamp)}] ${speaker}: ${segment.text}`;
    return segment.translation_en ? `${spoken}\nEN: ${segment.translation_en}` : spoken;
  });
  return `${transcript.display_meeting || transcript.meeting || "Встреча"}\n\n${lines.join("\n")}`;
}

async function writeClipboard(text) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return;
  }
  const helper = document.createElement("textarea");
  helper.value = text;
  helper.setAttribute("readonly", "");
  helper.style.position = "fixed";
  helper.style.opacity = "0";
  document.body.append(helper);
  helper.select();
  const copied = document.execCommand("copy");
  helper.remove();
  if (!copied) throw new Error("clipboard unavailable");
}

async function copyDialogue() {
  const text = transcriptDialogue(activeTranscript);
  const original = t("transcript.copy");
  if (!text) {
    elements.copyDialog.textContent = t("transcript.copy_empty");
  } else {
    try {
      await writeClipboard(text);
      elements.copyDialog.textContent = t("transcript.copied");
      elements.copyDialog.classList.add("copied");
    } catch (_error) {
      elements.copyDialog.textContent = t("transcript.copy_failed");
    }
  }
  setTimeout(() => {
    elements.copyDialog.textContent = original;
    elements.copyDialog.classList.remove("copied");
  }, 1800);
}

function jumpToTranscript(anchorAt) {
  transcriptView = "transcript";
  document.querySelectorAll("[data-transcript-view]").forEach((item) => {
    item.classList.toggle("active", item.dataset.transcriptView === "transcript");
  });
  elements.transcript.hidden = false;
  elements.frames.hidden = true;
  elements.speakerFilters.hidden = false;
  sourceFilter = "all";
  document.querySelectorAll(".segmented button").forEach((item) => {
    item.classList.toggle("active", item.dataset.source === "all");
  });
  transcriptSignature = "";
  if (activeTranscript) renderTranscript(activeTranscript);

  const target = new Date(anchorAt).getTime();
  const rows = [...elements.transcript.querySelectorAll("[data-timestamp]")];
  if (Number.isNaN(target) || !rows.length) return;
  const nearest = rows.reduce((best, row) => {
    const distance = Math.abs(new Date(row.dataset.timestamp).getTime() - target);
    return !best || distance < best.distance ? { row, distance } : best;
  }, null);
  if (!nearest) return;
  nearest.row.scrollIntoView({ behavior: "smooth", block: "center" });
  nearest.row.classList.add("time-anchor");
  setTimeout(() => nearest.row.classList.remove("time-anchor"), 2400);
}

function renderMeetingChat(items) {
  elements.meetingChatCount.textContent = String(items.length);
  const signature = JSON.stringify(items);
  if (signature === meetingChatSignature) return;
  meetingChatSignature = signature;
  const fragment = document.createDocumentFragment();
  if (!items.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state journal-empty";
    empty.append(
      textNode("strong", "", t("meeting_chat.empty_title")),
      textNode("span", "", t("meeting_chat.empty_text")),
    );
    fragment.append(empty);
  } else {
    for (const item of items) {
      const card = document.createElement("article");
      card.className = "meeting-chat-card";
      const header = document.createElement("div");
      header.className = "meeting-chat-card-header";
      header.append(
        textNode("strong", "", item.sender || t("meeting_chat.participant")),
        textNode("time", "", item.displayed_at || localTime(item.captured_at)),
      );
      card.append(header, textNode("p", "", item.text || ""));
      fragment.append(card);
    }
  }
  elements.meetingChatList.replaceChildren(fragment);
  elements.meetingChatList.scrollTop = elements.meetingChatList.scrollHeight;
}

function archiveDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(uiLanguage === "ru" ? "ru-RU" : "en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function archiveDay(value) {
  const date = new Date(value || "");
  if (Number.isNaN(date.getTime())) {
    return { key: "unknown", label: t("archive.unknown_day") };
  }
  const key = [date.getFullYear(), String(date.getMonth() + 1).padStart(2, "0"),
    String(date.getDate()).padStart(2, "0")].join("-");
  const label = new Intl.DateTimeFormat(uiLanguage === "ru" ? "ru-RU" : "en-GB", {
    dateStyle: "full",
  }).format(date);
  return { key, label };
}

function archiveDuration(seconds) {
  const total = Math.max(0, Number(seconds) || 0);
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  return `${hours ? `${hours}:` : ""}${String(minutes).padStart(hours ? 2 : 1, "0")}:${String(Math.floor(total % 60)).padStart(2, "0")}`;
}

async function openArchive() {
  if (!elements.archiveDialog.open) elements.archiveDialog.showModal();
  elements.archiveList.replaceChildren(textNode("div", "archive-loading", "…"));
  try {
    const response = await fetch("/api/archive", { cache: "no-store" });
    const data = await response.json();
    if (!response.ok || !data.ok) throw new Error(data.error || `HTTP ${response.status}`);
    archiveMeetings = data.meetings || [];
    renderArchiveList();
    const preferred = selectedArchiveMeeting || archiveMeetings[0]?.meeting_id;
    if (preferred) await loadArchiveMeeting(preferred);
  } catch (error) {
    elements.archiveList.replaceChildren(textNode("div", "archive-error", String(error)));
  }
}

function renderArchiveList() {
  elements.archiveDescription.textContent = archiveMeetings.length
    ? t("archive.count_description", { count: archiveMeetings.length })
    : t("archive.description");
  if (!archiveMeetings.length) {
    elements.archiveList.replaceChildren(textNode("div", "archive-empty", t("archive.empty")));
    return;
  }
  const fragment = document.createDocumentFragment();
  let currentDay = "";
  for (const meeting of archiveMeetings) {
    const day = archiveDay(meeting.started_at);
    if (day.key !== currentDay) {
      currentDay = day.key;
      const heading = textNode("h3", "archive-day-heading", day.label);
      fragment.append(heading);
    }
    const button = document.createElement("button");
    button.type = "button";
    button.className = "archive-item";
    button.classList.toggle("active", meeting.meeting_id === selectedArchiveMeeting);
    button.append(
      textNode("strong", "archive-item-title", meeting.title),
      textNode("span", "archive-item-date", archiveDate(meeting.started_at)),
      textNode("span", "archive-item-counts", [
        `${meeting.transcript_count} ${t("archive.utterances")}`,
        `${meeting.journal_count} ${t("archive.notes")}`,
        `${meeting.frame_count} ${t("archive.frames")}`,
      ].join(" · ")),
    );
    button.addEventListener("click", () => void loadArchiveMeeting(meeting.meeting_id));
    fragment.append(button);
  }
  elements.archiveList.replaceChildren(fragment);
}

function archiveSection(title, count, content, open = false) {
  const section = document.createElement("details");
  section.className = "archive-section";
  section.open = open;
  const summary = document.createElement("summary");
  summary.append(
    textNode("span", "", title),
    textNode("span", "archive-section-count", String(count)),
  );
  section.append(summary, content);
  return section;
}

function renderArchiveDetail(meeting) {
  const root = document.createDocumentFragment();
  const heading = document.createElement("div");
  heading.className = "archive-detail-heading";
  heading.append(
    textNode("h2", "", meeting.title),
    textNode("p", "", `${archiveDate(meeting.started_at)} · ${archiveDuration(meeting.duration_seconds)}`),
  );
  root.append(heading);

  const report = document.createElement("section");
  report.className = "archive-report-card";
  report.append(textNode("strong", "", t("archive.report")));
  const reportActions = document.createElement("div");
  reportActions.className = "archive-report-actions";
  if (meeting.report?.html && meeting.report?.pdf) {
    for (const [label, href] of [[t("archive.open_html"), meeting.report.html], [t("archive.open_pdf"), meeting.report.pdf]]) {
      const link = document.createElement("a");
      link.href = href;
      link.target = "_blank";
      link.rel = "noopener";
      link.textContent = label;
      reportActions.append(link);
    }
  }
  const generate = document.createElement("button");
  generate.type = "button";
  generate.className = "send-button";
  generate.textContent = t("archive.generate");
  generate.disabled = !(
    meeting.transcript?.length || meeting.journal?.length || meeting.frames?.length
  );
  generate.addEventListener("click", () => void generateArchiveReport(meeting.meeting_id, generate));
  reportActions.append(generate);
  const copy = document.createElement("button");
  copy.type = "button";
  copy.className = "quiet-button copy-dialog-button";
  copy.textContent = t("archive.copy_dialog");
  copy.disabled = !meeting.transcript?.length;
  copy.addEventListener("click", async () => {
    try {
      await writeClipboard(transcriptDialogue({
        meeting: meeting.title,
        segments: meeting.transcript || [],
      }));
      copy.textContent = t("transcript.copied");
      copy.classList.add("copied");
    } catch (_error) {
      copy.textContent = t("transcript.copy_failed");
    }
    setTimeout(() => {
      copy.textContent = t("archive.copy_dialog");
      copy.classList.remove("copied");
    }, 1800);
  });
  reportActions.append(copy);
  report.append(reportActions);
  const delivery = document.createElement("p");
  delivery.className = "archive-delivery";
  const statuses = [];
  if (meeting.report?.drive_status === "uploaded") statuses.push(t("archive.drive_uploaded"));
  else if (meeting.report?.drive_status === "auth_required") statuses.push(t("archive.drive_auth"));
  if (meeting.report?.mail_status === "sent") statuses.push(t("archive.mail_sent"));
  else if (meeting.report?.mail_status) statuses.push(t("archive.mail_pending"));
  delivery.textContent = statuses.join(" · ");
  report.append(delivery);
  root.append(report);

  const journal = document.createElement("div");
  journal.className = "archive-journal";
  for (const item of meeting.journal || []) {
    const card = document.createElement("article");
    card.className = `journal-card ${(item.category || "").toLowerCase()}`;
    const kind = document.createElement("div");
    kind.className = "journal-kind-wrap";
    const signal = trafficSignal(item.category);
    if (signal) kind.append(trafficLight(signal));
    kind.append(textNode(
      "strong",
      "journal-kind",
      journalLabels[uiLanguage][item.category] || item.category,
    ));
    card.append(
      kind,
      textNode("span", "journal-timing", item.timecode || localTime(item.created_at)),
      textNode("p", "journal-text", readableAnswer(item.text)),
    );
    journal.append(card);
  }
  root.append(archiveSection(t("archive.summary"), meeting.journal?.length || 0, journal, true));

  const frameGrid = document.createElement("div");
  frameGrid.className = "archive-frame-grid";
  for (const frame of meeting.frames || []) {
    const link = document.createElement("a");
    link.href = frame.url;
    link.target = "_blank";
    link.rel = "noopener";
    const image = document.createElement("img");
    image.loading = "lazy";
    image.src = frame.url;
    image.alt = frame.speaker || t("frames.alt");
    link.append(image, textNode("span", "", `${frame.speaker || t("frames.speaker_unknown")} · ${localTime(frame.captured_at)}`));
    frameGrid.append(link);
  }
  root.append(archiveSection(t("archive.screenshots"), meeting.frames?.length || 0, frameGrid));

  const meetingChat = document.createElement("div");
  meetingChat.className = "archive-chat";
  for (const item of meeting.meeting_chat || []) {
    const card = document.createElement("article");
    card.append(
      textNode("strong", "", item.sender || t("meeting_chat.participant")),
      textNode("time", "", item.displayed_at || localTime(item.captured_at)),
      textNode("p", "", item.text),
    );
    meetingChat.append(card);
  }
  root.append(archiveSection(t("archive.meeting_chat"), meeting.meeting_chat?.length || 0, meetingChat));

  const transcript = document.createElement("div");
  transcript.className = "archive-transcript";
  if (!meeting.transcript?.length) {
    transcript.append(textNode("p", "archive-empty", t("archive.no_transcript")));
  }
  for (const item of meeting.transcript || []) {
    const row = document.createElement("article");
    const speaker = item.speaker || (item.source === "microphone" ? t("speaker.me") : t("speaker.others"));
    row.append(
      textNode("strong", "", speaker),
      textNode("time", "", localTime(item.timestamp)),
      textNode("p", "", item.text),
    );
    transcript.append(row);
  }
  root.append(archiveSection(t("archive.transcript"), meeting.transcript?.length || 0, transcript));
  elements.archiveDetail.replaceChildren(root);
}

async function loadArchiveMeeting(meetingId) {
  selectedArchiveMeeting = meetingId;
  renderArchiveList();
  elements.archiveDetail.replaceChildren(textNode("div", "archive-loading", "…"));
  try {
    const response = await fetch(`/api/archive/${encodeURIComponent(meetingId)}`, { cache: "no-store" });
    const data = await response.json();
    if (!response.ok || !data.ok) throw new Error(data.error || `HTTP ${response.status}`);
    renderArchiveDetail(data.meeting);
  } catch (error) {
    elements.archiveDetail.replaceChildren(textNode("div", "archive-error", String(error)));
  }
}

async function generateArchiveReport(meetingId, button) {
  button.disabled = true;
  button.textContent = t("archive.generating");
  try {
    await post("/api/archive/report", { meeting_id: meetingId });
    await openArchive();
  } catch (error) {
    button.textContent = String(error).replace(/^Error:\s*/, "");
  } finally {
    button.disabled = false;
  }
}

async function state() {
  if (stateRequestInFlight) return;
  stateRequestInFlight = true;
  try {
    const response = await fetch("/api/state", { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    const project = data.project || {};
    const scopedRepositories = project.repositories || [];
    const count = repositoryCountLabel(scopedRepositories.length || data.repositories || 0);
    const projectKind = project.kind || "all";
    const hint = projectKind === "all" ? "project.all_hint"
      : project.confidence === "manual" ? "project.manual_hint" : "project.auto_hint";
    elements.repoStatus.textContent = projectKind === "all"
      ? t("project.all_scope", { count })
      : projectKind === "repository"
        ? t("project.repository_scope", { project: project.name })
        : t(project.confidence === "manual" ? "project.manual_scope" : "project.auto_scope", {
            project: project.name,
            count,
          });
    const repositoryList = scopedRepositories
      .map((repo) => `${repo.name}: ${repo.path}`)
      .join("\n");
    elements.repoStatus.title = `${t(hint)}\n${repositoryList}`;
    renderTranscript(data.transcript);
    renderFrames(data.frames || []);
    renderFrameStatus(data.frame_capture || {});
    renderMessages(data.copilot);
    renderJournal(data.journal || []);
    renderMeetingChat(data.meeting_chat || []);
    elements.send.disabled = requestBusy || data.copilot.busy;
    elements.analyze.disabled = requestBusy || data.copilot.busy;
    if (stateConnectionFailed && !requestBusy) {
      elements.help.textContent = t("help.codex");
      elements.help.classList.remove("error");
    }
    stateConnectionFailed = false;

    const finishedWithoutAnalysis = data.transcript.status === "finished"
      && data.transcript.segments.length > 0
      && data.copilot.messages.length === 0
      && data.copilot.analysis?.state === "idle";
    const analysisKey = `${data.transcript.meeting_id}:${data.transcript.status}:${data.transcript.latest_at}`;
    if (
      elements.autoAnalysis.checked &&
      (data.transcript.live || finishedWithoutAnalysis) &&
      data.transcript.latest_at &&
      analysisKey !== autoAnalysisPrimed &&
      !requestBusy &&
      !data.copilot.busy
    ) {
      autoAnalysisPrimed = analysisKey;
      void analyze(finishedWithoutAnalysis);
    }
  } catch (error) {
    stateConnectionFailed = true;
    elements.liveStatus.classList.add("error");
    elements.liveStatus.lastChild.textContent = t("ui.disconnected");
    elements.help.textContent = String(error);
    elements.help.classList.add("error");
  } finally {
    stateRequestInFlight = false;
  }
}

async function post(path, payload) {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok || !data.ok) throw new Error(data.error || `HTTP ${response.status}`);
  return data;
}

async function ask(question) {
  const clean = question.trim();
  if (!clean || requestBusy) return;
  requestBusy = true;
  elements.question.value = "";
  elements.help.textContent = t("help.codex");
  elements.help.classList.remove("error");
  const pending = document.createElement("article");
  pending.className = "message user";
  pending.append(
    textNode("div", "message-label", t("message.you")),
    textNode("p", "message-text", clean),
  );
  elements.chat.append(pending);
  elements.chat.scrollTop = elements.chat.scrollHeight;
  chatPinnedToLatest = true;
  updateChatLatestButton();
  try {
    await post("/api/chat", { question: clean });
  } catch (error) {
    elements.help.textContent = String(error);
    elements.help.classList.add("error");
  } finally {
    requestBusy = false;
    await state();
  }
}

async function saveNote() {
  const clean = elements.question.value.trim();
  if (!clean || noteBusy) return;
  noteBusy = true;
  elements.note.disabled = true;
  elements.help.textContent = t("note.saving");
  elements.help.classList.remove("error");
  try {
    const data = await post("/api/note", { text: clean });
    elements.question.value = "";
    const timecode = data.note?.timecode?.replace(/^00:/, "") || t("note.current");
    elements.help.textContent = t("note.saved", { time: timecode });
    journalSignature = "";
    await state();
  } catch (error) {
    elements.help.textContent = String(error);
    elements.help.classList.add("error");
  } finally {
    noteBusy = false;
    elements.note.disabled = false;
  }
}

async function analyze(force) {
  if (requestBusy) return;
  requestBusy = true;
  elements.help.textContent = force ? t("analysis.searching") : t("analysis.checking");
  elements.help.classList.remove("error");
  try {
    await post("/api/analyze", { force });
  } catch (error) {
    elements.help.textContent = String(error);
    elements.help.classList.add("error");
  } finally {
    requestBusy = false;
    await state();
  }
}

document.querySelectorAll(".segmented button").forEach((button) => {
  button.addEventListener("click", () => {
    sourceFilter = button.dataset.source;
    transcriptSignature = "";
    document.querySelectorAll(".segmented button").forEach((item) => {
      item.classList.toggle("active", item === button);
    });
    void state();
  });
});

document.querySelectorAll("[data-transcript-view]").forEach((button) => {
  button.addEventListener("click", () => {
    transcriptView = button.dataset.transcriptView;
    const framesOpen = transcriptView === "frames";
    document.querySelectorAll("[data-transcript-view]").forEach((item) => {
      item.classList.toggle("active", item === button);
    });
    elements.transcript.hidden = framesOpen;
    elements.frames.hidden = !framesOpen;
    elements.speakerFilters.hidden = framesOpen;
  });
});

document.querySelectorAll(".suggestions button").forEach((button) => {
  button.addEventListener("click", () => {
    elements.question.value = button.textContent;
    elements.question.focus();
  });
});

document.querySelectorAll("[data-content-view]").forEach((button) => {
  button.addEventListener("click", () => {
    const view = button.dataset.contentView;
    document.querySelectorAll("[data-content-view]").forEach((item) => {
      item.classList.toggle("active", item === button);
      item.setAttribute("aria-selected", String(item === button));
    });
    const journalView = Object.hasOwn(journalGroups, view);
    if (journalView) {
      journalFilter = view;
      journalSignature = "";
      void state();
    }
    elements.chat.hidden = view !== "chat";
    elements.journal.hidden = !journalView;
    elements.meetingChat.hidden = view !== "meeting-chat";
    elements.chatLatest.hidden = view !== "chat" || chatPinnedToLatest;
  });
});

function updateChatLatestButton() {
  const distance = elements.chat.scrollHeight
    - elements.chat.scrollTop
    - elements.chat.clientHeight;
  chatPinnedToLatest = distance < 72;
  elements.chatLatest.hidden = elements.chat.hidden || chatPinnedToLatest;
}

elements.chat.addEventListener("scroll", updateChatLatestButton, { passive: true });
elements.chatLatest.addEventListener("click", () => {
  chatPinnedToLatest = true;
  elements.chat.scrollTo({ top: elements.chat.scrollHeight, behavior: "smooth" });
  updateChatLatestButton();
});

elements.form.addEventListener("submit", (event) => {
  event.preventDefault();
  void ask(elements.question.value);
});

elements.question.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
    event.preventDefault();
    void saveNote();
    return;
  }
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    void ask(elements.question.value);
  }
});

elements.note.addEventListener("click", () => void saveNote());
elements.copyDialog.addEventListener("click", () => void copyDialogue());

elements.refresh.addEventListener("click", async () => {
  elements.refresh.disabled = true;
  try {
    await post("/api/refresh", {});
    setTimeout(() => void state(), 1400);
  } finally {
    setTimeout(() => { elements.refresh.disabled = false; }, 1800);
  }
});

elements.analyze.addEventListener("click", () => void analyze(true));
elements.captureFrame.addEventListener("click", async () => {
  elements.captureFrame.disabled = true;
  elements.captureFrame.textContent = t("frames.capturing");
  try {
    await post("/api/capture-frame", {});
    frameSignature = "";
    await state();
  } catch (error) {
    elements.captureFrame.textContent = String(error).replace(/^Error:\s*/, "");
    setTimeout(() => { elements.captureFrame.textContent = t("frames.capture"); }, 3000);
  } finally {
    elements.captureFrame.disabled = false;
    if (elements.captureFrame.textContent === t("frames.capturing")) {
      elements.captureFrame.textContent = t("frames.capture");
    }
  }
});
elements.repoStatus.addEventListener("click", () => void openProjectDialog());
elements.projectClose.addEventListener("click", () => elements.projectDialog.close());
elements.projectDialog.addEventListener("click", (event) => {
  if (event.target === elements.projectDialog) elements.projectDialog.close();
});
elements.projectEditRepos.addEventListener("click", () => {
  elements.projectDialog.close();
  void openRepositoryDialog();
});
elements.archiveButton.addEventListener("click", () => void openArchive());
elements.archiveClose.addEventListener("click", () => elements.archiveDialog.close());
elements.archiveDialog.addEventListener("click", (event) => {
  if (event.target === elements.archiveDialog) elements.archiveDialog.close();
});
elements.repoSearch.addEventListener("input", renderRepositoryCatalog);
elements.repoSave.addEventListener("click", () => void saveRepositorySelection());

elements.reset.addEventListener("click", async () => {
  if (requestBusy) return;
  await post("/api/reset", {});
  renderedMessages = "";
  await state();
});

document.querySelectorAll("[data-language]").forEach((button) => {
  button.addEventListener("click", () => {
    const language = button.dataset.language === "en" ? "en" : "ru";
    if (language === uiLanguage) return;
    uiLanguage = language;
    localStorage.setItem("meeting-copilot-language", uiLanguage);
    applyLanguage();
    transcriptSignature = "";
    frameSignature = "";
    renderedMessages = "";
    journalSignature = "";
    meetingChatSignature = "";
    if (elements.archiveDialog.open) void openArchive();
    if (elements.projectDialog.open) {
      renderProjectOptions();
      const count = projectChoices.find((choice) => choice.kind === "all")?.repositories.length || 0;
      elements.projectHelp.textContent = t("project.choose_help", {
        count: repositoryCountLabel(count),
      });
    }
    void state();
  });
});

applyLanguage();
void state();
setInterval(() => void state(), 2500);
window.addEventListener("online", () => void state());
document.addEventListener("visibilitychange", () => {
  if (!document.hidden) void state();
});
