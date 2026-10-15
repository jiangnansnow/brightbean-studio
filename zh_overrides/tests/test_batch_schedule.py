"""作曲器「文件夹」模式一键批量入队服务测试（zh_overrides 本地定制）。

Run with:
    DJANGO_SETTINGS_MODULE=zh_overrides.test_settings pytest zh_overrides/tests/test_batch_schedule.py
"""

from datetime import time

import pytest

from apps.accounts.models import User
from apps.calendar.models import PostingSlot, Queue
from apps.composer.models import PlatformPost, Post, PostMedia
from apps.media_library.models import MediaAsset, MediaFolder
from apps.organizations.models import Organization
from apps.social_accounts.models import SocialAccount
from apps.workspaces.models import Workspace
from zh_overrides import batch_schedule
from zh_overrides.batch_schedule import BatchScheduleError
from zh_overrides.models import ZhScheduledBatch, ZhScheduledBatchItem

pytestmark = pytest.mark.django_db


@pytest.fixture
def actor():
    return User.objects.create_user(email="maker@example.com", password="x", name="Maker")


@pytest.fixture
def workspace():
    org = Organization.objects.create(name="Org")
    return Workspace.objects.create(organization=org, name="WS")


def _account(workspace, platform, slug, connection_status=None):
    kwargs = {}
    if connection_status is not None:
        kwargs["connection_status"] = connection_status
    return SocialAccount.objects.create(
        workspace=workspace,
        platform=platform,
        account_platform_id=f"pid-{slug}",
        account_name=f"Name {slug}",
        **kwargs,
    )


def _queue_with_slots(workspace, account, slug, slot_times=()):
    queue = Queue.objects.create(workspace=workspace, name=f"Q {slug}", social_account=account)
    for day, t in slot_times:
        PostingSlot.objects.create(social_account=account, day_of_week=day, time=t)
    return queue


def _all_week_slots():
    # 每天一个 09:00 时段 → 未来 7 天内 7 个空槽。
    return [(day, time(9, 0)) for day in range(7)]


@pytest.fixture
def folder(workspace):
    return MediaFolder.objects.create(
        organization=workspace.organization, workspace=workspace, name="Folder A"
    )


def _video(workspace, folder, slug, *, status="completed", duration=50, has_file=True,
           media_type="video"):
    asset = MediaAsset.objects.create(
        organization=workspace.organization,
        workspace=workspace,
        folder=folder,
        filename=f"{slug}.mp4",
        media_type=media_type,
        processing_status=status,
        duration=duration,
    )
    if has_file:
        asset.file.name = f"media_library/{slug}.mp4"
        asset.save(update_fields=["file"])
    return asset


def _targets(workspace, *slugs):
    return [
        SocialAccount.objects.get(workspace=workspace, account_platform_id=f"pid-{s}")
        for s in slugs
    ]


def test_eligible_only_completed_videos_with_file_and_duration(workspace, folder):
    _video(workspace, folder, "ok")
    _video(workspace, folder, "pending", status="processing")
    _video(workspace, folder, "failed", status="failed")
    _video(workspace, folder, "zerosec", duration=0)
    _video(workspace, folder, "nofile", has_file=False)
    _video(workspace, folder, "image", media_type="image")

    assets = batch_schedule.eligible_assets(workspace, folder, [])
    assert [a.filename for a in assets] == ["ok.mp4"]


def test_assets_fifo_and_active_post_reverse_lookup(workspace, folder, actor):
    v1 = _video(workspace, folder, "first")
    v2 = _video(workspace, folder, "second")
    v3 = _video(workspace, folder, "third")
    account = _account(workspace, "instagram", "ig")
    _queue_with_slots(workspace, account, "ig", _all_week_slots())

    # v2 已在该账号上有 scheduled 帖（模拟文件夹素材已被排过一次）。
    post = Post.objects.create(workspace=workspace, author=actor, caption="x")
    PostMedia.objects.create(post=post, media_asset=v2, position=0)
    PlatformPost.objects.create(
        post=post, social_account=account, status=PlatformPost.Status.SCHEDULED
    )

    assets = batch_schedule.eligible_assets(workspace, folder, [account])
    assert list(assets) == [v1, v3]


def test_plan_default_is_min_of_videos_and_slots(workspace, folder):
    for i in range(10):
        _video(workspace, folder, f"v{i}")
    a = _account(workspace, "instagram", "ig")
    b = _account(workspace, "facebook", "fb")
    _queue_with_slots(workspace, a, "ig", [(d, time(9, 0)) for d in range(7)])  # 7 槽
    _queue_with_slots(workspace, b, "fb", [(0, time(9, 0)), (1, time(9, 0))])  # 2 槽

    plan = batch_schedule.build_plan(workspace, folder, [a.id, b.id])
    assert plan["eligible"] == 10
    assert plan["slots"][str(a.id)] == 7
    assert plan["slots"][str(b.id)] == 2
    assert plan["min_slots"] == 2
    assert plan["default"] == 2


