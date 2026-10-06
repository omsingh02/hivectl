"""
Rain: drops hit random keys and send out faint rings over a dark blue background.
"""
import math
import random
from typing import List, Dict, Any
from kreo import Effect, EffectContext, Layout, Color, GradientPalette
from kreo.math import sample_key_samples

class RainEffect(Effect):
    name = "rain"
    title = "Rain"
    cycle_duration = 10.0
    default_fps = 40

    def setup(self, layout: Layout):
        self.keys_list = layout.keys
        self.droplets: List[Dict[str, Any]] = []
        self.last_drop_time = 0.0

        # Water ripple palette (Midnight abyss -> Deep marine -> Aqua cyan -> White glint)
        self.palette = GradientPalette([
            (0.00, Color.from_hex("#010914")),  # Deep nocturnal pool
            (0.25, Color.from_hex("#031D38")),  # Marine blue
            (0.55, Color.from_hex("#0088CC")),  # Liquid body
            (0.75, Color.from_hex("#00F0FF")),  # Radiant crest cyan
            (0.90, Color.from_hex("#80FFFF")),  # Seafoam shimmer
            (1.00, Color.from_hex("#FFFFFF")),  # White impact glint
        ])

    def render(self, ctx: EffectContext):
        t = ctx.time
        canvas = ctx.canvas

        # Periodically spawn new raindrops on random physical keys
        # Average 1 droplet every 0.35 - 0.5 seconds
        if t - self.last_drop_time > 0.38:
            target_key = random.choice(self.keys_list)
            self.droplets.append({
                "x": target_key.cx,
                "y": target_key.cy,
                "start_time": t,
                "max_radius": random.uniform(3.0, 4.5),
                "speed": random.uniform(3.2, 4.2),
                "lifespan": 0.85
            })
            self.last_drop_time = t

        # Prune expired droplets
        self.droplets = [d for d in self.droplets if (t - d["start_time"]) < d["lifespan"]]

        for key in ctx.keys:
            samples = sample_key_samples(key)
            acc_intensity = 0.0

            for sx, sy, weight in samples:
                sample_int = 0.0

                for d in self.droplets:
                    age = t - d["start_time"]
                    if age < 0.0:
                        continue
                    age_norm = age / d["lifespan"]  # 0.0 to 1.0

                    current_radius = age * d["speed"]
                    dist = math.hypot(sx - d["x"], sy - d["y"])

                    # 1. Initial Impact Splash (age < 0.12s, directly on center key)
                    if age < 0.12 and dist < 0.8:
                        splash_p = 1.0 - (age / 0.12)
                        sample_int += splash_p * 1.2

                    # 2. Expanding Concentric Circular Crest
                    crest_dist = abs(dist - current_radius)
                    thickness = 0.55 + age_norm * 0.4
                    if crest_dist < thickness:
                        wave_height = 1.0 - (crest_dist / thickness)
                        # Wave attenuates as it expands outward
                        wave_energy = (wave_height ** 1.8) * (1.0 - age_norm)
                        sample_int += wave_energy * 0.95

                acc_intensity += sample_int * weight

            # Base ambient deep water level
            total_int = min(1.0, max(0.06, acc_intensity))
            c = self.palette.sample(total_int)
            canvas.set_pixel(key.slot, c)
