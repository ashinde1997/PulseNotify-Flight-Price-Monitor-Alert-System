from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from .models import UserProfile, PriceAlert, NotificationLog
from .tasks import check_prices, send_notification


# Core business logic tests
class PriceThresholdTest(TestCase):
    def test_price_below_threshold_triggers_alert(self):
        # Current price (4200) <= threshold (4500)
        self.assertTrue(4200 <= 4500)

    def test_price_above_threshold_does_not_trigger(self):
        # Current price (5000) > threshold (4500)
        self.assertFalse(5000 <= 4500)

    def test_price_equal_to_threshold_triggers_alert(self):
        # Exact match edge case
        self.assertTrue(4500 <= 4500)


class NotificationLogTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', password='testpass'
        )
        self.alert = PriceAlert.objects.create(
            user=self.user,
            origin='DEL', destination='BOM',
            threshold_price=4500,
            status=PriceAlert.Status.ACTIVE
        )

    def test_notification_log_created_with_correct_message(self):
        log = NotificationLog.objects.create(
            alert=self.alert,
            triggered_price=4200,
            message='Price dropped to 4200 for DEL-BOM'
        )
        self.assertEqual(log.triggered_price, 4200)
        self.assertEqual(log.alert, self.alert)
        self.assertIn('DEL-BOM', log.message)


class AlertScopingTest(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            username='user1', password='pass'
        )
        self.user2 = User.objects.create_user(
            username='user2', password='pass'
        )
        PriceAlert.objects.create(
            user=self.user1, origin='DEL', destination='BOM',
            threshold_price=4500
        )
        PriceAlert.objects.create(
            user=self.user2, origin='BLR', destination='HYD',
            threshold_price=2000
        )

    def test_user_only_sees_own_alerts(self):
        user1_alerts = PriceAlert.objects.filter(user=self.user1)
        self.assertEqual(user1_alerts.count(), 1)
        self.assertEqual(user1_alerts.first().origin, 'DEL')

    def test_user_cannot_see_other_users_alerts(self):
        user2_alerts = PriceAlert.objects.filter(user=self.user1)
        self.assertNotEqual(user2_alerts.first().origin, 'BLR')


