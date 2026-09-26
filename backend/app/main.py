"""Project Vigilance API entrypoint.

Router registration is defensive: several modules in this codebase
(detection engine, risk engine, DB layer) are still under active
development elsewhere in the project, and a broken import in any one
of them would otherwise take down the whole app. Each router is
imported and mounted independently, so a module that isn't ready yet
is skipped (with a logged warning) instead of blocking the routers
-- reports included -- that are.
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Project Vigilance API",
    description="AI-powered AML detection and investigation platform.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to the frontend's origin before production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


ROUTER_MODULES = [
    ("app.api.upload", "/api"),
    ("app.api.detection", "/api"),
    ("app.api.risk", "/api"),
    ("app.api.alerts", "/api"),
    ("app.api.graph", "/api"),
    ("app.api.investigation", "/api"),
    ("app.api.stats", "/api"),
    ("app.api.reports", "/api"),
]

for module_path, prefix in ROUTER_MODULES:
    try:
        module = __import__(module_path, fromlist=["router"])
        app.include_router(module.router, prefix=prefix)
        logger.info("Mounted router: %s -> %s", module_path, prefix)
    except Exception:
        logger.warning(
            "Skipping router %s: not ready yet (see traceback below).",
            module_path,
            exc_info=True,
        )


@app.get("/health")
def health_check():
    return {"status": "ok"}