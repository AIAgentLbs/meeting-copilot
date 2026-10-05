"""Parse exported chat without inventing senders or missing message times."""
import json
import re


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
