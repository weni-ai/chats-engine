from unittest import TestCase
import requests
from urllib3.util.retry import Retry

from chats.core.requests import get_request_session_with_retries


class TestRequests(TestCase):
    def test_get_request_session_with_retries_default_values(self):
        """
        Tests the creation of a session with default values
        """
        session = get_request_session_with_retries()
        
        self.assertIsInstance(session, requests.Session)
        
        self.assertIsNotNone(session.adapters.get('http://'))
        self.assertIsNotNone(session.adapters.get('https://'))
        
        adapter = session.adapters.get('https://')
        self.assertIsInstance(adapter.max_retries, Retry)
        
        self.assertEqual(adapter.max_retries.total, 5)
        self.assertEqual(adapter.max_retries.backoff_factor, 0.1)
        self.assertEqual(list(adapter.max_retries.status_forcelist), [])
        self.assertEqual(list(adapter.max_retries.method_whitelist), [])

    def test_get_request_session_with_retries_custom_values(self):
        """
        Tests the creation of a session with custom values
        """
        retries = 3
        backoff_factor = 0.5
        status_forcelist = [500, 502, 503, 504]
        method_whitelist = ['GET', 'POST']
        
        session = get_request_session_with_retries(
            retries=retries,
            backoff_factor=backoff_factor,
            status_forcelist=status_forcelist,
            method_whitelist=method_whitelist
        )
        
        self.assertIsInstance(session, requests.Session)
        
        self.assertIsNotNone(session.adapters.get('http://'))
        self.assertIsNotNone(session.adapters.get('https://'))
        
        adapter = session.adapters.get('https://')
        self.assertIsInstance(adapter.max_retries, Retry)
        
        self.assertEqual(adapter.max_retries.total, retries)
        self.assertEqual(adapter.max_retries.backoff_factor, backoff_factor)
        self.assertEqual(sorted(list(adapter.max_retries.status_forcelist)), sorted(status_forcelist))
        self.assertEqual(sorted(list(adapter.max_retries.method_whitelist)), sorted(method_whitelist))

    def test_get_request_session_with_retries_zero_retries(self):
        """
        Tests the creation of a session with zero retries
        """
        session = get_request_session_with_retries(retries=0)
        
        self.assertIsInstance(session, requests.Session)
        
        self.assertIsNotNone(session.adapters.get('http://'))
        self.assertIsNotNone(session.adapters.get('https://'))
        
        adapter = session.adapters.get('https://')
        self.assertIsInstance(adapter.max_retries, Retry)
        
        self.assertEqual(adapter.max_retries.total, 0)