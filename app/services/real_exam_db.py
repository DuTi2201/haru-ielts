"""The database side of app.services.real_exam: what a learner has met and answered, the sittings,
the answers, the hints, the summary.

Kept apart from the pure rules so the router reads and writes through one door."""
from __future__ import annotations

import math
import uuid
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ErrorLog, GrammarPoint, ItemState, Lesson, Profile, RealExamAttempt, RealExamSet, VocabItem
from app.schemas import (
    RxAnswerIn,
    RxAnswerOut,
    RxBlankResultOut,
    RxCardOut,
    RxCheckOut,
    RxClipOut,
    RxExamDetailOut,
    RxExamOut,
    RxFamilyOut,
    RxFitOut,
    RxGuideOut,
    RxHintOut,
    RxItemStatusOut,
    RxLessonOut,
    RxLessonPickOut,
    RxOverviewOut,
    RxPlanOut,
    RxPointOut,
    RxPrimerFormOut,
    RxPrimerWordOut,
    RxQuestionOut,
    RxRecentOut,
    RxResumeOut,
    RxRubricOut,
    RxScopeIn,
    RxSectionOut,
    RxSelfCheckIn,
    RxSelfCheckOut,
    RxSetOut,
    RxStageOut,
    RxSummaryItemOut,
    RxSummaryOut,
    RxTierOut,
    RxTurnOut,
    RxTypeDetailOut,
    RxTypeStatOut,
)
from app.services import competency_db, real_exam as rx

RESUME_WITHIN = timedelta(days=3)
RECENT_SETS = 5
MAX_NEW_POINTS = 14
MAX_REVIEW_CARDS = 10
MAX_TYPE_POINTS = 14
STAGE_LABEL_VI = {
    "starter": "Mới bắt đầu — ưu tiên các câu ăn chắc",
    "building": "Đang xây nền — làm vững bậc dễ rồi mới lên bậc giữa",
    "solid": "Nền khá vững — có thể thử cả các câu khó",
}
RUNG_OF_TYPE = {"write_fill": 2, "write_chart": 3, "write_essay": 3}  # the competency ladder (see GrammarCompetency)


class NothingToPractice(Exception):
    """Every question in the scope is resting (answered recently) or there are none."""


class NotFound(Exception):
    pass


class Conflict(Exception):
    pass


# --------------------------------------------------------------------- the learner --
@dataclass
class Context:
    """What the rules need to know about one learner, read once per request."""

    bank: rx.Bank
    lex: rx.Lexicon
    met: frozenset[tuple[str, int]]
    seen: dict[str, rx.Seen]
    known_grammar: int
    total_grammar: int
    goal: str | None
    now: datetime
    needs: dict[str, rx.Needs] = field(default_factory=dict)
    fit: dict[str, rx.Fit] = field(default_factory=dict)

    @property
    def stage(self) -> str:
        return rx.stage_of(self.known_grammar, self.total_grammar)

    def standing(self, code: str) -> dict[int, tuple[int, int]]:
        return rx.tier_standing(self.bank.of_type(code), self.seen)


async def load_lexicon(db: AsyncSession) -> rx.Lexicon:
    """The grammar and vocabulary cards of the seeded lessons (those with a slug)."""
    lessons = {
        lid: title
        for lid, title in (await db.execute(select(Lesson.id, Lesson.title).where(Lesson.slug.is_not(None)))).all()
    }
    g = (
        await db.execute(
            select(GrammarPoint.id, GrammarPoint.lesson_id, GrammarPoint.pattern, GrammarPoint.meaning_vi).where(
                GrammarPoint.lesson_id.in_(list(lessons) or [-1])
            )
        )
    ).all()
    v = (
        await db.execute(
            select(VocabItem.id, VocabItem.lesson_id, VocabItem.hangul, VocabItem.meaning_vi).where(
                VocabItem.lesson_id.in_(list(lessons) or [-1])
            )
        )
    ).all()
    return rx.lexicon_of(g, v, lessons)


def seen_map(attempts: list[RealExamAttempt]) -> dict[str, rx.Seen]:
    rows: dict[str, list[tuple[datetime, bool, int]]] = defaultdict(list)
    for a in attempts:
        rows[a.qid].append((a.created_at, a.right, a.hints or 0))
    out: dict[str, rx.Seen] = {}
    for qid, r in rows.items():
        s = rx.seen_of(r)
        if s is not None:
            out[qid] = s
    return out


async def load_context(db: AsyncSession, profile: Profile, now: datetime) -> Context:
    bank = rx.load()
    lex = await load_lexicon(db)
    met = frozenset(
        (t, i)
        for t, i in (
            await db.execute(select(ItemState.item_type, ItemState.item_id).where(ItemState.learner_id == profile.id))
        ).all()
    )
    attempts = list(
        (await db.execute(select(RealExamAttempt).where(RealExamAttempt.learner_id == profile.id))).scalars().all()
    )
    grammar_ids = {g[0] for g in lex.grammar}
    ctx = Context(
        bank=bank,
        lex=lex,
        met=met,
        seen=seen_map(attempts),
        known_grammar=sum(1 for t, i in met if t == "grammar_point" and i in grammar_ids),
        total_grammar=len(grammar_ids),
        goal=profile.goal,
        now=now,
    )
    for qid, it in bank.items.items():
        ctx.needs[qid] = rx.needs_of(it, lex)
        ctx.fit[qid] = rx.fit_of(ctx.needs[qid], met)
    return ctx


