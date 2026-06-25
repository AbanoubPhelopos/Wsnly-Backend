from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers
from rest_framework.permissions import IsAuthenticated, AllowAny
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiResponse,
    extend_schema,
    inline_serializer,
)
from src.Core.Domain.Constants.Roles import Roles

from src.Core.Application.Authentication.Commands.RegisterCommand import (
    RegisterCommand,
    RegisterCommandHandler,
)
from src.Core.Application.Authentication.Commands.LoginCommand import (
    LoginCommand,
    LoginCommandHandler,
)
from src.Core.Application.Authentication.Commands.GoogleLoginCommand import (
    GoogleLoginCommand,
    GoogleLoginCommandHandler,
)
from src.Core.Application.Authentication.Commands.ChangePasswordCommand import (
    ChangePasswordCommand,
    ChangePasswordCommandHandler,
)
from src.Core.Application.Authentication.Queries.GetProfileQuery import (
    GetProfileQuery,
    GetProfileQueryHandler,
)
from src.Presentation.schemas import (
    AuthSuccessResponseSerializer,
    GoogleLoginRequestSerializer,
    LoginRequestSerializer,
    RegisterRequestSerializer,
    ValidationErrorsResponseSerializer,
    MessageResponseSerializer,
)


# Map domain-error codes to HTTP status codes. Anything we don't know
# falls back to 400 (it means the request itself is malformed, even if
# we couldn't pinpoint exactly why).
_ERROR_STATUS_MAP = {
    "Auth.MissingFields": status.HTTP_400_BAD_REQUEST,
    "Auth.InvalidEmail": status.HTTP_400_BAD_REQUEST,
    "Auth.WeakPassword": status.HTTP_400_BAD_REQUEST,
    "Auth.InvalidCredentials": status.HTTP_401_UNAUTHORIZED,
    "Auth.UserExists": status.HTTP_409_CONFLICT,
    "Auth.GoogleTokenInvalid": status.HTTP_400_BAD_REQUEST,
    "Auth.GoogleAuthFailed": status.HTTP_400_BAD_REQUEST,
    "User.NotFound": status.HTTP_404_NOT_FOUND,
    "User.InvalidRole": status.HTTP_400_BAD_REQUEST,
}


def _errors_to_response(errors):
    """Translate a list of domain ``Error`` objects into a DRF Response
    with a consistent HTTP status code based on the error code prefix.
    """
    payload = {"errors": [{"code": e.code, "message": e.message} for e in errors]}
    status_code = status.HTTP_400_BAD_REQUEST
    if errors:
        status_code = _ERROR_STATUS_MAP.get(
            errors[0].code, status.HTTP_400_BAD_REQUEST
        )
    return Response(payload, status=status_code)


class RegisterView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Auth"],
        summary="Register user",
        request=RegisterRequestSerializer,
        responses={
            201: OpenApiResponse(response=AuthSuccessResponseSerializer),
            400: OpenApiResponse(response=ValidationErrorsResponseSerializer),
        },
        examples=[
            OpenApiExample(
                "Register Request",
                value={
                    "email": "user@example.com",
                    "password": "StrongPass123!",
                    "first_name": "Ali",
                    "last_name": "Hassan",
                    "mobile_number": "01000000000",
                    "gender": "male",
                    "address": "Cairo",
                },
                request_only=True,
            )
        ],
    )
    def post(self, request):
        command = RegisterCommand(
            email=request.data.get("email"),
            password=request.data.get("password"),
            first_name=request.data.get("first_name"),
            last_name=request.data.get("last_name"),
            mobile_number=request.data.get("mobile_number"),
            gender=request.data.get("gender"),
            address=request.data.get("address"),
            role=request.data.get("role", Roles.USER),
        )

        handler = RegisterCommandHandler()
        result = handler.handle(command)

        if result.is_success:
            return Response(
                {
                    "token": result.data.token,
                    "refresh_token": result.data.refresh_token,
                    "user": {
                        "email": result.data.user.email,
                        "first_name": result.data.user.first_name,
                        "last_name": result.data.user.last_name,
                    },
                },
                status=status.HTTP_201_CREATED,
            )

        return _errors_to_response(result.errors)


class LoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Auth"],
        summary="Login user",
        request=LoginRequestSerializer,
        responses={
            200: OpenApiResponse(response=AuthSuccessResponseSerializer),
            400: OpenApiResponse(response=ValidationErrorsResponseSerializer),
            401: OpenApiResponse(response=ValidationErrorsResponseSerializer),
        },
        examples=[
            OpenApiExample(
                "Login Request",
                value={
                    "email": "user@example.com",
                    "password": "StrongPass123!",
                },
                request_only=True,
            )
        ],
    )
    def post(self, request):
        command = LoginCommand(
            email=request.data.get("email"), password=request.data.get("password")
        )

        handler = LoginCommandHandler()
        result = handler.handle(command)

        if result.is_success:
            return Response(
                {
                    "token": result.data.token,
                    "refresh_token": result.data.refresh_token,
                    "user": {
                        "email": result.data.user.email,
                        "first_name": result.data.user.first_name,
                        "last_name": result.data.user.last_name,
                    },
                },
                status=status.HTTP_200_OK,
            )

        return _errors_to_response(result.errors)


class GoogleLoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Auth"],
        summary="Login with Google",
        request=GoogleLoginRequestSerializer,
        responses={
            200: OpenApiResponse(response=AuthSuccessResponseSerializer),
            400: OpenApiResponse(response=ValidationErrorsResponseSerializer),
        },
        examples=[
            OpenApiExample(
                "Google Login Request",
                value={"id_token": "google-id-token"},
                request_only=True,
            )
        ],
    )
    def post(self, request):
        command = GoogleLoginCommand(id_token=request.data.get("id_token"))
        handler = GoogleLoginCommandHandler()
        result = handler.handle(command)

        if result.is_success:
            return Response(
                {
                    "token": result.data.token,
                    "refresh_token": result.data.refresh_token,
                    "user": {
                        "email": result.data.user.email,
                        "first_name": result.data.user.first_name,
                        "last_name": result.data.user.last_name,
                    },
                },
                status=status.HTTP_200_OK,
            )

        return _errors_to_response(result.errors)


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Auth"],
        summary="Get user profile",
        responses={200: OpenApiResponse(description="Profile data")},
    )
    def get(self, request):
        query = GetProfileQuery(user_id=request.user.id)
        handler = GetProfileQueryHandler()
        result = handler.handle(query)

        if result.is_success:
            return Response(vars(result.data), status=status.HTTP_200_OK)

        return _errors_to_response(result.errors)

    @extend_schema(
        tags=["Auth"],
        summary="Update user profile",
        request=inline_serializer(
            name="UpdateProfileRequest",
            fields={
                "first_name": serializers.CharField(required=False),
                "last_name": serializers.CharField(required=False),
                "mobile_number": serializers.CharField(required=False),
                "gender": serializers.CharField(
                    required=False, allow_null=True, allow_blank=True
                ),
                "address": serializers.CharField(
                    required=False, allow_null=True, allow_blank=True
                ),
            },
        ),
        responses={200: None, 400: None},
    )
    def put(self, request):
        user = request.user
        updated_fields = []

        if "first_name" in request.data:
            user.first_name = request.data["first_name"]
            updated_fields.append("first_name")
        if "last_name" in request.data:
            user.last_name = request.data["last_name"]
            updated_fields.append("last_name")
        if "mobile_number" in request.data:
            user.mobile_number = request.data["mobile_number"]
            updated_fields.append("mobile_number")
        if "gender" in request.data:
            user.gender = request.data["gender"]
            updated_fields.append("gender")
        if "address" in request.data:
            user.address = request.data["address"]
            updated_fields.append("address")

        if not updated_fields:
            return Response(
                {"error": "No fields to update."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.save()
        return Response(
            {
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "mobile_number": user.mobile_number,
                "gender": user.gender,
                "address": user.address,
                "role": user.role,
            }
        )


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Auth"],
        summary="Change password",
        request=inline_serializer(
            name="ChangePasswordRequest",
            fields={
                "current_password": serializers.CharField(),
                "new_password": serializers.CharField(),
            },
        ),
        responses={
            200: OpenApiResponse(response=MessageResponseSerializer),
            400: OpenApiResponse(response=ValidationErrorsResponseSerializer),
            401: OpenApiResponse(response=ValidationErrorsResponseSerializer),
        },
        examples=[
            OpenApiExample(
                "Change Password Request",
                value={
                    "current_password": "OldPass123!",
                    "new_password": "NewPass456!",
                },
                request_only=True,
            ),
        ],
    )
    def post(self, request):
        current_password = request.data.get("current_password")
        new_password = request.data.get("new_password")

        if not current_password or not new_password:
            return Response(
                {
                    "errors": [
                        {
                            "code": "Auth.MissingFields",
                            "message": "current_password and new_password are required.",
                        }
                    ]
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        command = ChangePasswordCommand(
            user_id=request.user.id,
            current_password=current_password,
            new_password=new_password,
        )
        handler = ChangePasswordCommandHandler()
        result = handler.handle(command)

        if result.is_success:
            return Response(
                {"message": "Password changed successfully."},
                status=status.HTTP_200_OK,
            )

        return _errors_to_response(result.errors)
