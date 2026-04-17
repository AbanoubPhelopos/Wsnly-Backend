from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models
from django.utils.translation import gettext_lazy as _
from src.Core.Domain.Constants.Roles import Roles


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_("The Email field must be set"))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", Roles.ADMIN)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = (
        (Roles.ADMIN, "Admin"),
        (Roles.USER, "User"),
    )

    email = models.EmailField(_("email address"), unique=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    mobile_number = models.CharField(max_length=20)
    gender = models.CharField(max_length=10, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=Roles.USER)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name", "mobile_number"]

    def __str__(self):
        return self.email


class SavedLocation(models.Model):
    TYPE_HOME = "home"
    TYPE_WORK = "work"
    TYPE_CUSTOM = "custom"
    TYPE_CHOICES = (
        (TYPE_HOME, "Home"),
        (TYPE_WORK, "Work"),
        (TYPE_CUSTOM, "Custom"),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="saved_locations",
    )
    name = models.CharField(max_length=255)
    lat = models.FloatField()
    lon = models.FloatField()
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default=TYPE_CUSTOM)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} - {self.name}"


class FavoriteRoute(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="favorite_routes",
    )
    name = models.CharField(max_length=255)
    origin_lat = models.FloatField()
    origin_lon = models.FloatField()
    origin_name = models.CharField(max_length=255, blank=True, default="")
    destination_lat = models.FloatField()
    destination_lon = models.FloatField()
    destination_name = models.CharField(max_length=255, blank=True, default="")
    route_filter = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} - {self.name}"


class UserPreferences(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="preferences",
    )
    default_filter = models.IntegerField(default=1)
    max_walk_distance = models.IntegerField(default=1500)
    accessibility_mode = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.email} preferences"
