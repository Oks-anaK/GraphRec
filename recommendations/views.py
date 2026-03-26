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
        users_count = RecommendationUser.objects.count()
        items_count = Item.objects.count()
        interactions_count = Interaction.objects.count()
        return Response({
            "users_count": users_count,
            "items_count": items_count,
            "interactions_count": interactions_count,
        })


class DistributionStatisticsView(APIView):
    """Распределение по типам и оценкам."""
    def get(self, request):
        from collections import Counter
        from django.db.models import Count
        type_map = dict(Interaction.INTERACTION_TYPE_CHOICES)
        by_type_qs = (
            Interaction.objects.values("interaction_type")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        interaction_types = [
            {
                "type": row["interaction_type"],
                "label": type_map.get(row["interaction_type"], row["interaction_type"]),
                "count": row["count"],
            }
            for row in by_type_qs
        ]
        rated = Interaction.objects.filter(
            interaction_type=Interaction.RATED,
            rating__isnull=False,
        ).values_list("rating", flat=True)
        rounded = [round(float(r) * 2) / 2 for r in rated]
        rating_counter = Counter(rounded)
        rating_labels = sorted(rating_counter.keys())
        rating_distribution = [
            {"label": str(label), "count": rating_counter[label]}
            for label in rating_labels
        ]
        return Response({
            "interaction_types": interaction_types,
            "rating_distribution": rating_distribution,
        })


class PopularItemsView(APIView):
    """Популярные элементы по числу взаимодействий."""

    def get(self, request):
        try:
            limit = min(int(request.query_params.get("limit", 10) or 10), 100)
        except (TypeError, ValueError):
            limit = 10
        from django.db.models import Count

        popular = (
            Item.objects.annotate(interaction_count=Count("interactions"))
            .order_by("-interaction_count")[:limit]
        )
        data = [
            {
                "id": item.id,
                "name": item.name,
                "item_type": item.item_type,
                "interaction_count": item.interaction_count,
            }
            for item in popular
        ]
        return Response(data)
