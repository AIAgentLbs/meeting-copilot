const elements = {
  swapPanels: document.querySelector("#swap-panels"),
  meetingTitle: document.querySelector("#meeting-title"),
  liveStatus: document.querySelector("#live-status"),
  captureStatus: document.querySelector("#capture-status"),
  recognitionNotice: document.querySelector("#recognition-notice"),
  recognitionNoticeText: document.querySelector("#recognition-notice-text"),
  recognitionResume: document.querySelector("#recognition-resume"),
  repoStatus: document.querySelector("#repo-button"),
  archiveButton: document.querySelector("#archive-button"),
  deliveryAlert: document.querySelector("#delivery-alert"),
  deliverySummary: document.querySelector("#delivery-summary"),
  deliveryChannels: document.querySelector("#delivery-channels"),
  deliveryNotice: document.querySelector("#delivery-notice"),
  deliveryNoticeText: document.querySelector("#delivery-notice-text"),
  deliveryNoticeDetails: document.querySelector("#delivery-notice-details"),
  deliveryNoticeDismiss: document.querySelector("#delivery-notice-dismiss"),
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
  speakerEdit: document.querySelector("#speaker-edit"),
  speakerDialog: document.querySelector("#speaker-dialog"),
  speakerEditClose: document.querySelector("#speaker-edit-close"),
  speakerNameList: document.querySelector("#speaker-name-list"),
  speakerUtteranceList: document.querySelector("#speaker-utterance-list"),
  speakerEditHelp: document.querySelector("#speaker-edit-help"),
  speakerEditStatus: document.querySelector("#speaker-edit-status"),
  speakerSelectionCount: document.querySelector("#speaker-selection-count"),
  speakerAssignmentTarget: document.querySelector("#speaker-assignment-target"),
  speakerAssignmentName: document.querySelector("#speaker-assignment-name"),
  speakerAssignmentSave: document.querySelector("#speaker-assignment-save"),
  speakerSelectPending: document.querySelector("#speaker-select-pending"),
  speakerSelectClear: document.querySelector("#speaker-select-clear"),
  translationJump: document.querySelector("#translation-jump"),
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
  callPlan: document.querySelector("#call-plan"),
  callBoard: document.querySelector("#call-board"),
  callPlanTab: document.querySelector("#call-plan-tab"),
  callPlanCount: document.querySelector("#call-plan-count"),
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
    "delivery.auth_required": "Почта: нужен вход · {count}",
    "delivery.pending": "Почта: не отправлено · {count}",
    "delivery.hint": "Отчёты сохранены локально. Откройте историю встреч для статуса доставки.",
    "language.label": "Язык интерфейса",
    "aria.transcript_view": "Вид левой панели",
    "aria.speaker_filter": "Фильтр участников",
    "aria.copilot_view": "Режим правой панели",
    "aria.journal_filter": "Фильтр журнала",
    "aria.workspace_filter": "Чат и сигналы встречи",
    "common.refresh": "Обновить",
    "nav.swap_panels": "Поменять панели",
    "common.close": "Закрыть",
    "common.cancel": "Отмена",
    "transcript.heading": "Ход созвона",
    "transcript.loading": "Получаю последние реплики",
    "transcript.tab": "Стенограмма",
    "transcript.copy": "Копировать диалог",
    "transcript.copied": "Диалог скопирован",
    "transcript.copy_empty": "Нет реплик для копирования",
    "transcript.copy_failed": "Не удалось скопировать",
    "transcript.translation_jump": "EN: {count} · к последнему",
    "transcript.translation_hint": "Последний перевод: {time}. Новые реплики на английском не переводятся.",
    "frames.tab": "Кадры",
    "speaker.all": "Все",
    "speakers.open": "Имена",
    "speakers.title": "Участники и реплики",
    "speakers.help": "Имя меняется во всей встрече. Если два голоса слиплись, выберите реплики и назначьте участника.",
    "speakers.rename_title": "Переименовать во всей встрече",
    "speakers.assign_title": "Исправить, кто говорит",
    "speakers.select_pending": "Выбрать неразмеченные",
    "speakers.clear_selection": "Снять выбор",
    "speakers.selected": "Выбрано: {count}",
    "speakers.target": "Кто говорит",
    "speakers.new_name": "Или новое имя",
    "speakers.assign": "Назначить выбранным",
    "speakers.rename": "Переименовать все",
    "speakers.saved": "Сохранено. Имена обновлены в стенограмме и архиве; отчёт обновится автоматически.",
    "speakers.pending": "Разметить",
    "speakers.edit_hint": "Нажмите, чтобы переименовать спикера или изменить автора реплики",
    "speaker.me": "Я",
    "speaker.unverified": "Голос не подтверждён",
    "speaker.unverified_short": "Неясно",
    "transcript.capture_lost": "Потеря аудио",
    "transcript.capture_lost_hint": "Системная дорожка пропала. На отмеченном участке нельзя уверенно определить, кто говорит.",
    "speaker.others": "Собеседники",
    "transcript.empty_title": "Жду стенограмму",
    "transcript.empty_text": "Meeting Copilot передаёт локальную расшифровку примерно раз в секунду.",
    "frames.local_note": "Кадры хранятся только локально вместе с записью.",
    "frames.capture": "Снять кадр сейчас",
    "frames.armed": "Съёмка готова.",
    "frames.ok": "Последний кадр: {time}.",
    "frames.error": "Ошибка съёмки: {error}",
    "copilot.heading": "Карта звонка и помощник",
    "copilot.meta": "Codex читает стенограмму и локальные Git-репозитории",
    "view.chat": "Чат",
    "plan.tab": "Подготовка",
    "plan.links": "Материалы",
    "plan.question": "Вопросы",
    "plan.risk": "Риски",
    "plan.objection": "Возражения",
    "plan.open": "Не закрыто",
    "plan.resolved": "Закрыто",
    "plan.clarify": "Уточнить",
    "plan.evidence": "Из разговора: {quote}",
    "plan.tentative": "Подобрано по времени. Проверьте, что это нужная встреча.",
    "plan.calendar": "Подобрано по событию календаря. Проверьте, что это нужная встреча.",
    "plan.source": "Подготовка из {source}",
    "plan.score": "Пунктов закрыто: {resolved} из {total} · уточнить: {clarify}",
    "plan.group_score": "{label}: {resolved}/{total}",
    "plan.question.open": "Без ответа",
    "plan.question.resolved": "Ответ получен",
    "plan.question.clarify": "Уточнить ответ",
    "plan.risk.open": "Риск открыт",
    "plan.risk.resolved": "Риск снят",
    "plan.risk.clarify": "Риск уточнён",
    "plan.objection.open": "Не отработано",
    "plan.objection.resolved": "Отработано",
    "plan.objection.clarify": "Нужны детали",
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
    "meeting_chat.note": "Видимый Zoom Chat и импорт экспорта · сообщения сохраняются отдельно от скриншотов. Скрытая история автоматически не прокручивается.",
    "meeting_chat.import": "Импорт TXT / JSON",
    "meeting_chat.questions": "Только вопросы аудитории",
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
    "status.live": "Расшифровка идёт",
    "status.finished": "Созвон завершён · контекст сохранён",
    "status.model_loading": "Загрузка модели",
    "status.model_missing": "Нет live-модели",
    "status.overloaded": "Live-расшифровка перегружена",
    "status.no_fresh": "Нет свежих реплик",
    "transcript.overloaded_meta": "Расшифровка отстаёт. Последняя реплика: {age}",
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
    "speaker.voice": "Собеседник {value}",
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
    "delivery.auth_required": "Email: sign-in needed · {count}",
    "delivery.pending": "Email: not sent · {count}",
    "delivery.hint": "Reports are saved locally. Open meeting history for delivery status.",
    "language.label": "Interface language",
    "aria.transcript_view": "Left pane view",
    "aria.speaker_filter": "Speaker filter",
    "aria.copilot_view": "Right pane view",
    "aria.journal_filter": "Journal filter",
    "aria.workspace_filter": "Meeting chat and signals",
    "common.refresh": "Refresh",
    "nav.swap_panels": "Swap panels",
    "common.close": "Close",
    "common.cancel": "Cancel",
    "transcript.heading": "Live meeting",
    "transcript.loading": "Loading the latest utterances",
    "transcript.tab": "Transcript",
    "transcript.copy": "Copy dialogue",
    "transcript.copied": "Dialogue copied",
    "transcript.copy_empty": "No utterances to copy",
    "transcript.copy_failed": "Could not copy",
    "transcript.translation_jump": "EN: {count} · show latest",
    "transcript.translation_hint": "Latest translation: {time}. New English utterances are not translated.",
    "frames.tab": "Frames",
    "speaker.all": "All",
    "speakers.open": "Names",
    "speakers.title": "Participants and utterances",
    "speakers.help": "A name changes throughout this meeting. If voices were merged, select utterances and assign a participant.",
    "speakers.rename_title": "Rename throughout the meeting",
    "speakers.assign_title": "Correct who is speaking",
    "speakers.select_pending": "Select unassigned",
    "speakers.clear_selection": "Clear selection",
    "speakers.selected": "Selected: {count}",
    "speakers.target": "Who is speaking",
    "speakers.new_name": "Or a new name",
    "speakers.assign": "Assign selected",
    "speakers.rename": "Rename all",
    "speakers.saved": "Saved. Transcript and archive updated; the report will refresh automatically.",
    "speakers.pending": "Assign",
    "speakers.edit_hint": "Click to rename this speaker or correct the utterance author",
    "speaker.me": "Me",
    "speaker.unverified": "Unverified voice",
    "speaker.unverified_short": "Unverified",
    "transcript.capture_lost": "Audio dropout",
    "transcript.capture_lost_hint": "The system audio track was lost. Speaker identity is uncertain in the marked interval.",
    "speaker.others": "Others",
    "transcript.empty_title": "Waiting for the transcript",
    "transcript.empty_text": "Meeting Copilot publishes the local transcript about once per second.",
    "frames.local_note": "Frames are stored only locally with the recording.",
    "frames.capture": "Capture frame now",
    "frames.armed": "Capture is armed.",
    "frames.ok": "Last frame: {time}.",
    "frames.error": "Capture error: {error}",
    "copilot.heading": "Call map & assistant",
    "copilot.meta": "Codex reads the transcript and local Git repositories",
    "view.chat": "Chat",
    "plan.tab": "Preparation",
    "plan.links": "Materials",
    "plan.question": "Questions",
    "plan.risk": "Risks",
    "plan.objection": "Objections",
    "plan.open": "Open",
    "plan.resolved": "Resolved",
    "plan.clarify": "Clarify",
    "plan.evidence": "From this call: {quote}",
    "plan.tentative": "Matched by time only. Check this is the right meeting.",
    "plan.calendar": "Matched to a calendar event. Check this is the right meeting.",
    "plan.source": "Preparation from {source}",
    "plan.score": "Resolved: {resolved} of {total} · clarify: {clarify}",
    "plan.group_score": "{label}: {resolved}/{total}",
    "plan.question.open": "Unanswered",
    "plan.question.resolved": "Answered",
    "plan.question.clarify": "Needs clarification",
    "plan.risk.open": "Open risk",
    "plan.risk.resolved": "Risk cleared",
    "plan.risk.clarify": "Risk clarified",
    "plan.objection.open": "Not addressed",
    "plan.objection.resolved": "Addressed",
    "plan.objection.clarify": "More information needed",
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
    "meeting_chat.note": "Visible Zoom Chat and imported exports · messages are saved independently of screenshots. Hidden history is not scrolled automatically.",
    "meeting_chat.import": "Import TXT / JSON",
    "meeting_chat.questions": "Audience questions only",
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
    "status.live": "Transcription live",
    "status.finished": "Meeting ended · context retained",
    "status.model_loading": "Loading model",
    "status.model_missing": "Live model missing",
    "status.overloaded": "Live transcription overloaded",
    "status.no_fresh": "No recent utterances",
    "transcript.overloaded_meta": "Transcription is behind. Latest utterance: {age}",
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
    "speaker.voice": "Participant {value}",
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

const savedUiLanguage = localStorage.getItem("meeting-copilot-language");
let hasExplicitUiLanguage = ["en", "ru"].includes(savedUiLanguage);
let uiLanguage = hasExplicitUiLanguage ? savedUiLanguage : "ru";
let inheritedUiLanguage = false;
let panelsSwapped = localStorage.getItem("meeting-copilot-panels-swapped") === "true";
function applyPanelOrder() {
  const workspace = document.querySelector(".workspace");
  const transcript = workspace.querySelector(".transcript-pane");
  const copilot = workspace.querySelector(".copilot-pane");
  workspace.append(...(panelsSwapped ? [copilot, transcript] : [transcript, copilot]));
  workspace.classList.toggle("panels-swapped", panelsSwapped);
  elements.swapPanels.setAttribute("aria-pressed", String(panelsSwapped));
}
elements.swapPanels.addEventListener("click", () => {
  panelsSwapped = !panelsSwapped;
  localStorage.setItem("meeting-copilot-panels-swapped", String(panelsSwapped));
  applyPanelOrder();
});
applyPanelOrder();

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
  const googleAccount = document.querySelector("#google-account");
  if (googleAccount?.dataset.auth) googleAccount.textContent = googleAccount.dataset.auth === "connected"
    ? t("google.account", {account: googleAccount.dataset.account || "gws"}) : t("google.auth");
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
let recordingHealth = {};
let recognitionResumeBusy = false;
let recognitionResumeError = "";
let noteBusy = false;
let chatPinnedToLatest = true;
let archiveMeetings = [];
let selectedArchiveMeeting = "";
let deliverySignature = "";
let deliveryAcknowledgedThrough = 0;
let deliveryDismissBusy = false;
let deliveryHealth = {};
let callPlanSignature = "";
let selectedPlanMeetingId = "";
let currentCallPlan = null;
let currentJournal = [];
let callBoardSignature = "";
const boardExpanded = new Set();

Object.assign(translations.ru, {
  "delivery.heading": "Доставка отчётов", "delivery.button": "Доставка",
  "delivery.attention": "Доставка · проблем: {count}", "delivery.details": "Подробнее",
  "delivery.dismiss": "Прочитано", "delivery.dismiss_failed": "Не удалось сохранить. Повторите.",
  "delivery.local_note": "Запись и отчёт остаются локально. Ошибки доставки не останавливают звонок.",
  "delivery.state.not_configured": "Не подключён", "delivery.state.idle": "Нет отчётов за последние 3 дня",
  "delivery.state.sent": "Готово · {count}", "delivery.state.pending": "Ожидает отправки · {count}",
  "delivery.state.waiting": "После завершения звонка · {count}",
  "delivery.state.failed": "Не доставлено · {count}", "delivery.state.action_required": "Нужно действие · {count}",
  "delivery.reason.auth_required": "Восстановите авторизацию этого подключения.",
  "delivery.reason.links_missing": "Не получены корректные ссылки Drive. Приложение повторит загрузку.",
  "delivery.reason.delivery_failed": "Отправка не удалась. Приложение повторит её автоматически.",
  "delivery.reason.retry_overdue": "Доставка задерживается. Автоматические повторы продолжаются.",
  "delivery.reason.retry_expired": "Автоповторы закончились. Проверьте предыдущую доставку перед повторной отправкой.",
  "delivery.reason.metadata_invalid": "Не читается состояние отчёта. Проверьте локальный архив.",
  "delivery.event.failed": "{channel}: сбой доставки. {reason}",
  "delivery.event.action_required": "{channel}: нужно ваше действие. {reason}",
  "delivery.event.recovered": "{channel}: доставка отчёта восстановлена.",
  "delivery.more": "Ещё событий: {count}", "delivery.open_report": "Открыть отчёт",
  "delivery.explain": "Причина и что делать",
});
Object.assign(translations.en, {
  "delivery.heading": "Report delivery", "delivery.button": "Delivery",
  "delivery.attention": "Delivery · issues: {count}", "delivery.details": "Details",
  "delivery.dismiss": "Mark as read", "delivery.dismiss_failed": "Could not save. Try again.",
  "delivery.local_note": "Recordings and reports stay locally. Delivery errors do not interrupt the call.",
  "delivery.state.not_configured": "Not connected", "delivery.state.idle": "No reports in the last 3 days",
  "delivery.state.sent": "Ready · {count}", "delivery.state.pending": "Awaiting delivery · {count}",
  "delivery.state.waiting": "After the call ends · {count}",
  "delivery.state.failed": "Not delivered · {count}", "delivery.state.action_required": "Action needed · {count}",
  "delivery.reason.auth_required": "Restore authorization for this connection.",
  "delivery.reason.links_missing": "Valid Drive links are missing. The app will retry the upload.",
  "delivery.reason.delivery_failed": "Delivery failed. The app will retry automatically.",
  "delivery.reason.retry_overdue": "Delivery is delayed. Automatic retries continue.",
  "delivery.reason.retry_expired": "Automatic retries ended. Check earlier delivery before sending again.",
  "delivery.reason.metadata_invalid": "Report status is unreadable. Check the local archive.",
  "delivery.event.failed": "{channel}: delivery failed. {reason}",
  "delivery.event.action_required": "{channel}: your action is needed. {reason}",
  "delivery.event.recovered": "{channel}: report delivery recovered.",
  "delivery.more": "More events: {count}", "delivery.open_report": "Open report",
  "delivery.explain": "Cause and next step",
});

Object.assign(translations.ru, {
  "capture.recording": "Звук записывается", "capture.verifying": "Проверяю запись звука",
  "capture.stalled": "Проблема с записью звука", "capture.inactive": "Запись звука неактивна",
  "capture.paused": "Запись на паузе", "capture.disconnected": "Запись не подтверждена · нет связи",
  "recognition.heading": "Состояние расшифровки", "recognition.resume": "Возобновить расшифровку",
  "recognition.recovering": "Восстанавливаю расшифровку",
  "recognition.recovering_note": "Звук сохраняется. Восстанавливается только распознавание — в том же звонке.",
  "recognition.waiting": "Расшифровка зависла. Проверяю запись звука перед безопасным возобновлением.",
  "recognition.exhausted": "Автовосстановление не помогло. Звук сохраняется; повторите расшифровку позже из записи.",
  "recognition.audio_failed": "Аудиодорожка перестала расти. Проверьте доступ к микрофону и системному звуку; запись может быть неполной.",
  "recognition.resume_failed": "Не удалось возобновить расшифровку. Аудиозапись не перезапускалась.",
  "recognition.resuming": "Отправляю команду…", "recognition.command_sent": "Команда отправлена. Жду восстановления распознавания.",
  "recognition.paused": "Расшифровка на паузе", "recognition.error": "Сбой расшифровки",
  "recognition.unverified": "Не могу проверить запись и расшифровку: нет свежего ответа приложения. Аудиозапись не перезапускалась.",
});
Object.assign(translations.en, {
  "capture.recording": "Audio recording", "capture.verifying": "Checking audio recording",
  "capture.stalled": "Audio recording issue", "capture.inactive": "Audio recording inactive",
  "capture.paused": "Recording paused", "capture.disconnected": "Recording unverified · disconnected",
  "recognition.heading": "Transcription status", "recognition.resume": "Resume transcription",
  "recognition.recovering": "Recovering transcription",
  "recognition.recovering_note": "Audio is being saved. Only recognition is being recovered, in the same call.",
  "recognition.waiting": "Transcription stalled. Checking audio recording before a safe resume.",
  "recognition.exhausted": "Automatic recovery did not help. Audio is being saved; transcribe the recording later.",
  "recognition.audio_failed": "An audio track stopped growing. Check microphone and system audio access; the recording may be incomplete.",
  "recognition.resume_failed": "Could not resume transcription. Audio recording was not restarted.",
  "recognition.resuming": "Sending command…", "recognition.command_sent": "Command sent. Waiting for recognition to recover.",
  "recognition.paused": "Transcription paused", "recognition.error": "Transcription failed",
  "recognition.unverified": "Cannot verify recording or transcription: no fresh response from the app. Audio recording was not restarted.",
});

function renderRecordingHealth(health = {}) {
  recordingHealth = health;
  const capture = health.capture;
  const matched = health.meeting_id && health.meeting_id === activeTranscript?.meeting_id;
  const fresh = !stateConnectionFailed && Number.isFinite(health.checked_at) && Date.now() / 1000 - health.checked_at < 20;
  elements.captureStatus.hidden = !matched || !capture;
  elements.captureStatus.classList.toggle("live", Boolean(fresh && capture?.audio_recording));
  elements.captureStatus.classList.toggle("error", Boolean(!fresh || capture?.state === "stalled"));
  if (matched && capture) {
    elements.captureStatus.lastChild.textContent = t(fresh ? `capture.${capture.state}` : "capture.disconnected");
  }
  const state = matched && fresh ? health.state : "";
  const problem = matched && ["waiting", "recovering", "action_required"].includes(health.state);
  elements.recognitionNotice.hidden = !problem && !recognitionResumeError;
  const reasonKey = !fresh ? "recognition.unverified"
    : health.reason === "audio_track_stalled" ? "recognition.audio_failed"
    : health.reason === "recognition_retries_exhausted" ? "recognition.exhausted"
    : health.reason === "recognition_resume_failed" ? "recognition.resume_failed"
    : state === "recovering" ? "recognition.recovering_note" : "recognition.waiting";
  elements.recognitionNoticeText.textContent = recognitionResumeError || t(reasonKey);
  elements.recognitionResume.hidden = !fresh || !capture?.audio_recording || health.reason === "audio_track_stalled";
  elements.recognitionResume.disabled = recognitionResumeBusy || state === "recovering";
  elements.recognitionResume.setAttribute("aria-busy", String(recognitionResumeBusy));
  elements.recognitionResume.textContent = t(recognitionResumeBusy ? "recognition.resuming" : "recognition.resume");
  if (state === "recovering") elements.liveStatus.lastChild.textContent = t("recognition.recovering");
}

elements.recognitionResume.addEventListener("click", async () => {
  if (recognitionResumeBusy || !activeTranscript?.meeting_id) return;
  const meetingId = activeTranscript.meeting_id;
  recognitionResumeBusy = true;
  recognitionResumeError = "";
  renderRecordingHealth(recordingHealth);
  try {
    const data = await post("/api/recognition/resume", { meeting_id: meetingId });
    if (activeTranscript?.meeting_id !== meetingId) return;
    renderRecordingHealth(data.recording_health);
  } catch (error) {
    if (activeTranscript?.meeting_id === meetingId) recognitionResumeError = t("recognition.resume_failed");
  } finally {
    recognitionResumeBusy = false;
    renderRecordingHealth(recordingHealth);
  }
});

const deliveryChannelNames = { drive: "Google Drive", gmail: "Gmail", telegram: "Telegram" };

function renderDeliveryHealth(health = {}) {
  deliveryHealth = health;
  const signature = `${uiLanguage}:${deliveryAcknowledgedThrough}:${JSON.stringify([health.channels, health.notifications, health.issue_count])}`;
  if (signature === deliverySignature) return;
  deliverySignature = signature;
  const channels = health.channels || {};
  elements.deliveryAlert.hidden = !Object.keys(channels).length;
  elements.deliveryAlert.dataset.state = health.state || "not_configured";
  elements.deliveryAlert.textContent = t(health.issue_count ? "delivery.attention" : "delivery.button", { count: health.issue_count });
  const fragment = document.createDocumentFragment();
  const hints = [];
  for (const [key, name] of Object.entries(deliveryChannelNames)) {
    const channel = channels[key] || { state: "not_configured" };
    const state = channel.state || "not_configured";
    const count = channel[state] || 0;
    const label = t(`delivery.state.${state}`, { count });
    hints.push(`${name}: ${label}`);
    const row = textNode("div", "delivery-channel", "");
    row.dataset.channel = key;
    row.append(textNode("dt", "", name));
    const value = textNode("dd", "", "");
    const status = textNode("span", "delivery-state", label);
    status.dataset.state = state;
    value.append(status);
    const reasons = new Set();
    const explanation = document.createElement("details");
    explanation.className = "delivery-explanation";
    explanation.open = !window.matchMedia("(max-width: 600px)").matches;
    explanation.append(textNode("summary", "", t("delivery.explain")));
    for (const issue of channel.issues || []) {
      if (reasons.has(issue.reason)) continue;
      reasons.add(issue.reason);
      const reason = textNode("p", "delivery-reason", t(`delivery.reason.${issue.reason}`));
      const open = textNode("button", "quiet-button delivery-issue-link", t("delivery.open_report"));
      open.type = "button";
      open.addEventListener("click", () => void loadArchiveMeeting(issue.meeting_id));
      reason.append(open);
      explanation.append(reason);
    }
    if (reasons.size) value.append(explanation);
    row.append(value);
    fragment.append(row);
  }
  elements.deliveryAlert.title = hints.join("\n");
  elements.deliveryChannels.replaceChildren(fragment);
  elements.deliverySummary.hidden = !Object.keys(channels).length;
  const notices = (health.notifications || []).filter(item => item.id > deliveryAcknowledgedThrough);
  elements.deliveryNotice.hidden = !notices.length;
  if (notices.length) {
    const event = notices.at(-1);
    elements.deliveryNotice.dataset.kind = event.kind;
    const message = t(`delivery.event.${event.kind}`, {
      channel: deliveryChannelNames[event.channel] || "",
      reason: t(`delivery.reason.${event.reason}`),
    });
    const text = message + (notices.length > 1 ? ` ${t("delivery.more", { count: notices.length - 1 })}` : "");
    if (elements.deliveryNoticeText.textContent !== text) elements.deliveryNoticeText.textContent = text;
  }
}

async function acknowledgeDeliveryNotices() {
  if (deliveryDismissBusy) return;
  deliveryDismissBusy = true;
  elements.deliveryNoticeDismiss.disabled = true;
  const through = Math.max(0, ...(deliveryHealth.notifications || []).map(item => item.id));
  try {
    const data = await post("/api/delivery/ack", { through });
    deliveryAcknowledgedThrough = Math.max(deliveryAcknowledgedThrough, through);
    renderDeliveryHealth(data.delivery);
  } catch (_error) {
    elements.deliveryNoticeDismiss.textContent = t("delivery.dismiss_failed");
  } finally {
    deliveryDismissBusy = false;
    elements.deliveryNoticeDismiss.disabled = false;
  }
}

Object.assign(translations.ru, {
  "board.tab": "Обзор звонка", "board.mine": "Мне задать", "board.incoming": "Ко мне и общие",
  "board.risks": "Риски и возражения", "board.open": "Открыто", "board.clarify": "Нужно уточнение",
  "board.resolved": "Закрыто", "board.count": "{open} открыто · {closed} закрыто",
  "board.details": "Основание и источник", "board.prepared": "Подготовка", "board.live": "По ходу звонка",
  "board.to_me": "Ко мне", "board.general": "Общий вопрос", "board.risk": "Риск", "board.objection": "Возражение",
  "board.empty.mine": "Здесь появятся вопросы из подготовки и подсказки, что спросить.",
  "board.empty.incoming": "Здесь появятся вопросы собеседников из стенограммы.",
  "board.empty.risks": "Здесь появятся риски и возражения из подготовки и разговора.",
  "board.waiting": "Пункты появятся по мере анализа разговора.",
});
Object.assign(translations.en, {
  "board.tab": "Call overview", "board.mine": "Questions to ask", "board.incoming": "To me & the group",
  "board.risks": "Risks & objections", "board.open": "Open", "board.clarify": "Needs clarification",
  "board.resolved": "Closed", "board.count": "{open} open · {closed} closed",
  "board.details": "Evidence & source", "board.prepared": "Preparation", "board.live": "During this call",
  "board.to_me": "To me", "board.general": "General question", "board.risk": "Risk", "board.objection": "Objection",
  "board.empty.mine": "Prepared questions and suggestions for what to ask appear here.",
  "board.empty.incoming": "Questions captured from the conversation appear here.",
  "board.empty.risks": "Prepared and live risks and objections appear here.",
  "board.waiting": "Items appear as the conversation is analyzed.",
});

const journalGroups = {
  questions: new Set(["QUESTION", "ASK", "INCOMING_QUESTION", "OPEN_QUESTION"]),
  objections: new Set(["CONTRADICTION", "RISK", "OBJECTION"]),
  decisions: new Set(["DECISION", "COMMITMENT"]),
  notes: new Set(["NOTE"]),
  entities: new Set(["URL", "PRODUCT", "SERVICE"]),
};

const journalLabels = {
  ru: {
    QUESTION: "ВОПРОС",
    ASK: "ЧТО СПРОСИТЬ",
    INCOMING_QUESTION: "ВОПРОС КО МНЕ",
    OPEN_QUESTION: "ОБЩИЙ ВОПРОС",
    OBJECTION: "ВОЗРАЖЕНИЕ",
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
    INCOMING_QUESTION: "QUESTION TO ME",
    OPEN_QUESTION: "GENERAL QUESTION",
    OBJECTION: "OBJECTION",
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

function speakerLabel(segment) {
  if (segment.speaker_id === "unassigned") return t("speakers.pending");
  if (segment.speaker_identity === "manual") return segment.speaker_label || segment.speaker;
  if (segment.source === "microphone") return t("speaker.me");
  const label = segment.speaker_label || segment.speaker;
  if (label && !/^(Собеседник|Спикер)\s*\d*$/.test(label)) return label;
  return t("speaker.voice", { value: (segment.voice_id || "remote-1").replace(/^remote-/, "") });
}

let speakerEditorSnapshot = null;
let speakerEditorSelection = new Set();

function updateSpeakerSelection() {
  elements.speakerSelectionCount.textContent = t("speakers.selected", { count: speakerEditorSelection.size });
  elements.speakerAssignmentSave.disabled = !speakerEditorSelection.size;
  elements.speakerUtteranceList.querySelectorAll("input[type=checkbox]").forEach((input) => {
    input.checked = speakerEditorSelection.has(input.value);
  });
}

function openSpeakerEditor(snapshot, selectedSegment = "") {
  speakerEditorSnapshot = snapshot;
  speakerEditorSelection = new Set(selectedSegment ? [selectedSegment] : []);
  elements.speakerEditStatus.textContent = "";
  elements.speakerAssignmentName.value = "";
  elements.speakerEditHelp.textContent = t("speakers.help");
  const names = document.createDocumentFragment();
  const choices = document.createDocumentFragment();
  choices.append(new Option(t("speakers.target"), ""));
  for (const person of snapshot.speakers || []) {
    if (person.unassigned) continue;
    const row = document.createElement("form");
    row.className = "speaker-name-row";
    row.append(textNode("span", "", `${person.name} · ${person.count}`));
    const input = document.createElement("input");
    input.value = person.name;
    input.maxLength = 80;
    input.required = true;
    input.setAttribute("aria-label", `${t("speakers.rename")}: ${person.name}`);
    const save = textNode("button", "quiet-button", t("speakers.rename"));
    save.type = "submit";
    row.append(input, save);
    row.addEventListener("submit", (event) => {
      event.preventDefault();
      void saveSpeakerEdit({ operation: "rename", speaker_id: person.id, name: input.value }, save);
    });
    names.append(row);
    choices.append(new Option(person.name, person.id));
  }
  elements.speakerNameList.replaceChildren(names);
  elements.speakerAssignmentTarget.replaceChildren(choices);
  const utterances = document.createDocumentFragment();
  for (const segment of snapshot.segments || []) {
    const row = document.createElement("label");
    row.className = "speaker-edit-utterance";
    const check = document.createElement("input");
    check.type = "checkbox";
    check.value = segment.segment_id;
    check.checked = speakerEditorSelection.has(check.value);
    check.addEventListener("change", () => {
      if (check.checked) speakerEditorSelection.add(check.value);
      else speakerEditorSelection.delete(check.value);
      updateSpeakerSelection();
    });
    const author = textNode("strong", "", speakerLabel(segment));
    author.append(textNode("time", "", localTime(segment.timestamp)));
    row.append(check, author, textNode("span", "", segment.text));
    utterances.append(row);
  }
  elements.speakerUtteranceList.replaceChildren(utterances);
  updateSpeakerSelection();
  if (!elements.speakerDialog.open) elements.speakerDialog.showModal();
  if (selectedSegment) {
    const check = elements.speakerUtteranceList.querySelector(`input[value="${CSS.escape(selectedSegment)}"]`);
    check?.closest("label").scrollIntoView({ block: "center" });
  }
}

async function saveSpeakerEdit(payload, button) {
  const meetingId = speakerEditorSnapshot?.meeting_id;
  if (!meetingId) return;
  button.disabled = true;
  elements.speakerEditStatus.textContent = "…";
  try {
    const data = await post("/api/speakers", { ...payload, meeting_id: meetingId });
    openSpeakerEditor(data.transcript);
    elements.speakerEditStatus.textContent = t("speakers.saved");
    if (activeTranscript?.meeting_id === meetingId) {
      transcriptSignature = "";
      await state();
    }
    if (selectedArchiveMeeting === meetingId && elements.archiveDialog.open) await loadArchiveMeeting(meetingId);
  } catch (error) {
    elements.speakerEditStatus.textContent = String(error);
  } finally {
    button.disabled = false;
  }
}

elements.speakerEdit.addEventListener("click", () => { if (activeTranscript) openSpeakerEditor(activeTranscript); });
elements.speakerEditClose.addEventListener("click", () => elements.speakerDialog.close());
elements.speakerSelectPending.addEventListener("click", () => {
  speakerEditorSelection = new Set((speakerEditorSnapshot?.segments || []).filter(s => s.speaker_id === "unassigned").map(s => s.segment_id));
  updateSpeakerSelection();
});
elements.speakerSelectClear.addEventListener("click", () => { speakerEditorSelection.clear(); updateSpeakerSelection(); });
elements.speakerAssignmentSave.addEventListener("click", () => void saveSpeakerEdit({
  operation: "assign", segment_ids: [...speakerEditorSelection],
  speaker_id: elements.speakerAssignmentTarget.value, name: elements.speakerAssignmentName.value,
}, elements.speakerAssignmentSave));

function renderTranscript(transcript) {
  if (activeTranscript?.meeting_id !== transcript.meeting_id) recognitionResumeError = "";
  activeTranscript = transcript;
  elements.copyDialog.disabled = !transcript.segments.length;
  const translated = transcript.segments.filter((segment) => segment.translation_en);
  const latestTranslation = translated.at(-1);
  elements.translationJump.hidden = !latestTranslation;
  if (latestTranslation) {
    elements.translationJump.textContent = t("transcript.translation_jump", { count: translated.length });
    elements.translationJump.title = t("transcript.translation_hint", { time: localTime(latestTranslation.timestamp) });
  }
  elements.note.textContent = t("note.button", { time: timecodeLabel(transcript) });
  elements.meetingTitle.textContent = transcript.display_meeting || transcript.meeting || "Встреча";
  elements.liveStatus.classList.toggle("live", Boolean(transcript.live));
  elements.liveStatus.classList.toggle("error", Boolean(transcript.error || transcript.status === "error"));
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
  } else if (transcript.status === "paused") {
    elements.liveStatus.lastChild.textContent = t("recognition.paused");
  } else if (transcript.status === "error") {
    elements.liveStatus.lastChild.textContent = t("recognition.error");
  } else {
    elements.liveStatus.lastChild.textContent = t("status.no_fresh");
  }

  const signature = `${sourceFilter}:${transcript.meeting_id}:${transcript.updated_at}:${transcript.segments.length}:${transcript.translation_revision || 0}:${transcript.speaker_revision || 0}`;
  if (signature === transcriptSignature) return;
  transcriptSignature = signature;

  const audioDropoutActive = transcript.capture_warnings?.some((warning) => !warning.ended_at);
  elements.transcriptMeta.textContent = transcript.error
    ? transcript.error
    : audioDropoutActive
      ? t("transcript.capture_lost")
    : transcript.status === "overloaded"
      ? t("transcript.overloaded_meta", { age: ageLabel(transcript.latest_age_seconds) })
      : t("transcript.latest_meta", { age: ageLabel(transcript.latest_age_seconds) });
  elements.transcriptMeta.title = audioDropoutActive
    ? t("transcript.capture_lost_hint") : "";

  const nearBottom =
    elements.transcript.scrollHeight - elements.transcript.scrollTop - elements.transcript.clientHeight < 120;
  const fragment = document.createDocumentFragment();
  const filtered = transcript.segments.filter(
    (segment) => sourceFilter === "all" || (segment.speaker_id
      ? (sourceFilter === "microphone" ? segment.speaker_id === "self" : segment.speaker_id !== "self")
      : segment.source === sourceFilter),
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
      const speaker = document.createElement("div");
      speaker.className = "speaker";
      const nameButton = textNode("button", "speaker-name-button", speakerLabel(segment));
      nameButton.type = "button";
      nameButton.title = t("speakers.edit_hint");
      nameButton.addEventListener("click", () => openSpeakerEditor(transcript, segment.segment_id));
      speaker.append(nameButton);
      if (segment.speaker_identity === "unverified") {
        speaker.title = t("transcript.capture_lost_hint");
      } else if (segment.speaker_confidence === "acoustic-diarization" || segment.voice_id) {
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
      speaker.append(textNode("time", "", localTime(segment.timestamp)));
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

function renderCallPlan(plan) {
  currentCallPlan = plan;
  elements.callPlanTab.hidden = !plan;
  if (!plan) {
    callPlanSignature = "";
    elements.callPlan.replaceChildren();
    selectedPlanMeetingId = "";
    return;
  }
  selectedPlanMeetingId = plan.meeting_id;
  elements.callPlanCount.textContent = String(plan.items.filter((item) => item.status !== "resolved").length);
  const signature = `${uiLanguage}:${JSON.stringify(plan)}`;
  if (signature !== callPlanSignature) {
    callPlanSignature = signature;
    const fragment = document.createDocumentFragment();
    fragment.append(textNode("h3", "call-plan-title", plan.title));
    if (plan.match === "time-only") fragment.append(textNode("p", "call-plan-tentative", t("plan.tentative")));
    if (plan.match === "calendar") fragment.append(textNode("p", "call-plan-tentative", t("plan.calendar")));
    if (plan.source_label) fragment.append(textNode("p", "call-plan-source", t("plan.source", { source: plan.source_label })));
    if (plan.intro) fragment.append(textNode("p", "call-plan-intro", plan.intro));
    const score = document.createElement("div");
    score.className = "call-plan-score";
    score.append(textNode("strong", "", t("plan.score", plan.score)));
    const progress = document.createElement("progress");
    progress.max = Math.max(1, plan.score.total);
    progress.value = plan.score.resolved;
    score.append(progress);
    const groupScores = document.createElement("div");
    groupScores.className = "call-plan-group-scores";
    for (const kind of ["question", "risk", "objection"]) {
      const group = plan.score.by_kind?.[kind];
      if (!group?.total) continue;
      groupScores.append(textNode("span", "", t("plan.group_score", {
        label: t(`plan.${kind}`), resolved: group.resolved, total: group.total,
      })));
    }
    score.append(groupScores);
    fragment.append(score);
    if (plan.links.length) {
      fragment.append(textNode("h4", "call-plan-section-title", t("plan.links")));
      const links = document.createElement("div");
      links.className = "call-plan-links";
      for (const link of plan.links) {
        const anchor = document.createElement("a");
        anchor.href = link.url;
        anchor.target = "_blank";
        anchor.rel = "noopener noreferrer";
        anchor.textContent = link.label;
        links.append(anchor);
      }
      fragment.append(links);
    }
    for (const kind of ["question", "risk", "objection"]) {
      const items = plan.items.filter((item) => item.kind === kind);
      if (!items.length) continue;
      fragment.append(textNode("h4", "call-plan-section-title", t(`plan.${kind}`)));
      for (const item of items) {
        const card = document.createElement("article");
        card.className = `call-plan-item ${item.status}`;
        const marker = textNode("span", "call-plan-marker", item.status === "resolved" ? "✓" : item.status === "clarify" ? "?" : "○");
        marker.setAttribute("aria-hidden", "true");
        const text = textNode("p", "call-plan-item-text", item.text);
        const select = document.createElement("select");
        select.setAttribute("aria-label", `${item.text}: ${t("plan.tab")}`);
        for (const status of ["open", "resolved", "clarify"]) {
          const option = document.createElement("option");
          option.value = status;
          option.textContent = t(`plan.${kind}.${status}`);
          option.selected = item.status === status;
          select.append(option);
        }
        select.addEventListener("change", async () => {
          select.disabled = true;
          try {
            const result = await post("/api/call-plan/status", {
              meeting_id: plan.meeting_id, item_id: item.id, status: select.value,
            });
            callPlanSignature = "";
            renderCallPlan(result.call_plan);
            renderCallBoard(result.call_plan, currentJournal);
          } catch (error) {
            select.value = item.status;
            elements.help.textContent = String(error);
            elements.help.classList.add("error");
          } finally {
            select.disabled = false;
          }
        });
        card.append(marker, text, select);
        if (item.evidence) card.append(textNode("small", "call-plan-evidence", t("plan.evidence", { quote: item.evidence })));
        fragment.append(card);
      }
    }
    elements.callPlan.replaceChildren(fragment);
  }
}

function renderCallBoard(plan, journal) {
  currentJournal = journal;
  const signature = `${uiLanguage}:${activeTranscript?.meeting_id}:${JSON.stringify(plan)}:${JSON.stringify(journal)}`;
  if (signature === callBoardSignature) return;
  callBoardSignature = signature;
  const scrolls = Object.fromEntries([...elements.callBoard.querySelectorAll("[data-board-list]")]
    .map((list) => [list.dataset.boardList, list.scrollTop]));
  const entries = (plan?.items || []).map((item) => ({ ...item, origin: "plan",
    lane: item.kind === "question" ? "mine" : "risks", category: item.kind === "objection" ? "OBJECTION" : "RISK" }));
  for (const item of journal) {
    const lane = item.category === "ASK" ? "mine"
      : ["INCOMING_QUESTION", "OPEN_QUESTION"].includes(item.category) ? "incoming"
      : ["RISK", "OBJECTION", "CONTRADICTION"].includes(item.category) ? "risks" : "";
    if (lane) entries.push({ ...item, origin: "journal", lane, status: item.status || "open" });
  }
  const fragment = document.createDocumentFragment();
  const summary = document.createElement("div");
  summary.className = "board-summary";
  for (const status of ["open", "clarify", "resolved"]) {
    const count = entries.filter((item) => item.status === status).length;
    summary.append(textNode("span", `board-summary-status ${status}`, `${t(`board.${status}`)} ${count}`));
  }
  if (plan?.links?.length) {
    const materials = document.createElement("details");
    materials.className = "board-materials";
    materials.append(textNode("summary", "", t("plan.links")));
    const links = document.createElement("div");
    links.className = "call-plan-links";
    for (const link of plan.links) {
      const anchor = textNode("a", "", link.label);
      anchor.href = link.url;
      anchor.target = "_blank";
      anchor.rel = "noopener noreferrer";
      links.append(anchor);
    }
    materials.append(links);
    summary.append(materials);
  }
  fragment.append(summary);
  const columns = document.createElement("div");
  columns.className = "board-columns";
  for (const lane of ["mine", "incoming", "risks"]) {
    const group = entries.filter((item) => item.lane === lane).sort((a, b) =>
      ({ clarify: 0, open: 1, resolved: 2 }[a.status] - { clarify: 0, open: 1, resolved: 2 }[b.status]));
    const section = document.createElement("section");
    section.className = `board-column ${lane}`;
    const header = document.createElement("header");
    header.className = "board-column-header";
    header.append(textNode("h3", "", t(`board.${lane}`)), textNode("p", "", t("board.count", {
      open: group.filter((item) => item.status !== "resolved").length,
      closed: group.filter((item) => item.status === "resolved").length,
    })));
    const list = document.createElement("div");
    list.className = "board-list";
    list.dataset.boardList = lane;
    if (!group.length) list.append(textNode("p", "board-empty", t(`board.empty.${lane}`)));
    for (const item of group) {
      const card = document.createElement("article");
      card.className = `board-item ${item.status}`;
      const heading = document.createElement("div");
      heading.className = "board-item-heading";
      const light = trafficLight(item.status === "resolved" ? "green" : item.status === "clarify" ? "yellow" : "red");
      light.setAttribute("aria-label", t(`board.${item.status}`));
      light.title = t(`board.${item.status}`);
      heading.append(light);
      const mainText = readableAnswer(item.text).split(/\n|(?:Основание|Источник|Evidence|Source):/u)[0].trim();
      heading.append(textNode("p", "", mainText));
      const controls = document.createElement("div");
      controls.className = "board-item-controls";
      const subtype = lane === "incoming" ? (item.category === "INCOMING_QUESTION" ? "to_me" : "general")
        : lane === "risks" ? (item.category === "OBJECTION" ? "objection" : "risk")
        : item.origin === "plan" ? "prepared" : "live";
      controls.append(textNode("span", "board-item-type", t(`board.${subtype}`)));
      if (item.source === "meeting_chat") controls.append(textNode("span", "board-item-type", uiLanguage === "ru" ? "Из чата аудитории" : "Audience chat"));
      const select = document.createElement("select");
      select.setAttribute("aria-label", `${mainText}: ${t("board.tab")}`);
      for (const status of ["open", "clarify", "resolved"]) {
        const option = textNode("option", "", t(`board.${status}`));
        option.value = status;
        option.selected = item.status === status;
        select.append(option);
      }
      select.addEventListener("change", async () => {
        select.disabled = true;
        try {
          const result = await post(item.origin === "plan" ? "/api/call-plan/status" : "/api/journal/status", {
            meeting_id: activeTranscript.meeting_id, item_id: item.id, status: select.value,
          });
          if (result.call_plan) renderCallPlan(result.call_plan);
          if (result.journal) renderJournal(result.journal);
          renderCallBoard(result.call_plan || currentCallPlan, result.journal || currentJournal);
        } catch (error) {
          select.value = item.status;
          elements.help.textContent = String(error);
          elements.help.classList.add("error");
        } finally { select.disabled = false; }
      });
      controls.append(select);
      card.append(heading, controls);
      const detail = document.createElement("details");
      const key = `${activeTranscript?.meeting_id}:${item.origin}:${item.id}`;
      detail.open = boardExpanded.has(key);
      detail.append(textNode("summary", "", t("board.details")), textNode("p", "", readableAnswer(item.text)));
      if (item.evidence) detail.append(textNode("p", "board-evidence", t("plan.evidence", { quote: item.evidence })));
      if (item.origin === "plan" && plan.source_label) detail.append(textNode("small", "", plan.source_label));
      if (item.speaker) detail.append(textNode("small", "", item.speaker));
      detail.addEventListener("toggle", () => { if (detail.open) boardExpanded.add(key); else boardExpanded.delete(key); });
      card.append(detail);
      list.append(card);
    }
    section.append(header, list);
    columns.append(section);
  }
  fragment.append(columns);
  elements.callBoard.replaceChildren(fragment);
  for (const list of elements.callBoard.querySelectorAll("[data-board-list]")) list.scrollTop = scrolls[list.dataset.boardList] || 0;
}

function journalLinks(item) {
  const root = document.createElement("div");
  if (!["URL", "PRODUCT", "SERVICE"].includes(item.category)) return root;
  root.className = "journal-links";
  const urls = new Set();
  const candidates = `${item.url || ""} ${item.text || ""}`.match(/(?:https?:\/\/|www\.)[^\s<>"'\])}]+/giu) || [];
  for (const candidate of candidates) {
    try {
      const url = new URL(candidate.replace(/[.,;:!?]+$/u, "").replace(/^www\./iu, "https://www."));
      if (!["http:", "https:"].includes(url.protocol) || url.username || url.password || /(^|\.)zoom\.us$/iu.test(url.hostname)) continue;
      url.search = "";
      url.hash = "";
      urls.add(url.href);
    } catch { /* Malformed OCR is not a usable link. */ }
  }
  let homepage = false;
  if (!urls.size) {
    const sites = { "miro": "https://miro.com/", "youtube": "https://www.youtube.com/", "ютуб": "https://www.youtube.com/",
      "amocrm": "https://www.amocrm.ru/", "amo crm": "https://www.amocrm.ru/", "trendhero": "https://trendhero.io/",
      "google sheets": "https://sheets.google.com/", "telegram": "https://telegram.org/", "instagram": "https://www.instagram.com/",
      "tiktok": "https://www.tiktok.com/", "shopify": "https://www.shopify.com/", "amazon": "https://www.amazon.com/" };
    const name = String(item.text || "").split(/[:—\n]/u)[0].trim().toLowerCase();
    if (sites[name]) { urls.add(sites[name]); homepage = true; }
  }
  root.append(textNode("small", "", uiLanguage === "ru"
    ? (homepage ? "Сайт сервиса · не ссылка на конкретный материал" : urls.size ? "URL из встречи" : "URL не найден в материалах встречи")
    : (homepage ? "Service website · not a specific meeting resource" : urls.size ? "URL from meeting" : "No URL found in meeting materials")));
  for (const url of urls) {
    const link = textNode("a", "", url);
    link.href = url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    root.append(link);
  }
  return root;
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
        journalLinks(item),
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
    const speaker = speakerLabel(segment);
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
  const oldScroll = elements.meetingChatList.scrollTop;
  const pinned = elements.meetingChatList.scrollHeight - elements.meetingChatList.clientHeight - oldScroll < 72;
  window.currentMeetingChat = items;
  elements.meetingChatCount.textContent = String(items.length);
  const questionsOnly = document.querySelector("#chat-questions-only").checked;
  const signature = `${questionsOnly}:${JSON.stringify(items)}`;
  if (signature === meetingChatSignature) return;
  meetingChatSignature = signature;
  items = questionsOnly ? items.filter(item => (item.text || "").includes("?")) : items;
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
        textNode("time", "", item.displayed_at || `${uiLanguage === "ru" ? "Обнаружено" : "Detected"}: ${localTime(item.captured_at)}`),
      );
      card.append(header, textNode("p", "", item.text || ""));
      card.append(textNode("small", "", `${item.source === "export" ? "TXT / JSON" : "OCR"}${(item.text || "").includes("?") ? (uiLanguage === "ru" ? " · Вопрос аудитории — в реестре вопросов" : " · Audience question — in question register") : ""}`));
      fragment.append(card);
    }
  }
  elements.meetingChatList.replaceChildren(fragment);
  elements.meetingChatList.scrollTop = pinned ? elements.meetingChatList.scrollHeight : oldScroll;
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
    if (data.delivery) renderDeliveryHealth(data.delivery);
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
  const names = textNode("button", "quiet-button", t("speakers.title"));
  names.type = "button";
  names.disabled = !meeting.transcript?.length;
  names.addEventListener("click", () => openSpeakerEditor({ ...meeting, segments: meeting.transcript }));
  reportActions.append(names);
  report.append(reportActions);
  const delivery = document.createElement("p");
  delivery.className = "archive-delivery";
  const statuses = [];
  for (const [channel, field] of [["drive", "drive_status"], ["gmail", "mail_status"], ["telegram", "telegram_status"]]) {
    const raw = meeting.report?.[field] || "not_configured";
    const state = raw === "uploaded" || raw === "sent" ? "sent"
      : raw === "auth_required" ? "action_required" : raw === "waiting_for_end" ? "waiting"
        : raw === "pending" ? "pending" : raw === "not_configured" ? "not_configured" : "failed";
    statuses.push(`${deliveryChannelNames[channel]}: ${t(`delivery.state.${state}`, { count: 1 })}`);
  }
  delivery.textContent = statuses.join(" · ");
  report.append(delivery);
  root.append(report);

  if (meeting.call_plan) {
    const map = document.createElement("div");
    map.className = "archive-call-plan";
    for (const link of meeting.call_plan.links || []) {
      const anchor = document.createElement("a");
      anchor.href = link.url;
      anchor.target = "_blank";
      anchor.rel = "noopener noreferrer";
      anchor.textContent = link.label;
      map.append(anchor);
    }
    for (const item of meeting.call_plan.items || []) {
      const row = document.createElement("div");
      row.className = `call-plan-item ${item.status}`;
      row.append(
        textNode("span", "call-plan-marker", item.status === "resolved" ? "✓" : item.status === "clarify" ? "?" : "○"),
        textNode("span", "call-plan-item-text", item.text),
        textNode("strong", "call-plan-archive-status", t(`plan.${item.kind}.${item.status}`)),
      );
      if (item.evidence) row.append(textNode("small", "call-plan-evidence", t("plan.evidence", { quote: item.evidence })));
      map.append(row);
    }
    root.append(archiveSection(t("plan.tab"), meeting.call_plan.items.length, map, true));
  }

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
      journalLinks(item),
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
    const speaker = speakerLabel(item);
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
    const response = await fetch("/api/state", { cache: "no-store", signal: AbortSignal.timeout(8000) });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    const defaultLanguage = data.preferences?.interface_language;
    if (!hasExplicitUiLanguage && !inheritedUiLanguage && ["en", "ru"].includes(defaultLanguage)) {
      uiLanguage = defaultLanguage;
      inheritedUiLanguage = true;
      transcriptSignature = "";
      frameSignature = "";
      renderedMessages = "";
      journalSignature = "";
      meetingChatSignature = "";
      applyLanguage();
    }
    const project = data.project || {};
    renderDeliveryHealth(data.delivery || {});
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
    stateConnectionFailed = false;
    renderTranscript(data.transcript);
    renderRecordingHealth(data.recording_health || {});
    renderFrames(data.frames || []);
    renderFrameStatus(data.frame_capture || {});
    renderMessages(data.copilot);
    renderCallPlan(data.call_plan || null);
    renderJournal(data.journal || []);
    renderCallBoard(data.call_plan || null, data.journal || []);
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
    const analysisKey = `${data.transcript.meeting_id}:${data.transcript.status}:${data.transcript.latest_at}:${(data.meeting_chat || []).length}:${(data.meeting_chat || []).at(-1)?.id || ""}`;
    if (
      elements.autoAnalysis.checked &&
      (data.transcript.live || finishedWithoutAnalysis) &&
      (data.transcript.latest_at || data.meeting_chat?.length) &&
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
    renderRecordingHealth(recordingHealth);
    if (!elements.captureStatus.hidden) {
      elements.captureStatus.classList.remove("live");
      elements.captureStatus.classList.add("error");
      elements.captureStatus.lastChild.textContent = t("capture.disconnected");
    }
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
    ...(path === "/api/recognition/resume" ? { signal: AbortSignal.timeout(10000) }
      : path.startsWith("/api/google-context/") ? {signal: AbortSignal.timeout(25000)} : {}),
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
    elements.callBoard.hidden = view !== "board";
    elements.callPlan.hidden = view !== "plan";
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

document.querySelector("#chat-questions-only").addEventListener("change", () => renderMeetingChat(window.currentMeetingChat || []));
document.querySelector("#chat-import-file").addEventListener("click", () => document.querySelector("#chat-import-input").click());
document.querySelector("#chat-import-input").addEventListener("change", async event => {
  const file = event.target.files[0];
  if (!file) return;
  const meetingId = activeTranscript?.meeting_id;
  const result = document.querySelector("#chat-import-result");
  try {
    if (file.size > 2000000) throw new Error(uiLanguage === "ru" ? "Максимум 2 МБ" : "Maximum 2 MB");
    const response = await fetch("/api/meeting-chat/import", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ meeting_id: meetingId, text: await file.text() }) });
    const data = await response.json();
    if (!response.ok || !data.ok) throw new Error(data.error || "Import failed");
    result.textContent = `${uiLanguage === "ru" ? "Добавлено" : "Added"}: ${data.added}`;
    renderMeetingChat(data.meeting_chat);
    if (data.added && elements.autoAnalysis.checked) void analyze(true);
  } catch (error) { result.textContent = error.message; }
  event.target.value = "";
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
elements.deliveryAlert.addEventListener("click", () => elements.archiveButton.click());
elements.deliveryNoticeDetails.addEventListener("click", () => elements.archiveButton.click());
elements.deliveryNoticeDismiss.addEventListener("click", () => void acknowledgeDeliveryNotices());
elements.translationJump.addEventListener("click", () => {
  const latest = activeTranscript?.segments.filter((segment) => segment.translation_en).at(-1);
  if (latest) jumpToTranscript(latest.timestamp);
});

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
    hasExplicitUiLanguage = true;
    localStorage.setItem("meeting-copilot-language", language);
    if (language === uiLanguage) return;
    uiLanguage = language;
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

Object.assign(translations.ru, {
  "settings.open": "Настройки", "google.heading": "Google-аккаунт и источники LLM", "google.sources": "Разрешить LLM искать контекст",
  "google.manual": "Проверить поиск вручную (необязательно)",
  "google.connect": "Подключить Google", "google.disconnect": "Отключить Google от Copilot", "google.check": "Проверить подключение",
  "google.automatic": "После подключения и выбора источников LLM сам формулирует поисковые запросы по вопросу или теме звонка. Репозитории остаются дополнительным источником, а не единственным.",
  "google.disconnected": "Google отключён от Copilot. Общая авторизация gws сохранена для других функций, включая доставку отчётов.",
  "google.pending": "Завершите вход в открывшемся браузере, затем нажмите «Проверить подключение».",
  "google.calendar_note": "При включении Calendar Copilot также сопоставляет подготовку с событиями дня звонка.",
  "google.privacy": "Выключен по умолчанию. Только чтение. Найденные фрагменты используются в текущем звонке выбранной моделью анализа; при облачной модели покидают компьютер.",
  "google.save": "Сохранить источники", "google.query": "Участник, компания или тема встречи",
  "google.search": "Найти для текущего звонка", "google.loading": "Подключаю источники…",
  "google.searching": "Ищу контекст…", "google.saved": "Источники сохранены; предыдущие результаты очищены.",
  "google.limits": "Calendar: −90/+30 дней. Gmail: до 3 писем за год, заголовки и фрагменты. Drive: до 5 файлов, название, описание и ссылка, не полный текст. Результаты используются 10 минут; изменение источников очищает их. Отправка отчётов настраивается отдельно.",
  "google.account": "Подключён Google: {account}", "google.auth": "Google не подключён к Copilot. Нажмите «Подключить Google»; если gws ещё не настроен, потребуется локальная настройка OAuth-клиента.",
  "google.empty": "Ничего не найдено", "google.partial": "Показана часть результатов",
  "google.failed": "Источник недоступен: {source} ({state}). Проверьте gws и разрешения доступа.",
  "google.no_meeting": "Для поиска начните или откройте текущую запись.",
  "google.result": "Найдено {count}. Copilot может использовать эти фрагменты в текущей встрече в течение 10 минут.",
});
Object.assign(translations.en, {
  "settings.open": "Settings", "google.heading": "Google account and LLM sources", "google.sources": "Allow LLM context search",
  "google.manual": "Test search manually (optional)",
  "google.connect": "Connect Google", "google.disconnect": "Disconnect Google from Copilot", "google.check": "Check connection",
  "google.automatic": "Once connected and sources are selected, the LLM generates search queries from the question or call topic. Repositories remain an additional source, not the only one.",
  "google.disconnected": "Google disconnected from Copilot. Shared gws credentials are preserved for other features, including report delivery.",
  "google.pending": "Complete sign-in in the opened browser, then choose Check connection.",
  "google.calendar_note": "Enabling Calendar also matches meeting preparation against events on the call date.",
  "google.privacy": "Off by default. Read-only. Results are used for this call by your selected analysis model; a cloud model receives them outside your computer.",
  "google.save": "Save sources", "google.query": "Participant, company or meeting topic",
  "google.search": "Search for this call", "google.loading": "Loading connections…",
  "google.searching": "Searching context…", "google.saved": "Sources saved; previous results cleared.",
  "google.limits": "Calendar: past 90 / next 30 days. Gmail: up to 3 messages from the past year, headers and snippets. Drive: up to 5 file titles, descriptions and links, not full contents. Results expire in 10 minutes; source changes clear them. Report delivery is configured separately.",
  "google.account": "Connected Google: {account}", "google.auth": "Google is not connected to Copilot. Choose Connect Google; an unconfigured gws requires local OAuth client setup.",
  "google.empty": "No results", "google.partial": "Some results are omitted",
  "google.failed": "Source unavailable: {source} ({state}). Check gws and access permissions.",
  "google.no_meeting": "Start a current recording before searching.",
  "google.result": "Found {count}. Copilot can use these excerpts in this meeting for 10 minutes.",
});
let googleBusy = false;
let googleConnected = false;
const googleMessage = document.querySelector("#google-message");
const googleResults = document.querySelector("#google-results");
function googleControls(busy) {
  googleBusy = busy;
  document.querySelectorAll("#google-sources input, #google-save, #google-search, #google-query").forEach(node => { node.disabled = busy || !googleConnected; });
  document.querySelectorAll("#google-connect, #google-check").forEach(node => { node.disabled = busy; });
  document.querySelector("#google-disconnect").disabled = busy || !googleConnected;
  document.querySelector("#google-search-form").setAttribute("aria-busy", String(busy));
}
async function loadGoogleContext() {
  if (googleBusy) return;
  googleControls(true);
  const account = document.querySelector("#google-account");
  account.textContent = t("google.loading");
  try {
    const response = await fetch("/api/google-context", {cache: "no-store", signal: AbortSignal.timeout(10000)});
    const data = await response.json();
    if (!response.ok || !data.ok) throw new Error(`HTTP ${response.status}`);
    document.querySelectorAll("#google-sources input").forEach(input => { input.checked = data.sources?.[input.value] === true; });
    googleConnected = data.connected === true;
    account.dataset.auth = googleConnected ? "connected" : "not_connected";
    account.dataset.account = data.account || "";
    account.textContent = googleConnected ? t("google.account", {account: data.account || "gws"}) : data.login_pending ? t("google.pending") : t("google.auth");
  } catch (error) { account.textContent = String(error); }
  finally { googleControls(false); }
}
const googleSettings = document.querySelector("#google-context-settings");
document.querySelector("#settings-content").append(googleSettings);
googleSettings.open = true;
document.querySelector("#settings-open").addEventListener("click", () => {
  document.querySelector("#settings-panel").hidden = false;
  document.querySelector("#settings-open").setAttribute("aria-expanded", "true");
  void loadGoogleContext();
});
document.querySelector("#settings-close").addEventListener("click", () => {
  document.querySelector("#settings-panel").hidden = true;
  document.querySelector("#settings-open").setAttribute("aria-expanded", "false");
  document.querySelector("#settings-open").focus();
});
document.querySelector("#google-check").addEventListener("click", () => void loadGoogleContext());
for (const action of ["connect", "disconnect"]) document.querySelector(`#google-${action}`).addEventListener("click", async () => {
  if (googleBusy) return;
  googleControls(true);
  try {
    const data = await post(`/api/google-context/${action}`, {});
    googleConnected = data.connected === true;
    googleResults.replaceChildren();
    googleMessage.textContent = data.login_pending ? t("google.pending") : action === "disconnect" ? t("google.disconnected") : "";
  } catch (error) { googleMessage.textContent = String(error); }
  finally { googleControls(false); await loadGoogleContext(); }
});
document.querySelector("#google-save").addEventListener("click", async () => {
  if (googleBusy) return;
  const sources = Object.fromEntries([...document.querySelectorAll("#google-sources input")].map(input => [input.value, input.checked]));
  googleControls(true);
  try {
    await post("/api/google-context/settings", {sources});
    googleResults.replaceChildren();
    googleMessage.textContent = t("google.saved");
  } catch (error) { googleMessage.textContent = String(error); }
  finally { googleControls(false); }
});
document.querySelector("#google-search-form").addEventListener("submit", async event => {
  event.preventDefault();
  if (googleBusy) return;
  const query = document.querySelector("#google-query").value.trim();
  googleControls(true);
  googleResults.replaceChildren();
  googleMessage.textContent = t("google.searching");
  try {
    const snapshot = await fetch("/api/projects", {cache: "no-store"}).then(response => response.json());
    if (!snapshot.meeting_id) throw new Error(t("google.no_meeting"));
    const data = await post("/api/google-context/search", {meeting_id: snapshot.meeting_id, query});
    let count = 0;
    for (const [source, result] of Object.entries(data.sources || {})) {
      const section = document.createElement("section");
      section.append(textNode("h3", "", source === "gmail" ? "Gmail" : source === "drive" ? "Google Drive" : "Google Calendar"));
      if (result.state !== "ok") section.append(textNode("p", "", t("google.failed", {source, state: result.state})));
      else if (!result.items.length) section.append(textNode("p", "", t("google.empty")));
      if (result.limited) section.append(textNode("p", "", t("google.partial")));
      for (const item of result.items || []) {
        count++;
        const row = document.createElement("article");
        const link = document.createElement(item.url ? "a" : "strong");
        link.textContent = item.title || item.url || source;
        if (item.url) {
          const url = new URL(item.url);
          if (url.protocol === "https:" && url.hostname.endsWith(".google.com")) {
            link.href = url.href; link.target = "_blank"; link.rel = "noopener noreferrer";
          }
        }
        row.append(link, textNode("small", "", item.date || ""), textNode("p", "", item.excerpt || ""));
        section.append(row);
      }
      googleResults.append(section);
    }
    googleMessage.textContent = t("google.result", {count});
  } catch (error) { googleMessage.textContent = String(error); }
  finally { googleControls(false); }
});

applyLanguage();
void state();
// Freshness must expire even when a request never returns. An old response
// cannot keep either a recording claim or a recovery action alive indefinitely.
setInterval(() => {
  if (recordingHealth.checked_at && Date.now() / 1000 - recordingHealth.checked_at >= 20) {
    renderRecordingHealth(recordingHealth);
  }
}, 1000);
setInterval(() => void state(), 2500);
window.addEventListener("online", () => void state());
window.matchMedia("(max-width: 600px)").addEventListener("change", () => {
  deliverySignature = "";
  renderDeliveryHealth(deliveryHealth);
});
document.addEventListener("visibilitychange", () => {
  if (!document.hidden) void state();
});