# API & task integration tests
class AuthAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_register_new_user_success(self):
        data = {
            "username": "alice",
            "password": "securepass123",
            "email": "alice@example.com"
        }
        response = self.client.post('/api/auth/register/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['username'], "alice")
        self.assertEqual(response.data['role'], "user")
        self.assertIn('access', response.data)

        # Profile should be auto-created with default role
        user = User.objects.get(username="alice")
        self.assertEqual(user.profile.role, UserProfile.Role.USER)

    def test_register_duplicate_username_fails(self):
        User.objects.create_user(username="alice", password="securepass123")
        data = {
            "username": "alice",
            "password": "anotherpassword",
            "email": "alice2@example.com"
        }
        response = self.client.post('/api/auth/register/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_valid_credentials(self):
        User.objects.create_user(username="bob", password="validpassword123")
        data = {"username": "bob", "password": "validpassword123"}
        response = self.client.post('/api/auth/login/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertEqual(response.data['username'], 'bob')

    def test_login_invalid_credentials(self):
        User.objects.create_user(username="bob", password="validpassword123")
        data = {"username": "bob", "password": "wrongpassword"}
        response = self.client.post('/api/auth/login/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AlertAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="alice", password="password123")
        self.token = str(RefreshToken.for_user(self.user).access_token)

    def test_create_alert_without_token_fails(self):
        response = self.client.post('/api/alerts/', {"origin": "DEL", "destination": "BOM", "threshold_price": 5000})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_alert_with_token_success(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        data = {"origin": "DEL", "destination": "BOM", "threshold_price": "4500.00"}
        response = self.client.post('/api/alerts/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['origin'], "DEL")
        self.assertEqual(response.data['destination'], "BOM")
        self.assertEqual(response.data['status'], "active")

        alert = PriceAlert.objects.get(id=response.data['id'])
        self.assertEqual(alert.user, self.user)

    def test_list_alerts_scoped_to_user(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        PriceAlert.objects.create(user=self.user, origin="DEL", destination="BOM", threshold_price=4500)

        # Alert belonging to someone else
        other_user = User.objects.create_user(username="other", password="password")
        PriceAlert.objects.create(user=other_user, origin="BLR", destination="HYD", threshold_price=3000)

        response = self.client.get('/api/alerts/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['origin'], 'DEL')

    def test_deactivate_alert(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        alert = PriceAlert.objects.create(user=self.user, origin="DEL", destination="BOM", threshold_price=4500)

        response = self.client.delete(f'/api/alerts/{alert.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'inactive')

        alert.refresh_from_db()
        self.assertEqual(alert.status, PriceAlert.Status.INACTIVE)

    def test_deactivate_other_users_alert_returns_404(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        other_user = User.objects.create_user(username="other", password="password")
        alert = PriceAlert.objects.create(user=other_user, origin="BLR", destination="HYD", threshold_price=3000)

        response = self.client.delete(f'/api/alerts/{alert.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class FlightPriceFeedAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_mock_price_valid_route(self):
        response = self.client.get('/api/flights/price/?route=DEL-BOM')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['route'], 'DEL-BOM')
        self.assertTrue(3000 <= data['price'] <= 7000)

    def test_mock_price_invalid_route(self):
        response = self.client.get('/api/flights/price/?route=XYZ-ABC')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()['error'], 'Route not found')


class AdminSummaryAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="regular", password="password")
        self.user_token = str(RefreshToken.for_user(self.user).access_token)

        self.admin = User.objects.create_user(username="adminuser", password="adminpassword")
        self.admin.profile.role = UserProfile.Role.ADMIN
        self.admin.profile.save()
        self.admin_token = str(RefreshToken.for_user(self.admin).access_token)

        # Populate a few sample alerts
        PriceAlert.objects.create(user=self.user, origin="DEL", destination="BOM", threshold_price=4500, status=PriceAlert.Status.ACTIVE)
        PriceAlert.objects.create(user=self.user, origin="DEL", destination="BOM", threshold_price=5000, status=PriceAlert.Status.ACTIVE)
        PriceAlert.objects.create(user=self.user, origin="BLR", destination="HYD", threshold_price=2500, status=PriceAlert.Status.TRIGGERED)

    def test_regular_user_cannot_access_admin_summary(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.user_token}')
        response = self.client.get('/api/admin/summary/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_access_summary(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        response = self.client.get('/api/admin/summary/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_alerts'], 3)
        self.assertEqual(response.data['active_alerts'], 2)
        self.assertEqual(response.data['triggered_alerts'], 1)
        self.assertEqual(response.data['total_notifications'], 0)
        self.assertTrue(len(response.data['top_routes']) > 0)


class CeleryTasksTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="celeryuser", password="password")
        self.alert = PriceAlert.objects.create(
            user=self.user,
            origin="DEL",
            destination="BOM",
            threshold_price=4500,
            status=PriceAlert.Status.ACTIVE
        )

    def test_send_notification_task(self):
        send_notification(self.alert.id, 4200)
        self.alert.refresh_from_db()
        self.assertEqual(self.alert.status, PriceAlert.Status.TRIGGERED)

        logs = NotificationLog.objects.filter(alert=self.alert)
        self.assertEqual(logs.count(), 1)
        self.assertEqual(logs.first().triggered_price, 4200)

    @patch('pulse.tasks.requests.get')
    @patch('pulse.tasks.send_notification.delay')
    def test_check_prices_task_triggers_notification(self, mock_delay, mock_requests_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'route': 'DEL-BOM', 'price': 4200}
        mock_requests_get.return_value = mock_response

        check_prices()

        mock_delay.assert_called_once_with(self.alert.id, 4200)
