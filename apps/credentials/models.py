import uuid

from django.db import models

from apps.common.encryption import EncryptedJSONField
from apps.common.managers import OrgScopedManager

# Per-platform required credential keys. Each inner tuple is an "any of these
# aliases" group; a platform counts as configured only when EVERY group has a
# non-empty value. Mirrors the keys each provider actually reads — TikTok uses
# ``client_key`` (not ``client_id``); Meta and Pinterest accept ``app_id`` /
# ``app_secret`` as aliases for ``client_id`` / ``client_secret``. Platforms
# with no entry (bluesky, mastodon) use session / per-instance auth and need no
# app-level credentials.
REQUIRED_CREDENTIAL_KEYS = {
    "facebook": (("client_id", "app_id"), ("client_secret", "app_secret")),
    "instagram": (("client_id", "app_id"), ("client_secret", "app_secret")),
    "instagram_login": (("client_id", "app_id"), ("client_secret", "app_secret")),
    "threads": (("client_id", "app_id"), ("client_secret", "app_secret")),
    "pinterest": (("client_id", "app_id"), ("client_secret", "app_secret")),
    "tiktok": (("client_key",), ("client_secret",)),
    "youtube": (("client_id",), ("client_secret",)),
    "google_business": (("client_id",), ("client_secret",)),
    "linkedin_personal": (("client_id",), ("client_secret",)),
    "linkedin_company": (("client_id",), ("client_secret",)),
}


def derive_is_configured(platform, credentials):
    """Return True when ``credentials`` holds every required key for ``platform``.

    Used to populate ``PlatformCredential.is_configured`` (the runtime gate) from
    the credential values, so a row activates only when it is actually usable.
    """
    groups = REQUIRED_CREDENTIAL_KEYS.get(platform)
    if not groups:
        return False
    creds = credentials or {}
    return all(any(str(creds.get(k) or "").strip() for k in group) for group in groups)


