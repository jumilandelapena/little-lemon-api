"""Create demo users, groups, categories and menu items for local testing."""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from LittleLemonAPI.models import Category, MenuItem

DEMO_PASSWORD = "LittleLemon123!"
USERS = [("manager", "Manager"), ("crew", "Delivery Crew"), ("customer", None)]
MENU = {
    "appetizers": ("Appetizers", [("Bruschetta", "7.50", False), ("Greek Salad", "9.00", True)]),
    "mains": (
        "Mains",
        [
            ("Lemon Chicken", "16.50", True),
            ("Grilled Fish", "18.00", False),
            ("Pasta Primavera", "14.25", False),
        ],
    ),
    "desserts": ("Desserts", [("Lemon Dessert", "6.25", True), ("Baklava", "5.50", False)]),
    "drinks": ("Drinks", [("Lemonade", "3.50", False), ("Espresso", "2.75", False)]),
}


class Command(BaseCommand):
    help = "Seed demo users (manager / crew / customer), categories and menu items."

    def handle(self, *args, **options):
        User = get_user_model()
        for username, group_name in USERS:
            user, created = User.objects.get_or_create(
                username=username, defaults={"email": f"{username}@littlelemon.test"}
            )
            if created:
                user.set_password(DEMO_PASSWORD)
                user.save()
            if group_name:
                group, _ = Group.objects.get_or_create(name=group_name)
                user.groups.add(group)

        for slug, (title, items) in MENU.items():
            category, _ = Category.objects.get_or_create(slug=slug, defaults={"title": title})
            for name, price, featured in items:
                MenuItem.objects.get_or_create(
                    title=name,
                    category=category,
                    defaults={"price": Decimal(price), "featured": featured},
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded. Demo users: manager, crew, customer (password '{DEMO_PASSWORD}')."
            )
        )
