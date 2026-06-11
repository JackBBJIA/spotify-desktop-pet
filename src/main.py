#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
桌面宠物 — 像素小兔子 + Spotify 歌词同步
=============================================
- 16×16 像素风兔子，在桌面蹦蹦跳跳
- 检测 Windows 媒体播放（Spotify / 网易云 / QQ音乐等）
- 自动获取 LRC 同步歌词，气泡显示
- 歌词切换时兔子随节奏晃动

依赖: pip install winsdk requests syncedlyrics
"""

from .pet import DesktopPet


def main():
    print('Pixel Bunny + Spotify Lyrics')
    print('  Left drag     = move bunny')
    print('  Left click    = pet (happy jump!)')
    print('  Double-click  = refresh lyrics')
    print('  Right-click   = menu (theme / bubble / quit)')
    print('  Play music    = bunny shows synced lyrics!')
    print()
    DesktopPet().run()


if __name__ == '__main__':
    main()
