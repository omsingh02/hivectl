"""
Linux driver, effect engine and tools for the Kreo Hive 98 keyboard (EVision 320F:5055).
"""
__version__ = "3.0.0"

from kreo.color import Color
from kreo.palette import GradientPalette
from kreo.layout import Key, Layout, GLOBAL_LAYOUT
from kreo.canvas import Canvas
from kreo.sdk import Effect, EffectContext

__all__ = ["Color", "GradientPalette", "Key", "Layout", "GLOBAL_LAYOUT", "Canvas", "Effect", "EffectContext"]
