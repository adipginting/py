"""Render the pyagent architecture explainer: agent-loop.mp4.

Pure Pillow + imageio — no manim, no system ffmpeg (imageio-ffmpeg ships
its own binary). The animation follows the real loop in agent.py:

    prompt → stream → tool calls → re-prompt → Done

    pip install pillow imageio imageio-ffmpeg numpy
    python docs/animation/make_animation.py   # writes agent-loop.mp4 and .gif
"""

from __future__ import annotations

import math
from pathlib import Path

import imageio.v2 as imageio
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FPS = 20
DURATION = 12.0
W, H = 960, 540
SS = 2  # supersample factor for smooth edges

OUT = Path(__file__).with_name("agent-loop.mp4")

FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_DIR / name), size * SS)


F_TITLE = font("DejaVuSans-Bold.ttf", 26)
F_BOX = font("DejaVuSansMono-Bold.ttf", 15)
F_SUB = font("DejaVuSans.ttf", 11)
F_CAPTION = font("DejaVuSans.ttf", 17)
F_TERM = font("DejaVuSansMono.ttf", 13)
F_LABEL = font("DejaVuSansMono.ttf", 10)

BG = "#0d1117"
PANEL = "#161b22"
BORDER = "#30363d"
TEXT = "#e6edf3"
DIM = "#8b949e"
BLUE = "#58a6ff"    # prompt / messages
GREEN = "#3fb950"   # streamed text
ORANGE = "#d29922"  # tool calls
PURPLE = "#bc8cff"  # events


def hex_rgb(c: str) -> tuple[int, int, int]:
    return int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)


def with_alpha(c: str, a: int) -> tuple[int, int, int, int]:
    return (*hex_rgb(c), a)


