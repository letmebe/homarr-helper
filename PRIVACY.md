# Privacy Policy / 隐私政策

Homarr Helper（下称"本扩展"）不收集、不上传、不出售任何用户数据给开发者或任何第三方。

**English**

Homarr Helper does not collect, transmit, or share any personal data with the developer or any third party. There is no analytics, no telemetry, and no remote server operated by the developer.

## 数据存储 / Data Storage

- **服务器地址、API Key、目标面板 ID、界面语言偏好**：仅保存在浏览器本地的 `chrome.storage.local` 中，不会离开你的设备。
- The Homarr server URL, API key, target board ID and language preference are stored locally in your browser via `chrome.storage.local`. They never leave your device except when sent to the server you configured yourself.

## 数据传输 / Data Transmission

- 本扩展唯一会发出的网络请求，是发往**你自己填写的 Homarr 服务器地址**（通常是局域网内自建实例）。请求内容仅限：面板列表查询、以及你确认添加的应用名称/链接/图标 URL。
- 页面标题和 URL 从当前标签页读取，仅用于预填添加表单，不会被发送到除你的 Homarr 服务器以外的任何地方。
- The only network requests made by this extension go to the self-hosted Homarr server address that you configure yourself. Requests contain board listings and the app name/URL/icon you choose to add. The current tab's title and URL are read only to pre-fill the add form.

## 权限说明 / Permissions

- `activeTab` / `scripting`：点击扩展图标时读取当前页面的标题、URL 和图标，用于预填表单。
- `storage`：本地保存你的配置。
- `contextMenus`：在扩展图标右键菜单中提供设置入口。
- 主机访问权限采用**按需申请**（optional host permissions）：只在你保存/测试连接时，针对你填写的那个服务器地址向浏览器申请授权，可随时在浏览器扩展设置中撤销。
- Host access is requested on demand, only for the exact origin you enter, and can be revoked at any time from the browser's extension settings.

## 第三方服务 / Third Parties

无。本扩展不包含任何第三方统计、广告或跟踪代码。No third-party analytics, ads or trackers.

## 商标声明 / Trademark Notice

Homarr Helper 为独立社区作品，与 Homarr 项目（homarr-labs）无隶属、合作或背书关系。"Homarr" 名称仅用于指代本扩展所对接的目标软件，该名称及官方标志的一切权利归其各自所有者；本扩展图标为原创设计，未使用官方标志。
Homarr Helper is an independent community project, not affiliated with, endorsed by, or sponsored by the Homarr project (homarr-labs). "Homarr" is used only to identify the software this extension integrates with; all rights in the Homarr name and logo belong to their respective owners. The extension icon is an original design.

## 联系方式 / Contact

如对隐私有疑问，请通过本项目的 GitHub Issues 联系：<https://github.com/letmebe/homarr-helper/issues>
