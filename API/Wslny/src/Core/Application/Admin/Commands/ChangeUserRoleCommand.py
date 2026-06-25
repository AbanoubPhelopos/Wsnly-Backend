from __future__ import annotations

from dataclasses import dataclass

from django.contrib.auth import get_user_model

from src.Core.Application.Common.Interfaces.CQRS import ICommand
from src.Core.Application.Common.Models.Result import Error, Result
from src.Core.Domain.Constants.Roles import Roles
from src.Core.Domain.Errors.DomainErrors import UserErrors

User = get_user_model()


@dataclass
class ChangeUserRoleCommand(ICommand):
    user_id: int
    new_role: str


class ChangeUserRoleCommandHandler:
    # Map incoming role strings (case-insensitive, accept the legacy
    # lowercase form produced by earlier migrations and the canonical
    # capitalized form stored in ``Roles``).
    _ROLE_ALIASES = {
        "admin": Roles.ADMIN,
        "user": Roles.USER,
        Roles.ADMIN.lower(): Roles.ADMIN,
        Roles.USER.lower(): Roles.USER,
    }

    @staticmethod
    def _coerce_user_id(raw):
        if raw is None or raw == "":
            return None
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None

    def handle(self, command: ChangeUserRoleCommand) -> Result[bool]:
        normalized = (command.new_role or "").strip()
        canonical = self._ROLE_ALIASES.get(normalized.lower())
        if canonical is None:
            return Result.failure(UserErrors.InvalidRole)

        user_id = self._coerce_user_id(command.user_id)
        if user_id is None:
            return Result.failure(
                Error(
                    "Auth.MissingFields",
                    "user_id is required and must be an integer.",
                )
            )

        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Result.failure(UserErrors.NotFound)

        user.role = canonical

        # Update permissions based on role if needed
        if canonical == Roles.ADMIN:
            user.is_staff = True
            user.is_superuser = True
        else:
            user.is_staff = False
            user.is_superuser = False

        user.save()
        return Result.success(True)
