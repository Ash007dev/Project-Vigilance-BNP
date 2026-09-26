from collections import defaultdict


PATTERN_POINTS = {
    "STRUCTURING": 30,
    "MULE_ACCOUNT": 30,
    "LAYERING": 25,
    "CIRCULAR_FLOW": 35,
    "SHARED_DEVICE": 10,
    "SHARED_IP": 10,
    "CRYPTO_ACTIVITY": 10,
}


def classify_risk(score: int) -> str:

    if score <= 30:
        return "LOW"

    if score <= 60:
        return "MEDIUM"

    if score <= 80:
        return "HIGH"

    return "CRITICAL"


class RiskEngine:

    def __init__(self, detection_results):
        self.detection_results = detection_results

    def calculate(self):

        account_scores = defaultdict(
            lambda: {
                "score": 0,
                "patterns": [],
                "reasons": [],
            }
        )

        # ---------------------------------------
        # Process every detection
        # ---------------------------------------

        for category, findings in self.detection_results.items():

            for finding in findings:

                pattern = finding["pattern"]

                points = PATTERN_POINTS.get(
                    pattern,
                    0,
                )

                # Determine the entity associated
                # with the finding.
                account = (
                    finding.get("account")
                    or finding.get("identifier")
                )

                if not account:
                    continue

                account_scores[account]["score"] += points

                if pattern not in account_scores[account]["patterns"]:
                    account_scores[account]["patterns"].append(
                        pattern
                    )

                account_scores[account]["reasons"].append(
                    {
                        "pattern": pattern,
                        "points": points,
                        "reason": finding.get(
                            "reason",
                            "Suspicious activity detected.",
                        ),
                    }
                )

        # ---------------------------------------
        # Multiple-pattern bonus
        # ---------------------------------------

        for account, data in account_scores.items():

            if len(data["patterns"]) >= 2:

                data["score"] += 10

                data["reasons"].append(
                    {
                        "pattern": "MULTIPLE_PATTERNS",
                        "points": 10,
                        "reason": (
                            "Multiple independent risk "
                            "indicators were detected for "
                            "this entity."
                        ),
                    }
                )

        # ---------------------------------------
        # Cap at 100
        # ---------------------------------------

        results = []

        for account, data in account_scores.items():

            score = min(
                int(data["score"]),
                100,
            )

            results.append(
                {
                    "account": account,
                    "risk_score": score,
                    "risk_level": classify_risk(score),
                    "patterns": data["patterns"],
                    "reasons": data["reasons"],
                }
            )

        # Highest risk first
        results.sort(
            key=lambda item: item["risk_score"],
            reverse=True,
        )

        return results