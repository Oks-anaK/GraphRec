from django.contrib import admin

from .models import Interaction, Item, RecommendationUser


@admin.register(RecommendationUser)
class RecommendationUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'created_at')
    search_fields = ('username',)
    list_filter = ('created_at',)


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'item_type')
    search_fields = ('name',)
    list_filter = ('item_type',)


@admin.register(Interaction)
class InteractionAdmin(admin.ModelAdmin):
    list_display = ('user', 'item', 'interaction_type', 'rating', 'created_at')
    search_fields = ('user__username', 'item__name')
    list_filter = ('interaction_type', 'created_at')
