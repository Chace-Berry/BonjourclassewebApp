from celery import shared_task
from .models import CertificateFile
from django.utils import timezone

@shared_task
def delete_expired_certificates():
    now = timezone.now()
    expired_files = CertificateFile.objects.filter(expires_at__lt=now)
    for cert_file in expired_files:
        cert_file.file.delete(save=False)
        cert_file.delete()