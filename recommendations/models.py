"""Модели для системы рекомендаций на графах (ORM, PostgreSQL)."""
from django.db import models


class RecommendationUser(models.Model):
    """Пользователь — узел графа предпочтений."""

    username = models.CharField(max_length=150, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.username


class Item(models.Model):
    """Элемент (фильм, книга и т.д.) — узел графа."""

    name = models.CharField(max_length=255)
    item_type = models.CharField(max_length=50)

    class Meta:
        verbose_name = 'Элемент'
        verbose_name_plural = 'Элементы'

    def __str__(self):
        return self.name


class Interaction(models.Model):
    """Взаимодействие пользователя с элементом — ребро графа."""

    VIEWED = 'viewed'
    RATED = 'rated'
    LIKED = 'liked'
    PURCHASED = 'purchased'

    INTERACTION_TYPE_CHOICES = [
        (VIEWED, 'Просмотр'),
        (RATED, 'Оценка'),
        (LIKED, 'Лайк'),
        (PURCHASED, 'Покупка'),
    ]

    user = models.ForeignKey(
        RecommendationUser,
        on_delete=models.CASCADE,
        related_name='interactions',
    )
    item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        related_name='interactions',
    )
    interaction_type = models.CharField(
        max_length=20,
        choices=INTERACTION_TYPE_CHOICES,
    )
    rating = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'item']
        verbose_name = 'Взаимодействие'
        verbose_name_plural = 'Взаимодействия'

    def __str__(self):
        return f'{self.user} — {self.item} ({self.interaction_type})'
