"""What is for sale, and for how much. The products and their DEFAULT prices live here; an admin
can change a product's price, its "was" price, its name and blurb, and switch it on or off from
the admin screen (billing.product_setting, applied by `apply_settings`). Either way an order takes
its amount from the server, never from the browser. What a product opens (its lessons, its days,
its features) stays in this file: changing that is a code change.

A lesson is told apart by its `sort_order` (1-71 in the numbering before the Hangul lesson; 1-83 today, with the Hangul lesson in front and the five Nền tảng lessons cut into sixteen): 1-19 are free,
each pack covers a range above that. A lesson that sits in no pack (a future one, or one without a position)
opens only with the "all" grant until it is given a pack.

Prices (October 2026, docs: "Haru — Bảng giá & kinh tế đơn vị"): the lessons cost nothing to serve,
so they are priced by value; the Pass Luyện thi costs a few hundred đồng a day of model calls; Haru
Nói is the expensive one (Gemini Live is paid by the token, ~1,500đ a minute) and is sold as
MINUTES: a pass carries `minutes`, the live minutes (Trò chuyện + Tranh luận together) it includes,
on top of the daily cap. A RETIRED product is no longer sold, whatever an admin set, but the rights
bought with it stay (an old Haru Nói pass keeps its unlimited minutes within the daily cap).
"""
from dataclasses import dataclass, replace
from typing import Any, Literal

# Bảng chữ cái + the 16 Nền tảng parts + Buổi sáng, Việc nhà: free, complete, no wall in the middle.
# (Before the split it was 8: the same lessons, with Nền tảng 1-5 whole.)
FREE_LESSON_MAX = 19

# The Hangul lesson (bảng chữ cái) goes in FRONT of Nền tảng 1 and every lesson moves down one place.
# The free lessons stay 8 (Hangul + Nền tảng 1-5 + Buổi sáng, Việc nhà), so the old Bài 8 (Ăn uống)
# joins Sinh hoạt 2. Set this to 1 in the same commit that adds the Hangul seed and renumbers the
# others (`python -m app.services.lesson_seed --shift 1`): every pack range below and its words follow.
LESSON_SHIFT = 1
# November 2026: the five Nền tảng lessons were cut into sixteen (scripts/split_foundation.py), so
# every lesson after Việc nhà moved down 11 more places. The packs keep the same lessons.
SPLIT_SHIFT = 11
_LAST_FREE_BEFORE = 7  # Việc nhà, in the numbering before the Hangul lesson


def _at(n: int) -> int:
    """A lesson's position today, from its number before the Hangul lesson and the split (1-71)."""
    return n + LESSON_SHIFT + (SPLIT_SHIFT if n > _LAST_FREE_BEFORE else 0)


def _span(lo: int, hi: int) -> str:
    """'Bài 9–15 (7 bài' for a range given in today's positions."""
    return f"Bài {lo}–{hi} ({hi - lo + 1} bài"

ALL = "all"  # an admin / grandfather grant: every lesson and the exam pass

LESSON_PACK = "lesson_pack"
EXAM_PASS = "exam_pass"
FEATURE_PASS = "feature_pass"  # time-limited use of features (the AI speaking practice)
COMBO = "combo"  # several products in one order, for less: paying it grants each of them
PASS_KINDS = (EXAM_PASS, FEATURE_PASS)

# Features a feature pass opens. Free learners get a daily allowance of each (billing.features).
FEATURES: dict[str, str] = {
    "talk": "Trò chuyện với Haru",
    "present": "Trình bày",
    "debate": "Tranh luận · Đàm phán · Phản biện",
}


