"""Practice that feeds on mistakes: the weakness report, mini-drills made of real
exam questions, and "viết câu 51–52" exercises made from the learner's own cards.

Every wrong answer lands in `error_log` (the review router writes the card ones,
this router the exam and writing ones); app.services.weakness turns the log into
the report. Nothing here predicts an exam score.
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import _problem, get_current_profile, require_exam_pass, study_day
from app.api.routers.content import _word_sources, _lesson_item_keys, _lesson_order, _schedule_of
from app.db import get_db
from app.models import (
    ErrorLog,
    ExamAttempt,
    ExamItem,
    ExamPaper,
    ExamPassage,
    GrammarPoint,
    ItemState,
    Job,
    Lesson,
    LessonExerciseResult,
    Profile,
    QuestionType,
    VocabItem,
    WritingDrill,
)
from app.schemas import (
    ExamAccuracyOut,
    ExamAnswerOut,
    ExamAnswerRequest,
    ExamDrillOut,
    ExamDrillQuestion,
    MistakeBookOut,
    MistakeGrammarOut,
    MistakeLessonOut,
    MistakeOut,
    MistakeUnderstoodRequest,
    WeakFamilyOut,
    WeakItemOut,
    WeaknessesOut,
    WeakTypeOut,
    WritingAnswersRequest,
    WritingDrillOut,
    WritingDrillStartOut,
    WritingDrillStartRequest,
    WritingPromptOut,
    WritingResultOut,
)
from app.services import exam_drill, lesson_seed, mistake_book, srs, weakness, writing_drill
from app.workers.tasks import generate_writing_drill, grade_writing_drill

router = APIRouter(prefix="/me", tags=["practice"])

MAX_NEW_DRILLS_PER_DAY = 12  # each one costs the model calls of a whole exercise
STALE_AFTER = timedelta(minutes=10)  # a job that has not finished by then is treated as dead
MAX_ANSWER_CHARS = 200


# ------------------------------------------------------------------ exam bank --
def _bank_query():
    """Confirmed reading questions with everything the drill needs, one row each."""
    return (
        select(
            ExamItem,
            QuestionType.code,
            QuestionType.name_vi,
            QuestionType.skill,
            ExamPassage.kind,
            ExamPassage.body_ko,
            ExamPaper.session_label,
        )
        .join(QuestionType, QuestionType.id == ExamItem.qtype_id)
        .join(ExamPaper, ExamPaper.id == ExamItem.paper_id)
        .outerjoin(ExamPassage, ExamPassage.id == ExamItem.passage_id)
        .where(
            ExamItem.answer.isnot(None),
            ExamItem.answer_source == "editor",
            QuestionType.skill == exam_drill.READING_SKILL,
            QuestionType.active.is_(True),
        )
    )


def _candidate(row) -> exam_drill.Candidate:
    item, code, _name, skill, passage_kind, passage_ko, _label = row
    return exam_drill.Candidate(
        item_id=item.id,
        number=item.number,
        qtype_code=code,
        stem_ko=item.stem_ko,
        options=item.options,
        answer=item.answer,
        answer_source=item.answer_source,
        skill=skill,
        passage_kind=passage_kind,
        passage_ko=passage_ko,
        instruction_ko=item.instruction_ko or "",
        passage_linked=item.passage_id is not None,
    )


@router.get("/exam-drill", response_model=ExamDrillOut, dependencies=[Depends(require_exam_pass)])
async def get_exam_drill(
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
    n: Annotated[int, Query(ge=1, le=exam_drill.MAX_DRILL_SIZE)] = exam_drill.DEFAULT_DRILL_SIZE,
):
    """A few real exam questions to answer now: ones the learner got wrong before
    first, then ones never asked, the weakest question types first. Only reading
    questions whose answer was read from an answer key are offered; the key is
    never sent — answers are checked by POST /me/exam-drill/answers."""
    now = datetime.now(timezone.utc)
    rows = (await db.execute(_bank_query())).all()
    by_id = {row[0].id: row for row in rows}
    candidates = [_candidate(row) for row in rows]
    usable = [c for c in candidates if exam_drill.usable(c)]

    since = now - timedelta(days=30)
    attempt_rows = (
        await db.execute(
            select(ExamAttempt.exam_item_id, ExamAttempt.correct, ExamAttempt.created_at).where(
                ExamAttempt.learner_id == profile.id, ExamAttempt.created_at >= since
            )
        )
    ).all()
    attempts = [exam_drill.Attempt(item_id=i, correct=ok, at=at) for i, ok, at in attempt_rows]
    code_of = {c.item_id: c.qtype_code for c in candidates}
    accuracy = exam_drill.accuracy_by_type((code_of[a.item_id], a.correct) for a in attempts if a.item_id in code_of)

    picked = exam_drill.pick(usable, attempts, accuracy, now, n=n, seed=f"{profile.id}:{now.date()}")
    items = []
    for c in picked:
        row = by_id[c.item_id]
        items.append(
            ExamDrillQuestion(
                id=c.item_id,
                number=c.number,
                qtype_code=c.qtype_code,
                qtype_name_vi=row[2],
                instruction_ko=c.instruction_ko.strip() or None,
                stem_ko=c.stem_ko,
                options=exam_drill.clean_options(c.options) or [],
                passage_ko=(c.passage_ko or "").strip() or None,
                paper_label=row[6],
            )
        )
    return ExamDrillOut(items=items, available=len(usable))


@router.post("/exam-drill/answers", response_model=ExamAnswerOut, dependencies=[Depends(study_day), Depends(require_exam_pass)])
async def answer_exam_drill(
    body: ExamAnswerRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
):
    """Check one answer against the key, keep the attempt, and — when it is wrong —
    log it under the question's type so it shows up in the weakness report."""
    row = (await db.execute(_bank_query().where(ExamItem.id == body.item_id))).first()
    if row is None:
        raise _problem(status.HTTP_404_NOT_FOUND, "Question not found", "not_found")
    candidate = _candidate(row)
    if not exam_drill.usable(candidate):
        raise _problem(status.HTTP_404_NOT_FOUND, "Question not found", "not_found")
    if body.chosen > exam_drill.option_count(candidate):
        raise _problem(status.HTTP_422_UNPROCESSABLE_ENTITY, "Choice out of range", "invalid_choice")

    correct = exam_drill.grade(candidate, body.chosen)
    db.add(ExamAttempt(learner_id=profile.id, exam_item_id=body.item_id, chosen=body.chosen, correct=correct))
    if not correct:
        db.add(
            ErrorLog(
                learner_id=profile.id,
                skill=candidate.skill,
                error_type=candidate.qtype_code,
                example_ko=candidate.stem_ko[:300],
                mode="exam",
                detail={
                    "exam_item_id": str(body.item_id),
                    "number": candidate.number,
                    "paper": row[6],
                    "chosen": body.chosen,
                    "answer": candidate.answer,
                },
            )
        )
    await db.commit()
    assert candidate.answer is not None  # usable() guarantees it
    return ExamAnswerOut(item_id=body.item_id, chosen=body.chosen, answer=candidate.answer, correct=correct)


