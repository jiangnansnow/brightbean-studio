"""Backfill verified allauth EmailAddress for users missing one.

Console/admin-created users historically only had ``accounts_user.email``
without an ``account_emailaddress`` row. With
``SOCIALACCOUNT_EMAIL_AUTHENTICATION=True`` their first Google login was not
matched to the existing user and allauth auto-created a *second* user (and the
post_save signal then provisioned a duplicate organisation).

This migration registers a verified primary EmailAddress for every active
user that has none, so SSO resolves to the existing identity. Idempotent and
additive; normal sign-up users already have their own row and are untouched.
"""

from django.db import migrations


def backfill_verified_emails(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    EmailAddress = apps.get_model("account", "EmailAddress")
    for user in User.objects.filter(is_active=True).iterator():
        email = (user.email or "").strip().lower()
        if not email:
            continue
        if EmailAddress.objects.filter(user=user).exists():
            continue
        # If the same address exists on another user, leave it alone.
        if EmailAddress.objects.filter(email__iexact=email).exists():
            continue
        EmailAddress.objects.create(
            user=user, email=email, verified=True, primary=True
        )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("zh_overrides", "0002_workspace_meta"),
        ("account", "0002_email_max_length"),
    ]

    operations = [
        migrations.RunPython(backfill_verified_emails, noop),
    ]
