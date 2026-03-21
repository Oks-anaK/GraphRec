"""k-NN — поиск похожих пользователей и рекомендации на их основе."""
import numpy as np
from sklearn.neighbors import NearestNeighbors

from recommendations.services.collaborative import _build_user_item_matrix


def knn_recommendations(user_id, k=5, top_n=10):
    """
    Рекомендации на основе k ближайших соседей.
    Находит пользователей с похожими интересами и рекомендует элементы по их оценкам.
    """
    # Строим матрицу пользователь–элемент из БД (переиспользуем из collaborative)
    matrix, user_id_to_idx, item_idx_to_id = _build_user_item_matrix()
    if matrix is None or user_id not in user_id_to_idx:
        return []

    user_idx = user_id_to_idx[user_id]
    # Обучаем k-NN по косинусной метрике
    nn = NearestNeighbors(n_neighbors=k + 1, metric="cosine")
    nn.fit(matrix)
    # Находим k ближайших соседей (k+1, т.к. первый — сам пользователь)
    distances, indices = nn.kneighbors([matrix[user_idx]])
    similar_indices = indices[0][1:]
    similar_distances = distances[0][1:]
    # Элементы, с которыми пользователь уже взаимодействовал
    user_items = set(np.where(matrix[user_idx] > 0)[0])
    # Взвешенная сумма оценок соседей (расстояние -> сходство: 1 - distance)
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
    return [
        (f"i_{item_idx_to_id[i]}", float(scores[i]))
        for i in top_indices
        if scores[i] > 0
    ]
