from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List

from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

from src.Core.Application.Authentication.Common.AuthenticationResult import (
    AuthenticationResult,
)
from src.Core.Application.Common.Interfaces.CQRS import ICommand
from src.Core.Application.Common.Models.Result import Error, Result
from src.Core.Domain.Constants.Roles import Roles
from src.Core.Domain.Errors.DomainErrors import AuthErrors

User = get_user_model()

# Conservative RFC-5322 subset that's also what Django's EmailValidator
# accepts. We intentionally don't try to be more permissive than the
# ORM — we'd rather give a clear 400 than a 500 IntegrityError later.
_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
_PASSWORD_MIN_LENGTH = 8


def _missing_required_fields(command: "RegisterCommand") -> List[str]:
    missing: List[str] = []
    for field_name in (
        "email",
        "password",
        "first_name",
        "last_name",
        "mobile_number",
    ):
        value = getattr(command, field_name, None)
        if value is None or (isinstance(value, str) and not value.strip()):
            missing.append(field_name)
    return missing


def _is_valid_email(value: str) -> bool:
    return bool(value) and bool(_EMAIL_RE.match(value))


def _is_strong_password(value: str) -> bool:
    if not value or len(value) < _PASSWORD_MIN_LENGTH:
        return False
    has_letter = any(ch.isalpha() for ch in value)
    has_digit = any(ch.isdigit() for ch in value)
    return has_letter and has_digit


@dataclass
class RegisterCommand(ICommand):
    email: str
    password: str
    first_name: str
    last_name: str
    mobile_number: str
    gender: str = None
    address: str = None
    role: str = Roles.USER


class RegisterCommandHandler:
    def handle(self, command: RegisterCommand) -> Result[AuthenticationResult]:
        missing = _missing_required_fields(command)
        if missing:
            return Result.failure(AuthErrors.MissingFields)

        email = (command.email or "").strip()
        if not _is_valid_email(email):
            return Result.failure(AuthErrors.InvalidEmail)

        password = command.password or ""
        if not _is_strong_password(password):
            return Result.failure(AuthErrors.WeakPassword)

        if User.objects.filter(email=email).exists():
            return Result.failure(AuthErrors.UserExists)

        user = User.objects.create_user(
            email=email,
            password=password,
            first_name=command.first_name.strip(),
            last_name=command.last_name.strip(),
            mobile_number=command.mobile_number.strip(),
            gender=command.gender,
            address=command.address,
            role=command.role,
        )

        refresh = RefreshToken.for_user(user)

        return Result.success(
            AuthenticationResult(
                user=user,
                token=str(refresh.access_token),
                refresh_token=str(refresh),
            )
        )