def ease(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def path_pos(path: list[tuple[float, float]], t: float) -> tuple[float, float]:
    """Point at fraction t along a polyline, by arc length."""
    segs = []
    total = 0.0
    for a, b in zip(path, path[1:]):
        d = math.hypot(b[0] - a[0], b[1] - a[1])
        segs.append(d)
        total += d
    target = max(0.0, min(1.0, t)) * total
    for (a, b), d in zip(zip(path, path[1:]), segs):
        if target <= d and d > 0:
            f = target / d
            return a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f
        target -= d
    return path[-1]


class Box:
    def __init__(self, cx: float, cy: float, w: float, h: float,
                 title: str, sub: str, accent: str) -> None:
        self.cx, self.cy, self.w, self.h = cx, cy, w, h
        self.title, self.sub, self.accent = title, sub, accent

    def rect(self) -> list[int]:
        return [
            int((self.cx - self.w / 2) * SS), int((self.cy - self.h / 2) * SS),
            int((self.cx + self.w / 2) * SS), int((self.cy + self.h / 2) * SS),
        ]


BOXES = {
    "user": Box(110, 130, 110, 60, "you", "the prompt", BLUE),
    "cli": Box(300, 130, 140, 60, "cli.py", "prints events", PURPLE),
    "agent": Box(500, 130, 150, 64, "agent.py", "the loop", BLUE),
    "llm": Box(690, 130, 130, 60, "llm.py", "SSE stream", GREEN),
    "cloud": Box(850, 265, 150, 64, "LLM", "OpenRouter / Kimi", GREEN),
    "tools": Box(500, 265, 170, 64, "tools.py", "read · write · bash", ORANGE),
}

# Static connector lines between boxes.
CONNECTORS = [
    [(165, 130), (230, 130)],
    [(370, 130), (425, 130)],
    [(575, 130), (625, 130)],
    [(690, 160), (690, 200)],
    [(755, 232), (722, 165)],
    [(500, 162), (500, 233)],
]

# Moving packets: (path, t0, t1, color, label).
PACKETS = [
    # 1 · prompt in
    ([(168, 130), (227, 130)], 1.2, 1.7, BLUE, "prompt"),
    ([(373, 130), (422, 130)], 1.8, 2.3, BLUE, None),
    # 2 · request out
    ([(578, 130), (622, 130)], 2.6, 3.0, BLUE, "messages + tools"),
    ([(692, 163), (692, 200), (748, 232)], 3.0, 3.4, BLUE, None),
    # 3 · tokens stream back, events to the CLI
    ([(748, 232), (692, 200), (692, 163), (625, 130), (578, 130)], 3.8, 4.25, GREEN, "TextChunk"),
    ([(422, 130), (373, 130)], 4.0, 4.35, PURPLE, None),
    ([(748, 232), (692, 200), (692, 163), (625, 130), (578, 130)], 4.4, 4.85, GREEN, None),
    ([(422, 130), (373, 130)], 4.6, 4.95, PURPLE, None),
    ([(748, 232), (692, 200), (692, 163), (625, 130), (578, 130)], 5.0, 5.45, GREEN, None),
    ([(422, 130), (373, 130)], 5.2, 5.55, PURPLE, "TextDelta"),
    # 4 · tool call
    ([(748, 232), (692, 200), (692, 163), (625, 130), (578, 130)], 5.9, 6.35, ORANGE, "ToolCall"),
    ([(422, 130), (373, 130)], 6.4, 6.7, PURPLE, None),
    ([(500, 165), (500, 230)], 6.7, 7.1, ORANGE, "read(path)"),
    ([(500, 230), (500, 165)], 7.3, 7.7, ORANGE, "result"),
    # 5 · second lap, compressed
    ([(578, 130), (622, 130)], 8.5, 8.75, BLUE, None),
    ([(692, 163), (692, 200), (748, 232)], 8.75, 9.0, BLUE, None),
    ([(748, 232), (692, 200), (692, 163), (625, 130), (578, 130)], 9.05, 9.45, GREEN, None),
    ([(422, 130), (373, 130)], 9.2, 9.5, PURPLE, None),
    # 6 · done
    ([(422, 130), (373, 130)], 9.9, 10.3, PURPLE, "Done"),
]

# Boxes that glow during an interval: (name, t0, t1).
GLOWS = [
    ("user", 1.2, 1.7), ("cli", 1.7, 2.3), ("agent", 2.3, 3.0),
    ("llm", 3.0, 3.4), ("cloud", 3.3, 3.9),
    ("llm", 3.8, 5.5), ("agent", 3.8, 5.6), ("cli", 4.0, 5.6),
    ("agent", 5.9, 6.7), ("tools", 6.7, 7.7), ("agent", 7.7, 8.8),
    ("cloud", 8.9, 9.1), ("agent", 9.9, 10.3), ("cli", 9.9, 10.4),
]

# Bottom captions: (t0, t1, text).
CAPTIONS = [
    (1.1, 2.5, "1 · append the user prompt to messages"),
    (2.6, 3.7, "2 · stream one completion from the LLM"),
    (3.8, 5.75, "text flows back token by token → TextDelta events"),
    (5.85, 7.85, "3 · tool calls run locally; results re-enter the loop"),
    (7.95, 9.5, "loop until the model asks for nothing"),
    (9.6, 11.6, "4 · no tool calls → yield Done, print usage"),
]

# Terminal lines: (t0, text, color, typing_duration or None).
TERMINAL = [
    (4.05, "This repo is a minimal coding agent —", GREEN, 1.5),
    (6.55, "▶ read: README.md", ORANGE, None),
    (7.45, "  → # pyagent", DIM, None),
    (8.95, "...one provider, one loop, one printer.", GREEN, 1.1),
    (10.15, "[usage: 1033 in / 33 out]", DIM, None),
]

LOOP_ARC = (7.95, 8.75)  # circular arrow around agent.py


def draw_centered(draw: ImageDraw.ImageDraw, cx: float, y: float, text: str,
                  f: ImageFont.FreeTypeFont, fill, alpha: int = 255) -> None:
    if isinstance(fill, str):
        fill = with_alpha(fill, alpha)
    width = draw.textlength(text, font=f)
    draw.text((int(cx * SS - width / 2), int(y * SS)), text, font=f, fill=fill)


def render(t: float) -> Image.Image:
    img = Image.new("RGB", (W * SS, H * SS), BG)
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    fade = ease(t / 0.8)
    fa = int(255 * fade)

    draw_centered(draw, W / 2, 22, "pyagent — how the agent loop works", F_TITLE, TEXT, fa)
    draw_centered(draw, W / 2, 52, "events are the contract", F_SUB, DIM, fa)

    for conn in CONNECTORS:
        pts = [(int(x * SS), int(y * SS)) for x, y in conn]
        draw.line(pts, fill=with_alpha(BORDER, fa), width=2 * SS)

    for name, box in BOXES.items():
        glow = 0.0
        for gname, t0, t1 in GLOWS:
            if gname == name and t0 <= t <= t1:
                glow = max(glow, min((t - t0) / 0.2, 1.0, (t1 - t) / 0.2))
        r = box.rect()
        if glow > 0:
            pad = int(6 * SS * glow)
            draw.rounded_rectangle(
                [r[0] - pad, r[1] - pad, r[2] + pad, r[3] + pad],
                radius=int(12 * SS), fill=with_alpha(box.accent, int(60 * glow * fade)))
        draw.rounded_rectangle(r, radius=int(10 * SS),
                               fill=with_alpha(PANEL, fa),
                               outline=with_alpha(box.accent if glow > 0 else BORDER, fa),
                               width=max(1, int(2 * SS)))
        draw_centered(draw, box.cx, box.cy - 15, box.title, F_BOX, TEXT, fa)
        draw_centered(draw, box.cx, box.cy + 6, box.sub, F_SUB, DIM, fa)

    # Circular "loop" arrow around agent.py.
    a0, a1 = LOOP_ARC
    if a0 <= t <= a1:
        pulse = ease(min((t - a0) / 0.3, 1.0, (a1 - t) / 0.3))
        cx, cy, rad = 500 * SS, 130 * SS, 58 * SS
        sweep = 300 * ease((t - a0) / (a1 - a0))
        start = -90
        bbox = [cx - rad, cy - rad, cx + rad, cy + rad]
        draw.arc(bbox, start, start + sweep, fill=with_alpha(BLUE, int(220 * pulse)),
                 width=int(3 * SS))
        ang = math.radians(start + sweep)
        tip = (cx + rad * math.cos(ang), cy + rad * math.sin(ang))
        left = (tip[0] - 10 * SS * math.cos(ang - 0.5), tip[1] - 10 * SS * math.sin(ang - 0.5))
        right = (tip[0] - 10 * SS * math.cos(ang + 0.5), tip[1] - 10 * SS * math.sin(ang + 0.5))
        draw.polygon([tip, left, right], fill=with_alpha(BLUE, int(220 * pulse)))

    # Packets.
    for path, t0, t1, color, label in PACKETS:
        if not (t0 <= t <= t1):
            continue
        x, y = path_pos(path, ease((t - t0) / (t1 - t0)))
        px, py = int(x * SS), int(y * SS)
        draw.ellipse([px - 13 * SS, py - 13 * SS, px + 13 * SS, py + 13 * SS],
                     fill=with_alpha(color, 50))
        draw.ellipse([px - 6 * SS, py - 6 * SS, px + 6 * SS, py + 6 * SS],
                     fill=with_alpha(color, 255))
        if label:
            lw = draw.textlength(label, font=F_LABEL)
            draw.text((px - lw / 2, py - 24 * SS), label, font=F_LABEL,
                      fill=with_alpha(color, 230))

    # Terminal panel.
    term = [60 * SS, 392 * SS, 900 * SS, 524 * SS]
    draw.rounded_rectangle(term, radius=int(8 * SS), fill=with_alpha(PANEL, fa),
                           outline=with_alpha(BORDER, fa), width=max(1, SS))
    draw.text((74 * SS, 400 * SS), "terminal — cli.py rendering the event stream",
              font=F_LABEL, fill=with_alpha(DIM, fa))
    y = 424
    for t0, text, color, typing in TERMINAL:
        if t < t0:
            continue
        shown = text
        if typing is not None:
            n = min(len(text), int(len(text) * (t - t0) / typing))
            shown = text[:n]
        draw.text((78 * SS, y * SS), shown, font=F_TERM, fill=with_alpha(color, fa))
        if typing is not None and t < t0 + typing:
            cx = 78 * SS + draw.textlength(shown, font=F_TERM)
            draw.rectangle([cx + 2, y * SS, cx + 9 * SS, (y + 14) * SS],
                           fill=with_alpha(color, 200))
        y += 20

    # Caption.
    for t0, t1, text in CAPTIONS:
        if t0 <= t <= t1:
            alpha = int(255 * ease(min((t - t0) / 0.25, 1.0, (t1 - t) / 0.25)))
            draw_centered(draw, W / 2, 348, text, F_CAPTION, TEXT, alpha)

    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB").resize(
        (W, H), Image.LANCZOS)


def main() -> None:
    frames = int(DURATION * FPS)
    with imageio.get_writer(OUT, fps=FPS, codec="libx264", quality=8,
                            pixelformat="yuv420p", macro_block_size=1) as writer:
        for i in range(frames):
            writer.append_data(np.asarray(render(i / FPS)))
    print(f"wrote {OUT} ({frames} frames @ {FPS} fps)")

    gif = OUT.with_suffix(".gif")
    gif_fps = 15
    with imageio.get_writer(gif, fps=gif_fps) as writer:
        for i in range(int(DURATION * gif_fps)):
            frame = render(i / gif_fps).resize((640, 360), Image.LANCZOS)
            writer.append_data(np.asarray(frame))
    print(f"wrote {gif} ({int(DURATION * gif_fps)} frames @ {gif_fps} fps)")


if __name__ == "__main__":
    main()