@dataclass(frozen=True)
class Product:
    code: str
    kind: Literal["lesson_pack", "exam_pass", "feature_pass", "combo"]
    title_vi: str
    blurb_vi: str
    amount: int  # VND
    lessons: tuple[tuple[int, int], ...] = ()  # sort_order ranges, both ends included
    days: int | None = None  # pass length; a pack is for life
    order: int = 0  # position on the price page
    features: tuple[str, ...] = ()  # feature pass: what it opens (FEATURES)
    compare_at: int | None = None  # a "was" price shown struck through (set by an admin)
    active: bool = True  # on sale (an admin can take it off sale; rights already bought stay)
    minutes: int | None = None  # feature pass: live minutes included for its whole length (None = no total)
    retired: bool = False  # replaced by another product: never on sale again
    includes: tuple[str, ...] = ()  # a combo: the codes it grants (each one as if bought alone)

    def covers(self, sort_order: int | None) -> bool:
        return bool(sort_order) and any(lo <= sort_order <= hi for lo, hi in self.lessons)

    @property
    def lesson_count(self) -> int:
        return sum(hi - lo + 1 for lo, hi in self.lessons)


_FIRST_PAID = FREE_LESSON_MAX + 1
_TRUNG_CAP = ((_FIRST_PAID, _at(41)),)  # what pack_9_41 opens
_NANG_CAO = ((_at(42), _at(71)),)  # what pack_42_71 opens
_SINH_HOAT_END, _CONG_SO_END, _VIET_START, _VIET_END, _LAST = _at(15), _at(41), _at(42), _at(49), _at(71)
_PACKS = ((_FIRST_PAID, _at(15)), (_at(16), _at(27)), (_at(28), _at(33)))
_ONCE = "Mua một lần, học trọn đời."