# ----------------------------------------------------------------- weaknesses --
@router.get("/weaknesses", response_model=WeaknessesOut)
async def get_weaknesses(
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
):
    """Where the learner keeps going wrong over the last 30 days: counts by kind of
    mistake, the cards that went wrong more than once, the sets the mistakes gather
    in, and accuracy per exam question type. Plain counting — no score prediction."""
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=weakness.REPORT_DAYS)

    error_rows = (
        await db.execute(
            select(ErrorLog.skill, ErrorLog.error_type, ErrorLog.item_type, ErrorLog.item_id).where(
                ErrorLog.learner_id == profile.id, ErrorLog.created_at >= since
            )
        )
    ).all()
    rows = [weakness.ErrorRow(skill=a, error_type=b, item_type=c, item_id=d) for a, b, c, d in error_rows]
    qtype_names = dict((await db.execute(select(QuestionType.code, QuestionType.name_vi))).all())

    vocab_ids = {r.item_id for r in rows if r.item_type == "vocab_item" and r.item_id is not None}
    family_of: dict[weakness.ItemKey, str | None] = {}
    if vocab_ids:
        for vocab_id, family in (
            await db.execute(select(VocabItem.id, VocabItem.family).where(VocabItem.id.in_(vocab_ids)))
        ).all():
            family_of[("vocab_item", vocab_id)] = family

    repeats = weakness.repeat_items(rows)
    top_items: list[WeakItemOut] = []
    if repeats:
        wanted_vocab = [r.key[1] for r in repeats if r.key[0] == "vocab_item"]
        wanted_grammar = [r.key[1] for r in repeats if r.key[0] == "grammar_point"]
        vocab = (
            {v.id: v for v in (await db.execute(select(VocabItem).where(VocabItem.id.in_(wanted_vocab)))).scalars().all()}
            if wanted_vocab
            else {}
        )
        grammar = (
            {g.id: g for g in (await db.execute(select(GrammarPoint).where(GrammarPoint.id.in_(wanted_grammar)))).scalars().all()}
            if wanted_grammar
            else {}
        )
        for r in repeats:
            kind, item_id = r.key
            if kind == "vocab_item" and item_id in vocab:
                v = vocab[item_id]
                top_items.append(
                    WeakItemOut(item_type="vocab_item", item_id=item_id, title=v.hangul, meaning_vi=v.meaning_vi, family=v.family, errors=r.errors)
                )
            elif kind == "grammar_point" and item_id in grammar:
                g = grammar[item_id]
                top_items.append(
                    WeakItemOut(item_type="grammar_point", item_id=item_id, title=g.pattern, meaning_vi=g.meaning_vi, family=g.contrast_group, errors=r.errors)
                )

    attempt_rows = (
        await db.execute(
            select(QuestionType.code, ExamAttempt.correct)
            .join(ExamItem, ExamItem.id == ExamAttempt.exam_item_id)
            .join(QuestionType, QuestionType.id == ExamItem.qtype_id)
            .where(ExamAttempt.learner_id == profile.id, ExamAttempt.created_at >= since)
        )
    ).all()

    states = (await db.execute(select(ItemState).where(ItemState.learner_id == profile.id))).scalars().all()
    schedules = {(s.item_type, s.item_id): _schedule_of(s) for s in states}
    lesson_items = await _lesson_item_keys(db)
    articles = await _word_sources(db, profile)
    existing = {key for keys in lesson_items.values() for key in keys}
    existing |= {key for keys in articles.keys.values() for key in keys}
    shaky = srs.weak_keys(schedules, existing, limit=10_000)

    bank = (await db.execute(_bank_query())).all()
    exam_ready = sum(1 for row in bank if exam_drill.usable(_candidate(row)))

    return WeaknessesOut(
        days=weakness.REPORT_DAYS,
        total_errors=len(rows),
        by_type=[WeakTypeOut(error_type=c.error_type, label=c.label, skill=c.skill, count=c.count) for c in weakness.count_by_type(rows, qtype_names)],
        top_items=top_items,
        families=[WeakFamilyOut(family=f.family, errors=f.errors) for f in weakness.count_by_family(rows, family_of)],
        exam=[
            ExamAccuracyOut(qtype_code=a.qtype_code, name=a.name, attempts=a.attempts, correct=a.correct, accuracy_pct=a.accuracy_pct)
            for a in weakness.exam_accuracy(attempt_rows, qtype_names)
        ],
        weak_cards=len(shaky),
        leeches=sum(1 for key in shaky if srs.is_leech(schedules[key])),
        exam_ready=exam_ready,
    )


