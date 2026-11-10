"""The price list, who may open what, and what a payment means: the rules that need no database."""
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.services.billing import access as acc
from app.services.billing import catalog as cat
from app.services.billing import orders

NOW = datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc)


def ent(product, **kw):
    base = dict(product_code=product, revoked_at=None, starts_at=NOW - timedelta(days=1), ends_at=None)
    base.update(kw)
    return SimpleNamespace(**base)


def order(**kw):
    base = dict(amount=29_000, paid_amount=0, status="PENDING", needs_review=False, note=None, paid_at=None, provider_ref=None)
    base.update(kw)
    return SimpleNamespace(**base)


class CatalogTests(unittest.TestCase):
    def test_the_prices_are_the_planned_ones(self):
        on_sale = {p.code: p.amount for p in cat.DEFAULTS if p.active}
        self.assertEqual(on_sale, {
            "pack_sinh_hoat_2": 49_000,
            "pack_9_41": 199_000,
            "pack_viet_54": 149_000,
            "pack_42_71": 249_000,
            "pack_all": 349_000,
            "exam_pass_30": 99_000,
            "exam_pass_90": 249_000,
            "speak_30": 229_000,
            "speak_90": 599_000,
            "combo_giao_tiep": 379_000,
            "combo_topik2": 429_000,
            "combo_tron_goi": 999_000,
        })

    def test_a_combo_costs_less_than_its_products_and_holds_their_lessons(self):
        for code in ("combo_giao_tiep", "combo_topik2", "combo_tron_goi"):
            combo = cat.get(code)
            parts = cat.parts(combo)
            self.assertEqual([p.code for p in parts], list(combo.includes))
            self.assertLess(combo.amount, cat.list_total(combo), code)
            packs = [p for p in parts if p.kind == cat.LESSON_PACK]
            self.assertEqual(combo.lessons, packs[0].lessons, code)
            # the saving never eats into what the speaking minutes cost (~1,500đ a minute)
            minutes = sum(p.minutes or 0 for p in parts)
            self.assertGreater(combo.amount - minutes * 1_500, 100_000, code)
        self.assertEqual([p.code for p in cat.parts(cat.get("pack_all"))], ["pack_all"])

    def test_retired_products_still_open_what_was_bought_but_are_not_sold(self):
        for code in ("pack_quan_he", "pack_nhap_canh", "pack_cong_so", "pack_xa_hoi", "combo_3_packs", "speak_pass_30", "speak_pass_90"):
            p = cat.get(code)
            self.assertTrue(p is not None and p.retired and not p.active, code)
            self.assertNotIn(p, cat.listed())
        # an admin cannot put a retired product back on sale
        cat.apply_settings({"combo_3_packs": {"active": True}, "pack_9_41": {"active": False}})
        try:
            self.assertFalse(cat.get("combo_3_packs").active)
            self.assertFalse(cat.get("pack_9_41").active)
        finally:
            cat.apply_settings({})

    def test_every_paid_lesson_can_be_bought_and_the_big_packs_hold_the_small_ones(self):
        # Bảng chữ cái is Bài 1 and Nền tảng is 16 short lessons: the course runs 1–83, the first 19 are free
        sold = cat.listed()
        for n in range(20, 84):
            self.assertTrue(any(p.covers(n) for p in sold if p.kind == "lesson_pack"), n)
            self.assertTrue(cat.get("pack_all").covers(n), n)
        self.assertTrue(all(cat.get("pack_9_41").covers(n) for n in range(20, 54)))
        self.assertTrue(all(cat.get("pack_42_71").covers(n) for n in range(54, 84)))
        self.assertFalse(any(p.covers(19) for p in cat.PRODUCTS))
        self.assertFalse(any(p.covers(84) for p in cat.PRODUCTS))

    def test_the_pack_sizes_match_the_course(self):
        sizes = {p.code: p.lesson_count for p in cat.listed() if p.kind == "lesson_pack"}
        # Sinh hoạt 2 took the old Bài 8 (Ăn uống) when Bảng chữ cái went in front
        self.assertEqual(sizes, {"pack_sinh_hoat_2": 8, "pack_9_41": 34, "pack_viet_54": 8, "pack_42_71": 30, "pack_all": 64})

    def test_a_bigger_pack_costs_less_than_its_parts(self):
        self.assertLess(cat.get("pack_all").amount, cat.get("pack_9_41").amount + cat.get("pack_42_71").amount)
        self.assertLess(cat.get("exam_pass_90").amount, 3 * cat.get("exam_pass_30").amount)
        self.assertLess(cat.get("speak_90").amount, 3 * cat.get("speak_30").amount)

    def test_haru_noi_is_sold_by_the_minute_and_the_old_passes_had_no_total(self):
        self.assertEqual((cat.get("speak_30").minutes, cat.get("speak_90").minutes), (100, 300))
        # the longer pass is the cheaper minute
        per = lambda p: p.amount / p.minutes  # noqa: E731
        self.assertLess(per(cat.get("speak_90")), per(cat.get("speak_30")))
        self.assertIsNone(cat.get("speak_pass_30").minutes)
        self.assertEqual(cat.feature_passes("talk"), ["speak_30", "speak_90"])

    def test_with_the_hangul_lesson_in_front_and_nen_tang_split_every_range_moved_down(self):
        # Bảng chữ cái + the 16 Nền tảng parts + Buổi sáng, Việc nhà: the same free lessons as before
        self.assertEqual((cat.LESSON_SHIFT, cat.SPLIT_SHIFT, cat.FREE_LESSON_MAX), (1, 11, 19))
        self.assertEqual(cat.get("pack_sinh_hoat_2").lessons, ((20, 27),))
        self.assertTrue(cat.get("pack_sinh_hoat_2").blurb_vi.startswith("Bài 20–27 (8 bài"))
        self.assertEqual(cat.get("pack_viet_54").lessons, ((54, 61),))
        self.assertEqual(cat.get("pack_all").lessons, ((20, 83),))
        # what was bought keeps the same lessons
        self.assertEqual(cat.get("pack_quan_he").lessons, ((28, 39),))
        self.assertEqual(cat.get("combo_3_packs").lessons, ((20, 27), (28, 39), (40, 45)))

    def test_every_pack_starts_and_ends_on_the_same_lessons_as_before_the_split(self):
        import json
        from pathlib import Path

        at = {
            json.loads(f.read_text(encoding="utf-8"))["slug"]: json.loads(f.read_text(encoding="utf-8"))["sort_order"]
            for f in (Path(__file__).resolve().parents[1] / "app/seed/lessons").glob("*.json")
        }
        self.assertEqual(at["sinh-hoat-03-an-uong"], cat._FIRST_PAID)
        self.assertEqual(at["quan-he-01-gia-dinh"], cat.get("pack_quan_he").lessons[0][0])
        self.assertEqual(at["viet-nghi-luan-01-doc-de"], cat.get("pack_viet_54").lessons[0][0])
        self.assertEqual(at["xa-hoi-22-doc-chu-de-thai-do-muc-dich"], cat.get("pack_all").lessons[0][1])
        self.assertEqual(max(at.values()), cat.get("pack_all").lessons[0][1])

    def test_what_opens_a_lesson_is_listed_cheapest_first(self):
        self.assertEqual(cat.unlock_products(3), [])
        self.assertEqual(cat.unlock_products(19), [])
        self.assertEqual(cat.unlock_products(21), ["pack_sinh_hoat_2", "pack_9_41", "pack_all"])
        self.assertEqual(cat.unlock_products(31), ["pack_9_41", "pack_all"])
        self.assertEqual(cat.unlock_products(54), ["pack_viet_54", "pack_42_71", "pack_all"])
        self.assertEqual(cat.unlock_products(83), ["pack_42_71", "pack_all"])  # the reading lesson after topic 5
        self.assertEqual(cat.unlock_products(84), [])  # in no pack: only an "all" grant

    def test_the_passes_have_a_length_and_the_packs_do_not(self):
        self.assertEqual((cat.get("exam_pass_30").days, cat.get("exam_pass_90").days), (30, 90))
        self.assertEqual((cat.get("speak_30").days, cat.get("speak_90").days), (30, 90))
        self.assertTrue(all(p.days is None for p in cat.PRODUCTS if p.kind == "lesson_pack"))


