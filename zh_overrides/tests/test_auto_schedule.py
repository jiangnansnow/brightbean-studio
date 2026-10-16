"""文件夹自动排期（V2：24h 滚动 + 武装总开关）服务与 HTTP 测试。"""

from datetime import time

import pytest
from django.utils import timezone

from apps.accounts.models import User
from apps.calendar.models import PostingSlot, Queue
from apps.composer.models import PlatformPost, Post
from apps.media_library.models import MediaAsset, MediaFolder
from apps.organizations.models import Organization
from apps.social_accounts.models import SocialAccount
from apps.workspaces.models import Workspace
from zh_overrides import auto_schedule
from zh_overrides.models import (
    ZhAutoScheduleConsumption,
    ZhAutoScheduleRule,
    ZhScheduledBatch,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def actor(db):
    return User.objects.create_user(
        email="maker@example.com", password="x", name="Maker",
        tos_accepted_at=timezone.now(),
    )


@pytest.fixture
def workspace():
    org = Organization.objects.create(name="Sidecar Org")
    return Workspace.objects.create(organization=org, name="WS Auto")


@pytest.fixture
def folder(workspace):
    return MediaFolder.objects.create(
        organization=workspace.organization, workspace=workspace, name="产品视频"
    )


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
    queue = Queue.objects.create(
        workspace=workspace, social_account=account, name=f"Q {slug}"
    )
    for day, t in slot_times:
        PostingSlot.objects.create(social_account=account, day_of_week=day, time=t)
    return queue


def _all_week_slots():
    return [(day, time(9, 0)) for day in range(7)]


def _dense_slots():
    """每 3 小时一个时段，保证 24h 窗口内有多个空闲槽（用于多视频场景）。"""
    return [(day, time(h, 0)) for day in range(7) for h in range(0, 24, 3)]


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


def _submit(workspace, user, folder, account_ids, form_snapshot=None):
    """武装开关开启后的提交入口（补排 24h）。"""
    auto_schedule.set_armed(workspace, True)
    return auto_schedule.submit_folder_schedule(
        workspace=workspace,
        user=user,
        folder=folder,
        account_ids=account_ids,
        form_snapshot=form_snapshot or {},
    )


# ── 槽位 ──────────────────────────────────────────────────────────────


def test_open_slots_24h_only(workspace):
    import datetime

    a = _account(workspace, "instagram", "ig")
    _queue_with_slots(workspace, a, "ig", _all_week_slots())
    slots = auto_schedule.open_slot_datetimes(a)
    assert slots
    horizon = timezone.now() + datetime.timedelta(hours=24)
    assert all(dt <= horizon for dt in slots)
    assert max(slots) - min(slots) <= datetime.timedelta(hours=24)


def test_root_video_count(workspace, folder):
    _video(workspace, folder, "in-folder")
    _video(workspace, None, "root-1")
    _video(workspace, None, "root-2", media_type="image")
    assert auto_schedule.root_video_count(workspace) == 1


def test_folder_video_counts_named_folders(workspace, folder):
    f2 = MediaFolder.objects.create(
        organization=workspace.organization, workspace=workspace, name="F2"
    )
    f3 = MediaFolder.objects.create(
        organization=workspace.organization, workspace=workspace, name="空文件夹"
    )
    _video(workspace, folder, "a")
    _video(workspace, folder, "b")
    _video(workspace, folder, "img", media_type="image")  # 图片不计
    _video(workspace, f2, "c")
    counts = auto_schedule.folder_video_counts(workspace, [folder, f2, f3])
    assert counts[folder.id] == 2
    assert counts[f2.id] == 1
    assert f3.id not in counts  # 空文件夹不出现，视图层按 0 兜底


# ── 武装开关 ──────────────────────────────────────────────────────────


def test_submit_requires_armed(workspace, folder, actor):
    a = _account(workspace, "instagram", "ig")
    _queue_with_slots(workspace, a, "ig", _all_week_slots())
    _video(workspace, folder, "v")
    with pytest.raises(auto_schedule.AutoScheduleError):
        auto_schedule.submit_folder_schedule(
            workspace=workspace, user=actor, folder=folder,
            account_ids=[a.id], form_snapshot={},
        )


def test_unarm_stops_and_rearm_does_not_auto_resume(workspace, folder, actor):
    a = _account(workspace, "instagram", "ig")
    _queue_with_slots(workspace, a, "ig", _all_week_slots())
    _video(workspace, folder, "v1")
    rule, n = _submit(workspace, actor, folder, [a.id])
    assert n == 1 and Post.objects.filter(workspace=workspace).count() == 1

    auto_schedule.set_armed(workspace, False)
    rule.refresh_from_db()
    assert rule.is_active is False  # 关闭即停用规则
    assert auto_schedule.run_rule(rule) == 0

    # 重新武装：不自动恢复、不重发旧视频。
    auto_schedule.set_armed(workspace, True)
    assert not rule.is_active or auto_schedule.run_rule(rule) == 0
    assert Post.objects.filter(workspace=workspace).count() == 1


# ── 提交与补排 ────────────────────────────────────────────────────────


def test_submit_fills_24h_and_logs(workspace, folder, actor):
    a = _account(workspace, "instagram", "ig")
    b = _account(workspace, "facebook", "fb")
    _queue_with_slots(workspace, a, "ig", _all_week_slots())
    _queue_with_slots(workspace, b, "fb", _all_week_slots())
    videos = [_video(workspace, folder, f"v{i}") for i in range(10)]
    # 期望值必须在提交前计算：提交后空槽已被新建帖子占用。
    expected = min(
        10,
        len(auto_schedule.open_slot_datetimes(a)),
        len(auto_schedule.open_slot_datetimes(b)),
    )

    rule, n = _submit(
        workspace, actor, folder, [a.id, b.id],
        form_snapshot={"caption": "快照文案"},
    )
    assert rule.is_active and n == expected
    assert rule.folder_name == "产品视频"
    assert rule.caption == "快照文案"
    assert Post.objects.filter(workspace=workspace).count() == expected
    for post in Post.objects.filter(workspace=workspace):
        assert post.platform_posts.count() == 2
        assert all(pp.status == "scheduled" for pp in post.platform_posts.all())
    assert ZhAutoScheduleConsumption.objects.filter(rule=rule).count() == expected * 2
    assert ZhScheduledBatch.objects.filter(rule=rule).count() == 1
    used = set(
        ZhAutoScheduleConsumption.objects.filter(rule=rule)
        .values_list("media_asset_id", flat=True)
    )
    # 数量精确、且全部来自该文件夹（同一秒创建的 created_at 相同，FIFO 具体身份
    # 由随机 UUID 兜底排序，不做确定性断言）。
    assert len(used) == expected
    assert used <= {v.id for v in videos}


def test_submit_is_idempotent_no_resend_on_second_run(workspace, folder, actor):
    a = _account(workspace, "instagram", "ig")
    _queue_with_slots(workspace, a, "ig", _all_week_slots())
    _video(workspace, folder, "only")

    rule, n1 = _submit(workspace, actor, folder, [a.id])
    assert n1 == 1
    n2 = auto_schedule.run_rule(rule)
    assert n2 == 0
    assert Post.objects.filter(workspace=workspace).count() == 1


def test_replace_folder_keeps_ledger(workspace, folder, actor):
    a = _account(workspace, "instagram", "ig")
    _queue_with_slots(workspace, a, "ig", _dense_slots())
    _video(workspace, folder, "old")
    rule, n_old = _submit(workspace, actor, folder, [a.id])
    assert n_old == 1

    new_folder = MediaFolder.objects.create(
        organization=workspace.organization, workspace=workspace, name="新文件夹"
    )
    _video(workspace, new_folder, "new")
    rule2, n_new = _submit(workspace, actor, new_folder, [a.id])
    assert rule2.id == rule.id  # 同一行整单替换
    assert rule2.media_folder_id == new_folder.id
    assert n_new == 1
    assert rule2.consumptions.count() == 2  # 新旧各一，老视频未重发


def test_missing_folder_auto_disables(workspace, folder, actor):
    a = _account(workspace, "instagram", "ig")
    _queue_with_slots(workspace, a, "ig", _all_week_slots())
    _video(workspace, folder, "v")
    rule, _ = _submit(workspace, actor, folder, [a.id])
    folder.delete()
    rule.refresh_from_db()
    assert rule.folder_missing is True
    assert auto_schedule.run_rule(rule) == 0
    rule.refresh_from_db()
    assert rule.is_active is False


def test_run_all_active_filters_unarmed(workspace, actor):
    a = _account(workspace, "instagram", "ig")
    _queue_with_slots(workspace, a, "ig", _all_week_slots())
    _video(workspace, None, "root-v")
    rule = ZhAutoScheduleRule.objects.create(workspace=workspace, is_active=True)
    rule.accounts.add(a)

    assert auto_schedule.run_all_active_rules() == 0  # 未武装不投递
    auto_schedule.set_armed(workspace, True)
    assert auto_schedule.run_all_active_rules() == 1  # 武装后投递


def test_dead_accounts_skipped_but_rule_lives(workspace, folder, actor):
    good = _account(workspace, "instagram", "ig")
    dead = _account(
        workspace, "facebook", "fb",
        connection_status=SocialAccount.ConnectionStatus.DISCONNECTED,
    )
    _queue_with_slots(workspace, good, "ig", _all_week_slots())
    Queue.objects.create(workspace=workspace, social_account=dead, name="Q fb")
    _video(workspace, folder, "v")

    rule, n = _submit(workspace, actor, folder, [good.id, dead.id])
    assert n >= 1
    status = auto_schedule.rule_status(rule)
    assert "Name fb" in status["ignored"]
    # 恢复连接后该账号自动纳入：直接造队列验证 resolve_targets。
    dead.connection_status = SocialAccount.ConnectionStatus.CONNECTED
    dead.save()
    targets, ignored = auto_schedule.resolve_targets(workspace, [good, dead])
    assert len(targets) == 2 and ignored == []


def test_approval_workspace_blocks_submit(workspace, folder, actor):
    workspace.approval_workflow_mode = "required_internal"
    workspace.save(update_fields=["approval_workflow_mode"])
    a = _account(workspace, "instagram", "ig")
    _queue_with_slots(workspace, a, "ig", _all_week_slots())
    _video(workspace, folder, "v")
    auto_schedule.set_armed(workspace, True)
    with pytest.raises(auto_schedule.AutoScheduleError):
        auto_schedule.submit_folder_schedule(
            workspace=workspace, user=actor, folder=folder,
            account_ids=[a.id], form_snapshot={},
        )


def test_clear_batch_keeps_published_history(workspace, folder, actor):
    a = _account(workspace, "instagram", "ig")
    _queue_with_slots(workspace, a, "ig", _dense_slots())
    _video(workspace, folder, "v1")
    _video(workspace, folder, "v2")
    rule, _ = _submit(workspace, actor, folder, [a.id])
    posts = list(Post.objects.filter(workspace=workspace).order_by("created_at"))
    assert len(posts) >= 2
    # 模拟第一条已发布（历史，不应被清除）
    first_pp = posts[0].platform_posts.first()
    first_pp.status = PlatformPost.Status.PUBLISHED
    first_pp.save(update_fields=["status"])

    batch = ZhScheduledBatch.objects.filter(rule=rule).first()
    cleared = auto_schedule.clear_batch(batch)
    assert cleared == len(posts) - 1
    assert Post.objects.filter(id=posts[0].id).exists()
    assert not Post.objects.filter(id=posts[1].id).exists()


# ── 0 入队原因诊断 ─────────────────────────────────────────────────────


def test_explain_zero_no_slot(workspace, folder, actor):
    a = _account(workspace, "instagram", "ig")
    _queue_with_slots(workspace, a, "ig", [])  # 队列无任何发帖时段
    _video(workspace, folder, "v")
    rule, n = _submit(workspace, actor, folder, [a.id])
    assert n == 0
    assert "空闲发帖时段" in auto_schedule.explain_zero(rule)


def test_explain_zero_all_consumed(workspace, folder, actor):
    a = _account(workspace, "instagram", "ig")
    _queue_with_slots(workspace, a, "ig", _dense_slots())
    _video(workspace, folder, "only")
    rule, n = _submit(workspace, actor, folder, [a.id])
    assert n == 1
    # 该视频已投递，账本防重发 → 无可排期内容
    assert "没有可排期" in auto_schedule.explain_zero(rule)


# ── HTTP 层 ────────────────────────────────────────────────────────────


@pytest.fixture
def client_membership(db):
    from apps.members.models import OrgMembership, WorkspaceMembership

    user = User.objects.create_user(
        email="owner@auto.example", password="x", name="Owner",
        tos_accepted_at=timezone.now(),
    )
    org = Organization.objects.create(name="Org Auto")
    ws = Workspace.objects.create(organization=org, name="WS HTTP")
    OrgMembership.objects.create(
        user=user, organization=org, org_role=OrgMembership.OrgRole.OWNER
    )
    WorkspaceMembership.objects.create(
        user=user, workspace=ws, workspace_role=WorkspaceMembership.WorkspaceRole.OWNER
    )
    return user, ws


@pytest.mark.urls("zh_overrides.urls")
def test_folders_endpoint_includes_root_card(client, client_membership):
    user, ws = client_membership
    MediaFolder.objects.create(
        organization=ws.organization, workspace=ws, name="Sub"
    )
    client.force_login(user)
    body = client.get(f"/workspace/{ws.id}/zh-auto/folders/").content.decode()
    # htmx 片段只含文件夹网格（弹窗外壳/提交按钮由 JS 注入，不在此片段）。
    assert "未分文件夹" in body and "Sub" in body


@pytest.mark.urls("zh_overrides.urls")
def test_social_toggle_http_flow(client, client_membership):
    user, ws = client_membership
    client.force_login(user)

    state = client.get(f"/workspace/{ws.id}/zh-auto/social-toggle/").json()
    assert state["armed"] is False

    on = client.post(f"/workspace/{ws.id}/zh-auto/social-toggle/flip/").json()
    assert on["armed"] is True
    off = client.post(f"/workspace/{ws.id}/zh-auto/social-toggle/flip/").json()
    assert off["armed"] is False


@pytest.mark.urls("zh_overrides.urls")
def test_queue_http_flow(client, client_membership):
    user, ws = client_membership
    folder = MediaFolder.objects.create(
        organization=ws.organization, workspace=ws, name="HTTP Folder"
    )
    account = _account(ws, "instagram", "ig")
    _queue_with_slots(ws, account, "ig", _all_week_slots())
    _video(ws, folder, "v")
    client.force_login(user)

    # 未武装 → 400
    resp = client.post(
        f"/workspace/{ws.id}/zh-auto/queue/",
        {
            "folder_id": str(folder.id),
            "selected_accounts": str(account.id),
            "caption": "Hi",
        },
    )
    assert resp.status_code == 400

    # 社交页开启总开关后提交。
    client.post(f"/workspace/{ws.id}/zh-auto/social-toggle/flip/")
    resp = client.post(
        f"/workspace/{ws.id}/zh-auto/queue/",
        {
            "folder_id": str(folder.id),
            "selected_accounts": str(account.id),
            "caption": "Hi",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["queued_now"] == 1 and "redirect" in data

    # 账本不重发：二次提交（同一文件夹）不会重复建帖。
    assert ZhAutoScheduleConsumption.objects.filter(rule__workspace=ws).count() == 1


@pytest.mark.urls("zh_overrides.urls")
def test_queue_returns_reason_when_zero(client, client_membership):
    user, ws = client_membership
    folder = MediaFolder.objects.create(
        organization=ws.organization, workspace=ws, name="NoSlotFolder"
    )
    account = _account(ws, "instagram", "ig")
    _queue_with_slots(ws, account, "ig", [])  # 无时段 → 0 入队
    _video(ws, folder, "v")
    client.force_login(user)
    client.post(f"/workspace/{ws.id}/zh-auto/social-toggle/flip/")
    resp = client.post(
        f"/workspace/{ws.id}/zh-auto/queue/",
        {"folder_id": str(folder.id), "selected_accounts": str(account.id)},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["queued_now"] == 0
    assert "reason" in data and "空闲发帖时段" in data["reason"]


@pytest.mark.urls("zh_overrides.urls")
def test_root_folder_queue(client, client_membership):
    user, ws = client_membership
    account = _account(ws, "instagram", "ig")
    _queue_with_slots(ws, account, "ig", _all_week_slots())
    _video(ws, None, "root-v")
    client.force_login(user)
    client.post(f"/workspace/{ws.id}/zh-auto/social-toggle/flip/")
    resp = client.post(
        f"/workspace/{ws.id}/zh-auto/queue/",
        {"folder_id": "root", "selected_accounts": str(account.id)},
    )
    assert resp.status_code == 200
    assert resp.json()["queued_now"] == 1
    rule = ZhAutoScheduleRule.objects.get(workspace=ws)
    assert rule.media_folder_id is None and rule.folder_name == ""


@pytest.mark.urls("zh_overrides.urls")
def test_clear_media_http(client, client_membership):
    user, ws = client_membership
    client.force_login(user)
    resp = client.post(f"/workspace/{ws.id}/zh-auto/clear-media/")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


@pytest.mark.urls("zh_overrides.urls")
def test_active_and_clear_http(client, client_membership):
    user, ws = client_membership
    folder = MediaFolder.objects.create(
        organization=ws.organization, workspace=ws, name="F"
    )
    account = _account(ws, "instagram", "ig")
    _queue_with_slots(ws, account, "ig", _all_week_slots())
    _video(ws, folder, "v")
    client.force_login(user)
    client.post(f"/workspace/{ws.id}/zh-auto/social-toggle/flip/")
    client.post(
        f"/workspace/{ws.id}/zh-auto/queue/",
        {"folder_id": str(folder.id), "selected_accounts": str(account.id)},
    )

    batches = client.get(f"/workspace/{ws.id}/zh-auto/active/").json()
    assert len(batches) == 1 and batches[0]["remaining"] == 1

    cleared = client.post(
        f"/workspace/{ws.id}/zh-auto/batches/{batches[0]['batch_id']}/clear/"
    ).json()
    assert cleared["cleared"] == 1