PRODUCTS: tuple[Product, ...] = (
    # ---- on sale --------------------------------------------------------------------------
    Product(
        "pack_sinh_hoat_2", LESSON_PACK, "Sinh hoạt 2",
        f"{_span(_FIRST_PAID, _SINH_HOAT_END)}, gồm bài ôn tập): học tiếp chủ đề Sinh hoạt hằng ngày ngay sau "
        f"{FREE_LESSON_MAX} bài miễn phí. {_ONCE}",
        49_000, ((_FIRST_PAID, _SINH_HOAT_END),), order=1,
    ),
    Product(
        "pack_9_41", LESSON_PACK, "Lộ trình Trung cấp",
        f"{_span(_FIRST_PAID, _CONG_SO_END)}): Sinh hoạt hằng ngày, Quan hệ & Không gian sống, Nhập cảnh & Cư trú, Đời sống xã hội & Công sở, kèm đề thi thử TOPIK II mức 4. {_ONCE}",
        199_000, ((_FIRST_PAID, _CONG_SO_END),), order=2,
    ),
    Product(
        "pack_viet_54", LESSON_PACK, "Viết câu 54 từ con số 0",
        f"{_span(_VIET_START, _VIET_END)}): đọc đề, tìm ý, viết đoạn, ráp bài và luyện đề câu 54. {_ONCE}",
        149_000, ((_VIET_START, _VIET_END),), order=3,
    ),
    Product(
        "pack_42_71", LESSON_PACK, "Lộ trình TOPIK II nâng cao",
        f"{_span(_VIET_START, _LAST)}): trọn khoá Viết câu 54, ngữ pháp Đọc 3–4, quán ngữ, các chủ đề kinh tế, chính trị, khoa học, tư tưởng, lịch sử, y học, đề thi thử TOPIK II mức 5–6. {_ONCE}",
        249_000, ((_VIET_START, _LAST),), order=4,
    ),
    Product(
        "pack_all", LESSON_PACK, "Trọn bộ bài học",
        f"Bài {_FIRST_PAID}–{_LAST}: toàn bộ {_LAST - _FIRST_PAID + 1} bài trả phí, từ Sinh hoạt 2 đến TOPIK II mức 5–6, cả bài mới thêm vào các chủ đề này. {_ONCE}",
        349_000, ((_FIRST_PAID, _LAST),), order=5, compare_at=448_000,  # = Sơ – Trung cấp + TOPIK II nâng cao
    ),
    Product(
        "exam_pass_30", EXAM_PASS, "Pass Luyện thi 30 ngày",
        "Dùng trong 30 ngày, tối đa 12 đề viết câu 51–52 mỗi ngày. Trả một lần, không tự gia hạn.",
        99_000, days=30, order=6,
    ),
    Product(
        "exam_pass_90", EXAM_PASS, "Pass Luyện thi 90 ngày",
        "Đủ quyền lợi của Pass 30 ngày, dùng trong 90 ngày: vừa một mùa ôn thi. Trả một lần, không tự gia hạn.",
        249_000, days=90, order=7, compare_at=297_000,  # = 3 Pass 30 ngày
    ),
    Product(
        "speak_30", FEATURE_PASS, "Haru Nói 30 ngày",
        "100 phút nói với Haru, dùng trong 30 ngày (khoảng 10 buổi 10 phút). Trả một lần, không tự gia hạn.",
        229_000, days=30, order=8, features=("talk", "present", "debate"), minutes=100,
    ),
    Product(
        "speak_90", FEATURE_PASS, "Haru Nói 90 ngày",
        "300 phút nói với Haru, dùng trong 90 ngày (khoảng 30 buổi 10 phút). Trả một lần, không tự gia hạn.",
        599_000, days=90, order=9, features=("talk", "present", "debate"), minutes=300,
    ),
    # ---- combos: two or three products in one order, for less than apart. Each one is granted
    # as if bought alone (a pass in it extends the one held). The saving is taken from the
    # lessons, which cost nothing to serve, never below what the speaking minutes cost.
    Product(
        "combo_giao_tiep", COMBO, "Combo Giao tiếp",
        "Lộ trình Trung cấp + Haru Nói 30 ngày: học bài rồi nói thật với Haru, một lần thanh toán.",
        379_000, _TRUNG_CAP, order=10, features=("talk", "present", "debate"),
        includes=("pack_9_41", "speak_30"),
    ),
    Product(
        "combo_topik2", COMBO, "Combo Luyện thi TOPIK II",
        "Lộ trình TOPIK II nâng cao + Pass Luyện thi 90 ngày: học và luyện đề trọn một mùa thi.",
        429_000, _NANG_CAO, order=11, includes=("pack_42_71", "exam_pass_90"),
    ),
    Product(
        "combo_tron_goi", COMBO, "Combo Trọn gói",
        "Trọn bộ bài học + Haru Nói 90 ngày + Pass Luyện thi 90 ngày: mọi thứ Haru có.",
        999_000, ((_FIRST_PAID, _LAST),), order=12, features=("talk", "present", "debate"),
        includes=("pack_all", "speak_90", "exam_pass_90"),
    ),
    # ---- retired: no longer sold, the rights bought with them stay -------------------------
    Product(
        "pack_quan_he", LESSON_PACK, "Quan hệ & Không gian sống",
        f"{_span(_at(16), _at(27))}, gồm bài ôn tập chủ đề).", 39_000, ((_at(16), _at(27)),), order=90, active=False, retired=True,
    ),
    Product(
        "pack_nhap_canh", LESSON_PACK, "Nhập cảnh & Cư trú",
        f"{_span(_at(28), _at(33))}, gồm bài ôn tập chủ đề).", 29_000, ((_at(28), _at(33)),), order=91, active=False, retired=True,
    ),
    Product(
        "pack_cong_so", LESSON_PACK, "Đời sống xã hội & Công sở",
        f"{_span(_at(34), _at(41))}, gồm bài ôn tập và đề thi thử TOPIK II mức 4).", 35_000, ((_at(34), _at(41)),), order=92,
        active=False, retired=True,
    ),
    Product(
        "pack_xa_hoi", LESSON_PACK, "Xã hội, Tư tưởng & Chuyên ngành",
        f"{_span(_at(50), _LAST)}).", 59_000, ((_at(50), _LAST),), order=93, active=False, retired=True,
    ),
    Product(
        "combo_3_packs", LESSON_PACK, "Combo 3 gói",
        f"{_span(_FIRST_PAID, _at(33))}).", 79_000, _PACKS, order=94, active=False, retired=True,
    ),
    Product(
        "speak_pass_30", FEATURE_PASS, "Haru Nói 30 ngày (gói cũ)",
        "Trò chuyện, Trình bày, Tranh luận trong giới hạn phút mỗi ngày, 30 ngày.",
        79_000, days=30, order=95, features=("talk", "present", "debate"), active=False, retired=True,
    ),
    Product(
        "speak_pass_90", FEATURE_PASS, "Haru Nói 90 ngày (gói cũ)",
        "Trò chuyện, Trình bày, Tranh luận trong giới hạn phút mỗi ngày, 90 ngày.",
        199_000, days=90, order=96, features=("talk", "present", "debate"), active=False, retired=True,
    ),
)
DEFAULTS: tuple[Product, ...] = PRODUCTS

