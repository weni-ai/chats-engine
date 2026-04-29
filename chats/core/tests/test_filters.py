from django.test import TestCase
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from chats.apps.contacts.models import Contact
from chats.core.filters import DocumentAwareSearchFilter


class _FakeView:
    def __init__(self, search_fields):
        self.search_fields = search_fields


class DocumentAwareSearchFilterTests(TestCase):
    """
    Verifies the per-field normalization behavior of DocumentAwareSearchFilter
    by running the filter against a real Contact queryset.
    """

    @classmethod
    def setUpTestData(cls):
        cls.target = Contact.objects.create(
            name="Joao", email="joao@tokstok.com", document="123.456.789-00"
        )
        cls.other = Contact.objects.create(
            name="Maria", email="maria@example.com", document="98765432100"
        )

    def _filter(self, search_fields, term):
        backend = DocumentAwareSearchFilter()
        request = Request(APIRequestFactory().get("/", {"search": term}))
        view = _FakeView(search_fields)
        return backend.filter_queryset(request, Contact.objects.all(), view)

    def test_document_field_matches_formatted_term(self):
        qs = self._filter(["document"], "123-456-789-00")
        self.assertIn(self.target, qs)
        self.assertNotIn(self.other, qs)

    def test_document_field_matches_unformatted_term(self):
        qs = self._filter(["document"], "12345678900")
        self.assertIn(self.target, qs)
        self.assertNotIn(self.other, qs)

    def test_document_field_with_punctuation_only_term_does_not_match(self):
        """
        A term that becomes empty after normalization ("---") should not
        match any row on the document field, but should also not raise.
        """
        qs = self._filter(["document"], "---")
        self.assertEqual(qs.count(), 0)

    def test_email_field_keeps_raw_term(self):
        """
        Non-document fields must not be normalized: searching for
        the raw email (with @ and dots) has to work.
        """
        qs = self._filter(["email"], "joao@tokstok.com")
        self.assertIn(self.target, qs)
        self.assertNotIn(self.other, qs)

    def test_email_field_does_not_match_normalized_term(self):
        """
        Confirms that normalization is not applied to the email field:
        "JOAOTOKSTOKCOM" (what normalize_document would produce) must
        not match an email containing punctuation.
        """
        qs = self._filter(["email"], "JOAOTOKSTOKCOM")
        self.assertNotIn(self.target, qs)

    def test_mixed_fields_combine_with_or(self):
        """
        When both document and name are in search_fields, a single term
        should be tried against both with OR semantics.
        """
        qs = self._filter(["name", "document"], "123-456-789-00")
        self.assertIn(self.target, qs)
        self.assertNotIn(self.other, qs)

    def test_empty_term_returns_unfiltered_queryset(self):
        qs = self._filter(["document"], "")
        self.assertEqual(qs.count(), Contact.objects.count())

    def test_nested_document_lookup_is_normalized(self):
        """
        Works with traversal like `rooms__contact__document` — what
        matters for normalization is the final segment ending with
        `document`.
        """
        backend = DocumentAwareSearchFilter()
        request = Request(APIRequestFactory().get("/", {"search": "123-456-789-00"}))
        view = _FakeView(["rooms__contact__document"])
        qs = backend.filter_queryset(request, Contact.objects.all(), view)
        self.assertEqual(list(qs.values_list("uuid", flat=True)), [])


class DocumentAwareSearchFilterCommaOrTests(TestCase):
    """
    Validates the comma-as-OR semantics of DocumentAwareSearchFilter:
    `?search=a,b,c` returns rows matching any of the three terms.
    """

    @classmethod
    def setUpTestData(cls):
        cls.joao = Contact.objects.create(
            name="Joao",
            email="joao@tokstok.com",
            document="123.456.789-00",
            external_id="ws-001",
        )
        cls.maria = Contact.objects.create(
            name="Maria",
            email="maria@example.com",
            document="98765432100",
            external_id="ws-002",
        )
        cls.outro = Contact.objects.create(
            name="Outro",
            email="outro@example.com",
            document="11111111111",
            external_id="ws-003",
        )

    def _filter(self, search_fields, term):
        backend = DocumentAwareSearchFilter()
        request = Request(APIRequestFactory().get("/", {"search": term}))
        view = _FakeView(search_fields)
        return backend.filter_queryset(request, Contact.objects.all(), view)

    def test_comma_separates_groups_with_or_semantics(self):
        qs = self._filter(
            ["name", "email", "document", "external_id"],
            "ws-002,joao@tokstok.com,12345678900",
        )
        self.assertIn(self.joao, qs)
        self.assertIn(self.maria, qs)
        self.assertNotIn(self.outro, qs)

    def test_comma_with_normalized_document_term(self):
        qs = self._filter(["document", "name"], "123-456-789-00,Maria")
        self.assertIn(self.joao, qs)
        self.assertIn(self.maria, qs)
        self.assertNotIn(self.outro, qs)

    def test_whitespace_inside_group_keeps_and_semantics(self):
        Contact.objects.create(name="Joao Silva", email="joao.silva@x.com")
        only_one_term = self._filter(["name"], "Joao")
        and_query = self._filter(["name"], "Joao Silva")
        self.assertGreater(only_one_term.count(), and_query.count())
        self.assertTrue(
            and_query.filter(name="Joao Silva").exists(),
            "AND search must match the row whose name contains both terms",
        )

    def test_mixed_groups_or_between_groups_and_inside_group(self):
        Contact.objects.create(name="Joao Silva", document="22222222222")
        qs = self._filter(["name", "document"], "Joao Silva,98765432100")
        names = list(qs.values_list("name", flat=True))
        self.assertIn("Joao Silva", names)
        self.assertIn("Maria", names)
        self.assertNotIn("Outro", names)

    def test_empty_groups_are_ignored(self):
        qs = self._filter(["name"], ",,Maria,,")
        self.assertIn(self.maria, qs)
        self.assertNotIn(self.joao, qs)
        self.assertNotIn(self.outro, qs)

    def test_only_commas_returns_unfiltered_queryset(self):
        qs = self._filter(["name"], ",,,")
        self.assertEqual(qs.count(), Contact.objects.count())

    def test_single_term_without_comma_keeps_legacy_behavior(self):
        qs = self._filter(["document"], "12345678900")
        self.assertIn(self.joao, qs)
        self.assertNotIn(self.maria, qs)
        self.assertNotIn(self.outro, qs)
