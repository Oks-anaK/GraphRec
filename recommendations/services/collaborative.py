"""Коллаборативная фильтрация (косинусное сходство пользователей)."""
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from recommendations.graph.builder import _get_edge_weight
from recommendations.models import Interaction, Item, RecommendationUser


def _build_user_item_matrix():
    """Матрица user×item из БД."""
    interactions = Interaction.objects.select_related("user", "item")
    user_ids = list(
        RecommendationUser.objects.values_list("pk", flat=True).order_by("pk")
    )
    item_ids = list(Item.objects.values_list("pk", flat=True).order_by("pk"))

    if not user_ids or not item_ids:
        return None, {}, {}

    user_id_to_idx = {uid: i for i, uid in enumerate(user_ids)}
    item_id_to_idx = {iid: i for i, iid in enumerate(item_ids)}

    matrix = np.zeros((len(user_ids), len(item_ids)))

    for interaction in interactions:
        u_idx = user_id_to_idx.get(interaction.user_id)
        i_idx = item_id_to_idx.get(interaction.item_id)
        if u_idx is not None and i_idx is not None:
            matrix[u_idx, i_idx] = _get_edge_weight(interaction)

    item_idx_to_id = {i: iid for i, iid in enumerate(item_ids)}
    return matrix, user_id_to_idx, item_idx_to_id


def collaborative_filtering(user_id, k=5, top_n=10):
    """Топ-N по оценкам k похожих пользователей."""
    # Строим матрицу пользователь–элемент из БД
    matrix, user_id_to_idx, item_idx_to_id = _build_user_item_matrix()
    if matrix is None or user_id not in user_id_to_idx:
        return []
    if matrix.shape[0] <= k:
        return []

    user_idx = user_id_to_idx[user_id]
    # Вычисляем сходство пользователей
    user_similarity = cosine_similarity(matrix)
    # Находим k ближайших соседей (исключая самого пользователя)
    similar_indices = np.argsort(user_similarity[user_idx])[::-1][1 : k + 1]
    # Элементы, с которыми пользователь уже взаимодействовал
    user_items = set(np.where(matrix[user_idx] > 0)[0])
    # Взвешенная сумма оценок соседей для неоценённых элементов
    scores = np.zeros(matrix.shape[1])
    for neighbor_idx in similar_indices:
        sim = user_similarity[user_idx, neighbor_idx]
        if sim <= 0:
            continue
        scores += sim * matrix[neighbor_idx]
    # Исключаем уже просмотренные из рекомендаций
    scores[list(user_items)] = -np.inf
    # Сортируем по убыванию и возвращаем топ-N
    top_indices = np.argsort(scores)[::-1][:top_n]
    return [
        (f"i_{item_idx_to_id[i]}", float(scores[i]))
        for i in top_indices
        if scores[i] > 0
    ]
