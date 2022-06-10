from django.db import models

from django.utils.translation import gettext_lazy as _


class RoomTag(models.Model):

    name = models.CharField(_("Name"), max_length=120)

    class Meta:
        verbose_name = _("Room Tag")
        verbose_name_plural = _("Room Tags")

    def __str__(self):
        return self.name


class Room(models.Model):
    user = models.ForeignKey(
        "accounts.User",
        verbose_name=_("messages"),
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    contact = models.ForeignKey(
        "contacts.Contact",
        verbose_name=_("messages"),
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    started_at = models.DateTimeField(_("Started at"), auto_now_add=False)
    ended_at = models.DateTimeField(
        _("Ended at"), auto_now_add=False, null=True, blank=True
    )
    is_active = models.BooleanField(_("is active?"), default=True)

    tags = models.ManyToManyField(RoomTag, verbose_name=_("tags"))

    class Meta:
        verbose_name = _("Room")
        verbose_name_plural = _("Rooms")
