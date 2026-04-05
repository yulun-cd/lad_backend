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

    def test_change_password_requires_authentication(self):
        response = self.client.post(
            reverse("change-password"),
            {
                "current_password": "old-pass",
                "new_password": "new-pass-123",
                "new_password_confirm": "new-pass-123",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_change_password_succeeds_with_correct_current_password(self):
        old_password = "old-password-123"
        new_password = "new-password-456"
        user = get_user_model().objects.create_user(
            username="password_change_user",
            email="pwchange@example.com",
            password=old_password,
        )

        self.client.force_authenticate(user=user)
        response = self.client.post(
            reverse("change-password"),
            {
                "current_password": old_password,
                "new_password": new_password,
                "new_password_confirm": new_password,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["detail"], "Password changed successfully.")

        user.refresh_from_db()
        self.assertTrue(user.check_password(new_password))
        self.assertFalse(user.check_password(old_password))

        login_response = self.client.post(
            reverse("auth-login"),
            {
                "username": user.username,
                "password": new_password,
            },
            format="json",
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)

    def test_login_falls_back_to_email_when_username_is_wrong(self):
        password = "strong-pass-123"
        user = get_user_model().objects.create_user(
            username="yulun",
            email="linyulun0620@gmail.com",
            password=password,
        )

        response = self.client.post(
            reverse("auth-login"),
            {
                "username": "wrong-username",
                "email": user.email,
                "password": password,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_change_password_fails_with_incorrect_current_password(self):
        password = "correct-password-123"
        user = get_user_model().objects.create_user(
            username="pw_fail_user",
            email="pwfail@example.com",
            password=password,
        )

        self.client.force_authenticate(user=user)
        response = self.client.post(
            reverse("change-password"),
            {
                "current_password": "wrong-password",
                "new_password": "new-password-456",
                "new_password_confirm": "new-password-456",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("current_password", response.data)

    def test_change_password_fails_with_mismatched_new_passwords(self):
        password = "password-123"
        user = get_user_model().objects.create_user(
            username="pw_mismatch_user",
            email="pwmismatch@example.com",
            password=password,
        )

        self.client.force_authenticate(user=user)
        response = self.client.post(
            reverse("change-password"),
            {
                "current_password": password,
                "new_password": "new-password-456",
                "new_password_confirm": "different-password-789",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("new_password_confirm", response.data)
