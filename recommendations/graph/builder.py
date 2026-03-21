"""Построение графа предпочтений из данных БД."""
import networkx as nx

from recommendations.models import Interaction, Item, RecommendationUser


def _get_edge_weight(interaction):
    """Вес ребра по типу взаимодействия."""
    weights = {
        Interaction.VIEWED: 1.0, # 1.0 по умолчанию
        Interaction.LIKED: 1.0,
        Interaction.PURCHASED: 2.0, # Покупка важнее просмотра и лайка
    }
    # Для оценки высчитываем значение веса (по шкале 0–1)
    if interaction.interaction_type == Interaction.RATED and interaction.rating:
        return interaction.rating / 5.0
    return weights.get(interaction.interaction_type, 1.0)


def build_graph():
    """Строит двудольный граф из данных PostgreSQL."""
    # Создаем пустой граф
    G = nx.Graph()

    users = RecommendationUser.objects.all()
    items = Item.objects.all()

    for user in users:
        # Добавляем узлы пользователей
        G.add_node(f"u_{user.pk}", node_type="user", pk=user.pk)

    for item in items:
        # Добавляем узлы элементов
        G.add_node(f"i_{item.pk}", node_type="item", pk=item.pk)

    for interaction in Interaction.objects.select_related("user", "item"):
        # Добавляем рёбра между пользователем и элементом с весом по типу взаимодействия
        user_node = f"u_{interaction.user_id}"
        item_node = f"i_{interaction.item_id}"
        weight = _get_edge_weight(interaction)
        G.add_edge(
            user_node,
            item_node,
            weight=weight,
            interaction_type=interaction.interaction_type,
        )

    return G
