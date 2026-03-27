"""Веб-интерфейс (HTML + Bootstrap): предпочтения, рекомендации, статистика."""

from django.contrib import messages
from django.shortcuts import redirect, render

from recommendations.forms import PreferenceForm
from recommendations.models import Interaction, Item, RecommendationUser
from recommendations.services.recommendation_service import (
    get_recommendations,
    invalidate_recommendations_cache,
)
from recommendations.statistics_data import (
    get_distribution_statistics,
    get_popular_items,
    get_summary_statistics,
)


def _enrich_recommendation_rows(raw_pairs):
    """Пары (узел, score) → список словарей с человекочитаемым названием элемента."""
    pks = []
    for node, _ in raw_pairs:
        if isinstance(node, str) and node.startswith("i_"):
            try:
                pks.append(int(node[2:]))
            except ValueError:
                pass
    items = Item.objects.in_bulk(pks)
    rows = []
    for node, score in raw_pairs:
        title = node
        if isinstance(node, str) and node.startswith("i_"):
            try:
                pk = int(node[2:])
                item = items.get(pk)
                if item:
                    title = item.name
            except ValueError:
                pass
        rows.append({"node": node, "score": score, "title": title})
    return rows


def home(request):
    """Главная: навигация по разделам."""
    return render(
        request,
        "recommendations/home.html",
        {
            "users_count": RecommendationUser.objects.count(),
            "items_count": Item.objects.count(),
        },
    )


def preferences_page(request):
    """Ввод предпочтения и просмотр списка предпочтений выбранного пользователя."""
    if request.method == "POST":
        form = PreferenceForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data["user"]
            item = form.cleaned_data["item"]
            Interaction.objects.update_or_create(
                user=user,
                item=item,
                defaults={
                    "interaction_type": form.cleaned_data["interaction_type"],
                    "rating": form.cleaned_data.get("rating"),
                },
            )
            invalidate_recommendations_cache(user.pk)
            messages.success(request, "Предпочтение сохранено.")
            return redirect("web:preferences")
    else:
        form = PreferenceForm()

    view_user = None
    interactions = []
    uid = request.GET.get("user_id")
    if uid:
        try:
            view_user = RecommendationUser.objects.get(pk=int(uid))
            interactions = Interaction.objects.filter(user=view_user).select_related("item").order_by("-created_at")
        except (ValueError, RecommendationUser.DoesNotExist):
            messages.error(request, "Пользователь не найден.")

    return render(
        request,
        "recommendations/preferences.html",
        {
            "form": form,
            "view_user": view_user,
            "interactions": interactions,
        },
    )


def recommendations_page(request):
    """Параметры рекомендаций и таблица результатов."""
    algorithm = request.GET.get("algorithm", "hybrid")
    if algorithm not in ("hybrid", "pagerank", "collaborative", "knn"):
        algorithm = "hybrid"
    try:
        limit = int(request.GET.get("limit", 10))
    except (TypeError, ValueError):
        limit = 10
    limit = max(1, min(limit, 100))

    user_id = request.GET.get("user_id")
    rows = []
    selected_user = None
    selected_uid = None
    if user_id:
        try:
            uid = int(user_id)
            selected_uid = uid
            selected_user = RecommendationUser.objects.filter(pk=uid).first()
            if selected_user:
                raw = get_recommendations(uid, algorithm, limit)
                rows = _enrich_recommendation_rows(raw)
            else:
                messages.error(request, "Пользователь не найден.")
        except (ValueError, TypeError):
            messages.error(request, "Укажите корректный ID пользователя.")

    return render(
        request,
        "recommendations/recommendations.html",
        {
            "users": RecommendationUser.objects.all().order_by("username"),
            "algorithm": algorithm,
            "limit": limit,
            "selected_uid": selected_uid,
            "selected_user": selected_user,
            "rows": rows,
        },
    )


def statistics_page(request):
    """Сводная статистика и популярность элементов."""
    summary = get_summary_statistics()
    distribution = get_distribution_statistics()
    popular = get_popular_items(limit=15)
    return render(
        request,
        "recommendations/statistics.html",
        {
            "summary": summary,
            "distribution": distribution,
            "popular": popular,
        },
    )
