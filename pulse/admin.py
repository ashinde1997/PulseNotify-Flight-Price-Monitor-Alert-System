from django.contrib import admin
from .models import UserProfile, PriceAlert, NotificationLog


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'role', 'created_at')
    list_filter = ('role', 'created_at')
    search_fields = ('user__username', 'user__email')


@admin.register(PriceAlert)
class PriceAlertAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'origin', 'destination', 'threshold_price', 'status', 'created_at')
    list_filter = ('status', 'origin', 'destination', 'created_at')
    search_fields = ('user__username', 'origin', 'destination')


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'alert', 'triggered_price', 'message', 'notified_at')
    list_filter = ('notified_at',)
    search_fields = ('alert__user__username', 'message')
