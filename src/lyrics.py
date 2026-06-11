# -*- coding: utf-8 -*-
"""LRC 歌词解析 & 多源搜索（lrclib / 网易云 / QQ音乐 / syncedlyrics）"""

import json
import os
import re
import threading
import time

import requests

from .config import LYRICS_CACHE, LYRICS_CACHE_DIR

# ============================================================
# LRC Parser
# ============================================================
def parse_lrc(lrc_text: str) -> list[dict]:
    """Parse LRC text → sorted list of {'time': float_sec, 'text': str}"""
    lines = []
    pat = re.compile(r'\[(\d{2}):(\d{2})\.(\d{2,3})\]')
    for line in lrc_text.strip().split('\n'):
        matches = pat.findall(line)
        if not matches:
            continue
        text = pat.sub('', line).strip()
        if not text:
            continue
        for m in matches:
            mm, ss, cc = int(m[0]), int(m[1]), int(m[2])
            secs = mm * 60 + ss + cc / (100 if len(m[2]) == 3 else 1000)
            lines.append({'time': secs, 'text': text})
    lines.sort(key=lambda x: x['time'])
    return lines


# ============================================================
# Main fetch entry
# ============================================================
def fetch_lyrics(track: str, artist: str) -> list[dict] | None:
    """Fetch lyrics — try lrclib, then syncedlyrics, then Netease, then QQ."""
    cache_key = f'{track}|{artist}'

    if cache_key in LYRICS_CACHE:
        print(f'  [cache hit] {track}')
        return LYRICS_CACHE[cache_key]

    result = _load_cached_lyrics(cache_key)
    if result is not None:
        print(f'  [disk cache] {track}')
        LYRICS_CACHE[cache_key] = result
        return result if result else None

    norm_track = _normalize_track(track)
    norm_artist = _normalize_artist(artist)
    queries = _build_queries(norm_track, norm_artist)

    # 1) lrclib — fast for Western songs
    for t, a in queries[:3]:
        print(f'  [lrclib get] "{t}" / "{a}"')
        r = _try_lrclib_get(t, a)
        if r:
            print(f'  [lrclib OK] {len(r)} lines')
            _save_cached_lyrics(cache_key, r)
            LYRICS_CACHE[cache_key] = r
            return r

    q = f'{norm_track} {norm_artist}'.strip()
    print(f'  [lrclib search] "{q}"')
    r = _try_lrclib_search(q)
    if r:
        print(f'  [lrclib search OK] {len(r)} lines')
        _save_cached_lyrics(cache_key, r)
        LYRICS_CACHE[cache_key] = r
        return r

    # 2) syncedlyrics — broader coverage, handles Chinese sources
    t0, a0 = queries[0] if queries else (norm_track, norm_artist)
    print(f'  [syncedlyrics] "{t0}" / "{a0}"')
    r = _try_syncedlyrics(t0, a0)
    if r:
        print(f'  [syncedlyrics OK] {len(r)} lines')
        _save_cached_lyrics(cache_key, r)
        LYRICS_CACHE[cache_key] = r
        return r

    # 3) Netease Cloud Music — good for Chinese songs
    print(f'  [netease] "{t0}" / "{a0}"')
    r = _try_netease(t0, a0)
    if r:
        print(f'  [netease OK] {len(r)} lines')
        _save_cached_lyrics(cache_key, r)
        LYRICS_CACHE[cache_key] = r
        return r

    # 4) QQ Music — another Chinese source
    print(f'  [qqmusic] "{t0}" / "{a0}"')
    r = _try_qqmusic(t0, a0)
    if r:
        print(f'  [qqmusic OK] {len(r)} lines')
        _save_cached_lyrics(cache_key, r)
        LYRICS_CACHE[cache_key] = r
        return r

    print(f'  [FAIL] no lyrics for "{track}"')
    LYRICS_CACHE[cache_key] = None
    return None


def fetch_plain_lyrics(track: str, artist: str) -> list[dict] | None:
    """Fast plain lyrics from lrclib."""
    norm_track = _normalize_track(track)
    norm_artist = _normalize_artist(artist)
    for t, a in _build_queries(norm_track, norm_artist)[:2]:
        r = _try_lrclib_plain(t, a)
        if r:
            return r
    return None


# ============================================================
# Disk cache
# ============================================================
def _cache_path(key: str) -> str:
    safe = re.sub(r'[<>:"/\\|?*]', '_', key)[:180]
    return os.path.join(LYRICS_CACHE_DIR, safe + '.json')


