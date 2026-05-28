from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import agents, logs, messages, workflows

app = FastAPI(title="Symphony API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agents.router)
app.include_router(workflows.router)
app.include_router(messages.router)
app.include_router(logs.router)


@app.get("/")
async def root():
    return {"service": "Symphony API", "status": "ok"}