"""API views for the Little Lemon restaurant workflow."""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import transaction
from django.db.models import ProtectedError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .filters import MenuItemFilter, OrderFilter
from .models import Cart, Category, MenuItem, Order, OrderItem
from .permissions import (
    DELIVERY_CREW_GROUP,
    MANAGER_GROUP,
    CanEditOrder,
    IsCustomer,
    IsManager,
    IsManagerOrReadOnly,
    is_customer,
    is_delivery_crew,
    is_manager,
)
from .serializers import (
    CartSerializer,
    CategorySerializer,
    DeliveryCrewOrderSerializer,
    GroupMemberSerializer,
    MenuItemSerializer,
    OrderSerializer,
    UserSerializer,
)

User = get_user_model()


class DestroyWith200Mixin:
    """DELETE answers 200 + JSON (the brief lists 200 for success, not 204)."""

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            self.perform_destroy(instance)
        except ProtectedError:
            return Response(
                {"detail": "This record is referenced by other records and cannot be deleted."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"message": "Deleted."}, status=status.HTTP_200_OK)


# --------------------------------------------------------------------------- #
# Categories
# --------------------------------------------------------------------------- #
class CategoriesView(generics.ListCreateAPIView):
    """GET: anyone. POST: managers."""

    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsManagerOrReadOnly]
    filterset_fields = ["slug"]
    search_fields = ["title", "slug"]
    ordering_fields = ["id", "title"]
    ordering = ["id"]


class CategoryDetailView(DestroyWith200Mixin, generics.RetrieveUpdateDestroyAPIView):
    """GET: anyone. PUT/PATCH/DELETE: managers."""

    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsManagerOrReadOnly]


# --------------------------------------------------------------------------- #
# Menu items
# --------------------------------------------------------------------------- #
class MenuItemsView(generics.ListCreateAPIView):
    """GET: anyone, with filtering, search, ordering and pagination. POST: managers."""

    queryset = MenuItem.objects.select_related("category").all()
    serializer_class = MenuItemSerializer
    permission_classes = [IsManagerOrReadOnly]
    filterset_class = MenuItemFilter
    search_fields = ["title", "category__title"]
    ordering_fields = ["price", "title", "id"]
    ordering = ["id"]


class MenuItemDetailView(DestroyWith200Mixin, generics.RetrieveUpdateDestroyAPIView):
    """GET: anyone. PUT/PATCH/DELETE: managers."""

    queryset = MenuItem.objects.select_related("category").all()
    serializer_class = MenuItemSerializer
    permission_classes = [IsManagerOrReadOnly]


# --------------------------------------------------------------------------- #
# User group management (managers only)
# --------------------------------------------------------------------------- #
def lookup_user(data):
    """Resolve the ``GroupMemberSerializer`` payload to a user or raise 404."""
    if data.get("user_id") is not None:
        return get_object_or_404(User, pk=data["user_id"])
    return get_object_or_404(User, username=data["username"])


class GroupUsersView(generics.ListCreateAPIView):
    """GET: list users in ``group_name``. POST: add a user to it (201)."""

    group_name = None
    permission_classes = [IsAuthenticated, IsManager]
    pagination_class = None
    filterset_fields = []
    search_fields = ["username", "email"]
    ordering_fields = ["id", "username"]
    ordering = ["id"]

    def get_queryset(self):
        return User.objects.filter(groups__name=self.group_name).order_by("id")

    def get_serializer_class(self):
        if self.request.method == "POST":
            return GroupMemberSerializer
        return UserSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = lookup_user(serializer.validated_data)
        group, _ = Group.objects.get_or_create(name=self.group_name)
        group.user_set.add(user)
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class GroupUserDetailView(generics.GenericAPIView):
    """DELETE: remove ``userId`` from ``group_name`` (200, or 404 if not a member)."""

    group_name = None
    permission_classes = [IsAuthenticated, IsManager]
    serializer_class = UserSerializer
    queryset = User.objects.all()
    lookup_url_kwarg = "userId"
    filter_backends = []

    def delete(self, request, *args, **kwargs):
        user = self.get_object()
        group, _ = Group.objects.get_or_create(name=self.group_name)
        if not user.groups.filter(pk=group.pk).exists():
            return Response(
                {"detail": f"User '{user.username}' is not in the {self.group_name} group."},
                status=status.HTTP_404_NOT_FOUND,
            )
        group.user_set.remove(user)
        return Response(
            {"message": f"User '{user.username}' removed from the {self.group_name} group."},
            status=status.HTTP_200_OK,
        )


