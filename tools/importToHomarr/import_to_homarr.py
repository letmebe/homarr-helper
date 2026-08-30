#!/usr/bin/env python3
"""
通用书签 → Homarr 批量导入工具

用法:
  python import_to_homarr.py <excel文件> --enrich    解析URL、检测可用性、匹配图标、补充名称
  python import_to_homarr.py <excel文件> --import    从 Excel 读取并执行导入（支持断点续传）
  python import_to_homarr.py <excel文件> --retry     重试失败/死链项
  python import_to_homarr.py <excel文件> --status    查看当前导入状态

工作流:
  1. 准备 Excel 文件，至少包含"URL"列（可选"名称"列）
  2. --enrich 自动检测 URL 可用性、匹配图标、补充缺失名称，回写到 Excel
  3. 在 Excel「说明」页填写 Homarr URL 和 API Key
  4. 用户在 Excel 中填写"Board名称"和"分组"列（Board 名称须为英文 slug）
  5. --import 按 Board 分组执行导入，状态回写到 Excel
  6. --retry 重新检测死链/重试失败项
"""

import json
import os
import sys
import time
import re
import argparse
import urllib.request
import urllib.error
from urllib.parse import urlparse
from html.parser import HTMLParser
from pathlib import Path

# 修复 Windows 控制台 GBK 编码问题
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False

# ════════════════════════════════════════════════════════════
# 配置
# ════════════════════════════════════════════════════════════

OUTPUT_DIR = Path(__file__).parent

DEFAULT_ICON = "https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/svg/homarr.svg"

# Homarr dashboard-icons 常见应用映射（应用名关键词 → 图标文件名）
HOMARR_ICONS = {
    "github": "github.svg",
    "gitlab": "gitlab.svg",
    "docker": "docker.svg",
    "python": "python.svg",
    "java": "java.svg",
    "linux": "linux.svg",
    "nginx": "nginx.svg",
    "redis": "redis.svg",
    "mysql": "mysql.svg",
    "postgresql": "postgresql.svg",
    "mongodb": "mongodb.svg",
    "elasticsearch": "elasticsearch.svg",
    "kibana": "kibana.svg",
    "grafana": "grafana.svg",
    "prometheus": "prometheus.svg",
    "jenkins": "jenkins.svg",
    "ansible": "ansible.svg",
    "terraform": "terraform.svg",
    "kubernetes": "kubernetes.svg",
    "helm": "helm.svg",
    "vscode": "vscode.svg",
    "chrome": "chrome.svg",
    "firefox": "firefox.svg",
    "edge": "edge.svg",
    "safari": "safari.svg",
    "slack": "slack.svg",
    "discord": "discord.svg",
    "telegram": "telegram.svg",
    "wechat": "wechat.svg",
    "qq": "qq.svg",
    "weibo": "weibo.svg",
    "bilibili": "bilibili.svg",
    "youtube": "youtube.svg",
    "netflix": "netflix.svg",
    "spotify": "spotify.svg",
    "twitter": "twitter.svg",
    "facebook": "facebook.svg",
    "instagram": "instagram.svg",
    "linkedin": "linkedin.svg",
    "reddit": "reddit.svg",
    "stackoverflow": "stackoverflow.svg",
    "wikipedia": "wikipedia.svg",
    "google": "google.svg",
    "baidu": "baidu.svg",
    "aliyun": "aliyun.svg",
    "tencent": "tencentcloud.svg",
    "huawei": "huawei.svg",
    "aws": "aws.svg",
    "azure": "azure.svg",
    "cloudflare": "cloudflare.svg",
    "homarr": "homarr.svg",
    "plex": "plex.svg",
    "jellyfin": "jellyfin.svg",
    "emby": "emby.svg",
    "sonarr": "sonarr.svg",
    "radarr": "radarr.svg",
    "transmission": "transmission.svg",
    "qbittorrent": "qbittorrent.svg",
    "pihole": "pi-hole.svg",
    "adguard": "adguard-home.svg",
    "n8n": "n8n.svg",
    "homeassistant": "home-assistant.svg",
    "openwrt": "openwrt.svg",
    "proxmox": "proxmox.svg",
    "truenas": "truenas.svg",
    "unraid": "unraid.svg",
    "synology": "synology.svg",
    "minio": "minio.svg",
    "nextcloud": "nextcloud.svg",
    "vaultwarden": "vaultwarden.svg",
    "bitwarden": "bitwarden.svg",
    "traefik": "traefik.svg",
    "caddy": "caddy.svg",
    "portainer": "portainer.svg",
    "wireguard": "wireguard.svg",
    "tailscale": "tailscale.svg",
}
HOMARR_ICON_BASE = "https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/svg/{icon}"

