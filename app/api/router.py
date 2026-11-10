from fastapi import APIRouter

from app.api.routers import admin, admin_accounts, audio, auth, competency, content, conversation, conversation_history, debate, essay_checks, ingest, jobs, learning_events, lesson_images, practice, presentation, writing

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(jobs.router)
api_router.include_router(audio.router)
api_router.include_router(audio.vocab_router)
api_router.include_router(audio.text_router)
api_router.include_router(writing.router)
api_router.include_router(ingest.router)
api_router.include_router(admin.router)
api_router.include_router(admin_accounts.router)
api_router.include_router(content.router)
api_router.include_router(lesson_images.router)
api_router.include_router(practice.router)
api_router.include_router(essay_checks.router)
api_router.include_router(learning_events.router)
api_router.include_router(competency.router)
api_router.include_router(conversation.router)
api_router.include_router(conversation_history.router)
api_router.include_router(presentation.router)
api_router.include_router(debate.router)
