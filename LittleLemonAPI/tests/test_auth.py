from .base import PASSWORD, APITestBase


class DjoserAuthTests(APITestBase):
    def test_register_login_and_me(self):
        res = self.client.post(
            "/api/users/",
            {"username": "newbie", "email": "newbie@example.com", "password": PASSWORD},
            format="json",
        )
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data["username"], "newbie")

        res = self.client.post(
            "/api/token/login/", {"username": "newbie", "password": PASSWORD}, format="json"
        )
        self.assertEqual(res.status_code, 200, res.data)
        token = res.data["auth_token"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        res = self.client.get("/api/users/me/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["username"], "newbie")

        res = self.client.get("/api/users/users/me/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["username"], "newbie")

    def test_wrong_password_is_400(self):
        res = self.client.post(
            "/api/token/login/", {"username": "customer", "password": "wrong"}, format="json"
        )
        self.assertEqual(res.status_code, 400)

    def test_me_requires_authentication(self):
        self.assertEqual(self.client.get("/api/users/me/").status_code, 401)

    def test_protected_endpoints_return_401_for_anonymous(self):
        for path in ("/api/orders/", "/api/cart/menu-items/", "/api/groups/manager/users/"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 401)
