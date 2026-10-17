from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserProfile, PriceAlert, NotificationLog


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    email = serializers.EmailField(required=False, default='')

    class Meta:
        model = User
        fields = ['username', 'password', 'email']

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("A user with that username already exists.")
        return value

    def create(self, validated_data):
        # Create standard user; profile gets assigned role=USER automatically
        return User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password'],
            email=validated_data.get('email', '')
        )


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


class PriceAlertSerializer(serializers.ModelSerializer):
    origin = serializers.CharField(max_length=10)
    destination = serializers.CharField(max_length=10)

    class Meta:
        model = PriceAlert
        fields = ['id', 'origin', 'destination', 'threshold_price', 'status', 'created_at']
        read_only_fields = ['id', 'status', 'created_at']

    def validate_origin(self, value):
        return value.strip().upper()

    def validate_destination(self, value):
        return value.strip().upper()


class NotificationLogSerializer(serializers.ModelSerializer):
    route = serializers.SerializerMethodField()

    class Meta:
        model = NotificationLog
        fields = ['id', 'alert', 'route', 'triggered_price', 'message', 'notified_at']
        read_only_fields = ['id', 'alert', 'route', 'triggered_price', 'message', 'notified_at']

    def get_route(self, obj):
        return f"{obj.alert.origin}-{obj.alert.destination}"
