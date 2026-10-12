"""Service layer for the superuser tenant-configuration console.

Every write goes through these functions so the credential isolation rules
live in one place and are impossible to bypass from the view layer:

* **traditional mode** — org-level PlatformCredential rows exist for a
  platform; every workspace shares the org app and workspace rows are never
  read by the resolver.
* **independent mode** — no org-level rows exist; each workspace is resolved
  strictly from its own WorkspacePlatformCredential row.

The two modes never mix per platform, and a workspace credential row can
never satisfy a request for a different workspace (the resolver filters by
workspace_id).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from django.db import transaction

from apps.accounts.models import User
from apps.credentials.models import PlatformCredential
from apps.members.models import OrgMembership, WorkspaceMembership
from apps.organizations.models import Organization
from apps.social_accounts.models import SocialAccount
from apps.workspaces.models import Workspace

from .models import WorkspaceMeta, WorkspacePlatformCredential

FB = "facebook"
IG = "instagram_login"
PLATFORMS = (FB, IG)
PLATFORM_LABELS = {FB: "Facebook", IG: "Instagram (Direct)"}


class ConsoleError(ValueError):
    """User-facing configuration error (rendered as a flash message)."""


@dataclass
class OrgBundle:
    """Credentials for one platform in the two supported shapes."""

    client_id: str = ""
    client_secret: str = ""

    def as_json(self) -> dict:
        return {"client_id": self.client_id.strip(), "client_secret": self.client_secret.strip()}

    @classmethod
    def from_row(cls, row) -> OrgBundle:
        creds = row.credentials or {}
        return cls(
            client_id=str(creds.get("client_id") or creds.get("app_id") or ""),
            client_secret=str(creds.get("client_secret") or creds.get("app_secret") or ""),
        )


@dataclass
class AccountRow:
    """A connected social account ("member" under a workspace node)."""

    account_id: str
    platform: str
    platform_label: str
    name: str
    handle: str
    platform_account_id: str
    connected_at: object | None
    webhooks_active: bool | None
    connection_status: str
    token_expires_at: object | None
    last_health_check_at: object | None
    last_error: str


@dataclass
class WorkspaceRow:
    workspace_id: str | None
    name: str
    is_archived: bool
    fb: OrgBundle = field(default_factory=OrgBundle)
    ig: OrgBundle = field(default_factory=OrgBundle)
    fb_note: str = ""
    ig_note: str = ""
    fb_connected: bool = False
    ig_connected: bool = False
    accounts: list[AccountRow] = field(default_factory=list)
    is_new: bool = False


@dataclass
class TenantRow:
    organization_id: str
    organization_name: str
    owner_email: str
    mode: str  # "traditional" | "independent"
    org_credentials: dict[str, OrgBundle]
    workspaces: list[WorkspaceRow]


def load_tenants() -> list[TenantRow]:
    """Read the full console matrix (organisations + creds + notes)."""
    tenants: list[TenantRow] = []
    for org in Organization.objects.prefetch_related("workspaces").all().order_by("created_at"):
        org_rows = {
            c.platform: OrgBundle.from_row(c)
            for c in PlatformCredential.objects.filter(organization=org, platform__in=PLATFORMS)
        }
        # Mode follows the credential facts, never a stored flag: any complete
        # org row means traditional mode for that platform. The console uses a
        # single tenant-wide mode, derived from whether *either* platform has
        # an org row — the save layer always writes/deletes both together.
        mode = "traditional" if org_rows else "independent"

        ws_rows: list[WorkspaceRow] = []
        workspaces = list(Workspace.objects.filter(organization=org).order_by("is_archived", "created_at"))
        cred_map = {
            (c.workspace_id, c.platform): c
            for c in WorkspacePlatformCredential.objects.filter(
                workspace__organization=org, platform__in=PLATFORMS
            )
        }
        meta_map = {m.workspace_id: m for m in WorkspaceMeta.objects.filter(workspace__organization=org)}
        social_qs = SocialAccount.objects.filter(
            workspace__organization=org, platform__in=PLATFORMS
        ).order_by("platform", "account_name")
        connected = {(s.workspace_id, s.platform) for s in social_qs}
        accounts_by_ws: dict = {}
        for s in social_qs:
            accounts_by_ws.setdefault(s.workspace_id, []).append(
                AccountRow(
                    account_id=str(s.id),
                    platform=s.platform,
                    platform_label=PLATFORM_LABELS.get(s.platform, s.platform),
                    name=s.account_name or s.account_handle or s.account_platform_id,
                    handle=s.account_handle or "",
                    platform_account_id=s.account_platform_id or "",
                    connected_at=s.connected_at,
                    webhooks_active=s.webhooks_active,
                    connection_status=s.connection_status or "",
                    token_expires_at=s.token_expires_at,
                    last_health_check_at=s.last_health_check_at,
                    last_error=s.last_error or "",
                )
            )
        owner = (
            OrgMembership.objects.filter(organization=org)
            .select_related("user")
            .order_by("accepted_at")
            .first()
        )
        for ws in workspaces:
            row = WorkspaceRow(
                workspace_id=str(ws.id),
                name=ws.name,
                is_archived=ws.is_archived,
                fb_note=getattr(meta_map.get(ws.id), "fb_tester_note", ""),
                ig_note=getattr(meta_map.get(ws.id), "ig_tester_note", ""),
                fb_connected=(ws.id, FB) in connected,
                ig_connected=(ws.id, IG) in connected,
                accounts=accounts_by_ws.get(ws.id, []),
            )
            fb_row = cred_map.get((ws.id, FB))
            ig_row = cred_map.get((ws.id, IG))
            if fb_row:
                row.fb = OrgBundle.from_row(fb_row)
            if ig_row:
                row.ig = OrgBundle.from_row(ig_row)
            ws_rows.append(row)

        tenants.append(
            TenantRow(
                organization_id=str(org.id),
                organization_name=org.name,
                owner_email=owner.user.email if owner and owner.user else "",
                mode=mode,
                org_credentials={p: org_rows.get(p, OrgBundle()) for p in PLATFORMS},
                workspaces=ws_rows,
            )
        )
    return tenants


# ---------------------------------------------------------------- write side


def create_tenant(email: str, password: str, organization_name: str) -> Organization:
    """Create the login account and reuse the signal-provisioned org.

    The ``accounts`` post_save signal creates a default ``My Organization``
    + ``My Workspace`` for every new user (same upstream behaviour as normal
    sign-up and raw Admin user creation). We must NOT create a second org:
    rename that auto-provisioned org/workspace to the requested names.

    We also register a *verified* allauth ``EmailAddress``: without one,
    ``SOCIALACCOUNT_EMAIL_AUTHENTICATION`` fails to match the tenant's first
    Google login, which allauth then treats as a brand-new user and
    provisions a second organisation (observed duplicate-tenant bug).
    """
    from allauth.account.models import EmailAddress

    email = (email or "").strip().lower()
    name = (organization_name or "").strip() or email.split("@")[0]
    if not email:
        raise ConsoleError("登录邮箱不能为空。")
    if User.objects.filter(email__iexact=email).exists():
        raise ConsoleError(f"登录账号 {email} 已存在，请直接在矩阵中编辑该租户。")

    with transaction.atomic():
        # post_save signal provisions org + default workspace + memberships
        user = User.objects.create_user(email=email, password=password or None, name="")

        membership = (
            OrgMembership.objects.filter(user=user)
            .select_related("organization")
            .order_by("accepted_at")
            .first()
        )
        if membership is None:
            # Defensive fallback only (signal disabled / custom user factory)
            org = Organization.objects.create(name=name)
            first_ws = Workspace.objects.create(organization=org, name=name)
            OrgMembership.objects.create(
                user=user, organization=org, org_role=OrgMembership.OrgRole.OWNER
            )
            WorkspaceMembership.objects.create(
                user=user, workspace=first_ws,
                workspace_role=WorkspaceMembership.WorkspaceRole.OWNER,
            )
        else:
            org = membership.organization
            if org.name != name:
                org.name = name
                org.save(update_fields=["name", "updated_at"])
            first_ws = (
                Workspace.objects.filter(organization=org).order_by("created_at").first()
            )
            if first_ws and first_ws.name == "My Workspace":
                first_ws.name = name
                first_ws.save(update_fields=["name", "updated_at"])
            WorkspaceMembership.objects.get_or_create(
                user=user, workspace=first_ws,
                defaults={"workspace_role": WorkspaceMembership.WorkspaceRole.OWNER},
            )

        # Verified primary email -> first Google SSO matches this user,
        # instead of auto-creating a duplicate user/organisation.
        EmailAddress.objects.update_or_create(
            user=user, email=email,
            defaults={"verified": True, "primary": True},
        )
    return org


def save_tenant_mode(
    organization_id: str,
    mode: str,
    credentials: dict[str, OrgBundle],
    organization_name: str | None = None,
) -> None:
    """Switch tenant-wide mode and write org-level credentials.

    * traditional: upsert complete org rows for BOTH platforms; incomplete
      pairs are rejected (keeps "all or nothing" at the tenant level).
    * independent: delete any org rows for both platforms so every workspace
      is resolved from its own row.

    ``organization_name`` (when given) renames the organisation — in
    independent mode this makes the same save button a plain rename.
    """
    if mode not in ("traditional", "independent"):
        raise ConsoleError("模式取值非法。")
    org = Organization.objects.filter(id=organization_id).first()
    if org is None:
        raise ConsoleError("组织不存在。")

    with transaction.atomic():
        new_name = (organization_name or "").strip()
        if new_name and new_name != org.name:
            org.name = new_name
            org.save(update_fields=["name", "updated_at"])

        if mode == "traditional":
            for platform in PLATFORMS:
                bundle = credentials.get(platform) or OrgBundle()
                data = bundle.as_json()
                if not data["client_id"] or not data["client_secret"]:
                    raise ConsoleError(f"{PLATFORM_LABELS[platform]} 的 App ID 与 App Secret 必须同时填写。")
                _upsert_org_credential(org, platform, data)
        else:
            PlatformCredential.objects.filter(organization=org, platform__in=PLATFORMS).delete()


def _upsert_org_credential(org: Organization, platform: str, data: dict) -> None:
    row = PlatformCredential.objects.filter(organization=org, platform=platform).first()
    if row:
        row.credentials = data
        row.save(update_fields=["credentials", "is_configured", "updated_at"])
    else:
        PlatformCredential.objects.create(organization=org, platform=platform, credentials=data)


def _upsert_ws_credential(workspace: Workspace, platform: str, data: dict) -> None:
    row = WorkspacePlatformCredential.objects.filter(workspace=workspace, platform=platform).first()
    if row:
        row.credentials = data
        row.save(update_fields=["credentials", "is_configured", "updated_at"])
    else:
        WorkspacePlatformCredential.objects.create(workspace=workspace, platform=platform, credentials=data)


def upsert_workspace(
    organization_id: str,
    name: str,
    workspace_id: str | None,
    credentials: dict[str, OrgBundle],
    notes: dict[str, str],
) -> Workspace:
    """Create or rename one workspace and attach its credentials/notes.

    Workspace create/rename/notes are allowed in BOTH modes (raw Admin allows
    creating workspaces for any organisation; a traditional-mode tenant can
    have many workspaces sharing the org-level App). Only *workspace-scoped
    credential writes* are rejected in traditional mode.

    Credentials are written ONLY when both fields are non-empty. A partial
    pair is an explicit error (never stored half-configured). Empty pairs
    leave any existing row untouched — blank rows mean "not configured".
    """
    org = Organization.objects.filter(id=organization_id).first()
    if org is None:
        raise ConsoleError("组织不存在。")
    name = (name or "").strip()
    if not name:
        raise ConsoleError("工作区名称不能为空。")

    traditional_mode = PlatformCredential.objects.filter(
        organization=org, platform__in=PLATFORMS
    ).exists()

    credential_values_present = any(
        (credentials.get(p) or OrgBundle()).client_id.strip()
        or (credentials.get(p) or OrgBundle()).client_secret.strip()
        for p in PLATFORMS
    )
    if traditional_mode and credential_values_present:
        raise ConsoleError(
            "该租户为通用模式：App 凭证在组织级统一配置并由全部工作区共享，"
            "工作区不能单独配置凭证。如需独立 App，请先切换到独立模式。"
        )

    with transaction.atomic():
        owner_membership = (
            OrgMembership.objects.filter(
                organization=org, org_role=OrgMembership.OrgRole.OWNER
            )
            .select_related("user")
            .first()
        )
        if workspace_id:
            workspace = Workspace.objects.filter(id=workspace_id, organization=org).first()
            if workspace is None:
                raise ConsoleError("工作区不存在或不属于该组织。")
            workspace.name = name
            workspace.save(update_fields=["name", "updated_at"])
        else:
            workspace = Workspace.objects.create(organization=org, name=name)
            if owner_membership:
                WorkspaceMembership.objects.get_or_create(
                    user=owner_membership.user,
                    workspace=workspace,
                    defaults={"workspace_role": WorkspaceMembership.WorkspaceRole.OWNER},
                )

        for platform in PLATFORMS:
            bundle = credentials.get(platform) or OrgBundle()
            cid, secret = bundle.client_id.strip(), bundle.client_secret.strip()
            if bool(cid) != bool(secret):
                raise ConsoleError(
                    f"工作区「{name}」的 {PLATFORM_LABELS[platform]} App ID 与 App Secret 必须同时填写或同时留空。"
                )
            if cid and secret:
                _upsert_ws_credential(workspace, platform, {"client_id": cid, "client_secret": secret})

        meta, _created = WorkspaceMeta.objects.get_or_create(workspace=workspace)
        meta.fb_tester_note = (notes.get(FB) or "").strip()[:500]
        meta.ig_tester_note = (notes.get(IG) or "").strip()[:500]
        meta.save(update_fields=["fb_tester_note", "ig_tester_note", "updated_at"])
    return workspace


def archive_workspace(organization_id: str, workspace_id: str) -> None:
    """Reversible hide: posts/accounts/credentials are retained."""
    ws = Workspace.objects.filter(id=workspace_id, organization_id=organization_id).first()
    if ws is None:
        raise ConsoleError("工作区不存在或不属于该组织。")
    ws.is_archived = True
    ws.save(update_fields=["is_archived", "updated_at"])


def unarchive_workspace(organization_id: str, workspace_id: str) -> None:
    ws = Workspace.objects.filter(id=workspace_id, organization_id=organization_id).first()
    if ws is None:
        raise ConsoleError("工作区不存在或不属于该组织。")
    ws.is_archived = False
    ws.save(update_fields=["is_archived", "updated_at"])


def delete_workspace(organization_id: str, workspace_id: str) -> None:
    """Hard delete (CASCADE: posts, accounts, credentials). Guarded in UI."""
    ws = Workspace.objects.filter(id=workspace_id, organization_id=organization_id).first()
    if ws is None:
        raise ConsoleError("工作区不存在或不属于该组织。")
    ws.delete()


def delete_organization(organization_id: str) -> int:
    """Hard-delete a whole tenant organisation (CASCADE: everything).

    Returns the number of workspaces removed, for the confirmation message.
    """
    org = Organization.objects.filter(id=organization_id).first()
    if org is None:
        raise ConsoleError("组织不存在。")
    ws_count = Workspace.objects.filter(organization=org).count()
    org.delete()
    return ws_count


# ---------------------------------------------------------------- credential probe


# Meta token endpoints reject a bogus authorization code with HTTP 400 either
# way. The *shape* of the error tells us whether the app credentials
# themselves were accepted — no access token is ever issued or stored.
_FB_TOKEN_URL = "https://graph.facebook.com/v25.0/oauth/access_token"
_IG_TOKEN_URL = "https://api.instagram.com/oauth/access_token"

# Error substrings that mean "the app was authenticated; only the fake code
# was wrong" → credentials are valid.
_CODE_REJECTION_MARKERS = (
    "code", "verification code", "matching code", "authorization code",
    "redirect_uri", "redirect", "invalid request",
)
_APP_REJECTION_MARKERS = (
    "validating application", "invalid client", "client_id", "client_secret",
    "application info", "invalid app", "appsecret", "api key",
)


def probe_credential(platform: str, bundle: OrgBundle) -> tuple[bool, str]:
    """Validate an App ID/Secret pair WITHOUT any user authorisation.

    Returns ``(ok, detail)``. A pair is considered valid when Meta's token
    endpoint authenticates the app and only rejects the dummy code. Network or
    unexpected responses report ``(False, reason)`` so the operator is never
    told "valid" on ambiguity.
    """
    import httpx

    cid = (bundle.client_id or "").strip()
    csec = (bundle.client_secret or "").strip()
    if not cid or not csec:
        return False, "App ID 与 App Secret 必须同时填写。"
    if not cid.isdigit():
        return False, "App ID 应为纯数字。"

    dummy_code = "zh_console_probe_invalid_code_000000"
    try:
        if platform == FB:
            resp = httpx.post(
                _FB_TOKEN_URL,
                params={
                    "client_id": cid,
                    "client_secret": csec,
                    "grant_type": "authorization_code",
                    "redirect_uri": "https://v.ysec.cn/social-accounts/callback/facebook/",
                    "code": dummy_code,
                },
                timeout=12,
            )
        elif platform == IG:
            resp = httpx.post(
                _IG_TOKEN_URL,
                files={
                    "client_id": (None, cid),
                    "client_secret": (None, csec),
                    "grant_type": (None, "authorization_code"),
                    "redirect_uri": (None, "https://v.ysec.cn/social-accounts/callback/instagram_login/"),
                    "code": (None, dummy_code),
                },
                timeout=12,
            )
        else:
            return False, f"暂不支持平台 {platform} 的凭证探测。"
    except Exception as exc:
        return False, f"网络请求失败（未能连通 Meta）：{type(exc).__name__}"

    try:
        data = resp.json()
    except Exception:
        return False, f"Meta 返回非预期内容（HTTP {resp.status_code}），请稍后重试。"

    err = data.get("error") or {}
    message = " ".join(
        str(err.get(k) or data.get(k) or "")
        for k in ("message", "error_message", "error_type", "type")
    ).lower()
    code = err.get("code")

    # Unexpected: a token came back for a dummy code must never happen; treat
    # as inconclusive rather than "valid".
    if data.get("access_token"):
        return False, "探测出现异常响应（返回了访问令牌），请人工核对，勿继续使用。"

    app_bad = any(m in message for m in _APP_REJECTION_MARKERS)
    code_bad = any(m in message for m in _CODE_REJECTION_MARKERS)
    redirect_missing = "redirect_uri" in message or "redirect" in message

    if app_bad and not code_bad:
        return False, f"App 凭证无效（Meta 拒绝应用身份）：{message[:160] or code}"
    if code_bad:
        if redirect_missing:
            return True, "App 凭证有效，但 Meta 提示回调地址（redirect_uri）未在该 App 登记，请检查 OAuth 跳转 URI。"
        return True, "App 凭证有效：Meta 已接受应用身份，仅拒绝了测试用假授权码（符合预期）。"
    if code in (100,):
        return True, "App 凭证有效：Meta 已接受应用身份，仅拒绝了测试用假授权码（符合预期）。"
    # Fall back to known FB sub-codes: 101 = invalid api key/app.
    if code in (101, 190, 191):
        return False, f"App 凭证可能无效（Meta 错误码 {code}）：{message[:160]}"
    return False, f"无法确定凭证状态（HTTP {resp.status_code}，code={code}）：{message[:160]}"
