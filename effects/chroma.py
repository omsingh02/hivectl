"""
Chroma: diagonal cyan/violet/magenta/amber gradient sweeping across the board.
"""
from kreo import Effect, EffectContext, Layout, Color, GradientPalette
from kreo.math import sample_key_samples

class ChromaEffect(Effect):
    name = "chroma"
    title = "Chroma wave"
    cycle_duration = 8.0
    default_fps = 40

    def setup(self, layout: Layout):
        # Curated Cyberpunk Chroma palette (Cyan -> Violet -> Magenta -> Amber -> Cyan)
        self.palette = GradientPalette([
            (0.00, Color.from_hex("#00F0FF")),  # Electric cyber cyan
            (0.28, Color.from_hex("#6A00F4")),  # Royal neon violet
            (0.52, Color.from_hex("#FF007F")),  # Laser hot magenta
            (0.76, Color.from_hex("#FF5400")),  # High-energy sunset amber
            (1.00, Color.from_hex("#00F0FF")),  # Electric cyber cyan
        ])

    def render(self, ctx: EffectContext):
        t = ctx.time
        canvas = ctx.canvas

        # Wavelength and wave speed
        wavelength = 12.0
        speed = 2.4

        for key in ctx.keys:
            samples = sample_key_samples(key)
            acc_color = Color(0, 0, 0)

            for sx, sy, weight in samples:
                # 45-degree diagonal projection coordinate
                # (1 unit in X and 1.3 units in Y for balanced diagonal flow)
                diag_pos = (sx + sy * 1.3) / wavelength
                phase = (diag_pos - (t * speed) / wavelength) % 1.0

                c = self.palette.sample(phase)
                acc_color = acc_color + c * weight

            canvas.set_pixel(key.slot, acc_color)