class AccessTests(unittest.TestCase):
    def build(self, *rows):
        return acc.build_access(rows, NOW)

    def test_nothing_held_opens_only_the_free_lessons(self):
        held = self.build()
        self.assertTrue(held.can_open(19))
        self.assertFalse(held.can_open(20))
        self.assertEqual((held.label_for(19), held.label_for(20)), ("free", "locked"))
        self.assertFalse(held.can_use_exam_pass())

    def test_a_pack_opens_its_lessons_only(self):
        held = self.build(ent("pack_quan_he"))
        self.assertTrue(held.can_open(28) and held.can_open(39))
        self.assertFalse(held.can_open(27) or held.can_open(40))
        self.assertEqual(held.label_for(31), "owned")

    def test_the_combo_opens_all_three(self):
        held = self.build(ent("combo_3_packs"))
        self.assertTrue(all(held.can_open(n) for n in range(1, 46)))
        self.assertFalse(held.can_open(46))

    def test_an_all_grant_opens_everything_and_the_pass(self):
        held = self.build(ent("all"))
        self.assertTrue(held.can_open(99) and held.can_open(None) and held.can_use_exam_pass())

    def test_revoked_ended_or_not_yet_started_rights_do_not_count(self):
        self.assertFalse(self.build(ent("pack_quan_he", revoked_at=NOW)).can_open(28))
        self.assertFalse(self.build(ent("exam_pass_30", ends_at=NOW)).can_use_exam_pass())
        self.assertFalse(self.build(ent("pack_quan_he", starts_at=NOW + timedelta(hours=1))).can_open(28))

    def test_a_pass_runs_until_its_end_and_the_longest_wins(self):
        held = self.build(ent("exam_pass_30", ends_at=NOW + timedelta(days=3)), ent("exam_pass_90", ends_at=NOW + timedelta(days=40)))
        self.assertTrue(held.can_use_exam_pass())
        self.assertEqual(held.exam_pass_until, NOW + timedelta(days=40))

    def test_an_unknown_product_is_ignored(self):
        self.assertFalse(self.build(ent("pack_from_the_future")).can_open(27))

    def test_with_billing_off_everything_is_open(self):
        self.assertTrue(acc.OPEN.can_open(33) and acc.OPEN.can_use_exam_pass())
        self.assertEqual(acc.OPEN.label_for(20), "free")

    def test_an_anonymous_caller_holds_nothing(self):
        self.assertFalse(acc.ANONYMOUS.can_open(20))
        self.assertTrue(acc.ANONYMOUS.can_open(3))

    def test_a_pack_already_held_is_not_sold_again_but_a_pass_always_is(self):
        held = self.build(ent("pack_nhap_canh"))
        self.assertTrue(held.owns(cat.get("pack_nhap_canh")))
        self.assertFalse(held.owns(cat.get("pack_9_41")))
        self.assertFalse(self.build(ent("exam_pass_30", ends_at=NOW + timedelta(days=5))).owns(cat.get("exam_pass_30")))
        # the old packs together hold all of 9-41: the new pack has nothing left to sell them
        old = (ent("pack_sinh_hoat_2"), ent("pack_quan_he"), ent("pack_nhap_canh"), ent("pack_cong_so"))
        self.assertTrue(self.build(*old).owns(cat.get("pack_9_41")))
        self.assertTrue(self.build(ent("pack_all")).owns(cat.get("pack_viet_54")))


