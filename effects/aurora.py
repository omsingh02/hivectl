"""
Aurora: slow green/cyan/violet curtains drifting across the board (fractal noise).
"""
import math
from hivectl import Effect, EffectContext, Layout, Color, GradientPalette
from hivectl.math import fbm3d, sample_key_samples

class AuroraEffect(Effect):
    name = "aurora"
    title = "Aurora"
    cycle_duration = 12.0
    default_fps = 40

    def setup(self, layout: Layout):
        self.palette = GradientPalette([
            (0.00, Color.from_hex("#010814")),  # Deep arctic night sky
            (0.25, Color.from_hex("#00384D")),  # High atmosphere navy
            (0.50, Color.from_hex("#00F2FE")),  # Electric polar cyan
            (0.72, Color.from_hex("#0BE881")),  # Ionospheric emerald ribbon
            (0.88, Color.from_hex("#7D5FFF")),  # High-altitude violet
            (1.00, Color.from_hex("#FF007F")),  # Solar storm crimson apex
        ])

    def render(self, ctx: EffectContext):
        t = ctx.time
        canvas = ctx.canvas

        for key in ctx.keys:
            samples = sample_key_samples(key)
            acc_color = Color(0, 0, 0)

            for sx, sy, weight in samples:
                # 3D continuous fBm noise field drifting from right to left (east to west)
                turb1 = fbm3d(sx * 0.18 + t * 0.25, sy * 0.35, t * 0.15, octaves=3)
                turb2 = math.sin(sx * 0.45 - t * 0.6 + turb1 * 2.5)

                # Vertical curtain curtain ribbons (flowing from bottom to top)
                ribbon = (turb1 * 0.6 + (turb2 * 0.5 + 0.5) * 0.4)
                intensity = max(0.0, min(1.0, ribbon))

                # Altitude modulation (brighter towards function row, softer on spacebar)
                altitude = 1.0 - (sy / 5.5) * 0.3
                sample_pos = min(1.0, (intensity ** 1.3) * altitude)

                c = self.palette.sample(sample_pos) * (0.8 + 0.2 * math.sin(t * 1.8 + sx * 0.4))
                acc_color = acc_color + c * weight

            canvas.set_pixel(key.slot, acc_color)