# ------------------------------------------------------------- writing drills --
def _drill_out(drill: WritingDrill) -> WritingDrillOut:
    return WritingDrillOut(
        id=drill.id,
        status=drill.status,  # type: ignore[arg-type]
        grade_status=drill.grade_status,  # type: ignore[arg-type]
        job_id=drill.job_id,
        prompt=WritingPromptOut(**writing_drill.public_view(drill.prompt)) if drill.status == "ready" and drill.prompt else None,
        answers=drill.answers,
        result=WritingResultOut(**drill.result) if drill.grade_status == "ready" and drill.result else None,
        created_at=drill.created_at,
    )


def _expire_if_stale(drill: WritingDrill, now: datetime) -> bool:
    """A generate/grade job that never finished (the worker died) must not leave the
    learner waiting forever. Returns whether anything changed."""
    changed = False
    age = now - (drill.updated_at or drill.created_at)
    if age > STALE_AFTER:
        if drill.status == "pending":
            drill.status = "failed"
            changed = True
        if drill.grade_status == "pending":
            drill.grade_status = "failed"
            changed = True
    return changed


async def _own_drill(db: AsyncSession, drill_id: uuid.UUID, profile: Profile) -> WritingDrill:
    drill = await db.get(WritingDrill, drill_id)
    if drill is None or drill.learner_id != profile.id:
        raise _problem(status.HTTP_404_NOT_FOUND, "Exercise not found", "not_found")
    return drill


