"""
Music visualizer: cava captures system audio (PipeWire/PulseAudio) and reports 18
frequency bands, low to high; they are drawn across the board left to right.
"""
import contextlib
import math
import os
import subprocess
import tempfile
import threading
import time
from typing import List

from hivectl.color import Color, theme_color
from hivectl.layout import Key, Layout
from hivectl.palette import GradientPalette
from hivectl.sdk import Effect, EffectContext

BANDS = 18
MODES = ("bars", "pulse", "wave")
SCHEMES = ("theme", "vu", "fire", "ice", "rainbow")
BACKENDS = ("pulse", "pipewire")
METER = " ▁▂▃▄▅▆▇█"


def _even(colors: List[Color]) -> GradientPalette:
    return GradientPalette([(i / (len(colors) - 1), c) for i, c in enumerate(colors)])


def build_palette(scheme: str) -> GradientPalette:
    if scheme == "vu":
        return _even([Color.rgb(0, 255, 60), Color.rgb(120, 255, 0), Color.rgb(255, 230, 0),
                      Color.rgb(255, 120, 0), Color.rgb(255, 20, 40), Color.rgb(255, 255, 255)])
    if scheme == "fire":
        return _even([Color.rgb(80, 0, 0), Color.rgb(200, 30, 0), Color.rgb(255, 90, 0),
                      Color.rgb(255, 200, 0), Color.rgb(255, 255, 180)])
    if scheme == "ice":
        return _even([Color.rgb(0, 60, 120), Color.rgb(0, 160, 220), Color.rgb(68, 222, 245),
                      Color.rgb(170, 235, 255), Color.rgb(255, 255, 255)])
    if scheme == "rainbow":
        return _even([Color.from_hsv(i / BANDS, 0.9, 1.0) for i in range(BANDS)])
    r, g, b, _ = theme_color()
    base = Color.rgb(r, g, b)
    return _even([base * 0.4, base * 0.7, base, base * 1.2 + Color(0.16, 0.16, 0.16), Color(1, 1, 1)])


class Visualizer(Effect):
    name = "viz"
    title = "Music visualizer"
    cycle_duration = 3600.0
    default_fps = 35

    def __init__(self, mode: str = "bars", scheme: str = "theme", sensitivity: float = 1.3,
                 backend: str = "pulse", fps: int = 35):
        self.mode, self.scheme, self.sensitivity = mode, scheme, sensitivity
        self.backend, self.fps = backend, fps
        self.raw = [0] * BANDS
        self.proc = None
        self.cfg_path = None

    def setup(self, layout: Layout):
        self.keys = layout.keys
        self.center = (layout.width / 2.0, layout.height / 2.0 - 0.5)
        self.max_radius = math.hypot(layout.width / 2.0, 3.0)
        self.palette = build_palette(self.scheme)
        self.levels = [0.0] * BANDS
        self.phase = 0.0

        # Equal-width bands across the board; each band's keys ordered bottom to top
        self.band_of = {k.slot: min(BANDS - 1, int(k.cx / layout.width * BANDS)) for k in layout.keys}
        self.columns: List[List[Key]] = [[] for _ in range(BANDS)]
        for k in layout.keys:
            self.columns[self.band_of[k.slot]].append(k)
        for col in self.columns:
            col.sort(key=lambda k: -k.y)

        self._start_cava()

    def _start_cava(self):
        cfg = (f"[general]\nbars = {BANDS}\nframerate = {self.fps}\n"
               f"[input]\nmethod = {self.backend}\nsource = auto\n"
               "[output]\nmethod = raw\nraw_target = /dev/stdout\ndata_format = binary\n"
               "bit_format = 8bit\nchannels = mono\n")
        with tempfile.NamedTemporaryFile("w", prefix="hivectl-cava-", suffix=".cfg", delete=False) as f:
            f.write(cfg)
            self.cfg_path = f.name
        try:
            self.proc = subprocess.Popen(["cava", "-p", self.cfg_path], stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE)
        except FileNotFoundError:
            self.teardown()
            raise RuntimeError("cava is not installed (pacman -S cava)") from None
        time.sleep(0.3)
        if self.proc.poll() is not None:
            err = self.proc.stderr.read().decode(errors="replace").strip()
            self.teardown()
            raise RuntimeError(f"cava failed to start with the '{self.backend}' backend: {err[:200]}")
        threading.Thread(target=self._read_cava, args=(self.proc.stdout,), daemon=True).start()

    def _read_cava(self, stream):
        while True:
            data = stream.read(BANDS)
            if len(data) < BANDS:  # cava exited
                return
            self.raw = list(data)

    def teardown(self):
        if self.proc:
            self.proc.kill()
            self.proc.wait()
            self.proc = None
        if self.cfg_path:
            with contextlib.suppress(FileNotFoundError):
                os.unlink(self.cfg_path)
            self.cfg_path = None

    def render(self, ctx: EffectContext):
        if self.proc.poll() is not None:
            raise RuntimeError("cava stopped unexpectedly")
        raw = self.raw
        sens = self.sensitivity
        fall = 0.84 ** (ctx.dt * 35.0)  # peak hold that decays at the same rate at any fps
        for i in range(BANDS):
            self.levels[i] = max(min(1.0, raw[i] * sens / 255.0), self.levels[i] * fall)

        bass = min(1.0, max(raw[0:4]) * sens / 255.0)
        mid = min(1.0, sum(raw[4:12]) / 8.0 * sens / 255.0)
        treble = min(1.0, sum(raw[12:18]) / 6.0 * sens / 255.0)
        ctx.set_status("".join(METER[min(8, int(v * 8.99))] for v in self.levels)
                       + f"  bass {bass:4.0%}  mid {mid:4.0%}  treble {treble:4.0%}")

        if self.mode == "pulse":
            self._pulse(ctx, bass, mid, treble)
        elif self.mode == "wave":
            self._wave(ctx)
        else:
            self._bars(ctx)

    def _bars(self, ctx: EffectContext):
        for band, col in enumerate(self.columns):
            lit = int(self.levels[band] * len(col) + 0.5)
            for h, k in enumerate(col[:lit]):
                if self.scheme == "rainbow":
                    color = Color.from_hsv(band / BANDS, 0.9, 1.0)
                else:
                    color = self.palette.sample((h + 1) / len(col))
                ctx.canvas.set_pixel(k.slot, color)

    def _pulse(self, ctx: EffectContext, bass: float, mid: float, treble: float):
        self.phase += ctx.dt * (1.5 + bass * 3.5)
        front = (self.phase * 0.8) % 1.3
        cx, cy = self.center
        for k in self.keys:
            d = math.hypot(k.cx - cx, (k.cy - cy) * 1.5) / self.max_radius
            ring = max(0.0, 1.0 - abs(d - front) * 5.0) * bass
            core = max(0.0, 1.0 - d * 1.4) * bass * 0.8
            level = min(1.0, ring + core + mid * 0.35 + treble * 0.25)
            if level > 0.03:
                if self.scheme == "rainbow":
                    color = Color.from_hsv(d * 0.6 + self.phase * 0.1, 0.9, level)
                else:
                    color = self.palette.sample(level) * level
                ctx.canvas.set_pixel(k.slot, color)

    def _wave(self, ctx: EffectContext):
        self.phase += ctx.dt * 2.0
        for k in self.keys:
            energy = self.levels[self.band_of[k.slot]]
            level = min(1.0, energy * 0.8 + (math.sin(k.cx * 0.8 - self.phase) * 0.5 + 0.5) * energy * 0.4)
            if level > 0.03:
                ctx.canvas.set_pixel(k.slot, self.palette.sample(level) * level)
