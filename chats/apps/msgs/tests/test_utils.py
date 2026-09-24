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
# id (``ACF1292A9EB1991D17C575DDA2A6B587``) with length 32.
WAMID_HBGM_CONTACT_SELF_REPLY_ORIGINAL = (
    "wamid.HBgMNTU4NDg3NzgyMDg3FQIAEhggQUNGMTI5MkE5RUIxOTkxRDE3QzU3NUREQTJB"
    "NkI1ODcA"
)
WAMID_HBGT_CONTACT_SELF_REPLY_CONTEXT = (
    "wamid.HBgTQlIuMTE4MDk1NTMyMDg2MDk4OBUUABIYIEFDRjEyOTJBOUVCMTk5MUQxN0M1"
    "NzVEREEyQTZCNTg3AA=="
)
# Jul 2026 incident: contact self-reply where the original message was stored
# under a phone ``HBgM`` envelope (id length 20) and the reply's ``context.id``
# arrived with a LID ``HBgU`` envelope. Exact ``external_id`` match misses;
# the core extracted from both must coincide (id ``3A6CA38A67DC49A8F3B3``).
WAMID_HBGM_CONTACT_LEN20_ORIGINAL = (
    "wamid.HBgMNTU4NDg2MDY1NzQyFQIAEhgUM0E2Q0EzOEE2N0RDNDlBOEYzQjMA"
)
WAMID_HBGU_CONTACT_LEN20_CONTEXT = (
    "wamid.HBgUQlIuMzU2Nzk5ODIyNzQ5ODIwMjgVFAASGBQzQTZDQTM4QTY3REM0OUE4RjNCMwA="
)
WAMID_HBGU_CONTACT_LEN20_CONTEXT_B = (
    "wamid.HBgUQlIuMzU2Nzk5ODIyNzQ5ODIwMjgVFAASGBQzQTcyMkQzRUEwN0RBQUIxMzQyMQA="
)
WAMID_HBGU_CONTACT_LEN20_CONTEXT_C = (
    "wamid.HBgUQlIuMzU2Nzk5ODIyNzQ5ODIwMjgVFAASGBQzQTREMzA0MUM2NzhBQjQ2MzlDNgA="
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
        # used to fail to resolve because length-32 ids weren't recognized,
        # even though the original (HBgM/phone) and the reply's context.id
        # (HBgT/LID) reference the same message.
        original_core = extract_wamid_core(
            WAMID_HBGM_CONTACT_SELF_REPLY_ORIGINAL
        )
        context_core = extract_wamid_core(
            WAMID_HBGT_CONTACT_SELF_REPLY_CONTEXT
        )
        self.assertIsNotNone(original_core)
        self.assertIsNotNone(context_core)
        self.assertEqual(original_core, context_core)

    def test_lid_envelope_core_exceeds_old_64_char_column_limit(self):
        # Production incident regression test: every core produced via a
        # length-32 id (LID-based envelope) is 66 hex chars, not a rare
        # outlier. ``ChatMessageReplyIndex.external_id_core`` used to be
        # ``CharField(max_length=64)``, so storing this value raised a
        # ``DataError`` on every incoming message matching this envelope.
        # The field is now an unbounded ``TextField`` (see migration 0021);
        # this test documents *why* and guards against the column ever being
        # narrowed again without re-checking this.
        core = extract_wamid_core(WAMID_HBGT_CONTACT_SELF_REPLY_CONTEXT)
        self.assertIsNotNone(core)
        self.assertEqual(len(core), 66)
        self.assertGreater(len(core), 64)

    def test_resolves_hbgu_contact_self_reply_length_20(self):
        # Regression: Jul 2026 — ``HBgU`` reply context with id length 20
        # (``12 18 14``) against an ``HBgM`` original. The old fixed-marker
        # list did not include that length, so ``extract_wamid_core``
        # returned ``None`` and the quote never mounted.
        original_core = extract_wamid_core(WAMID_HBGM_CONTACT_LEN20_ORIGINAL)
        context_core = extract_wamid_core(WAMID_HBGU_CONTACT_LEN20_CONTEXT)
        self.assertIsNotNone(original_core)
        self.assertIsNotNone(context_core)
        self.assertEqual(original_core, context_core)
        # 20 ASCII hex chars + trailing NUL → 42 hex digits.
        self.assertEqual(len(original_core), 42)

    def test_extracts_core_for_hbgu_envelopes(self):
        for wamid in (
            WAMID_HBGU_CONTACT_LEN20_CONTEXT,
            WAMID_HBGU_CONTACT_LEN20_CONTEXT_B,
            WAMID_HBGU_CONTACT_LEN20_CONTEXT_C,
        ):
            with self.subTest(wamid=wamid):
                core = extract_wamid_core(wamid)
                self.assertIsNotNone(core)
                self.assertEqual(core, core.upper())
                self.assertEqual(len(core), 42)

    def test_distinct_hbgu_contexts_yield_distinct_cores(self):
        cores = {
            extract_wamid_core(WAMID_HBGU_CONTACT_LEN20_CONTEXT),
            extract_wamid_core(WAMID_HBGU_CONTACT_LEN20_CONTEXT_B),
            extract_wamid_core(WAMID_HBGU_CONTACT_LEN20_CONTEXT_C),
        }
        self.assertEqual(len(cores), 3)
        self.assertTrue(all(cores))
