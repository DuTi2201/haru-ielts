"""Merge the editorial articles' duplicate vocabulary/grammar cards into the course cards.

Every card with `lesson_id IS NULL` (135 words, 70 patterns on the dump of 2026-10) belongs to an
editorial article: apply_editorial_batch files each confirmed AI proposal as a new row and
appends its id to `editorial_article.vocab_ids/grammar_ids`. They are NOT orphans to delete —
the editorial reader shows them. What is wrong is that the same item was filed again and again:

* 18 words and ~45 patterns repeat a card a lesson already teaches (현상 ×4 next to the lesson's
  현상, -기 마련이다 ×10 next to cong-so-04's card). A learner who studies the article practises a
  second, unscheduled copy instead of the course card.
* the copies among themselves repeat (딜레마 ×2, -(으)ㄹ수록 ×3 …), written in five notations.
* a few proposals are wrong: a typo (-는 것처러), a pattern that is not one (-는 장치 아니다:
  장치 is a noun), an example that does not use the pattern (을/를 테지요).

So, for each such row: every reference (editorial arrays, corpus_item.grammar_point_ids,
item_state, grammar_competency, error_log, talk_note) is pointed at the surviving card, and the
duplicate row is deleted. A learner who already reviews both keeps the course card's state.
Rows this table does not name and that do not repeat anything are left exactly as they are.

Matching is by text (hangul / pattern) and target lesson slug, never by id, so it is safe on any
database; a target that does not exist is skipped. Not reversible (deleted rows carry no data the
surviving card lacks); downgrade is a no-op.

Revision ID: c5e1a7d3f9b2
Revises: b3d7f1a9c5e2
"""
from alembic import op
from sqlalchemy import text

revision = "c5e1a7d3f9b2"
down_revision = "b3d7f1a9c5e2"
branch_labels = None
depends_on = None

TRACKS = ("beginner", "intermediate", "advanced")

