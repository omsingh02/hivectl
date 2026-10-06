"""
Command line interface.
"""
import argparse
import json
import sys
import time
from pathlib import Path

from hivectl import __version__
from hivectl.color import Color, parse_color, theme_color
from hivectl.constants import FRAME_SIZE, CONFIG_SIZE, LIGHTING_MODES, MAX_BRIGHTNESS, MAX_SPEED, NAMED_COLORS
from hivectl.device import KreoKeyboard, Profile
from hivectl.engine import StreamLock, run
from hivectl.layout import GLOBAL_LAYOUT, ZONES

MODE_NAMES = {mode_id: name for name, (mode_id, _) in LIGHTING_MODES.items()}


def swatch(rgb) -> str:
    r, g, b = rgb
    return f"\033[48;2;{r};{g};{b}m    \033[0m #{r:02X}{g:02X}{b:02X}"


def describe(p: Profile) -> str:
    mode = MODE_NAMES.get(p.mode, f"0x{p.mode:02X}")
    color = "rainbow" if p.rainbow else swatch(p.color)
    return (f"{mode:<10} {color}  brightness {p.brightness}/{MAX_BRIGHTNESS}  "
            f"speed {p.speed} (0 fast, {MAX_SPEED} slow)" + ("  reversed" if p.direction else ""))


def render_board(colors) -> str:
    """Draws the board in the terminal; colors maps slot -> (r, g, b)."""
    scale = 5
    rows = {}
    for k in GLOBAL_LAYOUT.keys:
        rows.setdefault(int(k.y), []).append(k)
    lines = []
    for y in sorted(rows):
        line, col = "", 0
        for k in sorted(rows[y], key=lambda k: k.x):
            start, width = int(k.x * scale + 0.5), int(k.w * scale + 0.5) - 1
            line += " " * max(0, start - col)
            r, g, b = colors.get(k.slot, (0, 0, 0))
            fg = "30" if r * 0.3 + g * 0.59 + b * 0.11 > 110 else "37"
            label = k.name.replace("KP_", "")[:width].center(width)
            line += f"\033[{fg};48;2;{r};{g};{b}m{label}\033[0m"
            col = start + width
        lines.append(line)
    return "\n".join(lines)


# -- hardware settings ---------------------------------------------------------------

def cmd_status(args):
    with KreoKeyboard() as kbd:
        active = kbd.get_active_profile()
        print(f"Kreo Hive 98 on {kbd.path}")
        for i in range(3):
            marker = "*" if i == active else " "
            print(f" {marker} profile {i + 1}  {describe(kbd.read_profile(i))}")
    mouse = pegasus_status()
    if mouse:
        print(f"   Pegasus mouse  {mouse}")


def pegasus_status():
    """Battery of a connected Kreo Pegasus mouse via BlueZ, if python-dbus is available."""
    try:
        import dbus
        bus = dbus.SystemBus()
        manager = dbus.Interface(bus.get_object("org.bluez", "/"), "org.freedesktop.DBus.ObjectManager")
        for ifaces in manager.GetManagedObjects().values():
            dev = ifaces.get("org.bluez.Device1")
            if dev and "pegasus" in str(dev.get("Name", "")).lower():
                if not dev.get("Connected"):
                    return "disconnected"
                battery = ifaces.get("org.bluez.Battery1", {}).get("Percentage")
                return f"connected, battery {int(battery)}%" if battery is not None else "connected"
    except Exception:
        return None
    return None


def cmd_modes(args):
    for name, (mode_id, desc) in LIGHTING_MODES.items():
        print(f"  {name:<10} 0x{mode_id:02X}  {desc}")


def resolve_mode(text: str) -> int:
    key = text.lower()
    if key in LIGHTING_MODES:
        return LIGHTING_MODES[key][0]
    try:
        return int(text, 0)
    except ValueError:
        raise ValueError(f"unknown mode '{text}' (see: hivectl modes)") from None


def cmd_set(args):
    fields = {}
    if args.mode:
        fields["mode"] = resolve_mode(args.mode)
    if args.theme:
        fields["color"] = theme_color()[:3]
    elif args.color:
        fields["color"] = parse_color(args.color)
    if args.brightness is not None:
        fields["brightness"] = args.brightness
    if args.speed is not None:
        fields["speed"] = args.speed
    if args.reverse is not None:
        fields["direction"] = args.reverse
    if args.rainbow is not None:
        fields["rainbow"] = args.rainbow
    elif "color" in fields:
        fields["rainbow"] = False  # an explicit color means a fixed color
    if not fields:
        raise SystemExit("nothing to change (see: hivectl set -h)")

    idx = args.profile - 1 if args.profile else None
    with StreamLock(), KreoKeyboard() as kbd:
        before = kbd.read_profile(idx)
        after = kbd.write_profile(before.index, **fields)
        print(f"profile {after.index + 1}  {describe(after)}")
        if args.preview:
            try:
                time.sleep(args.preview)
            except KeyboardInterrupt:
                pass
            finally:
                kbd.write_profile(before.index, mode=before.mode, brightness=before.brightness,
                                  speed=before.speed, direction=before.direction,
                                  rainbow=before.rainbow, color=before.color)
                print(f"restored    {describe(before)}")


