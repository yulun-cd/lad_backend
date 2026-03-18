from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from task.models import Task


class TaskModelTests(TestCase):
    def test_task_defaults_and_created_at(self):
        task = Task.objects.create(
            name="Evening stretch",
            description="10 minutes",
            energy_level=2,
        )

        self.assertEqual(task.name, "Evening stretch")
        self.assertFalse(task.done)
        self.assertIsNotNone(task.created_at)

    def test_task_str_returns_name(self):
        task = Task(
            name="Read book",
            description="Read one chapter",
            energy_level=3,
        )

        self.assertEqual(str(task), "Read book")

    def test_energy_level_must_be_between_1_and_5(self):
        too_low = Task(
            name="Low",
            description="Invalid low energy",
            energy_level=0,
        )
        too_high = Task(
            name="High",
            description="Invalid high energy",
            energy_level=6,
        )

        with self.assertRaises(ValidationError):
            too_low.full_clean()

        with self.assertRaises(ValidationError):
            too_high.full_clean()


class TaskApiTests(APITestCase):
    def test_create_and_list_tasks(self):
        create_url = reverse("task-list")
        payload = {
            "name": "Read 10 pages",
            "done": False,
            "description": "Read after dinner",
            "energy_level": 3,
        }

        create_response = self.client.post(create_url, payload, format="json")
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        list_response = self.client.get(create_url)
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data), 1)
        self.assertEqual(list_response.data[0]["name"], payload["name"])

    def test_full_crud_flow(self):
        task = Task.objects.create(
            name="Morning jog",
            done=False,
            description="20 minute run",
            energy_level=4,
        )

        detail_url = reverse("task-detail", args=[task.id])

        retrieve_response = self.client.get(detail_url)
        self.assertEqual(retrieve_response.status_code, status.HTTP_200_OK)

        update_payload = {
            "name": "Morning jog",
            "done": True,
            "description": "25 minute run",
            "energy_level": 5,
        }
        update_response = self.client.put(detail_url, update_payload, format="json")
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertTrue(update_response.data["done"])
        self.assertEqual(update_response.data["energy_level"], 5)

        delete_response = self.client.delete(detail_url)
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Task.objects.filter(id=task.id).exists())

    def test_energy_level_validation(self):
        create_url = reverse("task-list")
        payload = {
            "name": "Too tired",
            "done": False,
            "description": "Invalid energy value",
            "energy_level": 8,
        }

        response = self.client.post(create_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("energy_level", response.data)
