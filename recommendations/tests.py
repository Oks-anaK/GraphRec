"""Тесты API рекомендаций."""

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from recommendations.forms import PreferenceForm
from recommendations.graph import build_graph
from recommendations.services.recommendation_service import (
    _normalize_scores,
    get_recommendations,
    invalidate_recommendations_cache,
)
from recommendations.statistics_data import get_popular_items
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


class RecommendationServiceCoverageTestCase(TestCase):
    """Покрытие сервиса рекомендаций, графа и вспомогательных веток."""

    def test_normalize_scores_empty(self):
        """Пустой список — пустой словарь."""
        self.assertEqual(_normalize_scores([]), {})

    def test_normalize_scores_all_equal(self):
        """Равные оценки — все 1.0 после нормализации."""
        out = _normalize_scores([("i_1", 3.0), ("i_2", 3.0)])
        self.assertEqual(out["i_1"], 1.0)
        self.assertEqual(out["i_2"], 1.0)

    def test_get_recommendations_unknown_algorithm_falls_back_to_hybrid(self):
        """Неизвестный algorithm — как гибрид (ветка else)."""
        cache.clear()
        user = RecommendationUser.objects.create(username="unk_algo_u")
        url = reverse("recommendations:recommendations", args=[user.pk])
        response = self.client.get(url, {"algorithm": "not-a-real-algorithm", "limit": 3})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("recommendations", response.json())

    def test_get_recommendations_pagerank_cache_hit(self):
        """Повторный GET с теми же параметрами — ответ из кэша."""
        cache.clear()
        user = RecommendationUser.objects.create(username="cache_pr_u")
        item = Item.objects.create(name="Cache Item", item_type="movie")
        Interaction.objects.create(user=user, item=item, interaction_type=Interaction.VIEWED)
        url = reverse("recommendations:recommendations", args=[user.pk])
        first = self.client.get(url, {"algorithm": "pagerank", "limit": 5})
        second = self.client.get(url, {"algorithm": "pagerank", "limit": 5})
        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(first.json(), second.json())

    def test_hybrid_with_many_users_exercises_algorithms(self):
        """≥6 пользователей — CF и k-NN не сразу возвращают []."""
        cache.clear()
        users = [RecommendationUser.objects.create(username=f"hyb{i}") for i in range(6)]
        items = [Item.objects.create(name=f"HItem{j}", item_type="movie") for j in range(4)]
        for i, u in enumerate(users):
            Interaction.objects.create(
                user=u,
                item=items[i % 3],
                interaction_type=Interaction.VIEWED,
            )
        Interaction.objects.create(
            user=users[0],
            item=items[3],
            interaction_type=Interaction.PURCHASED,
        )
        Interaction.objects.create(
            user=users[0],
            item=items[1],
            interaction_type=Interaction.RATED,
            rating=4.0,
        )
        out = get_recommendations(users[0].pk, algorithm="hybrid", limit=5)
        self.assertIsInstance(out, list)

    def test_build_graph_and_pagerank_paths(self):
        """Граф: разные типы рёбер и PageRank по существующему пользователю."""
        u = RecommendationUser.objects.create(username="graph_u")
        i1 = Item.objects.create(name="G1", item_type="book")
        i2 = Item.objects.create(name="G2", item_type="movie")
        Interaction.objects.create(user=u, item=i1, interaction_type=Interaction.LIKED)
        Interaction.objects.create(user=u, item=i2, interaction_type=Interaction.RATED, rating=5.0)
        G = build_graph()
        self.assertTrue(G.has_node(f"u_{u.pk}"))
        self.assertTrue(G.has_edge(f"u_{u.pk}", f"i_{i1.pk}"))
        cache.clear()
        pr_out = get_recommendations(u.pk, algorithm="pagerank", limit=3)
        self.assertIsInstance(pr_out, list)

    def test_invalidate_recommendations_cache_runs(self):
        """Сброс кэша по шаблону не падает."""
        u = RecommendationUser.objects.create(username="inv_cache_u")
        invalidate_recommendations_cache(u.pk)


class ModelAndSerializerExtrasTestCase(TestCase):
    """__str__ моделей, сериализатор, форма, statistics_data."""

    def test_model_str(self):
        """Строковое представление моделей."""
        u = RecommendationUser.objects.create(username="str_user")
        i = Item.objects.create(name="Str Item", item_type="book")
        inter = Interaction.objects.create(
            user=u,
            item=i,
            interaction_type=Interaction.VIEWED,
        )
        self.assertEqual(str(u), "str_user")
        self.assertEqual(str(i), "Str Item")
        self.assertIn("str_user", str(inter))
        self.assertIn("Str Item", str(inter))

    def test_preference_form_rated_requires_rating(self):
        """clean(): тип «Оценка» без rating — ошибка поля."""
        u = RecommendationUser.objects.create(username="form_u")
        i = Item.objects.create(name="Form Item", item_type="movie")
        form = PreferenceForm(
            data={
                "user": u.pk,
                "item": i.pk,
                "interaction_type": Interaction.RATED,
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("rating", form.errors)

    def test_get_popular_items_invalid_limit_uses_default(self):
        """Некорректный limit — ветка except в get_popular_items."""
        RecommendationUser.objects.create(username="pop_u")
        Item.objects.create(name="Pop", item_type="movie")
        rows = get_popular_items(limit="not-int")
        self.assertIsInstance(rows, list)


class PopularViewInvalidLimitTestCase(TestCase):
    """Ветка except в PopularItemsView при неверном query limit."""

    def test_popular_invalid_limit_defaults_in_view(self):
        self.client = APIClient()
        response = self.client.get(reverse("recommendations:popular"), {"limit": "bad"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
