"""
Per-slot framebuffer, serialized to the 384-byte frame the keyboard expects.
"""
from typing import List, Optional, Union

from hivectl.color import Color, BLACK
from hivectl.constants import NUM_SLOTS, FRAME_SIZE
from hivectl.layout import Key, Layout, GLOBAL_LAYOUT


def _cie_lut() -> List[int]:
    """Maps perceived lightness (sRGB-like input) to linear LED drive (CIE 1931 L*)."""
    lut = []
    for i in range(256):
        l_star = i / 255.0 * 100.0
        y = l_star / 903.3 if l_star <= 8.0 else ((l_star + 16.0) / 116.0) ** 3
        lut.append(min(255, int(y * 255.0 + 0.5)))
    return lut


CIE_LUT = _cie_lut()


class Canvas:
    def __init__(self, layout: Layout = GLOBAL_LAYOUT):
        self.layout = layout
        self.pixels: List[Color] = [BLACK] * NUM_SLOTS

    def clear(self, color: Optional[Color] = None):
        self.pixels = [color or BLACK] * NUM_SLOTS

    def set_pixel(self, slot: int, color: Color):
        """Sets a slot; translucent colors are composited over what is already there."""
        if 0 <= slot < NUM_SLOTS:
            self.pixels[slot] = color if color.a >= 0.999 else color.over(self.pixels[slot])

    def set_key(self, key: Union[str, Key], color: Color):
        k = key if isinstance(key, Key) else self.layout.get(key)
        if k:
            self.set_pixel(k.slot, color)

    def fill_zone(self, zone: str, color: Color):
        for k in self.layout.get_zone(zone):
            self.set_pixel(k.slot, color)

    def to_frame(self, perceptual: bool = True) -> bytes:
        buf = bytearray(FRAME_SIZE)
        lut = CIE_LUT
        for slot, c in enumerate(self.pixels):
            r, g, b = c.to_tuple()
            i = slot * 3
            if perceptual:
                buf[i], buf[i + 1], buf[i + 2] = lut[r], lut[g], lut[b]
            else:
                buf[i], buf[i + 1], buf[i + 2] = r, g, b
        return bytes(buf)
