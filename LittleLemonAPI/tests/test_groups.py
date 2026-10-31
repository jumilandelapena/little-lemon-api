from .base import APITestBase

MANAGER_URL = "/api/groups/manager/users/"
CREW_URL = "/api/groups/delivery-crew/users/"


class GroupManagementTests(APITestBase):
    def test_only_managers_can_access(self):
        for url in (MANAGER_URL, CREW_URL):
            self.logout()
            self.assertEqual(self.client.get(url).status_code, 401)
            for user in (self.customer, self.crew):
                self.login(user)
                self.assertEqual(self.client.get(url).status_code, 403, user.username)
                res = self.client.post(url, {"username": "customer2"}, format="json")
                self.assertEqual(res.status_code, 403, user.username)
                res = self.client.delete(f"{url}{self.customer2.pk}/")
                self.assertEqual(res.status_code, 403, user.username)

    def test_manager_lists_managers(self):
        self.login(self.manager)
        res = self.client.get(MANAGER_URL)
        self.assertEqual(res.status_code, 200)
        self.assertEqual([u["username"] for u in res.data], ["manager"])

    def test_manager_lists_delivery_crew(self):
        self.login(self.manager)
        res = self.client.get(CREW_URL)
        self.assertEqual(res.status_code, 200)
        self.assertEqual([u["username"] for u in res.data], ["crew", "crew2"])

    def test_superuser_can_manage_groups(self):
        self.login(self.admin)
        self.assertEqual(self.client.get(MANAGER_URL).status_code, 200)

    def test_add_and_remove_manager_by_username(self):
        self.login(self.manager)
        res = self.client.post(MANAGER_URL, {"username": "customer"}, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data["username"], "customer")
        self.assertTrue(self.customer.groups.filter(name="Manager").exists())

        res = self.client.delete(f"{MANAGER_URL}{self.customer.pk}/")
        self.assertEqual(res.status_code, 200)
        self.assertFalse(self.customer.groups.filter(name="Manager").exists())

        # Removing someone who is not in the group -> 404
        self.assertEqual(self.client.delete(f"{MANAGER_URL}{self.customer.pk}/").status_code, 404)

    def test_add_and_remove_delivery_crew_by_user_id(self):
        self.login(self.manager)
        res = self.client.post(CREW_URL, {"user_id": self.customer2.pk}, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        self.assertTrue(self.customer2.groups.filter(name="Delivery Crew").exists())

        self.assertEqual(self.client.delete(f"{CREW_URL}{self.customer2.pk}/").status_code, 200)
        self.assertFalse(self.customer2.groups.filter(name="Delivery Crew").exists())

    def test_unknown_user_is_404_and_empty_payload_is_400(self):
        self.login(self.manager)
        self.assertEqual(
            self.client.post(MANAGER_URL, {"username": "ghost"}, format="json").status_code, 404
        )
        self.assertEqual(self.client.post(MANAGER_URL, {}, format="json").status_code, 400)
        self.assertEqual(self.client.delete(f"{MANAGER_URL}9999/").status_code, 404)
