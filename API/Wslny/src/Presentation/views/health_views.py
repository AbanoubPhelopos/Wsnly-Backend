from django.db import connection
from django.http import JsonResponse
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from src.Infrastructure.GrpcClients import get_ai_client, get_routing_client


class HealthView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        tags=["System"],
        summary="Health check",
        description="Returns service readiness status for database and gRPC dependencies.",
        responses={200: None, 503: None},
    )
    def get(self, request):
        checks = {}
        overall_healthy = True

        try:
            connection.ensure_connection()
            checks["database"] = "healthy"
        except Exception as exc:
            checks["database"] = f"unhealthy: {exc}"
            overall_healthy = False

        ai_client, ai_error = get_ai_client()
        if ai_client is not None:
            checks["ai_service"] = "healthy"
        else:
            checks["ai_service"] = f"unhealthy: {ai_error or 'not initialized'}"
            overall_healthy = False

        routing_client, routing_error = get_routing_client()
        if routing_client is not None:
            checks["routing_engine"] = "healthy"
        else:
            checks["routing_engine"] = (
                f"unhealthy: {routing_error or 'not initialized'}"
            )
            overall_healthy = False

        status_code = 200 if overall_healthy else 503
        return JsonResponse(
            {"status": "healthy" if overall_healthy else "degraded", "checks": checks},
            status=status_code,
        )
