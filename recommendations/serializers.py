"""Сериализаторы DRF."""

from rest_framework import serializers

from recommendations.models import Interaction, Item, RecommendationUser


class PreferenceSerializer(serializers.Serializer):
    """Тело POST /api/preferences/."""

    user_id = serializers.IntegerField()
    item_id = serializers.IntegerField()
    interaction_type = serializers.ChoiceField(
        choices=[Interaction.VIEWED, Interaction.RATED, Interaction.LIKED, Interaction.PURCHASED]
    )
    rating = serializers.FloatField(required=False, allow_null=True, min_value=0, max_value=5)

    def validate_user_id(self, value):
        if not RecommendationUser.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Пользователь не найден.")
        return value

    def validate_item_id(self, value):
        if not Item.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Элемент не найден.")
        return value

    def validate(self, attrs):
        if attrs["interaction_type"] == Interaction.RATED and attrs.get("rating") is None:
            raise serializers.ValidationError({"rating": "Для типа 'rated' необходимо указать оценку."})
        return attrs

    def create(self, validated_data):
        user = RecommendationUser.objects.get(pk=validated_data["user_id"])
        item = Item.objects.get(pk=validated_data["item_id"])
        interaction, _ = Interaction.objects.update_or_create(
            user=user,
            item=item,
            defaults={
                "interaction_type": validated_data["interaction_type"],
                "rating": validated_data.get("rating"),
            },
        )
        return interaction

    def to_representation(self, instance):
        if instance:
            return {
                "id": instance.pk,
                "user_id": instance.user_id,
                "item_id": instance.item_id,
                "interaction_type": instance.interaction_type,
                "rating": instance.rating,
            }
        return super().to_representation(instance)


class ItemSerializer(serializers.ModelSerializer):
    """Сериализатор для элемента (Item)."""

    class Meta:
        model = Item
        fields = ["id", "name", "item_type"]


class InteractionSerializer(serializers.ModelSerializer):
    """Модель Interaction для списка предпочтений."""

    item_name = serializers.CharField(source="item.name", read_only=True)
    item_type = serializers.CharField(source="item.item_type", read_only=True)

    class Meta:
        model = Interaction
        fields = ["id", "item", "item_name", "item_type", "interaction_type", "rating", "created_at"]
