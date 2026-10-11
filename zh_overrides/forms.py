from django import forms
from django.utils.safestring import mark_safe

from apps.credentials.models import REQUIRED_CREDENTIAL_KEYS, derive_is_configured

from .models import WorkspacePlatformCredential

# Mirrors apps.credentials.forms._KEY_HINTS (kept local on purpose: the
# sidecar must not depend on a private symbol of the upstream form module).
_KEY_HINTS = {
    "facebook": "client_id, client_secret（app_id / app_secret 亦可），可选 config_id",
    "instagram": "client_id, client_secret（app_id / app_secret 亦可），可选 config_id",
    "instagram_login": "client_id, client_secret（app_id / app_secret 亦可）",
    "threads": "client_id, client_secret（app_id / app_secret 亦可）",
    "pinterest": "client_id, client_secret（app_id / app_secret 亦可）",
    "tiktok": "client_key, client_secret（注意是 client_key，不是 client_id）",
    "youtube": "client_id, client_secret",
    "google_business": "client_id, client_secret（可选 account_id、location_id）",
    "linkedin_personal": "client_id, client_secret",
    "linkedin_company": "client_id, client_secret",
}

CREDENTIALS_HELP = mark_safe(
    "应用凭证 JSON 对象，例如 "
    '<code>{"client_id": "...", "client_secret": "..."}</code>。'
    "仅当该工作区所属<b>组织</b>未配置同平台的组织级凭证时本行才生效；"
    "组织级已配置时全组织共享组织 App，本行被忽略。<br>"
    + "<br>".join(f"<b>{platform}</b>：{hint}" for platform, hint in _KEY_HINTS.items())
)


class WorkspacePlatformCredentialAdminForm(forms.ModelForm):
    credentials = forms.JSONField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 6, "cols": 60}),
        help_text=CREDENTIALS_HELP,
    )

    class Meta:
        model = WorkspacePlatformCredential
        fields = ("workspace", "platform", "credentials")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only platforms that take app-level credentials (mirrors the upstream
        # PlatformCredential form).
        self.fields["platform"].choices = [
            choice
            for choice in self.fields["platform"].choices
            if choice[0] == "" or choice[0] in REQUIRED_CREDENTIAL_KEYS
        ]
        self.fields["workspace"].label = "工作区"
        self.fields["platform"].label = "平台"
        self.fields["credentials"].label = "凭证（JSON）"

    def clean_credentials(self):
        data = self.cleaned_data.get("credentials")
        if data in (None, ""):
            return {}
        if not isinstance(data, dict):
            raise forms.ValidationError(
                '凭证必须是 JSON 对象，例如 {"client_id": "...", "client_secret": "..."}。'
            )
        cleaned = {}
        for key, value in data.items():
            if value is None:
                continue
            text = value if isinstance(value, str) else str(value)
            if text.strip():
                cleaned[key] = text
        return cleaned

    def clean(self):
        cleaned = super().clean()
        platform = cleaned.get("platform")
        credentials = cleaned.get("credentials") or {}
        if platform and credentials and not derive_is_configured(platform, credentials):
            required = REQUIRED_CREDENTIAL_KEYS.get(platform, ())
            hint = ", ".join(" / ".join(group) for group in required)
            self.add_error(
                "credentials",
                f"平台 {platform} 缺少必需字段，应为：{hint or '无'}。"
                "所有必需字段齐全前该行保持未配置状态。",
            )
        return cleaned
