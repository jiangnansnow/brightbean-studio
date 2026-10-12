"""Template helpers for the superuser tenant console (zh_overrides-only)."""

from django import template

register = template.Library()


@register.filter
def get_item(mapping, key):
    """Dict lookup by variable key: {{ impact_text|get_item:org_id }}."""
    if isinstance(mapping, dict):
        return mapping.get(key, "")
    return ""
