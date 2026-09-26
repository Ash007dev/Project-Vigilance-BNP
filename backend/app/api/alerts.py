from fastapi import APIRouter
from app.detection.engine import AMLDetectionEngine
from app.risk.engine import RiskEngine

router = APIRouter()


@router.get("/alerts")
def get_alerts():
    detection_engine = AMLDetectionEngine()
    detection_results = detection_engine.run_all()

    risk_engine = RiskEngine(detection_results, frame=detection_engine.df)
    risk_scores = risk_engine.calculate()

    alerts = []

    for item in risk_scores:
        # Low-risk accounts stay visible in scores but do not create alerts.
        if item["risk_level"] != "LOW":
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
