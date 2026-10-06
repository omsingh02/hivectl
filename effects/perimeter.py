"""
Perimeter: a comet runs clockwise around the outer ring of keys; each lap fires a ring
outward from the middle of the typing area.
"""
import math
from hivectl import Effect, EffectContext, Layout, Color, GradientPalette


class PerimeterEffect(Effect):
    name = "perimeter"
    title = "Perimeter runner"
    cycle_duration = 6.0
    default_fps = 40

    TRAIL = 8.0           # keys
    LAPS_PER_SEC = 0.8
    BURST = 0.35          # fraction of a lap the burst ring is visible

    def setup(self, layout: Layout):
        ring = ["ESC", "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12",
                "PRINTSCREEN", "DELETE", "PAGEUP", "PAGEDOWN",
                "KP_SUBTRACT", "KP_ADD", "KP_ENTER",
                "KP_DECIMAL", "KP_0", "RIGHT", "DOWN", "LEFT", "RCTRL", "FN", "RALT", "SPACE",
                "LALT", "LGUI", "LCTRL",
                "LSHIFT", "CAPSLOCK", "TAB", "GRAVE"]
        self.ring_index = {layout.get(name).slot: i for i, name in enumerate(ring)}
        self.ring_len = len(ring)
        self.center = (layout.cx, layout.cy)

        self.runner_palette = GradientPalette([
            (0.00, Color.from_hex("#000000")),
            (0.20, Color.from_hex("#051B33")),
            (0.50, Color.from_hex("#0099FF")),
            (0.80, Color.from_hex("#5CFFEA")),
            (1.00, Color.from_hex("#FFFFFF")),
        ])
        self.burst_palette = GradientPalette([
            (0.00, Color.from_hex("#000000")),
            (0.40, Color.from_hex("#3D0052")),
            (0.70, Color.from_hex("#FF007F")),
            (0.90, Color.from_hex("#FFB700")),
            (1.00, Color.from_hex("#FFFFFF")),
        ])

    def render(self, ctx: EffectContext):
        laps = ctx.time * self.LAPS_PER_SEC
        head = (laps * self.ring_len) % self.ring_len
        lap_phase = laps % 1.0
        burst = lap_phase / self.BURST if lap_phase < self.BURST else None

        for key in ctx.keys:
            color = Color(0, 0, 0)

            idx = self.ring_index.get(key.slot)
            if idx is not None:
                behind = (head - idx) % self.ring_len
                if behind <= self.TRAIL:
                    intensity = (1.0 - behind / self.TRAIL) ** 1.6
                    color = self.runner_palette.sample(intensity) * intensity

            if burst is not None:
                dist = math.hypot(key.cx - self.center[0], key.cy - self.center[1])
                ring_dist = abs(dist - burst * 11.0)
                if ring_dist < 2.0:
                    strength = (1.0 - ring_dist / 2.0) ** 1.5 * (1.0 - burst)
                    color = color + self.burst_palette.sample(strength) * strength

            ctx.canvas.set_pixel(key.slot, color)
