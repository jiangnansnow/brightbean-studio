"""Test settings that install the zh_overrides app on top of upstream tests.

Usage:
    DJANGO_SETTINGS_MODULE=zh_overrides.test_settings pytest zh_overrides

Uses in-memory SQLite so the local-custom sidecar tests can run without the
PostgreSQL ``brightbean_test`` database the upstream suite requires.
"""

from config.settings.test import *  # noqa: F401,F403

INSTALLED_APPS = ["zh_overrides.apps.ZhOverridesConfig"] + INSTALLED_APPS  # noqa: F405

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
