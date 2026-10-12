"""V3 image comparison copied for the synchronous standalone SDK.

Only asyncio/device-framework coupling is removed. In-flight synchronous capture
uses the device transport timeout; the comparison deadline is checked on return.
"""
import io
import time
from dataclasses import dataclass

from PIL import Image, ImageChops

@dataclass(frozen=True)
class StabilityResult:
    bytes_: bytes | None
    stable: bool
    elapsed_ms: int
    checks: int


@dataclass(frozen=True)
class FastStabilityPolicy:
    timeout_s: float = 4.0
    interval_s: float = 0.1
    pixel_delta: int = 12
    change_ratio: float = 0.001
    max_edge: int = 480


def policy_for_platform(platform: str) -> FastStabilityPolicy:
    if platform not in ('android', 'harmony', 'ios'):
        raise ValueError('Image comparison policy is not configured for this platform.')
    return FastStabilityPolicy(interval_s={'harmony': 0.0, 'ios': 0.2}.get(platform, 0.1))


def thumbnail(data: bytes, max_edge: int = 480) -> Image.Image:
    with Image.open(io.BytesIO(data)) as source:
        result = source.convert("RGB")
    result.thumbnail((max_edge, max_edge))
    return result


def pixel_change_ratio(previous: Image.Image, current: Image.Image, pixel_delta: int = 12) -> float:
    if previous.size != current.size:
        return 1.0
    red, green, blue = ImageChops.difference(previous, current).split()
    strongest = ImageChops.lighter(ImageChops.lighter(red, green), blue)
    histogram = strongest.histogram()
    return sum(histogram[pixel_delta + 1:]) / (current.width * current.height)


def wait_fast_stable(screenshot, *, frame_a_bytes=None, policy=None):
    """Compare fresh consecutive RGB frames; return the exact last JPEG.

    frame_a_bytes is intentionally ignored: an old pre-action frame must not
    substitute the first fresh sample. Visual quiet does not prove loading done.
    """
    policy = policy or FastStabilityPolicy()
    start = time.monotonic()
    previous = None
    last = None
    checks = 0
    while True:
        remaining = policy.timeout_s - (time.monotonic() - start)
        if remaining <= 0:
            return StabilityResult(last, False, int((time.monotonic()-start)*1000), checks)
        try:
            last = screenshot()
            if time.monotonic()-start >= policy.timeout_s:
                return StabilityResult(last, False, int((time.monotonic()-start)*1000), checks)
        except TimeoutError:
            return StabilityResult(last, False, int((time.monotonic()-start)*1000), checks)
        current = thumbnail(last, policy.max_edge)
        checks += 1
        if previous is not None:
            ratio = pixel_change_ratio(previous, current, policy.pixel_delta)
            if ratio <= policy.change_ratio:
                return StabilityResult(last, True, int((time.monotonic()-start)*1000), checks)
        previous = current
        elapsed = time.monotonic()-start
        time.sleep(min(policy.interval_s, max(0, policy.timeout_s-elapsed)))
