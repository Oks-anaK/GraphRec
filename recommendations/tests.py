"""Тесты API рекомендаций."""

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from recommendations.models import Interaction, Item, RecommendationUser


class RecommendationAPITestCase(TestCase):
    """GET /api/recommendations/<id>/."""

    def setUp(self):
        """Фикстура: пользователь, элементы, одно взаимодействие."""
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
        """Код ответа 200."""
        url = reverse("recommendations:recommendations", args=[self.user.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_recommendations_has_recommendations_key(self):
        """В JSON есть ключ recommendations."""
        url = reverse("recommendations:recommendations", args=[self.user.pk])
        response = self.client.get(url)
        self.assertIn("recommendations", response.json())

    def test_get_recommendations_with_algorithm_param(self):
        """Параметр algorithm: hybrid, pagerank, collaborative, knn."""
        url = reverse("recommendations:recommendations", args=[self.user.pk])
        for algo in ("hybrid", "pagerank", "collaborative", "knn"):
            response = self.client.get(url, {"algorithm": algo, "limit": 5})
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_recommendations_nonexistent_user_returns_200(self):
        """Несуществующий user — 200 и пустой список."""
        response = self.client.get(reverse("recommendations:recommendations", args=[99999]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.json()["recommendations"], list)

    def test_get_recommendations_response_item_format(self):
        """Элементы — пары [узел, число]."""
        url = reverse("recommendations:recommendations", args=[self.user.pk])
        response = self.client.get(url, {"algorithm": "pagerank", "limit": 3})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        recs = response.json()["recommendations"]
        for pair in recs:
            self.assertEqual(len(pair), 2)
            self.assertIsInstance(pair[0], str)
            self.assertTrue(pair[0].startswith("i_"))
            self.assertIsInstance(pair[1], (int, float))

    def test_get_recommendations_invalid_limit_defaults(self):
        """Некорректный limit не ломает запрос."""
        url = reverse("recommendations:recommendations", args=[self.user.pk])
        response = self.client.get(url, {"limit": "abc"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class PreferenceAPITestCase(TestCase):
    """POST /api/preferences/."""

    def setUp(self):
        """Пользователь и элемент."""
        self.client = APIClient()
        self.user = RecommendationUser.objects.create(username="user1")
        self.item = Item.objects.create(name="Book 1", item_type="book")

    def test_add_preference_returns_201(self):
        """Валидный POST — 201, одна запись Interaction."""
        url = reverse("recommendations:add_preference")
        response = self.client.post(
            url,
            {
                "user_id": self.user.pk,
                "item_id": self.item.pk,
                "interaction_type": "viewed",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Interaction.objects.count(), 1)

    def test_add_preference_response_has_ids(self):
        """В ответе id, user_id, item_id."""
        url = reverse("recommendations:add_preference")
        response = self.client.post(
            url,
            {
                "user_id": self.user.pk,
                "item_id": self.item.pk,
                "interaction_type": "liked",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertIn("id", data)
        self.assertEqual(data["user_id"], self.user.pk)
        self.assertEqual(data["item_id"], self.item.pk)

    def test_add_preference_rated_requires_rating(self):
        """rated без rating — 400."""
        url = reverse("recommendations:add_preference")
        response = self.client.post(
            url,
            {
                "user_id": self.user.pk,
                "item_id": self.item.pk,
                "interaction_type": "rated",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_add_preference_rated_with_rating_201(self):
        """rated с rating — сохраняется оценка."""
        url = reverse("recommendations:add_preference")
        response = self.client.post(
            url,
            {
                "user_id": self.user.pk,
                "item_id": self.item.pk,
                "interaction_type": "rated",
                "rating": 4.5,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        inter = Interaction.objects.get()
        self.assertEqual(inter.interaction_type, Interaction.RATED)
        self.assertEqual(inter.rating, 4.5)

    def test_add_preference_unknown_user_400(self):
        """Несуществующий user_id — 400."""
        url = reverse("recommendations:add_preference")
        response = self.client.post(
            url,
            {
                "user_id": 99999,
                "item_id": self.item.pk,
                "interaction_type": "viewed",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_add_preference_unknown_item_400(self):
        """Несуществующий item_id — 400."""
        url = reverse("recommendations:add_preference")
        response = self.client.post(
            url,
            {
                "user_id": self.user.pk,
                "item_id": 99999,
                "interaction_type": "viewed",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_add_preference_update_or_create_same_pair(self):
        """Повтор той же пары user+item обновляет строку."""
        url = reverse("recommendations:add_preference")
        self.client.post(
            url,
            {
                "user_id": self.user.pk,
                "item_id": self.item.pk,
                "interaction_type": "viewed",
            },
            format="json",
        )
        self.assertEqual(Interaction.objects.count(), 1)
        response = self.client.post(
            url,
            {
                "user_id": self.user.pk,
                "item_id": self.item.pk,
                "interaction_type": "purchased",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Interaction.objects.count(), 1)
        self.assertEqual(
            Interaction.objects.get().interaction_type,
            Interaction.PURCHASED,
        )


class ItemAPITestCase(TestCase):
    """GET /api/items/."""

    def setUp(self):
        """Один элемент «Книга»."""
        self.client = APIClient()
        self.item = Item.objects.create(
            name="Книга",
            item_type="book",
        )

    def test_item_list(self):
        """Список — JSON-массив, имя и тип совпадают."""
        url = reverse("recommendations:items")
        response = self.client.get(url)
        data = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0].get("name"), "Книга")
        self.assertEqual(data[0].get("item_type"), "book")


class UserRecommendationAPITestCase(TestCase):
    """POST preferences и GET users/.../preferences/."""

    def setUp(self):
        """Два пользователя и элемент."""
        self.client = APIClient()
        self.user = RecommendationUser.objects.create(username="test@example.com")
        self.other_user = RecommendationUser.objects.create(username="other@example.com")
        self.item = Item.objects.create(
            name="Фильм",
            item_type="movie",
        )

    def test_interaction_create(self):
        """POST создаёт Interaction."""
        url = reverse("recommendations:add_preference")
        response = self.client.post(
            url,
            {
                "user_id": self.user.pk,
                "item_id": self.item.pk,
                "interaction_type": "viewed",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Interaction.objects.count(), 1)
        self.assertEqual(Interaction.objects.first().user, self.user)

    def test_get_user_preferences_list(self):
        """GET возвращает список с item_name."""
        Interaction.objects.create(
            user=self.user,
            item=self.item,
            interaction_type=Interaction.VIEWED,
        )
        url = reverse(
            "recommendations:user_preferences",
            args=[self.user.pk],
        )
        response = self.client.get(url)
        data = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0].get("item_name"), "Фильм")


class StatisticsAPITestCase(TestCase):
    """Эндпоинты /api/statistics/*."""

    def setUp(self):
        """Пользователь, элемент, одно взаимодействие."""
        self.client = APIClient()
        u = RecommendationUser.objects.create(username="s1")
        it = Item.objects.create(name="Pop", item_type="movie")
        Interaction.objects.create(
            user=u,
            item=it,
            interaction_type=Interaction.VIEWED,
        )

    def test_get_statistics_returns_200(self):
        """Общая статистика — 200 и нужные ключи."""
        url = reverse("recommendations:statistics")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("users_count", data)
        self.assertIn("items_count", data)
        self.assertIn("interactions_count", data)

    def test_get_statistics_counts(self):
        """Счётчики совпадают с ORM."""
        url = reverse("recommendations:statistics")
        response = self.client.get(url)
        data = response.json()
        self.assertEqual(data["users_count"], RecommendationUser.objects.count())
        self.assertEqual(data["items_count"], Item.objects.count())
        self.assertEqual(data["interactions_count"], Interaction.objects.count())

    def test_get_popular_returns_200(self):
        """Популярное — 200."""
        url = reverse("recommendations:popular")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_popular_structure_and_limit(self):
        """Не больше limit элементов, поля name и interaction_count."""
        response = self.client.get(
            reverse("recommendations:popular"),
            {"limit": 5},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertLessEqual(len(data), 5)
        if data:
            self.assertIn("interaction_count", data[0])
            self.assertIn("name", data[0])

    def test_get_distribution_returns_200(self):
        """Распределение — ключи interaction_types и rating_distribution."""
        url = reverse("recommendations:statistics_distribution")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("interaction_types", data)
        self.assertIn("rating_distribution", data)

    def test_get_user_preferences_unknown_user_404(self):
        """Нет пользователя — 404."""
        response = self.client.get(reverse("recommendations:user_preferences", args=[99999]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class WebUITestCase(TestCase):
    """Веб-интерфейс (HTML, Bootstrap)."""

    def test_home_200(self):
        """Главная страница открывается."""
        response = self.client.get(reverse("web:home"))
        self.assertEqual(response.status_code, 200)

    def test_preferences_get_200(self):
        """Страница предпочтений."""
        response = self.client.get(reverse("web:preferences"))
        self.assertEqual(response.status_code, 200)

    def test_recommendations_get_200(self):
        """Страница рекомендаций."""
        response = self.client.get(reverse("web:recommendations"))
        self.assertEqual(response.status_code, 200)

    def test_statistics_get_200(self):
        """Страница статистики."""
        response = self.client.get(reverse("web:statistics"))
        self.assertEqual(response.status_code, 200)

    def test_api_root_200(self):
        """Корень /api/ — оглавление эндпоинтов."""
        response = self.client.get(reverse("recommendations:api_root"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "REST API")

    def test_preferences_post_creates_interaction(self):
        """POST формы предпочтений создаёт Interaction."""
        user = RecommendationUser.objects.create(username="web_user")
        item = Item.objects.create(name="Item W", item_type="movie")
        url = reverse("web:preferences")
        response = self.client.post(
            url,
            {
                "user": str(user.pk),
                "item": str(item.pk),
                "interaction_type": Interaction.VIEWED,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Interaction.objects.count(), 1)
