from django.db import migrations
import json

def clean_features_json(apps, schema_editor):
    Subscription = apps.get_model('api', 'Subscription')
    SubscriptionPackage = apps.get_model('api', 'SubscriptionPackage')

    # Clean Subscription.features
    for sub in Subscription.objects.all():
        val = sub.features
        if val is None or isinstance(val, (list, dict)):
            continue
        try:
            sub.features = json.loads(val)
        except Exception:
            sub.features = []
        sub.save(update_fields=['features'])

    # Clean SubscriptionPackage.features
    for pkg in SubscriptionPackage.objects.all():
        val = pkg.features
        if val is None or isinstance(val, (list, dict)):
            continue
        try:
            pkg.features = json.loads(val)
        except Exception:
            pkg.features = []
        pkg.save(update_fields=['features'])

class Migration(migrations.Migration):

    dependencies = [
        ('api', '0041_fix_subscription_features'),  # or your latest migration
    ]

    operations = [
        migrations.RunPython(clean_features_json),
    ]