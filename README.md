# 🐰 Pixel Bunny — Desktop Pet × Live Lyrics Sync

> A 16×16 pixel-art bunny that lives on your Windows desktop — and sings along when you play music.

[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-lightgrey?logo=windows)](https://www.microsoft.com/windows)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Size](https://img.shields.io/badge/EXE%20Size-~39MB-orange)](https://github.com)

---

## 📥 直接下载（无需 Python）

不想装 Python？直接下载 EXE 双击就能跑：

👉 **[📦 PixelBunny.exe](dist/PixelBunny.exe)**（~39MB，Windows 10/11）

> 下载后双击运行，小兔子就会出现在桌面上。放歌自动出歌词！

---

## 📸 Preview

<!-- Replace with your GIF / screenshot -->
<!-- ![demo](https://user-images.githubusercontent.com/xxx/demo.gif) -->

| 🐇 Pet Mode | 🎵 Music Mode |
|:-----------:|:-------------:|
| Bunny roams, bounces, and interacts | Auto-shows synced karaoke lyrics |
| Drag · Click · Double-click · Right-click | Past / Current / Future tri-state highlight |

---

## ✨ Features

### 🐇 Desktop Pet
- **Autonomous AI** — idle (gentle bob), walking (casual hop), and zoomies (fast dash) states, switching randomly
- **6 Color Themes** — White · Brown · Gray · Pink · Black · Golden Bunny
- **60fps Facial Animations** — blinking eyes, twitching nose, beat-triggered bounce
- **Interactive** — drag to move, click to pet (happy jump + floating hearts 💕), double-click to refresh lyrics, right-click for menu
- **Particle Effects** — ♥ hearts on pet, ♪ music notes during playback
- **Position Memory** — remembers window location and theme across sessions

### 🎵 Live Lyrics Sync
- **Cross-App Media Detection** — hooks into Windows `GlobalSystemMediaTransportControlsSession` API to detect playback from Spotify, NetEase Cloud Music, QQ Music, YouTube (browser), and more
- **4-Source Parallel Lyrics Search** — multi-threaded race: lrclib.net → syncedlyrics → NetEase → QQ Music; first response wins, others cancel
- **Karaoke-Style Bubble** — past (gray) / current (black + yellow highlight) / future (light gray) tri-state rendering
- **LRC Parsing** — regex `[mm:ss.cc]` parser, 2/3-digit millisecond compatible
- **Translation Merge** — auto-combines Chinese translations when available
- **Disk Cache** — JSON persistence to avoid re-fetching the same song
- **Timing Offset** — adjustable from -1.0s to +2.5s via right-click menu

---

## 🎮 Controls

| Action | Effect |
|--------|--------|
| **Left Drag** | Move bunny anywhere on screen |
| **Left Click** | Pet the bunny (happy jump + ♥ hearts) |
| **Double-Click** | Force re-fetch lyrics for current song |
| **Right-Click** | Menu: Theme · Bubble Size · Lyric Offset · Refresh · Quit |
| **Play Music** | Auto-detect & show synced lyrics 🎵 |

---

## 🚀 Quick Start

### Prerequisites
- **Windows 10 or 11**
- **Python 3.10+**

### Install & Run

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/desktop-pet.git
cd desktop-pet

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run
python -m src.main
```

> **Or just double-click `run.bat`** — no terminal needed.

### 打包为 EXE

```bash
# 双击 build_exe.bat
# → dist/PixelBunny.exe (~39MB, 无需安装 Python)
```

> 不想自己打包？直接下载 👆 上面「直接下载」区的预编译 EXE。

---

## 📦 Dependencies

| Package | Purpose |
|---------|---------|
| `winsdk` | Read Windows media playback session (SMTC) |
| `requests` | HTTP calls to lyrics APIs |
| `pillow` | Sprite image processing |
| `syncedlyrics` | Multi-source LRC lyrics search |

---

## 📁 Project Structure

```
desktop-pet/
├── README.md
├── requirements.txt
├── pyproject.toml
├── run.bat                    # One-click run
├── build_exe.bat              # Build standalone EXE
├── dist/
│   └── PixelBunny.exe         # Pre-built EXE (no Python needed)
└── src/
    ├── __init__.py
    ├── main.py                # Entry point
    ├── pet.py                 # Core pet: state machine, window, interactions
    ├── themes.py              # 16×16 pixel spritesheet + 6 color themes
    ├── config.py              # Global constants
    ├── bubble.py              # Karaoke lyrics bubble (Toplevel overlay)
    ├── lyrics.py              # LRC parser + 4-source parallel search
    ├── media_monitor.py       # Windows SMTC media detection
    └── particles.py           # ♥ hearts + ♪ notes particle system
```

---

## 🏗 Architecture

```
┌──────────────────────────────────────────────────┐
│                   DesktopPet                      │
│                                                   │
│  ┌─────────────┐   ┌─────────────┐               │
│  │ State Machine│   │  Particles  │               │
│  │ idle/walk/  │   │ ♥ hearts    │               │
│  │ zoomies/    │   │ ♪ notes     │               │
│  │ happy/drag  │   └─────────────┘               │
│  └─────────────┘                                  │
│         │                                         │
│  ┌──────▼──────────────────────────────────────┐ │
│  │           Lyrics Sync Engine                 │ │
│  │  MediaMonitor (Windows SMTC, 200ms poll)     │ │
│  │       │                                      │ │
│  │       ▼                                      │ │
│  │  fetch_lyrics() ── 4-thread parallel ──┐    │ │
│  │    ├─ lrclib.net        (first-wins)    │    │ │
│  │    ├─ syncedlyrics                      │    │ │
│  │    ├─ NetEase API                        │    │ │
│  │    └─ QQ Music API                       │    │ │
│  │       │                                      │ │
│  │       ▼                                      │ │
│  │  LRC Parse → Translation Merge → Cache       │ │
│  │       │                                      │ │
│  │       ▼                                      │ │
│  │  LyricsBubble (incremental render, 60fps)    │ │
│  └──────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────┘
```

---

## 🔧 Technical Highlights

| Technique | Detail |
|-----------|--------|
| **Transparent overlay** | `tkinter` + `overrideredirect` + `transparentcolor` for borderless, click-through desktop overlay |
| **60fps main loop** | `window.after(16ms)` drives state machine, physics, and lyrics sync in a single thread |
| **Async media polling** | Background thread calls Windows Runtime async API via `winsdk` every 200ms |
| **Multi-thread race** | 4 lyrics APIs queried in parallel, `threading.Event` for first-wins with 15s timeout |
| **Incremental rendering** | `canvas.itemconfig()` updates text/color per line, avoids full redraw |
| **Beat bounce physics** | `abs(sin(t×28)) × 7` sine-decay pulse, 220ms duration on lyric line change |
| **LRC regex** | `\[(\d{2}):(\d{2})\.(\d{2,3})\]` — compatible with both 2-digit and 3-digit milliseconds |

---

## 📝 License

MIT © 2025

---

## 🙏 Acknowledgments

- [lrclib.net](https://lrclib.net/) — Open-source LRC lyrics database
- [syncedlyrics](https://github.com/rtcq/syncedlyrics) — Python multi-source lyrics search
- NetEase Cloud Music / QQ Music — Lyrics APIs