# 请求间隔（秒）
REQUEST_DELAY = 0.3

# 需要跳过的 URL 模式
SKIP_PATTERNS = [
    r'^chrome://',
    r'^edge://',
    r'^about:',
    r'^javascript:',
]

# Excel 列名定义
COL_URL = "URL"
COL_NAME = "名称"
COL_ICON = "图标URL"
COL_BOARD = "Board名称"
COL_GROUP = "分组"
COL_STATUS = "状态"
COL_NOTE = "备注"

# 状态值
STATUS_PENDING = ""
STATUS_ALIVE = "可用"
STATUS_DEAD = "死链"
STATUS_SUCCESS = "已导入"
STATUS_FAILED = "失败"


# ════════════════════════════════════════════════════════════
# 工具函数
# ════════════════════════════════════════════════════════════

def should_skip(url):
    """判断 URL 是否应该跳过"""
    for pattern in SKIP_PATTERNS:
        if re.match(pattern, url, re.IGNORECASE):
            return True
    return False


def extract_domain(url):
    """从 URL 中提取域名"""
    try:
        parsed = urlparse(url)
        return parsed.hostname
    except Exception:
        return None


def guess_name_from_url(url):
    """从 URL 域名猜测网站名称"""
    domain = extract_domain(url)
    if not domain:
        return ""
    # 去掉常见前缀 www.
    name = re.sub(r'^(www\.)?', '', domain)
    # 去掉 TLD
    name = re.sub(r'\.\w{2,}$', '', name)
    # 首字母大写
    return name.capitalize()


def check_url_alive(url, timeout=3):
    """检测链接是否有效"""
    try:
        req = urllib.request.Request(url, method='HEAD')
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)')
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status < 400
    except Exception:
        try:
            req = urllib.request.Request(url, method='GET')
            req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)')
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status < 400
        except Exception:
            return False


def get_favicon_direct(url, timeout=5):
    """获取网站的 favicon.ico"""
    try:
        parsed = urlparse(url)
        scheme = parsed.scheme or 'https'
        netloc = parsed.hostname or ''
        if parsed.port:
            netloc += f":{parsed.port}"
        if not netloc:
            return None

        favicon_url = f"{scheme}://{netloc}/favicon.ico"
        req = urllib.request.Request(favicon_url, method='GET')
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)')

        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                content_type = resp.headers.get('Content-Type', '')
                data = resp.read(50000)
                if len(data) > 100 and (
                    'image' in content_type or 'octet' in content_type
                    or data[:4] in [b'\x89PNG', b'\xff\xd8\xff\xd8', b'GIF8']
                    or b'<svg' in data[:500] or b'<?xml' in data[:100]
                ):
                    return favicon_url
        except urllib.error.URLError as e:
            if 'SSL' in str(e) or 'certificate' in str(e).lower():
                import ssl
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                    content_type = resp.headers.get('Content-Type', '')
                    data = resp.read(50000)
                    if len(data) > 100:
                        return favicon_url
    except Exception:
        pass
    return None


def get_icon_url_quick(url, name):
    """
    快速图标匹配（不发起 HTTP 请求），用于 enrich 阶段。
    1. Homarr dashboard-icons 关键词匹配
    2. 构造 favicon URL
    3. 默认图标
    """
    if name:
        name_lower = name.lower()
        for keyword, icon_file in HOMARR_ICONS.items():
            if keyword in name_lower:
                return HOMARR_ICON_BASE.format(icon=icon_file)

    try:
        parsed = urlparse(url)
        scheme = parsed.scheme or 'https'
        netloc = parsed.hostname or ''
        if parsed.port:
            netloc += f":{parsed.port}"
        if netloc:
            return f"{scheme}://{netloc}/favicon.ico"
    except Exception:
        pass

    return DEFAULT_ICON


