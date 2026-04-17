import os

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from src.Core.Domain.Constants.Roles import Roles


class Command(BaseCommand):
    help = "Seeds the database with a default admin user"

    def handle(self, *args, **options):
        User = get_user_model()
        email = os.getenv("ADMIN_SEED_EMAIL", "admin@wslny.com")
        password = os.getenv("ADMIN_SEED_PASSWORD")
        if not password:
            self.stdout.write(
                self.style.WARNING("ADMIN_SEED_PASSWORD not set; skipping admin seed.")
            )
            return

        if not User.objects.filter(email=email).exists():
            User.objects.create_superuser(
                email=email,
                password=password,
                first_name="Admin",
                last_name="User",
                mobile_number="0000000000",
                role=Roles.ADMIN,
            )
            self.stdout.write(
                self.style.SUCCESS(f"Successfully created admin user: {email}")
            )
        else:
            self.stdout.write(self.style.SUCCESS(f"Admin user already exists: {email}"))
