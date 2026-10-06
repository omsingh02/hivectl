"""
Protocol constants for the Kreo Hive 98 (EVision V2 controller, USB 320F:5055).

Everything here was checked against the keyboard: packet framing and command
echoes, the profile layout (compared with the untouched factory profiles 2 and
3), the 128-slot key matrix, and the per-key LED table.
"""
from pathlib import Path

VENDOR_ID = 0x320F
PRODUCT_ID = 0x5055
KEYBOARD_INTERFACE = 0   # boot keyboard reports
VENDOR_INTERFACE = 1     # report 1 = NKRO bitmap, report 4 = vendor commands
REPORT_ID = 0x04
NKRO_REPORT_ID = 0x01

# Packet: [report id, checksum lo, checksum hi, cmd, size, offset lo, offset hi, 0, data...]
PACKET_SIZE = 64
HEADER_SIZE = 8
CHUNK_SIZE = PACKET_SIZE - HEADER_SIZE  # 56 data bytes per packet

CMD_BEGIN_CONFIG = 0x01
CMD_END_CONFIG = 0x02
CMD_READ_CONFIG = 0x05
CMD_WRITE_CONFIG = 0x06
CMD_READ_KEYMAP = 0x07
CMD_READ_CUSTOM_LEDS = 0x0A
CMD_WRITE_CUSTOM_LEDS = 0x0B
CMD_SEND_FRAME = 0x12
CMD_END_FRAME = 0x13

NUM_SLOTS = 128                  # key matrix: slot = column * 8 + row
FRAME_SIZE = NUM_SLOTS * 3       # RGB per slot, used by streaming and the custom LED table

# Config space: byte 0 = active profile, then three 64-byte profile blocks.
# The keymap is mapped right after (0xC0), so writes must stay below CONFIG_SIZE.
OFFSET_ACTIVE_PROFILE = 0x00
PROFILE_OFFSETS = (0x01, 0x41, 0x81)
CONFIG_SIZE = 0xC0

# Lighting fields at the start of a profile block. Only these are ever written;
# the rest of the block holds firmware settings this tool does not touch.
P_MODE, P_BRIGHTNESS, P_SPEED, P_DIRECTION, P_RAINBOW, P_RED, P_GREEN, P_BLUE = range(8)
LIGHTING_FIELDS = 8
MAX_BRIGHTNESS = 4
MAX_SPEED = 5

# Built-in hardware lighting modes: name -> (mode id, description)
LIGHTING_MODES = {
    "off":       (0x00, "Backlight off"),
    "wave":      (0x01, "Color wave"),
    "clouds":    (0x02, "Clouds fly"),
    "wheel":     (0x03, "Winding paths"),
    "spectrum":  (0x04, "Spectrum cycle"),
    "breathing": (0x05, "Breathing"),
    "static":    (0x06, "Static color"),
    "reactive":  (0x07, "Key reactive"),
    "ripple":    (0x08, "Ripple on keypress"),
    "stream":    (0x09, "Line reactive"),
    "stars":     (0x0A, "Starlight (fast)"),
    "flowers":   (0x0B, "Flowers blooming"),
    "swift":     (0x0C, "Vertical wave"),
    "hurricane": (0x0D, "Hurricane"),
    "cartoon":   (0x0E, "Accumulate"),
    "digital":   (0x0F, "Starlight (slow)"),
    "visor":     (0x10, "Visor"),
    "surmount":  (0x11, "Surmount"),
    "circle":    (0x12, "Rainbow circle"),
    "custom":    (0x14, "Per-key colors stored on the keyboard (hivectl custom)"),
}

NAMED_COLORS = {
    "red":     (255, 0, 0),
    "green":   (0, 255, 0),
    "blue":    (0, 0, 255),
    "cyan":    (68, 222, 245),
    "magenta": (255, 0, 255),
    "yellow":  (255, 255, 0),
    "orange":  (255, 128, 0),
    "purple":  (131, 131, 255),
    "pink":    (255, 51, 102),
    "lime":    (182, 216, 105),
    "mint":    (117, 252, 221),
    "white":   (255, 255, 255),
    "ice":     (172, 201, 234),
    "ruby":    (255, 30, 80),
    "amber":   (255, 160, 0),
    "black":   (0, 0, 0),
}

EFFECTS_DIR = Path.home() / ".config/hivectl/effects"