def test_enqueue_creates_one_post_per_video_on_every_account(workspace, folder, actor):
    videos = [_video(workspace, folder, f"v{i}") for i in range(5)]
    a = _account(workspace, "instagram", "ig")
    b = _account(workspace, "facebook", "fb")
    _queue_with_slots(workspace, a, "ig", _all_week_slots())
    _queue_with_slots(workspace, b, "fb", _all_week_slots())

    # 7 天视界内实际空槽数取决于测试运行时刻（当天 09:00 是否已过），
    # 期望值直接用同一口径函数算出，避免时间相关的脆弱断言。
    expected = min(
        5,
        len(batch_schedule.open_slot_datetimes(a)),
        len(batch_schedule.open_slot_datetimes(b)),
    )

    batch, n = batch_schedule.enqueue_batch(
        workspace=workspace,
        user=actor,
        folder=folder,
        account_ids=[a.id, b.id],
        count=5,
        caption="Hello",
    )
    assert n == expected
    assert Post.objects.filter(workspace=workspace).count() == n
    posts = list(Post.objects.filter(workspace=workspace).order_by("created_at"))
    for post in posts:
        assert post.caption == "Hello"
        assert list(
            post.platform_posts.values_list("social_account_id", flat=True).order_by(
                "social_account_id"
            )
        ) == sorted([a.id, b.id])
        assert all(pp.status == "scheduled" for pp in post.platform_posts.all())
    assert ZhScheduledBatchItem.objects.filter(batch=batch).count() == n
    # FIFO：前 n 个视频入队。
    used = set(
        ZhScheduledBatchItem.objects.filter(batch=batch).values_list(
            "media_asset_id", flat=True
        )
    )
    assert used == {v.id for v in videos[:n]}


def test_enqueue_respects_requested_count_and_clamps_to_slots(workspace, folder, actor):
    for i in range(10):
        _video(workspace, folder, f"v{i}")
    a = _account(workspace, "instagram", "ig")
    _queue_with_slots(workspace, a, "ig", _all_week_slots())

    _, n = batch_schedule.enqueue_batch(
        workspace=workspace, user=actor, folder=folder, account_ids=[a.id], count=2
    )
    assert n == 2
    assert Post.objects.filter(workspace=workspace).count() == 2


def test_enqueue_rejects_when_no_slots_within_horizon(workspace, folder, actor):
    _video(workspace, folder, "v1")
    a = _account(workspace, "instagram", "ig")
    # 有队列但没有任何 PostingSlot → 7 天内 0 槽。
    Queue.objects.create(workspace=workspace, name="Q", social_account=a)
    with pytest.raises(BatchScheduleError):
        batch_schedule.enqueue_batch(
            workspace=workspace, user=actor, folder=folder, account_ids=[a.id], count=1
        )


def test_enqueue_ignores_disconnected_and_queue_less_accounts(workspace, folder, actor):
    _video(workspace, folder, "v1")
    dead = _account(
        workspace, "instagram", "dead",
        connection_status=SocialAccount.ConnectionStatus.DISCONNECTED,
    )
    noqueue = _account(workspace, "facebook", "noq")
    good = _account(workspace, "threads", "th")
    _queue_with_slots(workspace, good, "th", _all_week_slots())

    targets, ignored = batch_schedule.resolve_targets(
        workspace, [dead.id, noqueue.id, good.id]
    )
    assert [a.id for a, _ in targets] == [good.id]
    assert {name for name, _ in ignored} == {f"Name {s}" for s in ("dead", "noq")}

    batch, n = batch_schedule.enqueue_batch(
        workspace=workspace,
        user=actor,
        folder=folder,
        account_ids=[dead.id, noqueue.id, good.id],
        count=1,
    )
    assert n == 1


def test_enqueue_all_invalid_accounts_raises(workspace, folder, actor):
    _video(workspace, folder, "v1")
    dead = _account(
        workspace, "instagram", "dead",
        connection_status=SocialAccount.ConnectionStatus.DISCONNECTED,
    )
    with pytest.raises(BatchScheduleError):
        batch_schedule.enqueue_batch(
            workspace=workspace, user=actor, folder=folder, account_ids=[dead.id], count=1
        )


def test_enqueue_blocks_when_approval_required(workspace, folder, actor):
    _video(workspace, folder, "v1")
    a = _account(workspace, "instagram", "ig")
    _queue_with_slots(workspace, a, "ig", _all_week_slots())
    workspace.approval_workflow_mode = "required_internal"
    workspace.save(update_fields=["approval_workflow_mode"])

    with pytest.raises(BatchScheduleError):
        batch_schedule.enqueue_batch(
            workspace=workspace, user=actor, folder=folder, account_ids=[a.id], count=1
        )
    assert Post.objects.filter(workspace=workspace).count() == 0


