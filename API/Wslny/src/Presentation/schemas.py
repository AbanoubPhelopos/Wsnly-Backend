from rest_framework import serializers


ROUTE_FILTER_ENUM_CHOICES = [
    (1, "optimal"),
    (2, "fastest"),
    (3, "cheapest"),
    (4, "bus_only"),
    (5, "microbus_only"),
    (6, "metro_only"),
]
FILTER_ENUM_TO_PREFERENCE = {value: name for value, name in ROUTE_FILTER_ENUM_CHOICES}
FILTER_PREFERENCE_TO_ENUM = {name: value for value, name in ROUTE_FILTER_ENUM_CHOICES}
ROUTE_FILTER_HELP_TEXT = (
    "Route filter enum: 1=optimal, 2=fastest, 3=cheapest, "
    "4=bus_only, 5=microbus_only, 6=metro_only"
)


class CoordinateSerializer(serializers.Serializer):
    lat = serializers.FloatField()
    lon = serializers.FloatField()


class RouteRequestSerializer(serializers.Serializer):
    text = serializers.CharField(required=False)
    origin = CoordinateSerializer(required=False)
    destination = CoordinateSerializer(required=False)
    current_location = CoordinateSerializer(required=False, allow_null=True)
    filter = serializers.ChoiceField(
        choices=ROUTE_FILTER_ENUM_CHOICES,
        required=False,
        default=1,
        help_text=ROUTE_FILTER_HELP_TEXT,
    )


class RouteQueryPointSerializer(serializers.Serializer):
    lat = serializers.FloatField()
    lon = serializers.FloatField()


class RouteQuerySerializer(serializers.Serializer):
    origin = RouteQueryPointSerializer()
    destination = RouteQueryPointSerializer()


class RouteOptionSegmentLocationSerializer(serializers.Serializer):
    lat = serializers.FloatField()
    lon = serializers.FloatField()
    name = serializers.CharField()


class PolylinePointSerializer(serializers.Serializer):
    lat = serializers.FloatField()
    lon = serializers.FloatField()


class RouteOptionSegmentSerializer(serializers.Serializer):
    startLocation = RouteOptionSegmentLocationSerializer()
    endLocation = RouteOptionSegmentLocationSerializer()
    method = serializers.CharField()
    numStops = serializers.IntegerField()
    distanceMeters = serializers.IntegerField()
    durationSeconds = serializers.IntegerField()
    polyline = PolylinePointSerializer(many=True, required=False, default=[])


class RouteOptionSerializer(serializers.Serializer):
    type = serializers.CharField(
        help_text=(
            "Selected route label. For filtered responses, this matches the "
            "requested filter name (optimal, fastest, cheapest, bus_only, "
            "microbus_only, metro_only)."
        )
    )
    found = serializers.BooleanField()
    totalDurationSeconds = serializers.IntegerField()
    totalDurationFormatted = serializers.CharField()
    totalSegments = serializers.IntegerField()
    totalDistanceMeters = serializers.FloatField()
    segments = RouteOptionSegmentSerializer(many=True)
    estimatedFare = serializers.FloatField(required=False, allow_null=True)
    walkDistanceMeters = serializers.FloatField(required=False, allow_null=True)


class RouteSuccessResponseSerializer(serializers.Serializer):
    request_id = serializers.UUIDField()
    source = serializers.ChoiceField(choices=["text", "map"])
    intent = serializers.CharField()
    filter = serializers.ChoiceField(
        choices=ROUTE_FILTER_ENUM_CHOICES,
        help_text=ROUTE_FILTER_HELP_TEXT,
    )
    from_name = serializers.CharField(allow_null=True, required=False)
    to_name = serializers.CharField(allow_null=True, required=False)
    query = RouteQuerySerializer()
    route = RouteOptionSerializer(required=False, allow_null=True)


class ErrorBodySerializer(serializers.Serializer):
    code = serializers.CharField()
    message = serializers.CharField()


class RouteErrorResponseSerializer(serializers.Serializer):
    request_id = serializers.UUIDField()
    error = ErrorBodySerializer()


class RegisterRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    mobile_number = serializers.CharField()
    gender = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    address = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    role = serializers.CharField(required=False)


class LoginRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()


class GoogleLoginRequestSerializer(serializers.Serializer):
    id_token = serializers.CharField()


class AuthUserSerializer(serializers.Serializer):
    email = serializers.EmailField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()


class AuthSuccessResponseSerializer(serializers.Serializer):
    token = serializers.CharField()
    refresh_token = serializers.CharField()
    user = AuthUserSerializer()


class ValidationErrorsResponseSerializer(serializers.Serializer):
    errors = serializers.ListField(child=serializers.DictField())


class MessageResponseSerializer(serializers.Serializer):
    message = serializers.CharField()


class ChangeUserRoleRequestSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    new_role = serializers.CharField()


class UserSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False)
    email = serializers.EmailField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    mobile_number = serializers.CharField(required=False)
    role = serializers.CharField(required=False)


class RouteHistoryItemSerializer(serializers.Serializer):
    request_id = serializers.CharField(allow_null=True)
    source_type = serializers.CharField()
    input_text = serializers.CharField(allow_null=True)
    filter = serializers.CharField(source="preference")
    selected_route_type = serializers.CharField(allow_null=True)
    origin_name = serializers.CharField(allow_null=True)
    destination_name = serializers.CharField(allow_null=True)
    status = serializers.CharField()
    error_code = serializers.CharField(allow_null=True)
    total_distance_meters = serializers.FloatField(allow_null=True)
    total_duration_seconds = serializers.FloatField(allow_null=True)
    estimated_fare = serializers.FloatField(allow_null=True)
    walk_distance_meters = serializers.FloatField(allow_null=True)
    created_at = serializers.DateTimeField()
