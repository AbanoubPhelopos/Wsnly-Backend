"""
Seed the database with realistic demo data so the admin dashboard has
something to display.

Creates:
  • 20 additional users (mix of Admin / User roles, varied join dates)
  • 60+ RouteHistory rows (varied sources, filters, statuses, dates,
    latencies — enough to populate every analytics view)
  • 20 RouteFeedback rows (varied ratings, comments)

Idempotent: running it again skips rows whose (request_id) already exists,
so it never blows up on a second run. Safe to call from
entrypoint.sh or by hand.

Usage (from inside the Django container or venv):
    python manage.py seed_demo_data
    python manage.py seed_demo_data --users 50 --routes 200  # bigger run
"""

import random
import uuid
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from src.Core.Domain.Constants.Roles import Roles
from src.Infrastructure.History.models import RouteFeedback, RouteHistory
from src.Infrastructure.Identity.models import User


PREFIX = "[seed]"  # marker so we can find/delete these rows later if needed


CAIRO_PLACES = [
    ("Tahrir Square", 30.0444, 31.2357),
    ("Cairo University", 30.0277, 31.2101),
    ("Maadi", 29.9602, 31.2569),
    ("Heliopolis", 30.0866, 31.3300),
    ("Nasr City", 30.0511, 31.3656),
    ("Giza Pyramids", 29.9792, 31.1342),
    ("Downtown Cairo", 30.0444, 31.2357),
    ("Zamalek", 30.0618, 31.2197),
    ("Mohandessin", 30.0500, 31.2000),
    ("Heliopolis Square", 30.0889, 31.3300),
    ("Ramses Station", 30.0611, 31.2467),
    ("Cairo Tower", 30.0459, 31.2244),
    ("Khan el-Khalili", 30.0478, 31.2622),
    ("Al-Azhar Park", 30.0405, 31.2625),
    ("Garden City", 30.0439, 31.2330),
]

PREFERENCES = [
    ("optimal", 1),
    ("fastest", 2),
    ("cheapest", 3),
    ("bus_only", 4),
    ("microbus_only", 5),
    ("metro_only", 6),
]

SOURCES = ["text", "map"]
STATUSES = ["success", "success", "success", "success", "failed"]  # 80% success

UNRESOLVED_REASONS = [
    "no_nearby_stops",
    "destination_not_found",
    "ai_extraction_failed",
    "routing_engine_timeout",
]

FEEDBACK_COMMENTS = [
    "Route was accurate, slight delay at transfer.",
    "Great route, fast and cheap.",
    "Driver was rude, but route was correct.",
    "Got me there in half the time. Excellent.",
    "Took me to a different place than I asked.",
    "Walk was very long, otherwise fine.",
    "Bus was late but route was good.",
    "Saved me time, will use again.",
    "Confusing transfer instructions.",
    "Perfect route through downtown.",
    "Cheaper than a taxi, thanks.",
    "Quick and easy, recommended.",
]


def make_request_id() -> str:
    return f"{PREFIX}-{uuid.uuid4().hex[:24]}"