def cmd_power(args):
    with StreamLock(), KreoKeyboard() as kbd:
        p = kbd.read_profile()
        is_on = p.brightness > 0 and p.mode != LIGHTING_MODES["off"][0]
        turn_on = {"on": True, "off": False, "toggle": not is_on}[args.command]
        if turn_on and not is_on:
            mode = LIGHTING_MODES["static"][0] if p.mode == LIGHTING_MODES["off"][0] else None
            kbd.write_profile(p.index, brightness=MAX_BRIGHTNESS if p.brightness == 0 else None, mode=mode)
        elif not turn_on and p.brightness > 0:
            kbd.write_profile(p.index, brightness=0)
        print(f"backlight {'on' if turn_on else 'off'}")


def cmd_profile(args):
    if args.number is None:
        return cmd_status(args)
    with StreamLock(), KreoKeyboard() as kbd:
        kbd.set_active_profile(args.number - 1)
        print(f"profile {args.number}  {describe(kbd.read_profile(args.number - 1))}")


def cmd_custom(args):
    if args.action == "show":
        with KreoKeyboard() as kbd:
            table = kbd.read_custom_leds()
        print(render_board({k.slot: tuple(table[k.slot * 3:k.slot * 3 + 3]) for k in GLOBAL_LAYOUT.keys}))
        return

    with StreamLock(), KreoKeyboard() as kbd:
        if args.action != "apply":
            if args.action == "set":
                keys = [GLOBAL_LAYOUT.get(name) for name in args.keys]
                unknown = [n for n, k in zip(args.keys, keys) if k is None]
                if unknown:
                    raise SystemExit(f"unknown key(s): {', '.join(unknown)} (see: hivectl map)")
            elif args.action == "zone":
                keys = GLOBAL_LAYOUT.get_zone(args.zone)
            else:
                keys = GLOBAL_LAYOUT.keys
            rgb = parse_color(args.color)
            table = bytearray(kbd.read_custom_leds())
            for k in keys:
                table[k.slot * 3:k.slot * 3 + 3] = bytes(rgb)
            kbd.write_custom_leds(bytes(table))
            print(f"{len(keys)} key(s) set to {swatch(rgb)}")
        if args.action == "apply" or args.apply:
            p = kbd.write_profile(mode=LIGHTING_MODES["custom"][0])
            print(f"profile {p.index + 1} now shows the per-key colors")


def cmd_map(args):
    rows = {}
    for k in GLOBAL_LAYOUT.keys:
        rows.setdefault(int(k.y), []).append(k.name)
    for y in sorted(rows):
        print("  " + " ".join(rows[y]))
    print(f"\nzones: {', '.join(ZONES)}   symbols also work: ` - = [ ] \\ ; ' , . /")


def cmd_backup(args):
    path = Path(args.file or f"hivectl-backup-{time.strftime('%Y%m%d-%H%M%S')}.json").expanduser()
    with KreoKeyboard() as kbd:
        data = {
            "format": "hivectl-backup-1",
            "created": time.strftime("%Y-%m-%d %H:%M:%S"),
            "config": kbd.read_config().hex(),
            "custom_leds": kbd.read_custom_leds().hex(),
            "keymap": kbd.read_keymap().hex(),  # reference only, never written back
        }
    path.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
    print(f"saved {path}")


def cmd_restore(args):
    data = json.loads(Path(args.file).expanduser().read_text(encoding="utf-8"))
    try:
        assert data["format"] in ("hivectl-backup-1", "kreo-backup-3")
        config, leds = bytes.fromhex(data["config"]), bytes.fromhex(data["custom_leds"])
        assert len(config) == CONFIG_SIZE and len(leds) == FRAME_SIZE
    except (AssertionError, KeyError, TypeError, ValueError):
        raise SystemExit(f"{args.file} is not a complete backup made by 'hivectl backup'") from None
    with StreamLock(), KreoKeyboard() as kbd:
        kbd.write_config(0, config)
        kbd.write_custom_leds(leds)
    print(f"restored profiles and per-key colors from {args.file}")


