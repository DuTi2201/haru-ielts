from fastapi import APIRouter

from app.api.routers import admin, admin_accounts, audio, auth, competency, content, essay_checks, ingest, jobs, learning_events, lesson_images, practice, pronunciation, speech

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(jobs.router)
api_router.include_router(audio.router)
api_router.include_router(audio.vocab_router)
api_router.include_router(audio.text_router)
api_router.include_router(ingest.router)
api_router.include_router(admin.router)
api_router.include_router(admin_accounts.router)
api_router.include_router(content.router)
api_router.include_router(lesson_images.router)
api_router.include_router(practice.router)
api_router.include_router(essay_checks.router)
api_router.include_router(learning_events.router)
api_router.include_router(speech.router)
api_router.include_router(pronunciation.router)
api_router.include_router(competency.router)

