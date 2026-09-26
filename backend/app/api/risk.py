from fastapi import APIRouter

from app.detection.engine import AMLDetectionEngine
from app.risk.engine import RiskEngine


router = APIRouter()


@router.get("/risk-scores")
def get_risk_scores():

    detection_engine = AMLDetectionEngine()

    detection_results = (
        detection_engine.run_all()
    )

    risk_engine = RiskEngine(
        detection_results
    )

    scores = risk_engine.calculate()

    return {
        "status": "success",
        "total_entities": len(scores),
        "risk_scores": scores,
    }