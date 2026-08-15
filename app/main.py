import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s  %(name)s — %(message)s",
)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import agents, logs, messages, workflows
from app.routers.agent_config import router as agent_config_router
from app.routers.knowledge import router as knowledge_router
from app.routers.templates import router as templates_router
from app.routers.tools import router as tools_router
from app.routers.workflow_runs import router as workflow_runs_router
from app.routers.workflow_runs import ws_router as workflow_runs_ws_router
from app.scheduler import start_scheduler, stop_scheduler
from app.slack_bot import start_slack_bot, stop_slack_bot


@asynccontextmanager
async def lifespan(app: FastAPI):
    await start_slack_bot()
    await start_scheduler()
    yield
    await stop_scheduler()
    await stop_slack_bot()


app = FastAPI(title="Symphony API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agents.router)
app.include_router(agent_config_router)
app.include_router(knowledge_router)
app.include_router(templates_router)
app.include_router(tools_router)
app.include_router(workflows.router)
app.include_router(messages.router)
app.include_router(logs.router)
app.include_router(workflow_runs_router)
app.include_router(workflow_runs_ws_router)


@app.get("/")
async def root():
    return {"service": "Symphony API", "status": "ok"}