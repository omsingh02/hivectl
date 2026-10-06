"""
Scanner: red beam sweeping left/right across the whole board with a fading trail.
"""
import math
from kreo import Effect, EffectContext, Layout, Color, GradientPalette
from kreo.math import sample_key_samples

class ScannerEffect(Effect):
    name = "scanner"
    title = "Scanner"
    cycle_duration = 3.6
    default_fps = 40

    def setup(self, layout: Layout):
        self.min_x = 0.5
        self.max_x = 18.5
        self.range_x = self.max_x - self.min_x

        # High-intensity laser palette (Incandescent core -> Radiant Neon Red -> Dark phosphor)
        self.palette = GradientPalette([
            (0.00, Color.from_hex("#000000")),
            (0.20, Color.from_hex("#330000")),  # Dark red phosphor
            (0.50, Color.from_hex("#B80000")),  # Saturated crimson
            (0.75, Color.from_hex("#FF1A1A")),  # Laser red
            (0.92, Color.from_hex("#FFA6A6")),  # Incandescent core
            (1.00, Color.from_hex("#FFFFFF")),  # Blinding white glint
        ])

    def render(self, ctx: EffectContext):
        t = ctx.time
        canvas = ctx.canvas

        # Harmonic pendulum sweep: smooth turnaround at left (0.5) and right (18.5)
        sweep_freq = 2.0 * math.pi / self.cycle_duration
        phase = t * sweep_freq
        norm_pos = 0.5 - 0.5 * math.cos(phase)  # 0.0 to 1.0
        beam_x = self.min_x + norm_pos * self.range_x

        # Sweep direction: +1 moving right, -1 moving left
        direction = 1.0 if math.sin(phase) > 0 else -1.0

        # Boundary impact flash (when near x min or max)
        at_edge = norm_pos < 0.05 or norm_pos > 0.95
        impact_glow = math.sin(phase * 2.0) ** 4.0 if at_edge else 0.0

        for key in ctx.keys:
            samples = sample_key_samples(key)
            acc_color = Color(0, 0, 0)

            for sx, sy, weight in samples:
                dx = sx - beam_x

                # 1. Main Beam Core (sharp Gaussian within 0.7u)
                core_dist = abs(dx)
                core_int = math.exp(-((core_dist / 0.45) ** 2))

                # 2. Directional Phosphor Persistence Trail (lags behind direction of motion)
                trail_int = 0.0
                trail_vector = -dx * direction  # Positive behind the beam
                if trail_vector > 0.0:
                    trail_len = 4.2  # Trail stretches 4.2 units behind beam
                    if trail_vector < trail_len:
                        trail_prog = 1.0 - (trail_vector / trail_len)
                        trail_int = (trail_prog ** 2.2) * 0.75

                total_int = min(1.0, max(core_int, trail_int))

                # 3. Ambient chassis backlight & boundary impact
                ambient = 0.03
                if impact_glow > 0.1:
                    edge_dist = min(abs(sx - self.min_x), abs(sx - self.max_x))
                    if edge_dist < 3.0:
                        ambient += (1.0 - edge_dist / 3.0) * impact_glow * 0.35

                c = self.palette.sample(max(ambient, total_int))
                acc_color = acc_color + c * weight

            canvas.set_pixel(key.slot, acc_color)
