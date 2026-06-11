# -*- coding: utf-8 -*-
"""粒子效果 — 爱心 / 音符"""

import random
import tkinter as tk


def spawn_hearts(canvas: tk.Canvas, count: int = 3) -> list[dict]:
    """Spawn floating heart particles. Returns particle list."""
    particles = []
    for _ in range(count):
        x = random.randint(35, 95)
        y = random.randint(25, 55)
        dx = random.uniform(-1.5, 1.5)
        dy = random.uniform(-2.8, -0.6)
        life = random.uniform(0.6, 1.2)
        hid = canvas.create_text(
            x, y, text='♥',
            fill=random.choice(['#FF69B4', '#FF1493', '#FFB6C1', '#FF6347']),
            font=('Arial', random.randint(10, 16)),
            tags=('particle',),
        )
        particles.append({
            'id': hid, 'x': x, 'y': y,
            'dx': dx, 'dy': dy, 'life': life, 'age': 0.0,
        })
    return particles


def spawn_music_notes(canvas: tk.Canvas, count: int = 1) -> list[dict]:
    """Spawn floating ♪ particles. Returns particle list."""
    notes = ['♪', '♫', '♬', '♩']
    particles = []
    for _ in range(count):
        x = random.randint(30, 100)
        y = random.randint(20, 45)
        dx = random.uniform(-0.8, 0.8)
        dy = random.uniform(-1.8, -0.4)
        life = random.uniform(1.5, 3.0)
        nid = canvas.create_text(
            x, y, text=random.choice(notes),
            fill=random.choice(['#888888', '#AAAAAA', '#666666', '#999999']),
            font=('Arial', random.randint(12, 18)),
            tags=('particle',),
        )
        particles.append({
            'id': nid, 'x': x, 'y': y,
            'dx': dx, 'dy': dy, 'life': life, 'age': 0.0,
        })
    return particles


def update_particles(canvas: tk.Canvas, particles: list[dict]) -> list[dict]:
    """Update particle positions, remove expired ones. Returns surviving list."""
    alive = []
    for p in particles:
        p['age'] += 1.0 / 60.0
        if p['age'] >= p['life']:
            canvas.delete(p['id'])
            continue
        p['x'] += p['dx']
        p['y'] += p['dy'] - 0.03
        canvas.coords(p['id'], p['x'], p['y'])
        alive.append(p)
    return alive
