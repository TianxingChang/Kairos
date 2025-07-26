from fastapi import APIRouter

from api.routes.agents import agents_router
from api.routes.health import health_router
from api.routes.playground import playground_router
from api.routes.youtube import router as youtube_router
from api.routes.video_qa import router as video_qa_router
from api.routes.frontend_video_qa import router as frontend_video_qa_router
from api.routes.frontend_youtube import router as frontend_youtube_router

v1_router = APIRouter(prefix="/v1")
v1_router.include_router(health_router)
v1_router.include_router(agents_router)
v1_router.include_router(playground_router)
v1_router.include_router(youtube_router)
v1_router.include_router(video_qa_router)
v1_router.include_router(frontend_video_qa_router)
v1_router.include_router(frontend_youtube_router)

