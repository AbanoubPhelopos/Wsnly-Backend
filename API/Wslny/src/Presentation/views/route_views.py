from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import (
    extend_schema,
    inline_serializer,
    OpenApiExample,
    OpenApiResponse,
)
from uuid import uuid4

from src.Infrastructure.GrpcClients.routing_client import RoutingGrpcClientError
from src.Infrastructure.History.models import RouteFeedback
from src.Presentation.schemas import (
    FILTER_ENUM_TO_PREFERENCE,
    RouteErrorResponseSerializer,
)
from src.Presentation.views.orchestrator import RouteOrchestratorView


class RouteAlternativesView(APIView):
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        from src.Infrastructure.GrpcClients import get_routing_client

        self.routing_client, routing_error = get_routing_client()
        self.client_boot_error = routing_error

    @extend_schema(
        tags=["Routing"],
        summary="Get all viable route alternatives",
        description=(
            "Returns all found route options (bus, metro, microbus, optimal) "
            "for the given origin/destination, not just the selected one."
        ),
        request=inline_serializer(
            name="RouteAlternativesRequest",
            fields={
                "origin_lat": serializers.FloatField(),
                "origin_lon": serializers.FloatField(),
                "destination_lat": serializers.FloatField(),
                "destination_lon": serializers.FloatField(),
            },
        ),
        responses={
            200: None,
            400: OpenApiResponse(response=RouteErrorResponseSerializer),
            503: OpenApiResponse(response=RouteErrorResponseSerializer),
        },
        examples=[
            OpenApiExample(
                "Alternatives Request",
                value={
                    "origin_lat": 30.05,
                    "origin_lon": 31.24,
                    "destination_lat": 30.07,
                    "destination_lon": 31.28,
                },
                request_only=True,
            ),
        ],
    )
    def post(self, request):
        request_id = str(uuid4())

        if self.client_boot_error:
            return Response(
                {
                    "request_id": request_id,
                    "error": {
                        "code": "SERVICE_CONFIGURATION_ERROR",
                        "message": self.client_boot_error,
                    },
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        data = request.data if isinstance(request.data, dict) else {}

        try:
            origin_lat = float(data.get("origin_lat"))
            origin_lon = float(data.get("origin_lon"))
            dest_lat = float(data.get("destination_lat"))
            dest_lon = float(data.get("destination_lon"))
        except (TypeError, ValueError):
            return Response(
                {
                    "request_id": request_id,
                    "error": {
                        "code": "INVALID_COORDINATES",
                        "message": "origin_lat, origin_lon, destination_lat, destination_lon are required and must be numbers.",
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if self.routing_client is None:
            return Response(
                {
                    "request_id": request_id,
                    "error": {
                        "code": "SERVICE_CONFIGURATION_ERROR",
                        "message": "Routing service client is not configured.",
                    },
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            route_result = self.routing_client.get_route(
                origin_lat, origin_lon, dest_lat, dest_lon
            )
        except RoutingGrpcClientError as error:
            return Response(
                {
                    "request_id": request_id,
                    "error": {
                        "code": "ROUTING_ERROR",
                        "message": error.details,
                    },
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        if not route_result or "routes" not in route_result:
            return Response(
                {
                    "request_id": request_id,
                    "error": {
                        "code": "NO_ROUTES_FOUND",
                        "message": "No routes found between the specified locations.",
                    },
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        alternatives = []
        for route in route_result.get("routes", []):
            if route.get("found"):
                alternatives.append(
                    {
                        "type": route.get("type"),
                        "totalDurationSeconds": route.get("totalDurationSeconds"),
                        "totalDurationFormatted": route.get("totalDurationFormatted"),
                        "totalSegments": route.get("totalSegments"),
                        "totalDistanceMeters": route.get("totalDistanceMeters"),
                        "segments": route.get("segments", []),
                    }
                )

        if not alternatives:
            return Response(
                {
                    "request_id": request_id,
                    "error": {
                        "code": "NO_ROUTES_FOUND",
                        "message": "No viable route alternatives found.",
                    },
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        alternatives.sort(key=lambda r: r.get("totalDurationSeconds", 10**9))

        return Response(
            {
                "request_id": request_id,
                "query": route_result.get("query"),
                "alternatives": alternatives,
                "count": len(alternatives),
            }
        )


class RouteFeedbackView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Routing"],
        summary="Submit route feedback",
        description="Submit a rating (1-5) and optional comment for a completed route.",
        request=inline_serializer(
            name="RouteFeedbackRequest",
            fields={
                "request_id": serializers.CharField(),
                "rating": serializers.IntegerField(
                    min_value=1,
                    max_value=5,
                    help_text="Rating from 1 (poor) to 5 (excellent)",
                ),
                "comment": serializers.CharField(required=False, default=""),
            },
        ),
        responses={
            201: None,
            400: OpenApiResponse(response=serializers.DictField),
        },
        examples=[
            OpenApiExample(
                "Feedback Request",
                value={
                    "request_id": "a1b2c3d4-...",
                    "rating": 4,
                    "comment": "Route was accurate, slight delay at transfer.",
                },
                request_only=True,
            ),
        ],
    )
    def post(self, request):
        request_id = request.data.get("request_id")
        rating = request.data.get("rating")
        comment = request.data.get("comment", "")

        if not request_id:
            return Response(
                {"error": "request_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            rating = int(rating)
            if rating < 1 or rating > 5:
                raise ValueError
        except (TypeError, ValueError):
            return Response(
                {"error": "rating must be an integer between 1 and 5."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        existing = RouteFeedback.objects.filter(
            user=request.user, request_id=request_id
        ).first()
        if existing:
            existing.rating = rating
            existing.comment = comment
            existing.save()
            return Response(
                {
                    "message": "Feedback updated.",
                    "request_id": request_id,
                    "rating": existing.rating,
                }
            )

        feedback = RouteFeedback.objects.create(
            user=request.user,
            request_id=request_id,
            rating=rating,
            comment=comment,
        )
        return Response(
            {
                "message": "Feedback submitted.",
                "request_id": feedback.request_id,
                "rating": feedback.rating,
            },
            status=status.HTTP_201_CREATED,
        )