# orphan pattern (exact) -> ("lesson", lesson slug, lesson card pattern) | ("rename", pattern, example or None) | ("drop",)
GRAMMAR = {
    "-ㄹ/을 뿐더러": ("lesson", "xa-hoi-16-y-hoc-suc-khoe", "V/A + -(으)ㄹ 법하다 · V/A + -(으)ㄹ 뿐더러"),
    **{p: ("lesson", "cong-so-01-tuyen-dung-hop-dong", "V/A + -(으)ㄹ 뿐만 아니라 · N + 뿐만 아니라") for p in (
        "V + ㄹ/을 뿐만 아니라", "-ㄹ/을 뿐만 아니라", "V + -ㄹ/을 뿐만 아니라",
        "A/V-ㄹ/을 뿐만 아니라 / V-는 것은 물론이고", "V-(으)ㄹ 뿐만 아니라", "-뿐 아니라")},
    **{p: ("lesson", "xa-hoi-02-them-va-gioi-han", "V/A + -(으)ㄹ 뿐이다 · N + 일 뿐이다") for p in ("-ㄹ/을 뿐이다", "V-(으)ㄹ 뿐이다")},
    **{p: ("lesson", "quan-he-09-thoi-tiet-2", "V/A + -(으)ㄹ수록 · N + 일수록") for p in ("-ㄹ수록", "V-ㄹ/을 수록", "V-(으)ㄹ수록")},
    **{p: ("lesson", "quan-he-10-du-lich", "V/A + -(으)ㄹ 수밖에 없다") for p in ("-ㄹ/을 수밖에 없다", "V/A + 을/를 수밖에 없다")},
    **{p: ("lesson", "cong-so-04-dong-nghiep-giao-tiep", "V/A + -기 마련이다") for p in (
        "A/V-기 마련이다", "-기 마련이다", "V + -기 마련이다", "V + 기 마련이다")},
    "V + 는 길에": ("lesson", "sinh-hoat-05-di-lai", "V + -는 길에"),
    **{p: ("lesson", "sinh-hoat-02-viec-nha", "V + -는 바람에") for p in ("V-는 바람에", "A/V-는 바람에")},
    **{p: ("lesson", "quan-he-03-sinh-nhat-le-tet", "V/A + -(으)ㄴ/는 셈이다") for p in ("-는 셈이다", "V + 는 셈이다")},
    "V-는 반면에": ("lesson", "quan-he-11-ky-nghi-van-hoa", "V/A + -(으)ㄴ/는 반면(에) · N + 인 반면(에)"),
    "V-(으)ㄴ/는 덕분에": ("lesson", "quan-he-11-ky-nghi-van-hoa", "N + 덕분에 · V + -(으)ㄴ/는 덕분에"),
    "-도록 하다": ("lesson", "quan-he-06-hang-xom-rac", "V + -도록 · V + -지 않도록 · V + -도록 하다"),
    **{p: ("lesson", "nhap-canh-05-ve-truong", "V/A + -(으)ㄴ/는지 알다/모르다 · N + 인지") for p in (
        "-는지/은지 알다[모르다]", "A/V-는지 / V-(으)ㄴ지")},
    "N + 조차": ("lesson", "cong-so-04-dong-nghiep-giao-tiep", "N + 마저 · N + 조차"),
    "-을/를 비롯하여": ("lesson", "cong-so-06-truyen-thong-thong-tin", "N + 을/를 비롯해(서) · N + 을/를 비롯한 N"),
    "A/V-는 한편": ("lesson", "xa-hoi-05-van-viet-trang-trong", "V/A + -(으)ㄴ/는 한편 · N + 인 한편"),
    "-은/는 만큼": ("lesson", "xa-hoi-05-van-viet-trang-trong", "V/A + -(으)ㄴ/는 만큼 · V + -(으)ㄹ 만큼 · N + 만큼"),
    **{p: ("lesson", "xa-hoi-10-kinh-te", "N + 에 그치다 · V + -는 데 그치다 · N + 에 불과하다 · V + -(으)ㄹ 따름이다") for p in (
        "N + 에 그치다", "V-는 데 그치다")},
    "N에 비추어 (볼 때)": ("lesson", "xa-hoi-14-lich-su-di-san", "N + (으)로 말미암아 · N + 에 비추어(서) · N + 을/를 거쳐(서)"),
    "V-(으)면서도": ("lesson", "xa-hoi-20-viet-53-54-cap-cao", "V/A + -(으)ㄴ/는 동시에 · V/A + -(으)면서도 · N + 이자 N"),
    # not taught in a lesson: one clean card per pattern (the copies are merged into it below)
    "-는 것처러": ("rename", "V/A + -(으)ㄴ/는 것처럼", "그는 마치 모든 것을 알고 있는 것처럼 이야기했다."),
    "-기와 무관하지 않다": ("rename", "N + 와/과 무관하지 않다", None),
    "V + 기는 어렵다": ("rename", "V + -기(는) 어렵다", None),
    "V/A + 는 데(에)": ("rename", "V + -는 데(에)", None),
    "-는 데에 있다": ("rename", "V/A + -(ㄴ/는)다는 데(에) 있다", None),
    "V-는 데는 실패하다": ("rename", "V + -는 데(에) 실패하다", None),
    "V-는 데 그치지 않다": ("rename", "V + -는 데 그치지 않다", None),
    "-는 데 그치지 않고": ("rename", "V + -는 데 그치지 않다", None),
    "-에 의하면 / -에 의거해": ("rename", "N + 에 의하면", None),
    "N에 의하면": ("rename", "N + 에 의하면", None),
    "-는지, -는지": ("rename", "V/A + -(으)ㄴ/는지, -(으)ㄴ/는지", None),
    "-는지에 대한": ("rename", "V/A + -(으)ㄴ/는지에 대한 N", None),
    "-을/를 넘어": ("rename", "N + 을/를 넘어(서)", None),
    "-을/를 토대로": ("rename", "N + 을/를 토대로", None),
    "-을/를 수단 삼아": ("rename", "N + 을/를 수단 삼아", None),
    "A/V + ~을/를 매개로": ("rename", "N + 을/를 매개로", None),
    "V + ~에 방점을 두다": ("rename", "N + 에 방점을 두다", None),
    "V-(으)ㄴ/는 계기가 되다": ("rename", "N + 이/가 계기가 되다", None),
    "V-(으)ㄹ 정도로": ("rename", "V/A + -(으)ㄹ 정도로", None),
    "V-기만 하다": ("rename", "V + -기만 하다", None),
    "V-(으)ㄴ/는 터인데": ("rename", "V/A + -(으)ㄴ/는 터인데", None),
    "V/A + 는 통에": ("rename", "V + -는 통에", None),
    # not a grammar pattern, or the example does not show it
    "V-는 장치(가/는) 아니다": ("drop",),
    "V + ~는 바야흐로 ... 고 있다": ("drop",),
    "V/A + 을/를 테지요": ("drop",),
}

