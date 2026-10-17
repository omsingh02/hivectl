from hivectl.color import Color, parse_color


def test_hex_round_trip():
    assert Color.from_hex("#FF8000").to_hex() == "#FF8000"


def test_short_hex_and_named_colours():
    assert parse_color("#0f8") == (0, 255, 136)
    assert parse_color("cyan") == (68, 222, 245)


def test_rgb_channels_are_clamped():
    assert Color(2.0, -1.0, 0.5).to_tuple() == (255, 0, 128)


def test_lerp_midpoint():
    assert Color(0, 0, 0).lerp(Color(1, 1, 1), 0.5).to_tuple() == (128, 128, 128)


def test_hsv_cyan():
    assert Color.from_hsv(0.5, 1.0, 1.0).to_tuple() == (0, 255, 255)


def test_over_blends_with_background():
    out = Color(1, 1, 1, 0.5).over(Color(0, 0, 0))
    assert out.to_tuple() == (128, 128, 128)
