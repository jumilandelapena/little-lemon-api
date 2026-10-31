"""Database models for the Little Lemon restaurant API."""

from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Category(models.Model):
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=255, db_index=True)

    class Meta:
        ordering = ["id"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.title


class MenuItem(models.Model):
    title = models.CharField(max_length=255, db_index=True)
    price = models.DecimalField(
        max_digits=6, decimal_places=2, db_index=True, validators=[MinValueValidator(0)]
    )
    featured = models.BooleanField(default=False, db_index=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="menu_items")

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.title


class Cart(models.Model):
    """One line in a customer's shopping cart.

    ``unit_price`` is copied from the menu item when it is added and
    ``price`` is always ``quantity * unit_price``.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart_items"
    )
    menuitem = models.ForeignKey(MenuItem, on_delete=models.CASCADE)
    quantity = models.SmallIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=6, decimal_places=2)
    price = models.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        ordering = ["id"]
        unique_together = ("user", "menuitem")

    def save(self, *args, **kwargs):
        self.price = Decimal(self.unit_price) * int(self.quantity)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user} - {self.menuitem} x{self.quantity}"


class Order(models.Model):
    """A placed order. ``status`` 0 = out for delivery, 1 = delivered."""

    OUT_FOR_DELIVERY = False
    DELIVERED = True

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders"
    )
    delivery_crew = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="delivery_crew",
        null=True,
        blank=True,
    )
    status = models.BooleanField(default=0, db_index=True)
    total = models.DecimalField(max_digits=8, decimal_places=2)
    date = models.DateField(db_index=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"Order #{self.pk} ({self.user})"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    menuitem = models.ForeignKey(MenuItem, on_delete=models.PROTECT)
    quantity = models.SmallIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=6, decimal_places=2)
    price = models.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        ordering = ["id"]
        unique_together = ("order", "menuitem")

    def __str__(self):
        return f"{self.menuitem} x{self.quantity}"
