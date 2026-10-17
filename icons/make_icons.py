"""Draw the TraceLoft-next desktop shortcut icons as multi-size .ico files: a green 'start' (play)
and a red 'stop' (square), each with a cobalt ring so they are told apart from the real TraceLoft
icons beside them.

Needs Pillow, which this venv does not install; TraceCapture's venv has it:
`..\\TraceCapture\\.venv\\Scripts\\python.exe icons\\make_icons.py`. The generated .ico files are
committed, so this only needs re-running to change the design.
"""

from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
SCALE = 4  # draw at 4x and downsample for smooth edges
COBALT = (37, 99, 235)
GREEN = (22, 163, 74)
RED = (220, 38, 38)


def icon(fill, glyph):
    n = 256 * SCALE
    image = Image.new('RGBA', (n, n), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    pad = 6 * SCALE
    draw.ellipse((pad, pad, n - pad, n - pad), fill=COBALT)
    inner = pad + 24 * SCALE
    draw.ellipse((inner, inner, n - inner, n - inner), fill=fill)
    c = n / 2
    if glyph == 'play':
        h = 84 * SCALE  # optical centering: the triangle sits slightly right of center
        draw.polygon(
            [(c - h * 0.42, c - h * 0.62), (c - h * 0.42, c + h * 0.62), (c + h * 0.66, c)],
            fill='white',
        )
    else:
        s = 44 * SCALE
        draw.rounded_rectangle((c - s, c - s, c + s, c + s), radius=10 * SCALE, fill='white')
    return image.resize((256, 256), Image.LANCZOS)


if __name__ == '__main__':
    icon(GREEN, 'play').save(HERE / 'start-next.ico', sizes=SIZES)
    icon(RED, 'stop').save(HERE / 'stop-next.ico', sizes=SIZES)
    print('wrote start-next.ico and stop-next.ico')
