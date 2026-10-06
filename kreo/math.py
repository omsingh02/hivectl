"""
Noise and sampling helpers for effects.
"""
import math
from typing import List, Tuple

_PERM = [
    151,160,137,91,90,15,131,13,201,95,96,53,194,233,7,225,140,36,103,30,69,142,
    8,99,37,240,21,10,23,190,6,148,247,120,234,75,0,26,197,62,94,252,219,203,117,
    35,11,32,57,177,33,88,237,149,56,87,174,20,125,136,171,168,68,175,74,165,71,
    134,139,48,27,166,77,146,158,231,83,111,229,122,60,211,133,230,220,105,92,41,
    55,46,245,40,244,102,143,54,65,25,63,161,1,216,80,73,209,76,132,187,208,89,
    18,169,200,196,135,130,116,188,159,86,164,100,109,198,173,186,3,64,52,217,226,
    250,124,123,5,202,38,147,118,126,255,82,85,212,207,206,59,227,47,16,58,17,182,
    189,28,42,223,183,170,213,119,248,152,2,44,154,163,70,221,153,101,155,167,43,
    172,9,129,22,39,253,19,98,108,110,79,113,224,232,178,185,112,104,218,246,97,
    228,251,34,242,193,238,210,144,12,191,179,162,241,81,51,145,235,249,14,239,
    107,49,192,214,31,181,199,106,157,184,84,204,176,115,121,50,45,127,4,150,254,
    138,236,205,93,222,114,67,29,24,72,243,141,128,195,78,66,215,61,156,180
] * 2


def _fade(t: float) -> float:
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def _lerp(t: float, lo: float, hi: float) -> float:
    return lo + t * (hi - lo)


def _grad(h: int, x: float, y: float, z: float) -> float:
    h &= 15
    u = x if h < 8 else y
    v = y if h < 4 else (x if h in (12, 14) else z)
    return (u if (h & 1) == 0 else -u) + (v if (h & 2) == 0 else -v)


def perlin3d(x: float, y: float, z: float) -> float:
    """3D Perlin gradient noise mapped to 0.0-1.0."""
    fx, fy, fz = math.floor(x), math.floor(y), math.floor(z)
    xi, yi, zi = int(fx) & 255, int(fy) & 255, int(fz) & 255
    x, y, z = x - fx, y - fy, z - fz
    u, v, w = _fade(x), _fade(y), _fade(z)
    p = _PERM
    a = p[xi] + yi
    aa, ab = p[a] + zi, p[a + 1] + zi
    b = p[xi + 1] + yi
    ba, bb = p[b] + zi, p[b + 1] + zi
    n = _lerp(w,
              _lerp(v, _lerp(u, _grad(p[aa], x, y, z), _grad(p[ba], x - 1, y, z)),
                       _lerp(u, _grad(p[ab], x, y - 1, z), _grad(p[bb], x - 1, y - 1, z))),
              _lerp(v, _lerp(u, _grad(p[aa + 1], x, y, z - 1), _grad(p[ba + 1], x - 1, y, z - 1)),
                       _lerp(u, _grad(p[ab + 1], x, y - 1, z - 1), _grad(p[bb + 1], x - 1, y - 1, z - 1))))
    return (n + 1.0) * 0.5


def fbm3d(x: float, y: float, z: float, octaves: int = 3, lacunarity: float = 2.0, gain: float = 0.5) -> float:
    """Fractal (multi-octave) Perlin noise in 0.0-1.0."""
    total, amplitude, frequency, norm = 0.0, 1.0, 1.0, 0.0
    for _ in range(octaves):
        total += perlin3d(x * frequency, y * frequency, z * frequency) * amplitude
        norm += amplitude
        amplitude *= gain
        frequency *= lacunarity
    return total / norm


def smoothstep(edge0: float, edge1: float, x: float) -> float:
    t = max(0.0, min(1.0, (x - edge0) / (edge1 - edge0)))
    return t * t * (3.0 - 2.0 * t)


def sample_key_samples(key, num_samples: int = 3) -> List[Tuple[float, float, float]]:
    """(x, y, weight) points along wide or tall keys (Space, Shift, KP+...) so they blend smoothly."""
    if num_samples <= 1 or (key.w <= 1.4 and key.h <= 1.4):
        return [(key.cx, key.cy, 1.0)]
    weight = 1.0 / num_samples
    if key.w > key.h:
        step = (key.w - 0.4) / (num_samples - 1)
        return [(key.x + 0.2 + i * step, key.cy, weight) for i in range(num_samples)]
    step = (key.h - 0.4) / (num_samples - 1)
    return [(key.cx, key.y + 0.2 + i * step, weight) for i in range(num_samples)]
