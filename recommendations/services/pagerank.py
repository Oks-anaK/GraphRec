"""PageRank по графу пользователь–элемент.

Идея: случайный «блуждающий» по графу чаще возвращается к «важным» узлам.
Веса рёбер (weight) передаются в PageRank влияние рёбер (больше вес — сильнее связь).
Для пользователя берём элементы с высоким PageRank среди тех, с которыми он
ещё не связан (не соседи в графе).
"""

import networkx as nx


def pagerank_recommendations(G, user_id, top_n=10):
    """Топ-N элементов по глобальному PageRank; уже связанные с пользователем исключаются."""
    # Узлы графа — строки вида u_<pk> и i_<pk> (см. build_graph)
    user_node = f"u_{user_id}"
    if not G.has_node(user_node):
        return []

    # Распределение важности по всем узлам; weight=вес ребра из ORM
    pr = nx.pagerank(G, weight="weight")
    # Соседи пользователя в двудольном графе — это элементы, с которыми уже есть взаимодействие
    user_items = set(G.neighbors(user_node))
    # Оставляем только узлы-элементы, до которых пользователь «ещё не доходил» по ребру
    item_scores = {
        node: pr[node] for node in G.nodes() if G.nodes[node].get("node_type") == "item" and node not in user_items
    }
    # Сортируем по убыванию оценки и возвращаем топ-N
    return sorted(item_scores.items(), key=lambda x: x[1], reverse=True)[:top_n]
