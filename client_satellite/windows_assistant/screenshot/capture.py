import io

MAX_PIXELS = 120_000_000


class CaptureError(Exception):
    pass


def grab():
    from PIL import ImageGrab

    try:
        image = ImageGrab.grab(all_screens=True)
    except OSError as exc:
        raise CaptureError(str(exc)) from exc
    if image.width * image.height > MAX_PIXELS:
        raise CaptureError("size")
    return image.convert("RGB")


def apply_masks(image, masks) -> None:
    from PIL import ImageDraw

    draw = ImageDraw.Draw(image)
    for mask in masks:
        x0 = image.width * mask.x // 1000
        y0 = image.height * mask.y // 1000
        x1 = -(-image.width * (mask.x + mask.w) // 1000)
        y1 = -(-image.height * (mask.y + mask.h) // 1000)
        draw.rectangle([x0, y0, max(x0, x1 - 1), max(y0, y1 - 1)], fill=(0, 0, 0))


def png(image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, "PNG", optimize=False, compress_level=3)
    return buffer.getvalue()


def locked() -> bool:
    import ctypes

    user32 = ctypes.windll.user32
    desktop = user32.OpenInputDesktop(0, False, 0x0100)
    if not desktop:
        return True
    user32.CloseDesktop(desktop)
    return False
