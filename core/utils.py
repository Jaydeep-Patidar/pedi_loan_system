from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q

DEFAULT_PAGE_SIZES = [10, 20, 25]


def apply_search(request, queryset, fields, search_param='search'):
    search_term = request.GET.get(search_param, '').strip()
    if not search_term and search_param != 'q':
        search_term = request.GET.get('q', '').strip()
    if search_term:
        query = Q()
        for field in fields:
            query |= Q(**{f"{field}__icontains": search_term})
        queryset = queryset.filter(query)
    return queryset, search_term


def apply_status_filter(request, queryset, filter_param='status', default_value=None):
    value = request.GET.get(filter_param, '').strip()
    if value:
        queryset = queryset.filter(**{filter_param: value})
    return queryset, value or default_value


def apply_boolean_filter(request, queryset, filter_param, field_name):
    value = request.GET.get(filter_param, '').strip().lower()
    if value in ('true', '1', 'yes'):
        queryset = queryset.filter(**{field_name: True})
    elif value in ('false', '0', 'no'):
        queryset = queryset.filter(**{field_name: False})
    return queryset, value


def apply_sorting(request, queryset, sort_map, default_order=None):
    sort_key = request.GET.get('sort', '')
    direction = request.GET.get('direction', 'desc')
    if sort_key in sort_map:
        order_field = sort_map[sort_key]
        if direction == 'asc':
            order_field = order_field.lstrip('-')
        else:
            if not order_field.startswith('-'):
                order_field = '-' + order_field
        queryset = queryset.order_by(order_field)
    elif default_order:
        queryset = queryset.order_by(default_order)
    return queryset, sort_key, direction


def paginate_queryset(request, queryset, default_per_page=10, page_param='page'):
    per_page = default_per_page
    requested_per_page = request.GET.get('per_page')
    try:
        requested_per_page = int(requested_per_page)
    except (TypeError, ValueError):
        requested_per_page = None
    if requested_per_page in DEFAULT_PAGE_SIZES:
        per_page = requested_per_page

    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get(page_param, 1)
    try:
        page_obj = paginator.page(page_number)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.page(1)
    return page_obj