# --------------------------------------------------------------------------- outputs --
def guide_out(bank: rx.Bank, code: str) -> RxGuideOut:
    t = bank.types[code]
    return RxGuideOut(
        code=code,
        sec=t.sec,
        name_vi=t.name_vi,
        asks_vi=t.asks_vi,
        steps=t.steps,
        traps=t.traps,
        tips=t.tips,
        gain_vi=t.gain_vi,
        family=t.family,
        family_name_vi=bank.families[t.family].name_vi,
    )


def card_out(ref: rx.CardRef, ctx: Context) -> RxCardOut:
    return RxCardOut(
        kind=ref.kind,
        id=ref.id,
        lesson_id=ref.lesson_id,
        lesson_title=ctx.lex.lessons.get(ref.lesson_id),
        label=ref.label,
        meaning_vi=ref.meaning_vi,
        known=(ref.kind, ref.id) in ctx.met,
        exact=ref.exact,
    )


def _point(kind: str, ko: str, vi: str, refs: tuple[rx.CardRef, ...], ctx: Context) -> RxPointOut:
    cards = [card_out(r, ctx) for r in refs[:3]]
    status = "new" if not refs else "known" if any((r.kind, r.id) in ctx.met for r in refs) else "upcoming"
    return RxPointOut(kind=kind, ko=ko, vi=vi, status=status, cards=cards)  # type: ignore[arg-type]


def points_of(it: rx.Item, ctx: Context) -> list[RxPointOut]:
    """The patterns and the words a question teaches, each with what the lessons say about it."""
    needs = ctx.needs[it.qid]
    out: list[RxPointOut] = []
    seen: set[tuple[str, str]] = set()
    for g, refs in needs.grammar:
        if ("grammar", g.k) not in seen:
            seen.add(("grammar", g.k))
            out.append(_point("grammar", g.k, g.vi, refs, ctx))
    for ko, vi, refs in needs.words:
        if ("word", ko) not in seen:
            seen.add(("word", ko))
            out.append(_point("word", ko, vi, refs, ctx))
    return out


def fit_out(f: rx.Fit) -> RxFitOut:
    return RxFitOut(known=f.known, upcoming=f.upcoming, new=f.new, status=f.status)


def image_url(name: str | None) -> str | None:
    return f"/api/v1/me/real-exam/assets/{name}" if name else None


def question_out(it: rx.Item, ctx: Context, hint_level: int, answered: bool) -> RxQuestionOut:
    s = it.seed
    exam = ctx.bank.exams[it.exam]
    return RxQuestionOut(
        qid=it.qid,
        exam=it.exam,
        exam_short=exam.short,
        sec=it.sec,  # type: ignore[arg-type]
        n=it.n,
        type=it.type,
        type_name=ctx.bank.types[it.type].name_vi,
        tier=it.tier,
        stem=it.stem,
        passage=it.passage,
        given=it.given,
        image_url=image_url(it.img),
        pic=s.pic,
        opts=list(s.opts or []),
        clips=[RxClipOut(who=c.who, voice=c.voice, ko=c.ko) for c in it.clips],  # type: ignore[arg-type]
        bundle_index=it.bundle.index(it.qid),
        bundle_size=len(it.bundle),
        blanks=[b.id for b in s.blanks or []],
        limit=s.limit,
        prompt=s.prompt,
        questions=list(s.questions or []),
        fit=fit_out(ctx.fit[it.qid]),
        hint_level=hint_level,
        answered=answered,
    )


def result_of(att: RealExamAttempt) -> str:
    return rx.result_of(rx.Outcome(att.qid, att.right, att.hints or 0, pending=att.pending))


def _type_stat_out(code: str, ctx: Context) -> RxTypeStatOut:
    items = ctx.bank.of_type(code)
    cands = [rx.Candidate(it, ctx.seen.get(it.qid), ctx.fit[it.qid]) for it in items]
    st = rx.type_stats(code, cands, ctx.now)
    tiers = [RxTierOut(tier=t, solid=a, total=b, is_solid=rx.tier_is_solid(a, b)) for t, (a, b) in st.standing.items()]
    if st.wrong_open:
        nxt = f"{st.wrong_open} câu cần làm lại bằng cách hiểu mới"
    elif st.tried == 0:
        first = min(st.standing, default=1)
        nxt = "Chưa làm — bắt đầu từ bậc 1 (các câu ăn chắc)" if first == 1 else f"Chưa làm — câu dễ nhất ở bậc {first}"
    elif st.cur_tier is None:
        nxt = "Mọi bậc đã vững — kiểm tra lại sau 7 ngày"
    else:
        a, b = st.standing[st.cur_tier]
        nxt = f"Đang làm chắc bậc {st.cur_tier} ({a}/{b} câu vững)"
    return RxTypeStatOut(
        code=code,
        name_vi=ctx.bank.types[code].name_vi,
        sec=ctx.bank.types[code].sec,  # type: ignore[arg-type]
        total=st.total,
        tried=st.tried,
        solid=st.solid,
        to_redo=st.wrong_open,
        open=st.open,
        ready_open=st.ready_open,
        attempts=st.attempts,
        right=st.right,
        cur_tier=st.cur_tier,
        tiers=tiers,
        next_vi=nxt,
    )


