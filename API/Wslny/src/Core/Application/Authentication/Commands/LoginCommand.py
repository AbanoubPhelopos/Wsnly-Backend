from __future__ import annotations

import re
from dataclasses import dataclass

from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken

from src.Core.Application.Authentication.Common.AuthenticationResult import (
    AuthenticationResult,
)
from src.Core.Application.Common.Interfaces.CQRS import ICommand
from src.Core.Application.Common.Models.Result import Result
from src.Core.Domain.Errors.DomainErrors import AuthErrors

_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")


@dataclass
class LoginCommand(ICommand):
    email: str
    password: str


class LoginCommandHandler:
    def handle(self, command: LoginCommand) -> Result[AuthenticationResult]:
        email = (command.email or "").strip()
        password = command.password or ""

        if not email or not password:
            return Result.failure(AuthErrors.MissingLoginFields)

        if not _EMAIL_RE.match(email):
            return Result.failure(AuthErrors.InvalidEmail)

        user = authenticate(email=email, password=password)

        if user is None:
            return Result.failure(AuthErrors.InvalidCredentials)

        refresh = RefreshToken.for_user(user)

        return Result.success(
            AuthenticationResult(
                user=user,
                token=str(refresh.access_token),
                refresh_token=str(refresh),
            )
        )
