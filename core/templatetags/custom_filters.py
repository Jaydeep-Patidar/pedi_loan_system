from django import template

register = template.Library()

@register.filter
def currency(value):
    try:
        return f"₹{float(value):,.2f}"
    except (ValueError, TypeError):
        return f"₹{value}"

@register.filter
def get_item(dictionary, key):
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None

@register.simple_tag(takes_context=True)
def query_transform(context, **kwargs):
    request = context['request']
    params = request.GET.copy()
    for key, value in kwargs.items():
        if value is None:
            params.pop(key, None)
        else:
            params[key] = value
    return params.urlencode()
