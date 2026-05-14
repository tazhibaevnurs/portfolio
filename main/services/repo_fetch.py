"""Fetch public GitHub repository context (README + sample files) without git clone."""
from __future__ import annotations

import base64
import json
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

MAX_CONTEXT_CHARS = 48_000

GITHUB_REPO_RE = re.compile(
    r'github\.com[/:](?P<owner>[\w.-]+)/(?P<repo>[\w.-]+?)(?:\.git)?/?$',
    re.I,
)

# Files to try if tree API unavailable
CANDIDATE_PATHS = [
    'README.md',
    'readme.md',
    'README.rst',
    'requirements.txt',
    'pyproject.toml',
    'package.json',
    'manage.py',
    'Dockerfile',
]


def _http_get(url: str, token: str | None = None, timeout: int = 25) -> str | None:
    headers = {
        'Accept': 'application/vnd.github+json',
        'User-Agent': 'portfolio-django-llm/1.0',
    }
    if token:
        headers['Authorization'] = f'Bearer {token}'
    try:
        req = Request(url, headers=headers)
        with urlopen(req, timeout=timeout) as resp:
            return resp.read().decode('utf-8', errors='replace')
    except (HTTPError, URLError, OSError):
        return None


def _parse_github(url: str) -> tuple[str, str] | None:
    m = GITHUB_REPO_RE.search(url.strip())
    if not m:
        return None
    return m.group('owner'), m.group('repo')


def fetch_raw_file(owner: str, repo: str, path: str, branch: str, token: str | None) -> str | None:
    raw = f'https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}'
    headers = {'User-Agent': 'portfolio-django-llm/1.0'}
    if token:
        headers['Authorization'] = f'token {token}'
    try:
        req = Request(raw, headers=headers)
        with urlopen(req, timeout=20) as resp:
            return resp.read().decode('utf-8', errors='replace')
    except (HTTPError, URLError, OSError):
        return None


def _readme_from_api(owner: str, repo: str, token: str | None) -> str | None:
    url = f'https://api.github.com/repos/{owner}/{repo}/readme'
    body = _http_get(url, token=token)
    if not body:
        return None
    try:
        data = json.loads(body)
        b64 = data.get('content', '')
        if b64:
            return base64.b64decode(b64).decode('utf-8', errors='replace')
    except (json.JSONDecodeError, ValueError):
        pass
    return None


def fetch_github_context(repo_url: str, github_token: str | None = None) -> str:
    """
    Build a text bundle: README + repository metadata + key files from default branch.
    """
    parsed = _parse_github(repo_url)
    if not parsed:
        return ''

    owner, repo = parsed
    api_base = f'https://api.github.com/repos/{owner}/{repo}'
    meta_json = _http_get(api_base, token=github_token)
    meta: dict = {}
    if meta_json:
        try:
            meta = json.loads(meta_json)
        except json.JSONDecodeError:
            pass

    branch = meta.get('default_branch') or 'main'
    parts: list[str] = []

    if meta:
        desc = meta.get('description') or ''
        topics = meta.get('topics') or []
        lang = meta.get('language') or ''
        parts.append(
            f"[META] description: {desc}\nlanguage: {lang}\ntopics: {topics}\n"
            f"homepage: {meta.get('homepage') or ''}\nhtml_url: {meta.get('html_url') or ''}\n"
        )

    readme = _readme_from_api(owner, repo, github_token)
    if not readme:
        for name in ('README.md', 'README.rst', 'readme.md'):
            readme = fetch_raw_file(owner, repo, name, branch, github_token)
            if readme:
                break

    if readme:
        parts.append('=== README ===\n' + readme[:15_000])

    commits_url = f'{api_base}/commits/{branch}?per_page=1'
    commits_json = _http_get(commits_url, token=github_token)
    tree_sha = ''
    if commits_json:
        try:
            arr = json.loads(commits_json)
            if isinstance(arr, list) and arr:
                tree_sha = arr[0].get('commit', {}).get('tree', {}).get('sha') or ''
        except json.JSONDecodeError:
            pass

    tree_json = ''
    if tree_sha:
        tree_url = f'https://api.github.com/repos/{owner}/{repo}/git/trees/{tree_sha}?recursive=1'
        tree_json = _http_get(tree_url, token=github_token)
    text_files: list[str] = []
    if tree_json:
        try:
            tree_data = json.loads(tree_json)
            for item in tree_data.get('tree', [])[:400]:
                if item.get('type') != 'blob':
                    continue
                path = item.get('path', '')
                if not path or item.get('size', 0) > 80_000:
                    continue
                low = path.lower()
                if not (
                    low.endswith('.py')
                    or low.endswith('.js')
                    or low.endswith('.ts')
                    or low.endswith('.tsx')
                    or low.endswith('.vue')
                    or low.endswith('.go')
                    or low.endswith('.rs')
                    or low.endswith('.md')
                    or path in ('requirements.txt', 'pyproject.toml', 'package.json')
                ):
                    continue
                if path.count('/') > 4:
                    continue
                text_files.append(path)
        except json.JSONDecodeError:
            pass

    # Limit number of extra files
    collected = 0
    for path in text_files[:25]:
        content = fetch_raw_file(owner, repo, path, branch, github_token)
        if not content or len(content) > 12_000:
            continue
        parts.append(f'\n=== FILE: {path} ===\n' + content[:8_000])
        collected += 1
        if collected >= 12:
            break

    # Fallback small candidates
    if collected == 0:
        for path in CANDIDATE_PATHS:
            c = fetch_raw_file(owner, repo, path, branch, github_token)
            if c:
                parts.append(f'\n=== FILE: {path} ===\n' + c[:8_000])
                break

    bundle = '\n'.join(parts)
    if len(bundle) > MAX_CONTEXT_CHARS:
        return bundle[:MAX_CONTEXT_CHARS] + '\n...[truncated]'
    return bundle
