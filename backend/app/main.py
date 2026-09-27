from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.upload import router as upload_router
from app.api.stats import router as stats_router

from app.api.detection import router as detection_router
from app.api.risk import router as risk_router
from app.api.alerts import router as alerts_router
from app.api.investigation import router as investigation_router
from app.api.graph import router as graph_router
from app.api.ai import router as ai_router
from app.api.copilot import router as copilot_router
from app.api.report import router as report_router

app = FastAPI(
    title="Project Vigilance",
    description="AI-assisted AML Investigation Platform",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    upload_router,
    prefix="/api",
)

app.include_router(
    stats_router,
    prefix="/api",
)

app.include_router(
    detection_router,
    prefix="/api",
)

app.include_router(
    risk_router,
    prefix="/api",
)

app.include_router(
    alerts_router,
    prefix="/api",
)

app.include_router(
    investigation_router,
    prefix="/api",
)

app.include_router(
    graph_router,
    prefix="/api",
)

app.include_router(
    ai_router,
    prefix="/api",
    )

app.include_router(
    copilot_router,
    prefix="/api",
)

app.include_router(
        report_router,
        prefix="/api",
    )

@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "project-vigilance",
    }


@app.get("/")
def root():
    return {
        "project": "Project Vigilance",
        "status": "running",
    }
