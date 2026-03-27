"""Сводная статистика для API и веб-интерфейса."""

from collections import Counter

from django.db.models import Count

from recommendations.models import Interaction, Item, RecommendationUser


def get_summary_statistics():
    """Счётчики пользователей, элементов, взаимодействий."""
    return {
        "users_count": RecommendationUser.objects.count(),
        "items_count": Item.objects.count(),
        "interactions_count": Interaction.objects.count(),
    }


def get_distribution_statistics():
    """Распределение по типам взаимодействий и по оценкам."""
    type_map = dict(Interaction.INTERACTION_TYPE_CHOICES)
    by_type_qs = Interaction.objects.values("interaction_type").annotate(count=Count("id")).order_by("-count")
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
    rating_distribution = [{"label": str(label), "count": rating_counter[label]} for label in rating_labels]
    return {
        "interaction_types": interaction_types,
        "rating_distribution": rating_distribution,
    }


def get_popular_items(limit=10):
    """Популярные элементы по числу взаимодействий."""
    try:
        limit = min(max(int(limit), 1), 100)
    except (TypeError, ValueError):
        limit = 10
    popular = Item.objects.annotate(interaction_count=Count("interactions")).order_by("-interaction_count")[:limit]
    return [
        {
            "id": item.id,
            "name": item.name,
            "item_type": item.item_type,
            "interaction_count": item.interaction_count,
        }
        for item in popular
    ]
