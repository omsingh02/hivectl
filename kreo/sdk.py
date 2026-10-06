"""
Effect base class, per-frame context, and effect discovery.
"""
import importlib.util
import sys
from pathlib import Path
from typing import Dict, List, Set, Type

from kreo.canvas import Canvas
from kreo.constants import EFFECTS_DIR
from kreo.layout import Key, Layout

REPO_EFFECTS_DIR = Path(__file__).resolve().parent.parent / "effects"


class EffectContext:
    """State handed to Effect.render() on every frame."""

    def __init__(self, canvas: Canvas, layout: Layout):
        self.canvas = canvas
        self.layout = layout
        self.keys = layout.keys
        self.width = layout.width
        self.height = layout.height
        self.cx = layout.cx
        self.cy = layout.cy

        self.time = 0.0            # seconds since start (scaled by --speed)
        self.dt = 0.0              # seconds since previous frame
        self.cycle_time = 0.0      # time within the current cycle_duration
        self.cycle_progress = 0.0  # cycle_time / cycle_duration

        self.key_events: List = []      # KeyEvent(key, is_down, timestamp) since last frame
        self.held_keys: Set[Key] = set()

        self.status = ""

    def set_status(self, text: str):
        self.status = text

    def is_key_down(self, name: str) -> bool:
        k = self.layout.get(name)
        return k in self.held_keys if k else False


class Effect:
    """Subclass and implement render(); setup() and teardown() are optional."""
    name = "base"
    title = "Base effect"
    cycle_duration = 10.0
    default_fps = 30
    uses_input = False

    def setup(self, layout: Layout):
        pass

    def render(self, ctx: EffectContext):
        pass

    def teardown(self):
        pass


def _load_module(path: Path):
    spec = importlib.util.spec_from_file_location(f"kreo_effect_{path.stem}", str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod  # dataclasses and friends look the module up while it loads
    try:
        spec.loader.exec_module(mod)
    except BaseException:
        del sys.modules[spec.name]
        raise
    return mod


def discover_effects() -> Dict[str, Type[Effect]]:
    """Effect classes by file name, from the repo effects/ dir and ~/.config/kreo/effects/
    (a user file with the same name replaces the built-in)."""
    found: Dict[str, Type[Effect]] = {}
    dirs = [d for d in (REPO_EFFECTS_DIR, EFFECTS_DIR) if d.is_dir()]
    for directory in dirs:
        for path in sorted(directory.glob("*.py")):
            if path.name.startswith(("_", ".")):
                continue
            try:
                mod = _load_module(path)
            except Exception as e:
                sys.stderr.write(f"warning: skipping effect {path}: {e}\n")
                continue
            classes = [v for v in vars(mod).values()
                       if isinstance(v, type) and issubclass(v, Effect) and v is not Effect
                       and v.__module__ == mod.__name__]
            if classes:
                found[path.stem.lower()] = classes[0]
    return dict(sorted(found.items()))
