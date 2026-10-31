"""Serializers (validation + representation) for the Little Lemon API."""

from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Cart, Category, MenuItem, Order, OrderItem
from .permissions import DELIVERY_CREW_GROUP

User = get_user_model()


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "slug", "title"]


class MenuItemSerializer(serializers.ModelSerializer):
    """Read: nested ``category``. Write: ``category_id``."""

    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), source="category", write_only=True
    )
    price = serializers.DecimalField(max_digits=6, decimal_places=2, min_value=Decimal("0.00"))

    class Meta:
        model = MenuItem
        fields = ["id", "title", "price", "featured", "category", "category_id"]


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email"]
        read_only_fields = fields


class GroupMemberSerializer(serializers.Serializer):
    """Payload for adding a user to a group: ``username`` or ``user_id``."""

    username = serializers.CharField(required=False, allow_blank=False)
    user_id = serializers.IntegerField(required=False)

    def validate(self, attrs):
        if not attrs.get("username") and attrs.get("user_id") is None:
            raise serializers.ValidationError("Provide 'username' or 'user_id'.")
        return attrs


class CartSerializer(serializers.ModelSerializer):
    """Customers send only ``menuitem_id`` and ``quantity``.

    The user comes from the request, ``unit_price`` from the menu item and
    ``price`` is calculated server-side.
    """

    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    menuitem = MenuItemSerializer(read_only=True)
    menuitem_id = serializers.PrimaryKeyRelatedField(
        queryset=MenuItem.objects.all(), source="menuitem", write_only=True
    )
    quantity = serializers.IntegerField(min_value=1)
    unit_price = serializers.DecimalField(max_digits=6, decimal_places=2, read_only=True)
    price = serializers.DecimalField(max_digits=8, decimal_places=2, read_only=True)

    class Meta:
        model = Cart
        fields = ["id", "user", "menuitem", "menuitem_id", "quantity", "unit_price", "price"]
        validators = [
            serializers.UniqueTogetherValidator(
                queryset=Cart.objects.all(),
                fields=["user", "menuitem_id"],
                message="This menu item is already in your cart.",
            )
        ]

    def create(self, validated_data):
        menuitem = validated_data["menuitem"]
        validated_data["unit_price"] = menuitem.price
        validated_data["price"] = menuitem.price * validated_data["quantity"]
        return super().create(validated_data)


class OrderItemSerializer(serializers.ModelSerializer):
    menuitem = serializers.PrimaryKeyRelatedField(read_only=True)
    title = serializers.CharField(source="menuitem.title", read_only=True)

    class Meta:
        model = OrderItem
        fields = ["menuitem", "title", "quantity", "unit_price", "price"]
        read_only_fields = fields


class OrderSerializer(serializers.ModelSerializer):
    """Full order view. Managers may write ``delivery_crew`` and ``status``."""

    user = serializers.PrimaryKeyRelatedField(read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    delivery_crew = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), allow_null=True, required=False
    )
    delivery_crew_username = serializers.CharField(
        source="delivery_crew.username", read_only=True, allow_null=True
    )
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "user",
            "username",
            "delivery_crew",
            "delivery_crew_username",
            "status",
            "total",
            "date",
            "items",
        ]
        read_only_fields = ["id", "user", "total", "date"]

    def validate_delivery_crew(self, user):
        if user is not None and not user.groups.filter(name=DELIVERY_CREW_GROUP).exists():
            raise serializers.ValidationError(
                f"User '{user.username}' is not in the {DELIVERY_CREW_GROUP} group."
            )
        return user


class DeliveryCrewOrderSerializer(serializers.ModelSerializer):
    """Delivery crew may only change ``status`` (0 = out for delivery, 1 = delivered)."""

    class Meta:
        model = Order
        fields = ["id", "status"]
