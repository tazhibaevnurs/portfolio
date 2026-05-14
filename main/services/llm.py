"""LLM integration: Groq (default) or Google Gemini — free API tiers."""
from __future__ import annotations

import json
import re
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings


# Cloudflare перед api.groq.com иногда режет запросы с дефолтным User-Agent Python-urllib.
_GROQ_HEADERS_EXTRA = {
    'Accept': 'application/json',
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/131.0.0.0 Safari/537.36'
    ),
}


def _http_json(
    url: str,
    payload: dict,
    headers: dict[str, str],
    timeout: int = 120,
) -> dict[str, Any]:
    data = json.dumps(payload).encode('utf-8')
    req = Request(url, data=data, headers=headers, method='POST')
    try:
        with urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode('utf-8', errors='replace')
    except HTTPError as e:
        raw = ''
        try:
            raw = e.read().decode('utf-8', errors='replace')
        except Exception:
            pass
        extra = ''
        try:
            j = json.loads(raw)
            err = j.get('error')
            if isinstance(err, dict):
                extra = err.get('message') or ''
            elif isinstance(err, str):
                extra = err
        except (json.JSONDecodeError, TypeError):
            extra = (raw or '')[:500]
        base = f'HTTP {e.code} {e.reason}'
        if extra:
            base = f'{base}: {extra}'
        raise ValueError(base) from e
    return json.loads(body)


def _extract_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    fence = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass
    return {}


def complete_json(
    system_prompt: str,
    user_prompt: str,
) -> tuple[dict[str, Any], str | None]:
    """
    Returns (parsed_json, error_message).
    """
    provider = getattr(settings, 'LLM_PROVIDER', 'groq').lower().strip()

    if provider == 'gemini':
        return _gemini_complete(system_prompt, user_prompt)

    return _groq_complete(system_prompt, user_prompt)


def _groq_error_hint(err: str) -> str:
    """Уточнение по типичным ответам Groq/Cloudflare (рус.)."""
    if '1010' in err:
        return (
            ' Код 1010 — это Cloudflare: доступ отклонён по IP, региону или «подписи» клиента '
            '(часто из РФ/некоторых стран или при блокировке датацентров). '
            'Попробуйте другую сеть или VPN с регионом, где Groq разрешён; убедитесь, что ключ активен '
            'на https://console.groq.com/keys и что модель доступна в настройках организации. '
            'Запасной путь: в .env укажите LLM_PROVIDER=gemini и GEMINI_API_KEY с aistudio.google.com.'
        )
    if '403' in err or 'Forbidden' in err:
        return (
            ' 403 также бывает при неверном/отозванном API-ключе. Проверьте GROQ_API_KEY в .env '
            '(без кавычек), перезапустите сервер; модели — в разделе Permissions в консоли Groq.'
        )
    return ''


def _groq_complete(system_prompt: str, user_prompt: str) -> tuple[dict[str, Any], str | None]:
    key = (getattr(settings, 'GROQ_API_KEY', None) or '').strip()
    if not key:
        return {}, (
            'Не задан GROQ_API_KEY. Добавьте ключ в файл .env в корне проекта '
            '(перезапустите сервер после сохранения).'
        )

    model = (getattr(settings, 'GROQ_MODEL', None) or 'llama-3.3-70b-versatile').strip()
    url = 'https://api.groq.com/openai/v1/chat/completions'
    payload = {
        'model': model,
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt},
        ],
        'temperature': 0.4,
        'max_tokens': 4_096,
    }
    headers = {
        'Authorization': f'Bearer {key}',
        'Content-Type': 'application/json',
        **_GROQ_HEADERS_EXTRA,
    }
    try:
        data = _http_json(url, payload, headers)
    except ValueError as e:
        err = str(e)
        err += _groq_error_hint(err)
        return {}, err
    except (URLError, OSError, json.JSONDecodeError, TypeError) as e:
        return {}, str(e)

    try:
        text = data['choices'][0]['message']['content']
    except (KeyError, IndexError, TypeError):
        return {}, 'Неожиданный ответ Groq API.'

    obj = _extract_json_object(text)
    return obj, None if obj else 'Не удалось разобрать JSON из ответа LLM.'


def _parse_gemini_retry_seconds(message: str) -> float | None:
    m = re.search(r'retry in ([\d.]+)\s*s', message, re.I)
    if m:
        return min(float(m.group(1)) + 1.0, 120.0)
    return None


def _gemini_error_hint(msg: str) -> str:
    """Краткая подсказка по квоте / 429 (не дублируем уже длинный ответ Google)."""
    low = msg.lower()
    if '429' in msg or 'too many' in low or 'quota' in low:
        return (
            f'{msg}\n\n'
            '— Подождите ~30–60 секунд и снова нажмите «Сохранить и обогатить через LLM» '
            '(код теперь делает несколько автоматических повторов с паузой).\n'
            '— В .env попробуйте другую модель: GEMINI_MODEL=gemini-2.5-flash или GEMINI_MODEL=gemini-1.5-flash '
            '(разные лимиты).\n'
            '— Если в тексте ошибки «limit: 0», у проекта в Google AI Studio может не быть квоты на эту модель в вашем регионе — '
            'создайте новый API key или посмотрите лимиты: https://ai.google.dev/gemini-api/docs/rate-limits\n'
            '— Запасной вариант: LLM_PROVIDER=groq и GROQ_API_KEY, если Groq у вас открывается.'
        )
    return msg


def _gemini_complete(system_prompt: str, user_prompt: str) -> tuple[dict[str, Any], str | None]:
    key = (getattr(settings, 'GEMINI_API_KEY', None) or '').strip()
    if not key:
        return {}, 'Не задан GEMINI_API_KEY в настройках окружения.'

    model = (getattr(settings, 'GEMINI_MODEL', None) or 'gemini-2.5-flash').strip()
    url = (
        f'https://generativelanguage.googleapis.com/v1beta/models/'
        f'{model}:generateContent?key={key}'
    )
    combined = f'{system_prompt}\n\n{user_prompt}'
    payload = {
        'contents': [{'parts': [{'text': combined}]}],
        'generationConfig': {
            'temperature': 0.4,
            'maxOutputTokens': 4096,
        },
    }
    headers = {'Content-Type': 'application/json'}
    max_retries = max(1, int(getattr(settings, 'GEMINI_HTTP_RETRIES', 4)))
    data: dict[str, Any] | None = None
    last_err = ''

    for attempt in range(max_retries):
        try:
            data = _http_json(url, payload, headers)
            break
        except ValueError as e:
            last_err = str(e)
            is_429 = '429' in last_err or 'Too Many Requests' in last_err
            if not is_429:
                return {}, _gemini_error_hint(last_err)
            if attempt >= max_retries - 1:
                return {}, _gemini_error_hint(last_err)
            wait = _parse_gemini_retry_seconds(last_err)
            if wait is None:
                wait = 25.0
            time.sleep(min(wait, 90.0))
        except (URLError, OSError) as e:
            return {}, _gemini_error_hint(str(e))

    if data is None:
        return {}, _gemini_error_hint(last_err or 'Gemini: нет ответа')

    try:
        text = data['candidates'][0]['content']['parts'][0]['text']
    except (KeyError, IndexError, TypeError):
        return {}, 'Неожиданный ответ Gemini API.'

    obj = _extract_json_object(text)
    return obj, None if obj else 'Не удалось разобрать JSON из ответа LLM.'
