"""Загрузка снимка PageSpeed Insights API v5 (те же данные, что на pagespeed.web.dev)."""

from __future__ import annotations

import json
import ssl
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.utils import timezone

PSI_BASE = 'https://www.googleapis.com/pagespeedonline/v5/runPagespeed'

_CATEGORY_IDS = (
    'performance',
    'accessibility',
    'best-practices',
    'seo',
)

_LAB_AUDITS = (
    ('lcp', 'largest-contentful-paint'),
    ('fcp', 'first-contentful-paint'),
    ('cls', 'cumulative-layout-shift'),
    ('tbt', 'total-blocking-time'),
    ('speed_index', 'speed-index'),
)

_OPPORTUNITY_AUDIT_IDS = (
    'render-blocking-resources',
    'unused-javascript',
    'unused-css-rules',
    'offscreen-images',
    'legacy-javascript',
    'uses-text-compression',
)


def _score_to_100(score: Any) -> int | None:
    if score is None:
        return None
    try:
        return int(round(float(score) * 100))
    except (TypeError, ValueError):
        return None


def _lh_scores(lighthouse: dict[str, Any]) -> dict[str, int | None]:
    cats = (lighthouse or {}).get('categories') or {}
    out: dict[str, int | None] = {}
    mapping = (
        ('performance', 'performance'),
        ('accessibility', 'accessibility'),
        ('best_practices', 'best-practices'),
        ('seo', 'seo'),
    )
    for key, lid in mapping:
        c = cats.get(lid) or {}
        out[key] = _score_to_100(c.get('score'))
    return out


def _lab_metrics(lighthouse: dict[str, Any]) -> dict[str, str]:
    audits = (lighthouse or {}).get('audits') or {}
    out: dict[str, str] = {}
    for short, audit_id in _LAB_AUDITS:
        a = audits.get(audit_id) or {}
        dv = (a.get('displayValue') or '').strip()
        if dv:
            out[short] = dv
    return out


def _diag_lists(lighthouse: dict[str, Any]) -> tuple[list[str], list[str]]:
    """Короткие пункты для дашборда: плюсы (пройденные аудиты) и узкие места."""
    audits = (lighthouse or {}).get('audits') or {}
    good: list[str] = []
    if (audits.get('uses-text-compression') or {}).get('score') == 1:
        good.append('Текстовые ответы сжимаются (gzip/brotli).')
    if (audits.get('uses-optimized-images') or {}).get('score') == 1:
        good.append('Изображения в целом оптимизированы.')
    if (audits.get('uses-long-cache-ttl') or {}).get('score', 0) >= 0.9:
        good.append('HTTP-кэширование статики настроено.')
    bad: list[str] = []
    for aid in _OPPORTUNITY_AUDIT_IDS:
        a = audits.get(aid) or {}
        title = (a.get('title') or '').strip()
        if not title:
            continue
        score = a.get('score')
        det = a.get('details') or {}
        savings_ms = 0
        if isinstance(det, dict):
            savings_ms = int(det.get('overallSavingsMs') or 0)
        if score is not None and score < 1:
            if savings_ms > 200 or aid in ('render-blocking-resources', 'unused-javascript'):
                bad.append(title[:120] + ('…' if len(title) > 120 else ''))
        if len(bad) >= 3:
            break
    if not bad:
        for aid in _OPPORTUNITY_AUDIT_IDS:
            a = audits.get(aid) or {}
            title = (a.get('title') or '').strip()
            if title and a.get('score') is not None and a.get('score') < 1:
                bad.append(title[:120])
            if len(bad) >= 2:
                break
    return good[:3], bad[:3]