# -- streaming -----------------------------------------------------------------------

def cmd_anim(args):
    from hivectl.sdk import discover_effects
    effects = discover_effects()
    if args.list or not args.name:
        for name, cls in effects.items():
            print(f"  {name:<11} {cls.title}")
        return
    cls = effects.get(args.name.lower())
    if not cls:
        raise SystemExit(f"no animation '{args.name}' (available: {', '.join(effects)})")
    effect = cls()
    run(effect, fps=args.fps or effect.default_fps, speed=args.speed, duration=args.duration)


def cmd_viz(args):
    from hivectl.visualizer import Visualizer
    run(Visualizer(args.mode, args.scheme, args.sensitivity, args.backend, args.fps), fps=args.fps)


def cmd_hud(args):
    from hivectl.hud import HudEffect
    base = None
    if args.base:
        base = Color.rgb(*(theme_color()[:3] if args.base == "theme" else parse_color(args.base)))
        base = base * args.base_level
    run(HudEffect(gauges=not args.no_gauges, base=base), fps=args.fps)


# -- interactive menu ----------------------------------------------------------------

def cmd_menu(args):
    from hivectl.sdk import discover_effects
    from hivectl.visualizer import MODES, SCHEMES

    def ask(prompt):
        try:
            return input(prompt).strip()
        except EOFError:
            raise SystemExit()

    def change(**fields):
        with StreamLock(), KreoKeyboard() as kbd:
            kbd.write_profile(**fields)

    while True:
        with KreoKeyboard() as kbd:
            p = kbd.read_profile()
        print(f"\nprofile {p.index + 1}  {describe(p)}")
        print("  1 mode  2 color  3 theme color  4 brightness  5 speed  6 rainbow  7 reverse  8 profile")
        print("  a animation  v visualizer  h hud  q quit")
        choice = ask("> ").lower()
        try:
            if choice in ("q", ""):
                return
            elif choice == "1":
                print("  " + " ".join(LIGHTING_MODES))
                change(mode=resolve_mode(ask("mode: ")))
            elif choice == "2":
                change(color=parse_color(ask(f"color (#RRGGBB or {', '.join(NAMED_COLORS)}): ")), rainbow=False)
            elif choice == "3":
                change(color=theme_color()[:3], rainbow=False)
            elif choice == "4":
                change(brightness=int(ask(f"brightness 0-{MAX_BRIGHTNESS}: ")))
            elif choice == "5":
                change(speed=int(ask(f"speed 0 (fast) - {MAX_SPEED} (slow): ")))
            elif choice == "6":
                change(rainbow=not p.rainbow)
            elif choice == "7":
                change(direction=not p.direction)
            elif choice == "8":
                with StreamLock(), KreoKeyboard() as kbd:
                    kbd.set_active_profile(int(ask("profile 1-3: ")) - 1)
            elif choice == "a":
                effects = discover_effects()
                print("  " + " ".join(effects))
                cls = effects.get(ask("animation: ").lower())
                if cls:
                    print("Ctrl+C to stop")
                    run(cls(), fps=cls.default_fps)
            elif choice == "v":
                mode = ask(f"mode ({'/'.join(MODES)}) [bars]: ") or "bars"
                scheme = ask(f"colors ({'/'.join(SCHEMES)}) [theme]: ") or "theme"
                if mode in MODES and scheme in SCHEMES:
                    from hivectl.visualizer import Visualizer
                    print("Ctrl+C to stop")
                    run(Visualizer(mode, scheme), fps=35)
            elif choice == "h":
                from hivectl.hud import HudEffect
                print("Ctrl+C to stop")
                run(HudEffect())
        except (ValueError, RuntimeError, OSError) as e:
            print(f"error: {e}")


# -- entry point -------------------------------------------------------------------------

def positive_float(text: str) -> float:
    value = float(text)
    if value <= 0:
        raise argparse.ArgumentTypeError("must be greater than 0")
    return value


