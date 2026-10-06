"""
RGBA color with float channels, color parsing, and pywal theme lookup.
"""
import json
import re
from pathlib import Path
from typing import Tuple

from hivectl.constants import NAMED_COLORS


class Color:
    """RGBA color with channels in 0.0-1.0. Use Color.rgb() for 0-255 values."""
    __slots__ = ("r", "g", "b", "a")

    def __init__(self, r: float = 0.0, g: float = 0.0, b: float = 0.0, a: float = 1.0):
        self.r = 0.0 if r < 0.0 else 1.0 if r > 1.0 else float(r)
        self.g = 0.0 if g < 0.0 else 1.0 if g > 1.0 else float(g)
        self.b = 0.0 if b < 0.0 else 1.0 if b > 1.0 else float(b)
        self.a = 0.0 if a < 0.0 else 1.0 if a > 1.0 else float(a)

    @classmethod
    def rgb(cls, r: int, g: int, b: int, a: float = 1.0) -> "Color":
        return cls(r / 255.0, g / 255.0, b / 255.0, a)

    @classmethod
    def from_hex(cls, hex_str: str, a: float = 1.0) -> "Color":
        return cls.rgb(*parse_color(hex_str), a)

    @classmethod
    def from_hsv(cls, h: float, s: float, v: float, a: float = 1.0) -> "Color":
        """h, s, v in 0.0-1.0 (h wraps)."""
        h = (h % 1.0) * 6.0
        i = int(h)
        f = h - i
        p, q, t = v * (1.0 - s), v * (1.0 - s * f), v * (1.0 - s * (1.0 - f))
        r, g, b = ((v, t, p), (q, v, p), (p, v, t), (p, q, v), (t, p, v), (v, p, q))[i % 6]
        return cls(r, g, b, a)

    def to_tuple(self) -> Tuple[int, int, int]:
        return int(self.r * 255 + 0.5), int(self.g * 255 + 0.5), int(self.b * 255 + 0.5)

    def to_hex(self) -> str:
        return "#%02X%02X%02X" % self.to_tuple()

    def __add__(self, other: "Color") -> "Color":
        return Color(self.r + other.r, self.g + other.g, self.b + other.b, self.a + other.a)

    def __mul__(self, scalar: float) -> "Color":
        """Scales brightness; alpha is unchanged."""
        return Color(self.r * scalar, self.g * scalar, self.b * scalar, self.a)

    __rmul__ = __mul__

    def lerp(self, other: "Color", t: float) -> "Color":
        return Color(self.r + (other.r - self.r) * t,
                     self.g + (other.g - self.g) * t,
                     self.b + (other.b - self.b) * t,
                     self.a + (other.a - self.a) * t)

    def over(self, dst: "Color") -> "Color":
        """Alpha-composites this color over dst and returns an opaque result."""
        a = self.a
        return Color(self.r * a + dst.r * (1.0 - a),
                     self.g * a + dst.g * (1.0 - a),
                     self.b * a + dst.b * (1.0 - a))

    def __repr__(self) -> str:
        return f"Color({self.to_hex()}, a={self.a:.2f})"


BLACK = Color(0.0, 0.0, 0.0)


def parse_color(color_str: str) -> Tuple[int, int, int]:
    """Parses '#RRGGBB', '#RGB' or a named color into 0-255 (r, g, b)."""
    s = color_str.strip().lower()
    if s in NAMED_COLORS:
        return NAMED_COLORS[s]
    s = s.lstrip("#")
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    if re.fullmatch(r"[0-9a-f]{6}", s):
        return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)
    raise ValueError(f"invalid color '{color_str}' (use #RRGGBB or one of: {', '.join(NAMED_COLORS)})")


def theme_color() -> Tuple[int, int, int, str]:
    """Accent color (color2) from the pywal cache, or a fallback green."""
    try:
        data = json.loads((Path.home() / ".cache/wal/colors.json").read_text(encoding="utf-8"))
        hex_str = data["colors"]["color2"]
        return (*parse_color(hex_str), hex_str.upper())
    except (OSError, KeyError, ValueError):
        return 182, 216, 105, "#B6D869"
