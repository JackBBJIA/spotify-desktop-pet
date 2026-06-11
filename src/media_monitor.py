# -*- coding: utf-8 -*-
"""Windows 媒体播放检测（Spotify / 网易云 / QQ音乐 等）"""

import asyncio
import threading
import time

from .config import MEDIA_POLL_SEC


class MediaMonitor:
    """
    Polls Windows GlobalSystemMediaTransportControlsSession
    to get currently-playing track info from *any* media app
    (Spotify, NetEase, QQ Music, browser YouTube, etc.)
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._current: dict | None = None  # {title, artist, position, is_playing}
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def get_current(self) -> dict | None:
        with self._lock:
            return dict(self._current) if self._current else None

    def stop(self):
        self._running = False

    # ---- internal ----
    def _poll_loop(self):
        while self._running:
            try:
                info = asyncio.run(self._get_info_async())
                with self._lock:
                    self._current = info
            except Exception:
                with self._lock:
                    self._current = None
            time.sleep(MEDIA_POLL_SEC)

    @staticmethod
    async def _get_info_async() -> dict | None:
        from winsdk.windows.media.control import \
            GlobalSystemMediaTransportControlsSessionManager as SM
        manager = await SM.request_async()
        session = manager.get_current_session()
        if not session:
            return None
        props = await session.try_get_media_properties_async()
        timeline = session.get_timeline_properties()
        playback = session.get_playback_info()
        return {
            'title': (props.title or '').strip(),
            'artist': (props.artist or '').strip(),
            'position': timeline.position.total_seconds() if timeline.position else 0,
            'is_playing': (playback.playback_status == 4),  # 4 = PLAYING
        }
