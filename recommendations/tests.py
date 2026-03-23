"""Тесты API рекомендаций."""
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from recommendations.models import Item, Interaction, RecommendationUser


class RecommendationAPITestCase(TestCase):
    """Тесты эндпоинта рекомендаций."""

    def setUp(self):
        self.client = APIClient()
        self.user = RecommendationUser.objects.create(username="test_user")
        self.item1 = Item.objects.create(name="Movie 1", item_type="movie")
        self.item2 = Item.objects.create(name="Movie 2", item_type="movie")
        Interaction.objects.create(
            user=self.user,
            item=self.item1,
            interaction_type=Interaction.VIEWED,
        )

    def test_get_recommendations_returns_200(self):
        """GET /api/recommendations/{user_id}/ возвращает 200."""
        response = self.client.get(
            f"/api/recommendations/{self.user.pk}/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_recommendations_has_recommendations_key(self):
        """Ответ содержит ключ 'recommendations'."""
        response = self.client.get(
            f"/api/recommendations/{self.user.pk}/"
        )
        self.assertIn("recommendations", response.json())

    def test_get_recommendations_with_algorithm_param(self):
        """Параметр algorithm выбирает алгоритм."""
        for algo in ("hybrid", "pagerank", "collaborative", "knn"):
            response = self.client.get(
                f"/api/recommendations/{self.user.pk}/",
                {"algorithm": algo, "limit": 5},
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_recommendations_nonexistent_user_returns_200(self):
        """Несуществующий user_id всё равно 200 (пустой список)."""
        response = self.client.get("/api/recommendations/99999/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.json()["recommendations"], list)


class PreferenceAPITestCase(TestCase):
    """Тесты POST /api/preferences/."""

    def setUp(self):
        self.client = APIClient()
        self.user = RecommendationUser.objects.create(username="user1")
        self.item = Item.objects.create(name="Book 1", item_type="book")

    def test_add_preference_returns_201(self):
        """POST с валидными данными возвращает 201."""
        response = self.client.post(
            "/api/preferences/",
            {
                "user_id": self.user.pk,
                "item_id": self.item.pk,
                "interaction_type": "viewed",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Interaction.objects.count(), 1)

    def test_add_preference_rated_requires_rating(self):
        """Тип 'rated' требует оценку."""
        response = self.client.post(
            "/api/preferences/",
            {
                "user_id": self.user.pk,
                "item_id": self.item.pk,
                "interaction_type": "rated",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ItemsAndStatisticsTestCase(TestCase):
    """Тесты items и statistics."""

    def setUp(self):
        self.client = APIClient()
        RecommendationUser.objects.create(username="u1")
        Item.objects.create(name="Item 1", item_type="movie")

    def test_get_items_returns_200(self):
        response = self.client.get("/api/items/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.json(), list)

    def test_get_statistics_returns_200(self):
        response = self.client.get("/api/statistics/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("users_count", data)
        self.assertIn("items_count", data)
        self.assertIn("interactions_count", data)

    def test_get_popular_returns_200(self):
        response = self.client.get("/api/statistics/popular/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_user_preferences_returns_200(self):
        user = RecommendationUser.objects.get(username="u1")
        response = self.client.get(f"/api/users/{user.pk}/preferences/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
