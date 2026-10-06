"""
Keystroke monitor reading the keyboard's own hidraw nodes (no root, no focus needed).

Interface 0 sends standard 8-byte boot reports (modifier bits + up to 6 keys);
interface 1 report 1 is the NKRO bitmap used when n-key rollover is active.
"""
import os
import time
from typing import Dict, List, NamedTuple, Set

from kreo.constants import KEYBOARD_INTERFACE, VENDOR_INTERFACE, NKRO_REPORT_ID
from kreo.device import DeviceNotFound, find_hidraw
from kreo.layout import GLOBAL_LAYOUT, Key, Layout

# USB HID keyboard-page usages for the keys on the board
USAGES: Dict[str, int] = {chr(ord("A") + i): 0x04 + i for i in range(26)}
USAGES.update({str(n % 10): 0x1E + n - 1 for n in range(1, 11)})
USAGES.update({f"F{n}": 0x39 + n for n in range(1, 13)})
USAGES.update({f"KP_{n}": 0x58 + n for n in range(1, 10)})
USAGES.update({
    "ENTER": 0x28, "ESC": 0x29, "BACKSPACE": 0x2A, "TAB": 0x2B, "SPACE": 0x2C, "MINUS": 0x2D,
    "EQUAL": 0x2E, "LBRACKET": 0x2F, "RBRACKET": 0x30, "BACKSLASH": 0x31, "SEMICOLON": 0x33,
    "QUOTE": 0x34, "GRAVE": 0x35, "COMMA": 0x36, "DOT": 0x37, "SLASH": 0x38, "CAPSLOCK": 0x39,
    "PRINTSCREEN": 0x46, "PAGEUP": 0x4B, "DELETE": 0x4C, "PAGEDOWN": 0x4E, "RIGHT": 0x4F,
    "LEFT": 0x50, "DOWN": 0x51, "UP": 0x52, "NUMLOCK": 0x53, "KP_DIVIDE": 0x54,
    "KP_MULTIPLY": 0x55, "KP_SUBTRACT": 0x56, "KP_ADD": 0x57, "KP_ENTER": 0x58, "KP_0": 0x62,
    "KP_DECIMAL": 0x63,
})
MODIFIER_BITS = {0x01: "LCTRL", 0x02: "LSHIFT", 0x04: "LALT", 0x08: "LGUI",
                 0x10: "RCTRL", 0x20: "RSHIFT", 0x40: "RALT"}


class KeyEvent(NamedTuple):
    key: Key
    is_down: bool
    timestamp: float


class InputMonitor:
    def __init__(self, layout: Layout = GLOBAL_LAYOUT):
        self.usage_to_key = {USAGES[k.name]: k for k in layout.keys if k.name in USAGES}
        self.mod_to_key = {bit: layout.get(name) for bit, name in MODIFIER_BITS.items()}
        self.mods = 0
        self.boot_usages: Set[int] = set()
        self.nkro_usages: Set[int] = set()
        self.held_keys: Set[Key] = set()
        self.fds: Dict[int, int] = {}
        for iface in (KEYBOARD_INTERFACE, VENDOR_INTERFACE):
            try:
                self.fds[iface] = os.open(find_hidraw(iface), os.O_RDONLY | os.O_NONBLOCK)
            except (DeviceNotFound, OSError):
                pass

    @property
    def available(self) -> bool:
        return bool(self.fds)

    def close(self):
        for fd in self.fds.values():
            os.close(fd)
        self.fds.clear()

    def poll(self) -> List[KeyEvent]:
        """Returns key down/up events since the previous call."""
        events: List[KeyEvent] = []
        for iface, fd in list(self.fds.items()):
            while True:
                try:
                    pkt = os.read(fd, 64)
                except BlockingIOError:
                    break
                except OSError:  # unplugged
                    os.close(fd)
                    del self.fds[iface]
                    break
                if iface == KEYBOARD_INTERFACE and len(pkt) >= 8:
                    self.mods = pkt[0]
                    if pkt[2] != 0x01:  # 0x01 = rollover error: keys unknown, keep the last set
                        self.boot_usages = {u for u in pkt[2:8] if u > 3}
                elif iface == VENDOR_INTERFACE and pkt and pkt[0] == NKRO_REPORT_ID:
                    self.nkro_usages = {0x04 + i * 8 + bit for i, byte in enumerate(pkt[1:])
                                        for bit in range(8) if byte >> bit & 1}
                else:
                    continue
                self._diff(events)
        return events

    def _diff(self, events: List[KeyEvent]):
        held = {key for bit, key in self.mod_to_key.items() if self.mods & bit}
        for usage in self.boot_usages | self.nkro_usages:
            key = self.usage_to_key.get(usage)
            if key:
                held.add(key)
        now = time.monotonic()
        events += [KeyEvent(k, True, now) for k in held - self.held_keys]
        events += [KeyEvent(k, False, now) for k in self.held_keys - held]
        self.held_keys = held
