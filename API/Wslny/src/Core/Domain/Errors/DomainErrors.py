from src.Core.Application.Common.Models.Result import Error

class AuthErrors:
    InvalidCredentials = Error("Auth.InvalidCredentials", "Invalid email or password.")
    InvalidEmail = Error("Auth.InvalidEmail", "Invalid email format.")
    GoogleTokenInvalid = Error("Auth.GoogleTokenInvalid", "Invalid Google ID token.")
    GoogleAuthFailed = Error("Auth.GoogleAuthFailed", "Google authentication failed.")
    UserExists = Error("Auth.UserExists", "User with this email already exists.")
    MissingFields = Error(
        "Auth.MissingFields",
        "email, password, first_name, last_name, and mobile_number are required.",
    )
    MissingLoginFields = Error(
        "Auth.MissingFields", "email and password are required."
    )
    WeakPassword = Error(
        "Auth.WeakPassword",
        "Password must be at least 8 characters and contain a digit and a letter.",
    )

class UserErrors:
    NotFound = Error("User.NotFound", "User not found.")
    InvalidRole = Error("User.InvalidRole", "Invalid role specified.")
    Unauthorized = Error("User.Unauthorized", "You are not authorized to perform this action.")