def _cwv_block(psi: dict[str, Any]) -> dict[str, Any]:
    """Полевые метрики CrUX, если Google отдал их в том же ответе."""
    le = psi.get('loadingExperience') or psi.get('originLoadingExperience')
    if not le:
        return {
            'field_available': False,
            'assessment': 'lab',
            'summary': (
                'Полевых данных CrUX в ответе нет — ниже оценки Lighthouse '
                '(лаборатория, как на pagespeed.web.dev).'
            ),
        }
    metrics = le.get('metrics') or {}
    parts: list[str] = []
    lcp = metrics.get('LARGEST_CONTENTFUL_PAINT_MS')
    cls = metrics.get('CUMULATIVE_LAYOUT_SHIFT_SCORE')
    inp = metrics.get('INTERACTION_TO_NEXT_PAINT')
    if isinstance(lcp, dict):
        pct = lcp.get('percentiles', {}).get('p75')
        if pct is not None:
            parts.append(f'LCP ~{int(pct) / 1000:.1f}s (p75, поле)')
    if isinstance(inp, dict):
        pct = inp.get('percentiles', {}).get('p75')
        if pct is not None:
            parts.append(f'INP ~{int(pct)}ms (p75)')
    if isinstance(cls, dict):
        pct = cls.get('percentiles', {}).get('p75')
        if pct is not None:
            parts.append(f'CLS ~{float(pct):.3f} (p75)')
    cats = []
    for m in (lcp, inp, cls):
        if isinstance(m, dict):
            c = (m.get('category') or '').upper()
            if c:
                cats.append(c)
    assessment = 'partial'
    if cats and all(c == 'FAST' for c in cats):
        assessment = 'passed'
    elif any(c == 'SLOW' for c in cats):
        assessment = 'failed'
    summary = '; '.join(parts) if parts else 'Полевые метрики получены (CrUX).'
    return {
        'field_available': True,
        'assessment': assessment,
        'summary': summary,
    }


def _run_strategy(url: str, api_key: str, strategy: str) -> dict[str, Any]:
    params: list[tuple[str, str]] = [
        ('url', url),
        ('key', api_key),
        ('strategy', strategy),
    ]
    for c in _CATEGORY_IDS:
        params.append(('category', c))
    qs = urlencode(params)
    req = Request(
        f'{PSI_BASE}?{qs}',
        headers={'User-Agent': 'portfolio-django-pagespeed/1.0'},
    )
    ctx = ssl.create_default_context()
    with urlopen(req, timeout=120, context=ctx) as resp:
        return json.loads(resp.read().decode('utf-8'))


def _parse_strategy_payload(psi: dict[str, Any]) -> dict[str, Any]:
    lh = psi.get('lighthouseResult') or {}
    good, bad = _diag_lists(lh)
    return {
        'scores': _lh_scores(lh),
        'lab': _lab_metrics(lh),
        'diagnostics_auto': {'good': good, 'attention': bad},
    }


def fetch_pagespeed_report(url: str) -> tuple[dict[str, Any] | None, str | None]:
    """
    Возвращает snapshot для JSON-поля Project.pagespeed_report и сообщение об ошибке.
    """
    url = (url or '').strip()
    if not url:
        return None, 'Укажите URL проекта (поле «Посмотреть проект» / demo URL).'
    key = (getattr(settings, 'GOOGLE_PAGESPEED_API_KEY', None) or '').strip()
    if not key:
        return (
            None,
            'Задайте GOOGLE_PAGESPEED_API_KEY в окружении или .env (ключ Google Cloud).',
        )

    try:
        mobile = _run_strategy(url, key, 'mobile')
        desktop = _run_strategy(url, key, 'desktop')
    except HTTPError as e:
        try:
            body = e.read().decode('utf-8', errors='replace')
        except Exception:
            body = ''
        return None, f'PageSpeed API HTTP {e.code}: {body[:400]}'
    except URLError as e:
        return None, f'Сеть: {e}'
    except (json.JSONDecodeError, TimeoutError, OSError) as e:
        return None, str(e)

    m_block = _parse_strategy_payload(mobile)
    d_block = _parse_strategy_payload(desktop)
    cwv = _cwv_block(mobile)

    snap: dict[str, Any] = {
        'tested_url': url,
        'fetched_at': timezone.now().isoformat(),
        'source': 'google_pagespeed_api_v5',
        'mobile': m_block,
        'desktop': d_block,
        'cwv': cwv,
        'diagnostics': {
            'good': (m_block.get('diagnostics_auto') or {}).get('good') or [],
            'attention': (m_block.get('diagnostics_auto') or {}).get('attention')
            or [],
        },
    }
    return snap, None
