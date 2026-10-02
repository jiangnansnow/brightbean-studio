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

from config.settings.production import *  # noqa: F401,F403
from config.settings.base import BASE_DIR, env
from config.settings.production import INSTALLED_APPS, MIDDLEWARE, TEMPLATES

INSTALLED_APPS = ["zh_overrides.apps.ZhOverridesConfig"] + INSTALLED_APPS

MIDDLEWARE = MIDDLEWARE + ["zh_overrides.middleware.ZhLocalizationMiddleware"]

TEMPLATES[0]["DIRS"] = [BASE_DIR / "zh_overrides" / "templates"] + TEMPLATES[0]["DIRS"]

ROOT_URLCONF = "zh_overrides.urls"

# Master switch for the Chinese overlay. Default on; set to false in .env to
# disable zh-hans without code changes or image rebuild.
ZH_LOCALIZATION_ENABLED = env.bool("ZH_LOCALIZATION_ENABLED", True)
