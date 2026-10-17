from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from pulse.models import UserProfile, PriceAlert, NotificationLog


class Command(BaseCommand):
    help = 'Seeds realistic Indian demonstration data (admin user, Indian users, domestic routes, and alerts)'

    def handle(self, *args, **options):
        self.stdout.write('Seeding Indian sample data for PulseNotify...')

        # 1. Create Admin User (Platform Administrator)
        admin_user, _ = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@pulsenotify.in',
                'first_name': 'Rajesh',
                'last_name': 'Sharma',
            }
        )
        admin_user.set_password('adminpass123')
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.save()

        admin_profile, _ = UserProfile.objects.get_or_create(user=admin_user)
        admin_profile.role = UserProfile.Role.ADMIN
        admin_profile.save()

        # 2. Create Indian Sample Users
        indian_users_data = [
            {
                'username': 'aarav',
                'email': 'aarav.patel@gmail.com',
                'first_name': 'Aarav',
                'last_name': 'Patel',
                'password': 'password123',
            },
            {
                'username': 'priya',
                'email': 'priya.sharma@yahoo.co.in',
                'first_name': 'Priya',
                'last_name': 'Sharma',
                'password': 'password123',
            },
            {
                'username': 'rohit',
                'email': 'rohit.verma@outlook.in',
                'first_name': 'Rohit',
                'last_name': 'Verma',
                'password': 'password123',
            },
            {
                'username': 'ananya',
                'email': 'ananya.iyer@gmail.com',
                'first_name': 'Ananya',
                'last_name': 'Iyer',
                'password': 'password123',
            },
            {
                'username': 'alice',
                'email': 'alice@example.com',
                'first_name': 'Alice',
                'last_name': 'Mehta',
                'password': 'securepass',
            },
        ]

        created_users = {}
        for u_data in indian_users_data:
            user_obj, _ = User.objects.get_or_create(
                username=u_data['username'],
                defaults={
                    'email': u_data['email'],
                    'first_name': u_data['first_name'],
                    'last_name': u_data['last_name'],
                }
            )
            user_obj.set_password(u_data['password'])
            user_obj.save()

            u_profile, _ = UserProfile.objects.get_or_create(user=user_obj)
            u_profile.role = UserProfile.Role.USER
            u_profile.save()
            created_users[u_data['username']] = user_obj

        # 3. Create Sample Indian Route Alerts with Realistic INR (₹) Prices
        # Popular corridors: DEL-BOM, BLR-HYD, DEL-BLR, BOM-GOA, CCU-DEL, MAA-BLR, PNQ-DEL
        sample_alerts_data = [
            # Aarav's Alerts
            {
                'user': created_users['aarav'],
                'origin': 'DEL',
                'destination': 'BOM',
                'threshold_price': 4500.00,
                'status': PriceAlert.Status.ACTIVE,
            },
            {
                'user': created_users['aarav'],
                'origin': 'DEL',
                'destination': 'BLR',
                'threshold_price': 5200.00,
                'status': PriceAlert.Status.TRIGGERED,
                'triggered_price': 4800.00,
            },
            # Priya's Alerts
            {
                'user': created_users['priya'],
                'origin': 'BLR',
                'destination': 'HYD',
                'threshold_price': 2200.00,
                'status': PriceAlert.Status.ACTIVE,
            },
            {
                'user': created_users['priya'],
                'origin': 'BOM',
                'destination': 'GOA',
                'threshold_price': 2800.00,
                'status': PriceAlert.Status.ACTIVE,
            },
            # Rohit's Alerts
            {
                'user': created_users['rohit'],
                'origin': 'DEL',
                'destination': 'BOM',
                'threshold_price': 4200.00,
                'status': PriceAlert.Status.ACTIVE,
            },
            {
                'user': created_users['rohit'],
                'origin': 'CCU',
                'destination': 'DEL',
                'threshold_price': 4600.00,
                'status': PriceAlert.Status.TRIGGERED,
                'triggered_price': 4150.00,
            },
            # Ananya's Alerts
            {
                'user': created_users['ananya'],
                'origin': 'MAA',
                'destination': 'BLR',
                'threshold_price': 2000.00,
                'status': PriceAlert.Status.ACTIVE,
            },
            {
                'user': created_users['ananya'],
                'origin': 'PNQ',
                'destination': 'DEL',
                'threshold_price': 3500.00,
                'status': PriceAlert.Status.INACTIVE,
            },
            # Alice's Alerts (Default assignment demo)
            {
                'user': created_users['alice'],
                'origin': 'DEL',
                'destination': 'BOM',
                'threshold_price': 4500.00,
                'status': PriceAlert.Status.ACTIVE,
            },
            {
                'user': created_users['alice'],
                'origin': 'BLR',
                'destination': 'HYD',
                'threshold_price': 2500.00,
                'status': PriceAlert.Status.ACTIVE,
            },
        ]

        for a_data in sample_alerts_data:
            alert, _ = PriceAlert.objects.get_or_create(
                user=a_data['user'],
                origin=a_data['origin'],
                destination=a_data['destination'],
                threshold_price=a_data['threshold_price'],
                defaults={'status': a_data['status']}
            )
            alert.status = a_data['status']
            alert.save()

            # If triggered, create realistic NotificationLog
            if a_data['status'] == PriceAlert.Status.TRIGGERED:
                trig_price = a_data.get('triggered_price', a_data['threshold_price'] - 300)
                msg = (
                    f"Price alert triggered! {alert.origin}-{alert.destination} "
                    f"is now ₹{trig_price} - below your threshold of ₹{alert.threshold_price}"
                )
                NotificationLog.objects.get_or_create(
                    alert=alert,
                    triggered_price=trig_price,
                    defaults={'message': msg}
                )

        self.stdout.write(self.style.SUCCESS('Successfully seeded Indian sample data!'))
        self.stdout.write('\n--- Demo Accounts Created ---')
        self.stdout.write('  [Admin] username: "admin"    | password: "adminpass123" | Rajesh Sharma (admin@pulsenotify.in)')
        self.stdout.write('  [User]  username: "aarav"    | password: "password123"  | Aarav Patel (DEL-BOM, DEL-BLR)')
        self.stdout.write('  [User]  username: "priya"    | password: "password123"  | Priya Sharma (BLR-HYD, BOM-GOA)')
        self.stdout.write('  [User]  username: "rohit"    | password: "password123"  | Rohit Verma (DEL-BOM, CCU-DEL)')
        self.stdout.write('  [User]  username: "ananya"   | password: "password123"  | Ananya Iyer (MAA-BLR, PNQ-DEL)')
        self.stdout.write('  [User]  username: "alice"    | password: "securepass"   | Alice Mehta (DEL-BOM, BLR-HYD)')
        self.stdout.write('\n--- Indian Domestic Routes Covered ---')
        self.stdout.write('  DEL-BOM (Delhi -> Mumbai), BLR-HYD (Bengaluru -> Hyderabad)')
        self.stdout.write('  DEL-BLR (Delhi -> Bengaluru), BOM-GOA (Mumbai -> Goa)')
        self.stdout.write('  CCU-DEL (Kolkata -> Delhi), MAA-BLR (Chennai -> Bengaluru), PNQ-DEL (Pune -> Delhi)')
