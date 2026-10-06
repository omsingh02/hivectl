"""
Multi-stop linear color gradient.
"""
from typing import List, Tuple

from kreo.color import Color


class GradientPalette:
    def __init__(self, stops: List[Tuple[float, Color]]):
        self.stops = sorted(stops, key=lambda s: s[0])

    def sample(self, t: float) -> Color:
        stops = self.stops
        if t <= stops[0][0]:
            return stops[0][1]
        for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
            if t <= t1:
                return c0.lerp(c1, (t - t0) / max(1e-6, t1 - t0))
        return stops[-1][1]
