from dataclasses import dataclass
from src.Core.Application.Common.Interfaces.CQRS import ICommand
from src.Core.Application.Common.Models.Result import Result
from src.Core.Domain.Errors.DomainErrors import AuthErrors


@dataclass
class ChangePasswordCommand(ICommand):
    user_id: int
    current_password: str
    new_password: str


class ChangePasswordCommandHandler:
    def handle(self, command: ChangePasswordCommand) -> Result:
        from src.Infrastructure.Identity.models import User

        try:
            user = User.objects.get(pk=command.user_id)
        except User.DoesNotExist:
            return Result.failure(AuthErrors.InvalidCredentials)

        if not user.check_password(command.current_password):
            return Result.failure(AuthErrors.InvalidCredentials)

        user.set_password(command.new_password)
        user.save()
        return Result.success()