class _IconLinkParser(HTMLParser):
    """解析 HTML 中的 <link> 标签，提取图标 URL 及分辨率"""
    def __init__(self):
        super().__init__()
        self.icons = []

    def handle_starttag(self, tag, attrs):
        if tag != 'link':
            return
        d = dict(attrs)
        rel = (d.get('rel') or '').lower()
        href = d.get('href')
        if not href:
            return
        sizes = d.get('sizes', '')

        if 'icon' in rel or 'apple-touch-icon' in rel:
            w = 0
            if sizes and sizes.lower() != 'any':
                try:
                    w = int(sizes.split('x')[0])
                except (ValueError, IndexError):
                    pass
            if href.lower().endswith('.svg'):
                score = 100000 + w
            elif 'apple-touch-icon' in rel:
                score = 50000 + w
            else:
                score = w
            self.icons.append((score, href))


def sniff_icon_from_html(url, timeout=5):
    """通过解析网页源码嗅探图标资源"""
    try:
        req = urllib.request.Request(url, method='GET')
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)')
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content_type = resp.headers.get('Content-Type', '')
            if 'html' not in content_type and 'xhtml' not in content_type:
                return None
            data = resp.read(100000)
            try:
                html = data.decode('utf-8', errors='replace')
            except Exception:
                html = data.decode('latin-1', errors='replace')

        parser = _IconLinkParser()
        parser.feed(html)

        if not parser.icons:
            return None

        parser.icons.sort(key=lambda x: x[0], reverse=True)
        icon_path = parser.icons[0][1]

        if icon_path.startswith('//'):
            scheme = urlparse(url).scheme or 'https'
            return f"{scheme}:{icon_path}"
        elif icon_path.startswith('/'):
            parsed = urlparse(url)
            netloc = parsed.hostname or ''
            if parsed.port:
                netloc += f":{parsed.port}"
            return f"{parsed.scheme or 'https'}://{netloc}{icon_path}"
        elif not icon_path.startswith(('http://', 'https://')):
            base = url.rsplit('/', 1)[0]
            return f"{base}/{icon_path}"
        return icon_path

    except Exception:
        return None


def get_icon_url(url, name):
    """
    多级图标策略（含 HTTP 请求），用于导入阶段：
    1. Homarr dashboard-icons 关键词匹配
    2. 解析网页源码嗅探图标
    3. 网站 favicon.ico
    4. 默认图标
    """
    if name:
        name_lower = name.lower()
        for keyword, icon_file in HOMARR_ICONS.items():
            if keyword in name_lower:
                return HOMARR_ICON_BASE.format(icon=icon_file)

    sniffed = sniff_icon_from_html(url)
    if sniffed:
        return sniffed

    favicon = get_favicon_direct(url)
    if favicon:
        return favicon

    return DEFAULT_ICON


def clean_name(name, max_len=30):
    """智能清理应用名称"""
    name = name.strip()
    original = name

    chinese_suffixes = [
        "官方网站", "官网", "教程", "文档", "下载", "登录", "首页",
        "中文网", "中文版", "正式版", "最新版", "完整版",
        "是什么", "怎么做", "怎么用", "入门", "学习",
    ]
    for suffix in chinese_suffixes:
        if name.endswith(suffix) and len(name) > len(suffix) + 2:
            name = name[:-len(suffix)].strip()
            break

    if len(name) > 25:
        for sep in [' - ', ' — ', ' | ', ' _ ', '–', '—']:
            if sep in name:
                parts = name.split(sep, 1)
                if len(parts[0].strip()) >= 3 and len(parts[0].strip()) <= 30:
                    name = parts[0].strip()
                    break

    if len(name) > 25:
        for left, right in [('(', ')'), ('（', '）'), ('[', ']')]:
            if left in name and right in name:
                start = name.find(left)
                end = name.find(right, start)
                if end > start:
                    bracket_content = name[start:end+1]
                    if len(bracket_content) > len(name) * 0.3:
                        name = (name[:start] + name[end+1:]).strip()
                        break

    if len(name) > max_len:
        name = name[:max_len].rstrip()
        if ' ' in name:
            last_space = name.rfind(' ')
            if last_space > max_len * 0.6:
                name = name[:last_space]

    return name or original[:max_len] or "Untitled"


