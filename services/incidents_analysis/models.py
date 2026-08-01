from dataclasses import dataclass

@dataclass
class Incident:
    incident_id: str
    date: str
    clinic_id: str
    country: str
    category: str
    description: str
    status: str
    patient_id: str  # PHI — never print, log, or export
    satisfaction_score: int | None = None