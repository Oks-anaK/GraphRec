"""Рекомендации на основе алгоритма PageRank."""
import networkx as nx


def pagerank_recommendations(G, user_id, top_n=10):
    """
    Возвращает топ-N элементов для пользователя по важности (PageRank).

    Учитывает веса рёбер (оценки, типы взаимодействий).
    Исключает элементы, с которыми пользователь уже взаимодействовал.
    """
    # Преобразуем user_id в ID узла графа
    user_node = f"u_{user_id}"
    if not G.has_node(user_node):
        return []

    # Запускаем PageRank с учётом весов рёбер
    pr = nx.pagerank(G, weight="weight")
    # Собираем элементы, с которыми пользователь уже взаимодействовал
    user_items = set(G.neighbors(user_node))
    # Формируем словарь: элемент -> оценка (только элементы, новые для пользователя)
    item_scores = {
        node: pr[node]
        for node in G.nodes()
        if G.nodes[node].get("node_type") == "item" and node not in user_items
    }
    # Сортируем по убыванию оценки и возвращаем топ-N
    return sorted(item_scores.items(), key=lambda x: x[1], reverse=True)[:top_n]
