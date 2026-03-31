"""Загрузка тестовых пользователей, элементов каталога и взаимодействий."""

from django.core.management.base import BaseCommand

from recommendations.models import Interaction, Item, RecommendationUser
from recommendations.services.recommendation_service import invalidate_recommendations_cache

USERS = [
    "Анна Смирнова",
    "Борис Волков",
    "Виктор Лебедев",
    "Галина Новикова",
    "Дмитрий Орлов",
    "Елена Павлова",
    "Олег Соколов",
    "Светлана Фёдорова",
]

MOVIES = [
    "Аватар",
    "Мстители: Финал",
    "Титаник",
    "Матрица",
    "Интерстеллар",
    "Властелин колец: Возвращение короля",
    "Гарри Поттер и философский камень",
    "Криминальное чтиво",
]

BOOKS = [
    "Мастер и Маргарита",
    "Преступление и наказание",
    "Война и мир",
    "1984",
    "Гарри Поттер и Дары Смерти",
    "Игра престолов",
    "Тихий Дон",
    "Евгений Онегин",
]


def _ensure_users():
    created = 0
    users = []
    for name in USERS:
        obj, was_created = RecommendationUser.objects.get_or_create(username=name)
        if was_created:
            created += 1
        users.append(obj)
    return users, created


def _ensure_items():
    created = 0
    items = []
    for title in MOVIES:
        obj, was_created = Item.objects.get_or_create(
            name=title,
            item_type="movie",
            defaults={},
        )
        if was_created:
            created += 1
        items.append(obj)
    for title in BOOKS:
        obj, was_created = Item.objects.get_or_create(
            name=title,
            item_type="book",
            defaults={},
        )
        if was_created:
            created += 1
        items.append(obj)
    return items, created


def _item_map():
    out = {}
    for it in Item.objects.all():
        out[(it.name, it.item_type)] = it
    return out


def _seed_interactions(users, items_by_key):
    n_movies = len(MOVIES)
    n_books = len(BOOKS)
    created = 0
    updated = 0

    def add(u, name, itype, inter_type, rating=None):
        nonlocal created, updated
        item = items_by_key[(name, itype)]
        obj, was_created = Interaction.objects.update_or_create(
            user=u,
            item=item,
            defaults={
                "interaction_type": inter_type,
                "rating": rating,
            },
        )
        if was_created:
            created += 1
        else:
            updated += 1

    for i, u in enumerate(users):
        add(u, "Аватар", "movie", Interaction.VIEWED)
        add(u, "Матрица", "movie", Interaction.LIKED)
        add(u, "Мастер и Маргарита", "book", Interaction.VIEWED)
        add(u, MOVIES[i % n_movies], "movie", Interaction.VIEWED)
        add(u, BOOKS[(i + 3) % n_books], "book", Interaction.RATED, rating=4.0 + (i % 2))
        if i % 2 == 0:
            add(u, MOVIES[(i + 2) % n_movies], "movie", Interaction.PURCHASED)

    return created, updated


class Command(BaseCommand):
    help = "Загружает пользователей, элементы каталога и взаимодействия."

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-interactions",
            action="store_true",
            help="Только пользователи и элементы каталога.",
        )

    def handle(self, *args, **options):
        users, uc = _ensure_users()
        _, ic = _ensure_items()
        items_by_key = _item_map()

        self.stdout.write(
            self.style.SUCCESS(
                f"Пользователи: +{uc} новых, всего {len(users)}. "
                f"Элементы каталога: +{ic} новых, всего {len(items_by_key)}."
            )
        )

        if options["no_interactions"]:
            self.stdout.write(self.style.WARNING("Взаимодействия не созданы (--no-interactions)."))
            return

        int_c, int_u = _seed_interactions(users, items_by_key)
        self.stdout.write(
            self.style.SUCCESS(
                f"Взаимодействия: создано {int_c}, обновлено {int_u}."
            )
        )

        for u in users:
            invalidate_recommendations_cache(u.pk)
        self.stdout.write(self.style.NOTICE("Кэш рекомендаций сброшен."))
