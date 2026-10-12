# 打包 Edge 加载项商店上传用的 zip（manifest.json 必须在压缩包根目录）
# 用法: python tools/package_store.py
import os, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

FILES = [
    'manifest.json', 'background.js',
    'popup.html', 'popup.js',
    'options.html', 'options.js',
    'newtab.html', 'newtab.js',
    'i18n-core.js', 'i18n.js',
    'icon48.png', 'icon128.png',
]
DIRS = ['_locales']

import json
version = json.load(open('manifest.json', encoding='utf-8'))['version']
out = f'homarr-helper-edge-{version}.zip'

with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
    for f in FILES:
        z.write(f, f)
    for d in DIRS:
        for dirpath, _, names in os.walk(d):
            for n in names:
                p = os.path.join(dirpath, n)
                z.write(p, p.replace('\\', '/'))

with zipfile.ZipFile(out) as z:
    names = z.namelist()
print(out, f'{os.path.getsize(out)/1024:.0f}KB', f'{len(names)} files')
for n in names:
    print(' ', n)
