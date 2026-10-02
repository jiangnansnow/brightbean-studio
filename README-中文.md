<p align="center">
  <a href="https://github.com/brightbeanxyz/brightbean-studio">
    <img src=".github/assets/brightbean-studio-logo.webp" alt="BrightBean Studio" width="280">
  </a>
</p>

<p align="center">
  <strong>面向创作者、代理机构和中小企业的开源社媒管理平台。</strong>
</p>

<p align="center">
  <a href="https://github.com/brightbeanxyz/brightbean-studio/actions/workflows/ci.yml"><img src="https://github.com/brightbeanxyz/brightbean-studio/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-AGPL--3.0-blue.svg" alt="License: AGPL-3.0"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.12%2B-blue.svg" alt="Python 3.12+"></a>
  <a href="https://www.djangoproject.com/"><img src="https://img.shields.io/badge/Django-5.x-green.svg" alt="Django 5.x"></a>
</p>

<p align="center">
  <a href="https://brightbean.xyz/studio/"><img src="https://img.shields.io/badge/Free%20hosted%20version-brightbean.xyz%2Fstudio-FFB300?style=for-the-badge" alt="Free hosted version at brightbean.xyz/studio"></a>
</p>

---

## 关于 BrightBean Studio

BrightBean Studio 是一个开源、可自托管的社媒管理平台，专为创作者、代理机构和中小企业打造。它具备 Sendible、SocialPilot 或 ContentStudio 的全部能力，但完全免费，没有按席位、按渠道或按工作区收费的限制。你可以在一个多工作区仪表盘中，对 Facebook、Instagram、LinkedIn、TikTok、YouTube、Pinterest、Threads、Bluesky、Google 商家资料（Google Business Profile）、Mastodon 和 DEV.to 的内容进行策划、撰写、排期、审批、发布与监控。

它适合在一个屋檐下管理大量客户账号、希望拥有自己社媒技术栈、而不愿每月向 SaaS 厂商支付 100–300 美元的团队。所有功能对所有用户开放。没有付费档位，没有功能门槛，没有诱导加购。

