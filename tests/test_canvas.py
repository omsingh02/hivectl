from hivectl.canvas import CIE_LUT, Canvas
from hivectl.color import Color
from hivectl.constants import FRAME_SIZE, NUM_SLOTS


def test_frame_has_the_size_the_keyboard_expects():
    assert len(Canvas().to_frame()) == FRAME_SIZE == NUM_SLOTS * 3


def test_raw_frame_writes_rgb_per_slot():
    canvas = Canvas()
    canvas.set_pixel(0, Color.rgb(10, 20, 30))
    assert canvas.to_frame(perceptual=False)[:3] == bytes([10, 20, 30])


def test_out_of_range_slot_is_ignored():
    canvas = Canvas()
    canvas.set_pixel(NUM_SLOTS + 5, Color.rgb(255, 0, 0))
    assert canvas.to_frame(perceptual=False) == bytes(FRAME_SIZE)


def test_translucent_pixel_composites_over_existing():
    canvas = Canvas()
    canvas.set_pixel(1, Color(1, 1, 1, 0.5))
    assert canvas.to_frame(perceptual=False)[3:6] == bytes([128, 128, 128])


def test_perceptual_curve_is_monotonic_and_spans_the_range():
    assert CIE_LUT[0] == 0
    assert CIE_LUT[255] == 255
    assert all(a <= b for a, b in zip(CIE_LUT, CIE_LUT[1:]))