def _candidates(ctx: Context, scope: rx.Scope) -> list[rx.Candidate]:
    return [
        rx.Candidate(it, ctx.seen.get(it.qid), ctx.fit[it.qid])
        for it in ctx.bank.items.values()
        if rx.in_scope(it, scope, ctx.bank)
    ]


def _all_type_stats(ctx: Context) -> dict[str, rx.TypeStat]:
    cap = rx.STAGE_TIER_CAP[ctx.stage]
    return {
        code: rx.type_stats(
            code,
            [rx.Candidate(it, ctx.seen.get(it.qid), ctx.fit[it.qid]) for it in ctx.bank.of_type(code)],
            ctx.now,
            cap,
        )
        for code in ctx.bank.types
        if ctx.bank.of_type(code)
    }


def _item_status(it: rx.Item, ctx: Context) -> RxItemStatusOut:
    s = ctx.seen.get(it.qid)
    return RxItemStatusOut(
        qid=it.qid,
        exam=it.exam,
        exam_short=ctx.bank.exams[it.exam].short,
        sec=it.sec,  # type: ignore[arg-type]
        n=it.n,
        type=it.type,
        type_name=ctx.bank.types[it.type].name_vi,
        tier=it.tier,
        status="new" if s is None else s.status,
        fit=ctx.fit[it.qid].status,
        open=rx.due_again(s, ctx.now),
    )


def _exam_note(exam: rx.ExamFile) -> str | None:
    if not exam.omitted:
        return None
    parts = [f"{rx.SEC_NAME_VI[sec]} câu {', '.join(map(str, ns))}" for sec, ns in exam.omitted.items() if ns]
    return ("Đề gốc không công bố: " + "; ".join(parts) + " — nên không có trong bộ này.") if parts else None


# ------------------------------------------------------------------------- overview --
def plan_today(ctx: Context) -> RxPlanOut | None:
    stats = _all_type_stats(ctx)
    code = rx.choose_type_today(ctx.bank, stats, ctx.stage)
    if code is None:
        return None
    st = stats[code]
    name = ctx.bank.types[code].name_vi
    return RxPlanOut(
        scope=RxScopeIn(type=code),
        title_vi=f"Gợi ý hôm nay: {name}",
        why_vi=_why(ctx, code, st),
        size=rx.DEFAULT_SET_SIZE,
    )


def _why(ctx: Context, code: str, st: rx.TypeStat) -> str:
    bits: list[str] = []
    if st.retry_due:
        bits.append(f"{st.retry_due} câu bạn làm sai hoặc phải dùng gợi ý lần trước quay lại để làm chắc")
    if st.tried == 0:
        first = min((a for a in st.standing), default=1)
        bits.append(
            "dạng này bạn chưa làm — bắt đầu từ bậc 1, những câu không được phép mất điểm"
            if first == 1
            else f"dạng này bạn chưa làm — các câu ở đây bắt đầu từ bậc {first}"
        )
    elif st.cur_tier:
        a, b = st.standing[st.cur_tier]
        bits.append(f"đang làm chắc bậc {st.cur_tier} ({a}/{b} câu vững) trước khi lên bậc cao hơn")
    if st.ready_open:
        bits.append(f"{st.ready_open} câu dùng đúng kiến thức bạn đã học")
    return "; ".join(bits).capitalize() + "." if bits else "Một bộ câu mới cho dạng này."


