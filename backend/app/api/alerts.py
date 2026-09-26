from fastapi import APIRouter
from app.detection.engine import AMLDetectionEngine
from app.risk.engine import RiskEngine

router = APIRouter()


@router.get("/alerts")
def get_alerts():
    detection_engine = AMLDetectionEngine()
    detection_results = detection_engine.run_all()

    risk_engine = RiskEngine(detection_results)
    risk_scores = risk_engine.calculate()

    alerts = []

    for item in risk_scores:
        # Only create alerts for entities with suspicious activity
        if item["risk_score"] > 0:
            alerts.append(
                {
                    "alert_id": f"ALT-{len(alerts) + 1:04d}",
                    "account": item["account"],
                    "risk_score": item["risk_score"],
                    "risk_level": item["risk_level"],
                    "patterns": item["patterns"],
                    "reasons": item["reasons"],
                    "status": "OPEN",
                }
            )

    return {
        "status": "success",
        "total_alerts": len(alerts),
        "alerts": alerts,
    }