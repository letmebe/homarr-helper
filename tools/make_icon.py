# 生成原创扩展图标（"添加到仪表盘"概念，不使用任何第三方商标图形）
# 设计：品牌渐变圆角底 + 2x2 仪表盘格 + 其中一格为"+"，含义"把页面加进面板"
# 输出: icon48.png / icon128.png / icon512.png（主稿）
import os
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BRAND_A = (99, 102, 241)   # #6366f1
BRAND_B = (139, 92, 246)   # #8b5cf6
WHITE = (255, 255, 255, 255)
WHITE_SOFT = (255, 255, 255, 235)

S = 512
RADIUS_TILE = 34          # 格子圆角
RADIUS_BG = int(S * 0.22) # 底板圆角


def v_gradient(size, top, bottom):
    w, h = size
    g = Image.new('RGB', (1, h))
    for y in range(h):
        t = y / max(1, h - 1)
        g.putpixel((0, y), tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
    return g.resize((w, h))


def rounded_mask(size, radius):
    m = Image.new('L', size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, size[0] - 1, size[1] - 1], radius=radius, fill=255)
    return m


def rounded_tile(draw, box, fill, radius=RADIUS_TILE):
    draw.rounded_rectangle(box, radius=radius, fill=fill)


def rounded_plus(draw, cx, cy, arm, thick, fill):
    """圆角端点的加号"""
    r = thick // 2
    draw.rounded_rectangle([cx - arm, cy - r, cx + arm, cy + r], radius=r, fill=fill)
    draw.rounded_rectangle([cx - r, cy - arm, cx + r, cy + arm], radius=r, fill=fill)


def build():
    base = v_gradient((S, S), BRAND_A, BRAND_B).convert('RGBA')

    # 轻微内高光，避免纯平面显得廉价
    hl = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(hl).rounded_rectangle(
        [10, 10, S - 10, int(S * 0.55)], radius=RADIUS_BG - 10, fill=(255, 255, 255, 26))
    base = Image.alpha_composite(base, hl)

    d = ImageDraw.Draw(base)

    # 2x2 网格：tile 132, gap 44 → 总宽 308，居中
    tile, gap = 132, 44
    total = tile * 2 + gap
    left = (S - total) // 2
    top = (S - total) // 2
    x0, x1 = left, left + tile + gap
    y0, y1 = top, top + tile + gap

    # 左上、左下、右下三块实心格子
    rounded_tile(d, [x0, y0, x0 + tile, y0 + tile], WHITE)
    rounded_tile(d, [x0, y1, x0 + tile, y1 + tile], WHITE_SOFT)
    rounded_tile(d, [x1, y1, x1 + tile, y1 + tile], WHITE_SOFT)

    # 右上格：加号（比格子略大，突出"添加"）
    cx, cy = x1 + tile // 2, y0 + tile // 2
    rounded_plus(d, cx, cy, arm=int(tile * 0.52), thick=40, fill=WHITE)

    # 裁圆角
    mask = rounded_mask((S, S), RADIUS_BG)
    out = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    out.paste(base, (0, 0), mask)

    out.save(os.path.join(ROOT, 'icon512.png'))
    out.resize((128, 128), Image.LANCZOS).save(os.path.join(ROOT, 'icon128.png'))
    out.resize((48, 48), Image.LANCZOS).save(os.path.join(ROOT, 'icon48.png'))
    return out


if __name__ == '__main__':
    build()
    for f in ('icon512.png', 'icon128.png', 'icon48.png'):
        p = os.path.join(ROOT, f)
        print(f, Image.open(p).size, f'{os.path.getsize(p)/1024:.0f}KB')
