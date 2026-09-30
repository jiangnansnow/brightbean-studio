from django.apps import AppConfig


class ZhOverridesConfig(AppConfig):
    # Chinese (zh-hans) template override layer.
    #
    # This app ships NO upstream modifications: every file under
    # zh_overrides/templates/ mirrors an upstream template's relative path with
    # a translated copy. Being first in INSTALLED_APPS makes Django's template
    # loader pick these up; pages without an override fall back to English.
    name = "zh_overrides"
    verbose_name = "中文模板覆盖层"
    default_auto_field = "django.db.models.BigAutoField"