class ManagerUsersView(GroupUsersView):
    group_name = MANAGER_GROUP


class ManagerUserDetailView(GroupUserDetailView):
    group_name = MANAGER_GROUP


class DeliveryCrewUsersView(GroupUsersView):
    group_name = DELIVERY_CREW_GROUP


class DeliveryCrewUserDetailView(GroupUserDetailView):
    group_name = DELIVERY_CREW_GROUP


# --------------------------------------------------------------------------- #
# Cart (customers only)
# --------------------------------------------------------------------------- #
class CartView(generics.ListCreateAPIView):
    """GET: my cart. POST: add ``menuitem_id`` + ``quantity``. DELETE: empty my cart."""

    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated, IsCustomer]
    pagination_class = None
    filter_backends = []

    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user).select_related(
            "menuitem", "menuitem__category"
        )

    def delete(self, request, *args, **kwargs):
        deleted, _ = self.get_queryset().delete()
        return Response(
            {"message": f"Cart cleared ({deleted} item(s) removed)."},
            status=status.HTTP_200_OK,
        )


# --------------------------------------------------------------------------- #
# Orders
# --------------------------------------------------------------------------- #
def orders_visible_to(user):
    """Managers see everything, crew their assignments, customers their own."""
    queryset = Order.objects.select_related("user", "delivery_crew").prefetch_related(
        "items__menuitem"
    )
    if is_manager(user):
        return queryset
    if is_delivery_crew(user):
        return queryset.filter(delivery_crew=user)
    return queryset.filter(user=user)


class OrdersView(generics.ListCreateAPIView):
    """GET: role-scoped order list. POST (customers): turn my cart into an order."""

    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    filterset_class = OrderFilter
    search_fields = ["user__username", "delivery_crew__username"]
    ordering_fields = ["id", "date", "total", "status"]
    ordering = ["id"]

    def get_queryset(self):
        return orders_visible_to(self.request.user)

    def create(self, request, *args, **kwargs):
        user = request.user
        if not is_customer(user):
            raise PermissionDenied("Only customers can place orders.")

        with transaction.atomic():
            cart_items = list(Cart.objects.filter(user=user).select_related("menuitem"))
            if not cart_items:
                return Response(
                    {"detail": "Your cart is empty."}, status=status.HTTP_400_BAD_REQUEST
                )
            total = sum((item.price for item in cart_items), Decimal("0.00"))
            order = Order.objects.create(user=user, total=total, date=timezone.localdate())
            OrderItem.objects.bulk_create(
                [
                    OrderItem(
                        order=order,
                        menuitem=item.menuitem,
                        quantity=item.quantity,
                        unit_price=item.unit_price,
                        price=item.price,
                    )
                    for item in cart_items
                ]
            )
            Cart.objects.filter(user=user).delete()

        order = orders_visible_to(user).get(pk=order.pk)
        serializer = self.get_serializer(order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class OrderDetailView(DestroyWith200Mixin, generics.RetrieveUpdateDestroyAPIView):
    """GET: owner / assigned crew / managers. PUT+PATCH+DELETE: managers.
    PATCH (status only): delivery crew."""

    permission_classes = [IsAuthenticated, CanEditOrder]

    def get_queryset(self):
        return orders_visible_to(self.request.user)

    def _crew_only(self):
        user = self.request.user
        return is_delivery_crew(user) and not is_manager(user)

    def get_serializer_class(self):
        if self._crew_only():
            return DeliveryCrewOrderSerializer
        return OrderSerializer

    def update(self, request, *args, **kwargs):
        if self._crew_only():
            keys = set(request.data.keys()) if hasattr(request.data, "keys") else set()
            forbidden = sorted(keys - {"status"})
            if forbidden:
                return Response(
                    {
                        "detail": "Delivery crew can only update the 'status' field.",
                        "forbidden_fields": forbidden,
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )
            if "status" not in keys:
                return Response(
                    {"status": ["This field is required."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        return super().update(request, *args, **kwargs)
