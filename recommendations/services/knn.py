"""k-NN по матрице user×item (cosine).

Идея близка к collaborative: те же строки пользователей, но соседей ищет
алгоритм sklearn NearestNeighbors (косинусная метрика), а не полная матрица
cosine_similarity. Вес соседа: 1 − distance (для cosine distance в [0, 1]).
"""

import numpy as np
from sklearn.neighbors import NearestNeighbors

from recommendations.services.collaborative import _build_user_item_matrix


def knn_recommendations(user_id, k=5, top_n=10):
    """Топ-N элементов по вкладу k ближайших по косинусному расстоянию пользователей."""
    # Та же матрица, что и в collaborative — единый источник правды из БД
    matrix, user_id_to_idx, item_idx_to_id = _build_user_item_matrix()
    if matrix is None or user_id not in user_id_to_idx:
        return []
    if matrix.shape[0] <= k:
        return []

    user_idx = user_id_to_idx[user_id]
    # metric="cosine": расстояние в [0, 2]; kneighbors возвращает k+1 точек, первая — сам пользователь
    nn = NearestNeighbors(n_neighbors=k + 1, metric="cosine")
    nn.fit(matrix)
    distances, indices = nn.kneighbors([matrix[user_idx]])
    # Отбрасываем себя с индексом 0
    similar_indices = indices[0][1:]
    similar_distances = distances[0][1:]
    # Уже просмотренные/оценённые элементы — не предлагаем в топе
    user_items = set(np.where(matrix[user_idx] > 0)[0])
    # Вес: чем меньше расстояние до соседа, тем больше сходство (1 − dist)
    scores = np.zeros(matrix.shape[1])
    for neighbor_idx, dist in zip(similar_indices, similar_distances):
        sim = 1 - dist if dist <= 1 else 0
        if sim <= 0:
            continue
        scores += sim * matrix[neighbor_idx]
    # Исключаем уже просмотренные
    scores[list(user_items)] = -np.inf
    # Сортируем и возвращаем топ-N
    top_indices = np.argsort(scores)[::-1][:top_n]
    return [(f"i_{item_idx_to_id[i]}", float(scores[i])) for i in top_indices if scores[i] > 0]
