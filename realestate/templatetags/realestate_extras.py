from decimal import Decimal

from django import template

register = template.Library()


@register.filter
def has_area(value):
    if value in (None, ''):
        return False
    try:
        dec = Decimal(str(value))
        return dec > 0
    except Exception:
        return False
