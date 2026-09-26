from fastapi import APIRouter

from app.detection.engine import AMLDetectionEngine


router = APIRouter()


@router.post("/detect")
def detect_suspicious_activity():

    engine = AMLDetectionEngine()

    results = engine.run_all()

    total_findings = sum(
        len(findings)
        for findings in results.values()
    )

    return {
        "status": "success",
        "total_findings": total_findings,
        "results": results,
    }