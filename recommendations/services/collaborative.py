"""Коллаборативная фильтрация (косинусное сходство пользователей).

Идея: найти пользователей с похожими предпочтениями (строки матрицы «оценки по
всем элементам» похожи по направлению), затем усилить элементы, которые понравились
соседям, но ещё не отмечены у текущего пользователя.
"""

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from recommendations.graph.builder import _get_edge_weight
from recommendations.models import Interaction, Item, RecommendationUser


def _build_user_item_matrix():
    """Строит разреженную матрицу user×item: строка = пользователь, столбец = элемент."""
    # Один запрос с JOIN к БД — без N+1 запросов при обходе взаимодействий
    interactions = Interaction.objects.select_related("user", "item")
    user_ids = list(RecommendationUser.objects.values_list("pk", flat=True).order_by("pk"))
    item_ids = list(Item.objects.values_list("pk", flat=True).order_by("pk"))

    if not user_ids or not item_ids:
        return None, {}, {}

    # Стабильный порядок строк/столбцов → фиксированные индексы в numpy
    user_id_to_idx = {uid: i for i, uid in enumerate(user_ids)}
    item_id_to_idx = {iid: i for i, iid in enumerate(item_ids)}

    matrix = np.zeros((len(user_ids), len(item_ids)))

    for interaction in interactions:
        u_idx = user_id_to_idx.get(interaction.user_id)
        i_idx = item_id_to_idx.get(interaction.item_id)
        if u_idx is not None and i_idx is not None:
            # Тот же вес, что и на ребре графа (просмотр, оценка и т.д.)
            matrix[u_idx, i_idx] = _get_edge_weight(interaction)

    # Обратное отображение: индекс столбца → pk элемента (для ответа API i_<id>)
    item_idx_to_id = {i: iid for i, iid in enumerate(item_ids)}
    return matrix, user_id_to_idx, item_idx_to_id


def collaborative_filtering(user_id, k=5, top_n=10):
    """Топ-N элементов по вкладу k ближайших по косинусу пользователей."""
    matrix, user_id_to_idx, item_idx_to_id = _build_user_item_matrix()
    if matrix is None or user_id not in user_id_to_idx:
        return []
    # Нужно k «чужих» пользователей; если в базе их не больше k — соседей не хватает
    if matrix.shape[0] <= k:
        return []

    user_idx = user_id_to_idx[user_id]
    # Создаем матрицу N×N: сходство каждой пары пользователей (строки как векторы)
    user_similarity = cosine_similarity(matrix)
    # Сортируем по убыванию сходства; [0] — сам пользователь, берём [1:k+1]
    # Cходство текущего пользователя с каждым из N пользователей — user_similarity[user_idx]
    similar_indices = np.argsort(user_similarity[user_idx])[::-1][1 : k + 1]
    # Столбцы, где у текущего пользователя уже есть взаимодействие — не рекомендуем
    user_items = set(np.where(matrix[user_idx] > 0)[0])
    # matrix.shape — размеры матрицы (число_пользователей, число_элементов)
    scores = np.zeros(matrix.shape[1])
    # Для каждого элемента — сумма (сходство × профиль соседа) по выбранным k
    for neighbor_idx in similar_indices:
        sim = user_similarity[user_idx, neighbor_idx]
        if sim <= 0:
            continue
        scores += sim * matrix[neighbor_idx]
    # Исключаем уже просмотренные из рекомендаций
    scores[list(user_items)] = -np.inf
    # Сортируем по убыванию и возвращаем топ-N
    top_indices = np.argsort(scores)[::-1][:top_n]
    return [(f"i_{item_idx_to_id[i]}", float(scores[i])) for i in top_indices if scores[i] > 0]
