"""
storage_filters.py
-------------------
Custom template filter(s) for storage_app templates.

`split` lets templates do:  {{ value|split:"," }}
turning "jpg,png,gif" into ["jpg", "png", "gif"] so we can check
membership with the `in` template operator (used to pick file icons).
"""
from django import template

register = template.Library()


@register.filter(name='split')
def split(value, delimiter=','):
    """Splits a string by the given delimiter. Usage: {{ "a,b"|split:"," }}"""
    return value.split(delimiter)
