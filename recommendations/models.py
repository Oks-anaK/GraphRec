"""ORM-модели графа предпочтений."""
from django.db import models


class RecommendationUser(models.Model):
    """Пользователь — узел графа предпочтений."""

    username = models.CharField(
        max_length=150,
        unique=True,
        verbose_name="Имя пользователя",
        help_text="Уникальный логин; узел u_{id}.",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата регистрации",
        help_text="Автодата создания.",
    )

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

    def __str__(self):
        return self.username


class Item(models.Model):
    """Узел элемента в графе."""

    name = models.CharField(
        max_length=255,
        verbose_name="Название",
        help_text="Название для отображения.",
    )
    item_type = models.CharField(
        max_length=50,
        verbose_name="Тип элемента",
        help_text="Категория (movie, book); узел i_{id}.",
    )

    class Meta:
        verbose_name = "Элемент"
        verbose_name_plural = "Элементы"

    def __str__(self):
        return self.name


class Interaction(models.Model):
    """Ребро user–item в графе."""

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
        help_text="Пользователь (узел u).",
    )
    item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        related_name="interactions",
        verbose_name="Элемент",
        help_text="Элемент (узел i).",
    )
    interaction_type = models.CharField(
        max_length=20,
        choices=INTERACTION_TYPE_CHOICES,
        verbose_name="Тип взаимодействия",
        help_text="Семантика и вес ребра.",
    )
    rating = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Оценка",
        help_text="Для rated — оценка 1–5; иначе опционально.",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Создано",
        help_text="Время записи.",
    )

    class Meta:
        unique_together = ["user", "item"]
        verbose_name = "Взаимодействие"
        verbose_name_plural = "Взаимодействия"

    def __str__(self):
        return f"{self.user} — {self.item} ({self.interaction_type})"
