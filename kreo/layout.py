"""
Physical layout of the Kreo Hive 98: key positions (in key units) and matrix slots.
"""
from typing import Dict, List, Optional, Union

# (name, matrix slot, x, y, width, height, category). Slots match the firmware keymap
# (slot = column * 8 + row); FN is the layer key at slot 85.
LAYOUT_HIVE98 = [
    # Row 0: Esc, F-keys, top-right cluster
    ('ESC', 0, 0.0, 0.0, 1.0, 1.0, 'func'),
    ('F1', 8, 1.75, 0.0, 1.0, 1.0, 'func'),
    ('F2', 16, 2.75, 0.0, 1.0, 1.0, 'func'),
    ('F3', 24, 3.75, 0.0, 1.0, 1.0, 'func'),
    ('F4', 32, 4.75, 0.0, 1.0, 1.0, 'func'),
    ('F5', 40, 6.25, 0.0, 1.0, 1.0, 'func'),
    ('F6', 48, 7.25, 0.0, 1.0, 1.0, 'func'),
    ('F7', 56, 8.25, 0.0, 1.0, 1.0, 'func'),
    ('F8', 64, 9.25, 0.0, 1.0, 1.0, 'func'),
    ('F9', 72, 10.75, 0.0, 1.0, 1.0, 'func'),
    ('F10', 80, 11.75, 0.0, 1.0, 1.0, 'func'),
    ('F11', 88, 12.75, 0.0, 1.0, 1.0, 'func'),
    ('F12', 96, 13.75, 0.0, 1.0, 1.0, 'func'),
    ('PRINTSCREEN', 123, 15.25, 0.0, 1.0, 1.0, 'nav'),
    ('DELETE', 104, 16.25, 0.0, 1.0, 1.0, 'nav'),
    ('PAGEUP', 122, 17.25, 0.0, 1.0, 1.0, 'nav'),
    ('PAGEDOWN', 115, 18.25, 0.0, 1.0, 1.0, 'nav'),

    # Row 1: number row, numpad top
    ('GRAVE', 1, 0.0, 1.0, 1.0, 1.0, 'alpha'),
    ('1', 9, 1.0, 1.0, 1.0, 1.0, 'alpha'),
    ('2', 17, 2.0, 1.0, 1.0, 1.0, 'alpha'),
    ('3', 25, 3.0, 1.0, 1.0, 1.0, 'alpha'),
    ('4', 33, 4.0, 1.0, 1.0, 1.0, 'alpha'),
    ('5', 41, 5.0, 1.0, 1.0, 1.0, 'alpha'),
    ('6', 49, 6.0, 1.0, 1.0, 1.0, 'alpha'),
    ('7', 57, 7.0, 1.0, 1.0, 1.0, 'alpha'),
    ('8', 65, 8.0, 1.0, 1.0, 1.0, 'alpha'),
    ('9', 73, 9.0, 1.0, 1.0, 1.0, 'alpha'),
    ('0', 81, 10.0, 1.0, 1.0, 1.0, 'alpha'),
    ('MINUS', 89, 11.0, 1.0, 1.0, 1.0, 'alpha'),
    ('EQUAL', 97, 12.0, 1.0, 1.0, 1.0, 'alpha'),
    ('BACKSPACE', 105, 13.0, 1.0, 2.0, 1.0, 'mod'),
    ('NUMLOCK', 6, 15.25, 1.0, 1.0, 1.0, 'numpad'),
    ('KP_DIVIDE', 14, 16.25, 1.0, 1.0, 1.0, 'numpad'),
    ('KP_MULTIPLY', 22, 17.25, 1.0, 1.0, 1.0, 'numpad'),
    ('KP_SUBTRACT', 30, 18.25, 1.0, 1.0, 1.0, 'numpad'),

    # Row 2: QWERTY row
    ('TAB', 2, 0.0, 2.0, 1.5, 1.0, 'mod'),
    ('Q', 10, 1.5, 2.0, 1.0, 1.0, 'alpha'),
    ('W', 18, 2.5, 2.0, 1.0, 1.0, 'alpha'),
    ('E', 26, 3.5, 2.0, 1.0, 1.0, 'alpha'),
    ('R', 34, 4.5, 2.0, 1.0, 1.0, 'alpha'),
    ('T', 42, 5.5, 2.0, 1.0, 1.0, 'alpha'),
    ('Y', 50, 6.5, 2.0, 1.0, 1.0, 'alpha'),
    ('U', 58, 7.5, 2.0, 1.0, 1.0, 'alpha'),
    ('I', 66, 8.5, 2.0, 1.0, 1.0, 'alpha'),
    ('O', 74, 9.5, 2.0, 1.0, 1.0, 'alpha'),
    ('P', 82, 10.5, 2.0, 1.0, 1.0, 'alpha'),
    ('LBRACKET', 90, 11.5, 2.0, 1.0, 1.0, 'alpha'),
    ('RBRACKET', 98, 12.5, 2.0, 1.0, 1.0, 'alpha'),
    ('BACKSLASH', 106, 13.5, 2.0, 1.5, 1.0, 'alpha'),
    ('KP_7', 38, 15.25, 2.0, 1.0, 1.0, 'numpad'),
    ('KP_8', 46, 16.25, 2.0, 1.0, 1.0, 'numpad'),
    ('KP_9', 54, 17.25, 2.0, 1.0, 1.0, 'numpad'),
    ('KP_ADD', 86, 18.25, 2.0, 1.0, 2.0, 'numpad'),

    # Row 3: home row
    ('CAPSLOCK', 3, 0.0, 3.0, 1.75, 1.0, 'mod'),
    ('A', 11, 1.75, 3.0, 1.0, 1.0, 'alpha'),
    ('S', 19, 2.75, 3.0, 1.0, 1.0, 'alpha'),
    ('D', 27, 3.75, 3.0, 1.0, 1.0, 'alpha'),
    ('F', 35, 4.75, 3.0, 1.0, 1.0, 'alpha'),
    ('G', 43, 5.75, 3.0, 1.0, 1.0, 'alpha'),
    ('H', 51, 6.75, 3.0, 1.0, 1.0, 'alpha'),
    ('J', 59, 7.75, 3.0, 1.0, 1.0, 'alpha'),
    ('K', 67, 8.75, 3.0, 1.0, 1.0, 'alpha'),
    ('L', 75, 9.75, 3.0, 1.0, 1.0, 'alpha'),
    ('SEMICOLON', 83, 10.75, 3.0, 1.0, 1.0, 'alpha'),
    ('QUOTE', 91, 11.75, 3.0, 1.0, 1.0, 'alpha'),
    ('ENTER', 107, 12.75, 3.0, 2.25, 1.0, 'mod'),
    ('KP_4', 62, 15.25, 3.0, 1.0, 1.0, 'numpad'),
    ('KP_5', 70, 16.25, 3.0, 1.0, 1.0, 'numpad'),
    ('KP_6', 78, 17.25, 3.0, 1.0, 1.0, 'numpad'),

    # Row 4: shift row, up arrow
    ('LSHIFT', 4, 0.0, 4.0, 2.25, 1.0, 'mod'),
    ('Z', 20, 2.25, 4.0, 1.0, 1.0, 'alpha'),
    ('X', 28, 3.25, 4.0, 1.0, 1.0, 'alpha'),
    ('C', 36, 4.25, 4.0, 1.0, 1.0, 'alpha'),
    ('V', 44, 5.25, 4.0, 1.0, 1.0, 'alpha'),
    ('B', 52, 6.25, 4.0, 1.0, 1.0, 'alpha'),
    ('N', 60, 7.25, 4.0, 1.0, 1.0, 'alpha'),
    ('M', 68, 8.25, 4.0, 1.0, 1.0, 'alpha'),
    ('COMMA', 76, 9.25, 4.0, 1.0, 1.0, 'alpha'),
    ('DOT', 84, 10.25, 4.0, 1.0, 1.0, 'alpha'),
    ('SLASH', 92, 11.25, 4.0, 1.0, 1.0, 'alpha'),
    ('RSHIFT', 108, 12.25, 4.0, 1.75, 1.0, 'mod'),
    ('UP', 116, 14.15, 4.0, 1.0, 1.0, 'arrow'),
    ('KP_1', 124, 15.25, 4.0, 1.0, 1.0, 'numpad'),
    ('KP_2', 94, 16.25, 4.0, 1.0, 1.0, 'numpad'),
    ('KP_3', 102, 17.25, 4.0, 1.0, 1.0, 'numpad'),
    ('KP_ENTER', 126, 18.25, 4.0, 1.0, 2.0, 'numpad'),

    # Row 5: bottom row, arrows
    ('LCTRL', 5, 0.0, 5.0, 1.25, 1.0, 'mod'),
    ('LGUI', 13, 1.25, 5.0, 1.25, 1.0, 'mod'),
    ('LALT', 21, 2.5, 5.0, 1.25, 1.0, 'mod'),
    ('SPACE', 45, 3.75, 5.0, 6.25, 1.0, 'mod'),
    ('RALT', 77, 10.0, 5.0, 1.0, 1.0, 'mod'),
    ('FN', 85, 11.0, 5.0, 1.0, 1.0, 'mod'),
    ('RCTRL', 101, 12.0, 5.0, 1.0, 1.0, 'mod'),
    ('LEFT', 109, 13.1, 5.0, 1.0, 1.0, 'arrow'),
    ('DOWN', 117, 14.15, 5.0, 1.0, 1.0, 'arrow'),
    ('RIGHT', 125, 15.2, 5.0, 1.0, 1.0, 'arrow'),
    ('KP_0', 110, 16.25, 5.0, 1.0, 1.0, 'numpad'),
    ('KP_DECIMAL', 118, 17.25, 5.0, 1.0, 1.0, 'numpad'),
]

