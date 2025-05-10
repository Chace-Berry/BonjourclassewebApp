from django.core.management.base import BaseCommand
from django.utils import timezone
from api.models import Subscription

class Command(BaseCommand):
    help = 'Delete subscriptions expired for more than 7 days'

    def handle(self, *args, **kwargs):
        now = timezone.now()
        cutoff = now - timezone.timedelta(days=7)
        expired_subs = Subscription.objects.filter(valid_until__lt=cutoff)
        count = expired_subs.count()
        expired_subs.delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {count} expired subscriptions"))