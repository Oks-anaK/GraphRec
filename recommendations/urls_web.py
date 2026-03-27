"""Маршруты веб-интерфейса (HTML, Bootstrap)."""

from django.urls import path

from recommendations import web_views

app_name = "web"

urlpatterns = [
    path("", web_views.home, name="home"),
    path("preferences/", web_views.preferences_page, name="preferences"),
    path("recommendations/", web_views.recommendations_page, name="recommendations"),
    path("statistics/", web_views.statistics_page, name="statistics"),
]
