"""Сервис рекомендаций: выбор алгоритма, гибрид, кэш Redis.

Фасад для API: один вызов get_recommendations(user_id, algorithm, limit).
Гибрид нормализует шкалы трёх алгоритмов (min–max) и смешивает с весами 40% CF,
30% PageRank, 30% k-NN — чтобы сравнивать несовместимые по масштабу числа.
"""

from django.conf import settings
from django.core.cache import cache

from recommendations.graph import build_graph
from recommendations.services.collaborative import collaborative_filtering
from recommendations.services.knn import knn_recommendations
from recommendations.services.pagerank import pagerank_recommendations


def _normalize_scores(results):
    """Минимакс: приводит второй компонент пар (узел, score) к диапазону [0, 1]."""
    if not results:
        return {}
    scores = [r[1] for r in results]
    min_s, max_s = min(scores), max(scores)
    if max_s == min_s:
        return {r[0]: 1.0 for r in results}
    return {item_node: (score - min_s) / (max_s - min_s) for item_node, score in results}


def _combine_hybrid_scores(cf_norm, pr_norm, knn_norm):
    """Взвешенная сумма нормализованных оценок: 40% CF, 30% PageRank, 30% k-NN."""
    all_items = set(cf_norm) | set(pr_norm) | set(knn_norm)
    combined = {}
    for item in all_items:
        combined[item] = 0.4 * cf_norm.get(item, 0) + 0.3 * pr_norm.get(item, 0) + 0.3 * knn_norm.get(item, 0)
    return sorted(combined.items(), key=lambda x: x[1], reverse=True)


def hybrid_recommendations(user_id, top_n=10):
    """
    Гибридные рекомендации: объединение PageRank (30%), CF (40%), k-NN (30%).
    Оценки каждого алгоритма нормализуются перед взвешенным суммированием.
    """
    # Берём с запасом кандидатов, затем режем до top_n после смешивания
    n = max(top_n * 3, 50)

    cf = collaborative_filtering(user_id, k=5, top_n=n)
    knn = knn_recommendations(user_id, k=5, top_n=n)
    G = build_graph()
    pr = pagerank_recommendations(G, user_id, top_n=n)

    cf_norm = _normalize_scores(cf)
    knn_norm = _normalize_scores(knn)
    pr_norm = _normalize_scores(pr)

    combined_sorted = _combine_hybrid_scores(cf_norm, pr_norm, knn_norm)
    return combined_sorted[:top_n]


def get_recommendations(user_id, algorithm="hybrid", limit=10):
    """Рекомендации по algorithm; кэш Redis. Возврат: список пар (узел, score)."""
    cache_key = f"recommendations:{user_id}:{algorithm}:{limit}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    if algorithm == "pagerank":
        G = build_graph()
        result = pagerank_recommendations(G, user_id, top_n=limit)
    elif algorithm == "collaborative":
        result = collaborative_filtering(user_id, k=5, top_n=limit)
    elif algorithm == "knn":
        result = knn_recommendations(user_id, k=5, top_n=limit)
    elif algorithm == "hybrid":
        result = hybrid_recommendations(user_id, top_n=limit)
    else:
        result = hybrid_recommendations(user_id, top_n=limit)

    timeout = getattr(settings, "RECOMMENDATIONS_CACHE_TIMEOUT", 3600)
    cache.set(cache_key, result, timeout=timeout)
    return result


def invalidate_recommendations_cache(user_id):
    """Сброс кэша рекомендаций пользователя (django-redis: delete_pattern)."""
    pattern = f"recommendations:{user_id}:*"
    if hasattr(cache, "delete_pattern"):
        cache.delete_pattern(pattern)
