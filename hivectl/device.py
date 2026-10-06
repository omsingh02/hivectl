"""
Kreo Hive 98 vendor protocol over Linux hidraw (no external dependencies).
"""
import glob
import os
import re
import select
import time
from dataclasses import dataclass
from typing import Optional, Tuple

from hivectl.constants import (
    VENDOR_ID, PRODUCT_ID, VENDOR_INTERFACE, REPORT_ID, PACKET_SIZE, HEADER_SIZE, CHUNK_SIZE,
    CMD_BEGIN_CONFIG, CMD_END_CONFIG, CMD_READ_CONFIG, CMD_WRITE_CONFIG, CMD_READ_KEYMAP,
    CMD_READ_CUSTOM_LEDS, CMD_WRITE_CUSTOM_LEDS, CMD_SEND_FRAME, CMD_END_FRAME,
    FRAME_SIZE, OFFSET_ACTIVE_PROFILE, PROFILE_OFFSETS, CONFIG_SIZE, LIGHTING_FIELDS,
    P_MODE, P_BRIGHTNESS, P_SPEED, P_DIRECTION, P_RAINBOW, P_RED, P_GREEN, P_BLUE,
    MAX_BRIGHTNESS, MAX_SPEED,
)

UDEV_HINT = ("install the udev rule: sudo install -m 0644 udev/71-kreo-hive98.rules /etc/udev/rules.d/ "
             "&& sudo udevadm control --reload && sudo udevadm trigger --subsystem-match=hidraw")


class DeviceNotFound(RuntimeError):
    pass


def find_hidraw(interface: int) -> str:
    """Returns /dev/hidrawN for the given USB interface of the keyboard."""
    hid_id = f"HID_ID=0003:{VENDOR_ID:08X}:{PRODUCT_ID:08X}"
    for node in sorted(glob.glob("/sys/class/hidraw/hidraw*")):
        try:
            with open(f"{node}/device/uevent", encoding="utf-8") as f:
                uevent = f.read()
        except OSError:
            continue
        m = re.search(r"^HID_PHYS=.*/input(\d+)$", uevent, re.M)
        if hid_id in uevent and m and int(m.group(1)) == interface:
            return "/dev/" + os.path.basename(node)
    raise DeviceNotFound("Kreo Hive 98 (USB 320F:5055) not found - is it plugged in by cable?")


@dataclass
class Profile:
    index: int
    mode: int
    brightness: int
    speed: int
    direction: int
    rainbow: bool
    color: Tuple[int, int, int]

    @property
    def hex(self) -> str:
        return "#%02X%02X%02X" % self.color


