"""
Hyprland HUD. While Super/Alt/Ctrl/Shift are held, the keys bound to that exact modifier
combination in Hyprland light up, colored by what they do (read live from `hyprctl binds`).
The number row shows workspaces (active / occupied) and the numpad shows CPU, RAM,
battery and volume gauges.
"""
import glob
import json
import os
import re
import shutil
import socket
import subprocess
import threading
from typing import Dict, List, Optional

from hivectl.color import Color
from hivectl.layout import Layout
from hivectl.sdk import Effect, EffectContext

# Hyprland modmask bits
SHIFT, CTRL, ALT, SUPER = 1, 4, 8, 64
MOD_KEYS = {"LSHIFT": SHIFT, "RSHIFT": SHIFT, "LCTRL": CTRL, "RCTRL": CTRL,
            "LALT": ALT, "RALT": ALT, "LGUI": SUPER}
MOD_NAMES = ((SUPER, "SUPER"), (CTRL, "CTRL"), (ALT, "ALT"), (SHIFT, "SHIFT"))

LAUNCH = Color.rgb(0, 240, 255)
WINDOW = Color.rgb(255, 175, 0)
MEDIA = Color.rgb(16, 217, 126)
SUBMAP = Color.rgb(168, 85, 247)
DANGER = Color.rgb(244, 63, 94)
OTHER = Color.rgb(226, 232, 240)
HELD = Color(1.0, 1.0, 1.0)
WS_ACTIVE = Color.rgb(0, 240, 255)
WS_OCCUPIED = Color.rgb(226, 232, 240) * 0.55
WS_EMPTY = Color.rgb(51, 65, 85)
GAUGE_OFF = Color.rgb(12, 16, 20)

DANGER_DISPATCHERS = {"killactive", "forcekillactive", "closewindow", "killwindow", "exit"}
WINDOW_DISPATCHERS = {
    "movefocus", "movewindow", "swapwindow", "resizeactive", "togglefloating", "setfloating",
    "settiled", "fullscreen", "fullscreenstate", "pin", "layoutmsg", "cyclenext", "swapnext",
    "bringactivetotop", "alterzorder", "pseudo", "togglesplit", "centerwindow", "focusmonitor",
    "focusurgentorlast", "focuscurrentorlast", "togglegroup", "changegroupactive",
    "moveintogroup", "moveoutofgroup", "movecurrentworkspacetomonitor", "swapactiveworkspaces",
}
WORKSPACE_DISPATCHERS = {"workspace", "movetoworkspace", "movetoworkspacesilent",
                         "focusworkspaceoncurrentmonitor", "togglespecialworkspace"}
MEDIA_HINT = re.compile(r"volume|media|playerctl|wpctl|pamixer|mpc\b|brightness|mute", re.I)

# xkb keysym (lowercase) -> layout key name, for names that differ
KEYSYMS = {
    "return": "ENTER", "kp_enter": "KP_ENTER", "backspace": "BACKSPACE", "tab": "TAB",
    "space": "SPACE", "escape": "ESC", "delete": "DELETE", "print": "PRINTSCREEN",
    "prior": "PAGEUP", "page_up": "PAGEUP", "next": "PAGEDOWN", "page_down": "PAGEDOWN",
    "left": "LEFT", "right": "RIGHT", "up": "UP", "down": "DOWN", "grave": "GRAVE",
    "minus": "MINUS", "equal": "EQUAL", "bracketleft": "LBRACKET", "bracketright": "RBRACKET",
    "backslash": "BACKSLASH", "semicolon": "SEMICOLON", "apostrophe": "QUOTE", "comma": "COMMA",
    "period": "DOT", "slash": "SLASH", "caps_lock": "CAPSLOCK", "num_lock": "NUMLOCK",
    "kp_add": "KP_ADD", "kp_subtract": "KP_SUBTRACT", "kp_multiply": "KP_MULTIPLY",
    "kp_divide": "KP_DIVIDE", "kp_decimal": "KP_DECIMAL", "kp_delete": "KP_DECIMAL",
    "kp_insert": "KP_0", "kp_end": "KP_1", "kp_down": "KP_2", "kp_next": "KP_3", "kp_left": "KP_4",
    "kp_begin": "KP_5", "kp_right": "KP_6", "kp_home": "KP_7", "kp_up": "KP_8", "kp_prior": "KP_9",
}
NUMBER_ROW = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"]   # workspaces 1..10

# Numpad gauge columns, bottom to top
GAUGES = {
    "cpu": ["KP_1", "KP_4", "KP_7", "NUMLOCK", "PRINTSCREEN"],
    "ram": ["KP_0", "KP_2", "KP_5", "KP_8", "KP_DIVIDE", "DELETE"],
    "bat": ["KP_DECIMAL", "KP_3", "KP_6", "KP_9", "KP_MULTIPLY", "PAGEUP"],
    "vol": ["KP_ENTER", "KP_ADD", "KP_SUBTRACT", "PAGEDOWN"],
}
CPU_COLORS = [Color.rgb(0, 185, 95), Color.rgb(0, 215, 140), Color.rgb(245, 180, 0),
              Color.rgb(255, 115, 15), Color.rgb(255, 35, 35)]


