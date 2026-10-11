"""Tests for the superuser tenant configuration console services.

Run: DJANGO_SETTINGS_MODULE=zh_overrides.test_settings pytest zh_overrides
"""

import pytest

from apps.accounts.models import User
from apps.credentials.models import PlatformCredential, resolve_platform_credentials
from apps.members.models import OrgMembership, WorkspaceMembership
from apps.organizations.models import Organization
from apps.workspaces.models import Workspace
from zh_overrides import admin_console_services as svc
from zh_overrides.models import WorkspaceMeta, WorkspacePlatformCredential

FB = {"client_id": "FB1", "client_secret": "FBS"}
IG = {"client_id": "IG1", "client_secret": "IGS"}


@pytest.fixture
def org_and_owner(db):
    org = Organization.objects.create(name="T1")
    user = User.objects.create_user(email="t1@x.com", password="pw12345678")
    ws = Workspace.objects.create(organization=org, name="W1")
    OrgMembership.objects.create(user=user, organization=org, org_role=OrgMembership.OrgRole.OWNER)
    WorkspaceMembership.objects.create(user=user, workspace=ws, workspace_role=WorkspaceMembership.WorkspaceRole.OWNER)
    return org, user, ws


@pytest.mark.django_db
def test_create_tenant_provisions_org_workspace_and_memberships():
    org = svc.create_tenant("new@x.com", "pw12345678", "租户A")

    user = User.objects.get(email="new@x.com")
    assert OrgMembership.objects.filter(user=user, organization=org, org_role="owner").exists()
    ws = Workspace.objects.get(organization=org)
    assert WorkspaceMembership.objects.filter(user=user, workspace=ws, workspace_role="owner").exists()
    assert ws.name == "租户A"
    assert org.name == "租户A"


@pytest.mark.django_db
def test_create_tenant_duplicate_email_rejected(db):
    User.objects.create_user(email="dup@x.com", password="pw12345678")
    with pytest.raises(svc.ConsoleError):
        svc.create_tenant("DUP@x.com", "pw12345678", "X")


@pytest.mark.django_db
def test_traditional_mode_writes_org_rows_and_shares(org_and_owner):
    org, _user, ws = org_and_owner
    svc.save_tenant_mode(str(org.id), "traditional", {svc.FB: svc.OrgBundle("FB1", "FBS"),
                                                       svc.IG: svc.OrgBundle("IG1", "IGS")})

    assert PlatformCredential.objects.filter(organization=org, platform="facebook").count() == 1
    got = resolve_platform_credentials("facebook", org.id, workspace_id=ws.id)
    assert got["client_id"] == "FB1"


@pytest.mark.django_db
def test_traditional_mode_requires_both_fields(org_and_owner):
    org, _u, _w = org_and_owner
    with pytest.raises(svc.ConsoleError):
        svc.save_tenant_mode(str(org.id), "traditional",
                             {svc.FB: svc.OrgBundle("onlyid", ""), svc.IG: svc.OrgBundle("IG1", "IGS")})


@pytest.mark.django_db
def test_switch_to_independent_deletes_org_rows(org_and_owner):
    org, _u, ws = org_and_owner
    svc.save_tenant_mode(str(org.id), "traditional", {svc.FB: svc.OrgBundle(**FB),
                                                       svc.IG: svc.OrgBundle(**IG)})
    svc.save_tenant_mode(str(org.id), "independent", {})
    assert not PlatformCredential.objects.filter(organization=org).exists()


@pytest.mark.django_db
def test_independent_workspace_credential_isolated(org_and_owner):
    org, user, w1 = org_and_owner
    w2 = Workspace.objects.create(organization=org, name="W2")
    WorkspaceMembership.objects.create(user=user, workspace=w2, workspace_role="owner")

    svc.upsert_workspace(str(org.id), "W1", str(w1.id),
                         {svc.FB: svc.OrgBundle(**FB), svc.IG: svc.OrgBundle(**IG)},
                         {svc.FB: "FB tester A", svc.IG: "IG tester A"})

    # W1 resolves its own app; W2 is unconfigured (no fallback to W1).
    assert resolve_platform_credentials("facebook", org.id, workspace_id=w1.id)["client_id"] == "FB1"
    from apps.credentials.models import derive_is_configured
    assert derive_is_configured("facebook", resolve_platform_credentials("facebook", org.id, workspace_id=w2.id)) is False
    meta = WorkspaceMeta.objects.get(workspace=w1)
    assert meta.fb_tester_note == "FB tester A"


@pytest.mark.django_db
def test_upsert_workspace_creates_new_with_owner_membership(org_and_owner):
    org, user, _w = org_and_owner
    ws = svc.upsert_workspace(str(org.id), "W3", None,
                              {svc.FB: svc.OrgBundle(**FB), svc.IG: svc.OrgBundle(**IG)}, {})
    assert WorkspaceMembership.objects.filter(user=user, workspace=ws, workspace_role="owner").exists()
    assert WorkspacePlatformCredential.objects.filter(workspace=ws).count() == 2


@pytest.mark.django_db
def test_partial_credential_pair_rejected(org_and_owner):
    org, _u, w1 = org_and_owner
    with pytest.raises(svc.ConsoleError):
        svc.upsert_workspace(str(org.id), "W1", str(w1.id),
                             {svc.FB: svc.OrgBundle("x", ""), svc.IG: svc.OrgBundle("", "")}, {})


@pytest.mark.django_db
def test_workspace_credential_rejected_in_traditional_mode(org_and_owner):
    org, _u, w1 = org_and_owner
    svc.save_tenant_mode(str(org.id), "traditional", {svc.FB: svc.OrgBundle(**FB),
                                                       svc.IG: svc.OrgBundle(**IG)})
    with pytest.raises(svc.ConsoleError):
        svc.upsert_workspace(str(org.id), "W1", str(w1.id),
                             {svc.FB: svc.OrgBundle("OTHER", "OTHERS"), svc.IG: svc.OrgBundle("", "")}, {})


@pytest.mark.django_db
def test_archive_unarchive_and_delete(org_and_owner):
    org, _u, w1 = org_and_owner
    svc.archive_workspace(str(org.id), str(w1.id))
    assert Workspace.objects.get(id=w1.id).is_archived is True
    svc.unarchive_workspace(str(org.id), str(w1.id))
    assert Workspace.objects.get(id=w1.id).is_archived is False
    svc.delete_workspace(str(org.id), str(w1.id))
    assert not Workspace.objects.filter(id=w1.id).exists()


@pytest.mark.django_db
def test_load_tenants_reports_mode_and_rows(org_and_owner):
    org, _u, w1 = org_and_owner
    svc.upsert_workspace(str(org.id), "W1", str(w1.id),
                         {svc.FB: svc.OrgBundle(**FB), svc.IG: svc.OrgBundle(**IG)}, {})
    tenants = svc.load_tenants()
    t = next(x for x in tenants if x.organization_id == str(org.id))
    assert t.mode == "independent"
    assert t.owner_email == "t1@x.com"
    row = next(r for r in t.workspaces if r.workspace_id == str(w1.id))
    assert row.fb.client_id == "FB1"
    assert row.fb_connected is False
