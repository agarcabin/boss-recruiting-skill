"""Bounded public GitHub route fallback, with per-installation route memory."""
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
from urllib.error import HTTPError
from urllib.parse import quote, urlparse
import uuid
from zipfile import BadZipFile

MIRRORS = ('https://gh-proxy.org/', 'https://gh-proxy.com/',
           'https://ghfast.top/', 'https://ghproxy.net/')
GITHUB_HOSTS = ('api.github.com', 'github.com', 'release-assets.githubusercontent.com',
                'objects.githubusercontent.com')
NETWORK_ERRORS = (OSError, ValueError, KeyError, TypeError, BadZipFile, RuntimeError)


def allowed_url(url):
    parsed = urlparse(url)
    hosts = (*GITHUB_HOSTS, *(urlparse(route).hostname for route in MIRRORS))
    return (parsed.scheme == 'https' and parsed.hostname in hosts and not parsed.username
            and not parsed.password and parsed.port in (None, 443))


def memory_file(root):
    import skill_update as updater
    identity = hashlib.sha256(str(Path(root).resolve()).casefold().encode()).hexdigest()[:20]
    return updater.state_dir() / 'updates' / ('routes-' + identity + '.json')


def memory(root):
    try:
        value = json.loads(memory_file(root).read_text(encoding='utf-8'))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def remember(root, kind, route):
    path = memory_file(root)
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        value = memory(root)
        value[kind] = route
        temporary.write_text(json.dumps(value), encoding='utf-8')
        os.replace(temporary, path)
    except OSError:
        pass  # Updating remains usable when local preference storage is read-only.
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def routes(root, kind):
    import skill_update as updater
    configured = updater.source(root).get('mirrors', list(MIRRORS))
    if not isinstance(configured, list) or any(item not in MIRRORS for item in configured):
        raise ValueError('invalid_update_mirrors')
    values = list(dict.fromkeys(['direct', *configured]))
    saved = memory(root)
    preferred = saved.get(kind, saved.get('metadata') if kind == 'download' else None)
    return ([preferred] if preferred in values else []) + [item for item in values if item != preferred]


def routed(route, url):
    return url if route == 'direct' else route + url


class ReleasePage(HTMLParser):
    def __init__(self):
        super().__init__()
        self.canonical = []
        self.og = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'link' and attrs.get('rel') == 'canonical':
            self.canonical.append(attrs.get('href', ''))
        if tag == 'meta' and attrs.get('property') == 'og:url':
            self.og.append(attrs.get('content', ''))


def release_from_page(data, repository):
    import skill_update as updater
    parser = ReleasePage()
    parser.feed(data.decode('utf-8-sig'))
    prefix = f'https://github.com/{repository}/releases/tag/'
    urls = [url for url in parser.canonical + parser.og if url.startswith(prefix)]
    if not urls:
        raise ValueError('release_page_canonical_tag_missing')
    tag = urls[0][len(prefix):]
    updater.version_key(tag)
    version = tag.removeprefix('v')
    assets = [dict(name=name, size=0, browser_download_url=
                   f'https://github.com/{repository}/releases/download/{quote(tag, safe="")}/{name}')
              for name in (f'boss-recruiting-{version}.zip', f'boss-recruiting-{version}.zip.sha256')]
    return dict(tag_name=tag, draft=False, prerelease=False, html_url=urls[0], assets=assets)


def check(root, config, local):
    import skill_update as updater
    errors = []
    only_not_found = True
    for route in routes(root, 'metadata'):
        api = f'https://api.github.com/repos/{config["repository"]}/releases/latest'
        try:
            release = json.loads(updater.fetch(routed(route, api), 2*1024*1024))
            result = updater.release_result(config, local, release)
        except NETWORK_ERRORS as api_error:
            # Download-only mirrors can still follow GitHub's stable latest redirect.
            page = f'https://github.com/{config["repository"]}/releases/latest'
            try:
                release = release_from_page(updater.fetch(routed(route, page), 2*1024*1024), config['repository'])
                result = updater.release_result(config, local, release)
            except NETWORK_ERRORS as page_error:
                only_not_found = only_not_found and all(isinstance(e, HTTPError) and e.code == 404
                                                       for e in (api_error, page_error))
                errors.append(dict(route=route, error=f'版本API：{api_error}；Release页面：{page_error}'))
                continue
        remember(root, 'metadata', route)
        result.update(update_route=route, route_failures=errors)
        return result
    if only_not_found:
        return dict(state='no_release', current_version=local, repository=config['repository'], route_failures=errors)
    raise ValueError('all_update_routes_failed: ' + json.dumps(errors, ensure_ascii=False))


def download(root, release):
    import skill_update as updater
    errors = []
    for route in routes(root, 'download'):
        try:
            data = updater.fetch(routed(route, release['archive_url']))
            checksum_text = updater.fetch(routed(route, release['checksum_url']), 4096).decode('ascii')
            checksum = checksum_text.strip().split()
            if not checksum or not re.fullmatch(r'[a-fA-F0-9]{64}', checksum[0]) or updater.digest(data) != checksum[0].lower():
                raise ValueError('release_archive_checksum_mismatch')
            updater.unpack(data, release['latest_version'], release['repository'])
        except NETWORK_ERRORS as exc:
            errors.append(dict(route=route, error=str(exc)))
            continue
        # Only a completely validated bundle makes a route the next preferred route.
        remember(root, 'download', route)
        release.update(download_route=route, download_route_failures=errors)
        return data, checksum_text
    raise ValueError('all_download_routes_failed: ' + json.dumps(errors, ensure_ascii=False))
