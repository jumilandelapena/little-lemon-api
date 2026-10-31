"""Shared fixtures: users for every role, two categories, three menu items."""

from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.cache import cache
from rest_framework.test import APITestCase
from rest_framework.throttling import SimpleRateThrottle

from LittleLemonAPI.models import Category, MenuItem

User = get_user_model()
PASSWORD = "Str0ng-Passw0rd!"

# DRF copies DEFAULT_THROTTLE_RATES onto SimpleRateThrottle at import time, so
# override_settings cannot change it. Patch the class attribute instead:
# generous rates here, deliberately low ones in test_throttling.py.
GENEROUS_RATES = {"anon": "1000/minute", "user": "1000/minute"}


@mock.patch.object(SimpleRateThrottle, "THROTTLE_RATES", GENEROUS_RATES)
class APITestBase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        manager_group, _ = Group.objects.get_or_create(name="Manager")
        crew_group, _ = Group.objects.get_or_create(name="Delivery Crew")

        cls.manager = User.objects.create_user("manager", "manager@example.com", PASSWORD)
        cls.manager.groups.add(manager_group)
        cls.crew = User.objects.create_user("crew", "crew@example.com", PASSWORD)
        cls.crew.groups.add(crew_group)
        cls.crew2 = User.objects.create_user("crew2", "crew2@example.com", PASSWORD)
        cls.crew2.groups.add(crew_group)
        cls.customer = User.objects.create_user("customer", "customer@example.com", PASSWORD)
        cls.customer2 = User.objects.create_user("customer2", "customer2@example.com", PASSWORD)
        cls.admin = User.objects.create_superuser("admin", "admin@example.com", PASSWORD)

        cls.mains = Category.objects.create(slug="mains", title="Mains")
        cls.desserts = Category.objects.create(slug="desserts", title="Desserts")
        cls.pasta = MenuItem.objects.create(
            title="Pasta", price="12.50", category=cls.mains, featured=True
        )
        cls.pizza = MenuItem.objects.create(title="Pizza", price="10.00", category=cls.mains)
        cls.cake = MenuItem.objects.create(title="Lemon Cake", price="6.25", category=cls.desserts)

    def setUp(self):
        cache.clear()  # throttle history lives in the cache

    def login(self, user):
        self.client.force_authenticate(user=user)

    def logout(self):
        self.client.force_authenticate(user=None)