def test_clear_batch_deletes_scheduled_keeps_published(workspace, folder, actor):
    v1 = _video(workspace, folder, "v1")
    v2 = _video(workspace, folder, "v2")
    a = _account(workspace, "instagram", "ig")
    _queue_with_slots(workspace, a, "ig", _all_week_slots())

    batch, n = batch_schedule.enqueue_batch(
        workspace=workspace, user=actor, folder=folder, account_ids=[a.id], count=2
    )
    assert n == 2

    # 模拟其中一条已发布（历史，不可清除）。
    published_item = ZhScheduledBatchItem.objects.filter(batch=batch).select_related(
        "post"
    ).first()
    published_item.post.platform_posts.update(status=PlatformPost.Status.PUBLISHED)

    cleared = batch_schedule.clear_batch(batch)
    assert cleared == 1
    remaining = Post.objects.filter(workspace=workspace)
    assert remaining.count() == 1
    assert remaining.first().id == published_item.post_id
    # 已清除帖子的明细随 CASCADE 删除；批次条只统计剩余 scheduled。
    active = batch_schedule.active_batches(workspace)
    assert active == []


def test_facebook_reel_snapshot_sets_platform_extra(workspace, folder, actor):
    _video(workspace, folder, "v1")
    fb = _account(workspace, "facebook", "fb")
    _queue_with_slots(workspace, fb, "fb", _all_week_slots())

    batch_schedule.enqueue_batch(
        workspace=workspace,
        user=actor,
        folder=folder,
        account_ids=[fb.id],
        count=1,
        facebook_post_types={f"facebook_post_type_{fb.id}": "reel"},
    )
    pp = PlatformPost.objects.get(social_account=fb)
    assert pp.platform_extra == {"post_type": "reel"}


@pytest.fixture
def client_membership(db):
    """完整客户端栈：组织/工作区/成员关系（OWNER 拥有 create_posts）。"""
    from django.utils import timezone as django_tz

    from apps.members.models import OrgMembership, WorkspaceMembership

    user = User.objects.create_user(
        email="owner@example.com", password="x", name="Owner",
        tos_accepted_at=django_tz.now(),
    )
    org = Organization.objects.create(name="Org")
    ws = Workspace.objects.create(organization=org, name="WS HTTP")
    OrgMembership.objects.create(
        user=user, organization=org, org_role=OrgMembership.OrgRole.OWNER
    )
    WorkspaceMembership.objects.create(
        user=user, workspace=ws, workspace_role=WorkspaceMembership.WorkspaceRole.OWNER
    )
    return user, ws


@pytest.mark.urls("zh_overrides.urls")
def test_folders_endpoint_renders(client, client_membership):
    user, ws = client_membership
    folder = MediaFolder.objects.create(
        organization=ws.organization, workspace=ws, name="Sub Folder"
    )
    client.force_login(user)

    resp = client.get(f"/workspace/{ws.id}/zh-batch/folders/")
    assert resp.status_code == 200
    body = resp.content.decode()
    assert "Media Library" in body and "Sub Folder" in body

    resp = client.get(f"/workspace/{ws.id}/zh-batch/folders/?parent={folder.id}")
    assert resp.status_code == 200
    assert "Select This Folder" in resp.content.decode()


@pytest.mark.urls("zh_overrides.urls")
def test_enqueue_active_clear_http_flow(client, client_membership):
    user, ws = client_membership
    folder = MediaFolder.objects.create(
        organization=ws.organization, workspace=ws, name="HTTP Folder"
    )
    account = _account(ws, "instagram", "ig")
    _queue_with_slots(ws, account, "ig", _all_week_slots())
    video = _video(ws, folder, "http-v")

    client.force_login(user)
    plan = client.get(
        f"/workspace/{ws.id}/zh-batch/plan/",
        {"folder": folder.id, "accounts": str(account.id)},
    ).json()
    assert plan["eligible"] == 1 and plan["default"] == 1

    resp = client.post(
        f"/workspace/{ws.id}/zh-batch/enqueue/",
        {
            "folder_id": str(folder.id),
            "count": "1",
            "selected_accounts": str(account.id),
            "caption": "Hi",
        },
    )
    assert resp.status_code == 200, resp.content.decode()
    data = resp.json()
    assert data["created"] == 1
    batch_id = data["batch_id"]

    active = client.get(f"/workspace/{ws.id}/zh-batch/active/").json()
    assert [b["batch_id"] for b in active] == [batch_id]
    assert active[0]["remaining"] == 1

    cleared = client.post(f"/workspace/{ws.id}/zh-batch/batches/{batch_id}/clear/").json()
    assert cleared["cleared"] == 1
    assert client.get(f"/workspace/{ws.id}/zh-batch/active/").json() == []
    assert not Post.objects.filter(workspace=ws).exists()
    assert not PlatformPost.objects.filter(social_account=account).exists()
    # 素材本身不受影响。
    assert MediaAsset.objects.filter(id=video.id).exists()


@pytest.mark.urls("zh_overrides.urls")
def test_enqueue_rejects_missing_accounts(client, client_membership):
    user, ws = client_membership
    folder = MediaFolder.objects.create(
        organization=ws.organization, workspace=ws, name="X"
    )
    client.force_login(user)
    resp = client.post(
        f"/workspace/{ws.id}/zh-batch/enqueue/",
        {"folder_id": str(folder.id), "count": "1", "selected_accounts": ""},
    )
    assert resp.status_code == 400
    assert "account" in resp.json()["error"]