# ════════════════════════════════════════════════════════════
# Excel 读写
# ════════════════════════════════════════════════════════════

INSTRUCTIONS_TEXT = """
通用书签 → Homarr 导入工具 — 使用说明
─────────────────────────────────────

Homarr 配置（导入前必填）:
  Homarr URL:
  API Key:

工作流程:
  1. 准备数据: 在"数据"工作表中填写 URL（必填）和名称（可选）
  2. 运行 enrich: python import_to_homarr.py <此文件> --enrich
     → 自动检测 URL 可用性、匹配图标、补充缺失名称
  3. 填写 Homarr 配置: 在上方填入 Homarr URL 和 API Key
  4. 填写分组: 在"数据"工作表中填写"Board名称"和"分组"列
     → Board 名称必须是 Homarr 中已存在的英文 slug（如 workbench、resources）
     → 提示: 同类网站可拖动单元格快速填充
  5. 运行导入: python import_to_homarr.py <此文件> --import
     → 按 Board 分组导入，状态回写到此表
  6. 重试失败: python import_to_homarr.py <此文件> --retry

列说明:
  URL        网站地址（必填），如 https://github.com
  名称       网站名称（可选），为空时自动从域名猜测
  图标URL    图标地址（enrich 自动填充）
  Board名称  Homarr 面板的英文 slug（用户填写），如 workbench
  分组       面板内的分组名称（用户填写），如 开发工具
  状态       导入状态（自动记录）: 可用/死链/已导入/失败
  备注       补充说明或错误信息（自动记录）

注意:
  - Homarr API 的 Board 名称不支持中文，请使用英文 slug
  - 可通过 Homarr 设置页面查看已有 Board 的 slug
  - 导入支持断点续传，可多次运行 --import
"""


def create_excel_with_instructions(filepath, rows):
    """创建包含说明页和数据页的 Excel 文件"""
    wb = openpyxl.Workbook()

    # ─ 说明页 ──
    ws_info = wb.active
    ws_info.title = "说明"
    for i, line in enumerate(INSTRUCTIONS_TEXT.strip().split('\n'), 1):
        ws_info.cell(row=i, column=1, value=line)
    ws_info.column_dimensions['A'].width = 80

    # ── 数据页 ──
    ws_data = wb.create_sheet(title="数据")

    # 表头
    headers = [COL_URL, COL_NAME, COL_ICON, COL_BOARD, COL_GROUP, COL_STATUS, COL_NOTE]
    for col, header in enumerate(headers, 1):
        cell = ws_data.cell(row=1, column=col, value=header)
        cell.font = Font(bold=True, color="FFFFFF", size=11)
        cell.fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")

    # 数据行
    for row_idx, row in enumerate(rows, 2):
        ws_data.cell(row=row_idx, column=1, value=row.get(COL_URL, ""))
        ws_data.cell(row=row_idx, column=2, value=row.get(COL_NAME, ""))
        ws_data.cell(row=row_idx, column=3, value=row.get(COL_ICON, ""))
        ws_data.cell(row=row_idx, column=4, value=row.get(COL_BOARD, ""))
        ws_data.cell(row=row_idx, column=5, value=row.get(COL_GROUP, ""))
        ws_data.cell(row=row_idx, column=6, value=row.get(COL_STATUS, ""))
        ws_data.cell(row=row_idx, column=7, value=row.get(COL_NOTE, ""))

    # 列宽
    ws_data.column_dimensions['A'].width = 55
    ws_data.column_dimensions['B'].width = 25
    ws_data.column_dimensions['C'].width = 50
    ws_data.column_dimensions['D'].width = 18
    ws_data.column_dimensions['E'].width = 16
    ws_data.column_dimensions['F'].width = 10
    ws_data.column_dimensions['G'].width = 30

    wb.save(filepath)
    return wb


