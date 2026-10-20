# Changelog

本文件记录 Homarr Helper 的版本变更。完整历史也发布在
[GitHub Releases](https://github.com/letmebe/homarr-helper/releases)。

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [1.1.1] - 2026-10-20

### Fixed

- 修复首次配置时点击「测试连接」成功后，目标面板下拉仍显示「请先填写服务器地址和 API Key」的问题，现在会自动填充面板列表。
  根因：测试连接的点击流程从未调用面板加载逻辑，此前依赖输入框失焦事件间接触发；而按需授权的引入使该路径在未授权时提前返回。

## [1.0.0] - 2026-08-30

### Added

- 首个正式版本：点击扩展图标将当前页面一键添加到 Homarr 面板，标题、网址、站点图标自动预填。
- 目标面板可手动切换，并记忆上次使用的面板。
- 主机访问权限按需申请，仅限用户填写的服务器地址，不再申请全站访问权限。
- 中英文双语界面，根据浏览器语言自动切换。
- 新标签页跳转到用户配置的 Homarr 面板。
- 附带 `importToHomarr` 命令行工具，支持从表格批量导入书签到面板。

[1.1.1]: https://github.com/letmebe/homarr-helper/releases/tag/v1.1.1
[1.0.0]: https://github.com/letmebe/homarr-helper/releases/tag/v1.0.0
