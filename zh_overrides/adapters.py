"""Signup gate adapters for the zh-hans overlay deployment.

Wired via ``ACCOUNT_ADAPTER`` / ``SOCIALACCOUNT_ADAPTER`` in
``zh_overrides.settings``. Upstream leaves public email/password signup open;
this deployment allows new accounts only through:

1. A valid org invitation (``pending_invite_token`` in session, set by the
   accept-invite view) — works for both the email/password form and Google
2. Google OAuth — when ``GOOGLE_AUTH_CLIENT_ID`` is configured

Login for existing users (including the superuser) is never affected.
"""

from django.conf import settings

from apps.accounts.adapters import AccountAdapter, SocialAccountAdapter
from apps.members.models import Invitation


def _has_valid_invite(request) -> bool:
    token = request.session.get("pending_invite_token")
    if not token:
        return False
    invitation = Invitation.objects.filter(
        token=token,
        accepted_at__isnull=True,
    ).first()
    return bool(invitation and not invitation.is_expired)


class ZhAccountAdapter(AccountAdapter):
    """Email/password signup: invite-only."""

    def is_open_for_signup(self, request, *args, **kwargs):
        return _has_valid_invite(request)


class ZhSocialAccountAdapter(SocialAccountAdapter):
    """Social signup: open for Google (when configured), or with an invite."""

    def is_open_for_signup(self, request, sociallogin):
        if _has_valid_invite(request):
            return True
        return bool(getattr(settings, "GOOGLE_AUTH_CLIENT_ID", ""))
