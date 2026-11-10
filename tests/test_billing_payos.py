"""The payOS client: signing (checked against values produced by payOS's own SDK), the payment link,
the status of a link, and the webhook check. Every key here is an obviously fake test value."""
import json
import unittest

import httpx

from app.services.billing import payos_client as px

KEY = "fake-test-checksum-key"
CLIENT = ("fake-test-client-id", "fake-test-api-key", KEY)

# produced by payos-lib-python 1.1.0 (CryptoProvider) with KEY; see the docstring of payos_client
GOLDEN_REQUEST = "f85933737823bc8daeed7a55cbcb9155837a7e419400a0974e0a3542f70e6a88"
GOLDEN_DATA = "fffe2ed53fd7a4bcf2ecdb88357bfe852892031ec63726c667d72ef98123f7e1"
GOLDEN_LINK = "8723396ea53e130f0ef267354ab8582c68fcbf06372a0b1cb2ec7b0f84202730"

REQUEST = {
    "orderCode": 1700000000123456,
    "amount": 29000,
    "description": "HARU 00123456",
    "cancelUrl": "https://haru.example/pricing?x=cancel",
    "returnUrl": "https://haru.example/pricing?x=ok",
}
WEBHOOK_DATA = {
    "orderCode": 123,
    "amount": 3000,
    "description": "VQRIO123",
    "accountNumber": "12345678",
    "reference": "TF230204212323",
    "transactionDateTime": "2023-02-04 18:25:00",
    "currency": "VND",
    "paymentLinkId": "124c33293c43417ab7879e14c8d9eb18",
    "code": "00",
    "desc": "Thành công",
    "counterAccountBankId": "",
    "counterAccountBankName": "",
    "counterAccountName": "",
    "counterAccountNumber": "",
    "virtualAccountName": "",
    "virtualAccountNumber": "",
}
LINK = {
    "id": "pl1",
    "orderCode": 123,
    "amount": 29000,
    "amountPaid": 29000,
    "amountRemaining": 0,
    "status": "PAID",
    "createdAt": "2026-10-14T10:00:00+07:00",
    "transactions": [
        {
            "reference": "FT1",
            "amount": 29000,
            "accountNumber": "1",
            "description": "HARU",
            "transactionDateTime": "2026-10-14 10:01:00",
            "virtualAccountName": None,
            "virtualAccountNumber": None,
            "counterAccountBankId": None,
            "counterAccountBankName": None,
            "counterAccountName": "NGUYEN VAN A",
            "counterAccountNumber": None,
        }
    ],
    "cancellationReason": None,
    "canceledAt": None,
}


def client_with(handler) -> px.PayosClient:
    return px.PayosClient(*CLIENT, base_url="https://payos.test", http=httpx.Client(transport=httpx.MockTransport(handler)))


def signed(data, code="00", key=KEY):
    return httpx.Response(200, json={"code": code, "desc": "success", "data": data, "signature": px.signature_of(data, key)})


class SigningTests(unittest.TestCase):
    def test_the_values_match_the_ones_payos_own_sdk_makes(self):
        self.assertEqual(px.signature_of_payment_request(REQUEST, KEY), GOLDEN_REQUEST)
        self.assertEqual(px.signature_of(WEBHOOK_DATA, KEY), GOLDEN_DATA)
        self.assertEqual(px.signature_of(LINK, KEY), GOLDEN_LINK)  # a list of objects, None values

    def test_the_key_and_the_data_both_matter(self):
        self.assertNotEqual(px.signature_of(WEBHOOK_DATA, KEY + "x"), GOLDEN_DATA)
        self.assertNotEqual(px.signature_of({**WEBHOOK_DATA, "amount": 3001}, KEY), GOLDEN_DATA)

    def test_the_order_of_the_keys_does_not_matter(self):
        shuffled = dict(reversed(list(WEBHOOK_DATA.items())))
        self.assertEqual(px.signature_of(shuffled, KEY), GOLDEN_DATA)

    def test_a_client_needs_all_three_credentials(self):
        for blank in range(3):
            args = list(CLIENT)
            args[blank] = ""
            with self.assertRaises(px.PayosError):
                px.PayosClient(*args)

    def test_order_codes_are_big_unique_integers_below_the_js_limit(self):
        codes = {px.new_order_code() for _ in range(200)}
        self.assertGreater(len(codes), 150)
        self.assertTrue(all(0 < c < 9007199254740991 for c in codes))


