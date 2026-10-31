from LittleLemonAPI.models import MenuItem, Order, OrderItem

from .base import APITestBase

URL = "/api/menu-items/"


class MenuItemReadTests(APITestBase):
    def test_anonymous_can_list(self):
        res = self.client.get(URL)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["count"], 3)
        self.assertEqual(res.data["results"][0]["category"]["slug"], "mains")

    def test_every_role_can_read(self):
        for user in (self.customer, self.crew, self.manager):
            self.login(user)
            self.assertEqual(self.client.get(URL).status_code, 200)
            self.assertEqual(self.client.get(f"{URL}{self.pasta.pk}/").status_code, 200)

    def test_unknown_item_is_404(self):
        self.assertEqual(self.client.get(f"{URL}9999/").status_code, 404)

    def test_filter_by_category_id_slug_or_title(self):
        for value in (self.desserts.pk, "desserts", "Desserts"):
            res = self.client.get(URL, {"category": value})
            self.assertEqual(res.data["count"], 1, value)
            self.assertEqual(res.data["results"][0]["title"], "Lemon Cake")

    def test_filter_featured_and_price_range(self):
        self.assertEqual(self.client.get(URL, {"featured": "true"}).data["count"], 1)
        res = self.client.get(URL, {"price_min": 7, "price_max": 11})
        self.assertEqual([i["title"] for i in res.data["results"]], ["Pizza"])

    def test_search(self):
        res = self.client.get(URL, {"search": "lemon"})
        self.assertEqual([i["title"] for i in res.data["results"]], ["Lemon Cake"])

    def test_ordering_by_price(self):
        asc = [i["price"] for i in self.client.get(URL, {"ordering": "price"}).data["results"]]
        self.assertEqual(asc, ["6.25", "10.00", "12.50"])
        desc = [i["price"] for i in self.client.get(URL, {"ordering": "-price"}).data["results"]]
        self.assertEqual(desc, ["12.50", "10.00", "6.25"])

    def test_pagination(self):
        res = self.client.get(URL, {"perpage": 2, "page": 1})
        self.assertEqual(len(res.data["results"]), 2)
        self.assertIsNotNone(res.data["next"])
        res = self.client.get(URL, {"perpage": 2, "page": 2})
        self.assertEqual(len(res.data["results"]), 1)
        self.assertIsNone(res.data["next"])
        self.assertEqual(self.client.get(URL, {"page": 99}).status_code, 404)


class MenuItemWriteTests(APITestBase):
    def new_item(self):
        return {
            "title": "Bruschetta",
            "price": "7.50",
            "featured": True,
            "category_id": self.mains.pk,
        }

    def test_anonymous_post_is_401(self):
        self.assertEqual(self.client.post(URL, self.new_item(), format="json").status_code, 401)

    def test_customer_and_crew_get_403(self):
        detail = f"{URL}{self.pasta.pk}/"
        for user in (self.customer, self.crew):
            self.login(user)
            self.assertEqual(self.client.post(URL, self.new_item(), format="json").status_code, 403)
            self.assertEqual(
                self.client.put(detail, self.new_item(), format="json").status_code, 403
            )
            self.assertEqual(
                self.client.patch(detail, {"price": "1.00"}, format="json").status_code, 403
            )
            self.assertEqual(self.client.delete(detail).status_code, 403)
        self.assertTrue(MenuItem.objects.filter(pk=self.pasta.pk, price="12.50").exists())

    def test_manager_can_create(self):
        self.login(self.manager)
        res = self.client.post(URL, self.new_item(), format="json")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data["category"]["title"], "Mains")
        self.assertEqual(res.data["price"], "7.50")
        self.assertTrue(MenuItem.objects.filter(title="Bruschetta").exists())

    def test_superuser_counts_as_manager(self):
        self.login(self.admin)
        self.assertEqual(self.client.post(URL, self.new_item(), format="json").status_code, 201)

    def test_manager_can_update_and_delete(self):
        self.login(self.manager)
        detail = f"{URL}{self.pizza.pk}/"
        res = self.client.put(
            detail,
            {"title": "Pizza Margherita", "price": "11.00", "category_id": self.mains.pk},
            format="json",
        )
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["title"], "Pizza Margherita")

        res = self.client.patch(detail, {"featured": True}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.data["featured"])

        self.assertEqual(self.client.delete(detail).status_code, 200)
        self.assertEqual(self.client.get(detail).status_code, 404)

    def test_invalid_payload_is_400(self):
        self.login(self.manager)
        res = self.client.post(URL, {"title": "", "price": "-1", "category_id": 999}, format="json")
        self.assertEqual(res.status_code, 400)
        for field in ("title", "price", "category_id"):
            self.assertIn(field, res.data)

    def test_item_in_an_order_cannot_be_deleted(self):
        order = Order.objects.create(user=self.customer, total="12.50", date="2026-10-31")
        OrderItem.objects.create(
            order=order, menuitem=self.pasta, quantity=1, unit_price="12.50", price="12.50"
        )
        self.login(self.manager)
        self.assertEqual(self.client.delete(f"{URL}{self.pasta.pk}/").status_code, 400)
        self.assertTrue(MenuItem.objects.filter(pk=self.pasta.pk).exists())
