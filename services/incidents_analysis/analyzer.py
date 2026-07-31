from collections import Counter

from .models import Incident


def analyze_incidents(
    valid: list[Incident],
    invalid_counts: dict[str, int],
    total: int,
) -> dict:
    """Build aggregate metrics from valid incidents + invalid rule counts.

    Does not validate records and must not expose patient_id.
    """
    valid_count = len(valid)
    invalid_count = sum(invalid_counts.values())

    by_category = Counter(i.category for i in valid)
    by_status = Counter(i.status for i in valid)
    by_country = Counter(i.country for i in valid)

    def pct(count: int) -> float:
        if valid_count == 0:
            return 0.0
        return round(count / valid_count * 100, 1)

    closed_scored = [
        i.satisfaction_score
        for i in valid
        if i.status == "CLOSED" and i.satisfaction_score is not None
    ]
    score_histogram = Counter(closed_scored)
    average_score = (
        round(sum(closed_scored) / len(closed_scored), 2)
        if closed_scored
        else None
    )

    return {
        "total": total,
        "valid": valid_count,
        "invalid": invalid_count,
        "invalid_breakdown": invalid_counts,
        "by_category": {
            name: {"count": by_category[name], "percentage": pct(by_category[name])}
            for name in (
                "APPOINTMENT",
                "BILLING",
                "CLINICAL_CARE",
                "ACCESSIBILITY",
                "ADMINISTRATIVE",
            )
        },
        "by_status": {
            name: {"count": by_status[name], "percentage": pct(by_status[name])}
            for name in ("OPEN", "CLOSED", "DISCARDED")
        },
        "by_country": {
            name: {"count": by_country[name], "percentage": pct(by_country[name])}
            for name in ("US", "UK")
        },
        "satisfaction": {
            "scored_cases": len(closed_scored),
            "average": average_score,
            "histogram": {score: score_histogram[score] for score in range(1, 6)},
        },
    }