@router.post("/writing-drills", response_model=WritingDrillStartOut, status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(require_exam_pass)])
async def start_writing_drill(
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
    body: WritingDrillStartRequest | None = None,
):
    """Start a "viết câu 51–52" exercise built from cards the learner is studying —
    the ones they get wrong most first. An exercise that is still being made, or
    made but not answered yet, is returned instead of starting another (each one
    costs model calls)."""
    now = datetime.now(timezone.utc)
    recent = (
        (await db.execute(select(WritingDrill).where(WritingDrill.learner_id == profile.id).order_by(WritingDrill.created_at.desc()).limit(12)))
        .scalars()
        .all()
    )
    for drill in recent:
        if _expire_if_stale(drill, now):
            db.add(drill)
    for drill in recent:
        waiting = drill.status == "pending" or (drill.status == "ready" and drill.grade_status in ("none", "pending"))
        if waiting and now - drill.created_at < timedelta(days=1):
            await db.commit()
            return WritingDrillStartOut(drill_id=drill.id, status=drill.status, job_id=drill.job_id)  # type: ignore[arg-type]
    if sum(1 for d in recent if now - d.created_at < timedelta(days=1)) >= MAX_NEW_DRILLS_PER_DAY:
        raise _problem(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Hôm nay bạn đã luyện viết khá nhiều rồi, mai làm tiếp nhé.",
            "daily_limit",
        )

    started = (
        (await db.execute(select(ItemState.item_id).where(ItemState.learner_id == profile.id, ItemState.item_type == "vocab_item")))
        .scalars()
        .all()
    )
    vocab = (
        {v.id: v for v in (await db.execute(select(VocabItem).where(VocabItem.id.in_(started)))).scalars().all()}
        if started
        else {}
    )
    if body is not None and body.deck_key:
        from app.api.routers.topik_bank import MIN_PRACTICED, practiced_words
        from app.services import topik_bank

        if body.deck_key not in topik_bank.decks():
            raise _problem(status.HTTP_404_NOT_FOUND, "Không có bộ từ này.", "not_found")
        deck_words = await practiced_words(db, profile, body.deck_key)
        if len(deck_words) < MIN_PRACTICED:
            raise _problem(
                status.HTTP_409_CONFLICT,
                "Hãy ôn thêm vài từ của bộ này (đúng ít nhất 2 lần) rồi mới viết câu bằng chính những từ đó.",
                "not_enough_words",
            )
        vocab = {v.id: v for v in deck_words}
    if not vocab:
        raise _problem(
            status.HTTP_409_CONFLICT,
            "Hãy ôn vài thẻ từ vựng trước, rồi bài viết sẽ được soạn từ chính những cụm đó.",
            "no_cards",
        )

    since = now - timedelta(days=weakness.REPORT_DAYS)
    error_counts = dict(
        (
            await db.execute(
                select(ErrorLog.item_id, func.count())
                .where(
                    ErrorLog.learner_id == profile.id,
                    ErrorLog.item_type == "vocab_item",
                    ErrorLog.item_id.isnot(None),
                    ErrorLog.created_at >= since,
                )
                .group_by(ErrorLog.item_id)
            )
        ).all()
    )
    states = (await db.execute(select(ItemState).where(ItemState.learner_id == profile.id, ItemState.item_type == "vocab_item"))).scalars().all()
    shaky = {s.item_id for s in states if srs.is_shaky(_schedule_of(s))}
    used = [int(item["item_id"]) for d in recent[:10] for item in (d.source_items or []) if item.get("item_type") == "vocab_item"]
    cards = [
        writing_drill.SourceCard(
            item_id=v.id,
            hangul=v.hangul,
            meaning_vi=v.meaning_vi,
            node_word=v.node_word,
            family=v.family,
            register=v.register,
            example_ko=v.example_ko,
            errors=error_counts.get(v.id, 0),
            shaky=v.id in shaky,
        )
        for v in vocab.values()
    ]
    chosen = writing_drill.pick_sources(cards, used, count=2)

    drill = WritingDrill(
        learner_id=profile.id,
        source_items=[{"item_type": "vocab_item", "item_id": c.item_id} for c in chosen],
        status="pending",
        grade_status="none",
    )
    db.add(drill)
    job = Job(type="generate_writing_drill", owner_id=profile.id, status="queued")
    db.add(job)
    await db.flush()
    drill.job_id = job.id
    await db.commit()
    generate_writing_drill.delay(str(job.id), str(drill.id))
    return WritingDrillStartOut(drill_id=drill.id, status="pending", job_id=job.id)