async def lesson_picks(db: AsyncSession, profile: Profile, lesson_id: int, now: datetime) -> RxLessonOut:
    """"Thử sức TOPIK II" of one lesson: the real questions its seed names (`topik2`), each with a
    primer of what is new in it and where the learner stands on it. Raises NotFound for an unknown lesson."""
    lesson = await db.get(Lesson, lesson_id)
    if lesson is None:
        raise NotFound(f"lesson {lesson_id}")
    picks = (lesson.practice or {}).get("topik2") or []
    bank = rx.load()
    wanted = [p for p in picks if p["qid"] in bank.items]
    if not wanted:
        return RxLessonOut(lesson_id=lesson_id, picks=[])
    attempts = list(
        (
            await db.execute(
                select(RealExamAttempt).where(
                    RealExamAttempt.learner_id == profile.id, RealExamAttempt.qid.in_([p["qid"] for p in wanted])
                )
            )
        )
        .scalars()
        .all()
    )
    seen = seen_map(attempts)
    out = []
    for pick in wanted:
        it = bank.items[pick["qid"]]
        words, forms = rx.primer_of(it)
        st = seen.get(it.qid)
        out.append(
            RxLessonPickOut(
                qid=it.qid,
                exam=it.exam,
                exam_title=bank.exams[it.exam].short,
                sec=it.sec,  # type: ignore[arg-type]
                n=it.n,
                type=it.type,
                type_name_vi=bank.types[it.type].name_vi,
                tier=it.tier,
                why_vi=pick["why_vi"],
                words=[RxPrimerWordOut(ko=ko, vi=vi) for ko, vi in words],
                forms=[RxPrimerFormOut(k=k, vi=vi) for k, vi in forms],
                status=st.status if st else "new",
                resting=not rx.due_again(st, now),
            )
        )
    return RxLessonOut(lesson_id=lesson_id, picks=out)


async def overview(db: AsyncSession, profile: Profile, now: datetime) -> RxOverviewOut:
    ctx = await load_context(db, profile, now)
    cap = rx.STAGE_TIER_CAP[ctx.stage]
    stage = RxStageOut(
        key=ctx.stage,  # type: ignore[arg-type]
        label_vi=STAGE_LABEL_VI[ctx.stage],
        known_grammar=ctx.known_grammar,
        total_grammar=ctx.total_grammar,
        tier_cap=cap,
        goal=ctx.goal,
    )
    exams = []
    for exam in ctx.bank.exams.values():
        sections = []
        for sec in rx.SECTIONS:
            items = [i for i in ctx.bank.of_exam(exam.id) if i.sec == sec]
            if items:
                sections.append(
                    RxSectionOut(
                        sec=sec,  # type: ignore[arg-type]
                        name_vi=rx.SEC_NAME_VI[sec],
                        total=len(items),
                        tried=sum(1 for i in items if i.qid in ctx.seen),
                        solid=sum(1 for i in items if i.qid in ctx.seen and ctx.seen[i.qid].status == "solid"),
                    )
                )
        exams.append(RxExamOut(id=exam.id, title=exam.title, short=exam.short, note_vi=_exam_note(exam), sections=sections))
    families = []
    for fam in sorted(ctx.bank.families.values(), key=lambda f: f.order):
        types = [_type_stat_out(c, ctx) for c in ctx.bank.types_of_family(fam.code)]
        if not types:
            continue
        families.append(
            RxFamilyOut(
                code=fam.code,
                sec=fam.sec,
                order=fam.order,
                name_vi=fam.name_vi,
                blurb_vi=fam.blurb_vi,
                gain_vi=fam.gain_vi,
                total=sum(t.total for t in types),
                tried=sum(t.tried for t in types),
                solid=sum(t.solid for t in types),
                types=types,
            )
        )
    sets = list(
        (
            await db.execute(
                select(RealExamSet)
                .where(RealExamSet.learner_id == profile.id)
                .order_by(RealExamSet.created_at.desc())
                .limit(20)
            )
        )
        .scalars()
        .all()
    )
    resume = None
    for s in sets:
        if s.finished_at is None and now - s.created_at <= RESUME_WITHIN:
            done = await _done_count(db, s.id)
            resume = RxResumeOut(set_id=s.id, title_vi=s.title, done=done, total=len(s.qids))
            break
    recent = []
    for s in [x for x in sets if x.finished_at is not None][:RECENT_SETS]:
        atts = await _attempts_of(db, s.id)
        counts = _counts(atts)
        recent.append(
            RxRecentOut(
                set_id=s.id,
                title_vi=s.title,
                finished_at=s.finished_at,
                solid=counts["solid"],
                aided=counts["aided"],
                wrong=counts["wrong"] + counts["pending"],
                total=len(s.qids),
            )
        )
    return RxOverviewOut(
        stage=stage, today=plan_today(ctx), resume=resume, exams=exams, families=families, recent=recent
    )


async def type_detail(db: AsyncSession, profile: Profile, code: str, now: datetime) -> RxTypeDetailOut:
    ctx = await load_context(db, profile, now)
    if code not in ctx.bank.types or not ctx.bank.of_type(code):
        raise NotFound(code)
    items = sorted(ctx.bank.of_type(code), key=lambda i: (i.tier, i.exam, i.n))
    # what this type keeps asking for, counted across its questions
    count: dict[tuple[str, str], int] = defaultdict(int)
    rep: dict[tuple[str, str], RxPointOut] = {}
    for it in items:
        for p in points_of(it, ctx):
            key = (p.kind, p.ko)
            count[key] += 1
            rep.setdefault(key, p)
    ranked = sorted(rep, key=lambda k: (-count[k], rep[k].status != "known", k))[:MAX_TYPE_POINTS]
    return RxTypeDetailOut(
        guide=guide_out(ctx.bank, code),
        stat=_type_stat_out(code, ctx),
        items=[_item_status(i, ctx) for i in items],
        points=[rep[k] for k in ranked],
    )