class KreoKeyboard:
    def __init__(self, path: Optional[str] = None):
        self.path = path or find_hidraw(VENDOR_INTERFACE)
        try:
            self.fd = os.open(self.path, os.O_RDWR | os.O_NONBLOCK)
        except PermissionError:
            raise PermissionError(f"no access to {self.path}; {UDEV_HINT}") from None
        self._drain()

    def close(self):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def _drain(self):
        while select.select([self.fd], [], [], 0)[0]:
            try:
                os.read(self.fd, PACKET_SIZE)
            except BlockingIOError:
                break

    # -- transport -------------------------------------------------------------

    def query(self, cmd: int, offset: int = 0, data: bytes = b"", size: Optional[int] = None,
              timeout: float = 0.5) -> bytes:
        """Sends one command packet and returns the matching response packet."""
        self._drain()  # drop queued key reports so a full buffer can't swallow the reply
        pkt = bytearray(PACKET_SIZE)
        pkt[0] = REPORT_ID
        pkt[3] = cmd
        pkt[4] = len(data) if size is None else size
        pkt[5] = offset & 0xFF
        pkt[6] = (offset >> 8) & 0xFF
        pkt[HEADER_SIZE:HEADER_SIZE + len(data)] = data
        checksum = sum(pkt[3:]) & 0xFFFF
        pkt[1] = checksum & 0xFF
        pkt[2] = checksum >> 8
        os.write(self.fd, pkt)

        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"keyboard did not answer command 0x{cmd:02X}")
            if not select.select([self.fd], [], [], remaining)[0]:
                continue
            resp = os.read(self.fd, PACKET_SIZE)
            # Interface 1 also carries NKRO key and mouse reports; skip anything else.
            if len(resp) == PACKET_SIZE and resp[0] == REPORT_ID and resp[3] == cmd \
                    and resp[5] | (resp[6] << 8) == offset & 0xFFFF:
                return resp

    def _read(self, cmd: int, offset: int, length: int) -> bytes:
        out = bytearray()
        while len(out) < length:
            n = min(CHUNK_SIZE, length - len(out))
            out += self.query(cmd, offset + len(out), size=n)[HEADER_SIZE:HEADER_SIZE + n]
        return bytes(out)

    def _write(self, cmd: int, offset: int, data: bytes):
        self.query(CMD_BEGIN_CONFIG)
        try:
            for pos in range(0, len(data), CHUNK_SIZE):
                self.query(cmd, offset + pos, data[pos:pos + CHUNK_SIZE])
        finally:
            self.query(CMD_END_CONFIG)

    # -- config / profiles -----------------------------------------------------

    def read_config(self, offset: int = 0, length: int = CONFIG_SIZE) -> bytes:
        return self._read(CMD_READ_CONFIG, offset, length)

    def write_config(self, offset: int, data: bytes):
        if offset < 0 or offset + len(data) > CONFIG_SIZE:
            raise ValueError("config write would run past the profile area into the keymap")
        self._write(CMD_WRITE_CONFIG, offset, data)
        if self.read_config(offset, len(data)) != bytes(data):
            raise IOError("keyboard did not store the new settings (read-back mismatch)")

    def get_active_profile(self) -> int:
        idx = self.read_config(OFFSET_ACTIVE_PROFILE, 1)[0]
        return idx if idx < len(PROFILE_OFFSETS) else 0

    def set_active_profile(self, idx: int):
        if idx not in range(len(PROFILE_OFFSETS)):
            raise ValueError("profile must be 1, 2 or 3")
        self.write_config(OFFSET_ACTIVE_PROFILE, bytes([idx]))

    def read_profile(self, idx: Optional[int] = None) -> Profile:
        if idx is None:
            idx = self.get_active_profile()
        b = self.read_config(PROFILE_OFFSETS[idx], LIGHTING_FIELDS)
        return Profile(idx, b[P_MODE], b[P_BRIGHTNESS], b[P_SPEED], b[P_DIRECTION],
                       b[P_RAINBOW] == 0xFF, (b[P_RED], b[P_GREEN], b[P_BLUE]))

    def write_profile(self, idx: Optional[int] = None, mode: Optional[int] = None,
                      brightness: Optional[int] = None, speed: Optional[int] = None,
                      direction: Optional[int] = None, rainbow: Optional[bool] = None,
                      color: Optional[Tuple[int, int, int]] = None) -> Profile:
        """Updates the given lighting fields of a profile; everything else is preserved."""
        p = self.read_profile(idx)
        if mode is not None:
            p.mode = mode
        if brightness is not None:
            p.brightness = max(0, min(MAX_BRIGHTNESS, int(brightness)))
        if speed is not None:
            p.speed = max(0, min(MAX_SPEED, int(speed)))
        if direction is not None:
            p.direction = 1 if direction else 0
        if rainbow is not None:
            p.rainbow = bool(rainbow)
        if color is not None:
            p.color = tuple(max(0, min(255, int(c))) for c in color)
        fields = bytes([p.mode, p.brightness, p.speed, p.direction,
                        0xFF if p.rainbow else 0x00, *p.color])
        self.write_config(PROFILE_OFFSETS[p.index], fields)
        return p

    # -- per-key colors stored on the keyboard (mode "custom") ------------------

    def read_custom_leds(self) -> bytes:
        return self._read(CMD_READ_CUSTOM_LEDS, 0, FRAME_SIZE)

    def write_custom_leds(self, data: bytes):
        if len(data) != FRAME_SIZE:
            raise ValueError(f"custom LED table must be {FRAME_SIZE} bytes")
        self._write(CMD_WRITE_CUSTOM_LEDS, 0, data)
        if self.read_custom_leds() != bytes(data):
            raise IOError("keyboard did not store the per-key colors (read-back mismatch)")

    def read_keymap(self) -> bytes:
        """Raw keymap (3 bytes per slot). Read-only: kept in backups for reference."""
        return self._read(CMD_READ_KEYMAP, 0, FRAME_SIZE)

    # -- live streaming (RAM only, no EEPROM wear) ------------------------------

    def send_frame(self, frame: bytes):
        for pos in range(0, FRAME_SIZE, CHUNK_SIZE):
            self.query(CMD_SEND_FRAME, pos, frame[pos:pos + CHUNK_SIZE], timeout=0.1)

    def end_frames(self):
        """Leaves streaming mode; the keyboard returns to its stored profile."""
        self.query(CMD_END_FRAME)