@router.get("/writing-drills/{drill_id}", response_model=WritingDrillOut)
async def get_writing_drill(
    drill_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
):
    drill = await _own_drill(db, drill_id, profile)
    if _expire_if_stale(drill, datetime.now(timezone.utc)):
        db.add(drill)
        await db.commit()
        await db.refresh(drill)
    return _drill_out(drill)


@router.post("/writing-drills/{drill_id}/answers", response_model=WritingDrillStartOut, status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(study_day), Depends(require_exam_pass)])
async def answer_writing_drill(
    drill_id: uuid.UUID,
    body: WritingAnswersRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
):
    """Send the learner's sentences for checking. An exercise is checked once; if
    the check failed (model outage) the same answers — or edited ones — can be sent
    again."""
    drill = await _own_drill(db, drill_id, profile)
    now = datetime.now(timezone.utc)
    if _expire_if_stale(drill, now):
        db.add(drill)
    if drill.status != "ready" or drill.prompt is None:
        raise _problem(status.HTTP_409_CONFLICT, "Đề chưa sẵn sàng.", "not_ready")
    if drill.grade_status in ("pending", "ready"):
        raise _problem(status.HTTP_409_CONFLICT, "Bài này đã được gửi chấm.", "already_graded")

    answers = {label: text.strip() for label, text in body.answers.items()}
    if any(len(text) > MAX_ANSWER_CHARS for text in answers.values()):
        raise _problem(status.HTTP_422_UNPROCESSABLE_ENTITY, "Mỗi chỗ trống chỉ viết một câu ngắn.", "answer_too_long")
    if not any(answers.values()):
        raise _problem(status.HTTP_422_UNPROCESSABLE_ENTITY, "Hãy viết ít nhất một câu.", "empty_answers")

    drill.answers = {label: answers.get(label, "") for label in writing_drill.LABELS}
    drill.grade_status = "pending"
    job = Job(type="grade_writing_drill", owner_id=profile.id, status="queued")
    db.add(job)
    await db.flush()
    drill.job_id = job.id
    db.add(drill)
    await db.commit()
    grade_writing_drill.delay(str(job.id), str(drill.id))
    return WritingDrillStartOut(drill_id=drill.id, status="ready", job_id=job.id)