class SettleTests(unittest.TestCase):
    def test_an_exact_payment_pays_the_order(self):
        o = order(paid_amount=29_000)
        s = orders.settle(o, NOW)
        self.assertEqual((s.granted, s.outcome, o.status, o.paid_at, o.needs_review), (True, "granted", "PAID", NOW, False))

    def test_a_short_payment_unlocks_nothing(self):
        o = order(paid_amount=20_000)
        s = orders.settle(o, NOW)
        self.assertEqual((s.granted, s.outcome, o.status, o.needs_review), (False, "underpaid", "UNDERPAID", True))
        self.assertIn("20000", o.note)

    def test_the_missing_money_arriving_later_completes_the_order(self):
        o = order(paid_amount=20_000, status="UNDERPAID", needs_review=True)
        o.paid_amount += 9_000
        s = orders.settle(o, NOW)
        self.assertEqual((s.granted, o.status, o.needs_review), (True, "PAID", False))

    def test_too_much_money_unlocks_and_asks_for_a_look(self):
        o = order(paid_amount=39_000)
        s = orders.settle(o, NOW)
        self.assertEqual((s.granted, s.outcome, o.needs_review), (True, "granted_over", True))
        self.assertIn("10000", o.note)

    def test_a_second_payment_on_a_paid_order_grants_nothing_and_is_flagged(self):
        o = order(paid_amount=58_000, status="PAID", paid_at=NOW)
        s = orders.settle(o, NOW + timedelta(hours=1))
        self.assertEqual((s.granted, s.outcome, o.status, o.paid_at, o.needs_review), (False, "extra", "PAID", NOW, True))

    def test_money_after_the_link_expired_still_unlocks(self):
        for dead in ("EXPIRED", "CANCELLED"):
            o = order(paid_amount=29_000, status=dead)
            self.assertTrue(orders.settle(o, NOW).granted, dead)
            self.assertEqual(o.status, "PAID")
            self.assertIn("hết hạn", o.note)


class WindowTests(unittest.TestCase):
    def test_a_pack_is_for_life(self):
        self.assertEqual(orders.entitlement_window(cat.get("pack_quan_he"), NOW, None), (NOW, None))

    def test_a_pass_lasts_its_days(self):
        self.assertEqual(orders.entitlement_window(cat.get("exam_pass_30"), NOW, None), (NOW, NOW + timedelta(days=30)))
        self.assertEqual(orders.entitlement_window(cat.get("exam_pass_90"), NOW, None)[1], NOW + timedelta(days=90))

    def test_a_second_pass_starts_when_the_first_ends(self):
        first_end = NOW + timedelta(days=10)
        start, end = orders.entitlement_window(cat.get("exam_pass_30"), NOW, first_end)
        self.assertEqual((start, end), (first_end, first_end + timedelta(days=30)))

    def test_an_ended_pass_does_not_push_the_new_one_back(self):
        start, _ = orders.entitlement_window(cat.get("exam_pass_30"), NOW, NOW - timedelta(days=2))
        self.assertEqual(start, NOW)

    def test_an_admin_can_name_the_days(self):
        self.assertEqual(orders.entitlement_window(cat.get("exam_pass_30"), NOW, None, days=7)[1], NOW + timedelta(days=7))


if __name__ == "__main__":
    unittest.main()
