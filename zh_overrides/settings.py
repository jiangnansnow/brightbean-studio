"""Self-contained settings module for the zh-hans overlay deployment.

Selected via the ``DJANGO_SETTINGS_MODULE=zh_overrides.settings`` environment
variable (injected through ``--env-file``; it wins over the ``setdefault`` in
``config/wsgi.py``). Imports the upstream production settings untouched and
then layers the Chinese overlay on top:

- ``zh_overrides`` prepended to INSTALLED_APPS (its template copies win
  resolution ahead of every other app; adds no models)
- ``ZhLocalizationMiddleware`` appended to the middleware chain
- ``zh_overrides/templates`` prepended to TEMPLATES[0]["DIRS"] (upstream puts
  its own ``templates/`` in DIRS, which beats APP_DIRS, so the prepend is what
  makes the Chinese copies win)
- ``ROOT_URLCONF`` switched to ``zh_overrides.urls`` (legal pages +
  dictionary payload routes live there, upstream urls stay pristine)

Zero upstream files are modified by the overlay, so ``git merge upstream/main``
can never conflict on ``config/``. Removing the ``DJANGO_SETTINGS_MODULE`` env
line fully disables the overlay and falls back to the upstream English site.
"""

from config.settings.base import BASE_DIR, env
from config.settings.production import *  # noqa: F401,F403
from config.settings.production import EMAIL_BACKEND_TYPE, INSTALLED_APPS, MIDDLEWARE, TEMPLATES

INSTALLED_APPS = ["zh_overrides.apps.ZhOverridesConfig"] + INSTALLED_APPS

MIDDLEWARE = MIDDLEWARE + ["zh_overrides.middleware.ZhLocalizationMiddleware"]

TEMPLATES[0]["DIRS"] = [BASE_DIR / "zh_overrides" / "templates"] + TEMPLATES[0]["DIRS"]

ROOT_URLCONF = "zh_overrides.urls"

# Signup gate: email/password registration is invite-only; Google OAuth
# signups stay open (when GOOGLE_AUTH_CLIENT_ID is configured). Existing-user
# login is unaffected. See zh_overrides/adapters.py.
ACCOUNT_ADAPTER = "zh_overrides.adapters.ZhAccountAdapter"
SOCIALACCOUNT_ADAPTER = "zh_overrides.adapters.ZhSocialAccountAdapter"

# Master switch for the Chinese overlay. Default on; set to false in .env to
# disable zh-hans without code changes or image rebuild.
ZH_LOCALIZATION_ENABLED = env.bool("ZH_LOCALIZATION_ENABLED", True)

# 运行时漏翻收集（默认关闭）。开启后 middleware 会把词典完全未命中的英文文本
# 追加写到 ZH_LEAK_COLLECT_DIR/leaks.jsonl，供 `python manage.py zhleak` 导出补词；
# 生产常态保持关闭，避免每请求的磁盘 IO 开销。DIR 留空则落到系统临时目录。
ZH_LEAK_COLLECT_ENABLED = env.bool("ZH_LEAK_COLLECT_ENABLED", default=False)
ZH_LEAK_COLLECT_DIR = env("ZH_LEAK_COLLECT_DIR", default="")

# SMTP implicit SSL (port 465) support. Upstream only wires EMAIL_USE_TLS
# (STARTTLS on 587); providers such as NetEase 163 mail require implicit SSL
# on 465. TLS and SSL are mutually exclusive in Django's SMTP backend.
# Set EMAIL_USE_SSL=true together with EMAIL_PORT=465 in .env.
if EMAIL_BACKEND_TYPE == "smtp" and env.bool("EMAIL_USE_SSL", default=False):
    EMAIL_USE_SSL = True
    EMAIL_USE_TLS = False

# R2/S3 public custom domain mode. Upstream defaults to a private bucket with
# 1-hour signed query URLs (AWS_QUERYSTRING_AUTH=True). Our deployment binds the
# bucket to a public custom domain (S3_CUSTOM_DOMAIN, e.g. media.ysec.cn) where
# objects are anonymously readable. Platforms (Meta etc.) fetch media
# server-side and may do so well after publish, so unsigned permanent URLs are
# more reliable than expiring signatures. Only applies when STORAGE_BACKEND=s3;
# the local backend never executes this block and stays byte-identical to
# upstream.
if STORAGE_BACKEND.lower() == "s3":
    # R2 does not accept the canned ACL header; None stops django-storages
    # from sending x-amz-acl.
    AWS_DEFAULT_ACL = None
    # Emit plain custom-domain URLs with no ?X-Amz-Signature query string.
    AWS_QUERYSTRING_AUTH = False
