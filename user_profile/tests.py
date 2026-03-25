from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class UserProfileApiTests(APITestCase):
    def test_register_login_refresh_and_me(self):
        register_payload = {
            "username": "auth_user",
            "email": "auth@example.com",
            "password": "strong-pass-123",
        }
        register_response = self.client.post(
            reverse("auth-register"),
            register_payload,
            format="json",
        )
        self.assertEqual(register_response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            get_user_model()
            .objects.filter(username=register_payload["username"])
            .exists()
        )

        login_response = self.client.post(
            reverse("auth-login"),
            {
                "username": register_payload["username"],
                "password": register_payload["password"],
            },
            format="json",
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        self.assertIn("access", login_response.data)
        self.assertIn("refresh", login_response.data)

        me_url = reverse("auth-me")
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}"
        )
        me_response = self.client.get(me_url)
        self.assertEqual(me_response.status_code, status.HTTP_200_OK)
        self.assertEqual(me_response.data["username"], register_payload["username"])

        refresh_response = self.client.post(
            reverse("token-refresh"),
            {"refresh": login_response.data["refresh"]},
            format="json",
        )
        self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)
        self.assertIn("access", refresh_response.data)

    def test_me_requires_authentication(self):
        response = self.client.get(reverse("auth-me"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_with_email(self):
        password = "strong-pass-123"
        user = get_user_model().objects.create_user(
            username="email_login_user",
            email="email-login@example.com",
            password=password,
        )

        response = self.client.post(
            reverse("auth-login"),
            {
                "email": user.email,
                "password": password,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_login_requires_username_or_email(self):
        response = self.client.post(
            reverse("auth-login"),
            {
                "password": "strong-pass-123",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("username", response.data)
