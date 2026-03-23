"""Гибридный сервис рекомендаций: объединяет PageRank, CF и k-NN."""
from recommendations.graph import build_graph
from recommendations.services.collaborative import collaborative_filtering
from recommendations.services.knn import knn_recommendations
from recommendations.services.pagerank import pagerank_recommendations


def _normalize_scores(results):
    """
    Минимаксная нормализация оценок в диапазон 0–1.
    Используется для корректного объединения результатов алгоритмов с разными шкалами.
    """
    if not results:
        return {}
    scores = [r[1] for r in results]
    min_s, max_s = min(scores), max(scores)
    if max_s == min_s:
        return {r[0]: 1.0 for r in results}
    return {
        item_node: (score - min_s) / (max_s - min_s)
        for item_node, score in results
    }


def hybrid_recommendations(user_id, top_n=10):
    """
    Гибридные рекомендации: объединение PageRank (30%), CF (40%), k-NN (30%).
    Оценки каждого алгоритма нормализуются перед взвешенным суммированием.
    """
    n = max(top_n * 3, 50)

    cf = collaborative_filtering(user_id, k=5, top_n=n)
    knn = knn_recommendations(user_id, k=5, top_n=n)
    G = build_graph()
    pr = pagerank_recommendations(G, user_id, top_n=n)

    cf_norm = _normalize_scores(cf)
    knn_norm = _normalize_scores(knn)
    pr_norm = _normalize_scores(pr)

    all_items = set(cf_norm) | set(knn_norm) | set(pr_norm)

    combined = {}
    for item in all_items:
        combined[item] = (
            0.4 * cf_norm.get(item, 0)
            + 0.3 * pr_norm.get(item, 0)
            + 0.3 * knn_norm.get(item, 0)
        )

    return sorted(
        combined.items(),
        key=lambda x: x[1],
        reverse=True,
    )[:top_n]


def get_recommendations(user_id, algorithm="hybrid", limit=10):
    """
    Единая точка входа для получения рекомендаций.

    Args:
        user_id: ID пользователя.
        algorithm: 'pagerank' | 'collaborative' | 'knn' | 'hybrid'.
        limit: количество рекомендаций.

    Returns:
        [(item_node, score), ...], например [("i_5", 0.82), ("i_8", 0.61)].
    """
    if algorithm == "pagerank":
        G = build_graph()
        return pagerank_recommendations(G, user_id, top_n=limit)
    if algorithm == "collaborative":
        return collaborative_filtering(user_id, k=5, top_n=limit)
    if algorithm == "knn":
        return knn_recommendations(user_id, k=5, top_n=limit)
    if algorithm == "hybrid":
        return hybrid_recommendations(user_id, top_n=limit)

    return hybrid_recommendations(user_id, top_n=limit)
