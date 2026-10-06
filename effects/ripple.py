"""
Ripple: rings of light spreading out from the middle of the typing area.
"""
import math
from kreo import Effect, EffectContext, Layout, Color, GradientPalette
from kreo.math import sample_key_samples


class RippleEffect(Effect):
    name = "ripple"
    title = "Ripple"
    cycle_duration = 8.0
    default_fps = 40

    WAVE_FREQ = 1.1     # radians per key unit (~5.7 keys between crests)
    WAVE_SPEED = 2.8

    def setup(self, layout: Layout):
        self.origin = (layout.cx, layout.cy)
        self.palette = GradientPalette([
            (0.00, Color.from_hex("#000000")),
            (0.35, Color.from_hex("#021A3A")),
            (0.65, Color.from_hex("#0088CC")),
            (0.85, Color.from_hex("#00D2FF")),
            (1.00, Color.from_hex("#C8FAFF")),
        ])

    def render(self, ctx: EffectContext):
        t = ctx.time
        for key in ctx.keys:
            acc = Color(0, 0, 0)
            for sx, sy, weight in sample_key_samples(key):
                dist = math.hypot(sx - self.origin[0], sy - self.origin[1])
                wave = math.sin(dist * self.WAVE_FREQ - t * self.WAVE_SPEED)
                level = (wave * 0.5 + 0.5) ** 2 / (1.0 + dist * 0.06)
                acc = acc + self.palette.sample(level) * weight
            ctx.canvas.set_pixel(key.slot, acc)