class CreateLinkTests(unittest.TestCase):
    def test_the_request_is_signed_and_the_answer_is_checked(self):
        seen = {}

        def handler(request: httpx.Request):
            seen["url"], seen["headers"], seen["body"] = str(request.url), request.headers, json.loads(request.content)
            return signed(
                {
                    "bin": "970415",
                    "accountNumber": "111",
                    "accountName": "HARU",
                    "amount": 29000,
                    "description": "HARU 00123456",
                    "orderCode": 1700000000123456,
                    "currency": "VND",
                    "paymentLinkId": "pl-1",
                    "status": "PENDING",
                    "expiredAt": 1790000000,
                    "checkoutUrl": "https://pay.payos.test/web/pl-1",
                    "qrCode": "000201...",
                }
            )

        link = client_with(handler).create_payment(
            order_code=1700000000123456,
            amount=29000,
            description="HARU 00123456",
            return_url=REQUEST["returnUrl"],
            cancel_url=REQUEST["cancelUrl"],
            expired_at=1790000000,
        )
        self.assertEqual(seen["url"], "https://payos.test/v2/payment-requests")
        self.assertEqual(seen["headers"]["x-client-id"], CLIENT[0])
        self.assertEqual(seen["headers"]["x-api-key"], CLIENT[1])
        self.assertEqual(seen["body"]["signature"], GOLDEN_REQUEST)
        self.assertEqual(seen["body"]["expiredAt"], 1790000000)
        self.assertEqual((link.payment_link_id, link.checkout_url, link.qr_code), ("pl-1", "https://pay.payos.test/web/pl-1", "000201..."))
        self.assertEqual(link.account_number, "111")

    def test_an_answer_with_a_wrong_signature_is_refused(self):
        def handler(request):
            return signed({"paymentLinkId": "x", "checkoutUrl": "https://evil.test"}, key="another-fake-key")

        with self.assertRaises(px.PayosError) as caught:
            client_with(handler).create_payment(order_code=1, amount=1, description="d", return_url="r", cancel_url="c")
        self.assertIn("signature", str(caught.exception))

    def test_a_refusal_carries_payos_code_and_words(self):
        def handler(request):
            return httpx.Response(200, json={"code": "231", "desc": "Đơn hàng đã tồn tại", "data": None, "signature": None})

        with self.assertRaises(px.PayosError) as caught:
            client_with(handler).create_payment(order_code=1, amount=1, description="d", return_url="r", cancel_url="c")
        self.assertEqual(caught.exception.code, "231")

    def test_an_unreachable_payos_is_an_error_not_a_crash(self):
        def handler(request):
            raise httpx.ConnectError("no route")

        with self.assertRaises(px.PayosError):
            client_with(handler).create_payment(order_code=1, amount=1, description="d", return_url="r", cancel_url="c")

    def test_an_answer_that_is_not_json_is_an_error(self):
        with self.assertRaises(px.PayosError):
            client_with(lambda r: httpx.Response(502, text="bad gateway")).get_payment(5)


class GetLinkTests(unittest.TestCase):
    def test_the_transactions_of_a_link_are_read(self):
        info = client_with(lambda r: signed(LINK)).get_payment(123)
        self.assertEqual((info.status, info.amount, info.amount_paid), ("PAID", 29000, 29000))
        self.assertEqual([(t.reference, t.amount) for t in info.transactions], [("FT1", 29000)])

    def test_the_url_names_the_order_code(self):
        seen = {}

        def handler(request):
            seen["url"] = str(request.url)
            return signed(LINK)

        client_with(handler).get_payment(123)
        self.assertEqual(seen["url"], "https://payos.test/v2/payment-requests/123")


class WebhookTests(unittest.TestCase):
    def body(self, data=WEBHOOK_DATA, key=KEY, **extra):
        return {"code": "00", "desc": "success", "success": True, "data": data, "signature": px.signature_of(data, key), **extra}

    def verify(self, payload):
        return client_with(lambda r: signed({})).verify_webhook(payload)

    def test_a_signed_payment_is_read(self):
        pay = self.verify(self.body())
        self.assertEqual((pay.order_code, pay.amount, pay.reference, pay.paid), (123, 3000, "TF230204212323", True))

    def test_the_golden_body_verifies(self):
        self.assertTrue(self.verify({"code": "00", "success": True, "data": WEBHOOK_DATA, "signature": GOLDEN_DATA}).paid)

    def test_a_body_signed_with_another_key_is_refused(self):
        with self.assertRaises(px.PayosError):
            self.verify(self.body(key="another-fake-key"))

    def test_a_signature_with_odd_characters_is_a_plain_refusal_not_a_crash(self):
        for odd in ("é" * 64, "\u0000" * 10, "🙂", 12345):
            payload = self.body()
            payload["signature"] = odd
            with self.assertRaises(px.PayosError):
                self.verify(payload)

    def test_an_altered_amount_is_refused(self):
        payload = self.body()
        payload["data"] = {**WEBHOOK_DATA, "amount": 3000000}
        with self.assertRaises(px.PayosError):
            self.verify(payload)

    def test_a_body_without_a_signature_is_refused(self):
        payload = self.body()
        payload.pop("signature")
        with self.assertRaises(px.PayosError):
            self.verify(payload)
        with self.assertRaises(px.PayosError):
            self.verify({"code": "00", "data": WEBHOOK_DATA})

    def test_things_that_are_not_a_webhook_are_refused(self):
        for junk in (None, "text", [], {}, {"data": 5, "signature": "x"}):
            with self.assertRaises(px.PayosError):
                self.verify(junk)

    def test_optional_fields_left_out_of_the_json_are_signed_as_empty(self):
        # the SDK signs absent optional fields as ""; a body that omits them still verifies
        sent = {k: v for k, v in WEBHOOK_DATA.items() if k not in px._WEBHOOK_OPTIONAL}
        self.assertTrue(self.verify({"code": "00", "success": True, "data": sent, "signature": GOLDEN_DATA}).paid)

    def test_a_failed_transaction_is_not_a_payment(self):
        failed = {**WEBHOOK_DATA, "code": "01"}
        self.assertFalse(self.verify(self.body(failed)).paid)
        self.assertFalse(self.verify(self.body(success=False)).paid)

    def test_a_signed_body_missing_a_field_is_refused(self):
        data = {k: v for k, v in WEBHOOK_DATA.items() if k != "reference"}
        with self.assertRaises(px.PayosError):
            self.verify(self.body(data))


if __name__ == "__main__":
    unittest.main()
