"""Conservative guard against conversational noise in the question register.

Topic relevance is assessed by the analysis model. This deterministic backstop
rejects clear connection checks and turn-taking even if the model labels them
substantive, including legacy entries. Never use it to alter raw speech/chat.
"""

import re


_EDGE_FILLERS = {"ну", "или", "вот", "так", "да", "ага", "а", "ок", "окей", "ладно",
                 "well", "so", "okay", "ok", "yeah", "right", "then"}
_EMPTY = _EDGE_FILLERS | {"угу", "эм", "это", "нет", "что", "yes", "no", "hmm"}
_PROCEDURAL = tuple(re.compile(pattern) for pattern in (
    r"(?:(?:ты|вы|я|мы|он|она) )?(?:уже )?(?:закончил(?:а|и)?|закончила?|"
    r"закончим|договорил(?:а|и)?|договорила?|готов(?:а|ы)?|все|всё)",
    r"(?:ты|вы) (?:закончил(?:а|и)?|готов(?:а|ы)?) (?:говорить|выступать)",
    r"(?:можно (?:мне )?(?:вопрос|спросить|говорить)|кто (?:следующий|дальше)|"
    r"(?:есть|какие нибудь|у кого нибудь есть) вопросы|вопросы есть|"
    r"(?:передаю|передать) слово|продолжаем|продолжать|можно продолжать)",
    r"(?:(?:ты|вы|все|вам|тебе) )?(?:(?:меня|нас) )?(?:(?:хорошо|нормально) )?"
    r"(?:слышно|видно|слышите|слышишь|видите|видишь)(?: (?:меня|нас))?",
    r"(?:меня|нас) (?:(?:хорошо|нормально) )?(?:слышно|видно|слышите|видите)",
    r"(?:звук|связь|микрофон|камера|экран|демонстрация) (?:есть|работает|виден|видна)",
    r"(?:как (?:дела|ты|вы)|how are you)",
    r"(?:are|have) you (?:done|finished|ready)",
    r"(?:did you finish|(?:are we|is everyone) (?:done|ready)|any questions|"
    r"(?:can|may) i (?:ask a question|speak|continue)|who(?: s| is) next)",
    r"(?:can|do) (?:you|everyone) (?:hear|see) (?:me|us|my screen|the screen)",
    r"(?:is|does) (?:the )?(?:audio|sound|mic|microphone|camera|screen) "
    r"(?:on|working|visible|work)",
))


def useful_question(text: str) -> bool:
    """Keep short/topic-specific questions; reject only recognizable noise.

    Full matches are deliberate: 'закончили проверку документов?' and
    'can you hear the customer objections?' are not turn-taking checks.
    ASR may omit question marks; semantic classification belongs upstream.
    """
    if not isinstance(text, str):
        return False
    words = re.findall(r"[^\W\d_]+", text.casefold(), re.UNICODE)
    if not words or all(word in _EMPTY for word in words):
        return False
    while words and words[0] in _EDGE_FILLERS:
        words.pop(0)
    while words and words[-1] in _EDGE_FILLERS:
        words.pop()
    return bool(words) and not any(pattern.fullmatch(" ".join(words))
                                   for pattern in _PROCEDURAL)


def register_question(item: dict) -> bool:
    """Do not hide owner-entered questions, preparations or other signals."""
    if (item.get("category") in {"ASK", "INCOMING_QUESTION", "OPEN_QUESTION"}
            and item.get("source") in {"copilot", "transcript", "meeting_chat", "screen"}):
        text = item.get("text", "")
        if item.get("category") == "ASK" and isinstance(text, str):
            # Basis/source lines are supporting metadata, not question content.
            text = text.split("\n", 1)[0]
        return useful_question(text)
    return True
