"""Role-based permissions built on Django's Group model."""

from rest_framework.permissions import SAFE_METHODS, BasePermission

MANAGER_GROUP = "Manager"
DELIVERY_CREW_GROUP = "Delivery Crew"


def is_manager(user):
    """Members of the Manager group; superusers count as managers."""
    return bool(
        user
        and user.is_authenticated
        and (user.is_superuser or user.groups.filter(name=MANAGER_GROUP).exists())
    )


def is_delivery_crew(user):
    return bool(
        user and user.is_authenticated and user.groups.filter(name=DELIVERY_CREW_GROUP).exists()
    )


def is_customer(user):
    """Any authenticated user who is neither manager, delivery crew nor superuser."""
    return bool(
        user and user.is_authenticated and not is_manager(user) and not is_delivery_crew(user)
    )


class IsManager(BasePermission):
    message = "Only managers can perform this action."

    def has_permission(self, request, view):
        return is_manager(request.user)


class IsDeliveryCrew(BasePermission):
    message = "Only delivery crew can perform this action."

    def has_permission(self, request, view):
        return is_delivery_crew(request.user)


class IsCustomer(BasePermission):
    message = "Only customers can perform this action."

    def has_permission(self, request, view):
        return is_customer(request.user)


class IsManagerOrReadOnly(BasePermission):
    """Anyone may read; only managers may create, update or delete."""

    message = "Only managers can modify this resource."

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return is_manager(request.user)


class CanEditOrder(BasePermission):
    """Order detail rules.

    * GET: every authenticated role (the queryset decides what is visible).
    * PUT / PATCH / DELETE: managers.
    * PATCH only: delivery crew (the view further limits them to ``status``).
    * Customers: read only.
    """

    message = "You do not have permission to modify this order."

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        if is_manager(request.user):
            return True
        return request.method == "PATCH" and is_delivery_crew(request.user)
