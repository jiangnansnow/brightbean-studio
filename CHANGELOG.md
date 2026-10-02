# Changelog（更新日志）

本文件记录 Brightbean Studio 中文汉化版（`local-custom` 分支）的所有显著变更。

- 格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)
- 版本号遵循 [语义化版本（Semantic Versioning）](https://semver.org/lang/zh-CN/)
- 汉化版基线：上游 `brightbeanxyz/brightbean-studio` 官方仓库 `main` 分支
- 词典规模（v1.2.1）：短语 773 条 / 单词 161 条 / 词元 41 条
- 部署环境、服务器运维、1Panel 连通方法等运维事实统一以仓库外的《Brightbean运维手册.md》（`E:\外贸文件夹\Brightbean Studio\`）为准，勿写入本文

## [1.3.1] - 2026-10-02

### 修复（Fixed）

- 法律页面（隐私政策/服务条款/数据删除说明）联系电话由 `+86 178 9713 9713` 更新为 `+86 134 6991 1193`（共 6 处，`legal.html`、`data_deletion.html`）。

### 变更（Changed）

- `.env.example` 改为中英文双语注释（变量名与默认值不变），文首标注「本地 .env 仅影响调试、Meta 凭据走 Admin 后台、Webhook 令牌只能走服务器环境变量」三条关键事实。

## [1.3.0] - 2026-10-02

### 变更（Changed）

- **零侵入重构**：汉化层与法律页面不再修改任何上游文件。新增 `zh_overrides/settings.py`（经 `DJANGO_SETTINGS_MODULE=zh_overrides.settings` 环境变量启用，内部 `from config.settings.production import *` 后叠加 app/中间件/模板目录）与 `zh_overrides/urls.py`（继承上游路由后追加 `/privacy`、`/legal`、`/terms`、`/data-deletion`、`/zh-overrides/`）；`config/urls.py`、`config/settings/base.py` 还原为上游原版，此后 `git merge upstream/main` 对 `config/` 零冲突。
- 本文件由 `汉化版更新日志.md` 更名为 `CHANGELOG.md`，部署环境信息节迁至仓库外《Brightbean运维手册.md》。

### 部署注意（Deployment）

- 服务器 `.env` 必须新增 `DJANGO_SETTINGS_MODULE=zh_overrides.settings`；缺失该行时站点回退为上游英文版且法律页 404（运维手册已列为必备键）。

## [1.2.1] - 2026-10-01

对应提交：`dff561e`

### 变更（Changed）

- 语言切换按钮由左下角移至**页面右上角**固定显示，避免在窗口高度不足或存在嵌套滚动区域时按钮被裁切而无法使用。

## [1.2.0] - 2026-10-01

对应提交：`9890c5a`

### 新增（Added）

- UI 语言切换按钮：页面悬浮胶囊，中文页显示 `EN`、英文页显示 `中`，一键切换中/英文界面。
- 切换基于 Cookie（`zh_lang`，有效期一年）：选择英文后整站所有页面立即呈现未改动的上游英文原版，选择中文即恢复，无需重启服务。
- 英文模式下同时停用客户端动态汉化观察器，确保 JavaScript 动态内容也保持英文。
- `?setlang=en|zh` 链接动作：写入语言 Cookie 并重定向到干净 URL。

## [1.1.0] - 2026-10-01

对应提交：`8a08f6e`

### 新增（Added）

- 汉化总开关接入环境变量：在 `.env` 中设置 `ZH_LOCALIZATION_ENABLED=false` 并重启即可回退为英文上游，无需改代码、无需重新构建镜像。
- `.env.example` 新增汉化开关章节与用法说明。
- 单页调试旁路：任意页面 URL 追加 `?raw=1` 可查看未经汉化的原始页面，用于快速判断问题是否由汉化层引起。

## [1.0.1] - 2026-09-30

对应提交：`e0800f5`

### 修复（Fixed）

- 修复 `&#x27;` 等十六进制 HTML 字符引用不被识别、访问特定页面时触发 500 错误的问题。
- 修复 `Mon`–`Sun` 周几缩写在子串替换层误伤 `Monthly` 等英文单词的问题（移至整词匹配层）。
- 修复 `followers` 被子串替换破坏为“关注ers”的问题。

### 新增（Added）

- 共享媒体库页：文件类型筛选标签（图片/视频/GIF/文档）、上传者等词条。
- 日历页：`Changes Requested（需修改）`、`Rejected（已拒绝）`等状态筛选词条。
- 审批设置页：四个审批模式卡片标题及说明文字整页覆盖。
- 媒体库侧栏：文件夹、全部媒体、已加星标、搜索框、排序下拉等词条。

### 变更（Changed）

- `VIDEO`/`IMAGE`/`DOCUMENT` 文件类型徽标加入恒等映射，刻意保留英文显示。

## [1.0.0] - 2026-09-30

对应提交：`c843d9d`。首个可部署的完整汉化版本。

### 新增（Added）

- **客户端动态汉化层**：`MutationObserver` 监听 JavaScript/htmx 动态写入的内容并即时重译，解决页面加载后英文“回潮”问题；自动跳过编辑框，不干扰输入。
- 词典 JS 载荷视图（`/zh-overrides/payload.js`）：按内容哈希缓存一年，词典更新自动失效。
- 服务端中间件新增实体粘合（如 `Drag & drop` 被实体拆开时整串翻译）与大小写不敏感回退。
- 低频页面全量扫描补译：analytics（数据分析）、通知及通知偏好（21 类事件标签）、连接平台、API keys、客户门户、成员、onboarding（引导）、组织页。
- 日历顶栏全部下拉框、月份名称、视图名、警告条补译。
- compose（发帖器）全部 JS 错误串与编辑器动态状态串补译。

## [0.3.0] - 2026-09-30

对应提交：`c93add6`

### 新增（Added）

- composer（发帖器）、calendar（日历）、inbox（收件箱）三大核心模块页面汉化。

## [0.2.0] - 2026-09-30

对应提交：`441b4b6`

### 新增（Added）

- 词典驱动的汉化中间件：基于 `html.parser` 仅翻译文本节点，支持 `title`/`aria-label`/`placeholder` 等白名单属性。
- `zhcheck` 汉化漂移自检命令：自动对比整页覆盖模板与上游模板，发现漂移以非零退出码报警，可用于构建门禁。
- 有意偏差白名单（`drift-allowlist.json`）。
- 侧栏、设置、社交账号页第二批汉化。

## [0.1.0] - 2026-09-30

对应提交：`7dcd378`

### 新增（Added）

- 首个汉化试点：社交账号页整模板覆盖（列表页、账号卡片、状态徽标、发布时段网格）。

---

## 刻意不译的内容

以下内容按设计保留英文，不属于遗漏：

- 平台名与品牌词：TikTok、YouTube、Facebook、Instagram、LinkedIn、Bluesky、Mastodon、Trustpilot、Brightbean 等。
- 技术专名：Webhook、AT Protocol 等。
- 用户数据：工作区名称、用户名、邮箱、话题标签等。
- 时区城市名：Shanghai、Tokyo 等。
- 文件类型徽标：VIDEO / IMAGE / DOCUMENT。

## 上游同步策略

汉化层遵循“只新增、不改上游”原则：全部汉化代码位于独立的 `zh_overrides` 包内，上游模板、模型、迁移、JS、CSS 零改动；仅在 `config/settings/base.py` 与 `config/urls.py` 有纯追加式挂载。

更新流程：

```
git checkout main
git pull
git checkout local-custom
git rebase main
python manage.py zhcheck
重新构建并部署
```

未补译的词条只会显示英文，不会导致功能异常；新词条加入 `zh_overrides/zh.json` 即可恢复，且补译不阻塞上线。