ALIASES = {
    "BKSP": "BACKSPACE", "RETURN": "ENTER", "RET": "ENTER",
    "WIN": "LGUI", "SUPER": "LGUI", "CTRL": "LCTRL", "ALT": "LALT", "SHIFT": "LSHIFT",
    "DEL": "DELETE", "PRT": "PRINTSCREEN", "PRTSC": "PRINTSCREEN",
    "PGUP": "PAGEUP", "PGDN": "PAGEDOWN", "CAPS": "CAPSLOCK", "NUM": "NUMLOCK",
    "KP0": "KP_0", "KP1": "KP_1", "KP2": "KP_2", "KP3": "KP_3", "KP4": "KP_4",
    "KP5": "KP_5", "KP6": "KP_6", "KP7": "KP_7", "KP8": "KP_8", "KP9": "KP_9",
    "KP_DOT": "KP_DECIMAL", "KP_PLUS": "KP_ADD", "KP_MINUS": "KP_SUBTRACT",
    "`": "GRAVE", "~": "GRAVE", "-": "MINUS", "=": "EQUAL", "[": "LBRACKET", "]": "RBRACKET",
    "\\": "BACKSLASH", ";": "SEMICOLON", "'": "QUOTE", ",": "COMMA", ".": "DOT", "/": "SLASH",
}

