from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from chats.apps.msgs.usecases.build_reply_index_maps import (
    BuildReplyIndexCoreMapUseCase,
    BuildReplyIndexMapUseCase,
)


def _message(metadata):
    return SimpleNamespace(metadata=metadata)


class BuildReplyIndexMapUseCaseTests(SimpleTestCase):
    def test_returns_empty_when_messages_have_no_context_id(self):
        messages = [
            _message(None),
            _message("not-a-dict"),
            _message({"context": "invalid"}),
            _message({"context": {}}),
        ]

        with patch(
            "chats.apps.msgs.usecases.build_reply_index_maps.ChatMessageReplyIndex.objects"
        ) as mock_objects:
            result = BuildReplyIndexMapUseCase().execute(messages)

        self.assertEqual(result, {})
        mock_objects.select_related.assert_not_called()

    def test_fetches_indexes_by_collected_external_ids(self):
        messages = [
            _message({"context": {"id": "wamid.one"}}),
            _message({"context": {"id": "wamid.one"}}),
            _message({"context": {"id": "wamid.two"}}),
        ]
        first = SimpleNamespace(external_id="wamid.one")
        second = SimpleNamespace(external_id="wamid.two")
        queryset = MagicMock()
        queryset.filter.return_value = [first, second]

        with patch(
            "chats.apps.msgs.usecases.build_reply_index_maps.ChatMessageReplyIndex.objects"
        ) as mock_objects:
            mock_objects.select_related.return_value = queryset
            result = BuildReplyIndexMapUseCase().execute(messages)

        queryset.filter.assert_called_once_with(
            external_id__in={"wamid.one", "wamid.two"}
        )
        self.assertEqual(
            result,
            {"wamid.one": first, "wamid.two": second},
        )


class BuildReplyIndexCoreMapUseCaseTests(SimpleTestCase):
    def test_returns_empty_when_all_ids_are_already_resolved(self):
        messages = [_message({"context": {"id": "wamid.one"}})]
        exact_map = {"wamid.one": object()}

        with patch(
            "chats.apps.msgs.usecases.build_reply_index_maps.ChatMessageReplyIndex.objects"
        ) as mock_objects:
            result = BuildReplyIndexCoreMapUseCase().execute(
                messages, exact_map, room_uuid="room-1"
            )

        self.assertEqual(result, {})
        mock_objects.select_related.assert_not_called()

    def test_returns_empty_when_unresolved_ids_have_no_core(self):
        messages = [_message({"context": {"id": "not-a-wamid"}})]

        with patch(
            "chats.apps.msgs.usecases.build_reply_index_maps.extract_wamid_core",
            return_value=None,
        ), patch(
            "chats.apps.msgs.usecases.build_reply_index_maps.ChatMessageReplyIndex.objects"
        ) as mock_objects:
            result = BuildReplyIndexCoreMapUseCase().execute(
                messages, exact_map={}, room_uuid="room-1"
            )

        self.assertEqual(result, {})
        mock_objects.select_related.assert_not_called()

    def test_filters_by_core_and_room(self):
        messages = [_message({"context": {"id": "wamid.unresolved"}})]
        index = SimpleNamespace(external_id_core="CORE1")
        queryset = MagicMock()
        queryset.filter.return_value = queryset
        queryset.order_by.return_value = [index]

        with patch(
            "chats.apps.msgs.usecases.build_reply_index_maps.extract_wamid_core",
            return_value="CORE1",
        ), patch(
            "chats.apps.msgs.usecases.build_reply_index_maps.ChatMessageReplyIndex.objects"
        ) as mock_objects:
            mock_objects.select_related.return_value = queryset
            result = BuildReplyIndexCoreMapUseCase().execute(
                messages, exact_map={}, room_uuid="room-1"
            )

        queryset.filter.assert_called_once_with(
            external_id_core__in={"CORE1"},
            message__room_id="room-1",
        )
        self.assertEqual(result, {"CORE1": index})
