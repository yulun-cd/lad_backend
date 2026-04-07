from datetime import timedelta

from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from task.models import Task


class TaskModelTests(TestCase):
    def test_task_defaults_and_created_at(self):
        task = Task.objects.create(
            name="Evening stretch",
            energy_level=2,
        )

        self.assertEqual(task.name, "Evening stretch")
        self.assertFalse(task.done)
        self.assertEqual(task.status, Task.Status.PENDING)
        self.assertEqual(task.description, "")
        self.assertIsNotNone(task.created_at)
        self.assertIsNone(task.updated_at)
        self.assertIsNone(task.completed_at)

    def test_completed_at_is_set_and_cleared_by_status_transition(self):
        task = Task.objects.create(
            name="Finish writeup",
            status=Task.Status.PENDING,
            energy_level=3,
        )
        self.assertIsNone(task.completed_at)

        task.status = Task.Status.COMPLETED
        task.save()
        task.refresh_from_db()
        self.assertIsNotNone(task.completed_at)
        completed_at = task.completed_at

        task.status = Task.Status.COMPLETED
        task.save()
        task.refresh_from_db()
        self.assertEqual(task.completed_at, completed_at)

        task.status = Task.Status.IN_PROGRESS
        task.save()
        task.refresh_from_db()
        self.assertIsNone(task.completed_at)

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
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="task_user",
            password="task-pass-123",
        )
        self.other_user = get_user_model().objects.create_user(
            username="other_task_user",
            password="task-pass-123",
        )

    def test_requires_authentication(self):
        response = self.client.get(reverse("task-list"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_and_list_tasks(self):
        self.client.force_authenticate(user=self.user)
        create_url = reverse("task-list")
        payload = {
            "name": "Read 10 pages",
            "done": False,
            "status": Task.Status.PENDING,
            "energy_level": 3,
        }

        create_response = self.client.post(create_url, payload, format="json")
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        list_response = self.client.get(create_url)
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data), 1)
        self.assertEqual(list_response.data[0]["name"], payload["name"])
        self.assertEqual(
            Task.objects.get(id=list_response.data[0]["id"]).user, self.user
        )

    def test_full_crud_flow(self):
        self.client.force_authenticate(user=self.user)
        task = Task.objects.create(
            user=self.user,
            name="Morning jog",
            done=False,
            status=Task.Status.PENDING,
            description="20 minute run",
            energy_level=4,
        )

        detail_url = reverse("task-detail", args=[task.id])

        retrieve_response = self.client.get(detail_url)
        self.assertEqual(retrieve_response.status_code, status.HTTP_200_OK)

        update_payload = {
            "name": "Morning jog",
            "done": True,
            "status": Task.Status.COMPLETED,
            "description": "25 minute run",
            "energy_level": 5,
        }
        update_response = self.client.put(detail_url, update_payload, format="json")
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertTrue(update_response.data["done"])
        self.assertEqual(update_response.data["status"], Task.Status.COMPLETED)
        self.assertEqual(update_response.data["energy_level"], 5)
        self.assertIsNotNone(update_response.data["completed_at"])

        task.refresh_from_db()
        self.assertIsNotNone(task.updated_at)
        self.assertEqual(
            update_response.data["updated_at"],
            task.updated_at.isoformat().replace("+00:00", "Z"),
        )
        self.assertEqual(
            update_response.data["completed_at"],
            task.completed_at.isoformat().replace("+00:00", "Z"),
        )

        delete_response = self.client.delete(detail_url)
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Task.objects.filter(id=task.id).exists())

    def test_user_cannot_access_another_users_task(self):
        self.client.force_authenticate(user=self.user)
        other_task = Task.objects.create(
            user=self.other_user,
            name="Private task",
            done=False,
            description="Not visible",
            energy_level=3,
        )

        detail_url = reverse("task-detail", args=[other_task.id])
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_energy_level_validation(self):
        self.client.force_authenticate(user=self.user)
        create_url = reverse("task-list")
        payload = {
            "name": "Too tired",
            "done": False,
            "status": Task.Status.PENDING,
            "description": "Invalid energy value",
            "energy_level": 8,
        }

        response = self.client.post(create_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("energy_level", response.data)

    def test_status_validation(self):
        self.client.force_authenticate(user=self.user)
        create_url = reverse("task-list")
        payload = {
            "name": "Bad status",
            "done": False,
            "status": "UNKNOWN",
            "description": "",
            "energy_level": 3,
        }

        response = self.client.post(create_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("status", response.data)

    def test_list_filters_by_status(self):
        self.client.force_authenticate(user=self.user)
        Task.objects.create(
            user=self.user,
            name="Task pending",
            status=Task.Status.PENDING,
            energy_level=3,
        )
        Task.objects.create(
            user=self.user,
            name="Task done",
            status=Task.Status.COMPLETED,
            energy_level=4,
        )

        response = self.client.get(
            reverse("task-list"),
            {"status": Task.Status.COMPLETED},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], "Task done")
        self.assertEqual(response.data[0]["status"], Task.Status.COMPLETED)

    def test_list_filter_rejects_invalid_status(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(reverse("task-list"), {"status": "INVALID"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("status", response.data)

    def test_list_orders_by_status_then_last_activity(self):
        self.client.force_authenticate(user=self.user)
        base_time = timezone.now() - timedelta(days=2)

        completed = Task.objects.create(
            user=self.user,
            name="Completed newest",
            status=Task.Status.COMPLETED,
            energy_level=2,
        )
        pending_old = Task.objects.create(
            user=self.user,
            name="Pending old",
            status=Task.Status.PENDING,
            energy_level=3,
        )
        pending_updated = Task.objects.create(
            user=self.user,
            name="Pending updated",
            status=Task.Status.PENDING,
            energy_level=4,
        )
        in_progress = Task.objects.create(
            user=self.user,
            name="In progress oldest",
            status=Task.Status.IN_PROGRESS,
            energy_level=5,
        )

        Task.objects.filter(id=completed.id).update(
            created_at=base_time + timedelta(hours=4)
        )
        Task.objects.filter(id=pending_old.id).update(
            created_at=base_time + timedelta(hours=2)
        )
        Task.objects.filter(id=pending_updated.id).update(
            created_at=base_time + timedelta(hours=1)
        )
        Task.objects.filter(id=in_progress.id).update(created_at=base_time)

        pending_updated.description = "updated"
        pending_updated.save()

        response = self.client.get(reverse("task-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ordered_names = [item["name"] for item in response.data]
        self.assertEqual(
            ordered_names,
            [
                "In progress oldest",
                "Pending updated",
                "Pending old",
                "Completed newest",
            ],
        )


class TaskTagApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="tag_user", password="pass"
        )
        self.other_user = get_user_model().objects.create_user(
            username="other_tag_user", password="pass"
        )

    def _make_tag(self, user=None, name="Work", color="#FF0000"):
        user = user or self.user
        from task.models import TaskTag

        return TaskTag.objects.create(name=name, color=color, created_by=user)

    def test_requires_authentication(self):
        response = self.client.get(reverse("task-tag-list"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_tag(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            reverse("task-tag-list"),
            {"name": "Work", "color": "#FF0000"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "Work")
        self.assertEqual(response.data["color"], "#FF0000")
        self.assertIn("id", response.data)
        self.assertIn("created_at", response.data)

    def test_create_tag_invalid_color(self):
        self.client.force_authenticate(user=self.user)
        for bad_color in ("red", "FF0000", "#GGG", "#1234567"):
            response = self.client.post(
                reverse("task-tag-list"),
                {"name": "Bad", "color": bad_color},
                format="json",
            )
            self.assertEqual(
                response.status_code, status.HTTP_400_BAD_REQUEST, msg=bad_color
            )
            self.assertIn("color", response.data)

    def test_list_only_own_tags(self):
        self.client.force_authenticate(user=self.user)
        self._make_tag(self.user, "Mine", "#AABBCC")
        self._make_tag(self.other_user, "Theirs", "#112233")

        response = self.client.get(reverse("task-tag-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], "Mine")

    def test_retrieve_own_tag(self):
        self.client.force_authenticate(user=self.user)
        tag = self._make_tag()
        response = self.client.get(reverse("task-tag-detail", args=[tag.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_cannot_access_other_users_tag(self):
        self.client.force_authenticate(user=self.user)
        other_tag = self._make_tag(self.other_user, "Theirs", "#123456")
        response = self.client.get(reverse("task-tag-detail", args=[other_tag.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_tag(self):
        self.client.force_authenticate(user=self.user)
        tag = self._make_tag()
        response = self.client.put(
            reverse("task-tag-detail", args=[tag.id]),
            {"name": "Personal", "color": "#00FF00"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Personal")
        self.assertEqual(response.data["color"], "#00FF00")

    def test_delete_tag(self):
        self.client.force_authenticate(user=self.user)
        tag = self._make_tag()
        response = self.client.delete(reverse("task-tag-detail", args=[tag.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        from task.models import TaskTag

        self.assertFalse(TaskTag.objects.filter(id=tag.id).exists())

    def test_cannot_delete_other_users_tag(self):
        self.client.force_authenticate(user=self.user)
        other_tag = self._make_tag(self.other_user, "Theirs", "#123456")
        response = self.client.delete(reverse("task-tag-detail", args=[other_tag.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class TaskTagRelationTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="taskrel_user", password="pass"
        )
        self.other_user = get_user_model().objects.create_user(
            username="taskrel_other", password="pass"
        )
        from task.models import TaskTag

        self.tag = TaskTag.objects.create(
            name="Work", color="#FF0000", created_by=self.user
        )
        self.other_tag = TaskTag.objects.create(
            name="Other", color="#0000FF", created_by=self.other_user
        )

    def test_create_task_with_tag(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            reverse("task-list"),
            {
                "name": "Tagged task",
                "energy_level": 3,
                "status": "PENDING",
                "tag": self.tag.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["tag"], self.tag.id)

    def test_create_task_without_tag(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            reverse("task-list"),
            {"name": "Untagged", "energy_level": 2, "status": "PENDING"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(response.data["tag"])

    def test_cannot_assign_other_users_tag_to_task(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            reverse("task-list"),
            {
                "name": "Bad tag",
                "energy_level": 2,
                "status": "PENDING",
                "tag": self.other_tag.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("tag", response.data)

    def test_update_task_tag_to_null(self):
        self.client.force_authenticate(user=self.user)
        task = Task.objects.create(
            user=self.user, name="Task", energy_level=2, tag=self.tag
        )
        response = self.client.put(
            reverse("task-detail", args=[task.id]),
            {"name": "Task", "energy_level": 2, "status": "PENDING", "tag": None},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["tag"])

    def test_tag_nulled_when_tag_deleted(self):
        self.client.force_authenticate(user=self.user)
        task = Task.objects.create(
            user=self.user, name="Task", energy_level=2, tag=self.tag
        )
        self.tag.delete()
        task.refresh_from_db()
        self.assertIsNone(task.tag)

    def test_filter_tasks_by_tag_id(self):
        self.client.force_authenticate(user=self.user)
        Task.objects.create(user=self.user, name="Tagged", energy_level=2, tag=self.tag)
        Task.objects.create(user=self.user, name="Untagged", energy_level=2)
        response = self.client.get(reverse("task-list") + f"?tag={self.tag.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [t["name"] for t in response.data]
        self.assertIn("Tagged", names)
        self.assertNotIn("Untagged", names)

    def test_filter_tasks_by_multiple_tag_ids(self):
        self.client.force_authenticate(user=self.user)
        from task.models import TaskTag
        tag2 = TaskTag.objects.create(name="Home", color="#00FF00", created_by=self.user)
        Task.objects.create(user=self.user, name="Work task", energy_level=2, tag=self.tag)
        Task.objects.create(user=self.user, name="Home task", energy_level=2, tag=tag2)
        Task.objects.create(user=self.user, name="Untagged", energy_level=2)
        response = self.client.get(reverse("task-list") + f"?tag={self.tag.id}&tag={tag2.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [t["name"] for t in response.data]
        self.assertIn("Work task", names)
        self.assertIn("Home task", names)
        self.assertNotIn("Untagged", names)

    def test_filter_by_invalid_tag_id_returns_400(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("task-list") + "?tag=notanid")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("tag", response.data)

    def test_filter_by_nonexistent_tag_returns_empty(self):
        self.client.force_authenticate(user=self.user)
        Task.objects.create(user=self.user, name="Tagged", energy_level=2, tag=self.tag)
        response = self.client.get(reverse("task-list") + "?tag=99999")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)
