from decimal import Decimal

from django.utils import timezone

from LittleLemonAPI.models import Cart, Order, OrderItem

from .base import APITestBase

URL = "/api/orders/"


class OrderTestBase(APITestBase):
    def fill_cart(self, user):
        Cart.objects.create(user=user, menuitem=self.pasta, quantity=2, unit_price=self.pasta.price)
        Cart.objects.create(user=user, menuitem=self.cake, quantity=1, unit_price=self.cake.price)

    def place_order(self, user):
        """Fill ``user``'s cart and POST /api/orders/ as them. Returns the response data."""
        self.fill_cart(user)
        self.login(user)
        res = self.client.post(URL)
        self.assertEqual(res.status_code, 201, res.data)
        return res.data


class CustomerOrderTests(OrderTestBase):
    def test_post_converts_cart_into_order(self):
        data = self.place_order(self.customer)
        self.assertEqual(data["total"], "31.25")
        self.assertEqual(len(data["items"]), 2)
        self.assertFalse(data["status"])
        self.assertIsNone(data["delivery_crew"])
        self.assertEqual(data["username"], "customer")
        self.assertEqual(data["date"], str(timezone.localdate()))

        self.assertEqual(Cart.objects.filter(user=self.customer).count(), 0)
        order = Order.objects.get(pk=data["id"])
        self.assertEqual(order.user, self.customer)
        self.assertEqual(order.total, Decimal("31.25"))
        item = order.items.get(menuitem=self.pasta)
        self.assertEqual(
            (item.quantity, item.unit_price, item.price), (2, Decimal("12.50"), Decimal("25.00"))
        )

    def test_empty_cart_is_400(self):
        self.login(self.customer)
        res = self.client.post(URL)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(Order.objects.count(), 0)

    def test_customer_sees_only_own_orders(self):
        mine = self.place_order(self.customer)
        theirs = self.place_order(self.customer2)

        self.login(self.customer)
        res = self.client.get(URL)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["count"], 1)
        self.assertEqual(res.data["results"][0]["id"], mine["id"])
        self.assertEqual(self.client.get(f"{URL}{mine['id']}/").status_code, 200)
        self.assertEqual(self.client.get(f"{URL}{theirs['id']}/").status_code, 404)

    def test_customer_cannot_modify_or_delete(self):
        order = self.place_order(self.customer)
        detail = f"{URL}{order['id']}/"
        self.assertEqual(self.client.patch(detail, {"status": 1}, format="json").status_code, 403)
        self.assertEqual(self.client.put(detail, {"status": 1}, format="json").status_code, 403)
        self.assertEqual(self.client.delete(detail).status_code, 403)
        self.assertTrue(Order.objects.filter(pk=order["id"], status=False).exists())


class ManagerOrderTests(OrderTestBase):
    def test_manager_and_crew_cannot_place_orders(self):
        for user in (self.manager, self.crew):
            self.login(user)
            self.assertEqual(self.client.post(URL).status_code, 403, user.username)

    def test_manager_sees_all_orders(self):
        self.place_order(self.customer)
        self.place_order(self.customer2)
        self.login(self.manager)
        res = self.client.get(URL)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["count"], 2)
        self.assertEqual({o["username"] for o in res.data["results"]}, {"customer", "customer2"})

    def test_manager_assigns_crew_and_updates_status(self):
        order = self.place_order(self.customer)
        detail = f"{URL}{order['id']}/"
        self.login(self.manager)

        res = self.client.patch(detail, {"delivery_crew": self.crew.pk}, format="json")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["delivery_crew"], self.crew.pk)
        self.assertEqual(res.data["delivery_crew_username"], "crew")

        res = self.client.put(detail, {"delivery_crew": self.crew2.pk, "status": 1}, format="json")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["delivery_crew"], self.crew2.pk)
        self.assertTrue(res.data["status"])
        self.assertEqual(res.data["total"], "31.25")  # read-only fields untouched

    def test_assigning_a_non_crew_user_is_400(self):
        order = self.place_order(self.customer)
        self.login(self.manager)
        res = self.client.patch(
            f"{URL}{order['id']}/", {"delivery_crew": self.customer2.pk}, format="json"
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("delivery_crew", res.data)

    def test_manager_deletes_order(self):
        order = self.place_order(self.customer)
        self.login(self.manager)
        self.assertEqual(self.client.delete(f"{URL}{order['id']}/").status_code, 200)
        self.assertEqual(self.client.get(f"{URL}{order['id']}/").status_code, 404)
        self.assertEqual(OrderItem.objects.filter(order_id=order["id"]).count(), 0)

    def test_manager_can_filter_by_status(self):
        first = self.place_order(self.customer)
        self.place_order(self.customer2)
        Order.objects.filter(pk=first["id"]).update(status=True)
        self.login(self.manager)
        self.assertEqual(self.client.get(URL, {"status": "true"}).data["count"], 1)
        self.assertEqual(self.client.get(URL, {"status": "false"}).data["count"], 1)


class DeliveryCrewOrderTests(OrderTestBase):
    def setUp(self):
        super().setUp()
        assigned = self.place_order(self.customer)
        Order.objects.filter(pk=assigned["id"]).update(delivery_crew=self.crew)
        unassigned = self.place_order(self.customer2)
        self.assigned_url = f"{URL}{assigned['id']}/"
        self.unassigned_url = f"{URL}{unassigned['id']}/"
        self.login(self.crew)

    def test_crew_sees_only_assigned_orders(self):
        res = self.client.get(URL)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["count"], 1)
        self.assertEqual(res.data["results"][0]["delivery_crew"], self.crew.pk)
        self.assertEqual(self.client.get(self.assigned_url).status_code, 200)
        self.assertEqual(self.client.get(self.unassigned_url).status_code, 404)

    def test_crew_updates_status(self):
        res = self.client.patch(self.assigned_url, {"status": 1}, format="json")
        self.assertEqual(res.status_code, 200, res.data)
        self.assertTrue(res.data["status"])
        self.assertTrue(Order.objects.get(delivery_crew=self.crew).status)

        res = self.client.patch(self.assigned_url, {"status": 0}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.data["status"])

    def test_crew_cannot_update_other_fields(self):
        res = self.client.patch(self.assigned_url, {"delivery_crew": self.crew2.pk}, format="json")
        self.assertEqual(res.status_code, 403)
        res = self.client.patch(self.assigned_url, {"status": 1, "total": "1.00"}, format="json")
        self.assertEqual(res.status_code, 403)
        order = Order.objects.get(delivery_crew=self.crew)
        self.assertFalse(order.status)
        self.assertEqual(order.total, Decimal("31.25"))

    def test_crew_cannot_put_or_delete(self):
        self.assertEqual(
            self.client.put(self.assigned_url, {"status": 1}, format="json").status_code, 403
        )
        self.assertEqual(self.client.delete(self.assigned_url).status_code, 403)

    def test_crew_patch_needs_a_valid_status(self):
        self.assertEqual(self.client.patch(self.assigned_url, {}, format="json").status_code, 400)
        res = self.client.patch(self.assigned_url, {"status": "maybe"}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_crew_cannot_patch_unassigned_order(self):
        self.assertEqual(
            self.client.patch(self.unassigned_url, {"status": 1}, format="json").status_code, 404
        )