class PlatformCredential(models.Model):
    class Platform(models.TextChoices):
        FACEBOOK = "facebook", "Facebook"
        INSTAGRAM = "instagram", "Instagram"
        INSTAGRAM_LOGIN = "instagram_login", "Instagram (Direct)"
        LINKEDIN_PERSONAL = "linkedin_personal", "LinkedIn (Personal Profile)"
        LINKEDIN_COMPANY = "linkedin_company", "LinkedIn (Company Page)"
        TIKTOK = "tiktok", "TikTok"
        YOUTUBE = "youtube", "YouTube"
        PINTEREST = "pinterest", "Pinterest"
        THREADS = "threads", "Threads"
        BLUESKY = "bluesky", "Bluesky"
        GOOGLE_BUSINESS = "google_business", "Google Business Profile"
        MASTODON = "mastodon", "Mastodon"
        DEVTO = "devto", "DEV.to"

    class TestResult(models.TextChoices):
        SUCCESS = "success", "Success"
        FAILURE = "failure", "Failure"
        UNTESTED = "untested", "Untested"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="platform_credentials",
    )
    platform = models.CharField(max_length=30, choices=Platform.choices)
    credentials = EncryptedJSONField(
        default=dict,
        help_text="Encrypted JSON containing platform-specific credential fields",
    )
    is_configured = models.BooleanField(default=False)
    tested_at = models.DateTimeField(blank=True, null=True)
    test_result = models.CharField(
        max_length=20,
        choices=TestResult.choices,
        default=TestResult.UNTESTED,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = OrgScopedManager()

    class Meta:
        db_table = "credentials_platform_credential"
        unique_together = [("organization", "platform")]

    def __str__(self):
        return f"{self.organization.name} - {self.get_platform_display()}"

    def save(self, *args, **kwargs):
        # ``is_configured`` is the runtime gate every consumer filters on; keep it
        # a pure function of the credential values so a row is only ever active
        # when it actually has the keys its provider needs.
        self.is_configured = derive_is_configured(self.platform, self.credentials)
        update_fields = kwargs.get("update_fields")
        if update_fields is not None:
            # Persist the derived flag even on a partial (update_fields) save.
            kwargs["update_fields"] = {*update_fields, "is_configured"}
        super().save(*args, **kwargs)

    @property
    def masked_credentials(self):
        """Return credentials with secrets masked (last 4 chars only)."""
        masked = {}
        for key, value in (self.credentials or {}).items():
            if isinstance(value, str) and len(value) > 4:
                masked[key] = "****" + value[-4:]
            else:
                masked[key] = "****"
        return masked


def _extract_secret(credentials):
    """Return the app secret from a credentials dict, accepting either spelling."""
    creds = credentials or {}
    return creds.get("app_secret") or creds.get("client_secret") or ""


def _workspace_credential_model():
    """Return the sidecar model when the zh_overrides app is installed, else None.

    Upstream test/CI settings don't install zh_overrides, and importing an
    uninstalled model raises at class construction — gate every sidecar lookup
    through this helper.
    """
    from django.apps import apps

    if not apps.is_installed("zh_overrides"):
        return None
    from zh_overrides.models import WorkspacePlatformCredential

    return WorkspacePlatformCredential


def resolve_platform_credentials(platform, org_id, workspace_id=None):
    """Return app credentials for ``platform``, with ``.env`` dominant.

    Resolution order:

    1. A complete ``.env`` config wins globally.
    2. The org's admin-entered ``PlatformCredential`` row wins — traditional
       mode: the whole org shares one app; workspace rows are ignored.
    3. Otherwise, when ``workspace_id`` is given, the workspace's own
       ``WorkspacePlatformCredential`` row is used (independent mode). A
       workspace without one is simply unconfigured — there is intentionally
       no fallback to a "default" workspace app.

    Returns a fresh dict.
    """
    from django.conf import settings

    env_creds = getattr(settings, "PLATFORM_CREDENTIALS_FROM_ENV", {}).get(platform, {})
    # .env wins only when it fully satisfies the platform's required keys, so a
    # partial env config can't shadow a complete admin-entered row.
    if derive_is_configured(platform, env_creds):
        return dict(env_creds)
    try:
        cred = PlatformCredential.objects.for_org(org_id).get(platform=platform, is_configured=True)
        return dict(cred.credentials)
    except PlatformCredential.DoesNotExist:
        workspace_model = _workspace_credential_model()
        if workspace_id is not None and workspace_model is not None:
            # Local-custom sidecar: workspace-scoped credentials (zh_overrides).
            try:
                ws_cred = workspace_model.objects.get(
                    workspace_id=workspace_id,
                    platform=platform,
                    is_configured=True,
                )
                return dict(ws_cred.credentials)
            except workspace_model.DoesNotExist:
                pass
        return dict(env_creds)


def resolve_app_secret(platform, org_id, workspace_id=None):
    """Return the single app secret for one org's platform (.env dominant).

    Used to bind inbound-webhook verification to the specific account/org being
    written, so one org's secret can't authorize events for another org.
    """
    return _extract_secret(resolve_platform_credentials(platform, org_id, workspace_id=workspace_id))


def resolve_app_secrets(*platforms):
    """Return all candidate app secrets for verifying inbound webhooks.

    Webhook verification authenticates an inbound event rather than selecting a
    single app, so we collect every secret that could legitimately have signed
    it: the env secret (if set) plus each configured org's admin-entered secret,
    across all the given platform keys (e.g. facebook + instagram share one Meta
    app). Deduped, env first.
    """
    from django.conf import settings

    env_map = getattr(settings, "PLATFORM_CREDENTIALS_FROM_ENV", {})
    secrets = []
    for platform in platforms:
        env_secret = _extract_secret(env_map.get(platform, {}))
        if env_secret and env_secret not in secrets:
            secrets.append(env_secret)
    for cred in PlatformCredential.objects.filter(platform__in=platforms, is_configured=True):
        secret = _extract_secret(cred.credentials)
        if secret and secret not in secrets:
            secrets.append(secret)
    # Local-custom sidecar: workspace-scoped rows are independent apps whose
    # webhooks hit the same shared endpoint, so their secrets must verify too.
    workspace_model = _workspace_credential_model()
    if workspace_model is not None:
        for cred in workspace_model.objects.filter(
            platform__in=platforms,
            is_configured=True,
        ):
            secret = _extract_secret(cred.credentials)
            if secret and secret not in secrets:
                secrets.append(secret)
    return secrets