class Command(BaseCommand):
    help = "Seeds the database with realistic demo data for the admin dashboard."

    def add_arguments(self, parser):
        parser.add_argument(
            "--users",
            type=int,
            default=20,
            help="Number of additional demo users to seed (default 20).",
        )
        parser.add_argument(
            "--routes",
            type=int,
            default=60,
            help="Number of route-history rows to seed (default 60).",
        )
        parser.add_argument(
            "--feedback",
            type=int,
            default=20,
            help="Number of feedback rows to seed (default 20).",
        )
        parser.add_argument(
            "--span-days",
            type=int,
            default=30,
            help="Spread created_at across the last N days (default 30).",
        )

    def handle(self, *args, **options):
        random.seed(42)  # deterministic output for reproducible testing

        n_users = options["users"]
        n_routes = options["routes"]
        n_feedback = options["feedback"]
        span_days = options["span_days"]

        now = timezone.now()
        self.stdout.write(
            f"{PREFIX} Seeding {n_users} users, {n_routes} routes, "
            f"{n_feedback} feedback rows (span = {span_days} days)"
        )

        users = self._seed_users(n_users, now, span_days)
        self._seed_routes(users, n_routes, now, span_days)
        self._seed_feedback(users, n_feedback, now, span_days)

        self.stdout.write(self.style.SUCCESS(f"{PREFIX} Done."))

    # ─── Users ────────────────────────────────────────────────────────
    def _seed_users(self, n_users: int, now, span_days: int) -> list[User]:
        first_names = [
            "Ali", "Sara", "Omar", "Layla", "Hassan", "Nour", "Karim",
            "Mona", "Ahmed", "Yasmin", "Mahmoud", "Yara", "Tarek", "Hala",
            "Karim", "Dina", "Amr", "Rana", "Walid", "Maya", "Salma", "Adel",
            "Nada", "Hussein", "Lina",
        ]
        last_names = [
            "Hassan", "Mahmoud", "Ali", "Ibrahim", "Sayed", "Khalil",
            "Nasser", "Farouk", "Soliman", "Mostafa", "Gaber", "Rashed",
            "Aziz", "Salem", "El-Sayed",
        ]
        genders = ["male", "female", "other"]
        created: list[User] = []
        existing_emails = set(User.objects.values_list("email", flat=True))
        for i in range(n_users):
            email = f"{PREFIX}.{first_names[i % len(first_names)]}.{last_names[i % len(last_names)]}{i}@example.com"
            if email in existing_emails:
                continue
            joined = now - timedelta(
                days=random.randint(0, span_days),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59),
            )
            role = Roles.ADMIN if i % 7 == 0 else Roles.USER
            user = User.objects.create_user(
                email=email,
                password="DemoUser!2026",
                first_name=first_names[i % len(first_names)],
                last_name=last_names[i % len(last_names)],
                mobile_number=f"+20100{random.randint(1000000, 9999999)}",
                gender=random.choice(genders),
                address=random.choice(
                    ["Cairo", "Giza", "Maadi", "Heliopolis", "Zamalek", "Nasr City"]
                ),
                role=role,
                is_active=(i % 11 != 0),  # ~9% inactive
            )
            # Override auto_now_add for date_joined by using raw update
            User.objects.filter(pk=user.pk).update(date_joined=joined)
            created.append(user)
        self.stdout.write(f"{PREFIX} users: created={len(created)}, total={User.objects.count()}")
        return User.objects.exclude(email="admin@wslny.com").order_by("id")[:]

    # ─── Routes ──────────────────────────────────────────────────────
    def _seed_routes(self, users: list[User], n_routes: int, now, span_days: int):
        existing_ids = set(
            RouteHistory.objects.filter(request_id__startswith=PREFIX)
            .values_list("request_id", flat=True)
        )
        if len(existing_ids) >= n_routes:
            self.stdout.write(f"{PREFIX} routes: skipped (already have {len(existing_ids)})")
            return

        rows = []
        for _ in range(n_routes):
            origin = random.choice(CAIRO_PLACES)
            destination = random.choice([p for p in CAIRO_PLACES if p[0] != origin[0]])
            preference_name, preference_num = random.choice(PREFERENCES)
            source = random.choice(SOURCES)
            status = random.choice(STATUSES)
            created_at = now - timedelta(
                days=random.randint(0, span_days),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59),
                seconds=random.randint(0, 59),
            )

            request_id = make_request_id()

            ai_ms = random.uniform(200, 900)
            routing_ms = random.uniform(40, 200)
            total_ms = ai_ms + routing_ms + random.uniform(20, 80)
            distance_km = random.uniform(2.0, 35.0)
            duration_min = distance_km * random.uniform(2.0, 5.0)
            fare = round(
                max(5.0, distance_km * random.uniform(0.8, 2.5)), 2
            )

            has_result = status == "success"
            unresolved_reason = None if has_result else random.choice(UNRESOLVED_REASONS)
            error_code = None if has_result else unresolved_reason.upper()
            error_message = None if has_result else f"Simulated failure: {unresolved_reason}"
            input_text = (
                f"From {origin[0]} to {destination[0]}"
                if source == "text"
                else None
            )

            user = random.choice(users) if users else None

            row = RouteHistory(
                user=user,
                source_type=source,
                request_id=request_id,
                input_text=input_text,
                preference=preference_name,
                selected_route_type=random.choice(
                    ["bus", "metro", "microbus", "optimal"]
                ),
                origin_name=origin[0],
                origin_lat=origin[1],
                origin_lon=origin[2],
                destination_name=destination[0],
                destination_lat=destination[1],
                destination_lon=destination[2],
                status=status,
                error_code=error_code,
                error_message=error_message,
                total_distance_meters=distance_km * 1000,
                total_duration_seconds=duration_min * 60,
                step_count=random.randint(1, 5),
                estimated_fare=fare,
                walk_distance_meters=random.uniform(50, 800),
                has_result=has_result,
                unresolved_reason=unresolved_reason,
                ai_latency_ms=ai_ms,
                routing_latency_ms=routing_ms,
                total_latency_ms=total_ms,
            )
            # auto_now_add prevents setting created_at via constructor; defer to bulk_create.
            row._created_at = created_at
            rows.append(row)

        # bulk_create honours the model's auto_now_add but we override after.
        RouteHistory.objects.bulk_create(rows, batch_size=100)
        # Patch created_at for our seeded rows (auto_now_add ignored on bulk_create).
        for row in rows:
            RouteHistory.objects.filter(pk=row.pk).update(created_at=row._created_at)
        self.stdout.write(f"{PREFIX} routes: created={len(rows)}, total={RouteHistory.objects.count()}")

    # ─── Feedback ────────────────────────────────────────────────────
    def _seed_feedback(self, users: list[User], n_feedback: int, now, span_days: int):
        if not users:
            self.stdout.write(f"{PREFIX} feedback: skipped (no users)")
            return

        routes = list(
            RouteHistory.objects.filter(
                request_id__startswith=PREFIX, status="success"
            )
        )
        if not routes:
            self.stdout.write(f"{PREFIX} feedback: skipped (no successful routes)")
            return

        existing = set(
            RouteFeedback.objects.filter(request_id__startswith=PREFIX)
            .values_list("user_id", "request_id")
        )

        rows = []
        attempts = 0
        while len(rows) < n_feedback and attempts < n_feedback * 5:
            attempts += 1
            user = random.choice(users)
            route = random.choice(routes)
            if (user.id, route.request_id) in existing:
                continue
            rating = random.choices([1, 2, 3, 4, 5], weights=[1, 2, 5, 8, 6])[0]
            created_at = route.created_at + timedelta(
                hours=random.randint(0, 48),
                minutes=random.randint(0, 59),
            )
            if created_at > now:
                created_at = now - timedelta(minutes=random.randint(1, 60))
            row = RouteFeedback(
                user=user,
                request_id=route.request_id,
                rating=rating,
                comment=random.choice(FEEDBACK_COMMENTS),
            )
            row._created_at = created_at
            rows.append(row)
            existing.add((user.id, route.request_id))

        RouteFeedback.objects.bulk_create(rows, batch_size=100)
        for row in rows:
            RouteFeedback.objects.filter(pk=row.pk).update(created_at=row._created_at)
        self.stdout.write(f"{PREFIX} feedback: created={len(rows)}, total={RouteFeedback.objects.count()}")