async def exam_detail(db: AsyncSession, profile: Profile, exam_id: str, now: datetime) -> RxExamDetailOut:
    ctx = await load_context(db, profile, now)
    exam = ctx.bank.exams.get(exam_id)
    if exam is None:
        raise NotFound(exam_id)
    items = sorted(ctx.bank.of_exam(exam_id), key=lambda i: (rx.SECTIONS.index(i.sec), i.n))
    return RxExamDetailOut(id=exam.id, title=exam.title, note_vi=_exam_note(exam), items=[_item_status(i, ctx) for i in items])


# ---------------------------------------------------------------------------- sittings --
async def _attempts_of(db: AsyncSession, set_id: uuid.UUID) -> list[RealExamAttempt]:
    return list(
        (await db.execute(select(RealExamAttempt).where(RealExamAttempt.set_id == set_id).order_by(RealExamAttempt.created_at)))
        .scalars()
        .all()
    )


async def _done_count(db: AsyncSession, set_id: uuid.UUID) -> int:
    return len(await _attempts_of(db, set_id))


def _counts(attempts: list[RealExamAttempt]) -> dict[str, int]:
    c = {"solid": 0, "aided": 0, "wrong": 0, "pending": 0}
    for a in attempts:
        c[result_of(a)] += 1
    return c


def _set_title_why(ctx: Context, scope: rx.Scope, chosen: list[rx.Item], auto: bool) -> tuple[str, str]:
    bank = ctx.bank
    if scope.qids:
        return "Các câu bạn chọn", "Bạn tự chọn các câu này."
    redo = sum(1 for it in chosen if ctx.seen.get(it.qid) is not None)
    fresh = len(chosen) - redo
    parts: list[str] = []
    if redo:
        parts.append(f"{redo} câu làm lại (sai hoặc dùng gợi ý lần trước)")
    if fresh:
        tiers = sorted({it.tier for it in chosen if ctx.seen.get(it.qid) is None})
        text = f"{fresh} câu mới ở bậc " + ", ".join(map(str, tiers))
        if 1 in tiers:
            text += " (bậc 1 là các câu không được mất điểm)"
        parts.append(text)
    why = "; ".join(parts).capitalize() + "."
    if scope.type:
        name = bank.types[scope.type].name_vi
        return (f"Gợi ý hôm nay: {name}" if auto else name), why
    if scope.family:
        return bank.families[scope.family].name_vi, why
    where = []
    if scope.sec:
        where.append(rx.SEC_NAME_VI[scope.sec])
    if scope.exam:
        where.append(bank.exams[scope.exam].short)
    return " · ".join(where) or "Luyện đề", why


