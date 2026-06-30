from django.test import SimpleTestCase

from chats.apps.msgs.utils import extract_wamid_core


# Real WAMID samples observed in production. Kept here so we catch any
# regression in the base64/marker logic if Meta ever changes the envelope.
WAMID_HBGM_AGENT_A = (
    "wamid.HBgMNTU0MTk4NTY3MDM0FQIAERgSODVEMjRDRkUyREFBRkM3QTExAA=="
)
WAMID_HBGM_AGENT_B = (
    "wamid.HBgMNTU0MTk4NTY3MDM0FQIAERgSRDgyRjdGMERFRTM1RDExRUQxAA=="
)
WAMID_HBGT_BUSINESS = (
    "wamid.HBgTQlIuMTE4MDk1NTMyMDg2MDk4OBUUABIYFjNFQjAwRUM1QkU1NTlDMTYwMUQwREYA"
)
WAMID_HBGL_US_CONTACT = (
    "wamid.HBgLMTUwODcxODkzNDUVAgARGBIxNjYzM0EyMURBNjg5RkZFODUA"
)
# Contact-self-reply pair observed in production: a contact message
# (HBgM/phone envelope) and the ``context.id`` of a later reply by the same
# contact to that message (HBgT/LID envelope). Both share the same internal
# id (``ACF1292A9EB1991D17C575DDA2A6B587``) but use the ``0x12, 0x18, 0x20``
# trailer marker, which is distinct from ``WAMID_HBGT_BUSINESS`` above
# (same HBgT/LID shape, but ``0x12, 0x18, 0x16`` marker).
WAMID_HBGM_CONTACT_SELF_REPLY_ORIGINAL = (
    "wamid.HBgMNTU4NDg3NzgyMDg3FQIAEhggQUNGMTI5MkE5RUIxOTkxRDE3QzU3NUREQTJB"
    "NkI1ODcA"
)
WAMID_HBGT_CONTACT_SELF_REPLY_CONTEXT = (
    "wamid.HBgTQlIuMTE4MDk1NTMyMDg2MDk4OBUUABIYIEFDRjEyOTJBOUVCMTk5MUQxN0M1"
    "NzVEREEyQTZCNTg3AA=="
)


class ExtractWamidCoreTests(SimpleTestCase):
    def test_returns_none_for_falsy_input(self):
        self.assertIsNone(extract_wamid_core(None))
        self.assertIsNone(extract_wamid_core(""))

    def test_returns_none_for_non_string_input(self):
        self.assertIsNone(extract_wamid_core(12345))  # type: ignore[arg-type]
        self.assertIsNone(extract_wamid_core([WAMID_HBGM_AGENT_A]))  # type: ignore[arg-type]

    def test_returns_none_when_prefix_is_missing(self):
        self.assertIsNone(extract_wamid_core("not-a-wamid.HBgM"))
        self.assertIsNone(extract_wamid_core("HBgMNTU0MTk4NTY3MDM0FQ=="))

    def test_returns_none_for_invalid_base64(self):
        self.assertIsNone(extract_wamid_core("wamid.!!!not-base64!!!"))

    def test_returns_none_when_marker_not_found(self):
        self.assertIsNone(extract_wamid_core("wamid.SGVsbG8="))  # "Hello"

    def test_is_deterministic_for_same_wamid(self):
        first = extract_wamid_core(WAMID_HBGM_AGENT_A)
        second = extract_wamid_core(WAMID_HBGM_AGENT_A)
        self.assertIsNotNone(first)
        self.assertEqual(first, second)

    def test_distinct_wamids_yield_distinct_cores(self):
        core_a = extract_wamid_core(WAMID_HBGM_AGENT_A)
        core_b = extract_wamid_core(WAMID_HBGM_AGENT_B)
        self.assertIsNotNone(core_a)
        self.assertIsNotNone(core_b)
        self.assertNotEqual(core_a, core_b)

    def test_extracts_core_for_known_envelopes(self):
        # All three envelopes (HBgM, HBgT, HBgL) must yield a non-empty core.
        for wamid in (WAMID_HBGM_AGENT_A, WAMID_HBGT_BUSINESS, WAMID_HBGL_US_CONTACT):
            with self.subTest(wamid=wamid):
                core = extract_wamid_core(wamid)
                self.assertIsNotNone(core)
                self.assertTrue(len(core) > 0)
                # Hex output is uppercase to match the way Meta encodes the
                # inner ASCII id; downstream lookups rely on this normalization.
                self.assertEqual(core, core.upper())

    def test_pad_handles_missing_base64_padding(self):
        # Strip the trailing "==" to ensure padding is restored before decode.
        unpadded = WAMID_HBGM_AGENT_A.rstrip("=")
        self.assertNotEqual(unpadded, WAMID_HBGM_AGENT_A)
        self.assertEqual(
            extract_wamid_core(unpadded),
            extract_wamid_core(WAMID_HBGM_AGENT_A),
        )

    def test_resolves_contact_self_reply_envelope(self):
        # Regression test: a contact replying to their own earlier message
        # used to fail to resolve because the ``0x12, 0x18, 0x20`` trailer
        # marker wasn't recognized, even though the original (HBgM/phone)
        # and the reply's context.id (HBgT/LID) reference the same message.
        original_core = extract_wamid_core(
            WAMID_HBGM_CONTACT_SELF_REPLY_ORIGINAL
        )
        context_core = extract_wamid_core(
            WAMID_HBGT_CONTACT_SELF_REPLY_CONTEXT
        )
        self.assertIsNotNone(original_core)
        self.assertIsNotNone(context_core)
        self.assertEqual(original_core, context_core)
