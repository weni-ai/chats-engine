from rest_framework import routers

from chats.apps.api.v2.msgs.viewsets import MessageViewSetV2

router = routers.SimpleRouter()

router.register(r"msg", MessageViewSetV2, basename="message-v2")
