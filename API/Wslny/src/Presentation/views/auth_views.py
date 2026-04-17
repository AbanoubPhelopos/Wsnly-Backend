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

        return Response(
            {"errors": [vars(e) for e in result.errors]},
            status=status.HTTP_400_BAD_REQUEST,
        )


class LoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Auth"],
        summary="Login user",
        request=LoginRequestSerializer,
        responses={
            200: OpenApiResponse(response=AuthSuccessResponseSerializer),
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

        return Response(
            {"errors": [vars(e) for e in result.errors]},
            status=status.HTTP_401_UNAUTHORIZED,
        )


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

        return Response(
            {"errors": [vars(e) for e in result.errors]},
            status=status.HTTP_400_BAD_REQUEST,
        )


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

        return Response(
            {"errors": [vars(e) for e in result.errors]},
            status=status.HTTP_404_NOT_FOUND,
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

        return Response(
            {"errors": [vars(e) for e in result.errors]},
            status=status.HTTP_400_BAD_REQUEST,
        )