def read_excel_data(filepath):
    """从 Excel 数据页读取所有行"""
    wb = openpyxl.load_workbook(filepath)
    ws = wb["数据"]
    rows = list(ws.iter_rows(values_only=True))
    wb.close()

    if not rows:
        return []

    headers = [str(h).strip() if h else "" for h in rows[0]]
    col = {h: i for i, h in enumerate(headers)}

    result = []
    for row_idx, row in enumerate(rows[1:], start=2):
        row_list = list(row)
        url = row_list[col.get(COL_URL, 0)]
        if not url:
            continue
        result.append({
            "row": row_idx,
            COL_URL: str(url).strip(),
            COL_NAME: str(row_list[col.get(COL_NAME, 1)] or "").strip(),
            COL_ICON: str(row_list[col.get(COL_ICON, 2)] or "").strip(),
            COL_BOARD: str(row_list[col.get(COL_BOARD, 3)] or "").strip(),
            COL_GROUP: str(row_list[col.get(COL_GROUP, 4)] or "").strip(),
            COL_STATUS: str(row_list[col.get(COL_STATUS, 5)] or "").strip(),
            COL_NOTE: str(row_list[col.get(COL_NOTE, 6)] or "").strip(),
        })

    return result


def update_excel_row(filepath, row_num, updates):
    """更新 Excel 中指定行的指定列"""
    wb = openpyxl.load_workbook(filepath)
    ws = wb["数据"]
    headers = [str(c.value).strip() if c.value else "" for c in ws[1]]
    col = {h: i + 1 for i, h in enumerate(headers)}

    for key, value in updates.items():
        if key in col:
            ws.cell(row=row_num, column=col[key], value=value)

    wb.save(filepath)
    wb.close()


# ════════════════════════════════════════════════════════════
# Homarr 配置（从 Excel 说明页读取）
# ════════════════════════════════════════════════════════════

def read_homarr_config(filepath):
    """从 Excel 说明页读取 Homarr 配置（URL 和 API Key）"""
    wb = openpyxl.load_workbook(filepath, read_only=True)
    ws = wb["说明"]
    url = ""
    api_key = ""
    for row in ws.iter_rows(max_col=2, values_only=True):
        if not row or not row[0]:
            continue
        text = str(row[0]).strip()
        val = str(row[1]).strip() if len(row) > 1 and row[1] else ""
        if not val and ":" in text:
            key_part, _, val_part = text.partition(":")
            val = val_part.strip()
            text_key = key_part
        else:
            text_key, _, _ = text.partition(":")
        if text_key.rstrip().endswith("URL") or text_key.rstrip().endswith("url"):
            if "Homarr" in text_key or "homarr" in text_key.lower():
                url = val
        elif text_key.rstrip().endswith("Key") or text_key.rstrip().endswith("key"):
            if "API" in text_key or "api" in text_key.lower():
                api_key = val
    wb.close()
    # 环境变量作为备选
    url = url or os.environ.get("HOMARR_URL", "")
    api_key = api_key or os.environ.get("HOMARR_API_KEY", "")
    return {"homarr_url": url, "homarr_api_key": api_key}


# ════════════════════════════════════════════════════════════
# Homarr API
# ════════════════════════════════════════════════════════════

def homarr_api(method, path, body=None, config=None):
    """调用 Homarr API"""
    if not config or not config.get("homarr_url") or not config.get("homarr_api_key"):
        raise Exception("未配置 Homarr 连接信息。请在 Excel 说明页中填写 Homarr URL 和 API Key。")

    url = config["homarr_url"].rstrip("/") + path
    data = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("ApiKey", config["homarr_api_key"])
    req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        raise Exception(f"HTTP {e.code}: {error_body}")
    except Exception as e:
        raise Exception(str(e))


def get_existing_boards(config):
    """获取 Homarr 中已有的面板列表（同时按 name 和 slug 索引）"""
    try:
        result = homarr_api("GET", "/api/boards", config=config)
        if isinstance(result, list):
            boards = {}
            for b in result:
                if b.get("name"):
                    boards[b["name"]] = b
                if b.get("slug") and b["slug"] != b.get("name"):
                    boards[b["slug"]] = b
            return boards
        return {}
    except Exception as e:
        print(f"  警告: 无法获取面板列表: {e}")
        return {}


