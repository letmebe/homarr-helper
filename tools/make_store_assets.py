# 生成 Microsoft Edge 加载项商店所需图片素材
# 用法: python tools/make_store_assets.py
# 输出: assets/store/
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'assets', 'store')
os.makedirs(OUT, exist_ok=True)

ICON = Image.open(os.path.join(ROOT, 'icon128.png')).convert('RGBA')

BRAND_A = (99, 102, 241)   # #6366f1
BRAND_B = (139, 92, 246)   # #8b5cf6
TEXT_LIGHT = (255, 255, 255)


def load_font(size, bold=True, cjk=False):
    if cjk:
        cjk_candidates = [
            r'C:\Windows\Fonts\msyhbd.ttc' if bold else r'C:\Windows\Fonts\msyh.ttc',
            r'C:\Windows\Fonts\simhei.ttf',
        ]
        for p in cjk_candidates:
            if os.path.exists(p):
                return ImageFont.truetype(p, size)
    candidates = [
        r'C:\Windows\Fonts\segoeuib.ttf' if bold else r'C:\Windows\Fonts\segoeui.ttf',
        r'C:\Windows\Fonts\arialbd.ttf' if bold else r'C:\Windows\Fonts\arial.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
    ]
    for p in candidates:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default(size)


def v_gradient(size, top, bottom):
    w, h = size
    g = Image.new('RGB', (1, h))
    for y in range(h):
        t = y / max(1, h - 1)
        g.putpixel((0, y), tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
    return g.resize((w, h))


def draw_text_center(img, text, font, fill, cy, stroke=0):
    d = ImageDraw.Draw(img)
    bbox = d.textbbox((0, 0), text, font=font, stroke_width=stroke)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text(((img.width - tw) / 2 - bbox[0], cy - th / 2 - bbox[1]), text,
           font=font, fill=fill, stroke_width=stroke,
           stroke_fill=fill)
    return th


# ── 1. 商店 Logo 300x300（必填）──────────────────────────
logo = ICON.resize((300, 300), Image.LANCZOS)
logo.save(os.path.join(OUT, 'logo-300x300.png'))

# 备用：128x128（商店最低尺寸，一般用不到，icon128 已有）
print('logo-300x300.png', logo.size)

# ── 2. 小促销磁贴 440x280（可选）─────────────────────────
tile = v_gradient((440, 280), BRAND_A, BRAND_B).convert('RGBA')
ico = ICON.resize((120, 120), Image.LANCZOS)
tile.alpha_composite(ico, ((440 - 120) // 2, 40))
f1 = load_font(34)
f2 = load_font(20, bold=False)
draw_text_center(tile, 'Homarr Helper', f1, TEXT_LIGHT, 205)
draw_text_center(tile, 'Add any page to your Homarr board', f2, (255, 255, 255, 225), 243)
tile.convert('RGB').save(os.path.join(OUT, 'promo-small-440x280.png'))

# ── 3. 大促销磁贴 1400x560（可选）────────────────────────
big = v_gradient((1400, 560), BRAND_A, BRAND_B).convert('RGBA')
# 轻微柔光圆装饰
deco = Image.new('RGBA', big.size, (0, 0, 0, 0))
dd = ImageDraw.Draw(deco)
dd.ellipse([1020, -180, 1560, 360], fill=(255, 255, 255, 26))
dd.ellipse([-160, 380, 320, 860], fill=(255, 255, 255, 20))
deco = deco.filter(ImageFilter.GaussianBlur(24))
big = Image.alpha_composite(big, deco)

bico = ICON.resize((220, 220), Image.LANCZOS)
big.alpha_composite(bico, (150, 170))

fb1 = load_font(66)
fb2 = load_font(30, bold=False)
fb3 = load_font(30, bold=False, cjk=True)
d = ImageDraw.Draw(big)
d.text((430, 195), 'Homarr Helper', font=fb1, fill=TEXT_LIGHT)
d.text((432, 285), 'Add any page to your Homarr dashboard', font=fb2, fill=(255, 255, 255, 235))
d.text((432, 335), 'One click  ·  Self-hosted friendly  ·  中文 / English', font=fb3, fill=(255, 255, 255, 200))
big.convert('RGB').save(os.path.join(OUT, 'promo-large-1400x560.png'))

for f in sorted(os.listdir(OUT)):
    p = os.path.join(OUT, f)
    print(f, Image.open(p).size, f'{os.path.getsize(p)/1024:.0f}KB')