def build_parser() -> argparse.ArgumentParser:
    from hivectl.visualizer import MODES, SCHEMES, BACKENDS
    parser = argparse.ArgumentParser(prog="hivectl", description="Kreo Hive 98 lighting control. "
                                     "Run without a command for an interactive menu.")
    parser.add_argument("--version", action="version", version=f"hivectl {__version__}")
    sub = parser.add_subparsers(dest="command", metavar="command")

    sub.add_parser("status", help="show the three onboard profiles (and Pegasus mouse battery)")
    sub.add_parser("modes", help="list the built-in hardware lighting modes")

    p = sub.add_parser("set", help="change the stored lighting of a profile")
    p.add_argument("-m", "--mode", help="mode name or id (see: hivectl modes)")
    color = p.add_mutually_exclusive_group()
    color.add_argument("-c", "--color", help="#RRGGBB or a color name")
    color.add_argument("-t", "--theme", action="store_true", help="use the pywal accent color")
    p.add_argument("-b", "--brightness", type=int, choices=range(MAX_BRIGHTNESS + 1))
    p.add_argument("-s", "--speed", type=int, choices=range(MAX_SPEED + 1), help="0 = fastest, 5 = slowest")
    p.add_argument("--reverse", action=argparse.BooleanOptionalAction, default=None,
                   help="run the animation in the opposite direction")
    p.add_argument("-r", "--rainbow", action=argparse.BooleanOptionalAction, default=None,
                   help="cycle colors instead of a fixed color")
    p.add_argument("-p", "--profile", type=int, choices=[1, 2, 3], help="profile to change (default: active)")
    p.add_argument("--preview", type=positive_float, metavar="SECONDS", help="apply, wait, then restore")

    for name, text in (("on", "backlight on"), ("off", "backlight off"), ("toggle", "toggle backlight")):
        sub.add_parser(name, help=text)

    p = sub.add_parser("profile", help="switch the active profile (no number: list them)")
    p.add_argument("number", type=int, nargs="?", choices=[1, 2, 3])

    p = sub.add_parser("custom", help="per-key colors stored on the keyboard (mode 'custom')")
    csub = p.add_subparsers(dest="action", metavar="action", required=True)
    c = csub.add_parser("set", help="color one or more keys")
    c.add_argument("keys", nargs="+", metavar="KEY")
    c.add_argument("color")
    c.add_argument("--apply", action="store_true", help="also switch the profile to mode 'custom'")
    c = csub.add_parser("zone", help="color a group of keys")
    c.add_argument("zone", choices=list(ZONES))
    c.add_argument("color")
    c.add_argument("--apply", action="store_true", help="also switch the profile to mode 'custom'")
    c = csub.add_parser("all", help="color every key")
    c.add_argument("color")
    c.add_argument("--apply", action="store_true", help="also switch the profile to mode 'custom'")
    csub.add_parser("show", help="draw the stored per-key colors")
    csub.add_parser("apply", help="switch the active profile to mode 'custom'")

    sub.add_parser("map", help="list key names and zones")

    p = sub.add_parser("anim", help="stream an animation (Ctrl+C to stop)")
    p.add_argument("name", nargs="?")
    p.add_argument("-l", "--list", action="store_true")
    p.add_argument("--speed", type=float, default=1.0, help="playback speed multiplier")
    p.add_argument("--fps", type=int, help="frame rate (max 45)")
    p.add_argument("--duration", type=float, default=0.0, metavar="SECONDS", help="stop after this long")

    p = sub.add_parser("viz", help="music visualizer via cava (Ctrl+C to stop)")
    p.add_argument("-m", "--mode", choices=MODES, default="bars")
    p.add_argument("-s", "--scheme", choices=SCHEMES, default="theme")
    p.add_argument("-S", "--sensitivity", type=float, default=1.3)
    p.add_argument("-f", "--fps", type=int, default=35)
    p.add_argument("-b", "--backend", choices=BACKENDS, default="pulse")

    p = sub.add_parser("hud", help="Hyprland keybind HUD + numpad gauges (Ctrl+C to stop)")
    p.add_argument("--no-gauges", action="store_true", help="leave the numpad dark")
    p.add_argument("--base", metavar="COLOR", help="dim backlight under everything ('theme' or a color)")
    p.add_argument("--base-level", type=float, default=0.25, help="brightness of --base (0-1)")
    p.add_argument("--fps", type=int, default=30)

    p = sub.add_parser("backup", help="save profiles and per-key colors to a JSON file")
    p.add_argument("file", nargs="?")
    p = sub.add_parser("restore", help="write a backup made with 'hivectl backup' back to the keyboard")
    p.add_argument("file")
    return parser


COMMANDS = {
    "status": cmd_status, "modes": cmd_modes, "set": cmd_set, "on": cmd_power, "off": cmd_power,
    "toggle": cmd_power, "profile": cmd_profile, "custom": cmd_custom, "map": cmd_map,
    "anim": cmd_anim, "viz": cmd_viz, "hud": cmd_hud,
    "backup": cmd_backup, "restore": cmd_restore,
}


def main():
    args = build_parser().parse_args()
    handler = COMMANDS.get(args.command, cmd_menu)
    try:
        handler(args)
    except KeyboardInterrupt:
        print()
    except (RuntimeError, OSError, ValueError) as e:
        sys.exit(f"hivectl: {e}")


if __name__ == "__main__":
    main()