def get_existing_apps(config):
    """获取 Homarr 中已有的应用列表（用于去重）"""
    try:
        result = homarr_api("GET", "/api/apps", config=config)
        if isinstance(result, list):
            return {app.get("href", ""): app for app in result if app.get("href")}
        return {}
    except Exception as e:
        print(f"  警告: 无法获取现有应用列表: {e}")
        return {}


# ════════════════════════════════════════════════════════════
# 步骤 1: Enrich — 解析 URL、检测可用性、匹配图标、补充名称
# ════════════════════════════════════════════════════════════

def enrich_excel(filepath):
    """
    解析 Excel 中的 URL，执行:
    1. 检测 URL 可用性
    2. 匹配图标 URL
    3. 补充缺失的名称
    结果回写到 Excel
    """
    if not HAS_OPENPYXL:
        print("错误: 需要安装 openpyxl: pip install openpyxl")
        return

    rows = read_excel_data(filepath)
    if not rows:
        print("错误: Excel 数据页中没有数据")
        return

    # 过滤掉已标记为死链的（除非强制）
    todo = [r for r in rows if r[COL_STATUS] not in (STATUS_DEAD, STATUS_SUCCESS)]
    skipped_dead = sum(1 for r in rows if r[COL_STATUS] == STATUS_DEAD)
    skipped_success = sum(1 for r in rows if r[COL_STATUS] == STATUS_SUCCESS)

    print(f"共 {len(rows)} 行，待处理 {len(todo)} 行"
          f"（跳过已标记死链 {skipped_dead}、已导入 {skipped_success}）")

    alive_count = 0
    dead_count = 0
    enriched_count = 0

    for i, row in enumerate(todo):
        url = row[COL_URL]
        name = row[COL_NAME]
        idx = i + 1
        total = len(todo)

        # 跳过无效 URL
        if should_skip(url):
            update_excel_row(filepath, row["row"], {
                COL_STATUS: STATUS_DEAD,
                COL_NOTE: "无效协议/地址",
            })
            dead_count += 1
            print(f"  [{idx}/{total}] [跳过] {url}")
            continue

        # 检测 URL 可用性
        print(f"  [{idx}/{total}] 检测: {url}", end="", flush=True)
        is_alive = check_url_alive(url)

        if not is_alive:
            update_excel_row(filepath, row["row"], {
                COL_STATUS: STATUS_DEAD,
                COL_NOTE: "链接不可达",
            })
            dead_count += 1
            print(" → 死链")
            continue

        # URL 可用
        alive_count += 1
        updates = {COL_STATUS: STATUS_ALIVE}

        # 补充名称
        if not name:
            name = clean_name(guess_name_from_url(url))
            updates[COL_NAME] = name
            enriched_count += 1

        # 匹配图标
        icon = get_icon_url_quick(url, name)
        updates[COL_ICON] = icon

        update_excel_row(filepath, row["row"], updates)
        print(f" → 可用" + (f", 名称: {name}" if not row[COL_NAME] else ""))

        time.sleep(REQUEST_DELAY)

    print(f"\n── Enrich 完成 ──")
    print(f"  可用: {alive_count}")
    print(f"  死链: {dead_count}")
    print(f"  补充名称: {enriched_count}")
    print(f"\n请在 Excel 中填写「Board名称」和「分组」列，然后运行 --import")


# ════════════════════════════════════════════════════════════
# 步骤 3: Import — 按 Board 分组导入
# ════════════════════════════════════════════════════════════