def _load_cached_lyrics(key: str):
    path = _cache_path(key)
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if data is None:
            return False  # sentinel: cached negative
        return data
    except Exception:
        return None


def _save_cached_lyrics(key: str, data: list[dict] | None):
    if data is None:
        return
    try:
        with open(_cache_path(key), 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception:
        pass


# ============================================================
# Normalize helpers
# ============================================================
def _normalize_track(track: str) -> str:
    """Aggressive track-name cleaning for Chinese + Western songs."""
    t = track.strip()
    t = re.sub(
        r'\s*[-–—~]\s*(feat\.?.*|with.*|ft\.?.*)$',
        '', t, flags=re.IGNORECASE,
    ).strip()
    t = re.sub(
        r'\s*[（(][^)）]*[)）]\s*$', '', t,
    ).strip()
    t = re.sub(
        r'\s*[-–—~]\s*(Live|现场|live|Acoustic|Remix|Cover|翻唱|完整版|MV|Official\s*Video|Audio|Lyric\s*Video|Visualizer).*$',
        '', t, flags=re.IGNORECASE,
    ).strip()
    t = re.sub(r'[（(][^)）]*[)）]', '', t).strip()
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def _normalize_artist(artist: str) -> str:
    """Clean up artist name."""
    a = artist.strip()
    a = re.sub(r'\s*[,，&/、]\s*', ' ', a).strip()
    a = re.sub(r'\s+', ' ', a).strip()
    return a


def _build_queries(track: str, artist: str) -> list[tuple[str, str]]:
    """Return list of (track, artist) pairs to try, most specific first."""
    qs = []
    if artist:
        qs.append((track, artist))
        short_artist = artist.split()[0] if len(artist.split()) > 1 else artist
        if short_artist != artist:
            qs.append((track, short_artist))
    qs.append((track, ''))
    simple = re.sub(r'\s*[-–—·]\s*.*$', '', track).strip()
    if simple and simple != track and len(simple) >= 2:
        if artist:
            qs.append((simple, artist))
        qs.append((simple, ''))
    return qs


# ============================================================
# Source: lrclib
# ============================================================
def _try_lrclib_get(track: str, artist: str) -> list[dict] | None:
    """Get synced (LRC) lyrics from lrclib, fallback to plain lyrics."""
    try:
        params = {'track_name': track}
        if artist:
            params['artist_name'] = artist
        r = requests.get('https://lrclib.net/api/get', params=params, timeout=3)
        if r.status_code != 200:
            return None
        data = r.json()
        synced = data.get('syncedLyrics')
        if synced:
            parsed = parse_lrc(synced)
            if _good_lyrics(parsed):
                return parsed
        plain = data.get('plainLyrics')
        if plain:
            parsed = [{'time': float(i * 5), 'text': ln}
                      for i, ln in enumerate(plain.strip().split('\n')) if ln.strip()]
            if parsed:
                return parsed
    except Exception:
        pass
    return None


def _try_lrclib_plain(track: str, artist: str) -> list[dict] | None:
    """Get plain (non-synced) lyrics from lrclib."""
    try:
        params = {'track_name': track}
        if artist:
            params['artist_name'] = artist
        r = requests.get('https://lrclib.net/api/get', params=params, timeout=1.5)
        if r.status_code != 200:
            return None
        data = r.json()
        plain = data.get('plainLyrics')
        if plain:
            lines = [ln.strip() for ln in plain.strip().split('\n') if ln.strip()]
            if len(lines) >= 2:
                return [{'time': float(i * 5), 'text': ln}
                        for i, ln in enumerate(lines)]
    except Exception:
        pass
    return None


def _try_lrclib_search(query: str) -> list[dict] | None:
    try:
        r = requests.get('https://lrclib.net/api/search', params={'q': query}, timeout=2)
        if r.status_code != 200:
            return None
        for item in (r.json() or [])[:4]:
            result = _try_lrclib_get(item.get('trackName', ''), item.get('artistName', ''))
            if result:
                return result
    except Exception:
        pass
    return None


# ============================================================
# Source: Netease Cloud Music (163)
# ============================================================
def _try_netease(track: str, artist: str) -> list[dict] | None:
    """Search Netease Cloud Music and fetch LRC lyrics."""
    try:
        query = f'{track} {artist}'.strip()
        hdrs = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://music.163.com/',
        }
        sr = requests.post(
            'https://music.163.com/api/search/get',
            data={'s': query, 'type': 1, 'limit': 5, 'offset': 0},
            headers=hdrs, timeout=2,
        )
        if sr.status_code != 200:
            return None
        data = sr.json()
        if data.get('code') != 200:
            return None
        songs = (data.get('result', {}) or {}).get('songs', []) or []
        if not songs:
            return None

        for song in songs[:2]:
            sid = song.get('id')
            if not sid:
                continue
            lr = requests.get(
                'https://music.163.com/api/song/lyric',
                params={'id': sid, 'lv': 1, 'kv': 1, 'tv': -1},
                headers=hdrs, timeout=1.5,
            )
            if lr.status_code != 200:
                continue
            ldata = lr.json()
            if ldata.get('code') != 200:
                continue
            lrc_text = (ldata.get('lrc') or {}).get('lyric', '')
            tlyric_text = (ldata.get('tlyric') or {}).get('lyric', '')
            if lrc_text:
                parsed = parse_lrc(lrc_text)
                if tlyric_text:
                    parsed = _merge_translation(parsed, parse_lrc(tlyric_text))
                if _good_lyrics(parsed):
                    return parsed
    except Exception:
        pass
    return None


