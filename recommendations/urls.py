"""Маршруты API приложения recommendations."""

from django.urls import path

from recommendations.views import (
    DistributionStatisticsView,
    ItemListView,
    PopularItemsView,
    RecommendationView,
    StatisticsView,
    UserPreferencesView,
    add_preference,
    api_root,
)

app_name = "recommendations"

urlpatterns = [
    path("", api_root, name="api_root"),
    path("preferences/", add_preference, name="add_preference"),
    path(
        "recommendations/<int:user_id>/",
        RecommendationView.as_view(),
        name="recommendations",
    ),
    path("items/", ItemListView.as_view(), name="items"),
    path(
        "users/<int:user_id>/preferences/",
        UserPreferencesView.as_view(),
        name="user_preferences",
    ),
    # Сначала подмаршруты statistics/*, затем statistics/
    path(
        "statistics/distribution/",
        DistributionStatisticsView.as_view(),
        name="statistics_distribution",
    ),
    path("statistics/popular/", PopularItemsView.as_view(), name="popular"),
    path("statistics/", StatisticsView.as_view(), name="statistics"),
]
