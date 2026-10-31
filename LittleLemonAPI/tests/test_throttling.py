from unittest import mock

from django.core.cache import cache
from rest_framework.throttling import SimpleRateThrottle

from .base import APITestBase

LOW_RATES = {"anon": "3/minute", "user": "3/minute"}


class ThrottlingTests(APITestBase):
    @mock.patch.object(SimpleRateThrottle, "THROTTLE_RATES", LOW_RATES)
    def test_anonymous_requests_are_throttled(self):
        cache.clear()
        for _ in range(3):
            self.assertEqual(self.client.get("/api/menu-items/").status_code, 200)
        res = self.client.get("/api/menu-items/")
        self.assertEqual(res.status_code, 429)
        self.assertIn("Retry-After", res.headers)

    @mock.patch.object(SimpleRateThrottle, "THROTTLE_RATES", LOW_RATES)
    def test_authenticated_requests_are_throttled(self):
        cache.clear()
        self.login(self.customer)
        for _ in range(3):
            self.assertEqual(self.client.get("/api/menu-items/").status_code, 200)
        self.assertEqual(self.client.get("/api/menu-items/").status_code, 429)

    def test_default_rates_are_configured(self):
        from django.conf import settings

        rates = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]
        self.assertIn("anon", rates)
        self.assertIn("user", rates)
        classes = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"]
        self.assertIn("rest_framework.throttling.AnonRateThrottle", classes)
        self.assertIn("rest_framework.throttling.UserRateThrottle", classes)
