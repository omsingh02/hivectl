"""
Heartbeat: red double pulse (lub-dub) radiating from the middle of the typing area.
"""
import math
from kreo import Effect, EffectContext, Layout, Color, GradientPalette
from kreo.math import sample_key_samples

class HeartbeatEffect(Effect):
    name = "heartbeat"
    title = "Heartbeat"
    cycle_duration = 1.8  # ~67 BPM resting heart rate
    default_fps = 40

    def setup(self, layout: Layout):
        self.cx = layout.cx  # Typing center (7.0, 2.8)
        self.cy = layout.cy

        self.palette = GradientPalette([
            (0.00, Color.from_hex("#000000")),  # Resting diastole
            (0.20, Color.from_hex("#260005")),  # Deep venous crimson
            (0.45, Color.from_hex("#800018")),  # Arterial red
            (0.70, Color.from_hex("#FF003C")),  # Vibrant systolic ruby
            (0.88, Color.from_hex("#FF6B8B")),  # High-pressure coral
            (1.00, Color.from_hex("#FFFFFF")),  # Peak systolic glint
        ])

    def render(self, ctx: EffectContext):
        t = ctx.cycle_time  # 0.0 to 1.8 seconds
        canvas = ctx.canvas

        # Physiological heartbeat waveform:
        # Stroke 1: Atrial kick (t = 0.0s to 0.25s)
        # Stroke 2: Ventricular surge (t = 0.32s to 0.95s)
        # Diastolic rest: (t = 0.95s to 1.80s)

        beat1_active = t < 0.25
        beat2_active = 0.30 <= t < 0.95

        wave1_radius = (t / 0.25) * 4.5 if beat1_active else 0.0
        wave2_radius = ((t - 0.30) / 0.65) * 15.0 if beat2_active else 0.0

        for key in ctx.keys:
            samples = sample_key_samples(key)
            acc_intensity = 0.0

            for sx, sy, weight in samples:
                dist = math.hypot(sx - self.cx, sy - self.cy)
                sample_int = 0.0

                # 1. Stroke 1: Sharp localized atrial pulse (center keys F, G, H, J)
                if beat1_active:
                    dist_to_wave1 = abs(dist - wave1_radius)
                    if dist_to_wave1 < 1.4:
                        int1 = (1.0 - dist_to_wave1 / 1.4) ** 1.5 * (1.0 - t / 0.25)
                        sample_int += int1 * 0.75

                # 2. Stroke 2: Massive systemic ventricular surge washing across deck
                if beat2_active:
                    p2 = (t - 0.30) / 0.65
                    dist_to_wave2 = abs(dist - wave2_radius)
                    if dist_to_wave2 < 2.5:
                        int2 = (1.0 - dist_to_wave2 / 2.5) ** 1.3 * (1.0 - p2)
                        sample_int += int2 * 1.1

                    # Core combustion glow during ventricular contraction
                    core_glow = math.exp(-((dist / 3.0) ** 2)) * ((1.0 - p2) ** 2.0)
                    sample_int += core_glow * 0.6

                # 3. Resting Diastolic Exhalation (soft ambient breathing)
                ambient = 0.06 + 0.03 * math.sin(t * (2.0 * math.pi / self.cycle_duration))
                sample_int = max(ambient, sample_int)

                acc_intensity += sample_int * weight

            c = self.palette.sample(min(1.0, acc_intensity))
            canvas.set_pixel(key.slot, c)