_BY_CODE = {p.code: p for p in PRODUCTS}

# What an admin may change, and the bounds a price must stay in (payOS takes whole VND).
MIN_AMOUNT = 2_000
MAX_AMOUNT = 50_000_000
EDITABLE = ("amount", "compare_at", "title_vi", "blurb_vi", "active")


def apply_settings(rows: dict[str, dict[str, Any]]) -> None:
    """Replace the effective catalogue: the defaults above with each product's admin setting on top
    (`rows`: product code -> the non-null fields of billing.product_setting). Unknown codes and
    out-of-bounds prices are ignored, so a bad row can never make a product free."""
    global PRODUCTS, _BY_CODE
    out = []
    for p in DEFAULTS:
        r = rows.get(p.code) or {}
        changes: dict[str, Any] = {}
        amount = r.get("amount")
        if isinstance(amount, int) and MIN_AMOUNT <= amount <= MAX_AMOUNT:
            changes["amount"] = amount
        compare_at = r.get("compare_at")
        if isinstance(compare_at, int) and compare_at > changes.get("amount", p.amount):
            changes["compare_at"] = compare_at
        for k in ("title_vi", "blurb_vi"):
            if isinstance(r.get(k), str) and r[k].strip():
                changes[k] = r[k].strip()
        if isinstance(r.get("active"), bool) and not p.retired:
            changes["active"] = r["active"]
        out.append(replace(p, **changes) if changes else p)
    PRODUCTS = tuple(out)
    _BY_CODE = {p.code: p for p in PRODUCTS}


def listed() -> list[Product]:
    """What the price page shows and what can be ordered: the products on sale, in page order."""
    return sorted((p for p in PRODUCTS if p.active), key=lambda p: p.order)


def default(code: str) -> Product | None:
    return next((p for p in DEFAULTS if p.code == code), None)


def get(code: str) -> Product | None:
    """A product, on sale or not (a right bought before it was taken off sale still opens)."""
    return _BY_CODE.get(code)


def parts(product: Product) -> list[Product]:
    """What paying for this product grants: a combo's products (as they are sold today), else the
    product itself."""
    if product.kind != COMBO:
        return [product]
    return [p for code in product.includes if (p := get(code)) is not None]


def list_total(product: Product) -> int:
    """A combo's products bought one by one, at today's prices (its struck-through price)."""
    return sum(p.amount for p in parts(product)) if product.kind == COMBO else product.amount


def feature_passes(feature: str) -> list[str]:
    """Codes of the products on sale that open `feature`, cheapest first."""
    return [p.code for p in sorted(listed(), key=lambda p: p.amount) if p.kind == FEATURE_PASS and feature in p.features]


def is_free(sort_order: int | None) -> bool:
    """The lessons everyone may open. A lesson without a position is not free."""
    return bool(sort_order) and sort_order <= FREE_LESSON_MAX  # type: ignore[operator]


def unlock_products(sort_order: int | None) -> list[str]:
    """Codes of the things that open this lesson, cheapest first ([] for a free lesson)."""
    if is_free(sort_order):
        return []
    return [p.code for p in sorted(listed(), key=lambda p: p.amount) if p.kind == LESSON_PACK and p.covers(sort_order)]
