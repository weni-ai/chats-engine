from unittest import mock
from django.test import SimpleTestCase

from chats.apps.api.v1.external.agents.filters import AgentFlowFilter


class AgentFlowFilterTests(SimpleTestCase):
    def _build_filter(self):
        """Return a filter instance with a mocked queryset to be reused in assertions."""
        qs = mock.Mock(name="QuerySet")
        return AgentFlowFilter(data={}, queryset=qs), qs

    def test_filter_queue_calls_correct_field_lookup(self):
        # Arrange
        filt, qs = self._build_filter()
        
        # Act
        filt.filter_queue(qs, "queue", "queue-123")
        
        # Assert
        qs.filter.assert_called_once_with(queue_authorizations__queue="queue-123")

    def test_filter_sector_calls_correct_field_lookup(self):
        # Arrange
        filt, qs = self._build_filter()
        
        # Act
        filt.filter_sector(qs, "sector", "sector-42")
        
        # Assert
        qs.filter.assert_called_once_with(sector_authorizations__sector="sector-42") 