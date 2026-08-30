# importToHomarr — 通用书签批量导入工具

一个独立的 Python 命令行工具，用于将任意来源的书签/收藏数据批量导入 [Homarr](https://github.com/homarr-labs/homarr) 导航面板。只要数据能整理成 Excel 表格（至少包含 URL 列），就可以使用本工具完成导入。

与浏览器扩展 [Homarr Helper](../../README.md) 互为补充：扩展适合日常单个添加，本工具适合一次性迁移大批量书签。

## 特性

- **来源无关** — 无论书签来自 Infinity、Chrome 导出、Pocket 还是任何地方，整理成 Excel 即可
- **自动检测** — 逐个检测 URL 可用性，标记死链，避免导入无效站点
- **自动补全** — 缺失的网站名称从域名推断；图标采用多级匹配策略（Homarr dashboard-icons 关键词 → 网页 `<link>` 嗅探 → favicon.ico → 默认图标）
- **Excel 驱动** — 全部状态回写 Excel，天然支持断点续传、人工核查与二次修正
- **配置内嵌** — Homarr 地址和 API Key 就写在 Excel 的「说明」工作表中，无需额外配置文件

## 环境要求

- Python 3.8+
- [openpyxl](https://pypi.org/project/openpyxl/)

```bash
pip install openpyxl
```

## 三步工作流

### 第 1 步：准备数据并 enrich

```bash
python tools/importToHomarr/import_to_homarr.py bookmarks.xlsx --enrich
```

如果 `bookmarks.xlsx` 不存在，脚本会自动生成带说明页的模板。在「数据」工作表中填入 URL（必填）和名称（可选）后，再次运行 `--enrich`：

- 逐行检测 URL 可用性，死链标记为「死链」
- 为缺失名称的行从域名推断网站名称
- 匹配图标 URL

### 第 2 步：人工填写配置与分组

打开 Excel：

1. 在「说明」工作表顶部填写 **Homarr URL** 和 **API Key**
2. 在「数据」工作表为每行填写 **Board名称** 和 **分组**

> **注意**：Homarr API 的 Board 名称即 slug，只支持 `^[A-Za-z0-9-_]*$`（英文、数字、连字符、下划线），**不支持中文**。已有的 Board slug 可在 Homarr 面板切换器中查看。

源数据通常有内聚性（同类网站相邻），拖动单元格即可快速批量填充。

### 第 3 步：执行导入

```bash
python tools/importToHomarr/import_to_homarr.py bookmarks.xlsx --import
```

按 Board 分组导入，每个应用创建后自动挂到对应面板，状态回写为「已导入」。可随时中断后重新运行，已导入的行会自动跳过。

## 其他命令

```bash
# 重试失败项 / 重新检测死链
python tools/importToHomarr/import_to_homarr.py bookmarks.xlsx --retry

# 查看导入状态统计（按 Board 分组汇总）
python tools/importToHomarr/import_to_homarr.py bookmarks.xlsx --status
```

## 状态说明

| 状态 | 含义 |
| --- | --- |
| （空） | 未处理 |
| 可用 | enrich 检测通过，等待导入 |
| 死链 | 链接不可达，导入时自动跳过 |
| 已导入 | 成功导入 Homarr |
| 失败 | 导入出错，备注列有错误信息，可 `--retry` 重试 |

## 注意事项

- 本工具**只会向已有 Board 添加应用**，不会自动创建 Board——请先在 Homarr 中建好英文 slug 的面板
- 同一 URL 的应用在 Homarr 中已存在时会直接复用，不会重复创建
- 请求间隔默认 0.3 秒，导入大量数据请耐心等待
- API Key 保存在 Excel 中，请勿将该 Excel 文件分享或提交到公开仓库
