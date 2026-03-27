"""Модели системы рекомендаций на графах (ORM)."""

from django.db import models


class RecommendationUser(models.Model):
    """Пользователь — узел графа предпочтений."""

    username = models.CharField(
        max_length=150,
        unique=True,
        verbose_name="Имя пользователя",
        help_text="Уникальный логин; в графе узел вида u_{id}.",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата регистрации",
        help_text="Автоматически при создании записи.",
    )

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

    def __str__(self):
        return self.username


class Item(models.Model):
    """Элемент каталога (фильм, книга и т.п.) — узел графа."""

    name = models.CharField(
        max_length=255,
        verbose_name="Название",
        help_text="Отображаемое имя элемента (фильм, книга и т.п.).",
    )
    item_type = models.CharField(
        max_length=50,
        verbose_name="Тип элемента",
        help_text="Категория: movie, book и т.д.; в графе узел вида i_{id}.",
    )

    class Meta:
        verbose_name = "Элемент"
        verbose_name_plural = "Элементы"

    def __str__(self):
        return self.name


class Interaction(models.Model):
    """Взаимодействие пользователя с элементом — ребро графа."""

    VIEWED = "viewed"
    RATED = "rated"
    LIKED = "liked"
    PURCHASED = "purchased"

    INTERACTION_TYPE_CHOICES = [
        (VIEWED, "Просмотр"),
        (RATED, "Оценка"),
        (LIKED, "Лайк"),
        (PURCHASED, "Покупка"),
    ]

    user = models.ForeignKey(
        RecommendationUser,
        on_delete=models.CASCADE,
        related_name="interactions",
        verbose_name="Пользователь",
        help_text="Узел пользователя в двудольном графе.",
    )
    item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        related_name="interactions",
        verbose_name="Элемент",
        help_text="Узел элемента в двудольном графе.",
    )
    interaction_type = models.CharField(
        max_length=20,
        choices=INTERACTION_TYPE_CHOICES,
        verbose_name="Тип взаимодействия",
        help_text="Определяет семантику ребра и вес при построении графа.",
    )
    rating = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Оценка",
        help_text=("Для типа «Оценка»: значение по шкале (часто 1–5); " "для остальных типов не обязательна."),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Создано",
        help_text="Время фиксации взаимодействия.",
    )

    class Meta:
        unique_together = ["user", "item"]
        verbose_name = "Взаимодействие"
        verbose_name_plural = "Взаимодействия"

    def __str__(self):
        return f"{self.user} — {self.item} ({self.interaction_type})"