def import_from_excel(filepath, retry_only=False):
    """从 Excel 读取数据并执行导入"""
    if not HAS_OPENPYXL:
        print("错误: 需要安装 openpyxl: pip install openpyxl")
        return

    rows = read_excel_data(filepath)
    if not rows:
        print("错误: Excel 数据页中没有数据")
        return

    # 筛选待导入的行
    if retry_only:
        todo = [r for r in rows if r[COL_STATUS] in (STATUS_DEAD, STATUS_FAILED)]
        print(f"重试模式: {len(todo)} 个待重试项")
    else:
        todo = [r for r in rows if r[COL_STATUS] in ("", STATUS_ALIVE)]
        # 跳过未填写 Board 的
        no_board = [r for r in todo if not r[COL_BOARD]]
        todo = [r for r in todo if r[COL_BOARD]]
        if no_board:
            print(f"跳过 {len(no_board)} 行未填写 Board 名称")
        print(f"导入模式: {len(todo)} 个待导入项")

    if not todo:
        print("没有需要处理的项")
        return

    # 从 Excel 说明页读取 Homarr 配置
    try:
        config = read_homarr_config(filepath)
    except Exception as e:
        print(f"错误: 无法读取 Excel 配置: {e}")
        return

    if not config["homarr_url"] or not config["homarr_api_key"]:
        print("错误: 未配置 Homarr 连接信息")
        print("  请在 Excel「说明」工作表中填写 Homarr URL 和 API Key")
        return

    # 获取已有面板和应用
    existing_boards = get_existing_boards(config)
    existing_apps = get_existing_apps(config)

    if existing_boards:
        print(f"\n已有面板: {', '.join(existing_boards.keys())}")

    # 按 Board 分组
    board_groups = {}
    for row in todo:
        board = row[COL_BOARD]
        if board not in board_groups:
            board_groups[board] = []
        board_groups[board].append(row)

    success_count = 0
    fail_count = 0
    dead_count = 0

    for board_slug, items in board_groups.items():
        print(f"\n── 面板: {board_slug} ({len(items)} 项) ──")

        # 检查面板是否存在
        if board_slug not in existing_boards:
            print(f"  警告: 面板 '{board_slug}' 不存在，以下项将跳过:")
            for item in items:
                print(f"    - {item[COL_NAME] or item[COL_URL]}")
                update_excel_row(filepath, item["row"], {
                    COL_STATUS: STATUS_FAILED,
                    COL_NOTE: f"面板 '{board_slug}' 不存在",
                })
                fail_count += 1
            continue

        board_id = existing_boards[board_slug].get("id", "")

        for idx, item in enumerate(items):
            url = item[COL_URL]
            name = item[COL_NAME] or guess_name_from_url(url)
            group = item[COL_GROUP] or "默认"
            row_num = item["row"]

            print(f"  [{idx+1}/{len(items)}] {name}", end="", flush=True)

            # 重试模式下重新检测死链
            if retry_only and item[COL_STATUS] == STATUS_DEAD:
                if not check_url_alive(url):
                    print(" → 仍为死链，跳过")
                    dead_count += 1
                    continue
                # 死链恢复，更新状态
                update_excel_row(filepath, row_num, {COL_STATUS: STATUS_ALIVE})

            # 检测链接（非重试模式下对 ALIVE 状态跳过检测）
            if not retry_only and item[COL_STATUS] != STATUS_ALIVE:
                if not check_url_alive(url):
                    print(" → 死链")
                    update_excel_row(filepath, row_num, {
                        COL_STATUS: STATUS_DEAD,
                        COL_NOTE: "链接不可达",
                    })
                    dead_count += 1
                    continue

            # 获取图标（导入阶段使用完整策略）
            icon_url = get_icon_url(url, name)

            try:
                # 检查是否已有同名/同URL的应用
                app_id = None
                if url in existing_apps:
                    app_id = existing_apps[url].get("id")
                    print(f" → 复用 (id={app_id})", end="")
                else:
                    # 创建新应用
                    app_result = homarr_api("POST", "/api/apps", {
                        "name": clean_name(name)[:64],
                        "description": "",
                        "iconUrl": icon_url,
                        "href": url,
                        "pingUrl": "",
                    }, config=config)
                    app_id = app_result["appId"]
                    existing_apps[url] = {"id": app_id}
                    print(f" → 创建 (id={app_id})", end="")

                # 添加到面板
                homarr_api("POST", "/api/boards/items", {
                    "boardId": board_id,
                    "kind": "app",
                    "options": {"appId": app_id},
                    "integrationIds": [],
                }, config=config)

                update_excel_row(filepath, row_num, {
                    COL_STATUS: STATUS_SUCCESS,
                    COL_ICON: icon_url,
                    COL_NOTE: f"board={board_slug}, group={group}",
                })
                success_count += 1
                print(f" ✓")

            except Exception as e:
                error_msg = str(e)[:200]
                update_excel_row(filepath, row_num, {
                    COL_STATUS: STATUS_FAILED,
                    COL_NOTE: error_msg,
                })
                fail_count += 1
                print(f" ✗ {error_msg}")

            time.sleep(REQUEST_DELAY)

    print(f"\n── 导入完成 ──")
    print(f"  成功: {success_count}")
    print(f"  失败: {fail_count}")
    print(f"  死链: {dead_count}")


