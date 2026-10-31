import django_filters
from django.db.models import Q

from .models import MenuItem, Order


class MenuItemFilter(django_filters.FilterSet):
    """``?category=<id|slug|title>&featured=true&price_min=5&price_max=15``."""

    category = django_filters.CharFilter(
        method="filter_category", label="Category id, slug or title"
    )
    price_min = django_filters.NumberFilter(field_name="price", lookup_expr="gte")
    price_max = django_filters.NumberFilter(field_name="price", lookup_expr="lte")

    class Meta:
        model = MenuItem
        fields = ["category", "featured", "price_min", "price_max"]

    def filter_category(self, queryset, name, value):
        value = value.strip()
        if value.isdigit():
            return queryset.filter(category_id=int(value))
        return queryset.filter(Q(category__slug__iexact=value) | Q(category__title__iexact=value))


class OrderFilter(django_filters.FilterSet):
    """``?status=1&date=2026-10-31&date_from=...&date_to=...&delivery_crew=<id>``."""

    date_from = django_filters.DateFilter(field_name="date", lookup_expr="gte")
    date_to = django_filters.DateFilter(field_name="date", lookup_expr="lte")

    class Meta:
        model = Order
        fields = ["status", "date", "delivery_crew", "user", "date_from", "date_to"]
