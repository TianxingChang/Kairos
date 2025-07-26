from fastapi import APIRouter

from api.routes.agents import agents_router
from api.routes.health import health_router
from api.routes.playground import playground_router
from api.routes.knowledge_graph import knowledge_graph_router
from api.routes.learning import learning_router
from api.routes.video_segments import video_segments_router
from api.routes.knowledge_hierarchy import knowledge_hierarchy_router
from api.routes.questions import questions_router
from api.routes.video_answers import video_answer_router

from api.routes.youtube import router as youtube_router
from api.routes.video_qa import router as video_qa_router
from api.routes.frontend_video_qa import router as frontend_video_qa_router
from api.routes.frontend_youtube import router as frontend_youtube_router

v1_router = APIRouter(prefix="/v1")
v1_router.include_router(health_router)
v1_router.include_router(agents_router)
v1_router.include_router(playground_router)

v1_router.include_router(knowledge_graph_router)
v1_router.include_router(learning_router)
v1_router.include_router(video_segments_router)
v1_router.include_router(knowledge_hierarchy_router)
v1_router.include_router(questions_router)
v1_router.include_router(video_answer_router)
v1_router.include_router(youtube_router)
v1_router.include_router(video_qa_router)
v1_router.include_router(frontend_video_qa_router)
v1_router.include_router(frontend_youtube_router)