ZONES = {
    "wasd": lambda k: k.name in ("W", "A", "S", "D"),
    "arrows": lambda k: k.category == "arrow",
    "fkeys": lambda k: k.category == "func" and k.name != "ESC",
    "numpad": lambda k: k.category == "numpad",
    "nav": lambda k: k.category == "nav",
    "alpha": lambda k: k.category == "alpha",
    "mod": lambda k: k.category == "mod",
    "home": lambda k: k.name in ("A", "S", "D", "F", "G", "H", "J", "K", "L", "SEMICOLON", "QUOTE"),
}


class Key:
    __slots__ = ("name", "slot", "x", "y", "w", "h", "cx", "cy", "category")

    def __init__(self, name: str, slot: int, x: float, y: float, w: float, h: float, category: str):
        self.name, self.slot, self.category = name, slot, category
        self.x, self.y, self.w, self.h = x, y, w, h
        self.cx, self.cy = x + w / 2.0, y + h / 2.0

    def __repr__(self) -> str:
        return f"<Key {self.name} slot={self.slot}>"


class Layout:
    def __init__(self, raw=LAYOUT_HIVE98):
        self.keys = [Key(*item) for item in raw]
        self.by_slot: Dict[int, Key] = {k.slot: k for k in self.keys}
        self.by_name: Dict[str, Key] = {k.name: k for k in self.keys}
        for alias, target in ALIASES.items():
            self.by_name.setdefault(alias, self.by_name[target])
        self.width = max(k.x + k.w for k in self.keys)    # 19.25
        self.height = max(k.y + k.h for k in self.keys)   # 6.0
        self.cx, self.cy = 7.0, 2.8                       # middle of the typing area

    def get(self, name_or_slot: Union[str, int]) -> Optional[Key]:
        if isinstance(name_or_slot, int):
            return self.by_slot.get(name_or_slot)
        return self.by_name.get(str(name_or_slot).strip().upper())

    def get_zone(self, zone: str) -> List[Key]:
        test = ZONES.get(zone.strip().lower())
        return [k for k in self.keys if test(k)] if test else []


GLOBAL_LAYOUT = Layout()
