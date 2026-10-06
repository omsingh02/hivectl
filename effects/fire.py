"""
Fire: flames rising from the bottom row, hottest at the spacebar, fading out at the F-keys.
"""
import math
from kreo import Effect, EffectContext, Layout, Color, GradientPalette
from kreo.math import fbm3d, perlin3d, sample_key_samples


class FireEffect(Effect):
    name = "fire"
    title = "Fire"
    cycle_duration = 10.0
    default_fps = 40

    def setup(self, layout: Layout):
        self.palette = GradientPalette([
            (0.00, Color.from_hex("#000000")),
            (0.18, Color.from_hex("#3A0200")),
            (0.38, Color.from_hex("#B80800")),
            (0.60, Color.from_hex("#FF4D00")),
            (0.82, Color.from_hex("#FFB700")),
            (1.00, Color.from_hex("#FFFFE6")),
        ])

    def render(self, ctx: EffectContext):
        t = ctx.time
        canvas = ctx.canvas

        for key in ctx.keys:
            samples = sample_key_samples(key)
            acc_color = Color(0, 0, 0)

            for sx, sy, weight in samples:
                # 0.0 at the F-key row, 1.0 at the bottom row
                depth = sy / 5.5

                # Noise scrolls upward over time so the flames rise
                turb1 = fbm3d(sx * 0.35, sy * 0.6 + t * 2.8, t * 0.4, octaves=3)
                turb2 = perlin3d(sx * 0.8 - t * 0.5, sy * 0.4 + t * 3.5, t * 0.8)
                heat = (depth ** 1.3) * 0.72 + (turb1 - 0.4) * 0.55 + (turb2 - 0.5) * 0.35

                # Glowing coals along the bottom row
                if sy > 5.0:
                    heat = max(heat, 0.65 + 0.25 * math.sin(t * 8.0 + sx * 2.0))

                # Occasional sparks drifting up
                spark = perlin3d(sx * 1.5, sy * 1.2 + t * 4.0, t * 2.0)
                if spark > 0.82:
                    heat += (spark - 0.82) / 0.18 * 0.6

                acc_color = acc_color + self.palette.sample(max(0.0, min(1.0, heat))) * weight

            canvas.set_pixel(key.slot, acc_color)
