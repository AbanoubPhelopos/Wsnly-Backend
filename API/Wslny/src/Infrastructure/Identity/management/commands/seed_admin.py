import os

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from src.Core.Domain.Constants.Roles import Roles


# Hardcoded fallback used ONLY when:
#   1. ADMIN_SEED_PASSWORD env var is unset, AND
#   2. DEBUG=True (Django debug mode — i.e. local development / docker-compose)
#
# Production deployments must always set ADMIN_SEED_PASSWORD explicitly.
# This constant is loud, dev-only, and bypassed whenever DEBUG is False.
DEV_FALLBACK_PASSWORD = "Admin@Wslny2026"


class Command(BaseCommand):
    help = "Seeds the database with a default admin user"

    def handle(self, *args, **options):
        User = get_user_model()
        email = os.getenv("ADMIN_SEED_EMAIL", "admin@wslny.com")
        password = os.getenv("ADMIN_SEED_PASSWORD")
        debug = os.getenv("DEBUG", "True").lower() in {"true", "1", "yes"}

        if not password:
            if not debug:
                # Production safety: never seed an admin with a known password.
                self.stdout.write(
                    self.style.ERROR(
                        "ADMIN_SEED_PASSWORD not set and DEBUG=False; "
                        "refusing to seed an admin user. "
                        "Set ADMIN_SEED_PASSWORD in your environment."
                    )
                )
                return
            password = DEV_FALLBACK_PASSWORD
            self.stdout.write(
                self.style.WARNING(
                    "ADMIN_SEED_PASSWORD not set; using DEV fallback password. "
                    "DO NOT deploy this configuration to production. "
                    f"Email: {email} | Password: {password}"
                )
            )

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
            existing = User.objects.get(email=email)
            self.stdout.write(
                self.style.SUCCESS(f"Admin user already exists: {email}")
            )

            updates = []
            if existing.role != Roles.ADMIN:
                existing.role = Roles.ADMIN
                existing.is_staff = True
                existing.is_superuser = True
                updates.extend(["role", "is_staff", "is_superuser"])
            if not existing.has_usable_password():
                existing.set_password(password)
                updates.append("password")
                self.stdout.write(
                    self.style.WARNING(
                        f"User had no usable password; reset to the seed password."
                    )
                )
            if updates:
                existing.save(update_fields=updates)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Updated existing user: {email} ({', '.join(updates)})"
                    )
                )

            if debug and not os.getenv("ADMIN_SEED_PASSWORD"):
                self.stdout.write(
                    self.style.WARNING(
                        f"To sign in locally, use: {email} / {DEV_FALLBACK_PASSWORD}"
                    )
                )
