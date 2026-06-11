# -*- coding: utf-8 -*-
"""歌词气泡组件 — 卡拉OK风格多行歌词显示"""

import tkinter as tk

from .config import BUBBLE_W, CANVAS_H, CANVAS_W, PAD, HEADER_H, LINE_H, POINTER_H


class LyricsBubble:
    """A speech-bubble that shows multiple lyric lines with karaoke colouring."""

    def __init__(self, parent: tk.Tk, num_lines: int = 3):
        self.parent = parent
        self.visible = False
        self.num_lines = num_lines
        self._height = self._calc_height()
        self._line_ids: list[int] = []
        self._highlight_id: int | None = None
        self._song_text_id: int | None = None
        self._screen_w = parent.winfo_screenwidth()
        self._screen_h = parent.winfo_screenheight()

        self.win = tk.Toplevel(parent)
        self.win.overrideredirect(True)
        self.win.attributes('-topmost', True)
        self.win.attributes('-transparentcolor', '#010101')
        self.win.geometry(f'1x1+0+0')

        self.canvas = tk.Canvas(
            self.win, width=BUBBLE_W, height=self._height,
            bg='#010101', highlightthickness=0, bd=0,
        )
        self.canvas.pack(expand=True, fill='both')

    def _calc_height(self) -> int:
        return PAD + HEADER_H + 2 + self.num_lines * LINE_H + 2 + POINTER_H + PAD

    def set_num_lines(self, n: int):
        """Change how many lyric lines are visible."""
        if n == self.num_lines:
            return
        self.num_lines = n
        self._height = self._calc_height()
        self.canvas.config(height=self._height)
        self.win.geometry(f'{BUBBLE_W}x{self._height}')
        if self.visible:
            self.canvas.delete('bubble')
            self._line_ids = []
            self._highlight_id = None

    def _ensure_background(self):
        """Draw background rectangle + pointer if not already drawn."""
        c = self.canvas
        if not c.find_withtag('bg_rect'):
            pw = BUBBLE_W - PAD * 2
            ph = self._height - PAD * 2 - POINTER_H
            c.create_rectangle(
                PAD, PAD, PAD + pw, PAD + ph,
                fill='#FFFFFF', outline='#DDDDDD', width=1,
                tags=('bubble', 'bg_rect'),
            )
            cx = BUBBLE_W // 2
            c.create_polygon(
                cx - 8, PAD + ph, cx + 8, PAD + ph, cx, PAD + ph + POINTER_H,
                fill='#FFFFFF', outline='#DDDDDD', width=1,
                tags=('bubble', 'bg_ptr'),
            )

    def show(self, song_info: str, lines_data: list[dict]):
        """
        Draw / redraw the bubble.
        lines_data: [{'text': str, 'status': 'past'|'current'|'future'}, ...]
        """
        c = self.canvas
        c.delete('bubble')
        self._line_ids = []
        self._highlight_id = None

        self._ensure_background()

        pw = BUBBLE_W - PAD * 2 - 8

        # song info (top, small, grey)
        self._song_text_id = c.create_text(
            BUBBLE_W // 2, PAD + HEADER_H // 2,
            text=song_info, fill='#AAAAAA',
            font=('Microsoft YaHei', 9),
            tags=('bubble',), width=pw,
        )

        # lyric lines
        y_start = PAD + HEADER_H + 2 + LINE_H // 2
        for i, ld in enumerate(lines_data[:self.num_lines]):
            y = y_start + i * LINE_H
            status = ld['status']

            if status == 'current':
                color = '#222222'
                font = ('Microsoft YaHei', 11, 'bold')
                hl_id = c.create_rectangle(
                    PAD + 6, y - LINE_H // 2 + 1,
                    BUBBLE_W - PAD - 6, y + LINE_H // 2 - 1,
                    fill='#FFF9C4', outline='', tags=('bubble',),
                )
                c.tag_lower(hl_id, 'bg_rect')
                self._highlight_id = hl_id
            elif status == 'past':
                color = '#BBBBBB'
                font = ('Microsoft YaHei', 10)
            else:  # future
                color = '#999999'
                font = ('Microsoft YaHei', 10)

            tid = c.create_text(
                BUBBLE_W // 2, y,
                text=ld['text'], fill=color, font=font,
                tags=('bubble',), width=pw,
            )
            self._line_ids.append((tid, ld['status']))

        self.win.lift()
        self.visible = True

    def update_lines(self, song_info: str, lines_data: list[dict]):
        """Update text/colours without full redraw (when possible)."""
        if not self.visible:
            self.show(song_info, lines_data)
            return
        c = self.canvas

        if self._song_text_id:
            c.itemconfig(self._song_text_id, text=song_info)

        y_start = PAD + HEADER_H + 2 + LINE_H // 2
        for i, ld in enumerate(lines_data[:self.num_lines]):
            y = y_start + i * LINE_H
            status = ld['status']

            if status == 'current':
                color, font = '#222222', ('Microsoft YaHei', 11, 'bold')
            elif status == 'past':
                color, font = '#BBBBBB', ('Microsoft YaHei', 10)
            else:
                color, font = '#999999', ('Microsoft YaHei', 10)

            if i < len(self._line_ids):
                tid, old_status = self._line_ids[i]
                c.itemconfig(tid, text=ld['text'], fill=color, font=font)
                self._line_ids[i] = (tid, status)
            else:
                tid = c.create_text(
                    BUBBLE_W // 2, y,
                    text=ld['text'], fill=color, font=font,
                    tags=('bubble',), width=BUBBLE_W - PAD * 2 - 8,
                )
                self._line_ids.append((tid, status))

        # update highlight bar for current line
        if self._highlight_id:
            c.delete(self._highlight_id)
            self._highlight_id = None
        cur_idx = next((i for i, ld in enumerate(lines_data[:self.num_lines])
                        if ld['status'] == 'current'), -1)
        if cur_idx >= 0:
            cy = y_start + cur_idx * LINE_H
            hl_id = c.create_rectangle(
                PAD + 6, cy - LINE_H // 2 + 1,
                BUBBLE_W - PAD - 6, cy + LINE_H // 2 - 1,
                fill='#FFF9C4', outline='', tags=('bubble',),
            )
            c.tag_lower(hl_id, 'bg_rect')
            self._highlight_id = hl_id

    def hide(self):
        if self.visible:
            self.win.geometry(f'1x1+0+0')
            self.visible = False

    def move(self, bunny_x: int, bunny_y: int):
        """Reposition bubble relative to bunny window."""
        sw = self._screen_w
        bx = bunny_x + (CANVAS_W - BUBBLE_W) // 2
        by = bunny_y - self._height - 6  # default: above bunny
        bx = max(0, min(bx, sw - BUBBLE_W))
        if by < 5:
            by = bunny_y + CANVAS_H + 6  # flip below
        self.win.geometry(f'{BUBBLE_W}x{self._height}+{bx}+{by}')

    def destroy(self):
        self.hide()
        try:
            self.win.destroy()
        except Exception:
            pass
