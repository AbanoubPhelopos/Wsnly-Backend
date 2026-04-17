from django.db import transaction
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

from src.Infrastructure.Identity.models import (
    SavedLocation,
    FavoriteRoute,
    UserPreferences,
)
from src.Presentation.schemas import MessageResponseSerializer


class SavedLocationsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["User"],
        summary="List saved locations",
        responses={200: None},
    )
    def get(self, request):
        locations = SavedLocation.objects.filter(user=request.user)
        data = [
            {
                "id": loc.id,
                "name": loc.name,
                "lat": loc.lat,
                "lon": loc.lon,
                "type": loc.type,
                "created_at": loc.created_at,
            }
            for loc in locations
        ]
        return Response({"locations": data, "count": len(data)})

    @extend_schema(
        tags=["User"],
        summary="Create saved location",
        request=inline_serializer(
            name="CreateSavedLocationRequest",
            fields={
                "name": serializers.CharField(),
                "lat": serializers.FloatField(),
                "lon": serializers.FloatField(),
                "type": serializers.ChoiceField(
                    choices=["home", "work", "custom"],
                    default="custom",
                ),
            },
        ),
        responses={
            201: None,
            400: OpenApiResponse(response=serializers.DictField),
        },
        examples=[
            OpenApiExample(
                "Save Location",
                value={
                    "name": "Home",
                    "lat": 30.05,
                    "lon": 31.24,
                    "type": "home",
                },
                request_only=True,
            ),
        ],
    )
    def post(self, request):
        name = request.data.get("name")
        try:
            lat = float(request.data.get("lat"))
            lon = float(request.data.get("lon"))
        except (TypeError, ValueError):
            return Response(
                {"error": "lat and lon must be valid numbers."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not name:
            return Response(
                {"error": "name is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        loc_type = request.data.get("type", "custom")
        if loc_type not in ("home", "work", "custom"):
            return Response(
                {"error": "type must be home, work, or custom."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        loc = SavedLocation.objects.create(
            user=request.user,
            name=name,
            lat=lat,
            lon=lon,
            type=loc_type,
        )
        return Response(
            {
                "id": loc.id,
                "name": loc.name,
                "lat": loc.lat,
                "lon": loc.lon,
                "type": loc.type,
            },
            status=status.HTTP_201_CREATED,
        )


class SavedLocationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["User"],
        summary="Update saved location",
        request=inline_serializer(
            name="UpdateSavedLocationRequest",
            fields={
                "name": serializers.CharField(required=False),
                "lat": serializers.FloatField(required=False),
                "lon": serializers.FloatField(required=False),
                "type": serializers.ChoiceField(
                    choices=["home", "work", "custom"],
                    required=False,
                ),
            },
        ),
        responses={200: None, 404: None},
    )
    def put(self, request, pk):
        try:
            loc = SavedLocation.objects.get(pk=pk, user=request.user)
        except SavedLocation.DoesNotExist:
            return Response(
                {"error": "Saved location not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if "name" in request.data:
            loc.name = request.data["name"]
        if "lat" in request.data:
            try:
                loc.lat = float(request.data["lat"])
            except (TypeError, ValueError):
                return Response(
                    {"error": "lat must be a valid number."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        if "lon" in request.data:
            try:
                loc.lon = float(request.data["lon"])
            except (TypeError, ValueError):
                return Response(
                    {"error": "lon must be a valid number."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        if "type" in request.data:
            if request.data["type"] not in ("home", "work", "custom"):
                return Response(
                    {"error": "type must be home, work, or custom."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            loc.type = request.data["type"]

        loc.save()
        return Response(
            {
                "id": loc.id,
                "name": loc.name,
                "lat": loc.lat,
                "lon": loc.lon,
                "type": loc.type,
            }
        )

    @extend_schema(
        tags=["User"],
        summary="Delete saved location",
        responses={200: None, 404: None},
    )
    def delete(self, request, pk):
        try:
            loc = SavedLocation.objects.get(pk=pk, user=request.user)
        except SavedLocation.DoesNotExist:
            return Response(
                {"error": "Saved location not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        loc.delete()
        return Response({"message": "Saved location deleted."})


class FavoriteRoutesView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["User"],
        summary="List favorite routes",
        responses={200: None},
    )
    def get(self, request):
        favorites = FavoriteRoute.objects.filter(user=request.user)
        data = [
            {
                "id": fav.id,
                "name": fav.name,
                "origin": {
                    "lat": fav.origin_lat,
                    "lon": fav.origin_lon,
                    "name": fav.origin_name,
                },
                "destination": {
                    "lat": fav.destination_lat,
                    "lon": fav.destination_lon,
                    "name": fav.destination_name,
                },
                "filter": fav.route_filter,
                "created_at": fav.created_at,
            }
            for fav in favorites
        ]
        return Response({"favorites": data, "count": len(data)})

    @extend_schema(
        tags=["User"],
        summary="Save a route as favorite",
        request=inline_serializer(
            name="CreateFavoriteRouteRequest",
            fields={
                "name": serializers.CharField(),
                "origin_lat": serializers.FloatField(),
                "origin_lon": serializers.FloatField(),
                "origin_name": serializers.CharField(required=False, default=""),
                "destination_lat": serializers.FloatField(),
                "destination_lon": serializers.FloatField(),
                "destination_name": serializers.CharField(required=False, default=""),
                "filter": serializers.IntegerField(required=False, default=1),
            },
        ),
        responses={201: None, 400: None},
        examples=[
            OpenApiExample(
                "Save Favorite",
                value={
                    "name": "Home to Work",
                    "origin_lat": 30.05,
                    "origin_lon": 31.24,
                    "origin_name": "Home",
                    "destination_lat": 30.07,
                    "destination_lon": 31.28,
                    "destination_name": "Work",
                    "filter": 1,
                },
                request_only=True,
            ),
        ],
    )
    def post(self, request):
        name = request.data.get("name")
        if not name:
            return Response(
                {"error": "name is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            origin_lat = float(request.data.get("origin_lat"))
            origin_lon = float(request.data.get("origin_lon"))
            dest_lat = float(request.data.get("destination_lat"))
            dest_lon = float(request.data.get("destination_lon"))
        except (TypeError, ValueError):
            return Response(
                {
                    "error": "origin_lat, origin_lon, destination_lat, destination_lon must be valid numbers."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        fav = FavoriteRoute.objects.create(
            user=request.user,
            name=name,
            origin_lat=origin_lat,
            origin_lon=origin_lon,
            origin_name=request.data.get("origin_name", ""),
            destination_lat=dest_lat,
            destination_lon=dest_lon,
            destination_name=request.data.get("destination_name", ""),
            route_filter=request.data.get("filter", 1),
        )
        return Response(
            {
                "id": fav.id,
                "name": fav.name,
                "origin": {
                    "lat": fav.origin_lat,
                    "lon": fav.origin_lon,
                    "name": fav.origin_name,
                },
                "destination": {
                    "lat": fav.destination_lat,
                    "lon": fav.destination_lon,
                    "name": fav.destination_name,
                },
                "filter": fav.route_filter,
            },
            status=status.HTTP_201_CREATED,
        )


class FavoriteRouteDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["User"],
        summary="Remove favorite route",
        responses={200: None, 404: None},
    )
    def delete(self, request, pk):
        try:
            fav = FavoriteRoute.objects.get(pk=pk, user=request.user)
        except FavoriteRoute.DoesNotExist:
            return Response(
                {"error": "Favorite route not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        fav.delete()
        return Response({"message": "Favorite route removed."})


class UserPreferencesView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["User"],
        summary="Get user preferences",
        responses={200: None},
    )
    def get(self, request):
        prefs, _ = UserPreferences.objects.get_or_create(
            user=request.user,
            defaults={
                "default_filter": 1,
                "max_walk_distance": 1500,
                "accessibility_mode": False,
            },
        )
        return Response(
            {
                "default_filter": prefs.default_filter,
                "max_walk_distance": prefs.max_walk_distance,
                "accessibility_mode": prefs.accessibility_mode,
            }
        )

    @extend_schema(
        tags=["User"],
        summary="Update user preferences",
        request=inline_serializer(
            name="UpdatePreferencesRequest",
            fields={
                "default_filter": serializers.IntegerField(required=False),
                "max_walk_distance": serializers.IntegerField(required=False),
                "accessibility_mode": serializers.BooleanField(required=False),
            },
        ),
        responses={200: None},
    )
    def put(self, request):
        prefs, _ = UserPreferences.objects.get_or_create(
            user=request.user,
            defaults={
                "default_filter": 1,
                "max_walk_distance": 1500,
                "accessibility_mode": False,
            },
        )

        if "default_filter" in request.data:
            try:
                prefs.default_filter = int(request.data["default_filter"])
            except (TypeError, ValueError):
                return Response(
                    {"error": "default_filter must be an integer."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if "max_walk_distance" in request.data:
            try:
                prefs.max_walk_distance = int(request.data["max_walk_distance"])
            except (TypeError, ValueError):
                return Response(
                    {"error": "max_walk_distance must be an integer."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if "accessibility_mode" in request.data:
            prefs.accessibility_mode = bool(request.data["accessibility_mode"])

        prefs.save()
        return Response(
            {
                "default_filter": prefs.default_filter,
                "max_walk_distance": prefs.max_walk_distance,
                "accessibility_mode": prefs.accessibility_mode,
            }
        )
