"""EUNIA FastAPI application entry point."""
import asyncio
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from .routers import router
from .knowledge_processing import resume_pending_documents
from .task_processing import resume_pending_tasks


@asynccontextmanager
async def lifespan(_: FastAPI):
    recovery = asyncio.create_task(asyncio.to_thread(resume_pending_documents))
    task_recovery = asyncio.create_task(asyncio.to_thread(resume_pending_tasks))
    yield
    if not recovery.done():
        recovery.cancel()
    if not task_recovery.done():
        task_recovery.cancel()


app = FastAPI(title="EUNIA API", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","), allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
