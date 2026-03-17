"""Module 10: BehavioralSignalsEngine — Detects bot-like candidate behavior."""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("identity_trust.behavioral_signals")


class BehavioralSignalsEngine:
    """Detects bot-like application behavior using metadata signals.

    NOTE: In production, this would integrate with real application telemetry.
    Currently uses heuristic analysis of available metadata.
    """

    def analyze(self, profile: Dict[str, Any], application_metadata: Dict[str, Any] | None = None) -> Optional[float]:
        """Returns behavioral_trust_score (0-10) or None if no metadata."""
        if not application_metadata:
            logger.info("BehavioralSignals: no application metadata available")
            return None

        score = 7.0  # Default: neutral-positive assumption

        # --- Application Velocity ---
        apps_last_24h = application_metadata.get("applications_last_24h", 0)
        if isinstance(apps_last_24h, int):
            if apps_last_24h > 50:
                score -= 3.0  # Likely automated
                logger.warning(f"High application velocity: {apps_last_24h} in 24h")
            elif apps_last_24h > 20:
                score -= 1.5

        # --- Interaction Timing ---
        avg_time_on_form_sec = application_metadata.get("avg_time_on_form_seconds", None)
        if isinstance(avg_time_on_form_sec, (int, float)):
            if avg_time_on_form_sec < 30:
                score -= 2.0  # Too fast, likely bot
            elif avg_time_on_form_sec < 60:
                score -= 0.5

        # --- Assessment Behavior ---
        assessment_completion_time = application_metadata.get("assessment_time_seconds", None)
        if isinstance(assessment_completion_time, (int, float)):
            if assessment_completion_time < 10:
                score -= 2.0  # Impossibly fast

        # --- Session Signals ---
        unique_sessions = application_metadata.get("unique_sessions", 1)
        if isinstance(unique_sessions, int) and unique_sessions > 1:
            score += 0.5  # Multiple sessions suggests genuine interest

        score = max(0.0, min(10.0, score))
        logger.info(f"BehavioralSignals: score={score:.1f}")
        return round(score, 1)  # type: ignore
