"""
Supernova: 14-second story centered on the typing area - a pulsing star, a collapsing
blue vortex, a moment of darkness, a white blast wave across the board, then a fading nebula.
"""
import math
from kreo import Effect, EffectContext, Layout, Color, GradientPalette
from kreo.math import fbm3d, sample_key_samples

class SupernovaEffect(Effect):
    name = "supernova"
    title = "Supernova"
    cycle_duration = 14.0
    default_fps = 40

    def setup(self, layout: Layout):
        self.center_x = layout.cx  # Typing cluster center (7.0, 2.8)
        self.center_y = layout.cy
        self.max_reach = math.hypot(layout.width - self.center_x, layout.height - self.center_y) + 1.0

        # Planckian thermonuclear color ramp
        self.core_palette = GradientPalette([
            (0.00, Color.from_hex("#000000")),  # Interstellar cold void
            (0.20, Color.from_hex("#4A0008")),  # Dark red coronal rim
            (0.45, Color.from_hex("#D93800")),  # Radiant thermonuclear amber
            (0.70, Color.from_hex("#FFB700")),  # High-energy plasma yellow
            (0.88, Color.from_hex("#FFF0A6")),  # Incandescent white-yellow
            (1.00, Color.from_hex("#FFFFFF")),  # Pure relativistic singularity
        ])

        # Relativistic blueshift infall palette
        self.infall_palette = GradientPalette([
            (0.00, Color.from_hex("#000000")),
            (0.30, Color.from_hex("#05163D")),  # Deep space void
            (0.55, Color.from_hex("#0088FF")),  # Accelerated hydrogen emission
            (0.78, Color.from_hex("#00F0FF")),  # Relativistic blueshift cyan
            (0.92, Color.from_hex("#8A2BE2")),  # Extreme gravitational violet
            (1.00, Color.from_hex("#FFFFFF")),  # Event horizon boundary
        ])

        # Interstellar nebula remnant palette
        self.nebula_palette = GradientPalette([
            (0.00, Color.from_hex("#010208")),  # Cosmic void
            (0.25, Color.from_hex("#120024")),  # Deep ultraviolet gas
            (0.50, Color.from_hex("#8B0066")),  # Ionized nitrogen / magenta
            (0.72, Color.from_hex("#3A0088")),  # Electric synchrotron purple
            (0.88, Color.from_hex("#00B4D8")),  # Ethereal oxygen-III cyan
            (1.00, Color.from_hex("#E0FFFF")),  # Proto-star ignition point
        ])

    def render(self, ctx: EffectContext):
        t = ctx.cycle_time
        canvas = ctx.canvas
        cx = self.center_x
        cy = self.center_y

        # =====================================================================
        # ACT 1: STELLAR EQUILIBRIUM & CORONAL ERUPTIONS (0.0s -> 3.5s)
        # =====================================================================
        if t < 3.5:
            p = t / 3.5
            ctx.set_status("1/5 star")
            pulse = 0.3 * math.sin(t * 4.5)
            core_radius = 2.2 + pulse

            for key in ctx.keys:
                samples = sample_key_samples(key)
                acc_color = Color(0, 0, 0)

                for sx, sy, weight in samples:
                    dist = math.hypot(sx - cx, sy - cy)
                    angle = math.atan2(sy - cy, sx - cx)

                    # Continuous 3D turbulent solar flares
                    flare_noise = fbm3d(math.cos(angle) * 1.5, math.sin(angle) * 1.5, t * 0.8, octaves=3)
                    flares = max(0.0, flare_noise - 0.45) * 2.0 * max(0.0, 1.0 - dist / 6.0)

                    # Hydrostatic core Gaussian falloff
                    core_intensity = math.exp(-((dist / core_radius) ** 2))
                    total_intensity = min(1.0, core_intensity + flares * 0.45)

                    c = self.core_palette.sample(total_intensity) * (0.85 + 0.15 * math.sin(t * 6.0 + dist))
                    acc_color = acc_color + c * weight

                canvas.set_pixel(key.slot, acc_color)

        # =====================================================================
        # ACT 2: GRAVITATIONAL INFALL & ACCRETION VORTEX (3.5s -> 6.5s)
        # =====================================================================
        elif t < 6.5:
            p = (t - 3.5) / 3.0
            ctx.set_status("2/5 collapse")
            infall_radius = self.max_reach * (1.0 - p) + 0.4
            rot_speed = 5.0 + (p ** 2.5) * 20.0
            singularity_r = 1.8 * (1.0 - p * 0.75)

            for key in ctx.keys:
                samples = sample_key_samples(key)
                acc_color = Color(0, 0, 0)

                for sx, sy, weight in samples:
                    dist = math.hypot(sx - cx, sy - cy)
                    angle = math.atan2(sy - cy, sx - cx)

                    # Logarithmic spiral accretion ribbons
                    spiral = math.sin(angle * 3.0 + dist * 1.2 - t * rot_speed)
                    spiral_front = max(0.0, 1.0 - abs(dist - infall_radius) / 2.8)
                    spiral_val = max(0.0, spiral) * spiral_front

                    # Gravitational core compression
                    core_val = math.exp(-((dist / max(0.2, singularity_r)) ** 2)) * (1.0 + p * 2.0)
                    total_val = min(1.0, spiral_val * 0.8 + core_val)

                    c = self.infall_palette.sample(total_val)
                    acc_color = acc_color + c * weight

                canvas.set_pixel(key.slot, acc_color)

        # =====================================================================
        # ACT 3: EVENT HORIZON BLACKOUT / THE VOID (6.5s -> 7.1s)
        # =====================================================================
        elif t < 7.1:
            ctx.set_status("3/5 darkness")
            # Absolute black silence
            canvas.clear()

        # =====================================================================
        # ACT 4: HYPERNOVA DETONATION & BLAST WAVE (7.1s -> 9.0s)
        # =====================================================================
        elif t < 9.0:
            p = (t - 7.1) / 1.9
            ctx.set_status("4/5 blast")
            blast_radius = (p ** 0.75) * (self.max_reach + 2.0)
            thickness = 1.4 + p * 2.5

            for key in ctx.keys:
                samples = sample_key_samples(key)
                acc_color = Color(0, 0, 0)

                for sx, sy, weight in samples:
                    dist = math.hypot(sx - cx, sy - cy)

                    # Relativistic shockwave leading edge
                    dist_to_wave = abs(dist - blast_radius)
                    shock_ring = max(0.0, 1.0 - dist_to_wave / thickness)
                    shock = shock_ring ** 1.6

                    # Incandescent fireball core wake
                    fireball = max(0.0, 1.0 - dist / max(0.1, blast_radius)) * ((1.0 - p) ** 1.8)

                    r = min(1.0, shock * 1.0 + fireball * 0.95)
                    g = min(1.0, (shock ** 1.4) * 0.9 + fireball * 0.45)
                    b = min(1.0, shock * 1.0 + fireball * 0.9)

                    # Leading shockwave is brilliant blinding white
                    if shock > 0.8:
                        r, g, b = 1.0, 1.0, 1.0

                    acc_color = acc_color + Color(r, g, b) * weight

                canvas.set_pixel(key.slot, acc_color)

        # =====================================================================
        # ACT 5: INTERSTELLAR CRAB NEBULA & STELLAR RE-IGNITION (9.0s -> 14.0s)
        # =====================================================================
        else:
            p = (t - 9.0) / 5.0
            ctx.set_status("5/5 nebula")
            decay = max(0.0, 1.0 - (p ** 1.1))

            for key in ctx.keys:
                samples = sample_key_samples(key)
                acc_color = Color(0, 0, 0)

                for sx, sy, weight in samples:
                    dist = math.hypot(sx - cx, sy - cy)
                    angle = math.atan2(sy - cy, sx - cx)

                    # Multi-octave 3D continuous gas filaments
                    gas_turb = fbm3d(sx * 0.2, sy * 0.3, t * 0.25, octaves=3)
                    gas_density = (gas_turb ** 1.3) * decay * max(0.0, 1.0 - dist / (self.max_reach + 1.0))

                    c = self.nebula_palette.sample(min(1.0, gas_density * 1.5))

                    # Re-birth of core at end of cycle
                    if p > 0.65:
                        birth_p = (p - 0.65) / 0.35
                        core_revive = math.exp(-((dist / 2.0) ** 2)) * birth_p
                        c = c + Color(1.0, 0.6, 0.2) * core_revive

                    acc_color = acc_color + c * weight

                canvas.set_pixel(key.slot, acc_color)
