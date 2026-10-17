import random
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .models import UserProfile, PriceAlert, NotificationLog
from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    PriceAlertSerializer,
    NotificationLogSerializer
)
from .permissions import IsAdminUser

# Simulated price ranges for domestic routes
MOCK_PRICES = {
    'DEL-BOM': (3000, 7000),   # Delhi - Mumbai
    'BLR-HYD': (1500, 4000),   # Bengaluru - Hyderabad
    'DEL-BLR': (4000, 9000),   # Delhi - Bengaluru
    'BOM-GOA': (2000, 5000),   # Mumbai - Goa
    'CCU-DEL': (3500, 7500),   # Kolkata - Delhi
    'MAA-BLR': (1800, 4200),   # Chennai - Bengaluru
    'PNQ-DEL': (3200, 6800),   # Pune - Delhi
    'AMD-BOM': (2200, 4800),   # Ahmedabad - Mumbai
    'COK-BLR': (2000, 4500),   # Kochi - Bengaluru
    'JAI-BOM': (2800, 5800),   # Jaipur - Mumbai
}


class RegisterView(APIView):
    """Handles user registration and issues initial JWT tokens."""
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.save()
        refresh = RefreshToken.for_user(user)

        # Profile gets auto-created via post_save signal
        profile, _ = UserProfile.objects.get_or_create(user=user)

        return Response({
            "username": user.username,
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "role": profile.role
        }, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """Authenticates credentials and returns fresh JWT tokens."""
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        username = serializer.validated_data['username']
        password = serializer.validated_data['password']

        user = authenticate(request, username=username, password=password)
        if user is None:
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

        refresh = RefreshToken.for_user(user)
        profile, _ = UserProfile.objects.get_or_create(user=user)

        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "username": user.username,
            "role": profile.role
        }, status=status.HTTP_200_OK)


class AlertListCreateView(generics.ListCreateAPIView):
    """List or create alerts for the authenticated user."""
    serializer_class = PriceAlertSerializer

    def get_queryset(self):
        # Users should only ever see their own alerts
        return PriceAlert.objects.filter(user=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        # Force ownership to request.user regardless of any body payload
        serializer.save(user=self.request.user, status=PriceAlert.Status.ACTIVE)


class AlertDeleteView(APIView):
    """Soft-deactivates an alert without deleting the audit history."""

    def delete(self, request, pk):
        alert = get_object_or_404(PriceAlert, id=pk)

        # Disallow deactivating someone else's alert
        if alert.user != request.user:
            return Response({"error": "Alert not found"}, status=status.HTTP_404_NOT_FOUND)

        alert.status = PriceAlert.Status.INACTIVE
        alert.save(update_fields=['status'])
        return Response({"status": "inactive"}, status=status.HTTP_200_OK)


def get_flight_price(request):
    """Mock price feed simulating airline ticket prices."""
    route = request.GET.get('route', '').strip().upper()
    price_range = MOCK_PRICES.get(route)
    if not price_range:
        return JsonResponse({'error': 'Route not found'}, status=404)

    price = random.randint(*price_range)
    return JsonResponse({'route': route, 'price': price})


class AdminSummaryView(APIView):
    """Admin dashboard summary computing aggregations at the database level."""
    permission_classes = [IsAdminUser]

    def get(self, request):
        # Aggregate alert status counts
        alert_stats = PriceAlert.objects.aggregate(
            total_alerts=Count('id'),
            active_alerts=Count('id', filter=Q(status=PriceAlert.Status.ACTIVE)),
            triggered_alerts=Count('id', filter=Q(status=PriceAlert.Status.TRIGGERED)),
        )

        notif_stats = NotificationLog.objects.aggregate(
            total_notifications=Count('id')
        )

        # Group alerts by route in SQL
        top_routes_qs = (
            PriceAlert.objects
            .values('origin', 'destination')
            .annotate(alert_count=Count('id'))
            .order_by('-alert_count')
        )

        top_routes = [
            {
                "route": f"{item['origin']}-{item['destination']}",
                "alert_count": item['alert_count']
            }
            for item in top_routes_qs
        ]

        return Response({
            "total_alerts": alert_stats['total_alerts'] or 0,
            "active_alerts": alert_stats['active_alerts'] or 0,
            "triggered_alerts": alert_stats['triggered_alerts'] or 0,
            "total_notifications": notif_stats['total_notifications'] or 0,
            "top_routes": top_routes
        }, status=status.HTTP_200_OK)


class NotificationLogListView(generics.ListAPIView):
    """Returns triggered notification logs for the user (or all if admin)."""
    serializer_class = NotificationLogSerializer

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'profile') and user.profile.role == UserProfile.Role.ADMIN:
            return NotificationLog.objects.all().order_by('-notified_at')
        return NotificationLog.objects.filter(alert__user=user).order_by('-notified_at')
