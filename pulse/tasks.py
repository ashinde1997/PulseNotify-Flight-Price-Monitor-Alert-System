import logging
import requests
from celery import shared_task
from django.conf import settings
from .models import PriceAlert, NotificationLog

logger = logging.getLogger(__name__)


@shared_task
def check_prices():
    """Periodic task running on Celery Beat to monitor flight prices."""
    logger.info("Starting flight price check...")
    active_alerts = PriceAlert.objects.filter(status=PriceAlert.Status.ACTIVE)
    routes = active_alerts.values_list('origin', 'destination').distinct()

    flight_api_url = getattr(
        settings,
        'INTERNAL_FLIGHT_API_URL',
        'http://localhost:8000/api/flights/price/'
    )

    for origin, destination in routes:
        route = f'{origin}-{destination}'

        try:
            # Query the mock flight endpoint for latest pricing
            response = requests.get(
                flight_api_url,
                params={'route': route},
                timeout=10
            )

            if response.status_code != 200:
                logger.warning(f"Could not retrieve price for {route} (HTTP {response.status_code})")
                continue

            current_price = response.json().get('price')
            if current_price is None:
                continue

            logger.info(f"Route {route} current price: ₹{current_price}")

            # Match against active alerts on this route
            route_alerts = active_alerts.filter(
                origin=origin,
                destination=destination
            )

            for alert in route_alerts:
                if current_price <= float(alert.threshold_price):
                    logger.info(
                        f"Price drop detected for alert #{alert.id} ({route}): "
                        f"₹{current_price} <= ₹{alert.threshold_price}"
                    )
                    # Offload alert notification to worker
                    send_notification.delay(alert.id, current_price)

        except requests.RequestException as exc:
            logger.error(f"Price check error for route {route}: {exc}")
            continue

    logger.info("Price check finished.")


@shared_task
def send_notification(alert_id, triggered_price):
    """Processes alert notification and records log entry asynchronously."""
    try:
        alert = PriceAlert.objects.get(id=alert_id)
        message = (
            f'Price alert triggered! {alert.origin}-{alert.destination} '
            f'is now ₹{triggered_price} - below your threshold of '
            f'₹{alert.threshold_price}'
        )

        NotificationLog.objects.create(
            alert=alert,
            triggered_price=triggered_price,
            message=message
        )

        # Transition status so this alert doesn't re-trigger
        alert.status = PriceAlert.Status.TRIGGERED
        alert.save()

        logger.info(f"Alert #{alert_id} notification logged at ₹{triggered_price}")
    except PriceAlert.DoesNotExist:
        logger.error(f"Alert #{alert_id} not found in database.")