async def make_set(db: AsyncSession, profile: Profile, body: RxScopeIn, now: datetime) -> RealExamSet:
    ctx = await load_context(db, profile, now)
    bank = ctx.bank
    if body.type and body.type not in bank.types:
        raise NotFound(body.type)
    if body.family and body.family not in bank.families:
        raise NotFound(body.family)
    if body.exam and body.exam not in bank.exams:
        raise NotFound(body.exam)
    for q in body.qids:
        if q not in bank.items:
            raise NotFound(q)
    scope = rx.Scope(type=body.type, family=body.family, sec=body.sec, exam=body.exam, qids=tuple(body.qids))
    auto = not (scope.type or scope.family or scope.sec or scope.exam or scope.qids)
    size = min(body.size or rx.DEFAULT_SET_SIZE, rx.MAX_SET_SIZE)
    if scope.qids:
        chosen = [bank.items[q] for q in body.qids][:size]
    else:
        if auto:
            ranked = rx.rank_types(bank, _all_type_stats(ctx), ctx.stage)
            if not ranked:
                raise NothingToPractice()
            scope = rx.Scope(type=ranked[0])
            chosen = []
            cap = rx.STAGE_TIER_CAP[ctx.stage]
            for code in ranked:  # the best type first; a type with few questions left is topped up from the next ones
                if len(chosen) >= size:
                    break
                pool = _candidates(ctx, rx.Scope(type=code))
                chosen += rx.pick_questions(
                    bank, pool, {code: ctx.standing(code)}, size=size - len(chosen), now=now, tier_cap=cap
                )
        else:
            pool = _candidates(ctx, scope)
            if body.redo_wrong:
                pool = [c for c in pool if c.seen is not None and c.seen.status != "solid"]
                now_for_pick = now + rx.REASK_SOLID  # an asked redo does not wait for the rest
            else:
                now_for_pick = now
            standing = {code: ctx.standing(code) for code in {c.it.type for c in pool}}
            chosen = rx.pick_questions(bank, pool, standing, size=size, now=now_for_pick)
    if not chosen:
        raise NothingToPractice()
    title, why = _set_title_why(ctx, scope, chosen, auto)
    row = RealExamSet(
        learner_id=profile.id,
        title=title[:200],
        why=why,
        scope={"type": scope.type, "family": scope.family, "sec": scope.sec, "exam": scope.exam, "qids": list(scope.qids)},
        qids=[it.qid for it in chosen],
        hints={},
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def get_set(db: AsyncSession, profile: Profile, set_id: uuid.UUID) -> RealExamSet:
    row = await db.get(RealExamSet, set_id)
    if row is None or row.learner_id != profile.id:
        raise NotFound(str(set_id))
    return row


async def set_out(db: AsyncSession, profile: Profile, row: RealExamSet, now: datetime) -> RxSetOut:
    ctx = await load_context(db, profile, now)
    attempts = await _attempts_of(db, row.id)
    answered = {a.qid for a in attempts}
    items = [ctx.bank.items[q] for q in row.qids if q in ctx.bank.items]
    codes = list(dict.fromkeys(i.type for i in items))
    return RxSetOut(
        id=row.id,
        title_vi=row.title,
        why_vi=row.why,
        created_at=row.created_at,
        finished=row.finished_at is not None,
        done=len(answered),
        total=len(items),
        guides=[guide_out(ctx.bank, c) for c in codes],
        questions=[question_out(i, ctx, int((row.hints or {}).get(i.qid, 0)), i.qid in answered) for i in items],
    )


async def open_hint(db: AsyncSession, profile: Profile, row: RealExamSet, qid: str, level: int) -> RxHintOut:
    if qid not in row.qids:
        raise NotFound(qid)
    if await _attempt_of(db, row.id, qid) is not None:
        raise Conflict("Câu này đã trả lời.")
    it = rx.load().items[qid]
    data = rx.hint(it, level)
    hints = dict(row.hints or {})
    hints[qid] = max(int(hints.get(qid, 0)), level)
    row.hints = hints  # a new dict: the change is seen
    await db.commit()
    return RxHintOut(**data)


# ----------------------------------------------------------------------------- answers --
async def _attempt_of(db: AsyncSession, set_id: uuid.UUID, qid: str) -> RealExamAttempt | None:
    return (
        await db.execute(select(RealExamAttempt).where(RealExamAttempt.set_id == set_id, RealExamAttempt.qid == qid))
    ).scalar_one_or_none()


def _example(it: rx.Item) -> str:
    return (it.passage or it.stem or it.qid).replace("\n", " ")[:300]


def _exact_known_grammar(it: rx.Item, ctx: Context) -> list[int]:
    ids: list[int] = []
    for _g, refs in ctx.needs[it.qid].grammar:
        for r in refs:
            if r.exact and ("grammar_point", r.id) in ctx.met and r.id not in ids:
                ids.append(r.id)
    return ids


async def _record_outcome(db: AsyncSession, profile: Profile, ctx: Context, it: rx.Item, att: RealExamAttempt) -> None:
    """A wrong answer goes to the "điểm yếu" log under each lesson card of the same pattern that the
    learner has met; an answer with no hint, right or wrong, is one more outcome on those cards'
    competency ladder. An answer that needed a hint says nothing sure about the card, so it is skipped."""
    cards = _exact_known_grammar(it, ctx)
    if not att.right:
        refs = cards[:2] or [None]
        for gid in refs:
            db.add(
                ErrorLog(
                    learner_id=profile.id,
                    skill=rx.SKILL_OF[it.sec],
                    error_type=it.type,
                    example_ko=_example(it),
                    item_type="grammar_point" if gid else None,
                    item_id=gid,
                    mode="exam",
                    detail={"qid": it.qid, "chosen": att.chosen, "ans": it.seed.ans, "hints": att.hints},
                )
            )
    if (att.hints or 0) == 0 and cards:
        await competency_db.record_outcomes(db, profile.id, cards, RUNG_OF_TYPE.get(it.type, 0), att.right)


async def answer(db: AsyncSession, profile: Profile, row: RealExamSet, body: RxAnswerIn, now: datetime) -> RxAnswerOut:
    if body.qid not in row.qids:
        raise NotFound(body.qid)
    ctx = await load_context(db, profile, now)
    it = ctx.bank.items[body.qid]
    existing = await _attempt_of(db, row.id, body.qid)
    if existing is not None:  # answered already (a second tap, a reload): show the same
        return await _answer_out(db, ctx, row, it, existing)
    hints = int((row.hints or {}).get(it.qid, 0))
    att = RealExamAttempt(
        learner_id=profile.id,
        set_id=row.id,
        qid=it.qid,
        qtype=it.type,
        tier=it.tier,
        hints=hints,
        correct=False,
        pending=False,
    )
    if it.is_mcq:
        att.chosen = body.choice
        att.correct = rx.grade_choice(it, body.choice)
    elif it.type == "write_fill":
        results = rx.grade_blanks(it, body.answers)
        att.answer = {b.id: text for b, text, _ok in results}
        att.correct = all(ok for _b, _t, ok in results)
        att.pending = not att.correct
        att.detail = {"matched": {b.id: ok for b, _t, ok in results}}
    else:
        text = (body.text or "").strip()
        checks = rx.check_writing(it, text)
        att.answer = {"text": text}
        att.pending = True
        att.detail = {"checks": [{"label": c.label, "ok": c.ok, "note": c.note} for c in checks]}
    db.add(att)
    if not att.pending:
        await _record_outcome(db, profile, ctx, it, att)
    await db.flush()
    await _maybe_finish(db, row, now)
    await db.commit()
    await db.refresh(att)
    return await _answer_out(db, ctx, row, it, att)


async def _maybe_finish(db: AsyncSession, row: RealExamSet, now: datetime) -> None:
    done = {a.qid for a in await _attempts_of(db, row.id)}
    if row.finished_at is None and set(row.qids) <= done:
        row.finished_at = now


async def self_check(
    db: AsyncSession, profile: Profile, attempt_id: uuid.UUID, body: RxSelfCheckIn, now: datetime
) -> RxSelfCheckOut:
    att = await db.get(RealExamAttempt, attempt_id)
    if att is None or att.learner_id != profile.id:
        raise NotFound(str(attempt_id))
    if not att.pending:
        raise Conflict("Câu này đã được chấm.")
    ctx = await load_context(db, profile, now)
    it = ctx.bank.items[att.qid]
    right = total = 0
    if it.type == "write_fill":
        if body.ok is None:
            raise Conflict("Cần cho biết bài viết của bạn đúng hay chưa.")
        att.self_ok = body.ok
        right, total = (1, 1) if body.ok else (0, 1)
    else:
        rubric = it.seed.rubric or []
        ticks = list(body.rubric_ok or [])
        if len(ticks) != len(rubric):
            raise Conflict("Cần tick đủ các tiêu chí.")
        right, total = sum(1 for t in ticks if t), len(rubric)
        length_ok = all(c.get("ok") for c in (att.detail or {}).get("checks", []) if c.get("label") == "Độ dài")
        att.self_ok = right >= math.ceil(rx.SOLID_SHARE * total) and length_ok
        att.detail = {**(att.detail or {}), "rubric_ok": ticks}
    att.pending = False
    await _record_outcome(db, profile, ctx, it, att)
    await db.commit()
    return RxSelfCheckOut(attempt_id=att.id, result=result_of(att), right=right, total=total)  # type: ignore[arg-type]


def _lines(it: rx.Item) -> list[tuple[str, str]]:
    ko = (it.passage or "").split("\n") if it.passage else []
    vi = it.tr_lines
    if ko and len(vi) == len(ko):
        return list(zip(ko, vi))
    return [(k, "") for k in ko]


def _turns(it: rx.Item) -> list[RxTurnOut]:
    """The script, turn by turn, with its Vietnamese (the translation keeps one line per turn, each
    starting with who speaks) and the voice of every turn that is spoken."""
    turns = it.turns
    vi = it.tr_lines
    out: list[RxTurnOut] = []
    for i, (who, ko) in enumerate(turns):
        text = vi[i].split(": ", 1)[-1] if len(vi) == len(turns) else None
        spoken = rx.clips_of([(who, ko)])
        out.append(RxTurnOut(who=who, ko=ko, vi=text, voice=spoken[0].voice if spoken else None))
    return out


async def _answer_out(db: AsyncSession, ctx: Context, row: RealExamSet, it: rx.Item, att: RealExamAttempt) -> RxAnswerOut:
    s = it.seed
    guide = ctx.bank.types[it.type]
    done = await _done_count(db, row.id)
    notes = {k: v for k, v in s.wrong.items()}
    if s.ans:
        notes[str(s.ans)] = ""
    blanks: list[RxBlankResultOut] = []
    if it.type == "write_fill":
        matched = (att.detail or {}).get("matched", {})
        for b in s.blanks or []:
            blanks.append(
                RxBlankResultOut(
                    id=b.id,
                    text=(att.answer or {}).get(b.id, ""),
                    matched=bool(matched.get(b.id)),
                    sample=b.model,
                    accepted=b.accepted[:8],
                    why=b.why,
                    gram=[g.model_dump() for g in b.gram],
                    traps=b.traps,
                )
            )
    checks = [RxCheckOut(**c) for c in (att.detail or {}).get("checks", [])]
    data = list(zip(s.data or [], s.dataTr or [])) if s.data else []
    return RxAnswerOut(
        attempt_id=att.id,
        qid=it.qid,
        result=result_of(att),  # type: ignore[arg-type]
        hints=att.hints or 0,
        chosen=att.chosen,
        ans=s.ans,
        why=s.why,
        option_notes=notes,
        options_vi=list(s.ov or []),
        passage_lines=_lines(it) if it.sec != "L" or it.passage else [],
        turns=_turns(it) if it.sec == "L" else [],
        given_vi=it.given_tr,
        points=points_of(it, ctx),
        take=s.take or "",
        guide_tip=guide.tips[0] if guide.tips else None,
        blanks=blanks,
        checks=checks,
        sample=s.model,
        sample_vi=s.modelTr,
        data=data,
        phrases=[p.model_dump() for p in s.phrases or []],
        rubric=[RxRubricOut(k=r.k, w=r.w) for r in s.rubric or []],
        tips=s.tips,
        needs_self_check=att.pending,
        done=done,
        total=len(row.qids),
    )


async def set_answers(db: AsyncSession, profile: Profile, row: RealExamSet, now: datetime) -> list[RxAnswerOut]:
    """The explanation of every question of a sitting that has been answered (to pick a sitting up again)."""
    ctx = await load_context(db, profile, now)
    out = []
    for a in await _attempts_of(db, row.id):
        it = ctx.bank.items.get(a.qid)
        if it is not None:
            out.append(await _answer_out(db, ctx, row, it, a))
    return out


# ----------------------------------------------------------------------------- summary --
async def summary(db: AsyncSession, profile: Profile, row: RealExamSet, now: datetime) -> RxSummaryOut:
    ctx = await load_context(db, profile, now)
    attempts = {a.qid: a for a in await _attempts_of(db, row.id)}
    items: list[RxSummaryItemOut] = []
    counts = {"solid": 0, "aided": 0, "wrong": 0, "pending": 0}
    review: dict[tuple[str, int], RxCardOut] = {}
    points: dict[tuple[str, str], RxPointOut] = {}
    types: list[str] = []
    for q in row.qids:
        it = ctx.bank.items.get(q)
        a = attempts.get(q)
        if it is None or a is None:
            continue
        res = result_of(a)
        counts[res] += 1
        if it.type not in types:
            types.append(it.type)
        items.append(
            RxSummaryItemOut(
                qid=q,
                n=it.n,
                exam_short=ctx.bank.exams[it.exam].short,
                sec=it.sec,  # type: ignore[arg-type]
                type=it.type,
                type_name=ctx.bank.types[it.type].name_vi,
                tier=it.tier,
                result=res,  # type: ignore[arg-type]
                hints=a.hints or 0,
                take=it.seed.take or "",
            )
        )
        for p in points_of(it, ctx):
            points.setdefault((p.kind, p.ko), p)
            if res != "solid":
                for c in p.cards:
                    if c.exact:
                        review.setdefault((c.kind, c.id), c)
    answered = len(items)
    order = {"new": 0, "upcoming": 1, "known": 2}
    new_points = sorted(
        (p for p in points.values() if p.status != "known"), key=lambda p: (order[p.status], p.kind != "grammar", p.ko)
    )
    to_review = sorted(review.values(), key=lambda c: (not c.known, c.label))[:MAX_REVIEW_CARDS]
    upcoming = [c.label for c in to_review if not c.known]
    type_stats = [_type_stat_out(c, ctx) for c in types]
    cur_done = bool(items) and all(
        rx.tier_is_solid(*ctx.standing(it.type).get(it.tier, (0, 0)))
        for it in (ctx.bank.items[i.qid] for i in items)
    )
    total = len(row.qids)
    head = [f"{counts['solid']}/{total} câu làm chắc, không cần gợi ý"]
    if counts["aided"]:
        head.append(f"{counts['aided']} câu đúng nhờ gợi ý")
    if counts["wrong"]:
        head.append(f"{counts['wrong']} câu cần làm lại")
    if counts["pending"]:
        head.append(f"{counts['pending']} bài viết chưa tự chấm")
    names = [ctx.bank.types[c].name_vi for c in types]
    if len(types) == 1:
        value = f"Bạn vừa luyện «{names[0]}»: {ctx.bank.types[types[0]].gain_vi}"
    elif types:
        value = f"Bạn vừa luyện {len(types)} dạng ({', '.join(names)})."
    else:
        value = "Chưa có câu nào được trả lời."
    n_new = sum(1 for p in new_points if p.status == "new")
    if n_new:
        value += f" Có {n_new} điểm kiến thức mới (chưa có trong bài học) được giải thích ngay dưới mỗi câu — chọn vài điểm đáng nhớ nhất để ôn."
    return RxSummaryOut(
        set_id=row.id,
        title_vi=row.title,
        finished=row.finished_at is not None,
        total=total,
        answered=answered,
        solid=counts["solid"],
        aided=counts["aided"],
        wrong=counts["wrong"],
        pending=counts["pending"],
        headline_vi=", ".join(head) + ".",
        value_vi=value,
        items=items,
        new_points=new_points[:MAX_NEW_POINTS],
        to_review=to_review,
        types=type_stats,
        next_vi=rx.next_step(counts, cur_done, upcoming),
    )


async def finish_set(db: AsyncSession, row: RealExamSet, now: datetime) -> None:
    """Close a sitting the learner leaves with questions unanswered (they stay unanswered)."""
    if row.finished_at is None:
        row.finished_at = now
        await db.commit()
