# -*- coding: utf-8 -*-
"""桌面宠物核心 — 像素小兔子"""

import json
import math
import os
import random
import sys
import threading
import time
import tkinter as tk

from .config import CANVAS_H, CANVAS_W, CONFIG_PATH
from .themes import BUNNY_SPRITE, LETTER_TAGS, THEMES
from .media_monitor import MediaMonitor
from .lyrics import fetch_lyrics
from .bubble import LyricsBubble
from . import particles


class DesktopPet:
    def __init__(self):
        self.config = self._load_config()
        self.theme_name = self.config.get('theme', 'White Bunny')
        self.theme = THEMES.get(self.theme_name, THEMES['White Bunny'])

        # --- animation state ---
        self.state = 'idle'          # idle | walking | zoomies | dragged | happy
        self.anim_time = 0.0
        self.rest_y = None
        self.current_bob = 0

        # walk
        self.target_x = None
        self.target_y = None
        self.walk_speed = 2.0
        self.facing_right = True

        # timers
        self.blink_timer = 0.0
        self.next_blink = random.uniform(2.0, 5.0)
        self.nose_twitch_timer = 0.0
        self.next_nose_twitch = random.uniform(3.0, 7.0)
        self.idle_timer = 0.0
        self.next_walk = random.uniform(3.0, 7.0)
        self.happy_timer = 0.0

        # beat bounce (music mode)
        self.beat_bounce_timer = 0.0

        # drag
        self.is_dragging = False
        self.drag_ox = self.drag_oy = 0
        self._click_sx = self._click_sy = 0

        # particles
        self.particles_list = []

        # --- music ---
        self.media = MediaMonitor()
        self.bubble = None              # created after window
        self.bubble_lines = 1           # lyric lines visible (1/3/5)
        self.current_track_id = None    # (title, artist) tuple to detect song changes
        self.lyrics = None              # parsed LRC list for current song
        self.lyric_index = 0            # current line index
        self.lyric_offset = 1.5         # seconds: positive = show lyrics earlier
        self._pending_track_id = None   # track being fetched in background
        self._lyrics_result = None      # result from background fetch
        self._lyrics_ready = False      # True when bg fetch completed
        self._bg_lock = threading.Lock()  # protect bg fetch state
        self.last_lyric_index = -1
        self.music_note_timer = 0.0    # spawn ♪ particles
        self._fetch_start_time = 0.0

        # --- build ---
        self._setup_window()
        self.bubble = LyricsBubble(self.window, num_lines=self.bubble_lines)
        self._render_sprite()
        self._setup_menu()
        self._update()

    # ============================================================
    # config
    # ============================================================
    def _load_config(self):
        try:
            if os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def _save_config(self):
        try:
            self.config['x'] = self.window.winfo_x()
            self.config['y'] = self.window.winfo_y()
            self.config['theme'] = self.theme_name
            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2)
        except Exception:
            pass

    # ============================================================
    # window
    # ============================================================
    def _setup_window(self):
        self.window = tk.Tk()
        self.window.title('Pixel Bunny')
        self.window.overrideredirect(True)
        self.window.attributes('-topmost', True)
        self.window.attributes('-transparentcolor', '#010101')

        sw = self.window.winfo_screenwidth()
        sh = self.window.winfo_screenheight()
        sx = self.config.get('x')
        sy = self.config.get('y')
        if sx is None or not (0 <= sx <= sw - CANVAS_W):
            sx = random.randint(100, max(100, sw - CANVAS_W - 100))
        if sy is None or not (0 <= sy <= sh - CANVAS_H):
            sy = random.randint(100, max(100, sh - CANVAS_H - 100))
        self.window.geometry(f'{CANVAS_W}x{CANVAS_H}+{sx}+{sy}')
        self.rest_y = sy

        from .config import PIXEL_SIZE
        self.canvas = tk.Canvas(
            self.window, width=CANVAS_W, height=CANVAS_H,
            bg='#010101', highlightthickness=0, bd=0,
        )
        self.canvas.pack()

        # mouse
        self.canvas.bind('<Button-1>',        self._on_left_press)
        self.canvas.bind('<B1-Motion>',       self._on_drag)
        self.canvas.bind('<ButtonRelease-1>', self._on_release)
        self.canvas.bind('<Button-3>',        self._on_right_click)
        self.canvas.bind('<Double-Button-1>', self._on_double_click)

        self.window.protocol('WM_DELETE_WINDOW', self.quit)
        self.window.bind('<Alt-F4>', lambda e: self.quit())

    # ============================================================
    # sprite
    # ============================================================
    def _render_sprite(self):
        c = self.canvas
        c.delete('pet')
        self.eye_ids = []
        self.nose_ids = []
        from .config import PIXEL_SIZE
        ps = PIXEL_SIZE

        for ri, row in enumerate(BUNNY_SPRITE):
            for ci, ch in enumerate(row):
                if ch == '.':
                    continue
                color = self.theme.get(ch, '#FFFFFF')
                tag = LETTER_TAGS.get(ch, '')
                tags = ('pet', tag) if tag else ('pet',)
                rid = c.create_rectangle(
                    ci * ps, ri * ps,
                    ci * ps + ps, ri * ps + ps,
                    fill=color, outline='', tags=tags,
                )
                if ch == 'B':
                    self.eye_ids.append(rid)
                elif ch == 'N':
                    self.nose_ids.append(rid)

    def _recolour_sprite(self):
        t = self.theme
        for ch, tag in LETTER_TAGS.items():
            if ch in t:
                self.canvas.itemconfig(tag, fill=t[ch])

    # ============================================================
    # menu
    # ============================================================
    def _setup_menu(self):
        self.menu = tk.Menu(self.window, tearoff=0)
        self.menu.add_command(label='Refresh Lyrics', command=self._refresh_lyrics)
        self.menu.add_command(label='Pet Me!', command=self._do_happy_jump)
        self.menu.add_separator()
        theme_menu = tk.Menu(self.menu, tearoff=0)
        for name in THEMES:
            theme_menu.add_command(label=name, command=lambda n=name: self._change_theme(n))
        self.menu.add_cascade(label='Theme', menu=theme_menu)
        # bubble size submenu
        size_menu = tk.Menu(self.menu, tearoff=0)
        for n in [1, 3, 5]:
            size_menu.add_command(
                label=f'{n} Line{"s" if n > 1 else ""}',
                command=lambda n=n: self._set_bubble_lines(n),
            )
        self.menu.add_cascade(label='Bubble Size', menu=size_menu)
        # lyric timing offset submenu
        offset_menu = tk.Menu(self.menu, tearoff=0)
        for off in [-1.0, -0.5, 0, 0.5, 1.0, 1.5, 2.0, 2.5]:
            label = f'{off:+.1f}s' if off != 1.5 else '1.5s (default)'
            offset_menu.add_command(
                label=label,
                command=lambda o=off: self._set_lyric_offset(o),
            )
        self.menu.add_cascade(label='Lyric Sync', menu=offset_menu)
        self.menu.add_separator()
        self.menu.add_command(label='Quit', command=self.quit)

    def _change_theme(self, name):
        self.theme_name = name
        self.theme = THEMES[name]
        self._recolour_sprite()
        self._save_config()

    def _set_bubble_lines(self, n: int):
        """Resize the lyrics bubble to show 1 / 3 / 5 lines."""
        self.bubble_lines = n
        if self.bubble:
            self.bubble.set_num_lines(n)
            self.bubble.visible = False

    def _set_lyric_offset(self, offset: float):
        """Adjust lyric timing. +0.5 = show lyrics 0.5s earlier, -0.5 = later."""
        self.lyric_offset = offset

    def _refresh_lyrics(self):
        """Manually re-fetch lyrics for the current song (clears cache)."""
        from .lyrics import LYRICS_CACHE, _cache_path
        info = self.media.get_current()
        if not info or not info.get('title'):
            return
        title, artist = info['title'], info.get('artist', '')
        cache_key = f'{title}|{artist}'
        LYRICS_CACHE.pop(cache_key, None)
        try:
            os.remove(_cache_path(cache_key))
        except Exception:
            pass
        self.current_track_id = None
        self._pending_track_id = None
        self._lyrics_ready = False
        self._lyrics_result = None
        self.lyrics = None

    # ============================================================
    # main loop  (60 fps)
    # ============================================================
    def _update(self):
        dt = 1.0 / 60.0
        self.anim_time += dt

        # --- facial timers ---
        self.blink_timer -= dt
        self.next_blink -= dt
        if self.next_blink <= 0:
            self.blink_timer = 0.12
            self.next_blink = random.uniform(2.0, 5.0)

        self.nose_twitch_timer -= dt
        self.next_nose_twitch -= dt
        if self.next_nose_twitch <= 0:
            self.nose_twitch_timer = 0.08
            self.next_nose_twitch = random.uniform(3.0, 8.0)

        if self.happy_timer > 0:
            self.happy_timer -= dt

        if self.beat_bounce_timer > 0:
            self.beat_bounce_timer -= dt

        # --- animation state ---
        if self.state == 'idle':
            self._animate_idle(dt)
        elif self.state in ('walking', 'zoomies'):
            self._animate_walk(dt)
        elif self.state == 'happy':
            self._animate_happy(dt)
        # dragged → no auto animation

        # --- facial ---
        self._animate_blink()
        self._animate_nose()

        # --- music ---
        self._check_media()

        # --- particles ---
        self.particles_list = particles.update_particles(self.canvas, self.particles_list)

        self.window.after(16, self._update)

    # ============================================================
    # idle
    # ============================================================
    def _animate_idle(self, dt):
        self.idle_timer += dt
        if self.rest_y is None:
            self.rest_y = self.window.winfo_y()

        bob = int(math.sin(self.anim_time * 2.0) * 1.5)
        extra = self._beat_offset()
        if bob != self.current_bob or extra:
            self.window.geometry(
                f'{CANVAS_W}x{CANVAS_H}+{self.window.winfo_x()}+{self.rest_y + bob - extra}'
            )
            self.current_bob = bob
            self._sync_bubble()

    # ============================================================
    # walk
    # ============================================================
    def _animate_walk(self, dt):
        if self.target_x is None:
            self._start_walking()
            return

        cx = self.window.winfo_x()
        cy = self.window.winfo_y()
        dx = self.target_x - cx
        dy = self.target_y - cy
        dist = math.sqrt(dx * dx + dy * dy)

        if dist < 6:
            self.state = 'idle'
            self.next_walk = random.uniform(2.0, 6.0)
            self.rest_y = self.window.winfo_y()
            self.current_bob = 0
            self.idle_timer = 0
            self._save_config()
            self._sync_bubble()
            return

        self.facing_right = dx > 0

        speed = self.walk_speed * 60 * dt
        if self.state == 'zoomies':
            speed *= 3.5

        step = min(speed, dist)
        nx = cx + (dx / dist) * step
        ny = cy + (dy / dist) * step

        sw = self.window.winfo_screenwidth()
        sh = self.window.winfo_screenheight()
        nx = max(0, min(nx, sw - CANVAS_W))
        ny = max(0, min(ny, sh - CANVAS_H - 48))

        hop = int(abs(math.sin(self.anim_time * 12.0)) * 5)
        extra = self._beat_offset()
        self.window.geometry(f'{CANVAS_W}x{CANVAS_H}+{int(nx)}+{int(ny - hop - extra)}')
        self._sync_bubble()

    # ============================================================
    # happy
    # ============================================================
    def _animate_happy(self, dt):
        cx = self.window.winfo_x()
        cy = self.window.winfo_y()
        phase = self.happy_timer * 9.0
        jump = int(abs(math.sin(phase)) * 15)
        self.window.geometry(f'{CANVAS_W}x{CANVAS_H}+{cx}+{cy - jump}')
        self._sync_bubble()
        if self.happy_timer <= 0:
            self.state = 'idle'
            self.rest_y = self.window.winfo_y()
            self.current_bob = 0
            self.next_walk = random.uniform(2.0, 5.0)

    # ============================================================
    # blink / nose
    # ============================================================
    def _animate_blink(self):
        c = self.theme['W'] if self.blink_timer > 0 else self.theme['B']
        for eid in self.eye_ids:
            self.canvas.itemconfig(eid, fill=c)

    def _animate_nose(self):
        c = '#FFB6C1' if self.nose_twitch_timer > 0 else self.theme['N']
        for nid in self.nose_ids:
            self.canvas.itemconfig(nid, fill=c)

    # ============================================================
    # beat bounce
    # ============================================================
    def _trigger_beat_bounce(self):
        self.beat_bounce_timer = 0.22

    def _beat_offset(self) -> int:
        """Extra Y offset (pixels up) for beat bounce."""
        if self.beat_bounce_timer <= 0:
            return 0
        t = self.beat_bounce_timer
        return int(abs(math.sin(t * 28)) * 7 * min(1.0, t / 0.1))

    # ============================================================
    # music / lyrics  (called every frame)
    # ============================================================
    def _fetch_lyrics_bg(self, title: str, artist: str, track_id: tuple):
        """Fetch lyrics in background."""
        try:
            result = fetch_lyrics(title, artist)
            with self._bg_lock:
                if (self._pending_track_id == track_id or
                        self.current_track_id == track_id):
                    self._lyrics_result = result
                    self._lyrics_ready = True
        except Exception:
            pass
        finally:
            with self._bg_lock:
                if self._pending_track_id == track_id:
                    self._pending_track_id = None

    def _check_media(self):
        info = self.media.get_current()

        # --- no media → hide bubble ---
        if not info or not info.get('title'):
            if self.lyrics is not None:
                self.lyrics = None
                self.lyric_index = 0
                self.last_lyric_index = -1
                self.bubble.hide()
            return

        # --- paused? keep bubble visible, freeze lyrics in place ---
        if not info.get('is_playing'):
            if self.lyrics and self.bubble.visible:
                pass
            return

        title = info['title']
        artist = info.get('artist', '')
        position = info.get('position', 0)
        track_id = (title, artist)

        # --- new song? fetch lyrics in background ---
        if track_id != self.current_track_id and track_id != self._pending_track_id:
            self.current_track_id = track_id
            self._pending_track_id = track_id
            self._fetch_start_time = time.time()
            self.lyrics = None
            self.lyric_index = 0
            self.last_lyric_index = -1
            song_info = f'{artist} - {title}' if artist else title
            lines_data = [{'text': '🎵 Loading...', 'status': 'current'}]
            if self.bubble.visible:
                self.bubble.update_lines(song_info, lines_data)
            else:
                self.bubble.show(song_info, lines_data)
            self._sync_bubble()
            threading.Thread(
                target=self._fetch_lyrics_bg,
                args=(title, artist, track_id),
                daemon=True,
            ).start()
            return

        # --- still loading? ---
        if self._pending_track_id is not None:
            elapsed = time.time() - self._fetch_start_time
            if elapsed > 15:
                self._pending_track_id = None
                self.lyrics = None
            else:
                return

        # --- fetch completed? ---
        if self._lyrics_ready:
            with self._bg_lock:
                self.lyrics = self._lyrics_result
                self._lyrics_ready = False
                self._lyrics_result = None
                self._pending_track_id = None

        # --- no lyrics → show info ---
        if not self.lyrics:
            song_info = f'{artist} - {title}' if artist else title
            lines_data = [{'text': '🔍 no lyrics found', 'status': 'current'}]
            if self.bubble.visible:
                self.bubble.update_lines(song_info, lines_data)
            else:
                self.bubble.show(song_info, lines_data)
            self._sync_bubble()
            return

        # --- find current lyric line ---
        adjusted_pos = position + self.lyric_offset
        new_index = 0
        for i, entry in enumerate(self.lyrics):
            if entry['time'] <= adjusted_pos:
                new_index = i
            else:
                break
        self.lyric_index = new_index

        # --- beat bounce on line change ---
        if self.lyric_index != self.last_lyric_index:
            self.last_lyric_index = self.lyric_index
            self._trigger_beat_bounce()

        # --- karaoke display ---
        song_info = f'{artist} - {title}' if artist else title
        half = self.bubble_lines // 2
        lines_data = []
        for offset in range(-half, half + 1):
            idx = self.lyric_index + offset
            if 0 <= idx < len(self.lyrics):
                status = 'past' if offset < 0 else ('current' if offset == 0 else 'future')
                lines_data.append({'text': self.lyrics[idx]['text'], 'status': status})

        if self.bubble.visible:
            self.bubble.update_lines(song_info, lines_data)
        else:
            self.bubble.show(song_info, lines_data)

        self._sync_bubble()

        self.music_note_timer -= (1.0 / 60.0)
        if self.music_note_timer <= 0:
            self.music_note_timer = random.uniform(1.5, 3.5)
            new_notes = particles.spawn_music_notes(self.canvas, 1)
            self.particles_list.extend(new_notes)

    def _sync_bubble(self):
        """Reposition bubble to follow the bunny."""
        if self.bubble and self.bubble.visible:
            self.bubble.move(self.window.winfo_x(), self.window.winfo_y())

    # ============================================================
    # movement AI
    # ============================================================
    def _start_walking(self):
        sw = self.window.winfo_screenwidth()
        sh = self.window.winfo_screenheight()
        self.target_x = random.randint(30, max(30, sw - CANVAS_W - 30))
        self.target_y = random.randint(30, max(30, sh - CANVAS_H - 90))
        self.state = 'walking'
        self.walk_speed = random.uniform(1.5, 2.5)

    def _start_zoomies(self):
        sw = self.window.winfo_screenwidth()
        sh = self.window.winfo_screenheight()
        self.target_x = random.randint(30, max(30, sw - CANVAS_W - 30))
        self.target_y = random.randint(30, max(30, sh - CANVAS_H - 90))
        self.state = 'zoomies'
        self.walk_speed = random.uniform(3.5, 6.0)

    # ============================================================
    # mouse
    # ============================================================
    def _on_left_press(self, event):
        self.drag_ox = event.x
        self.drag_oy = event.y
        self._click_sx = event.x_root
        self._click_sy = event.y_root

    def _on_drag(self, event):
        dx = event.x_root - self._click_sx
        dy = event.y_root - self._click_sy
        if not self.is_dragging and (abs(dx) > 3 or abs(dy) > 3):
            self.is_dragging = True
            self.state = 'dragged'
            self.rest_y = None

        if self.is_dragging:
            x = event.x_root - self.drag_ox
            y = event.y_root - self.drag_oy
            self.window.geometry(f'{CANVAS_W}x{CANVAS_H}+{x}+{y}')
            self._sync_bubble()

    def _on_release(self, event):
        was_drag = self.is_dragging
        self.is_dragging = False
        if was_drag:
            self.state = 'idle'
            self.rest_y = self.window.winfo_y()
            self.current_bob = 0
            self.next_walk = random.uniform(3.0, 7.0)
            self._save_config()
        else:
            self._do_happy_jump()

    def _on_double_click(self, event):
        self._refresh_lyrics()

    def _on_right_click(self, event):
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

    def _do_happy_jump(self, big=False):
        prev = self.state
        self.state = 'happy'
        self.happy_timer = 1.0 if big else 0.5
        new_hearts = particles.spawn_hearts(self.canvas, count=6 if big else 3)
        self.particles_list.extend(new_hearts)
        if prev in ('walking', 'zoomies'):
            def _back():
                if self.state == 'happy':
                    self.state = 'idle'
                    self.rest_y = self.window.winfo_y()
                    self.current_bob = 0
                    self.next_walk = random.uniform(2.0, 5.0)
            self.window.after(int(self.happy_timer * 1000) + 100, _back)

    # ============================================================
    # quit
    # ============================================================
    def quit(self):
        self._save_config()
        self.media.stop()
        if self.bubble:
            self.bubble.destroy()
        try:
            self.window.destroy()
        except Exception:
            pass
        sys.exit(0)

    def run(self):
        try:
            self.window.mainloop()
        except KeyboardInterrupt:
            self.quit()
