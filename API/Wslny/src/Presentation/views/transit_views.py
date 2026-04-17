from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from django.conf import settings

from src.Core.Application.Transit.GtfsDataService import (
    get_nearby_stops,
    get_stop_detail,
    get_all_lines,
    get_line_detail,
)


class NearbyStopsView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Transit"],
        summary="Find stops near a location",
        description="Returns transit stops within a given radius of the specified coordinates, along with lines served at each stop.",
        parameters=[
            OpenApiParameter(
                name="lat",
                type=OpenApiTypes.FLOAT,
                location=OpenApiParameter.QUERY,
                required=True,
                description="Latitude of the search center",
            ),
            OpenApiParameter(
                name="lon",
                type=OpenApiTypes.FLOAT,
                location=OpenApiParameter.QUERY,
                required=True,
                description="Longitude of the search center",
            ),
            OpenApiParameter(
                name="radius",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=False,
                default=500,
                description="Search radius in meters (default: 500, max: 2000)",
            ),
        ],
        responses={200: None},
    )
    def get(self, request):
        try:
            lat = float(request.query_params.get("lat"))
            lon = float(request.query_params.get("lon"))
        except (TypeError, ValueError):
            return Response(
                {
                    "error": "lat and lon query parameters are required and must be numbers."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        radius = 500
        try:
            radius = int(request.query_params.get("radius", 500))
        except (TypeError, ValueError):
            pass
        radius = min(max(radius, 50), 2000)

        if not settings.GTFS_PATH:
            return Response(
                {"error": "Transit data not configured."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        stops = get_nearby_stops(lat, lon, radius)
        return Response({"stops": stops, "count": len(stops)})


class StopDetailView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Transit"],
        summary="Get stop details",
        description="Returns details for a specific stop including all lines/routes passing through it.",
        responses={200: None, 404: None},
    )
    def get(self, request, stop_id):
        if not settings.GTFS_PATH:
            return Response(
                {"error": "Transit data not configured."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        stop = get_stop_detail(stop_id)
        if stop is None:
            return Response(
                {"error": f"Stop '{stop_id}' not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(stop)


class LinesView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Transit"],
        summary="List all transport lines",
        description="Returns all transport lines/routes with their type and metadata.",
        responses={200: None},
    )
    def get(self, request):
        if not settings.GTFS_PATH:
            return Response(
                {"error": "Transit data not configured."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        lines = get_all_lines()
        return Response({"lines": lines, "count": len(lines)})


class LineDetailView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Transit"],
        summary="Get line details",
        description="Returns details for a specific line including all stops in order and the route polyline.",
        responses={200: None, 404: None},
    )
    def get(self, request, route_id):
        if not settings.GTFS_PATH:
            return Response(
                {"error": "Transit data not configured."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        line = get_line_detail(route_id)
        if line is None:
            return Response(
                {"error": f"Line '{route_id}' not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(line)
