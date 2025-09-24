from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.contrib.auth.models import UserManager as BaseUserManager
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from chats.core.models import BaseModel


class UserManager(BaseUserManager):
    def _create_user(self, email, password, **extra_fields):
        """
        Create and save a user with the given email and password.
        """
        if not email:
            raise ValueError("The given email must be set")

        email = self.normalize_email(email)

        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)

    def get_admin_user(self):
        user, _ = self.get_or_create(email=settings.ADMIN_USER_EMAIL)
        return user

    def update_email(self, user_id, new_email):
        """
        Update user email with cache invalidation
        """
        from chats.core.cache_utils import invalidate_user_email_cache

        try:
            user = self.get(pk=user_id)
            old_email = user.email
            user.email = self.normalize_email(new_email)
            user.save()

            invalidate_user_email_cache(old_email)
            invalidate_user_email_cache(new_email)

            return user
        except self.model.DoesNotExist:
            raise


class User(AbstractBaseUser, PermissionsMixin):
    first_name = models.CharField(_("first name"), max_length=30, blank=True)
    last_name = models.CharField(_("last name"), max_length=150, blank=True)
    email = models.EmailField(_("email"), unique=True, help_text=_("User email"))

    photo_url = models.TextField(blank=True, null=True)

    is_staff = models.BooleanField(_("staff status"), default=False)
    is_active = models.BooleanField(_("active"), default=True)

    language = models.CharField(max_length=5, null=True, blank=True)

    date_joined = models.DateTimeField(_("date joined"), default=timezone.now)

    objects = UserManager()

    EMAIL_FIELD = "email"
    USERNAME_FIELD = "email"

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")

    @property
    def sector_ids(self):
        return self.sector_authorizations.values_list("sector__id", flat=True)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def name(self):
        return self.first_name


class Profile(BaseModel):
    user = models.OneToOneField(
        User, related_name="profile", verbose_name=_("User"), on_delete=models.CASCADE
    )
    sound_new_room = models.BooleanField(
        _("New room messages notification sound"), default=True
    )
    sound_chat_msg = models.BooleanField(
        _("Chat messages notification sound"), default=True
    )
    sound_action = models.BooleanField(_("Action sound"), default=True)
    config = models.JSONField(
        _("config"),
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = _("Profile")
        verbose_name_plural = _("Profiles")
