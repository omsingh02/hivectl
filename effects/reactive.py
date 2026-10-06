"""
Reactive: pressed keys flash and send out rings; Space launches a wave up the board and
Enter sweeps a line back to the left edge. Reads keystrokes straight from the keyboard.
"""
import math
from kreo import Effect, EffectContext, Layout, Color
from kreo.math import sample_key_samples

KEY_COLORS = [Color.rgb(0, 240, 255), Color.rgb(0, 255, 180), Color.rgb(120, 100, 255),
              Color.rgb(255, 0, 140), Color.rgb(255, 180, 0)]
SPACE_COLOR = Color.rgb(255, 210, 50)
SURGE_COLOR = Color.rgb(255, 200, 60)
FOUNTAIN_COLOR = Color.rgb(0, 240, 255)
ENTER_COLOR = Color.rgb(255, 0, 110)
SWEEP_COLOR = Color.rgb(255, 0, 120)
BACKSPACE_COLOR = Color.rgb(255, 45, 0)
NUMPAD_COLOR = Color.rgb(0, 255, 150)
HOME_COLOR = Color.rgb(0, 60, 90)
HOMING_COLOR = Color.rgb(255, 160, 20)
WHITE = Color(1.0, 1.0, 1.0)
LIFETIME = 1.3


class Strike:
    __slots__ = ("key", "start", "color", "kind")

    def __init__(self, key, start, color, kind):
        self.key, self.start, self.color, self.kind = key, start, color, kind


class ReactiveEffect(Effect):
    name = "reactive"
    title = "Reactive typing"
    cycle_duration = 3600.0
    default_fps = 40
    uses_input = True

    def setup(self, layout: Layout):
        self.home = layout.get_zone("home")
        self.homing = [layout.get("F"), layout.get("J")]
        self.space_x = layout.get("SPACE").cx
        self.strikes = []
        self.history = []
        self.color_idx = 0

    def render(self, ctx: EffectContext):
        now = ctx.time
        canvas = ctx.canvas

        for ev in ctx.key_events:
            if not ev.is_down:
                continue
            name = ev.key.name
            kind = "space" if name == "SPACE" else "enter" if name in ("ENTER", "KP_ENTER") else "key"
            if kind == "space":
                color = SPACE_COLOR
            elif kind == "enter":
                color = ENTER_COLOR
            elif name == "BACKSPACE":
                color = BACKSPACE_COLOR
            elif name.startswith("KP_"):
                color = NUMPAD_COLOR
            else:
                color = KEY_COLORS[self.color_idx % len(KEY_COLORS)]
                self.color_idx += 1
            self.strikes.append(Strike(ev.key, now, color, kind))
            self.history.append(now)

        self.strikes = [s for s in self.strikes if now - s.start <= LIFETIME]
        self.history = [t for t in self.history if t > now - 5.0]
        ctx.set_status(f"{len(self.history) * 12 // 5} wpm" if self.history else "waiting for keys")

        # Resting state: dim home row, breathing amber F/J
        breath = 0.20 + 0.15 * math.sin(now * 1.8)
        for k in self.home:
            canvas.set_pixel(k.slot, HOME_COLOR * breath)
        for k in self.homing:
            canvas.set_pixel(k.slot, HOMING_COLOR * min(1.0, breath * 1.5))

        if not self.strikes:
            return

        for key in ctx.keys:
            light = Color(0, 0, 0)

            for s in self.strikes:
                if s.key is key:
                    dt = now - s.start
                    light = light + s.color * math.exp(-dt / 0.35) + WHITE * max(0.0, 1.0 - dt * 9.0)

            for sx, sy, weight in sample_key_samples(key):
                for s in self.strikes:
                    dt = now - s.start
                    if s.kind == "space":
                        # Surge along the bottom row, then a band rising up the board
                        if sy > 5.0:
                            off = abs(abs(sx - self.space_x) - dt * 18.0)
                            if off < 2.0:
                                light = light + SURGE_COLOR * ((1.0 - off / 2.0) * math.exp(-dt / 0.35) * 0.8 * weight)
                        band_y = 5.0 - dt * 6.5
                        if band_y >= -0.5 and abs(sy - band_y) < 1.0:
                            band = math.cos(abs(sy - band_y) * math.pi / 2.0) ** 2
                            light = light + FOUNTAIN_COLOR * (band * math.exp(-dt / 0.5) * 0.75 * weight)
                    elif s.kind == "enter":
                        # Line sweeping from the Enter key back to the left edge, then a flash on Esc
                        sweep_x = 14.0 - dt * 16.0
                        if sx <= 14.5 and sweep_x >= -1.0 and abs(sx - sweep_x) < 1.4:
                            band = math.cos(abs(sx - sweep_x) / 1.4 * math.pi / 2.0) ** 2
                            light = light + SWEEP_COLOR * (band * math.exp(-dt / 0.7) * 0.95 * weight)
                        if key.name == "ESC" and 0.0 <= dt - 0.875 <= 0.4:
                            light = light + WHITE * (math.exp(-(dt - 0.875) / 0.12) * weight)
                    else:
                        # Ring expanding from the pressed key
                        radius = dt * 12.0
                        if radius < 9.0:
                            off = abs(math.hypot(sx - s.key.cx, sy - s.key.cy) - radius)
                            if off < 1.3:
                                ring = math.cos(off / 1.3 * math.pi / 2.0) ** 2
                                light = light + s.color * (ring * math.exp(-dt / 0.45) * 0.85 * weight)

            if light.r or light.g or light.b:
                canvas.set_pixel(key.slot, canvas.pixels[key.slot] + light)
