"""Parse exported chat without inventing senders or missing message times."""
import json
import re
from datetime import datetime, timedelta


def _date(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return parsed if parsed.tzinfo else None
    except (ValueError, TypeError):
        return None


def normalize_chat_times(messages, physical, *, local_timezone=True):
    """Resolve clock-only exports only within a known physical recording day."""
    start = _date(physical.get('started_at'))
    end = _date(physical.get('ended_at') or physical.get('updated_at'))
    result = []
    for source in messages:
        item = dict(source)
        absolute = next((item.get(key) for key in ('sent_at', 'timestamp', 'captured_at', 'displayed_at')
                         if _date(item.get(key))), None)
        if absolute:
            item['captured_at'] = absolute
            result.append(item)
            continue
        moment = None
        clock = str(item.get('displayed_at') or '').strip().upper()
        if start and end and 0 <= (end - start).total_seconds() < 86400:
            local = start.astimezone() if local_timezone else start
            for pattern in ('%H:%M:%S', '%H:%M', '%I:%M:%S %p', '%I:%M %p'):
                try:
                    parsed = datetime.strptime(clock, pattern)
                    candidate = local.replace(hour=parsed.hour, minute=parsed.minute, second=parsed.second, microsecond=0)
                    if candidate < start:
                        candidate += timedelta(days=1)
                    if start <= candidate <= end:
                        moment = candidate
                    break
                except ValueError:
                    continue
        if moment:
            item['captured_at'] = moment.isoformat()
            item['time_inferred'] = True
        else:
            item['boundary_unassigned'] = True
        result.append(item)
    return result


def parse_chat_export(text):
    if len(text.encode('utf-8')) > 2_000_000:
        raise ValueError('Чат слишком большой (максимум 2 МБ)')
    if text.lstrip().startswith('{') or re.match(r'^\s*\[\s*(?:\{|\])', text):
        data = json.loads(text)
        rows = data.get('messages', data.get('items', [])) if isinstance(data, dict) else data
        if not isinstance(rows, list):
            raise ValueError('Ожидается список сообщений')
        result = []
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError('Некорректное сообщение')
            sender = str(row.get('sender') or row.get('author') or '').strip()
            body = str(row.get('text') or '').strip()
            if sender and body:
                result.append({'sender': sender, 'text': body,
                               'displayed_at': str(row.get('displayed_at') or row.get('time') or '')})
                for key in ('sent_at', 'timestamp', 'captured_at'):
                    if _date(row.get(key)):
                        result[-1]['captured_at'] = str(row[key])
                        break
        return result
    # Zoom exports and ordinary copied chat: HH:MM[:SS] From Name to Everyone: text
    header = re.compile(r'^\[?(\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AP]M)?)\]?\s+(?:From\s+)?(.+?)(?:\s+to\s+[^:]+)?:\s*(.*)$', re.I)
    rows = []
    for line in text.lstrip('\ufeff').splitlines():
        match = header.match(line.strip())
        if match:
            rows.append({'displayed_at': match[1], 'sender': match[2].strip(), 'text': match[3]})
        elif rows and line.strip():
            rows[-1]['text'] += '\n' + line
    return [row for row in rows if row['text'].strip()]
