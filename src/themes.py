# -*- coding: utf-8 -*-
"""精灵图 & 主题配色"""

# ============================================================
# 16×16 Pixel Bunny Sprite
#   W=body  P=pink  B=eye  N=nose  R=blush  .=transparent
# ============================================================
BUNNY_SPRITE_STR = """
................
....PP....PP....
....WW....WW....
....WW....WW....
....PP....PP....
...WWWWWWWWWW...
..WWWWWWWWWWWW..
..WWBBWWWBBWWW..
..WWRWWWWRWWW..
...WWWWNNWWWW...
....WWWWWWWW....
...WWWWWWWWWW...
...WWWWWWWWWW...
....WWWWWWWW....
....WWW..WWW....
.....WW..WW.....
"""

THEMES = {
    'White Bunny':   {'W': '#FFFFFF', 'P': '#FFB6C1', 'B': '#444444', 'N': '#FF69B4', 'R': '#FFAAAA'},
    'Brown Bunny':   {'W': '#E8D5B7', 'P': '#E8B4B8', 'B': '#3D2B1F', 'N': '#C97A7A', 'R': '#F0C0C0'},
    'Gray Bunny':    {'W': '#D3D3D3', 'P': '#FFB6C1', 'B': '#444444', 'N': '#FF69B4', 'R': '#FFAAAA'},
    'Pink Bunny':    {'W': '#FFD0DC', 'P': '#FF8FAB', 'B': '#4A2040', 'N': '#FF5D8F', 'R': '#FFB0C0'},
    'Black Bunny':   {'W': '#5A5A5A', 'P': '#8888AA', 'B': '#1A1A1A', 'N': '#7777AA', 'R': '#6A6A8A'},
    'Golden Bunny':  {'W': '#FFF3CD', 'P': '#FFC107', 'B': '#5D4037', 'N': '#FF9800', 'R': '#FFE082'},
}

LETTER_TAGS = {'W': 'body', 'P': 'pink', 'B': 'eye', 'N': 'nose', 'R': 'blush'}


def parse_sprite(raw: str):
    lines = [ln.strip() for ln in raw.strip().split('\n') if ln.strip()]
    return [list(ln) for ln in lines]


BUNNY_SPRITE = parse_sprite(BUNNY_SPRITE_STR)
