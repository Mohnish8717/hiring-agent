"""Module 12: ApplicationFraudDetector — Detects automated job applications."""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("identity_trust.application_fraud")


class ApplicationFraudDetector:
    """Detects automated / fraudulent job applications using pattern analysis.

    NOTE: In production, this would compare against a database of known patterns.
    Currently uses heuristic signals from application metadata.
    """

    def detect(self, profile: Dict[str, Any], application_metadata: Dict[str, Any] | None = None) -> Optional[float]:
        """Returns application_authenticity_score (0-10) or None if no metadata."""
        if not application_metadata:
            logger.info("ApplicationFraud: no metadata available")
            return None

        score = 8.0  # Default: assume authentic

        # --- Check for empty / minimal profile ---
        name = profile.get("name", "")
        email = profile.get("email", "")
        skills = profile.get("resume_skills", [])
        experience = profile.get("resume_experience", [])

        if not name or not email:
            score -= 2.0
        if not skills:
            score -= 1.0
        if not experience:
            score -= 1.5

        # --- Duplicate Resume Patterns ---
        if application_metadata:
            duplicate_count = application_metadata.get("duplicate_resume_count", 0)
            if isinstance(duplicate_count, int) and duplicate_count > 3:
                score -= 3.0
                logger.warning(f"Duplicate resume detected: {duplicate_count} copies")

            # Rapid applications
            apps_per_hour = application_metadata.get("applications_per_hour", 0)
            if isinstance(apps_per_hour, (int, float)) and apps_per_hour > 10:
                score -= 2.0
                logger.warning(f"Rapid application rate: {apps_per_hour}/hour")

            # Identical cover letters
            identical_cover_letters = application_metadata.get("identical_cover_letter_count", 0)
            if isinstance(identical_cover_letters, int) and identical_cover_letters > 2:
                score -= 1.5

        score = max(0.0, min(10.0, score))
        logger.info(f"ApplicationFraud: authenticity_score={score:.1f}")
        return round(score, 1)  # type: ignore
