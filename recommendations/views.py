from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.status import HTTP_201_CREATED, HTTP_400_BAD_REQUEST
from rest_framework.views import APIView

from recommendations.models import Interaction, Item, RecommendationUser
from recommendations.serializers import (
    InteractionSerializer,
    ItemSerializer,
    PreferenceSerializer,
)
from recommendations.services.recommendation_service import (
    get_recommendations,
    invalidate_recommendations_cache,
)
from recommendations.statistics_data import (
    get_distribution_statistics,
    get_popular_items,
    get_summary_statistics,
)


class RecommendationView(APIView):
    """Рекомендации для user_id."""

    def get(self, request, user_id):
        algorithm = request.query_params.get("algorithm", "hybrid")
        try:
            limit = int(request.query_params.get("limit", 10))
        except (TypeError, ValueError):
            limit = 10
        recommendations = get_recommendations(user_id, algorithm, limit)
        return Response({"recommendations": recommendations})


@api_view(["POST"])
def add_preference(request):
    """Создать или обновить взаимодействие."""
    serializer = PreferenceSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        invalidate_recommendations_cache(serializer.validated_data["user_id"])
        return Response(serializer.data, status=HTTP_201_CREATED)
    return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class ItemListView(APIView):
    """Список элементов."""

    def get(self, request):
        items = Item.objects.all()
        serializer = ItemSerializer(items, many=True)
        return Response(serializer.data)


class UserPreferencesView(APIView):
    """Предпочтения пользователя."""

    def get(self, request, user_id):
        if not RecommendationUser.objects.filter(pk=user_id).exists():
            return Response(
                {"detail": "Пользователь не найден."},
                status=404,
            )
        interactions = Interaction.objects.filter(user_id=user_id).select_related("item")
        serializer = InteractionSerializer(interactions, many=True)
        return Response(serializer.data)


class StatisticsView(APIView):
    """Сводные счётчики."""

    def get(self, request):
        return Response(get_summary_statistics())


class DistributionStatisticsView(APIView):
    """Распределение по типам и оценкам."""

    def get(self, request):
        return Response(get_distribution_statistics())


class PopularItemsView(APIView):
    """Популярные элементы по числу взаимодействий."""

    def get(self, request):
        try:
            limit = min(int(request.query_params.get("limit", 10) or 10), 100)
        except (TypeError, ValueError):
            limit = 10
        return Response(get_popular_items(limit=limit))


def api_root(request):
    """Корень REST API: оглавление эндпоинтов (для ссылки «API» в меню)."""
    rows = [
        ("GET", "items/", "Список элементов каталога"),
        ("POST", "preferences/", "Добавить или обновить предпочтение (JSON)"),
        (
            "GET",
            "recommendations/<user_id>/",
            "Рекомендации (параметры: algorithm, limit)",
        ),
        ("GET", "users/<user_id>/preferences/", "Предпочтения пользователя"),
        ("GET", "statistics/", "Сводная статистика"),
        ("GET", "statistics/popular/", "Популярные элементы"),
        ("GET", "statistics/distribution/", "Распределение по типам и оценкам"),
    ]
    base = request.build_absolute_uri("/").rstrip("/") + "/api/"
    endpoints = []
    for method, rel, description in rows:
        endpoints.append(
            {
                "method": method,
                "url": base + rel.replace("<user_id>", "1"),
                "path": rel,
                "description": description,
            }
        )
    return render(
        request,
        "recommendations/api_index.html",
        {"endpoints": endpoints},
    )
