"""Формы веб-интерфейса."""

from django import forms

from recommendations.models import Interaction, Item, RecommendationUser


class PreferenceForm(forms.Form):
    """Добавление или обновление предпочтения (ребра графа)."""

    user = forms.ModelChoiceField(
        queryset=RecommendationUser.objects.all(),
        label="Пользователь",
        empty_label="— выберите —",
    )
    item = forms.ModelChoiceField(
        queryset=Item.objects.all(),
        label="Элемент",
        empty_label="— выберите —",
    )
    interaction_type = forms.ChoiceField(
        choices=Interaction.INTERACTION_TYPE_CHOICES,
        label="Тип взаимодействия",
    )
    rating = forms.FloatField(
        required=False,
        min_value=0,
        max_value=5,
        label="Оценка (для типа «Оценка»)",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for _name, field in self.fields.items():
            w = field.widget
            if isinstance(w, forms.Select):
                w.attrs.setdefault("class", "form-select")
            else:
                w.attrs.setdefault("class", "form-control")

    def clean(self):
        cleaned = super().clean()
        if not cleaned:
            return cleaned
        if cleaned.get("interaction_type") == Interaction.RATED:
            if cleaned.get("rating") is None:
                self.add_error(
                    "rating",
                    "Для типа «Оценка» укажите значение от 0 до 5.",
                )
        return cleaned