# ════════════════════════════════════════════════════════════
# 状态查看
# ════════════════════════════════════════════════════════════

def show_status(filepath):
    """显示 Excel 中的导入状态统计"""
    rows = read_excel_data(filepath)
    if not rows:
        print("Excel 中没有数据")
        return

    total = len(rows)
    status_counts = {}
    no_board = 0
    no_group = 0

    for row in rows:
        s = row[COL_STATUS] or "未检测"
        status_counts[s] = status_counts.get(s, 0) + 1
        if not row[COL_BOARD]:
            no_board += 1
        if not row[COL_GROUP]:
            no_group += 1

    print(f"数据总览: {total} 行")
    print(f"\n状态分布:")
    for status, count in sorted(status_counts.items()):
        print(f"  {status or '未检测'}: {count}")

    if no_board:
        print(f"\n未填写 Board 名称: {no_board} 行")
    if no_group:
        print(f"未填写分组: {no_group} 行")

    # 按 Board 分组统计
    board_stats = {}
    for row in rows:
        board = row[COL_BOARD] or "(未填写)"
        if board not in board_stats:
            board_stats[board] = {"total": 0, "success": 0, "failed": 0, "dead": 0, "other": 0}
        board_stats[board]["total"] += 1
        s = row[COL_STATUS]
        if s == STATUS_SUCCESS:
            board_stats[board]["success"] += 1
        elif s == STATUS_FAILED:
            board_stats[board]["failed"] += 1
        elif s == STATUS_DEAD:
            board_stats[board]["dead"] += 1
        else:
            board_stats[board]["other"] += 1

    print(f"\n按 Board 分组:")
    for board, stats in sorted(board_stats.items()):
        print(f"  {board}: {stats['total']} 项 "
              f"(成功 {stats['success']}, 失败 {stats['failed']}, "
              f"死链 {stats['dead']}, 待处理 {stats['other']})")


# ════════════════════════════════════════════════════════════
# 主入口
# ════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="通用书签 → Homarr 批量导入工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python import_to_homarr.py bookmarks.xlsx --enrich    解析并 enrich
  python import_to_homarr.py bookmarks.xlsx --import    执行导入
  python import_to_homarr.py bookmarks.xlsx --retry     重试失败项
  python import_to_homarr.py bookmarks.xlsx --status    查看状态

配置:
  在 Excel 文件的「说明」工作表中填写 Homarr URL 和 API Key
  也可通过环境变量 HOMARR_URL 和 HOMARR_API_KEY 设置
        """
    )
    parser.add_argument("excel", help="Excel 文件路径")
    parser.add_argument("--enrich", action="store_true", help="解析URL、检测可用性、匹配图标、补充名称")
    parser.add_argument("--import", dest="do_import", action="store_true", help="执行导入")
    parser.add_argument("--retry", action="store_true", help="重试失败/死链项")
    parser.add_argument("--status", action="store_true", help="查看导入状态")
    args = parser.parse_args()

    filepath = args.excel

    # 如果文件不存在，创建一个模板
    if not os.path.exists(filepath):
        if not HAS_OPENPYXL:
            print("错误: 需要安装 openpyxl: pip install openpyxl")
            return
        print(f"文件不存在，创建模板: {filepath}")
        create_excel_with_instructions(filepath, [])
        print("请在 Excel 中填写数据后重新运行")
        return

    if args.status:
        show_status(filepath)
        return

    if args.enrich:
        enrich_excel(filepath)
        return

    if args.do_import or args.retry:
        import_from_excel(filepath, retry_only=args.retry)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
