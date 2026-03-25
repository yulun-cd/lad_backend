from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from daily_log.models import DailyLog


class DailyLogModelTests(TestCase):
    def test_description_is_optional(self):
        log = DailyLog.objects.create(
            date=date(2026, 3, 18),
            overall=4,
            energy=3,
            emotion=5,
            productivity=4,
        )

        self.assertEqual(log.description, "")
        self.assertIsNone(log.updated_at)

    def test_rating_fields_must_be_between_1_and_5(self):
        log = DailyLog(
            date=date(2026, 3, 18),
            overall=0,
            energy=6,
            emotion=3,
            productivity=3,
            description="invalid",
        )

        with self.assertRaises(ValidationError):
            log.full_clean()


class DailyLogApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="daily_user",
            password="daily-pass-123",
        )
        self.other_user = get_user_model().objects.create_user(
            username="other_daily_user",
            password="daily-pass-123",
        )

    def test_requires_authentication(self):
        response = self.client.get(reverse("daily-log-list"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_and_list_daily_logs(self):
        self.client.force_authenticate(user=self.user)
        list_url = reverse("daily-log-list")
        payload = {
            "date": "2026-03-18",
            "overall": 4,
            "energy": 4,
            "emotion": 3,
            "productivity": 5,
            "description": "Solid day",
        }

        create_response = self.client.post(list_url, payload, format="json")
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        list_response = self.client.get(list_url)
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data), 1)
        self.assertEqual(list_response.data[0]["date"], payload["date"])
        self.assertEqual(
            DailyLog.objects.get(id=list_response.data[0]["id"]).user,
            self.user,
        )

    def test_list_orders_by_date_descending(self):
        self.client.force_authenticate(user=self.user)
        DailyLog.objects.create(
            user=self.user,
            date=date(2026, 3, 18),
            overall=3,
            energy=3,
            emotion=3,
            productivity=3,
            description="middle",
        )
        DailyLog.objects.create(
            user=self.user,
            date=date(2026, 3, 20),
            overall=4,
            energy=4,
            emotion=4,
            productivity=4,
            description="newest",
        )
        DailyLog.objects.create(
            user=self.user,
            date=date(2026, 3, 15),
            overall=2,
            energy=2,
            emotion=2,
            productivity=2,
            description="oldest",
        )

        response = self.client.get(reverse("daily-log-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item["date"] for item in response.data],
            ["2026-03-20", "2026-03-18", "2026-03-15"],
        )

    def test_full_crud_flow(self):
        self.client.force_authenticate(user=self.user)
        log = DailyLog.objects.create(
            user=self.user,
            date=date(2026, 3, 17),
            overall=3,
            energy=2,
            emotion=4,
            productivity=3,
            description="Average day",
        )
        detail_url = reverse("daily-log-detail", args=[log.id])

        retrieve_response = self.client.get(detail_url)
        self.assertEqual(retrieve_response.status_code, status.HTTP_200_OK)

        update_payload = {
            "date": "2026-03-17",
            "overall": 5,
            "energy": 5,
            "emotion": 4,
            "productivity": 5,
            "description": "Great day",
        }
        update_response = self.client.put(detail_url, update_payload, format="json")
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertEqual(update_response.data["overall"], 5)

        log.refresh_from_db()
        self.assertIsNotNone(log.updated_at)
        self.assertEqual(
            update_response.data["updated_at"],
            log.updated_at.isoformat().replace("+00:00", "Z"),
        )

        delete_response = self.client.delete(detail_url)
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(DailyLog.objects.filter(id=log.id).exists())

    def test_user_cannot_access_another_users_daily_log(self):
        self.client.force_authenticate(user=self.user)
        other_log = DailyLog.objects.create(
            user=self.other_user,
            date=date(2026, 3, 19),
            overall=4,
            energy=4,
            emotion=4,
            productivity=4,
            description="Private",
        )

        detail_url = reverse("daily-log-detail", args=[other_log.id])
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_validation_for_out_of_range_values(self):
        self.client.force_authenticate(user=self.user)
        list_url = reverse("daily-log-list")
        payload = {
            "date": "2026-03-18",
            "overall": 9,
            "energy": 4,
            "emotion": 3,
            "productivity": 5,
            "description": "invalid",
        }

        response = self.client.post(list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("overall", response.data)

    def test_cannot_create_daily_log_with_future_date(self):
        self.client.force_authenticate(user=self.user)
        list_url = reverse("daily-log-list")
        future_date = (date.today() + timedelta(days=1)).isoformat()
        payload = {
            "date": future_date,
            "overall": 4,
            "energy": 4,
            "emotion": 3,
            "productivity": 5,
            "description": "future day",
        }

        response = self.client.post(list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("date", response.data)

    def test_can_create_daily_log_with_today_date(self):
        self.client.force_authenticate(user=self.user)
        list_url = reverse("daily-log-list")
        today = date.today().isoformat()
        payload = {
            "date": today,
            "overall": 4,
            "energy": 4,
            "emotion": 3,
            "productivity": 5,
            "description": "today's log",
        }

        response = self.client.post(list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["date"], today)

    def test_cannot_update_daily_log_with_future_date(self):
        self.client.force_authenticate(user=self.user)
        log = DailyLog.objects.create(
            user=self.user,
            date=date.today(),
            overall=3,
            energy=2,
            emotion=4,
            productivity=3,
            description="Current log",
        )
        detail_url = reverse("daily-log-detail", args=[log.id])
        future_date = (date.today() + timedelta(days=2)).isoformat()
        update_payload = {
            "date": future_date,
            "overall": 5,
            "energy": 5,
            "emotion": 4,
            "productivity": 5,
            "description": "Updated to future",
        }

        response = self.client.put(detail_url, update_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("date", response.data)

    def test_cannot_create_duplicate_daily_log_for_same_date(self):
        self.client.force_authenticate(user=self.user)
        test_date = date(2026, 3, 15).isoformat()
        list_url = reverse("daily-log-list")
        payload = {
            "date": test_date,
            "overall": 4,
            "energy": 4,
            "emotion": 3,
            "productivity": 5,
            "description": "first log",
        }

        create_response = self.client.post(list_url, payload, format="json")
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        duplicate_payload = {
            "date": test_date,
            "overall": 3,
            "energy": 3,
            "emotion": 2,
            "productivity": 3,
            "description": "duplicate log",
        }
        duplicate_response = self.client.post(
            list_url, duplicate_payload, format="json"
        )
        self.assertEqual(duplicate_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "daily log for this date already exists",
            str(duplicate_response.data).lower(),
        )

    def test_different_users_can_have_daily_log_same_date(self):
        list_url = reverse("daily-log-list")
        test_date = date(2026, 3, 15).isoformat()

        self.client.force_authenticate(user=self.user)
        payload = {
            "date": test_date,
            "overall": 4,
            "energy": 4,
            "emotion": 3,
            "productivity": 5,
            "description": "user 1 log",
        }
        response1 = self.client.post(list_url, payload, format="json")
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)

        self.client.force_authenticate(user=self.other_user)
        payload["description"] = "user 2 log"
        response2 = self.client.post(list_url, payload, format="json")
        self.assertEqual(response2.status_code, status.HTTP_201_CREATED)