# ============================================================
# Source: QQ Music
# ============================================================
def _try_qqmusic(track: str, artist: str) -> list[dict] | None:
    """Search QQ Music and fetch LRC lyrics."""
    try:
        query = f'{track} {artist}'.strip()
        hdrs = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://y.qq.com/',
        }
        sr = requests.get(
            'https://c.y.qq.com/soso/fcgi-bin/client_search_cp',
            params={'w': query, 'format': 'json', 'n': 5, 't': 0},
            headers=hdrs, timeout=2,
        )
        if sr.status_code != 200:
            return None
        data = sr.json()
        if data.get('code') != 0:
            return None
        songs = (data.get('data', {}) or {}).get('song', {}) or {}
        song_list = songs.get('list', []) or []

        for song in song_list[:2]:
            songmid = song.get('songmid')
            if not songmid:
                continue
            lr = requests.get(
                'https://c.y.qq.com/lyric/fcgi-bin/fcg_query_lyric.fcg',
                params={'songmid': songmid, 'format': 'json', 'nobase64': 1},
                headers=hdrs, timeout=1.5,
            )
            if lr.status_code != 200:
                continue
            ldata = lr.json()
            if ldata.get('code') != 0:
                continue
            lrc_text = ldata.get('lyric', '')
            trans_text = ldata.get('trans', '')
            if lrc_text:
                lrc_text = lrc_text.replace('\\n', '\n')
                parsed = parse_lrc(lrc_text)
                if trans_text:
                    trans_text = trans_text.replace('\\n', '\n')
                    parsed = _merge_translation(parsed, parse_lrc(trans_text))
                if _good_lyrics(parsed):
                    return parsed
    except Exception:
        pass
    return None


# ============================================================
# Source: syncedlyrics
# ============================================================
def _try_syncedlyrics(track: str, artist: str) -> list[dict] | None:
    try:
        import syncedlyrics
        query = f'{track} {artist}'.strip()
        lrc = syncedlyrics.search(query, enhanced=True)
        if lrc:
            parsed = parse_lrc(lrc)
            if _good_lyrics(parsed):
                return parsed
    except Exception:
        pass
    return None


# ============================================================
# Helpers
# ============================================================
def _good_lyrics(parsed: list[dict]) -> bool:
    """Check if parsed lyrics are good enough (has synced timestamps)."""
    if not parsed or len(parsed) < 2:
        return False
    has_sync = any(e['time'] > 0.5 for e in parsed)
    return has_sync and len(parsed) >= 2


def _merge_translation(main: list[dict], trans: list[dict]) -> list[dict]:
    """Merge translation lines into main LRC by closest timestamp."""
    if not trans:
        return main
    trans_by_time = {}
    for t in trans:
        key = round(t['time'] * 2) / 2
        trans_by_time[key] = t['text']
    for entry in main:
        key = round(entry['time'] * 2) / 2
        if key in trans_by_time and trans_by_time[key] != entry['text']:
            entry['text'] = f"{entry['text']}  〔{trans_by_time[key]}〕"
    return main
