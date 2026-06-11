# -*- coding: utf-8 -*-
"""常量 & 全局配置"""

import os

CONFIG_PATH = os.path.join(os.path.expanduser('~'), '.desktop_pet_config.json')
PIXEL_SIZE = 8
CANVAS_W = 128
CANVAS_H = 128
BUBBLE_W = 370
BUBBLE_H = 72
MEDIA_POLL_SEC = 0.2  # poll Windows media every 0.2s

# Bubble layout constants
HEADER_H = 18
LINE_H = 22
POINTER_H = 10
PAD = 6

LYRICS_CACHE = {}  # in-memory cache: (title,artist) -> parsed LRC
LYRICS_CACHE_DIR = os.path.join(os.path.expanduser('~'), '.desktop_pet_lyrics')
os.makedirs(LYRICS_CACHE_DIR, exist_ok=True)
