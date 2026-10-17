# Changelog（更新日志）

本文件记录 Brightbean Studio 中文汉化版（`local-custom` 分支）的所有显著变更。

- 格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)
- 版本号遵循 [语义化版本（Semantic Versioning）](https://semver.org/lang/zh-CN/)
- 汉化版基线：上游 `brightbeanxyz/brightbean-studio` 官方仓库 `main` 分支
- 词典规模（v1.2.1）：短语 773 条 / 单词 161 条 / 词元 41 条
- 词典规模（v1.3.4）：短语 877 条 / 单词 207 条 / 词元 43 条
- 部署环境、服务器运维、1Panel 连通方法等运维事实统一以仓库外的《Brightbean运维手册.md》（`E:\外贸文件夹\Brightbean Studio\`）为准，勿写入本文
- 词典规模（v1.4.0）：短语 1031 条 / 单词 201 条 / 词元 90 条
- 词典规模（v1.7.0）：短语 1054 条 / 单词 201 条 / 词元 98 条
- 词典规模（v1.8.0）：短语 1416 条 / 单词 201 条 / 词元 113 条
- 词典规模（v1.9.0）：短语 1438 条 / 单词 201 条 / 词元 120 条
- 词典规模（v1.10.0）：短语 1478 条 / 单词 201 条 / 词元 121 条
- 词典规模（v1.10.1）：短语 1485 条 / 单词 204 条 / 词元 121 条
- 词典规模（v1.10.2）：短语 1485 条 / 单词 204 条 / 词元 121 条

## [1.10.2] - 2026-10-17

### 新增（Added）

- **zhcheck 增加 tokens 子串嵌入检测**：检测 tokens 段中「无词界锚定、会切碎更长英文词/蛇形标识符」的危险 token（如 `posts`→`create_posts`/`Reposts`、`members`→`memberships`、`title`→`titles`），随 `python manage.py zhcheck` 输出，提示应移入 words 段或加键值保护，从机制上预防残片回归。

### 部署注意（Deployment）

- 无数据库迁移；纯 zhcheck 工具增强，词典无变化。

## [1.10.1] - 2026-10-17

### 修复（Fixed）

- **API 密钥权限标识符误译**：`create_posts` / `edit_others_posts` / `approve_posts` 等 snake_case 权限 key 不再被 tokens 段 `posts → 帖子` 子串替换切碎，改为「键值相同」词条做精确匹配保护，权限标识符保持英文不翻译（权限不翻、描述可翻）。
- **onboarding 引导清单补整句**：`Connect social accounts` / `Link your Instagram, LinkedIn, or other platforms` / `Add team members to collaborate on content` 三条整句补词，替代此前靠 tokens 子串产生的 `other 个平台` 类残片。

### 新增（Added）

- **API 密钥权限描述整句**：`Create posts` / `Edit others posts` / `Publish directly` / `Manage social accounts` 四条 label 补词（描述可翻，权限 key 保留）。

### 部署注意（Deployment）

- 无数据库迁移；纯词典增量，随镜像部署生效。

## [1.10.0] - 2026-10-17

### 新增（Added）

- **残片检测命令 `zh_residue`**：回归上游模板文本节点、跑与中间件同一套 `translate_text`，检出「部分翻译造成的中英混杂残句」，并定位到 `文件:行号`（精确匹配优先，tokens 子串替换只作用于未整句命中的动态片段）。

### 修复（Fixed）

- **根治 33 处机械子串替换残片**：19 个 `zh_overrides/templates` 覆盖 + 17 处词典整句补词，消除 `monthly→个月ly`、`memberships→成员hips`、`title-only→标题-only` 等破坏性单词切碎，以及 `posts/members/workspaces/caption/title/social accounts/media assets` 等单词被切进长句的中英混杂问题。
- **zh_audit 跳过 HTML 实体**：`&middot;` / `&rsaquo;` / `&times;` 等不再被误报为「残留英文」。
- **漏翻补词**：登录页（Continue with Google→使用 Google 登录 等）、通知（发布失败/无匹配）、成员角色权限项（View analytics/Use inbox 等 7 项）、onboarding 引导、API 密钥提示、`401/403` 等 20+ 词条。

### 变更（Changed）

- tokens 段新增 `Issued by → 签发人`，与既有 `Invited by → 邀请人` 对齐。

### 部署注意（Deployment）

- 本次无新增数据库迁移；新增 19 个模板覆盖 + 词典增量，随镜像部署后生效，需在容器内执行 `python manage.py migrate` 之外无额外步骤。

## [1.9.0] - 2026-10-17

### 新增（Added）

- **汉化回归三重防护机制**（对翻译的过去、当前、未来结果负责）：
  - **译文异常检测命令 `zh_audit`**：全量扫描 `zh.json` 每个词条的译文质量，检出「空译文、译文含模板占位符、译文与原文相同（未翻译）、译文残留英文片段、译文异常缩短」五类问题，并为每条结果附带其在模板中的出现位置（`文件:行号` + 上下文行），便于人工用浏览器 F12 定位来源后判断改法。
  - **翻译快照回归测试 `test_translation_snapshot`**：冻结上游 `templates/**/*.html` 全部文本节点的翻译输出为基线（`zh_overrides/tests/fixtures/translation_snapshot.json`），改动 `zh.json` 后重跑即可捕获「误伤已有翻译」的回归；首次运行自动生成基线，之后只对「已有译文结果发生变化」判失败。
  - **部署前变更影响报告命令 `zh_diff`**：对比当前 `zh.json` 与指定旧版（`--baseline`），列出新增/修改/删除的词条，并扫出每条英文源在上游模板中的出现位置，作为部署前必审清单；不依赖 git CLI，适配本机无 git、走 gh REST API 的环境。

### 修复（Fixed）

- **删除 1 条孤儿词条**：`phrases` 段移除截断重复项 `Expected columns: date, time, platforms, caption, media`（精确匹配永不命中，全站仅完整版 `... first_comment` 被 CSV 导入页使用）。

### 部署注意（Deployment）

- 本次无新增数据库迁移，纯工具脚本 + 单条词典删除；部署后无需执行 `migrate`。
- 三个管理命令/回归测试随镜像部署后在生产容器内使用：`python manage.py zh_audit`、`python manage.py zh_diff --baseline <旧版 zh.json>`、`python -m pytest --ds=zh_overrides.test_settings zh_overrides/tests/test_translation_snapshot.py`（重新定基线只需删除该 fixtures 文件）。

## [1.8.0] - 2026-10-16

### 新增（Added）

- **LLM 批量补全汉化词条 417 条**：以「专名/品牌/平台名保英文、社媒行业术语沿用标准译法、已有词条一字不动」为约束，批量翻译回填上游模板中未覆盖的英文 UI 文案，词典规模从 1353 增至 1730 键，模板层精确翻译覆盖率由约 42% 提升至约 77%。
- **运行时漏翻收集机制**：新增 `zh_overrides/leak_collector.py`，在 `ZhLocalizationMiddleware` 翻译文本节点时捕获「词典完全未命中」的英文原文，经去重与过滤后追加写入本地 `leaks.jsonl`（不触碰生产数据库）；配套管理命令 `python manage.py zhleak` 导出漏翻清单、`--clear` 清空。默认关闭，用于部署后运行时精确补词，替代不可靠的静态扫描。

### 变更（Changed）

- **汉化机制硬化——子串替换收归 `tokens` 白名单**：`load_dictionary()` 与客户端 payload 生成改为 `phrases` 段只做整段精确匹配、不再参与子串替换，子串替换完全由 `tokens` 段承担（`middleware.py` / `payload_views.py` 同步修改）。从机制上杜绝「短词误伤更长英文词」的残片。
- **词典清洗**：`tokens` 段移除 22 个高危子串键（星期缩写 `Mon/Tue/Wed/Thu/Fri/Sat/Sun`、月份缩写 `Jan/Feb/…/Dec`、单词碎片 `post/user/member/workspace` 等），`AM/PM/hours/hour` 改为带空格边界；`phrases` 段删除 18 个与 `words` 完全重复的键；37 个带空格边界的动态拼接碎片键由 `phrases` 迁回 `tokens`，保证动态文案（如「Caption exceeds … character limit」「… days ago」）翻译不丢失。

### 修复（Fixed）

- **根治半中半英显示残片**：旧机制下短键做子串替换，导致 `Changes`→「更改s」、`Saved`→「保存d」、`Thumbnail`→「四mbnail」、`Remember`→「re成员」等破坏性误译；机制硬化 + 词典清洗后此类残片不再产生。

### 部署注意（Deployment）

- 本次无新增数据库迁移，纯静态词典与中间件逻辑变更。
- 漏翻收集默认关闭；如需收集，在 `.env` 增加 `ZH_LEAK_COLLECT_ENABLED=true`（可选 `ZH_LEAK_COLLECT_DIR=/某个可写目录`，留空则落到系统临时目录），收集后执行 `python manage.py zhleak` 导出，补词完成后关闭开关并 `python manage.py zhleak --clear` 清理。

## [1.7.0] - 2026-10-16

### 新增（Added）

- **文件夹自动候补排期（V2 定稿，24 小时滚动窗口）**：帖子编辑器文案区底栏「媒体库」旁新增「排期文件夹」入口，弹窗与现有媒体库弹窗同款外壳（640px 圆角卡片、标题居左+X、极简文案、只显示文件夹与可排期视频数量角标，不显示素材本身）。每个文件夹卡片左下角显示**排除已排期视频后的可排期数量**，空文件夹显示 0 并与非空文件夹以底色深浅区分。**单击**文件夹仅高亮选中、**双击**进入子文件夹（面包屑逐级返回），第一屏含「未分文件夹（根目录）」虚拟卡片；选定后底部按钮为「添加文件夹」（仅设定路径，不直接启动），点击后文件夹卡片替换文案编辑区的素材位（两者互斥不可共存），再点原生「加入队列」才正式生效，此时左侧「下一个可用时段/优先处理/立即/设置日期和时间」按钮置灰不可点；未勾选平台账号时行内红字提示。生效瞬间快照当前页面勾选的账号、文案/首评/Facebook 形态（默认普通视频）；系统每 10 分钟（1Panel 计划任务 `zh_auto_schedule --once`）扫描一次，把每个目标账号**未来 24 小时**内的空槽用监听文件夹内 FIFO 最前的合格视频（处理完成/时长合格/有文件；图片与未处理素材静默过滤；不含子文件夹）持续补满；跨手动操作的避让由统一槽位占位自动完成，批量写入改用 `bulk_create` 合并（450 条降至 ≤15 条 SQL）。消耗账本 `(账号,视频)` 唯一，发布失败/手动取消/一键清除/停用恢复/整单替换均不重发；断连或无队列账号保留在规则中、状态条列名，恢复后自动续上；监听文件夹被删时规则自动停用并提示重新选择；审批流工作区禁止开启。工作区设置→社交账号→「连接账号」左侧新增**唯一总开关**（**纯武装语义**：关闭仅停止后续补货，已排期任务保留，需到发布队列手动取消；重新开启需重新配置，不再自动恢复原排期）；发布队列页顶部按每次投递显示「自动 N」系统标签，两步确认一键清除该批未发帖子（已发布历史保留）。旁路表 `zh_overrides_auto_schedule_rule/_consumption/_scheduled_batch/_scheduled_batch_item`（迁移 0004），全部代码位于 `zh_overrides`，上游核心、模板与媒体库零改动；Admin 仅保留批次只读审计页，规则/账本不进后台。

### 变更（Changed）

- **自动候补排期窗口由 48 小时收窄为 24 小时**：减少对未来空槽的过度占用，避免一次性吃掉过长周期的发帖时段；配套总开关语义改为纯武装（见上）。

- **支持 Cloudflare R2 公开自定义域作为媒体主机**：`STORAGE_BACKEND=s3` 时 `zh_overrides/settings.py` 在覆盖层关闭 `AWS_QUERYSTRING_AUTH`（不再生成 1 小时签名 URL）与 `AWS_DEFAULT_ACL`（R2 不接受 canned ACL），改用 `S3_CUSTOM_DOMAIN`（如 `media.ysec.cn`）输出匿名、永久有效的媒体地址。媒体走独立主机，平台（Meta 等）服务器端异步回拉不再受签名 1 小时过期限制，也与应用域名的 WAF/AI bot 策略物理隔离。仅在 s3 后端生效，local 后端行为与上游完全一致、零变化。`.env.example` 双语补充 `S3_CUSTOM_DOMAIN` 说明。

### 修复（Fixed）

- **文件夹角标不显示数量**：旧查询 `folder_video_counts` 以「根目录」（`folder_id=None`）为基准再叠加 `folder__in`，条件自相矛盾，导致命名文件夹计数恒为 0；改由 `_completed_video_base()` 提供统一基准后再按文件夹过滤。同时把空文件夹角标由低对比（`text-stone-400 bg-black/30`）改为高对比（`text-white bg-black/50`），避免 10px 的「0」渲染在深色卡片上视觉不可见。
- **自动候补排期 0 入队完全静默、无法事后定位**：`run_rule` 的 6 个 return-0 分支补 `logger.info`（规则未启用/文件夹缺失/未武装/无可用账号/无空闲时段/已消费或无合格素材）；新增只读诊断函数 `explain_zero(rule)`；`queue` 视图在 0 入队时返回 `reason`，前端由静默跳转改为弹窗提示具体原因；补 4 个 0 入队边界测试。
- **社交账号页「自动排期」总开关脚本注入路径错误**：注入规则原先只命中 `/social-accounts` 根路径，导致总开关在部分路径下不渲染；已修正挂载范围（提交 `d6b5e985`）。
- **选中文件夹后顶部路径未回显「根目录」**：现正确显示为「媒体库 / 根目录」（提交 `fa1d7649`）。
- **补 4 条遗漏汉化的界面文案**：发布列表「文案」列的 `(no caption)`、发布失败提示 `The platform rejected this post.`（修复前显示为「这个平台 rejected 这篇帖子。」）、构思看板默认卡片的标题与副标题。

### 部署注意（Deployment）

- 新增迁移 `0005_auto_schedule_armed`（`zh_overrides` 增加 `auto_schedule_armed` 布尔字段）。镜像 `CMD` 直接是 gunicorn，**不会自动 migrate**，部署后需在容器内执行 `python manage.py migrate`。
- 关闭「自动排期」总开关不会取消已排期任务，仅停止后续补货；需到发布队列手动一键清除。

## [1.6.1] - 2026-10-13

### 变更（Changed）

- **租户控制台细节打磨**：左树组织架构默认折叠（平台根节点保持展开，展开状态本地记忆）；折叠三角加大加深；层级缩进加大（每级约 24px）、引导线改为更清晰的实线、组织行加粗；右侧操作说明栏上提与控制台顶栏齐平。
- **通用模式可新建/改名工作区**：通用模式下组织现在可以添加多个工作区（共享组织级 App，与原 Admin 行为一致），工作区面板新增「保存名称」；仅当实际填写工作区凭证时才拒绝（旧逻辑把改名/新建也一并拦截）。新建工作区表单按模式显示，通用模式只填名称。
- **删除警示与原 Admin 对齐**：删除组织/工作区的确认文案改为 Django Admin 删除确认页同款级联清单（将永久删除 N 个帖子/社交账号/成员关系/凭证等，中文展示），面板内同步显示红色影响提示并建议归档替代。

### 修复（Fixed）

- **修复控制台建租户产生重复组织的根因**：`create_tenant` 现在复用注册信号自动创建的默认组织/工作区并改名，保证一个邮箱只产生一个组织、一个工作区（旧防御分支在成员关系时序异常时会建第二个组织）。
- **防止租户首次 Google 登录生成重复身份/组织**：控制台建租户时补建已验证的 allauth `EmailAddress`（`SOCIALACCOUNT_EMAIL_AUTHENTICATION` 依赖它匹配老用户）；新增数据迁移 `0003` 为存量缺失邮箱记录的活跃用户幂等补建已验证主邮箱。线上由此产生的空壳「My Organization」可在控制台确认后删除。

## [1.6.0] - 2026-10-12

### 变更（Changed）

- **超管「租户配置矩阵」改为企业微信式层级控制台**：原功能维度的分散 Admin 菜单（建组织、建工作区、配凭证要跨菜单）整合为一站式「左树 + 右详情 + 操作说明」三栏页面（原 Admin 菜单保持不动，读写同一套数据表，无第二套数据）：
  - 左树按用户层级呈现：🔷 Brightbean 平台（超级管理员/公司层，含组织/工作区/账号统计与管理员入口）→ 📁 组织（树中只显示注册邮箱，通用/独立徽标右列对齐）→ 📁 工作区（共享/归档徽标、连接状态点）→ 平台账号叶子（前台 OAuth 授权后自动出现，未连接不显示）。分区标题「管理 / 组织架构」；任意节点悬停出 `⋯`（添加下级/改名/归档/删除/ID），折叠状态本地记忆、默认全展开。
  - 右侧详情按层级切换：组织面板（改名、模式、通用模式组织级 FB/IG 两对凭证、工作区列表、新建工作区就地展开）；工作区面板（独立模式 FB/IG App ID/Secret/测试员备注等宽对齐表单、保存并测试、归档/删除；通用模式显示共享锁定提示）；平台账号面板为只读自然状态（Page/IG ID、连接时间、Webhook 订阅、令牌、健康检查）。
  - 模式互斥规则继续由后端强制（通用=组织凭证全组织共享、独立=工作区只认自己、不回退默认）；独立→通用即时变形并提示保存生效，通用→独立保留二次确认。新建组织弹窗保留；三栏内部独立滚动且隐藏滚动条，页面无外层滚动。

### 修复（Fixed）

- **租户配置矩阵所有写操作保存后报 500**：动作视图重定向误用不存在的路由名 `zh_overrides:tenant-config`，任何保存/测试/归档/删除 POST 执行成功后均触发 `NoReverseMatch`；改为正确的 `admin:zh_overrides_tenant_config`，补超管 Client POST 302 回归测试。工作区保存后锚点定位到对应工作区面板。

## [1.5.0] - 2026-10-11

### 修复（Fixed）

- **租户配置矩阵控制台 CSP 合规化**：原实现使用内联脚本，在启用 CSP 策略的部署下会被拦截、导致控制台交互失效；改为 nonce 注入 + 事件委托绑定（提交 `4ae7c660`）。
- **通知页「全部标记为已读」报「出了点问题，请重试。」**：上游 `notifications.mark_all_read` 在处理 htmx POST 时直接调用了被 `@require_GET` 装饰的 `notification_drawer()`，POST 请求触发 405（数据库更新其实已成功，但前端收到错误 toast 且列表不刷新），且返回的抽屉模板与历史页列表容器不匹配。改为抽出无装饰器的 `_render_drawer()`，并按 `HX-Target` 分别返回历史列表 partial（`#notification-history-list`）或抽屉 partial（`#notification-drawer-content`）；补 2 个 htmx 回归测试。

### 新增（Added）

- **矩阵页「保存并测试」凭证探测**：租户配置矩阵的组织级与工作区级保存按钮旁新增「保存并测试凭证/测试」按钮，保存后用假授权码探测 Meta OAuth 换令牌端点验证 FB/IG App ID/Secret 是否真实有效（不产生任何授权或令牌）；正确凭证返回 code/redirect 类拒绝（并能顺带提示回调 URI 未登记），错误凭证返回应用身份拒绝，网络异常/未知响应一律判失败。说明栏新增第 ⑪ 节解释探测原理与边界。
- **超管「租户配置矩阵」控制台**：Admin 新增单页控制台（`/admin/zh_overrides/workspaceplatformcredential/tenant-config/`，仅超管），把原本分散在「用户/组织/工作区/平台凭证」多个 Admin 菜单的开通动作合并为一个页面：租户卡片折叠展开（支持搜索与全部展开/收起）、新建租户登录账号（密码可空=仅 Google SSO，自动 provision 组织+默认工作区并幂等补齐 Owner 成员关系）、通用/独立模式一键切换（前端即时锁定对侧输入区，后端按解析器同规则强制互斥）、独立模式下「+ 添加工作区」子级动态加行并逐行/整组保存、App 凭证明文显示、工作区归档（可逆默认）与强删（二次确认）、连接状态实时读取。
- 新增 `WorkspaceMeta` 旁路表（`zh_overrides_workspace_meta`，0002 迁移）：承载 Tester/Page ID/IG ID 等运营备注字段，矩阵页直接维护，台账单处化。
- 矩阵页右侧固定 1/4 宽独立滚动**操作说明栏**（模式规则、开租户 8 步流程、各凭据在 Meta 后台的获取位置、FB 9 项/IG 5 项权限清单、固定回调 URL 与两条共享 Webhook 口令、Tester 邀请路径、法律页/数据删除说明、开发模式与 Live 审核规则、常见错误码、安全提示），另带不占版面的**悬浮大纲**快速定位；以后开租户无需再翻外部文档。
- Admin 首页与左侧导航中「中文汉化与平台扩展」应用分组置顶，并注入「租户配置矩阵」入口（通过包装 `AdminSite.get_app_list` 实现，纯叠加不改上游）。
- 所有控制台写操作（建号/切模式/加工作区/归档/删除）写入 Django admin LogEntry 操作日志。
- **工作区级平台 App 凭证（Workspace-scoped platform credentials）**：新增旁路模型 `zh_overrides.WorkspacePlatformCredential`（独立表 `zh_overrides_workspace_platform_credential`，约束 `(workspace, platform)` 唯一，凭证经 `EncryptedJSONField` 加密），支持代理商形态下「一个组织（租户）的每个工作区使用各自独立的 Meta/平台开发者 App」。凭证解析按「租户 × 平台」两级模式判定：
  - **通用模式（组织级已配置）**：组织在原 Platform credentials（平台凭证）建有完整凭证行时，全组织工作区共享该 App，行为与上游 100% 一致，工作区凭证行即使存在也被忽略；
  - **独立模式（组织级未配置）**：系统只查该工作区自己的凭证行——已配置即用工作区专属 App，未配置即空配置（连接页卡片置灰不可点、不可发布），不向任何默认 App 回退；
  - 环境变量完整配置时仍为最高优先级（与上游一致）。
- Admin 后台新增 **工作区平台凭证（Workspace platform credentials）** 管理入口（超管专属，Django Admin 标准表单自动生成，无自定义模板）；原组织级 Platform credentials 入口保持不变。
- 全链路透传 `workspace_id`：OAuth 发起/回调（回调从签名 state 取工作区）/重连、发布引擎、数据分析、健康检查与令牌刷新、Webhook 订阅/退订、`diagnose_facebook` / `subscribe_webhooks` 管理命令、composer 的 Pinterest/TikTok 校验。
- Webhook 验签密钥全集（`resolve_app_secrets`）纳入工作区凭证行：多个独立 App 推送至同一回调端点时照常验签，再按 Page/IG 账号归属工作区的密钥二次复核；OAuth 回调与 Webhook 地址、验证口令各租户继续共用，无需细分。

### 变更（Changed）

- 解析器 `resolve_platform_credentials()` / `resolve_app_secret()` 新增可选参数 `workspace_id`（默认 `None`，旧调用行为不变）；连接页「已配置平台」集合改为按工作区计算（复用既有未配置遮罩模板，租户前端页面零模板改动）。
- `zh_overrides` 应用后台显示名由「中文模板覆盖层」改为「中文汉化与平台扩展」。

### 部署注意（Deployment）

- 随镜像 migrate 自动新建两张旁路表（工作区凭证、工作区备注）；无新增环境变量、无需改 docker-compose；服务器 `.env` 仍不得设置 `PLATFORM_FACEBOOK_*` / `PLATFORM_INSTAGRAM_*`（完整 env 配置会压掉组织与工作区凭证行）。
- 独立模式工作区更换 App 后，该工作区已连接账号的旧令牌失效，必须重新 OAuth 授权（令牌与签发 App 绑定）。
- 新增测试设置 `zh_overrides.test_settings`（内存 SQLite）：`DJANGO_SETTINGS_MODULE=zh_overrides.test_settings pytest zh_overrides`。

## [1.4.0] - 2026-10-03

### 新增（Added）

- **Django Admin 后台完整汉化**：中间件对 `/admin/` 路径临时激活 `zh-hans`（用 `translation.activate` + 保存/恢复，仅作用于 admin 请求，不影响主站 `|date:"M j"` 等显式日期格式），移除 admin 绕过，让 zh.json 词典也对后台生效。Django 官方 zh-hans 负责后台框架（登录、仪表板、按钮、分页、筛选、auth/allauth），zh.json 补充自定义应用名、模型名、字段标签、选项值。零上游改动：不改 `LANGUAGE_CODE`、不改任何上游 model 的 `verbose_name`。

### 修复（Fixed）

- 数据分析页互动率公式仍为英文（如 `(Reactions + Comments + Shares) ÷ Views. Not reported by Facebook.`）：19 个指标标签原先在 `words` 段（仅精确匹配），公式是拼接字符串故不命中；将指标标签全部移入 `tokens` 段（子串替换），并新增 `Not reported by` → `非由`。
- 工作区设置页「归档/删除工作区」说明文字、确认弹窗文字未汉化：补入对应短语。
- 发布页筛选按钮 `All Tags` / `All Posts`、日历发布确认弹窗 `Publish now?` / `Publish X selected posts now...`、创作页 Unsplash `Select photos to add` / `Add images` / `Use this frame` 等由 Alpine `x-text` 动态渲染的文案未汉化：补入短语/词元，由 `zh-client.js` 观察器在运行时翻译。
- 后台列表中 `Google` 被误译为 `执行ogle`：`Go`（后台「执行」按钮）原在 `phrases` 段会参与子串替换，误伤 `Google`；改为移入 `words` 段（仅精确匹配独立文本节点）。

## [1.3.6] - 2026-10-03

### 修复（Fixed）

- **数据分析页筛选时表格上方异常文字逐次累积（v1.3.5 修复未净，复发根治）**：v1.3.5 把多行 `{# #}` 注释改为单行时，新注释文本里又写了字面嵌套标记示例 `{# #}`——Django 单行注释遇到第一个 `#}` 即闭合，导致后半句「仅支持单行注释！ #}」作为纯文本渲染在 `#analytics-post-table` 容器**之前**；htmx 筛选切换（7D/30D/90D/全部时间、类型、排序、分页）统一用 `hx-swap="outerHTML"` 只替换容器本身，容器外的残留文本节点每换页多一份。修复：删除含嵌套标记的注释写法，改为不含任何字面标记的单行说明注释，并将注释移入交换容器内部（即便日后注释语法再误写，文本也在容器内随换页被整体替换）。已用 Django 5.1 词法分析器对比验证：修复前渲染输出含泄漏文本，修复后注释全部正确分词、容器前零可见文本节点。

## [1.3.5] - 2026-10-03

### 修复（Fixed）

- 数据分析页帖子表格上方异常文字逐次累积：`analytics/_post_table.html` 的文首说明注释跨了 3 行，而 Django `{# #}` 注释**仅支持单行**，多行时被当纯文本渲染；且该文本节点位于 `#analytics-post-table` 容器**之外**，htmx 筛选切换用 `outerHTML` 只替换容器，旧文本残留 + 新响应再插一份，每点一次「7D/30D/90D/全部时间」多一行。改为单行注释。
- 发布编辑页点击任意处整页卡死：`zh-client.js` 自 v1.0.0 起因 404 从未真正执行，v1.3.4 修复加载后首次运行即暴露缺陷——观察器同步处理变更，自身写入的翻译再次触发观察器（译文仍含 BrightBean 等拉丁字母可通过正则初筛），在发布页 Alpine 高频重绘下形成主线程风暴。改为 `requestAnimationFrame` 批处理 + 写入前断开观察器（写完再挂回），并对同一节点去重。

## [1.3.4] - 2026-10-03

### 修复（Fixed）

- **客户端汉化覆盖层从未生效（zh-client.js 404）**：构建期 `collectstatic` 使用上游 `config.settings.production`（其 `INSTALLED_APPS` 不含 `zh_overrides`），本应用 `static/` 目录从不被收集，线上 `/static/zh_overrides/zh-client.js` 恒 404，导致所有 JS 动态写入（Alpine `x-text`、发布页 `setMode()` 等）的英文无法翻译——发布编辑页切换「下一个可用时段/优先处理/立即/设置日期和时间」后按钮变回英文即此因。修复：`zh-client.js` 改由 Django 视图 `/zh-overrides/client.js` 直接按文件内容提供服务（与 `payload.js` 同源、内容哈希缓存一年），彻底绕开 `collectstatic`，不改上游 `Dockerfile`。
- 发布编辑页 split-button 双保险：中间件属性白名单新增 `data-label`/`data-action-label`，模式按钮文案在服务端即译好，JS `setMode()` 读出即为中文（不依赖客户端覆盖层时序）。

### 新增（Added）

- 词典扩充至短语 877 / 单词 207 / 词元 43，覆盖：团队成员页（邀请弹窗、组织/工作区角色、成员与邀请计数、邀请行「邀请人/剩余 N 天」）、客户门户页（邀请客户弹窗、客户计数）、API 密钥页两句描述、日历页（筛选器「— 全部」项、时区下拉 21 个城市名及「（工作区）」后缀、「N 项已选」）、数据分析页（指标 Views/Reach/Reactions/Shares/Link clicks、主图「指标 · 近 N 天」、免责声明动态句、delta 提示 title、空态文案）、组织设置默认时区下拉（25 个 IANA 常用时区中文化，`value` 属性不受影响、提交值不变）、相对时间单位（天/周/月/分钟/前）。
- 新增 `zh_overrides/templates/analytics/_post_table.html` 模板覆盖：帖子表格工具栏计数（N 篇帖子 · 近 N 天/全部时间）与分页（第 X / Y 页、共 N 条）直写中文——词典无法安全处理 ` of ` 类动态拼接；`drift-allowlist.json` 已登记去复数后缀与默认文案中译两处偏差。
- `zhcheck` 支持 `_added` 白名单：有意新增的纯中文模板（法律页）跳过漂移比对，命令恢复零问题退出，可继续作为自动化关卡。

## [1.3.3] - 2026-10-03

### 新增（Added）

- 注册闸门（叠加层 `zh_overrides/adapters.py`，经 `ACCOUNT_ADAPTER`/`SOCIALACCOUNT_ADAPTER` 挂载，不改上游）：邮箱+密码公开注册关闭，仅「持有效组织邀请」或「Google 授权（配置 `GOOGLE_AUTH_CLIENT_ID` 时）」可注册新账号；已有用户（含超级管理员）登录不受影响。

## [1.3.2] - 2026-10-03

### 新增（Added）

- `zh_overrides/settings.py` 支持 SMTP 465 隐式 SSL：新增 `EMAIL_USE_SSL` 开关，启用时自动关闭 `EMAIL_USE_TLS`（Django 中二者互斥），适配网易 163 邮箱（`smtp.163.com:465`）等不支持 587 STARTTLS 的发信服务；`.env.example` 双语补充该变量。

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