def keysym_to_key(name: str) -> Optional[str]:
    n = name.lower()
    if n in KEYSYMS:
        return KEYSYMS[n]
    if len(n) == 1 and n.isalnum():
        return n.upper()
    if re.fullmatch(r"f(?:[1-9]|1[0-2])|kp_[0-9]", n):
        return n.upper()
    return None


def bind_color(dispatcher: str, arg: str) -> Color:
    if dispatcher in DANGER_DISPATCHERS:
        return DANGER
    if dispatcher in WINDOW_DISPATCHERS or dispatcher in WORKSPACE_DISPATCHERS:
        return WINDOW
    if dispatcher == "submap":
        return SUBMAP
    if dispatcher in ("exec", "execr"):
        return MEDIA if MEDIA_HINT.search(arg) else LAUNCH
    return OTHER


class Hyprland:
    """Minimal client for the Hyprland request socket."""

    def __init__(self):
        self.path: Optional[str] = None

    def _find_socket(self) -> Optional[str]:
        runtime = os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
        sig = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE")
        if sig and os.path.exists(f"{runtime}/hypr/{sig}/.socket.sock"):
            return f"{runtime}/hypr/{sig}/.socket.sock"
        sockets = glob.glob(f"{runtime}/hypr/*/.socket.sock")
        return max(sockets, key=os.path.getmtime) if sockets else None

    def query(self, command: str):
        try:
            if not self.path or not os.path.exists(self.path):
                self.path = self._find_socket()
                if not self.path:
                    return None
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                s.connect(self.path)
                s.sendall(f"j/{command}".encode())
                chunks = []
                while True:
                    chunk = s.recv(65536)
                    if not chunk:
                        break
                    chunks.append(chunk)
            return json.loads(b"".join(chunks))
        except (OSError, ValueError):
            self.path = None
            return None


class SystemStats:
    """CPU / RAM / battery / volume, sampled in the HUD's background thread."""

    def __init__(self):
        self.cpu = self.ram = 0.0
        self.battery: Optional[float] = None
        self.charging = False
        self.volume: Optional[float] = None
        self.muted = False
        self._cpu_prev = None
        self._bat = sorted(glob.glob("/sys/class/power_supply/BAT*"))
        self._wpctl = shutil.which("wpctl")

    def update(self, with_volume: bool):
        with open("/proc/stat") as f:
            fields = [int(x) for x in f.readline().split()[1:]]
        idle, total = fields[3] + fields[4], sum(fields)
        if self._cpu_prev:
            d_total = total - self._cpu_prev[1]
            self.cpu = 100.0 * (1.0 - (idle - self._cpu_prev[0]) / d_total) if d_total else self.cpu
        self._cpu_prev = (idle, total)

        mem = {}
        with open("/proc/meminfo") as f:
            for line in f:
                key, value = line.split(":", 1)
                mem[key] = int(value.split()[0])
        self.ram = 100.0 * (1.0 - mem["MemAvailable"] / mem["MemTotal"])

        if self._bat:
            try:
                with open(f"{self._bat[0]}/capacity") as f:
                    self.battery = float(f.read())
                with open(f"{self._bat[0]}/status") as f:
                    self.charging = f.read().strip() == "Charging"
            except (OSError, ValueError):
                self.battery = None

        if with_volume and self._wpctl:
            try:
                out = subprocess.run([self._wpctl, "get-volume", "@DEFAULT_AUDIO_SINK@"],
                                     capture_output=True, text=True, timeout=1).stdout
                parts = out.split()
                if len(parts) >= 2 and parts[0] == "Volume:":
                    self.volume = min(100.0, float(parts[1]) * 100.0)
                    self.muted = "[MUTED]" in out
            except (OSError, ValueError, subprocess.TimeoutExpired):
                self.volume = None


