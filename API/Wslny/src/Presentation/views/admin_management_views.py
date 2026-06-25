from django.contrib.auth import get_user_model
from django.db.models import Avg, Count, Q
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    OpenApiTypes,
    extend_schema,
    inline_serializer,
)

from src.Core.Domain.Constants.Roles import Roles
from src.Infrastructure.History.models import RouteFeedback, RouteHistory
from src.Presentation.permissions import IsAdminUser
from src.Presentation.schemas import (
    AdminUserDetailSerializer,
    AdminUserUpdateSerializer,
    MessageResponseSerializer,
)

User = get_user_model()


class AdminUserDetailView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        tags=["Admin"],
        summary="Get user detail with stats",
        responses={
            200: AdminUserDetailSerializer,
            404: OpenApiResponse(description="User not found"),
        },
    )
    def get(self, request, user_id):
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response(
                {"error": {"code": "USER_NOT_FOUND", "message": "User not found."}},
                status=status.HTTP_404_NOT_FOUND,
            )

        route_count = RouteHistory.objects.filter(user=user).count()
        saved_locations_count = user.saved_locations.count()
        favorite_routes_count = user.favorite_routes.count()

        return Response(
            {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "mobile_number": user.mobile_number,
                "gender": user.gender,
                "address": user.address,
                "role": user.role,
                "is_active": user.is_active,
                "date_joined": user.date_joined,
                "total_routes": route_count,
                "saved_locations_count": saved_locations_count,
                "favorite_routes_count": favorite_routes_count,
            }
        )

    @extend_schema(
        tags=["Admin"],
        summary="Update user profile",
        request=AdminUserUpdateSerializer,
        responses={
            200: AdminUserDetailSerializer,
            400: OpenApiResponse(description="Validation error"),
            404: OpenApiResponse(description="User not found"),
        },
    )
    def put(self, request, user_id):
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response(
                {"error": {"code": "USER_NOT_FOUND", "message": "User not found."}},
                status=status.HTTP_404_NOT_FOUND,
            )

        data = request.data if isinstance(request.data, dict) else {}

        if "first_name" in data:
            user.first_name = data["first_name"]
        if "last_name" in data:
            user.last_name = data["last_name"]
        if "mobile_number" in data:
            user.mobile_number = data["mobile_number"]
        if "gender" in data:
            user.gender = data["gender"]
        if "address" in data:
            user.address = data["address"]
        if "role" in data:
            new_role = data["role"]
            if new_role not in [Roles.ADMIN, Roles.USER]:
                return Response(
                    {
                        "error": {
                            "code": "INVALID_ROLE",
                            "message": f"Role must be '{Roles.ADMIN}' or '{Roles.USER}'.",
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            user.role = new_role
            user.is_staff = new_role == Roles.ADMIN
            user.is_superuser = new_role == Roles.ADMIN
        if "is_active" in data:
            user.is_active = bool(data["is_active"])

        user.save()

        return Response(
            {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "mobile_number": user.mobile_number,
                "gender": user.gender,
                "address": user.address,
                "role": user.role,
                "is_active": user.is_active,
                "date_joined": user.date_joined,
                "message": "User updated successfully.",
            }
        )

    @extend_schema(
        tags=["Admin"],
        summary="Deactivate user (soft delete)",
        responses={
            200: OpenApiResponse(response=MessageResponseSerializer),
            404: OpenApiResponse(description="User not found"),
        },
    )
    def delete(self, request, user_id):
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response(
                {"error": {"code": "USER_NOT_FOUND", "message": "User not found."}},
                status=status.HTTP_404_NOT_FOUND,
            )

        if user.id == request.user.id:
            return Response(
                {
                    "error": {
                        "code": "CANNOT_DEACTIVATE_SELF",
                        "message": "You cannot deactivate your own account.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.is_active = False
        user.save()

        return Response({"message": f"User {user.email} has been deactivated."})


class UserAnalyticsOverviewView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        tags=["Admin Analytics"],
        summary="User growth and activity overview",
        parameters=[
            OpenApiParameter(
                name="from_date",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="to_date",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
            ),
        ],
        responses={
            200: inline_serializer(
                name="UserAnalyticsOverviewResponse",
                fields={
                    "totals": serializers.DictField(),
                    "growth": serializers.ListField(child=serializers.DictField()),
                    "top_users_by_routes": serializers.ListField(
                        child=serializers.DictField()
                    ),
                },
            )
        },
    )
    def get(self, request):
        from django.utils.dateparse import parse_date

        raw_from = request.query_params.get("from_date")
        raw_to = request.query_params.get("to_date")
        from_date = parse_date(raw_from) if raw_from else None
        to_date = parse_date(raw_to) if raw_to else None

        if raw_from and from_date is None:
            return Response(
                {
                    "error": {
                        "code": "INVALID_QUERY_PARAM",
                        "message": "from_date must be in YYYY-MM-DD format.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if raw_to and to_date is None:
            return Response(
                {
                    "error": {
                        "code": "INVALID_QUERY_PARAM",
                        "message": "to_date must be in YYYY-MM-DD format.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        admin_users = User.objects.filter(role=Roles.ADMIN).count()

        users_with_routes = RouteHistory.objects.values("user").distinct().count()

        total_routes = RouteHistory.objects.count()
        avg_routes_per_user = (
            round(total_routes / total_users, 2) if total_users else 0.0
        )

        user_qs = User.objects.all()
        if from_date:
            user_qs = user_qs.filter(date_joined__date__gte=from_date)
        if to_date:
            user_qs = user_qs.filter(date_joined__date__lte=to_date)

        growth_qs = (
            user_qs.extra({"day": "date(date_joined)"})
            .values("day")
            .annotate(count=Count("id"))
            .order_by("day")
        )
        growth = list(growth_qs)

        top_users_qs = (
            RouteHistory.objects.values(
                "user__email", "user__first_name", "user__last_name"
            )
            .annotate(
                route_count=Count("id"),
                success_count=Count("id", filter=Q(status=RouteHistory.STATUS_SUCCESS)),
            )
            .order_by("-route_count")[:10]
        )
        top_users = list(top_users_qs)

        return Response(
            {
                "totals": {
                    "total_users": total_users,
                    "active_users": active_users,
                    "inactive_users": total_users - active_users,
                    "admin_users": admin_users,
                    "users_with_routes": users_with_routes,
                    "avg_routes_per_user": avg_routes_per_user,
                },
                "growth": growth,
                "top_users_by_routes": top_users,
            }
        )


class FeedbackAnalyticsView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        tags=["Admin Analytics"],
        summary="List feedback with filters",
        parameters=[
            OpenApiParameter(
                name="min_rating",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter by minimum rating (1-5)",
            ),
            OpenApiParameter(
                name="max_rating",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter by maximum rating (1-5)",
            ),
            OpenApiParameter(
                name="user_id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter by user ID",
            ),
            OpenApiParameter(
                name="from_date",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="to_date",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="limit",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Page size (default 20)",
            ),
            OpenApiParameter(
                name="offset",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Page offset (default 0)",
            ),
        ],
        responses={
            200: inline_serializer(
                name="FeedbackListResponse",
                fields={
                    "feedback": serializers.ListField(child=serializers.DictField()),
                    "pagination": serializers.DictField(),
                },
            )
        },
    )
    def get(self, request):
        from django.utils.dateparse import parse_date

        qs = RouteFeedback.objects.select_related("user").all()

        min_rating = request.query_params.get("min_rating")
        max_rating = request.query_params.get("max_rating")
        user_id = request.query_params.get("user_id")
        raw_from = request.query_params.get("from_date")
        raw_to = request.query_params.get("to_date")
        from_date = parse_date(raw_from) if raw_from else None
        to_date = parse_date(raw_to) if raw_to else None

        if raw_from and from_date is None:
            return Response(
                {
                    "error": {
                        "code": "INVALID_QUERY_PARAM",
                        "message": "from_date must be in YYYY-MM-DD format.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if raw_to and to_date is None:
            return Response(
                {
                    "error": {
                        "code": "INVALID_QUERY_PARAM",
                        "message": "to_date must be in YYYY-MM-DD format.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if min_rating:
            try:
                qs = qs.filter(rating__gte=int(min_rating))
            except ValueError:
                pass
        if max_rating:
            try:
                qs = qs.filter(rating__lte=int(max_rating))
            except ValueError:
                pass
        if user_id:
            try:
                qs = qs.filter(user_id=int(user_id))
            except ValueError:
                pass
        if from_date:
            qs = qs.filter(created_at__date__gte=from_date)
        if to_date:
            qs = qs.filter(created_at__date__lte=to_date)

        total = qs.count()

        try:
            limit = min(int(request.query_params.get("limit", 20)), 200)
        except (TypeError, ValueError):
            limit = 20
        try:
            offset = max(int(request.query_params.get("offset", 0)), 0)
        except (TypeError, ValueError):
            offset = 0

        feedback_list = qs[offset : offset + limit]

        feedback_data = [
            {
                "id": fb.id,
                "user_id": fb.user_id,
                "user_email": fb.user.email,
                "request_id": fb.request_id,
                "rating": fb.rating,
                "comment": fb.comment,
                "created_at": fb.created_at,
            }
            for fb in feedback_list
        ]

        return Response(
            {
                "feedback": feedback_data,
                "pagination": {
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                },
            }
        )


class FeedbackSummaryView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        tags=["Admin Analytics"],
        summary="Feedback aggregate statistics",
        parameters=[
            OpenApiParameter(
                name="from_date",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="to_date",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
            ),
        ],
        responses={
            200: inline_serializer(
                name="FeedbackSummaryResponse",
                fields={
                    "total_feedback": serializers.IntegerField(),
                    "average_rating": serializers.FloatField(),
                    "rating_distribution": serializers.DictField(),
                },
            )
        },
    )
    def get(self, request):
        from django.utils.dateparse import parse_date

        qs = RouteFeedback.objects.all()

        raw_from = request.query_params.get("from_date")
        raw_to = request.query_params.get("to_date")
        from_date = parse_date(raw_from) if raw_from else None
        to_date = parse_date(raw_to) if raw_to else None

        if raw_from and from_date is None:
            return Response(
                {
                    "error": {
                        "code": "INVALID_QUERY_PARAM",
                        "message": "from_date must be in YYYY-MM-DD format.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if raw_to and to_date is None:
            return Response(
                {
                    "error": {
                        "code": "INVALID_QUERY_PARAM",
                        "message": "to_date must be in YYYY-MM-DD format.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if from_date:
            qs = qs.filter(created_at__date__gte=from_date)
        if to_date:
            qs = qs.filter(created_at__date__lte=to_date)

        total = qs.count()
        avg_rating = qs.aggregate(avg=Avg("rating"))["avg"] or 0.0

        distribution = {}
        for rating_value in range(1, 6):
            count = qs.filter(rating=rating_value).count()
            distribution[str(rating_value)] = count

        return Response(
            {
                "total_feedback": total,
                "average_rating": round(avg_rating, 2),
                "rating_distribution": distribution,
            }
        )