# ---------------------------------------------------------------- mistake book --
@router.get("/mistakes", response_model=MistakeBookOut)
async def get_mistake_book(
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
):
    """Sổ lỗi sai: the practice questions the learner currently has wrong, with what they chose,
    the right answer, the explanation and the grammar cards the question is about, by lesson in
    curriculum order. Only the lessons that have the study guide (`coach`) are in the book for now; a
    question answered right later is no longer a mistake. Self-scored tasks (essay, speaking) are not."""
    rows = (
        await db.execute(
            select(LessonExerciseResult, Lesson)
            .join(Lesson, Lesson.id == LessonExerciseResult.lesson_id)
            .where(
                LessonExerciseResult.learner_id == profile.id,
                LessonExerciseResult.correct.is_(False),
                Lesson.coach.is_not(None),
            )
        )
    ).all()

    built: dict[int, tuple[Lesson, list[MistakeOut]]] = {}
    card_slugs: dict[tuple[int, str], dict[str, str]] = {}  # (lesson id, question id) -> pattern -> lesson slug
    for result, lesson in rows:
        exercise = lesson_seed.question_index(lesson.practice).get(result.question_id)
        if exercise is None:  # the lesson was edited and no longer has this question
            continue
        data = mistake_book.entry(exercise, result.question_id, result.last_answer)
        if data is None:
            continue
        info = (lesson.practice or {}).get("grammar") or {}
        patterns = [p for p in data.pop("grammar")[:3] if p in info]
        card_slugs[(lesson.id, result.question_id)] = {p: info[p]["lesson_slug"] for p in patterns if info[p].get("lesson_slug")}
        built.setdefault(lesson.id, (lesson, []))[1].append(
            MistakeOut(
                **data,
                grammar=[
                    MistakeGrammarOut(pattern=p, meaning_vi=info[p].get("meaning_vi"), lesson_title=info[p].get("lesson_title"))
                    for p in patterns
                ],
                attempts=result.attempts or 1,
                updated_at=result.updated_at,
                understood=result.understood_at is not None,
            )
        )

    slugs = {slug for per_question in card_slugs.values() for slug in per_question.values()}
    lesson_ids = dict((await db.execute(select(Lesson.slug, Lesson.id).where(Lesson.slug.in_(slugs)))).all()) if slugs else {}
    order = {lid: i for i, lid in enumerate(await _lesson_order(db))}
    lessons: list[MistakeLessonOut] = []
    for lesson_id in sorted(built, key=lambda i: order.get(i, len(order))):
        lesson, items = built[lesson_id]
        for m in items:
            per_pattern = card_slugs.get((lesson_id, m.question_id), {})
            for card in m.grammar:
                card.lesson_id = lesson_ids.get(per_pattern.get(card.pattern, ""))
        # open ones first, the most recent mistake first
        items.sort(key=lambda m: (m.understood, -m.updated_at.timestamp()))
        lessons.append(MistakeLessonOut(lesson_id=lesson.id, title=lesson.title, sort_order=lesson.sort_order, mistakes=items))
    total = sum(len(l.mistakes) for l in lessons)
    done = sum(m.understood for l in lessons for m in l.mistakes)
    return MistakeBookOut(lessons=lessons, open=total - done, understood=done)


@router.put("/mistakes/understood", response_model=MistakeBookOut)
async def mark_mistake_understood(
    body: MistakeUnderstoodRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    profile: Annotated[Profile, Depends(get_current_profile)],
):
    """"Đã hiểu" on one mistake (or taking it back): it moves to the end of the list, greyed. The next
    wrong answer to the same question puts it back. Returns the whole book."""
    row = (
        await db.execute(
            select(LessonExerciseResult).where(
                LessonExerciseResult.learner_id == profile.id,
                LessonExerciseResult.lesson_id == body.lesson_id,
                LessonExerciseResult.question_id == body.question_id,
                LessonExerciseResult.correct.is_(False),
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise _problem(status.HTTP_404_NOT_FOUND, "That question is not in your mistake book", "not_found")
    row.understood_at = datetime.now(timezone.utc) if body.understood else None
    await db.commit()
    return await get_mistake_book(db, profile)
