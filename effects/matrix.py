"""
Matrix: green code rain falling down 24 columns, with white-hot heads and fading trails.
"""
import math
from hivectl import Effect, EffectContext, Layout, Color
from hivectl.math import sample_key_samples


class MatrixEffect(Effect):
    name = "matrix"
    title = "Matrix rain"
    cycle_duration = 16.0
    default_fps = 40

    def setup(self, layout: Layout):
        stream_x = [
            0.5, 1.2, 2.0, 2.8, 3.6, 4.4, 5.2, 6.0, 6.8, 7.6, 8.4, 9.2,
            10.0, 10.8, 11.6, 12.5, 13.5, 14.3, 15.25, 16.25, 17.25, 18.25, 18.9, 0.8
        ]
        speeds = [
            2.2, 3.4, 1.9, 2.8, 3.9, 2.1, 3.1, 2.5, 3.7, 1.8, 2.9, 3.3,
            2.3, 3.6, 2.0, 3.0, 2.6, 3.5, 2.4, 3.2, 2.7, 3.8, 2.1, 3.0
        ]
        offsets = [
            0.0, 3.2, 1.5, 5.1, 0.8, 4.3, 2.1, 6.0, 1.2, 4.8, 2.7, 0.4,
            5.5, 3.1, 1.9, 4.6, 0.7, 3.9, 2.0, 5.8, 1.1, 4.1, 2.9, 5.0
        ]
        trail_lens = [
            3.8, 4.5, 3.2, 5.0, 4.1, 3.6, 4.8, 3.5, 4.2, 5.2, 3.9, 4.6,
            3.4, 4.9, 3.7, 4.3, 5.1, 3.8, 4.4, 3.6, 5.0, 4.2, 3.5, 4.7
        ]
        self.streams = [{"x": x, "speed": s, "offset": o, "length": n}
                        for x, s, o, n in zip(stream_x, speeds, offsets, trail_lens)]

    def render(self, ctx: EffectContext):
        t = ctx.time
        canvas = ctx.canvas

        for key in ctx.keys:
            samples = sample_key_samples(key)
            acc_r, acc_g, acc_b = 0.0, 0.0, 0.0

            for sx, sy, weight in samples:
                sample_r, sample_g, sample_b = 0.0, 0.0, 0.0

                for s in self.streams:
                    dx = abs(sx - s["x"])
                    if dx > 1.3:
                        continue
                    gx = math.exp(-(dx * dx) / (2.0 * 0.55 * 0.55))

                    # Head travels from y=-1.5 to y=8.5, then wraps
                    period = 10.0 / s["speed"]
                    head_y = -1.5 + ((t + s["offset"]) % period) * s["speed"]
                    dy = sy - head_y

                    if -0.35 <= dy <= 0.25:
                        # Bright head
                        head = max(0.0, 1.0 - abs(dy + 0.05) / 0.35) * gx
                        sample_r += 230 * head
                        sample_g += 255 * head
                        sample_b += 230 * head
                    elif -s["length"] <= dy < -0.35:
                        # Trail above the head
                        decay = math.exp(-(abs(dy) - 0.35) / (s["length"] - 0.35) * 2.8) * gx
                        sample_r += 12 * decay
                        sample_g += 255 * decay
                        sample_b += 45 * decay

                    # Small splash when a head reaches the bottom row
                    if sy > 5.0 and 0.0 <= (head_y - 4.8) <= 0.9:
                        splash_age = (head_y - 4.8) / 0.9
                        if abs(dx - splash_age * 1.5) < 0.5:
                            splash = (1.0 - splash_age) ** 1.8
                            sample_r += 50 * splash
                            sample_g += 240 * splash
                            sample_b += 80 * splash

                acc_r += sample_r * weight
                acc_g += sample_g * weight
                acc_b += sample_b * weight

            acc_g += 3.0 + 1.5 * math.sin(t * 1.2 + key.cx * 0.3)  # faint green base
            canvas.set_pixel(key.slot, Color.rgb(acc_r, acc_g, acc_b))
