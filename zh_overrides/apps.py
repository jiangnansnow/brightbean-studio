from django.apps import AppConfig


class ZhOverridesConfig(AppConfig):
    # Chinese (zh-hans) template override layer + local-custom platform
    # extensions (workspace-scoped credentials, superuser tenant console).
    name = "zh_overrides"
    verbose_name = "中文汉化与平台扩展"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        self._pin_admin_app_first()

    def _pin_admin_app_first(self):
        """Reorder the admin index/nav: keep this app group at the very top
        and inject a direct link to the tenant configuration console.

        Wrapping ``get_app_list`` is additive: upstream app dicts are returned
        untouched apart from ordering, so upstream admin upgrades cannot break
        model entries.
        """
        from django.contrib import admin

        original_get_app_list = admin.AdminSite.get_app_list
        app_label = self.name
        console_label = "租户配置矩阵"
        console_url = "/admin/zh_overrides/workspaceplatformcredential/tenant-config/"

        def get_app_list(self, request, app_label_arg=None):
            if app_label_arg is not None:
                apps_ = original_get_app_list(self, request, app_label_arg)
            else:
                apps_ = original_get_app_list(self, request)

            zh = next((a for a in apps_ if a.get("app_label") == app_label), None)
            if zh is None:
                return apps_

            zh["name"] = "中文汉化与平台扩展"

            # Inject console entry at the top of this app's model list.
            existing_urls = {m.get("admin_url") or m.get("add_url") for m in zh.get("models", [])}
            if console_url not in existing_urls and not any(
                m.get("object_name") == console_label for m in zh.get("models", [])
            ):
                zh.setdefault("models", []).insert(
                    0,
                    {
                        "name": console_label,
                        "object_name": console_label,
                        "perms": {"add": False, "change": True, "delete": False, "view": True},
                        "admin_url": console_url,
                        "add_url": None,
                        "view_only": False,
                    },
                )

            ordered = [zh] + [a for a in apps_ if a.get("app_label") != app_label]
            return ordered

        admin.AdminSite.get_app_list = get_app_list
