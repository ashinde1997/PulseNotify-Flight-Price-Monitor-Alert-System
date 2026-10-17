from django.urls import path
from .views import (
    RegisterView,
    LoginView,
    AlertListCreateView,
    AlertDeleteView,
    get_flight_price,
    AdminSummaryView,
    NotificationLogListView,
)

urlpatterns = [
    # Auth Endpoints
    path('auth/register/', RegisterView.as_view(), name='auth-register'),
    path('auth/login/', LoginView.as_view(), name='auth-login'),

    # Price Alert Endpoints
    path('alerts/', AlertListCreateView.as_view(), name='alert-list-create'),
    path('alerts/<int:pk>/', AlertDeleteView.as_view(), name='alert-delete'),

    # Mock Flight Price Feed Endpoint
    path('flights/price/', get_flight_price, name='flight-price-feed'),

    # Admin Summary Endpoint
    path('admin/summary/', AdminSummaryView.as_view(), name='admin-summary'),

    # Notifications Endpoint (useful for verifying Celery triggered notifications)
    path('notifications/', NotificationLogListView.as_view(), name='notification-list'),
]
