from django.conf import settings

from chats.apps.event_driven.base_app import EventDrivenAPP


class RoomsInfoMixin:
    base_room_exchange = settings.ROOMS_INFO_EXCHANGE

    def request_room(self, content):
        """
        Generic function to handle room actions
        """
        EventDrivenAPP().backend.basic_publish(
            content=content,
            exchange=self.base_room_exchange,
            headers={"callback_exchange": settings.DEFAULT_DEAD_LETTER_EXCHANGE},
        )
