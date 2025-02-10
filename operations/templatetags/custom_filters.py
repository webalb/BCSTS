from django import template
import calendar

register = template.Library()

@register.filter
def month_name(month_number):
    try:
        return calendar.month_name[month_number]
    except IndexError:
        return ''
