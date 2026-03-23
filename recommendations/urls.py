"""URL-маршруты API рекомендаций."""
from django.urls import path

from recommendations.views import (
    ItemListView,
    PopularItemsView,
    RecommendationView,
    StatisticsView,
    UserPreferencesView,
    add_preference,
)

urlpatterns = [
    path("preferences/", add_preference, name="add_preference"),
    path(
        "recommendations/<int:user_id>/",
        RecommendationView.as_view(),
        name="recommendations",
    ),
    path("items/", ItemListView.as_view(), name="items"),
    path("users/<int:user_id>/preferences/", UserPreferencesView.as_view(), name="user_preferences"),
    path("statistics/", StatisticsView.as_view(), name="statistics"),
    path("statistics/popular/", PopularItemsView.as_view(), name="popular"),
]
