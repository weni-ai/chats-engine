from django.db import models
from django.utils.translation import gettext_lazy as _


# Create your models here.
class Contact(models.Model):
    name = models.CharField(_("first name"), max_length=30, blank=True)
    email = models.EmailField(_("email"), unique=True, help_text=_("User email"))

    class Meta:
        verbose_name = _("Contact")
        verbose_name_plural = _("Contacts")
