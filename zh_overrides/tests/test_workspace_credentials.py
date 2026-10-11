"""Tests for workspace-scoped platform credentials (local-custom sidecar).

Run with:
    DJANGO_SETTINGS_MODULE=zh_overrides.test_settings pytest zh_overrides
"""

import pytest
from django.test import override_settings

from apps.credentials.models import (
    PlatformCredential,
    resolve_app_secret,
    resolve_app_secrets,
    resolve_platform_credentials,
)
from apps.organizations.models import Organization
from apps.workspaces.models import Workspace
from zh_overrides.models import WorkspacePlatformCredential

FB = {"client_id": "ORG_FB_ID", "client_secret": "ORG_FB_SECRET"}
WS1 = {"client_id": "WS1_FB_ID", "client_secret": "WS1_FB_SECRET"}
WS2 = {"client_id": "WS2_FB_ID", "client_secret": "WS2_FB_ID"}


@pytest.fixture
def org():
    return Organization.objects.create(name="Sidecar Org")


@pytest.fixture
def workspaces(org):
    w1 = Workspace.objects.create(organization=org, name="W1")
    w2 = Workspace.objects.create(organization=org, name="W2")
    return w1, w2


@pytest.mark.django_db
def test_workspace_credential_used_when_org_has_none(workspaces):
    w1, _w2 = workspaces
    WorkspacePlatformCredential.objects.create(workspace=w1, platform="facebook", credentials=WS1)

    assert resolve_platform_credentials("facebook", w1.organization_id, workspace_id=w1.id) == WS1


@pytest.mark.django_db
def test_unconfigured_when_neither_org_nor_workspace_row(workspaces):
    w1, _w2 = workspaces

    @override_settings(PLATFORM_CREDENTIALS_FROM_ENV={})
    def _run():
        assert resolve_platform_credentials("facebook", w1.organization_id, workspace_id=w1.id) == {}

    _run()


@pytest.mark.django_db
def test_workspace_rows_are_isolated_per_workspace(workspaces):
    w1, w2 = workspaces
    WorkspacePlatformCredential.objects.create(workspace=w1, platform="facebook", credentials=WS1)

    @override_settings(PLATFORM_CREDENTIALS_FROM_ENV={})
    def _run():
        # W2 has no row of its own: it must not borrow W1's credentials.
        assert resolve_platform_credentials("facebook", w2.organization_id, workspace_id=w2.id) == {}

    _run()


@pytest.mark.django_db
def test_org_row_wins_traditional_mode_even_with_workspace_row(workspaces):
    w1, _w2 = workspaces
    PlatformCredential.objects.create(organization=w1.organization, platform="facebook", credentials=FB)
    WorkspacePlatformCredential.objects.create(workspace=w1, platform="facebook", credentials=WS1)

    assert resolve_platform_credentials("facebook", w1.organization_id, workspace_id=w1.id) == FB


@pytest.mark.django_db
def test_complete_env_config_beats_both(org, workspaces):
    w1, _w2 = workspaces
    PlatformCredential.objects.create(organization=org, platform="threads", credentials={
        "client_id": "ORG_TH",
        "client_secret": "ORG_TH_SECRET",
    })
    WorkspacePlatformCredential.objects.create(workspace=w1, platform="threads", credentials={
        "client_id": "WS_TH",
        "client_secret": "WS_TH_SECRET",
    })
    env = {"threads": {"app_id": "ENV_TH", "app_secret": "ENV_TH_SECRET"}}

    @override_settings(PLATFORM_CREDENTIALS_FROM_ENV=env)
    def _run():
        result = resolve_platform_credentials("threads", org.id, workspace_id=w1.id)
        assert result["app_id"] == "ENV_TH"

    _run()


@pytest.mark.django_db
def test_incomplete_workspace_row_stays_inactive(workspaces):
    w1, _w2 = workspaces
    row = WorkspacePlatformCredential.objects.create(
        workspace=w1,
        platform="facebook",
        credentials={"client_id": "ONLY_ID"},
    )
    assert row.is_configured is False

    @override_settings(PLATFORM_CREDENTIALS_FROM_ENV={})
    def _run():
        assert resolve_platform_credentials("facebook", w1.organization_id, workspace_id=w1.id) == {}

    _run()


@pytest.mark.django_db
def test_resolve_app_secret_prefers_workspace_row(workspaces):
    w1, _w2 = workspaces
    WorkspacePlatformCredential.objects.create(workspace=w1, platform="facebook", credentials=WS1)

    @override_settings(PLATFORM_CREDENTIALS_FROM_ENV={})
    def _run():
        assert resolve_app_secret("facebook", w1.organization_id, workspace_id=w1.id) == "WS1_FB_SECRET"

    _run()


@pytest.mark.django_db
def test_app_secrets_union_includes_workspace_rows(workspaces):
    w1, w2 = workspaces
    PlatformCredential.objects.create(
        organization=w1.organization,
        platform="facebook",
        credentials={"client_id": "ORG_ID", "client_secret": "ORG_SECRET"},
    )
    WorkspacePlatformCredential.objects.create(workspace=w2, platform="facebook", credentials={
        "client_id": "W2_ID",
        "client_secret": "W2_SECRET",
    })

    @override_settings(PLATFORM_CREDENTIALS_FROM_ENV={})
    def _run():
        secrets = resolve_app_secrets("facebook")
        assert "ORG_SECRET" in secrets
        assert "W2_SECRET" in secrets

    _run()


@pytest.mark.django_db
def test_unique_together_workspace_platform(workspaces):
    from django.db import IntegrityError

    w1, _w2 = workspaces
    WorkspacePlatformCredential.objects.create(workspace=w1, platform="facebook", credentials=WS1)
    with pytest.raises(IntegrityError):
        WorkspacePlatformCredential.objects.create(workspace=w1, platform="facebook", credentials={
            "client_id": "DUP",
            "client_secret": "DUP_SECRET",
        })