# every array/column that holds a vocab_item or grammar_point id
_REMAP = {
    "vocab_item": [
        "UPDATE editorial.editorial_article SET vocab_ids = {dedupe_v} WHERE :old = ANY(vocab_ids)",
        "UPDATE public.item_state s SET item_id = :new WHERE item_type = 'vocab_item' AND item_id = :old"
        " AND NOT EXISTS (SELECT 1 FROM public.item_state t WHERE t.learner_id = s.learner_id AND t.item_type = 'vocab_item' AND t.item_id = :new)",
        "DELETE FROM public.item_state WHERE item_type = 'vocab_item' AND item_id = :old",
        "UPDATE public.error_log SET item_id = :new WHERE item_type = 'vocab_item' AND item_id = :old",
        "UPDATE public.talk_note SET vocab_item_id = :new WHERE vocab_item_id = :old",
        "DELETE FROM audio.vocab_item_audio WHERE vocab_item_id = :old",
        "DELETE FROM content.vocab_item WHERE id = :old",
    ],
    "grammar_point": [
        "UPDATE editorial.editorial_article SET grammar_ids = {dedupe_g} WHERE :old = ANY(grammar_ids)",
        "UPDATE corpus.corpus_item SET grammar_point_ids = {dedupe_c} WHERE :old = ANY(grammar_point_ids)",
        "UPDATE public.item_state s SET item_id = :new WHERE item_type = 'grammar_point' AND item_id = :old"
        " AND NOT EXISTS (SELECT 1 FROM public.item_state t WHERE t.learner_id = s.learner_id AND t.item_type = 'grammar_point' AND t.item_id = :new)",
        "DELETE FROM public.item_state WHERE item_type = 'grammar_point' AND item_id = :old",
        "UPDATE public.grammar_competency c SET grammar_id = :new WHERE grammar_id = :old"
        " AND NOT EXISTS (SELECT 1 FROM public.grammar_competency d WHERE d.learner_id = c.learner_id AND d.grammar_id = :new)",
        "DELETE FROM public.grammar_competency WHERE grammar_id = :old",
        "UPDATE public.error_log SET item_id = :new WHERE item_type = 'grammar_point' AND item_id = :old",
        "DELETE FROM content.grammar_point WHERE id = :old",
    ],
}


def _dedupe(col: str) -> str:
    # replace :old by :new (NULL :new = remove it), keep the first occurrence of each id, keep order
    return (
        f"COALESCE((SELECT array_agg(x ORDER BY o) FROM (SELECT x, min(o) AS o FROM unnest("
        f"CASE WHEN CAST(:new AS integer) IS NULL THEN array_remove({col}, :old) ELSE array_replace({col}, :old, CAST(:new AS integer)) END"
        f") WITH ORDINALITY AS u(x, o) GROUP BY x) AS d), '{{}}')"
    )


def _sql(kind: str) -> list:
    fill = {"dedupe_v": _dedupe("vocab_ids"), "dedupe_g": _dedupe("grammar_ids"), "dedupe_c": _dedupe("grammar_point_ids")}
    return [text(s.format(**fill)) for s in _REMAP[kind]]


def _merge(conn, kind: str, old: int, new: int | None) -> None:
    for stmt in _sql(kind):
        conn.execute(stmt, {"old": old, "new": new})


def _lesson_cards(conn, table: str, key: str) -> dict[str, tuple[int, int, int]]:
    """course card text -> (track index, sort_order, id) of its earliest lesson."""
    rows = conn.execute(text(
        f"SELECT c.{key}, l.track, l.sort_order, c.id, l.slug FROM content.{table} c JOIN content.lesson l ON l.id = c.lesson_id"
    )).all()
    out: dict[str, tuple[int, int, int]] = {}
    for k, track, order, cid, _slug in rows:
        pos = (TRACKS.index(track) if track in TRACKS else 9, order, cid)
        if k not in out or pos < out[k]:
            out[k] = pos
    return out


def upgrade() -> None:
    conn = op.get_bind()

    # words: a copy of a course word -> the course card; copies among themselves -> the oldest
    course = _lesson_cards(conn, "vocab_item", "hangul")
    seen: dict[str, int] = {}
    for vid, hangul in conn.execute(text("SELECT id, hangul FROM content.vocab_item WHERE lesson_id IS NULL ORDER BY id")).all():
        if hangul in course:
            _merge(conn, "vocab_item", vid, course[hangul][2])
        elif hangul in seen:
            _merge(conn, "vocab_item", vid, seen[hangul])
        else:
            seen[hangul] = vid

    # patterns: the curated table first, then copies among themselves -> the oldest
    targets = {
        (slug, pat): gid
        for gid, slug, pat in conn.execute(text(
            "SELECT g.id, l.slug, g.pattern FROM content.grammar_point g JOIN content.lesson l ON l.id = g.lesson_id"
        )).all()
    }
    rows = conn.execute(text("SELECT id, pattern FROM content.grammar_point WHERE lesson_id IS NULL ORDER BY id")).all()
    for gid, pattern in rows:
        rule = GRAMMAR.get(pattern)
        if rule is None:
            continue
        if rule[0] == "lesson":
            target = targets.get((rule[1], rule[2]))
            if target is not None:
                _merge(conn, "grammar_point", gid, target)
        elif rule[0] == "drop":
            _merge(conn, "grammar_point", gid, None)
        else:
            conn.execute(
                text("UPDATE content.grammar_point SET pattern = :p, example_ko = COALESCE(:e, example_ko) WHERE id = :id"),
                {"p": rule[1], "e": rule[2], "id": gid},
            )
    seen = {}
    for gid, pattern in conn.execute(text("SELECT id, pattern FROM content.grammar_point WHERE lesson_id IS NULL ORDER BY id")).all():
        if pattern in seen:
            _merge(conn, "grammar_point", gid, seen[pattern])
        else:
            seen[pattern] = gid


def downgrade() -> None:
    # deleted rows were exact copies of the card that now carries their references
    pass
