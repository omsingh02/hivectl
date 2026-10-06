"""
Frame loop: renders an Effect and streams it to the keyboard until stopped.
"""
import fcntl
import os
import shutil
import signal
import sys
import time

from hivectl.canvas import Canvas
from hivectl.device import KreoKeyboard
from hivectl.input import InputMonitor
from hivectl.layout import GLOBAL_LAYOUT
from hivectl.sdk import Effect, EffectContext

MAX_FPS = 45            # one frame is 7 USB round trips (~21 ms)
KEEPALIVE_SEC = 0.1     # an unchanged frame is re-sent at this interval only


class StreamLock:
    """Only one hivectl process can stream frames at a time."""

    def __init__(self):
        runtime_dir = os.environ.get("XDG_RUNTIME_DIR") or "/tmp"
        self.path = os.path.join(runtime_dir, f"hivectl-{os.getuid()}.lock")
        self.file = None

    def __enter__(self):
        self.file = open(self.path, "a+")
        try:
            fcntl.flock(self.file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.file.seek(0)
            pid = self.file.read().strip() or "?"
            self.file.close()
            raise RuntimeError(f"another hivectl stream is already running (pid {pid}); stop it first")
        self.file.truncate(0)
        self.file.write(str(os.getpid()))
        self.file.flush()
        return self

    def __exit__(self, *exc):
        self.file.close()


def run(effect: Effect, fps: int = 30, speed: float = 1.0, duration: float = 0.0):
    """Streams effect frames until Ctrl+C / SIGTERM (or `duration` seconds)."""
    interval = 1.0 / max(1, min(MAX_FPS, int(fps)))
    canvas = Canvas(GLOBAL_LAYOUT)
    ctx = EffectContext(canvas, GLOBAL_LAYOUT)
    show_status = sys.stdout.isatty()

    stop = False

    def request_stop(signum, frame):
        nonlocal stop
        stop = True

    # SIGHUP: closing the terminal must still hand the keyboard back to its profile
    stop_signals = (signal.SIGINT, signal.SIGTERM, signal.SIGHUP, signal.SIGQUIT)
    previous = {s: signal.signal(s, request_stop) for s in stop_signals}
    try:
        with StreamLock(), KreoKeyboard() as kbd:
            inputs = InputMonitor(GLOBAL_LAYOUT) if effect.uses_input else None
            try:
                effect.setup(GLOBAL_LAYOUT)
                try:
                    _loop(effect, ctx, canvas, kbd, inputs, interval, speed, duration, show_status, lambda: stop)
                finally:
                    try:
                        kbd.end_frames()
                    except OSError:
                        pass
                    effect.teardown()
            finally:
                if inputs:
                    inputs.close()
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)
        if show_status:
            print()


def _loop(effect, ctx, canvas, kbd, inputs, interval, speed, duration, show_status, stopped):
    start = last = next_frame = time.monotonic()
    last_frame, last_send = b"", 0.0
    frames, fps_since, measured_fps, last_status = 0, start, 0.0, 0.0
    while not stopped():
        now = time.monotonic()
        if duration and now - start >= duration:
            break
        ctx.dt = (now - last) * speed
        ctx.time = (now - start) * speed
        ctx.cycle_time = ctx.time % effect.cycle_duration
        ctx.cycle_progress = ctx.cycle_time / effect.cycle_duration
        last = now
        if inputs:
            ctx.key_events = inputs.poll()
            ctx.held_keys = inputs.held_keys

        canvas.clear()
        effect.render(ctx)
        frame = canvas.to_frame()
        if frame != last_frame or now - last_send >= KEEPALIVE_SEC:
            kbd.send_frame(frame)
            last_frame, last_send = frame, now
        frames += 1

        if show_status and now - last_status >= 0.25:
            if now - fps_since >= 1.0:
                measured_fps, frames, fps_since = frames / (now - fps_since), 0, now
            line = f"  {effect.name}  {measured_fps:4.1f} fps  {ctx.status}"
            width = shutil.get_terminal_size().columns - 1
            sys.stdout.write("\r" + line[:width].ljust(width))
            sys.stdout.flush()
            last_status = now

        next_frame += interval
        delay = next_frame - time.monotonic()
        if delay > 0:
            time.sleep(delay)
        elif delay < -0.25:  # fell far behind (suspend, slow frame): resync instead of bursting
            next_frame = time.monotonic()
