from datetime import date

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
    def test_create_and_list_daily_logs(self):
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

    def test_full_crud_flow(self):
        log = DailyLog.objects.create(
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

        delete_response = self.client.delete(detail_url)
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(DailyLog.objects.filter(id=log.id).exists())

    def test_validation_for_out_of_range_values(self):
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
