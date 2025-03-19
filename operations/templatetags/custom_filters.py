from django import template
import calendar

register = template.Library()

@register.filter
def month_name(month_number):
    try:
        return calendar.month_name[month_number]
    except IndexError:
        return ''
    
from django.utils.dateparse import parse_datetime
from datetime import datetime


@register.filter
def format_date(value):
    """Formats `value` as 'F, Y' only if it's a valid date."""
    if isinstance(value, datetime):  # If already a datetime object
        return value.strftime("%B, %Y")
    try:
        parsed_date = parse_datetime(value)  # Try parsing if it's a string
        if parsed_date:
            return parsed_date.strftime("%B, %Y")
    except (TypeError, ValueError):
        pass
    return value  # Return as-is if not a valid date

