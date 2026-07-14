# Homarr Helper

一键将当前浏览页面添加到 [Homarr](https://github.com/homarr-labs/homarr) 导航面板的浏览器扩展。

## 功能

- 点击扩展图标，弹出编辑框，自动预填页面标题、网址和图标
- 所有字段均可手动修改后确认添加
- 自动记忆上次使用的面板，也可手动切换
- 支持 Chrome / Edge / Brave 等 Chromium 内核浏览器

## 安装

### 方式一：从 Release 加载（推荐）

1. 从 [Releases](../../releases) 页面下载最新 `homarr-helper-x.x.x.zip`
2. 解压到任意目录
3. 打开 `chrome://extensions/`，启用右上角「开发者模式」
4. 点击「加载已解压的扩展程序」，选择解压目录

### 方式二：从源码加载

```bash
git clone https://github.com/<your-username>/homarr-helper.git
```

然后在 `chrome://extensions/` 加载项目目录。

## 配置

首次安装后会自动打开设置页面，需要填写：

- **Homarr 服务器地址** — 例如 `http://192.168.18.18:7575`
- **API Key** — 在 Homarr 管理面板 → 工具 → API 中创建

点击「测试连接」确认通过后保存即可。

## 使用

1. 浏览任意网页
2. 点击浏览器工具栏上的 Homarr Helper 图标
3. 在弹出框中确认或修改应用名称、链接、图标
4. 选择目标面板，点击「添加」

## 开发

项目为纯 Manifest V3 扩展，无构建步骤，直接修改源文件后在扩展管理页刷新即可。

```
├── manifest.json        # 扩展清单
├── background.js        # Service Worker（API 调用）
├── popup.html / popup.js   # 弹出编辑框
├── options.html / options.js  # 设置页面
└── icon48.png / icon128.png   # 图标
```

## License

MIT
