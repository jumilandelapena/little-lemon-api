from decimal import Decimal

from LittleLemonAPI.models import Cart

from .base import APITestBase

URL = "/api/cart/menu-items/"


class CartTests(APITestBase):
    def test_customer_adds_item_with_server_side_prices(self):
        self.login(self.customer)
        res = self.client.post(URL, {"menuitem_id": self.pasta.pk, "quantity": 2}, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data["unit_price"], "12.50")
        self.assertEqual(res.data["price"], "25.00")
        self.assertEqual(res.data["menuitem"]["title"], "Pasta")
        self.assertNotIn("user", res.data)

        cart = Cart.objects.get(user=self.customer, menuitem=self.pasta)
        self.assertEqual(cart.quantity, 2)
        self.assertEqual(cart.price, Decimal("25.00"))

    def test_duplicate_item_is_400(self):
        self.login(self.customer)
        payload = {"menuitem_id": self.pasta.pk, "quantity": 1}
        self.assertEqual(self.client.post(URL, payload, format="json").status_code, 201)
        res = self.client.post(URL, payload, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(Cart.objects.filter(user=self.customer).count(), 1)

    def test_invalid_quantity_or_item_is_400(self):
        self.login(self.customer)
        res = self.client.post(URL, {"menuitem_id": self.pasta.pk, "quantity": 0}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertIn("quantity", res.data)
        res = self.client.post(URL, {"menuitem_id": 9999, "quantity": 1}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertIn("menuitem_id", res.data)
        res = self.client.post(URL, {}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_get_returns_only_own_items(self):
        Cart.objects.create(user=self.customer, menuitem=self.pasta, quantity=1, unit_price="12.50")
        Cart.objects.create(user=self.customer2, menuitem=self.cake, quantity=3, unit_price="6.25")

        self.login(self.customer)
        res = self.client.get(URL)
        self.assertEqual(res.status_code, 200)
        self.assertEqual([i["menuitem"]["title"] for i in res.data], ["Pasta"])

        self.login(self.customer2)
        res = self.client.get(URL)
        self.assertEqual([i["price"] for i in res.data], ["18.75"])

    def test_delete_clears_only_my_cart(self):
        Cart.objects.create(user=self.customer, menuitem=self.pasta, quantity=1, unit_price="12.50")
        Cart.objects.create(user=self.customer, menuitem=self.cake, quantity=1, unit_price="6.25")
        Cart.objects.create(user=self.customer2, menuitem=self.cake, quantity=1, unit_price="6.25")

        self.login(self.customer)
        res = self.client.delete(URL)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(self.client.get(URL).data, [])
        self.assertEqual(Cart.objects.filter(user=self.customer2).count(), 1)

    def test_only_customers_can_use_the_cart(self):
        self.assertEqual(self.client.get(URL).status_code, 401)
        for user in (self.manager, self.crew, self.admin):
            self.login(user)
            self.assertEqual(self.client.get(URL).status_code, 403, user.username)
            res = self.client.post(
                URL, {"menuitem_id": self.pasta.pk, "quantity": 1}, format="json"
            )
            self.assertEqual(res.status_code, 403, user.username)
            self.assertEqual(self.client.delete(URL).status_code, 403, user.username)
