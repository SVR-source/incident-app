from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Profile


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.get_or_create(
            user=instance,
            defaults={'must_change_password': True}
        )
        # Nếu admin chưa set password → mặc định 123456
        if not instance.has_usable_password():
            instance.set_password('123456')
            instance.save()