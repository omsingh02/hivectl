"""Renders docs/effects/*.gif from the real effect code (needs Pillow): python tools/render_previews.py"""
import contextlib
import io
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from hivectl import GLOBAL_LAYOUT, Canvas  # noqa: E402
from hivectl.hud import HudEffect  # noqa: E402
from hivectl.input import KeyEvent  # noqa: E402
from hivectl.sdk import EffectContext, discover_effects  # noqa: E402
from hivectl.visualizer import BANDS, Visualizer  # noqa: E402

OUT = ROOT / "docs/effects"
S, PAD, BG, FPS = 26, 14, (10, 10, 14), 15
W, H = int(19.25 * S) + PAD * 2, int(6 * S) + PAD * 2


def draw(canvas):
    base = Image.new("RGB", (W, H), BG)
    glow = Image.new("RGB", (W, H), BG)
    d, g = ImageDraw.Draw(base), ImageDraw.Draw(glow)
    for k in GLOBAL_LAYOUT.keys:
        x0, y0 = PAD + k.x * S + 2, PAD + k.y * S + 2
        box = [x0, y0, x0 + k.w * S - 4, y0 + k.h * S - 4]
        rgb = canvas.pixels[k.slot].to_tuple()
        g.rounded_rectangle(box, 5, fill=rgb)
        d.rounded_rectangle(box, 5, fill=tuple(int(v * 0.88) + 14 for v in rgb), outline=(38, 38, 48))
    halo = Image.blend(Image.new("RGB", (W, H), BG), glow.filter(ImageFilter.GaussianBlur(8)), 0.55)
    mask = base.convert("L").point(lambda v: 255 if v > 16 else 0)
    return Image.composite(base, halo, mask)


def save_gif(name, frames):
    sample = Image.new("RGB", (W, H * 4))
    for i, f in enumerate(frames[:: max(1, len(frames) // 4)][:4]):
        sample.paste(f, (0, i * H))
    palette = sample.quantize(colors=160, dither=Image.Dither.NONE)
    out = [f.quantize(palette=palette, dither=Image.Dither.NONE) for f in frames]
    out[0].save(OUT / f"{name}.gif", save_all=True, append_images=out[1:], duration=int(1000 / FPS),
                loop=0, optimize=True)
    print(f"{name:<12} {len(frames):3d} frames {(OUT / f'{name}.gif').stat().st_size // 1024} KB")


def record(effect, seconds, events=None, before_frame=None):
    canvas = Canvas()
    ctx = EffectContext(canvas, GLOBAL_LAYOUT)
    effect.setup(GLOBAL_LAYOUT)
    frames = []
    for i in range(int(seconds * FPS)):
        t = i / FPS
        ctx.time, ctx.dt = t, 1.0 / FPS
        ctx.cycle_time = t % effect.cycle_duration
        ctx.cycle_progress = ctx.cycle_time / effect.cycle_duration
        ctx.key_events = events(t, i) if events else []
        if before_frame:
            before_frame(ctx, t)
        canvas.clear()
        effect.render(ctx)
        frames.append(draw(canvas))
    return frames


def typing(text, start=0.3, gap=0.16):
    names = {" ": "SPACE", "\n": "ENTER"}
    schedule = {int((start + i * gap) * FPS): names.get(ch, ch.upper()) for i, ch in enumerate(text)}
    return lambda t, i: [KeyEvent(GLOBAL_LAYOUT.get(schedule[i]), True, t)] if i in schedule else []


class FakeCava:
    def poll(self):
        return None


def viz(mode):
    v = Visualizer(mode, "vu" if mode == "bars" else "fire" if mode == "pulse" else "ice")
    v._start_cava = lambda: None
    v.proc = FakeCava()

    def feed(ctx, t):
        beat = max(0.0, math.sin(t * math.pi * 2.2)) ** 6
        v.raw = [int(max(0, min(255, 255 * (0.55 + 0.35 * math.sin(t * 2.7 + b * 0.8) * math.sin(t * 1.1 + b * 1.7)
                                           - b * 0.022 + (0.5 * beat if b < 4 else 0.0))))) for b in range(BANDS)]
    return v, feed


SAMPLE_BINDS = [(64, k, d, a) for k, d, a in [
    ("Return", "exec", "foot"), ("Q", "killactive", ""), ("W", "exec", "firefox"), ("E", "exec", "thunar"),
    ("F", "togglefloating", ""), ("M", "fullscreen", "1"), ("Space", "layoutmsg", "swapwithmaster"),
    ("left", "movefocus", "l"), ("right", "movefocus", "r"), ("up", "movefocus", "u"), ("down", "movefocus", "d"),
    ("P", "exec", "playerctl play-pause"), ("comma", "exec", "playerctl previous"), ("period", "exec", "playerctl next"),
    ("minus", "exec", "wpctl set-volume @DEFAULT_SINK@ 5%-"), ("equal", "exec", "wpctl set-volume @DEFAULT_SINK@ 5%+"),
    ("L", "exec", "hyprlock"), ("R", "submap", "resize"), ("D", "exec", "rofi -show drun"), ("V", "exec", "pavucontrol"),
]] + [(64, str(n % 10), "workspace", str(n)) for n in range(1, 11)] \
  + [(65, str(n % 10), "movetoworkspace", str(n)) for n in range(1, 11)] \
  + [(65, "Q", "exit", ""), (65, "left", "movewindow", "l"), (65, "right", "movewindow", "r"),
     (65, "up", "movewindow", "u"), (65, "down", "movewindow", "d"), (8, "Tab", "cyclenext", ""),
     (8, "Space", "exec", "rofi -show window")]


def hud():
    h = HudEffect()
    h._poll = lambda force_binds=False: None
    h.setup = lambda layout: (setattr(h, "layout", layout),
                              setattr(h, "gauge_slots", {n: [layout.get(k).slot for k in keys]
                                                         for n, keys in __import__("hivectl.hud").hud.GAUGES.items()}),
                              setattr(h, "layers", h._build_layers([{"modmask": m, "key": k, "dispatcher": d, "arg": a}
                                                                    for m, k, d, a in SAMPLE_BINDS])))
    h.active_ws, h.occupied, h.connected = 3, {1, 2, 3, 5}, True
    h.stats.cpu, h.stats.ram, h.stats.battery, h.stats.volume = 38.0, 61.0, 82.0, 70.0
    layers = [(0.0, set()), (1.2, {"LGUI"}), (3.0, {"LGUI", "LSHIFT"}), (4.8, {"LALT"}), (6.0, set())]

    def hold(ctx, t):
        names = [held for start, held in layers if t >= start][-1]
        ctx.held_keys = {GLOBAL_LAYOUT.get(n) for n in names}
    return h, hold


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    with contextlib.redirect_stderr(io.StringIO()):
        effects = discover_effects()
    for name, cls in effects.items():
        e = cls()
        if name == "reactive":
            save_gif(name, record(e, 5.0, typing("hello world\n")))
        else:
            save_gif(name, record(e, min(e.cycle_duration, 6.0) if name != "supernova" else 14.0))
    for mode in ("bars", "pulse", "wave"):
        v, feed = viz(mode)
        save_gif(f"viz-{mode}", record(v, 4.0, before_frame=feed))
    h, hold = hud()
    save_gif("hud", record(h, 6.6, before_frame=hold))
