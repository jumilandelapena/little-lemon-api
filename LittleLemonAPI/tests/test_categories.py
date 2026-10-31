from LittleLemonAPI.models import Category

from .base import APITestBase

URL = "/api/categories/"


class CategoryTests(APITestBase):
    def test_anyone_can_list(self):
        res = self.client.get(URL)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["count"], 2)
        self.assertEqual(res.data["results"][0]["slug"], "mains")

    def test_anonymous_post_is_401(self):
        res = self.client.post(URL, {"slug": "drinks", "title": "Drinks"}, format="json")
        self.assertEqual(res.status_code, 401)

    def test_customer_and_crew_post_is_403(self):
        for user in (self.customer, self.crew):
            self.login(user)
            res = self.client.post(URL, {"slug": "drinks", "title": "Drinks"}, format="json")
            self.assertEqual(res.status_code, 403, user.username)

    def test_manager_post_is_201(self):
        self.login(self.manager)
        res = self.client.post(URL, {"slug": "drinks", "title": "Drinks"}, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertTrue(Category.objects.filter(slug="drinks").exists())

    def test_duplicate_slug_is_400(self):
        self.login(self.manager)
        res = self.client.post(URL, {"slug": "mains", "title": "Mains again"}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertIn("slug", res.data)

    def test_manager_can_update_and_delete(self):
        self.login(self.manager)
        drinks = Category.objects.create(slug="drinks", title="Drinks")
        res = self.client.patch(f"{URL}{drinks.pk}/", {"title": "Beverages"}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["title"], "Beverages")
        self.assertEqual(self.client.delete(f"{URL}{drinks.pk}/").status_code, 200)
        self.assertEqual(self.client.get(f"{URL}{drinks.pk}/").status_code, 404)

    def test_category_with_items_cannot_be_deleted(self):
        self.login(self.manager)
        res = self.client.delete(f"{URL}{self.mains.pk}/")
        self.assertEqual(res.status_code, 400)
        self.assertTrue(Category.objects.filter(pk=self.mains.pk).exists())
