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
        connected = {
            (s.workspace_id, s.platform)
            for s in SocialAccount.objects.filter(workspace__organization=org, platform__in=PLATFORMS)
        }
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
    """Create the login account; the signup signal provisions org + 1 ws.

    Then make both memberships idempotent (the signal already creates them
    for a normal signup, but guaranteeing them here keeps this usable even if
    provisioning logic changes upstream).
    """
    email = (email or "").strip().lower()
    if not email:
        raise ConsoleError("登录邮箱不能为空。")
    if User.objects.filter(email__iexact=email).exists():
        raise ConsoleError(f"登录账号 {email} 已存在，请直接在矩阵中编辑该租户。")

    with transaction.atomic():
        user = User.objects.create_user(email=email, password=password or None, name="")
        # The accounts.post_save signal provisions org + default workspace;
        # look it up, and only create it ourselves if provisioning was absent.
        org = Organization.objects.filter(memberships__user=user).first()
        if org is None:
            # Defensive: provision now if the signal did not run.
            org = Organization.objects.create(name=organization_name or email.split("@")[0])
            ws = Workspace.objects.create(organization=org, name=organization_name or "My Workspace")
            from django.utils import timezone

            OrgMembership.objects.get_or_create(
                user=user, organization=org,
                defaults={"org_role": OrgMembership.OrgRole.OWNER, "accepted_at": timezone.now()},
            )
            WorkspaceMembership.objects.get_or_create(
                user=user, workspace=ws,
                defaults={"workspace_role": WorkspaceMembership.WorkspaceRole.OWNER},
            )
        if organization_name.strip():
            org.name = organization_name.strip()
            org.save(update_fields=["name"])
            first_ws = Workspace.objects.filter(organization=org).order_by("created_at").first()
            if first_ws and first_ws.name in ("My Workspace",):
                first_ws.name = organization_name.strip()
                first_ws.save(update_fields=["name"])
        # Guarantee memberships regardless of the provisioning path above.
        first_ws = Workspace.objects.filter(organization=org).order_by("created_at").first()
        from django.utils import timezone

        OrgMembership.objects.get_or_create(
            user=user, organization=org,
            defaults={"org_role": OrgMembership.OrgRole.OWNER, "accepted_at": timezone.now()},
        )
        if first_ws:
            WorkspaceMembership.objects.get_or_create(
                user=user, workspace=first_ws,
                defaults={"workspace_role": WorkspaceMembership.WorkspaceRole.OWNER},
            )
    return org


def save_tenant_mode(organization_id: str, mode: str, credentials: dict[str, OrgBundle]) -> None:
    """Switch tenant-wide mode and write org-level credentials.

    * traditional: upsert complete org rows for BOTH platforms; incomplete
      pairs are rejected (keeps "all or nothing" at the tenant level).
    * independent: delete any org rows for both platforms so every workspace
      is resolved from its own row.
    """
    if mode not in ("traditional", "independent"):
        raise ConsoleError("模式取值非法。")
    org = Organization.objects.filter(id=organization_id).first()
    if org is None:
        raise ConsoleError("组织不存在。")

    with transaction.atomic():
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

    # Independent mode is a hard precondition for workspace-scoped rows.
    if PlatformCredential.objects.filter(organization=org, platform__in=PLATFORMS).exists():
        raise ConsoleError("该租户为通用模式：App 凭证在组织级统一配置，工作区凭证不生效。请先切换到独立模式。")

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