class HudEffect(Effect):
    name = "hud"
    title = "Hyprland keybind HUD"
    cycle_duration = 3600.0
    default_fps = 30
    uses_input = True

    def __init__(self, gauges: bool = True, base: Optional[Color] = None):
        self.show_gauges = gauges
        self.base = base
        self.hypr = Hyprland()
        self.stats = SystemStats()
        self.layers: Dict[int, Dict[str, tuple]] = {}
        self.active_ws = 0
        self.occupied: set = set()
        self.connected = False
        self._stop = threading.Event()

    def setup(self, layout: Layout):
        self.layout = layout
        self.gauge_slots = {name: [layout.get(k).slot for k in keys] for name, keys in GAUGES.items()}
        self._poll(force_binds=True)
        if self.show_gauges:
            self.stats.update(with_volume=True)
        threading.Thread(target=self._worker, daemon=True).start()

    def teardown(self):
        self._stop.set()

    # -- background polling --------------------------------------------------------

    def _worker(self):
        tick = 0
        while not self._stop.wait(0.25):
            tick += 1
            try:
                self._poll(force_binds=tick % 40 == 0)
                if self.show_gauges and tick % 2 == 0:
                    self.stats.update(with_volume=True)
            except (OSError, ValueError, KeyError, IndexError):
                pass  # transient read failure; try again on the next tick

    def _poll(self, force_binds: bool = False):
        active = self.hypr.query("activeworkspace")
        workspaces = self.hypr.query("workspaces")
        self.connected = active is not None
        if active:
            self.active_ws = active.get("id", 0)
        if workspaces is not None:
            self.occupied = {w["id"] for w in workspaces if w.get("windows", 0) > 0}
        if force_binds or not self.layers:
            binds = self.hypr.query("binds")
            if binds is not None:
                self.layers = self._build_layers(binds)

    def _build_layers(self, binds: List[dict]) -> Dict[int, Dict[str, tuple]]:
        layers: Dict[int, Dict[str, tuple]] = {}
        for b in binds:
            if b.get("submap") or b.get("mouse") or not b.get("modmask"):
                continue
            key = keysym_to_key(b.get("key", ""))
            if key and self.layout.get(key):
                layers.setdefault(b["modmask"], {}).setdefault(key, (b["dispatcher"], b.get("arg", "")))
        return layers

    # -- drawing ---------------------------------------------------------------------

    def _workspace_color(self, ws: int, show_empty: bool) -> Optional[Color]:
        if ws == self.active_ws:
            return WS_ACTIVE
        if ws in self.occupied:
            return WS_OCCUPIED
        return WS_EMPTY if show_empty else None

    def render(self, ctx: EffectContext):
        canvas = ctx.canvas
        if self.base:
            for k in ctx.keys:
                canvas.pixels[k.slot] = self.base

        if self.show_gauges:
            self._gauges(canvas)

        mask = 0
        for name, bit in MOD_KEYS.items():
            if ctx.is_key_down(name):
                mask |= bit

        if mask:
            layer = self.layers.get(mask, {})
            for key, (dispatcher, arg) in layer.items():
                color = bind_color(dispatcher, arg)
                if dispatcher in WORKSPACE_DISPATCHERS and arg.strip().isdigit():
                    color = self._workspace_color(int(arg), show_empty=True)
                canvas.set_key(key, color)
            for name, bit in MOD_KEYS.items():
                if ctx.is_key_down(name):
                    canvas.set_key(name, HELD)
            mods = "+".join(n for bit, n in MOD_NAMES if mask & bit)
            ctx.set_status(f"{mods}: {len(layer)} bound keys")
        else:
            for ws, key in enumerate(NUMBER_ROW, start=1):
                color = self._workspace_color(ws, show_empty=False)
                if color:
                    canvas.set_key(key, color)
            ctx.set_status(f"workspace {self.active_ws}" if self.connected else "Hyprland not found")

    def _meter(self, canvas, slots: List[int], pct: Optional[float], color_for):
        if pct is None:
            return
        lit = int(round(max(0.0, min(100.0, pct)) / 100.0 * len(slots)))
        if lit == 0 and pct > 2.0:
            lit = 1
        for i, slot in enumerate(slots):
            canvas.pixels[slot] = color_for(i, lit) if i < lit else GAUGE_OFF

    def _gauges(self, canvas):
        s = self.stats  # updated by the worker thread: take a consistent copy first
        cpu, ram, battery, charging = s.cpu, s.ram, s.battery, s.charging
        volume, muted = s.volume, s.muted

        cpu_slots = self.gauge_slots["cpu"]
        self._meter(canvas, cpu_slots, cpu,
                    lambda i, lit: CPU_COLORS[min(len(CPU_COLORS) - 1, i * len(CPU_COLORS) // len(cpu_slots))])
        ram_color = Color.rgb(235, 35, 130) if ram > 85 else Color.rgb(130, 80, 255) if ram > 70 \
            else Color.rgb(0, 195, 235)
        self._meter(canvas, self.gauge_slots["ram"], ram, lambda i, lit: ram_color)
        if battery is not None:
            bat_color = Color.rgb(255, 40, 40) if battery < 20 else Color.rgb(245, 170, 0) \
                if battery < 50 else Color.rgb(20, 220, 110)
            self._meter(canvas, self.gauge_slots["bat"], battery,
                        lambda i, lit: Color.rgb(235, 245, 255) if charging and i == lit - 1 else bat_color)
        if volume is not None:
            vol = self.gauge_slots["vol"]
            if muted:  # only the bottom segment, in red
                self._meter(canvas, vol, 100.0 / len(vol), lambda i, lit: Color.rgb(185, 25, 25))
            else:
                self._meter(canvas, vol, volume, lambda i, lit: Color.rgb(45, 160, 255))