官方在 [brightbean.xyz/studio](https://brightbean.xyz/studio/) 提供免费托管版本。你也可以通过 Heroku、Render 或 Railway 的一键按钮自行部署，或使用 Docker 在自己的 VPS 上运行，也可以在本地运行。所有平台集成都使用你自己的开发者凭证，直接对接官方第一方 API，因此不存在中间商、没有厂商锁定，也没有第三方处于你和你的数据之间。

## 功能特性

| | |
|---|---|
| **多工作区与团队** | 无限层级的组织 → 工作区 → 成员。精细化 RBAC（基于角色的访问控制），支持自定义角色、邀请函，以及面向外部协作者的独立 Client（客户）角色。 |
| **内容编辑器** | 富文本编辑器，支持按平台分别设置文案/媒体覆盖、版本历史、可复用模板、内容分类与标签，以及看板形式的创意板。 |
| **日历与排期** | 可视化日历，支持为每个账号设置每周重复的发布时段，以及命名队列，可自动将帖子分配到下一个可用时段。 |
| **发布引擎** | 直接对接第一方 API（无聚合中间商），自动重试、按账号追踪速率限制，并提供 90 天发布审计日志。 |
| **审批工作流** | 可配置阶段（无 / 可选 / 内部 / 内部 + 客户），支持楼中楼式的内部与外部评论、提醒，以及完整审计轨迹。 |
| **统一社交收件箱** | 将来自每个已连接平台的评论、@提及、私信和评价汇集一处，支持情感分析、任务指派、楼中楼回复和历史回填。 |
| **数据分析** | 通过每个平台的原生 API 获取单帖及渠道层级的表现数据，提供 KPI 卡片、7/30/90 天趋势图表，以及可按浏览量、互动量、粉丝增长、触达量和观看时长排序的全部帖子表格。 |
| **媒体库** | 支持组织级和工作区级媒体库，含嵌套文件夹、自动生成的平台优化版本、替代文本（alt text），并在编辑器内内置 Unsplash 正版图库搜索。 |
| **客户门户** | 免密码的 30 天魔法链接访问，客户无需注册账号即可批准或驳回帖子。 |
| **通知** | 支持站内、邮件和 Webhook 投递，并可由每位用户针对每类事件设置偏好。 |
| **安全与运维** | 加密的令牌与凭证存储、Google 单点登录（SSO）、Sentry 支持，以及 14 天可逆的组织删除宽限期。双因素认证（TOTP）已在路线图上。 |
| **利于白标** | 可按工作区设置品牌（Logo、配色），并为话题标签、首条评论和发布模板设置工作区默认值。 |

### 快速一览

<table>
  <tr>
    <td colspan="2"><img src=".github/assets/BrightBean%20Studio%20Calendar.webp" alt="Calendar view"><br><sub><b>可视化日历</b> — 拖拽式排期，支持重复时段与队列。</sub></td>
  </tr>
  <tr>
    <td width="50%"><img src=".github/assets/BrightBean%20Studio%20Post%20Editor.webp" alt="Post editor"><br><sub><b>帖子编辑器</b> — 支持按平台覆盖与预览的编辑器。</sub></td>
    <td width="50%"><img src=".github/assets/BrightBean%20Studio%20Idea%20Kanban%20Board.webp" alt="Idea kanban board"><br><sub><b>创意板</b> — 用看板工作流跟踪你所有的发帖灵感。</sub></td>
  </tr>
  <tr>
    <td width="50%"><img src=".github/assets/BrightBean%20Social%20Media%20Platforms.webp" alt="Connected platforms"><br><sub><b>连接任意平台</b> — 10+ 第一方集成，无聚合中间商。</sub></td>
    <td width="50%"><img src=".github/assets/BrightBean%20Studio%20Analytics.webp" alt="Analytics dashboard"><br><sub><b>表现分析</b> — 单帖与渠道层级指标，含 KPI 卡片与趋势图表。</sub></td>
  </tr>
</table>

## 支持的平台

| 平台 | 发布 | 评论 | 私信 | 洞察 |
|---|:---:|:---:|:---:|:---:|
| <img src="https://cdn.simpleicons.org/facebook" width="16" height="16"> Facebook | ✓ | ✓ | ✓ | ✓ |
| <img src="https://cdn.simpleicons.org/instagram" width="16" height="16"> Instagram | ✓ | ✓ | ✓ | ✓ |
| <img src="https://cdn.simpleicons.org/instagram" width="16" height="16"> Instagram（直连） | ✓ | ✓ | ✓ | ✓ |
| <img src="https://api.iconify.design/logos/linkedin-icon.svg" width="16" height="16"> LinkedIn（个人） | ✓ | ✓ | — | ✓ |
| <img src="https://api.iconify.design/logos/linkedin-icon.svg" width="16" height="16"> LinkedIn（公司主页） | ✓ | ✓ | — | ✓ |
| <img src="https://cdn.simpleicons.org/tiktok" width="16" height="16"> TikTok | ✓ | — | — | ✓ |
| <img src="https://cdn.simpleicons.org/youtube" width="16" height="16"> YouTube | ✓ | ✓ | — | ✓ |
| <img src="https://cdn.simpleicons.org/pinterest" width="16" height="16"> Pinterest | ✓ | — | — | ✓ |
| <img src="https://cdn.simpleicons.org/threads" width="16" height="16"> Threads | ✓ | ✓ | — | ✓ |
| <img src="https://cdn.simpleicons.org/bluesky" width="16" height="16"> Bluesky | ✓ | ✓ | — | — |
| <img src="https://api.iconify.design/logos/google-icon.svg" width="16" height="16"> Google 商家资料 | ✓ | — | — | ✓ |
| <img src="https://cdn.simpleicons.org/mastodon" width="16" height="16"> Mastodon | ✓ | ✓ | — | — |
| <img src="https://cdn.simpleicons.org/devdotto/000000" width="16" height="16"> DEV.to | ✓ | — | — | — |

---

### 托管版本

Brightbean Studio 的免费托管版本位于 [brightbean.xyz/studio](https://brightbean.xyz/studio/)。它运行与本仓库相同的代码，无需任何搭建或维护。

如果你更愿意自托管，请选择下面任一方式。

### 一键部署

| Heroku | Render | Railway |
|:------:|:------:|:-------:|
| [![Deploy to Heroku](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/brightbeanxyz/brightbean-studio) | [![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/brightbeanxyz/brightbean-studio) | [![Deploy on Railway](https://railway.com/button.svg)](https://railway.com/deploy/brightbean-studio?referralCode=brightbean) |

部署完成后，在你所用平台的仪表盘中设置以下环境变量：

| 变量 | 是否必需 | 说明 |
|----------|----------|-------------|
| `DJANGO_SETTINGS_MODULE` | 自动设置 | `config.settings.production`。若部署配置未自动写入，则手动设置。 |
| `SECRET_KEY` | 自动生成 | Django 密钥。由部署按钮自动设置。 |
| `ENCRYPTION_KEY_SALT` | 自动生成 | 加密盐值。由部署按钮自动设置。 |
| `DATABASE_URL` | 自动配置 | PostgreSQL 连接字符串。自动设置。 |
| `ALLOWED_HOSTS` | 是 | 你应用的域名，例如 `your-app.herokuapp.com` |
| `APP_URL` | 是 | 完整的公网 URL，例如 `https://your-app.herokuapp.com` |
| `STORAGE_BACKEND` | 否 | 设为 `s3` 可使用 S3/R2 存储。默认：`local`。Heroku、Render 和 Railway 的文件系统是临时的，若不使用 S3，重新部署时上传的文件会丢失。 |
| `SERVE_MEDIA` | 否 | 仅在 `STORAGE_BACKEND=local` 时使用。默认 `true`，即由 Django 在 `/media/` 路径提供上传文件。这些文件是**未经鉴权**提供的——任何拿到路径的人都能访问。在此模式下这是必需的：Instagram、Threads、Facebook、Pinterest、Google 商家资料和 dev.to 在发布时会在服务端拉取附件 URL，因此 `/media/` 必须可公开访问。以这种方式暴露的只有媒体库、头像和工作区图标（见 `config/urls.py` 中的 `PUBLIC_MEDIA_PREFIXES`）；评论附件则通过一个有权限校验的视图提供。只有当反向代理或 CDN 在相同的公开路径上提供这些内容时，才设为 `false`。 |
| `CADDY_MEDIA_ROOT` | 否 | 仅 docker-compose 使用。Caddy 读取上传文件的位置。默认：`/app/media`。当 `STORAGE_BACKEND=s3` 时设为 `/var/empty`——`media_data` 数据卷在切换后仍保留，而 Caddy 无法感知 `SERVE_MEDIA`，否则它会继续提供之前遗留的上传文件。 |
| `S3_ENDPOINT_URL` | 使用 S3 时 | 兼容 S3 的端点 URL |
| `S3_ACCESS_KEY_ID` | 使用 S3 时 | S3 访问密钥 |
| `S3_SECRET_ACCESS_KEY` | 使用 S3 时 | S3 秘密密钥 |
| `S3_BUCKET_NAME` | 使用 S3 时 | S3 存储桶名称 |
| `EMAIL_HOST` | 否 | 用于发送邀请函和密码重置邮件的 SMTP 服务器 |
| `EMAIL_PORT` | 否 | SMTP 端口（默认：`587`） |
| `EMAIL_HOST_USER` | 否 | SMTP 用户名 |
| `EMAIL_HOST_PASSWORD` | 否 | SMTP 密码 |
| `GOOGLE_AUTH_CLIENT_ID` | 否 | 用于 Google OAuth 登录。从 [Google Cloud Console](https://console.cloud.google.com/) → Credentials（凭证）获取。 |
| `GOOGLE_AUTH_CLIENT_SECRET` | 否 | Google OAuth 密钥 |
| `UNSPLASH_ACCESS_KEY` | 否 | 在编辑器中启用 Unsplash 图库搜索。可在 [unsplash.com/developers](https://unsplash.com/developers) 免费创建应用。 |

社交媒体 API 密钥，参见[平台凭证](#平台凭证)。完整变量参考：`.env.example`。

## 快速开始（Docker）

```bash
git clone https://github.com/brightbeanxyz/brightbean-studio.git
cd brightbean-studio
cp .env.example .env
```

编辑 `.env`——将 `DATABASE_URL` 改为指向 Docker 服务名：

```
DATABASE_URL=postgres://postgres:postgres@postgres:5432/brightbean
```

然后启动全部服务：

```bash
docker compose up -d --build
docker compose exec app python manage.py createsuperuser
```

数据库迁移由 `migrate` Compose 服务在 `app` 和 `worker` 服务启动之前自动执行，因此没有单独的迁移步骤。

Tailwind 由 `tailwind` Compose 服务自动编译。首次构建约需 60–90 秒（在全新容器中运行 `npm install`）；之后的启动是即时的。可用 `docker compose logs -f tailwind` 查看进度。

打开 http://localhost:8000 ——你已成功运行。


## 完全本地化开发（不使用 Docker）

以原生方式运行所有内容——无需 Docker，也无需安装 PostgreSQL。数据库使用 SQLite。

### 前置条件

- Python 3.12+
- Node.js 20+

### 安装步骤

**1. 克隆并配置**

```bash
git clone https://github.com/brightbeanxyz/brightbean-studio.git
cd brightbean-studio
cp .env.example .env
```

**2. 切换到 SQLite**

打开 `.env`，替换 `DATABASE_URL` 这一行：

```
DATABASE_URL=sqlite:///db.sqlite3
```

就这样——无需安装或管理任何数据库服务器。

**3. 配置 Python 环境**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**4. 配置 Tailwind CSS**

```bash
cd theme/static_src
npm install
cd ../..
```

**5. 执行数据库迁移**

```bash
python manage.py migrate
```

**6. 创建管理员账号**

```bash
python manage.py createsuperuser
```

**7. 启动应用（3 个终端标签页）**

标签页 1 —— Tailwind 监视器：
```bash
cd theme/static_src && npm run start
```

标签页 2 —— Django 开发服务器：
```bash
source .venv/bin/activate
python manage.py runserver
```

标签页 3 —— 后台 worker：
```bash
source .venv/bin/activate
python manage.py process_tasks
```

打开 http://localhost:8000，用你创建的超级用户登录。

### 日常工作流（不使用 Docker）

```bash
source .venv/bin/activate                # 激活 Python 环境
python manage.py runserver               # 启动 Web 服务器
# （另开一个标签页）
python manage.py process_tasks           # 启动 worker
```

> **注意：** SQLite 适合本地开发和小型部署。对于生产环境或高并发使用，请切换到 PostgreSQL。

## 运行测试

```bash
pytest
```

查看覆盖率：

```bash
pytest --cov=apps --cov-report=term-missing
```

## 代码检查与类型检查

```bash
ruff check .                             # 代码检查（lint）
ruff format --check .                    # 格式检查
mypy apps/ config/ --ignore-missing-imports  # 类型检查
```

自动修复代码检查问题：

```bash
ruff check --fix .
ruff format .
```

## 生产环境部署

### 在 VPS 上使用 Docker Compose（推荐）

```bash
# 在你的服务器上：
git clone https://github.com/brightbeanxyz/brightbean-studio.git
cd brightbean-studio
cp .env.example .env
# 编辑 .env：
#   SECRET_KEY=<生成一个 50+ 字符的随机字符串>
#   DEBUG=false
#   ALLOWED_HOSTS=yourdomain.com
#   APP_URL=https://yourdomain.com
#   DATABASE_URL=postgres://postgres:<强密码>@postgres:5432/brightbean

docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
docker compose exec app python manage.py createsuperuser
```

这会启动 5 个容器：app（Gunicorn）、worker、PostgreSQL、Caddy（自动 HTTPS），以及一个一次性的 migrate 容器，用于在启动时自动执行数据库迁移。请在 `Caddyfile` 中填入你的域名。

在默认的 `STORAGE_BACKEND=local` 下，Caddy 直接从 `media_data` 数据卷在 `/media/` 路径提供上传媒体，因此大图片和视频不会占用 Gunicorn worker 线程，并且字节范围请求（视频拖拽 seek）可正常工作。Django 自身的 `/media/` 路由仍然可用，作为没有该代理时的部署回退。

更新方式：

```bash
git pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

### 其他平台

| 平台 | 配置文件 | 说明 |
|----------|-------------|-------|
| **Heroku** | `Procfile` + `app.json` | 已为部署按钮做好准备。必须使用 Basic 或以上档位的 dyno（Eco dyno 会导致 worker 无法正常工作）。 |
| **Railway** | `railway.toml` | [一键模板](https://railway.com/deploy/brightbean-studio)会配置三个服务：web（Gunicorn，启动时执行 `migrate`）、worker（`python manage.py process_tasks`）以及托管 PostgreSQL。Web 服务启动时的 `migrate` 会触发 `post_migrate` 钩子，注册周期性任务，因此排期开箱即用。 |
| **Render** | `render.yaml` | 包含 web、worker、PostgreSQL 的蓝图。必须使用付费档位。 |

所有使用临时文件系统的平台都需要 `STORAGE_BACKEND=s3` —— S3 配置见 `.env.example`。

**内存配置。** 导入应用本身在处理任何请求之前约需 100 MB，一个预热后的 Gunicorn worker 稳定在 200 MB 左右——因此内置命令运行单线程 worker（`--workers 1 --threads 4`），可适配 512 MB 的 dyno，并为媒体处理留出空间。只有在相应增加内存时才提高 `--workers`；经验法则是每个 worker 约 250 MB。**不要**添加 `--max-requests`：gthread 在触发计数器的那个请求开始时会停止心跳，一旦超过 `--timeout`（30 秒），arbiter 会在请求中途杀死 worker——这会丢掉恰好是该请求的上传，而这里的上传最大可达 1 GB。`worker` 进程也需要同样的余量：它会把视频下载到磁盘再流式上传到平台，如果在发布中途被杀死（Heroku 的 R15、OOM 内存杀除、一次部署），受影响的帖子会被确认清理流程标记为失败，而不是停留在不确定状态。

**为什么 worker 使用 `--duration 3600` 运行。** `process_tasks` 是一个不分叉的单一进程，在同一个堆中运行每个任务且从不重启，因此一次峰值分配会永久抬高 RSS（常驻内存）——CPython 和 glibc 会把释放的页保留在各自的 arena 中。放任不管它会只增不减：在 512 MB 的 Basic dyno 上，它从部署后约 280 MB 在 15 小时内攀升到 566 MB，达到配额的 110%。`--duration` 在运行循环的*顶部*检查，因此正在执行的任务总会完成；进程随后在任务之间以退出码 0 退出，平台会在内存下限重启它。不会丢失任何东西——回收不会打断发布，且 `confirm_pending_publishes` 无论如何都会处理任何进行中的任务。不要低于约 1800 秒，否则 Heroku 的崩溃冷却机制会开始介入。其他部署目标保持原命令：`docker-compose.yml` 中 worker 没有 `restart:` 策略，在那里干净退出只会让它停止。

**`MALLOC_ARENA_MAX`。** glibc 给每个线程一个独立的 arena（最大 64 MB），上限为 `8 × nproc`，而容器报告的是宿主机的核心数，因此该上限实际上是无限的。本应用存在真实的线程频繁创建销毁——发布器每 15 秒构建一个新线程池，boto3 的托管传输每次下载增加十个线程——而这些 arena 永远不会归还给操作系统。在 Heroku 上，仓库的 `.profile` 已将其设为 2，同等适用于 web、worker、release 阶段以及一次性的 `heroku run` dyno；它被写为默认值而非强制覆盖，因此如果你想调优，配置变量仍然优先生效。基于 `Dockerfile` 构建的部署目标（Render、Railway、docker-compose）不读取 `.profile`——如果主机内存紧张，请在它们各自的环境配置中设置。

各平台的详细说明与成本分析见 `architecture.md`。

## 项目结构

```
brightbean-studio/
├── config/
│   ├── settings/
│   │   ├── base.py            # 共享设置
│   │   ├── development.py     # 本地开发覆盖
│   │   ├── production.py      # 生产环境加固
│   │   └── test.py            # 测试覆盖
│   ├── urls.py                # 根 URL 配置
│   ├── wsgi.py
│   └── asgi.py
├── apps/
│   ├── accounts/              # 自定义 User 模型、认证、OAuth、会话
│   ├── organizations/         # 组织管理
│   ├── workspaces/            # 工作区增删改查
│   ├── members/               # RBAC、邀请函、中间件、装饰器
│   ├── settings_manager/      # 带级联逻辑的可配置默认值
│   ├── credentials/           # 平台 API 凭证存储（加密）
│   └── common/                # 共享：加密字段、作用域模型管理器
├── providers/                 # 社媒平台 API 模块（每个平台一个文件）
├── templates/                 # Django 模板
│   ├── base.html              # 带侧边栏与导航的布局
│   └── components/            # 可复用的 HTMX 局部模板
├── static/
│   └── js/                    # 内置的 HTMX + Alpine.js
├── theme/                     # django-tailwind 主题应用
│   └── static_src/
│       ├── src/styles.css     # Tailwind 指令
│       └── tailwind.config.js
├── Dockerfile
├── docker-compose.yml         # 开发：app + worker + postgres
├── docker-compose.prod.yml    # 生产覆盖：增加 Caddy，使用 Gunicorn
├── Caddyfile                  # 反向代理 + 自动 HTTPS 配置
├── .env.example               # 全部环境变量
├── Procfile                   # Heroku
├── app.json                   # Heroku 部署按钮
├── railway.toml               # Railway 配置
└── render.yaml                # Render 蓝图
```

> **设置选择：** `DJANGO_SETTINGS_MODULE` 环境变量控制 Django 使用哪个设置文件。各场景的默认值已接好：`manage.py` 使用 `development`，`wsgi.py`/`asgi.py` 使用 `production`，`pytest` 使用 `test`（通过 `pyproject.toml`）。Docker Compose 文件和平台部署配置（Heroku、Render）也会显式设置它。只有当你想为特定命令使用非默认模块时才需手动覆盖，例如 `DJANGO_SETTINGS_MODULE=config.settings.production python manage.py check --deploy`。

## 平台凭证

要连接社交媒体账号，你需要从每个平台的开发者门户获取 API 凭证。你可以通过 `.env` 中的环境变量设置（见 `.env.example`），或者按组织通过 Django 后台在 `{APP_URL}/admin/` → **Credentials（凭证）→ Platform credentials（平台凭证）** 设置（仅限超级用户）。如果某个平台在两处都配置了，`.env` 的值优先。

**后台 UI 访问（仅限超级用户）：** 位于 `{APP_URL}/admin/`（例如 `https://brightbean.example.com/admin/`）的 Django 后台仅限超级用户账号——只有超级用户才能在其中查看或编辑平台凭证。如果你还没有超级用户，请创建一个，然后登录并打开 **Credentials（凭证）→ Platform credentials（平台凭证）**：

```bash
python manage.py createsuperuser
# Docker：docker compose exec app python manage.py createsuperuser
```

**重定向 URI：** 在任何平台注册应用时，将 OAuth 重定向 URI 设为：

```
{APP_URL}/social-accounts/callback/{platform}/
```

例如，如果你的 `APP_URL` 是 `https://brightbean.example.com`，Facebook 的重定向 URI 就是 `https://brightbean.example.com/social-accounts/callback/facebook/`。

> **TikTok：** 使用 slug `social1` 而不是 `tiktok`——TikTok 会拒绝包含其品牌名的重定向 URI。见 [TikTok](#tiktok) 小节。

### Meta（Facebook、Instagram、Threads）

Facebook 和 Instagram 共享同一套 Meta 应用凭证。Threads 运行在同一个 Meta 应用上，但使用**独立的应用身份**——它自己的 App ID、App Secret 和重定向 URI 列表（下面的步骤 6–7）。

1. 前往 [Meta for Developers](https://developers.facebook.com/) 并创建一个新应用（类型：**Business（业务）**）
2. 在 **App Settings（应用设置）→ Basic（基本）** 下，复制你的 **App ID（应用编号）** 和 **App Secret（应用密钥）**——即普通的那一对，用于 Facebook 和 Instagram。添加 Threads 用例后，此页面还会列出 **Threads App ID** / **Threads App Secret**；那是另一套应用身份，应填入步骤 7 的 Threads 变量，而不是这里。
3. 在应用面板中，前往 **Use cases（用例）**，添加以下四个用例。对每个用例，点进去并前往 **Permissions and features（权限和功能）** 添加所需的可选权限：

   **用例："Manage everything on your Page"（管理你公共主页上的一切）**（Facebook）
   - 该用例自动包含 `business_management`、`pages_show_list` 和 `public_profile`
   - 添加以下可选权限：`pages_manage_posts`、`pages_manage_engagement`、`pages_read_engagement`、`pages_read_user_content`、`pages_manage_metadata`、`read_insights`

   **用例："Messenger from Meta"（来自 Meta 的 Messenger）**（Facebook 消息）
   - 启用 `pages_messaging` 权限所必需，该权限在 "Manage Pages" 用例下不可用
   - 添加可选权限：`pages_messaging`

   **用例："Manage messaging & content on Instagram"（管理 Instagram 上的消息与内容）**（Instagram）
   - 添加以下权限：`instagram_basic`、`instagram_content_publish`、`instagram_manage_comments`、`instagram_manage_insights`

   **用例："Access the Threads API"（访问 Threads API）**（Threads）
   - 该用例自动包含 `threads_basic`
   - 添加以下可选权限：`threads_content_publish`、`threads_manage_insights`、`threads_manage_replies`

4. 在 **Facebook Login → Settings（设置）→ Valid OAuth Redirect URIs（有效的 OAuth 重定向 URI）** 下，添加以下重定向 URI：
   ```
   {APP_URL}/social-accounts/callback/facebook/
   {APP_URL}/social-accounts/callback/instagram/
   ```
   > **Threads 是独立的。** 它的回调**不**属于这里——Threads 用例维护自己的重定向 URI 列表。见步骤 7。
5. **Webhooks（网络钩子，收件箱所必需）。** 在应用面板中，前往 **Webhooks**（也可通过 **Use cases → Manage everything on your Page → Webhooks** 到达），订阅 **Page（公共主页）** 对象：
   - **Callback URL（回调 URL）：** `{APP_URL}/webhooks/facebook/`
   - **Verify token（验证令牌）：** 你 `.env` 中 `FACEBOOK_WEBHOOK_VERIFY_TOKEN` 的值（任意随机字符串；生成一个并在点击 *Verify and Save（验证并保存）* 之前设置好该环境变量）
   - 验证通过后，订阅 `feed`、`mention` 和 `messages` 字段。`feed` 承载你公共主页帖子上的评论。

   > **这一步容易遗漏，而且会静默失败。** 连接公共主页会自动让它订阅你的应用，因此账号无论如何都显示为健康——但如果不在这里配置回调 URL，Meta 永远不会投递任何东西。此时评论只能通过 5 分钟轮询回退到达，而 @提及则完全无法到达。可运行 `python manage.py diagnose_facebook --account-id <uuid>` 检查。

   **如果你通过这个 Facebook 应用连接 Instagram，还需在同一个 Webhooks 页面订阅 `Instagram` 对象**：
   - **Callback URL（回调 URL）：** `{APP_URL}/webhooks/facebook/`（同一个端点——它同时处理两个平台）
   - 订阅 `comments` 和 `mentions` 字段。

   > `comments` 和 `mentions` 属于 **Instagram** 对象，而不是 Page——Page 只接受它自己的字段（`feed`、`mention`、`messages` 等）。Studio 会在连接时自动订阅 Instagram *账号*，但这里的对象级配置只能在面板中完成。没有它，Instagram 评论只能通过 5 分钟轮询到达，@提及则完全无法到达。
6. 设置环境变量：
   ```
   PLATFORM_FACEBOOK_APP_ID=your-app-id
   PLATFORM_FACEBOOK_APP_SECRET=your-app-secret
   # 可选：用于代理商/多业务引导的 Facebook Login for Business 配置 ID
   PLATFORM_FACEBOOK_CONFIG_ID=your-configuration-id
   FACEBOOK_WEBHOOK_VERIFY_TOKEN=your-random-verify-token
   ```
   当设置了 `PLATFORM_FACEBOOK_CONFIG_ID` 时，Facebook 以及基于 Facebook 登录的 Instagram 连接器会使用该 Login for Business 配置，而不是发送临时的 `scope` 列表。请在 Meta 的配置中设置所需权限和资产选择，并纳入其公共主页应对该登录可用的每个业务资产。
7. **Threads：** "Access the Threads API" 用例有自己的 App ID、App Secret 和重定向 URI。前往 **Use cases → Access the Threads API → Settings（设置）**，添加 Threads 重定向 URI：
   ```
   {APP_URL}/social-accounts/callback/threads/
   ```
   然后复制 **Threads App ID** 和 **Threads App Secret**（也列在 **App settings → Basic** 下，与你的 Facebook App ID 并列但不同），并设置：
   ```
   PLATFORM_THREADS_APP_ID=your-threads-app-id
   PLATFORM_THREADS_APP_SECRET=your-threads-app-secret
   ```
   这些没有回退：在两者都设置之前，Threads 在连接页面显示为 **Not Configured（未配置）**。向 Threads 发送 Facebook App ID 会报错 `4476002`。

### Instagram（直连，通过 Instagram Login）

Instagram（直连）连接器使用 **Instagram API with Instagram Login（基于 Instagram 登录的 Instagram API）**——这是与上面基于 Facebook Login 的 Instagram 连接器不同的一套 OAuth 流程。它适用于**专业版** Instagram 账号（Business 商家或 Creator 创作者），**无需**关联的 Facebook 公共主页。

> **账号类型要求：** 自 Instagram Basic Display API 于 2024-12-04 停用后，个人版 Instagram 账号没有任何 API 访问权限。用户必须先将账号转为专业版（免费，在 Instagram 设置 → *Account type and tools（账号类型和工具）* → *Switch to professional account（切换为专业账号）*）。

1. 在同一个 Meta 应用中，前往 **Use cases（用例）**，添加 **"Instagram API"** 用例
2. 在 **API setup with Instagram Login（使用 Instagram 登录配置 API）** 下，记下你的 **Instagram App ID** 和 **Instagram App Secret**（它们与你的 Facebook App ID/Secret 不同）
3. 前往 **Permissions and features（权限和功能）**，添加所需权限：
   - `instagram_business_basic`、`instagram_business_content_publish`、`instagram_business_manage_comments`、`instagram_business_manage_messages`、`instagram_business_manage_insights`
4. 在 **API setup with Instagram Login → Step 4: Set up Instagram business login（第 4 步：设置 Instagram 商家登录）** 下，点击 **Set up（设置）** 并添加重定向 URI（必须完全一致，包括末尾斜杠）：
   ```
   {APP_URL}/social-accounts/callback/instagram_login/
   ```
5. 在 **API setup with Instagram Login → Step 3: Configure webhooks（第 3 步：配置网络钩子）** 下，设置：
   - **Callback URL（回调 URL）：** `{APP_URL}/webhooks/instagram_login/`
   - **Verify token（验证令牌）：** 你 `.env` 中 `INSTAGRAM_LOGIN_WEBHOOK_VERIFY_TOKEN` 的值（任意随机字符串；生成一个并在点击 Verify and Save 之前设置好该环境变量）。验证通过后，订阅 `messages`、`comments` 和 `mentions` 字段。
6. 设置环境变量：
   ```
   PLATFORM_INSTAGRAM_APP_ID=your-instagram-app-id
   PLATFORM_INSTAGRAM_APP_SECRET=your-instagram-app-secret
   INSTAGRAM_LOGIN_WEBHOOK_VERIFY_TOKEN=your-random-verify-token
   ```

### LinkedIn

Brightbean Studio 支持两条 LinkedIn 路径。选择你的 LinkedIn 开发者应用能取得的那条——或者在不同的应用上两条都配置。

**路径 A —— 仅个人（任何个人开发者都能完成）：**

1. 前往 [LinkedIn Developer Portal](https://developer.linkedin.com/) 并创建一个新应用（无需公司主页验证）。
2. 在 **Products（产品）** 下，申请访问（两者都会自动批准）：
   - **Sign In with LinkedIn using OpenID Connect（使用 OpenID Connect 通过 LinkedIn 登录）**
   - **Share on LinkedIn（在 LinkedIn 上分享）**
3. 在 **Auth（认证）** 下，添加重定向 URI：
   ```
   {APP_URL}/social-accounts/callback/linkedin_personal/
   ```
4. Scopes（权限范围）：`openid`、`profile`、`email`、`w_member_social`。
5. 设置环境变量：
   ```
   PLATFORM_LINKEDIN_PERSONAL_CLIENT_ID=your-client-id
   PLATFORM_LINKEDIN_PERSONAL_CLIENT_SECRET=your-client-secret
   ```

> **路径 A 的限制：** 访问令牌有效期约 60 天，而 LinkedIn 不为这些 scope 签发刷新令牌——用户必须每约 60 天手动重新连接。此路径下个人账号无法使用收件箱 / 评论读取。

**路径 B —— 公司主页（同时启用完整的个人功能）：**

1. 前往 [LinkedIn Developer Portal](https://developer.linkedin.com/) 并创建一个新应用。
2. 验证该应用与某个 LinkedIn 公司主页的关联。
3. 在 **Products（产品）** 下，申请访问：
   - **Community Management API（社群管理 API）** *（受限制——需要 LinkedIn 审核）*
4. 在 **Auth（认证）** 下，添加**两个**重定向 URI：
   ```
   {APP_URL}/social-accounts/callback/linkedin_personal/
   {APP_URL}/social-accounts/callback/linkedin_company/
   ```
5. Scopes（权限范围）：
   - **个人：** `r_basicprofile`、`w_member_social`、`r_member_social`
   - **公司：** `r_basicprofile`、`w_member_social`、`w_organization_social`、`r_organization_social`、`rw_organization_admin`
6. 设置环境变量：
   ```
   PLATFORM_LINKEDIN_COMPANY_CLIENT_ID=your-client-id
   PLATFORM_LINKEDIN_COMPANY_CLIENT_SECRET=your-client-secret
   ```

如果你只设置了路径 B（公司）凭证，Brightbean Studio 会自动将它们复用于个人连接——刷新令牌（365 天）和收件箱都能工作。只有当你有一个独立的仅个人应用时，才需要路径 A 的变量。

> **注意：** "Sign In with LinkedIn using OpenID Connect" / "Share on LinkedIn" 与 "Community Management API" 在单个 LinkedIn 应用上是**互斥**的。路径 A 和路径 B 需要各自独立的应用。

> **向后兼容：** 旧版 `PLATFORM_LINKEDIN_CLIENT_ID` / `PLATFORM_LINKEDIN_CLIENT_SECRET` 环境变量仍作为 `linkedin_personal` 和 `linkedin_company` 的回退被支持——现有自托管用户无需改动即可继续工作。旧版凭证默认视为已通过 CM（社群管理）批准；如果你的旧应用仅支持 OIDC，请迁移到 `PLATFORM_LINKEDIN_PERSONAL_*`。

### TikTok

1. 前往 [TikTok Developer Portal](https://developers.tiktok.com/) 并创建一个新应用
2. 添加产品 **Login Kit（登录套件）** 和 **Content Posting API（内容发布 API）**
3. 配置重定向 URI——使用 `social1`，而不是 `tiktok`（TikTok 会拒绝包含其品牌名的 URI）：
   ```
   {APP_URL}/social-accounts/callback/social1/
   ```
4. 所需 scopes：`user.info.basic`、`video.publish`、`video.upload`、`video.list`
5. 注意：TikTok 使用 **Client Key（客户端密钥，注意不是 Client ID）**。从你的应用面板复制 **Client Key** 和 **Client Secret**
6. 设置环境变量：
   ```
   PLATFORM_TIKTOK_CLIENT_KEY=your-client-key
   PLATFORM_TIKTOK_CLIENT_SECRET=your-client-secret
   ```
7. 为通过生产环境审核，请针对 TikTok **Sandbox（沙箱）** 录制演示视频，展示每个申请的 scope 都在使用。

### Google（YouTube、Google 商家资料）

YouTube 和 Google 商家资料共享同一套 Google Cloud 凭证。

1. 前往 [Google Cloud Console](https://console.cloud.google.com/) 并创建一个新项目（或选择现有项目）
2. 在 **APIs & Services（API 和服务）→ Library（库）** 下启用以下 API：
   - **YouTube Data API v3**（用于 YouTube）
   - **My Business Account Management API**、**My Business Business Information API** 和 **Google My Business API**（用于 Google 商家资料）
3. 前往 **APIs & Services → Credentials（凭证）**，创建一个 **OAuth 2.0 Client ID（OAuth 2.0 客户端 ID）**（类型：Web application 网页应用）
4. 在 **Authorized redirect URIs（已授权的重定向 URI）** 下添加以下重定向 URI：
   ```
   {APP_URL}/social-accounts/callback/youtube/
   {APP_URL}/social-accounts/callback/google_business/
   ```
5. 复制 **Client ID（客户端 ID）** 和 **Client Secret（客户端密钥）**
6. 所需 scopes：
   - **YouTube：** `https://www.googleapis.com/auth/youtube.upload`、`https://www.googleapis.com/auth/youtube.readonly`、`https://www.googleapis.com/auth/youtube.force-ssl`、`https://www.googleapis.com/auth/yt-analytics.readonly`
   - **Google 商家资料：** `https://www.googleapis.com/auth/business.manage`
7. 设置环境变量：
   ```
   PLATFORM_GOOGLE_CLIENT_ID=your-client-id
   PLATFORM_GOOGLE_CLIENT_SECRET=your-client-secret
   ```

### Pinterest

1. 前往 [Pinterest Developer Portal](https://developers.pinterest.com/) 并创建一个新应用
2. 在你的应用设置中，添加重定向 URI：
   ```
   {APP_URL}/social-accounts/callback/pinterest/
   ```
3. 复制 **App ID（应用编号）** 和 **App Secret（应用密钥）**
4. 所需 scopes：`user_accounts:read`、`boards:read`、`boards:write`、`pins:read`、`pins:write`
5. 设置环境变量：
   ```
   PLATFORM_PINTEREST_APP_ID=your-app-id
   PLATFORM_PINTEREST_APP_SECRET=your-app-secret
   ```

### Bluesky

无需注册开发者应用。用户通过输入其 Bluesky 用户名（handle）和一个 **App Password（应用专用密码）** 来连接：

1. 登录 [Bluesky](https://bsky.app/)
2. 前往 **Settings（设置）→ Privacy and Security（隐私与安全）→ App Passwords（应用密码）**
3. 创建一个新的应用密码，并在 Brightbean Studio 中连接账号时使用它

### Mastodon

无需注册开发者应用。当用户连接账号时，Brightbean Studio 会在每个 Mastodon 实例上自动注册一个 OAuth 应用。用户只需输入其实例 URL（例如 `mastodon.social`）。

### DEV.to

无需注册开发者应用。用户通过输入个人 **API key（API 密钥）** 来连接：

1. 登录 [DEV.to](https://dev.to/)，打开 **[Settings（设置）→ Extensions（扩展）](https://dev.to/settings/extensions)**
2. 在 **DEV Community API Keys** 下，输入一段描述（例如 `Brightbean`），点击 **Generate API Key（生成 API 密钥）**
3. 复制生成的密钥，在 Brightbean Studio 中连接账号时粘贴

帖子会以 DEV.to 文章形式发布（标题 + Markdown 正文）。该密钥可随时在同一设置页面撤销。

## 收件箱：回填历史消息

各平台的收件箱能力，见上面的[支持的平台](#支持的平台)矩阵。

要导入历史消息（例如最近 7 天）：

```bash
python manage.py backfill_inbox --days 7
```

选项：
- `--days N` —— 回填的天数（默认：7）
- `--platform NAME` —— 仅回填某个特定平台（例如 `facebook`、`youtube`、`linkedin`、`tiktok`）
- `--account-id UUID` —— 仅回填某个特定账号

对于 Facebook，这会恢复公共主页帖子最近 30 天的评论——在修复了一个从未正常投递的 webhook 之后很有用，否则故障期间错过的评论将不可见：

```bash
python manage.py backfill_inbox --platform facebook --days 30
```

## 收件箱：诊断一个收不到任何消息的 Facebook 公共主页

当某个公共主页的评论始终无法进入收件箱，或某条帖子的首条评论始终不出现时，原因通常是某个权限未授予、或某个 webhook 从未配置——这两者在应用内部都看不到。直接向 Meta 查询：

```bash
python manage.py diagnose_facebook --account-id <uuid>
```

它会报告令牌已授予的 scopes（缺少 `pages_manage_engagement` 正是首条评论失败的原因）、哪个应用订阅了该公共主页以及订阅了哪些字段（`feed` 承载评论），以及评论究竟是否可读。添加 `--subscribe` 可就地修复缺失的公共主页订阅，或用 `--json` 输出可粘贴到事故报告中的内容。

## 面向智能体的 API 与 MCP

BrightBean Studio 内置一个 REST API 和一个 MCP（Model Context Protocol，模型上下文协议）服务器，让智能体和脚本可以读取分析数据、管理媒体、创建或排期帖子。两者共享相同的认证、权限模型、速率限制和审计日志。选择适合你客户端的任一协议。

**Base URL（根地址）：** `{APP_URL}/api/v1/`（例如 `https://your-studio.example.com/api/v1/`）

### 认证

在 **Organization（组织）→ API Keys（API 密钥）** 签发一个 API 密钥。密钥以工作区为作用域，可加入针对特定社媒账号的白名单，并继承签发者工作区权限的一个子集。吊销立即生效。将密钥作为 Bearer 令牌发送：

```
Authorization: Bearer bb_studio_...
```

同时发送一个标明你客户端的 `User-Agent` 请求头（例如 `User-Agent: my-agent/1.0`）。Cloudflare 的浏览器完整性检查默认开启，并挡在托管的 `studio.brightbean.xyz` 前面，它会以 `403` 加一段纯文本 `error code: 1010` 响应体拒绝 Python 标准库的默认 UA（`Python-urllib/3.x`），请求根本到不了 Studio。任何你自定义的值都能通过；`requests`、`httpx`、curl 和 Node 客户端本就发送可通过的 UA。

权限键：`create_posts`、`publish_directly`、`upload_media`、`view_analytics`、`use_inbox`、`reply_from_inbox`。每个端点要求相应的权限；缺少权限返回 `403`。

### 速率限制

| 作用域 | 限制 |
|---|---|
| 每个密钥的写入 | 120 / 分钟 |
| 每个密钥的读取 | 300 / 分钟 |
| 每个工作区的聚合 | 1000 / 分钟 |

速率限制响应（`429`）包含 `Retry-After`、`X-RateLimit-Limit` 和 `X-RateLimit-Remaining` 请求头。

### REST 端点

| 方法 | 路径 | 用途 | 权限 |
|---|---|---|---|
| `GET` | `/me` | 查看调用者的作用域与工作区权限 | — |
| `GET` | `/accounts` | 列出已连接的社媒账号 | — |
| `POST` | `/posts` | 创建草稿或定时帖子 | `create_posts`（排期还需 `publish_directly`） |
| `GET` | `/posts/{post_id}` | 读取单个帖子 | — |
| `PATCH` | `/posts/{post_id}` | 更新草稿字段 | `create_posts` |
| `POST` | `/posts/{post_id}/schedule` | 为草稿排期 | `create_posts` + `publish_directly` |
| `POST` | `/posts/{post_id}/cancel` | 将定时帖子还原为草稿 | `create_posts` |
| `GET` | `/analytics/accounts/{account_id}` | 渠道分析摘要（7/30/90 天窗口） | `view_analytics` |
| `GET` | `/analytics/posts/{post_id}` | 帖子分析，含各平台指标 | `view_analytics` |
| `POST` | `/media` | 上传媒体文件（multipart） | `upload_media` |
| `GET` | `/media/{media_id}` | 获取一个媒体资产 | — |
| `GET` | `/media` | 列出媒体资产（可过滤、分页） | — |
| `GET` | `/inbox` | 列出收件箱消息（按状态/类型/账号过滤，分页） | `use_inbox` |
| `GET` | `/inbox/{message_id}` | 读取一条收件箱消息及其回复线程 | `use_inbox` |
| `POST` | `/inbox/{message_id}/replies` | 起草回复（设置 `send: true` 立即发送） | `use_inbox`（发送还需 `reply_from_inbox`） |
| `PATCH` | `/inbox/replies/{reply_id}` | 编辑草稿回复 | `use_inbox` |
| `POST` | `/inbox/replies/{reply_id}/send` | 将草稿回复投递到平台 | `reply_from_inbox` |
| `DELETE` | `/inbox/replies/{reply_id}` | 丢弃草稿回复 | `use_inbox` |
| `POST` | `/mcp` | 面向 MCP 客户端的 JSON-RPC 2.0 端点 | — |

帖子创建、媒体上传和收件箱回复创建接受 `idempotency_key`（或 `Idempotency-Key` 请求头），以便安全重试。

对于收件箱回复创建，复用相同的键和请求会重放原始响应，而不会创建或发送另一条回复。失败的"创建并发送"响应也会被重放；可从消息线程中取回保留的失败回复，并通过 `/inbox/replies/{reply_id}/send` 重试投递。

### MCP 工具

MCP 服务器位于 `POST {APP_URL}/api/v1/mcp`，通过 Streamable HTTP 讲 JSON-RPC 2.0。它实现标准的 `initialize`、`tools/list`、`tools/call` 和 `ping` 方法。工具如下：

| 工具 | 用途 | 权限 |
|---|---|---|
| `list_accounts` | 列出该 API 密钥可操作的社媒账号 | — |
| `create_draft` | 创建草稿帖子（文案、标题、媒体、首条评论，可选建议发布时间） | `create_posts` |
| `schedule_post` | 一步创建并排期帖子 | `create_posts` + `publish_directly` |
| `schedule_draft` | 为现有草稿排期 | `create_posts` + `publish_directly` |
| `get_post` | 获取帖子，含聚合状态和各平台状态 | — |
| `list_posts` | 按最新优先列出帖子，可选状态过滤和游标分页 | — |
| `cancel_post` | 将定时帖子还原为草稿 | `create_posts` |
| `search_media` | 按查询、类型、标签或文件夹查找媒体资产 | — |
| `get_media` | 按 ID 获取单个媒体资产 | — |
| `upload_media` | 上传一个小型 base64 编码文件（原始大小 ≤ 1 MB）。更大的文件请使用 REST `POST /media`。 | `upload_media` |
| `get_account_analytics` | 在滚动的 7–90 天窗口内获取渠道分析 | `view_analytics` |
| `get_post_analytics` | 获取单个帖子的各平台指标（适合轮询草稿） | `view_analytics` |
| `list_inbox_messages` | 列出收件箱条目（评论、@提及、私信、评价）及其回复线程 | `use_inbox` |
| `get_inbox_message` | 获取一条收件箱消息及其回复线程 | `use_inbox` |
| `create_reply_draft` | 为收件箱消息起草回复（已保存，未发送） | `use_inbox` |
| `update_reply_draft` | 替换草稿（或失败）回复的正文 | `use_inbox` |
| `discard_reply_draft` | 删除草稿（或失败）回复 | `use_inbox` |
| `send_reply` | 投递回复（用 `reply_id`，或用 `message_id` + `body` 起草并发送） | `reply_from_inbox` |

### 连接 MCP 客户端

服务器位于 `{APP_URL}/api/v1/mcp`，支持两种认证模式——选择你客户端所用的那种。

**Claude Desktop（及其他原生 OAuth 连接器）。** 在 Claude Desktop 中打开 **Settings（设置）→ Connectors（连接器）→ Add custom connector（添加自定义连接器）**，为其命名，并输入服务器 URL `{APP_URL}/api/v1/mcp`。Claude 会自行注册（动态客户端注册）并打开浏览器登录 BrightBean Studio 并批准访问——**无需 API 密钥**。任何 Studio 用户都可连接；该连接以**其本人**的工作区权限行事（只读角色得到只读工具，而发帖/排期/上传需要相应权限），作用于其最后活跃的工作区。要求 Studio 通过公开的 **https** URL 提供服务。

**Claude Code、Cursor、自定义智能体（静态 API 密钥）。** 将客户端指向同一 URL，并把 API 密钥作为 Bearer 令牌发送（`Authorization: Bearer bb_studio_...`）。对于 Claude Code：

```bash
claude mcp add --transport http brightbean {APP_URL}/api/v1/mcp \
  --header "Authorization: Bearer bb_studio_..."
```

### 预制的智能体技能

不想自己搭建客户端？配套的 [brightbean-studio-agent](https://github.com/brightbeanxyz/brightbean-studio-agent) 仓库提供一个完整的智能体技能，通过上面文档所述的 REST API 和 MCP 工具端到端驱动 BrightBean Studio。

---

## 技术栈

| 层 | 技术 |
|-------|-----------|
| 后端 | Django 5.x |
| 前端 | Django 模板、HTMX、Alpine.js |
| CSS | 通过 django-tailwind 使用 Tailwind CSS 4 |
| 数据库 | PostgreSQL 16+ |
| 后台任务 | django-background-tasks（无需 Redis） |
| 认证 | django-allauth（邮箱 + Google OAuth） |
| 媒体 | Pillow（图片）、FFmpeg（视频） |
| 部署 | Docker、Gunicorn、Caddy |

---

## 故障排查

**Docker：`postgres` 容器不健康（unhealthy）**
`docker compose up` 后等待 10–15 秒让健康检查通过，然后重试命令。用 `docker compose logs postgres` 查看日志。

**`python manage.py migrate` 因连接错误失败**
确保 PostgreSQL 正在运行且健康。Docker：`docker compose ps` 应显示 postgres 为 "healthy"。本地：检查 `.env` 中的 `DATABASE_URL` 是否匹配你的设置。

**Tailwind CSS 改动没有出现**
确保 Tailwind 监视器正在运行：`cd theme/static_src && npm run start`。如果样式仍不更新，尝试 `npm run build` 进行完整重建。

**OAuth 回调错误（"redirect URI mismatch"，重定向 URI 不匹配）**
在平台上注册的重定向 URI 必须与 `{APP_URL}/social-accounts/callback/{platform}/` 完全一致。检查 `.env` 中的 `APP_URL` 是否与你访问的 URL 匹配（包括 `http` 与 `https` 以及端口号）。

**Threads："No app ID was provided in the request"（请求中未提供应用 ID，错误 `4476002`）**
Threads 使用它自己的 App ID，而不是 Facebook 的。从 **Use cases → Access the Threads API → Settings** 设置 `PLATFORM_THREADS_APP_ID` / `PLATFORM_THREADS_APP_SECRET`，并在同一面板注册 `{APP_URL}/social-accounts/callback/threads/`——Facebook Login 的重定向 URI 列表不覆盖 Threads。见 [Meta](#metafacebookinstagramthreads) 小节。

**后台任务不运行（帖子不发布）**
确保 worker 正在运行：`python manage.py process_tasks`。Docker：检查 `docker compose logs worker`。

**帖子卡在 "Publishing（发布中）"**
它不应停留在那里。`confirm_pending_publishes` 每 60 秒运行一次并处理任何处于该状态的帖子：异步发布（TikTok 接受上传后再转码）会向平台确认并标记为已发布，或连同平台给出的原因标记为失败；而 worker 在发布中途死亡的帖子会在 `PUBLISHER_STALE_PUBLISHING_TIMEOUT` 后标记为失败，使其重新可编辑、可重试。它永远不会被自动重新发布——我们无法区分"平台从未收到"与"平台已收到但我们在记录之前崩溃"，而一个正式账号上的重复视频无法撤销。第三种情况被有意保持区分：当平台已接受上传，但我们无法联系它询问结果时，清理流程会持续对账达 `PUBLISHER_UNCONFIRMED_TIMEOUT`（默认 6 小时），若始终得不到答案，则把帖子标记为失败，文案提示用户在重新发布前**先检查账号**，而不是直接重试——帖子可能已经上线。如果帖子停留在 "Publishing" 超过这个时长，说明 worker 没有运行（见上）或正被反复杀死——检查它的内存。

**生产环境中上传的图片 404（且 Instagram/Facebook/Pinterest 帖子失败）**
当 `STORAGE_BACKEND=local` 时，`/media/` 必须可公开访问。检查 `SERVE_MEDIA` 没有被设为 `false`（除非你的反向代理在相同路径提供 `MEDIA_ROOT`），并检查 `MEDIA_ROOT` 位于持久化数据卷上。这些平台在服务端拉取附件 URL，因此那里的 404 会导致发布失败，而不只是缩略图失败。

## 参与贡献

开发设置、编码规范以及如何提交拉取请求，见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 安全

要报告安全漏洞，见 [SECURITY.md](SECURITY.md)。请不要公开提 issue。

## 许可证

[AGPL-3.0](LICENSE) —— 详情见 LICENSE。
